# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.10'
__release__ = 20230104
__all__ = ['SimDataFrame']

# import warnings

from sys import getsizeof
from os.path import commonprefix
import pandas as pd
import fnmatch
from pandas import Series, DataFrame, DatetimeIndex, Timestamp, Index
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
from unyts.converter import convertible as _convertible, convert_for_SimPandas as _converter
from unyts.operations import unit_power as _unit_power

from simpandas.common.slope import slope as _slope
from simpandas.common.stringformat import multisplit, is_date, date as strDate
from simpandas.common.math import znorm as _znorm, minmaxnorm as _minmaxnorm, jitter as _jitter
from simpandas.indexer import _SimLocIndexer
from simpandas.series import SimSeries
from simpandas.common.helpers import clean_axis
from simpandas.writters.xlsx import write_excel


def _series2frame(a_SimSeries):
    """
    when a row is extracted from a DataFrame, Pandas returns a Series in wich
    the columns of the DataFrame are converted to the indexes of the Series and
    the extracted index from the DataFrame is set as the Name of the Series.

    This function returns the proper DataFrame view of such Series.

    Works with SimSeries as well as with Pandas standard Series
    """
    if isinstance(a_SimSeries, DataFrame):
        return a_SimSeries
    if type(a_SimSeries) is SimSeries:
        try:
            from simpandas.frame import SimDataFrame
            return SimDataFrame(data=dict(zip(list(a_SimSeries.index),
                                              a_SimSeries.to_list()
                                              )
                                          ),
                                units=a_SimSeries.get_units(),
                                index=a_SimSeries.columns,
                                verbose=a_SimSeries.verbose,
                                indexName=a_SimSeries.index.name,
                                indexUnits=a_SimSeries.index_units,
                                nameSeparator=a_SimSeries.name_separator,
                                intersectionCharacter=a_SimSeries.intersection_character,
                                autoAppend=a_SimSeries.auto_append,
                                operatePerName=a_SimSeries.operate_per_name)
        except:
            return a_SimSeries
    if type(a_SimSeries) is Series:
        try:
            return DataFrame(data=dict(zip(list(a_SimSeries.index),
                                           a_SimSeries.to_list()
                                           )
                                       ),
                             index=a_SimSeries.columns)
        except:
            return a_SimSeries


class SimDataFrame(DataFrame):
    """
    A SimDataFrame object is a pandas.DataFrame that units associated with to
    each column. In addition to the standard DataFrame constructor arguments,
    SimDataFrame also accepts the following keyword arguments:

    Parameters
    ----------
    units : string or dictionary of units(optional)
        Can be any string, but only units acepted by the UnitConverter will
        be considered when doing arithmetic calculations with other SimSeries
        or SimDataFrames.

    See Also
    --------
    SimSeries
    pandas.DataFrame

    """
    _metadata = ['units',
                 'verbose',
                 'index_units',
                 'name_separator',
                 'intersection_character',
                 'auto_append',
                 'spdLocator',
                 'operate_per_name',
                 'transposed',
                 'name']

    def __init__(self,
                 data=None,
                 index=None,
                 columns=None,
                 units=None,
                 dtype=None,
                 name=None,
                 copy=None,
                 verbose=False,
                 index_name=None,
                 index_units=None,
                 name_separator=None,
                 intersection_character='∩',
                 auto_append=False,
                 operate_per_name=False,
                 transposed=False,
                 *args, **kwargs):

        self.units = {}
        self.verbose = bool(verbose)
        self.index_units = None
        self.name_separator = None
        self.intersection_character = intersection_character if type(intersection_character) is str else '∩'
        self.auto_append = bool(auto_append)
        self.operate_per_name = bool(operate_per_name)
        self.transposed = bool(transposed)
        self.spdLocator = _SimLocIndexer("loc", self)
        self.name = name

        # get units from data if it is SimDataFrame or SimSeries
        if units is None or (type(units) in [list, dict] and len(units) == 0):
            if hasattr(data, 'get_units'):
                units = data.get_units()
        elif type(units) is str:
            units = units.strip()

        # get nameSeparator
        if name_separator is None and hasattr(data, 'nameSeparator'):
            name_separator = data.name_separator
        elif name_separator is not None and type(name_separator) is str and len(name_separator.strip()) > 0:
            pass
        elif name_separator is False:
            name_separator = ''
        else:
            name_separator = ':'
        self.name_separator = name_separator

        # define default dtype
        if data is None and dtype is None:
            dtype = object

        # initialize pd.DataFrame
        super().__init__(data=data, index=index, columns=columns, dtype=dtype, copy=copy)

        # set units
        self.set_units(units)

        # get indexUnits
        if index_units is None:
            if self.index.name is not None and self.index.name in self.units:
                self.index_units = self.units[self.index.name]
            elif hasattr(data, 'indexUnits'):
                self.index_units = data.indexUnits.copy() if type(data.indexUnits) is dict else data.indexUnits

        # override index.name with indexName
        if index_name is not None:
            if self.index.name in self.units:
                self.units[index_name] = self.units[self.index.name]
            self.index.name = index_name

    @property
    def _constructor(self):
        return SimDataFrame

    @property
    def _constructor_sliced(self):
        return SimSeries

    @property
    def _class(self):
        return SimDataFrame

    def __repr__(self):
        """
        Return a string representation for a particular DataFrame, with Units.
        """
        return self._DataFrame_with_MultiIndex().__repr__()

    def __call__(self, key=None):
        if key is None:
            key = self.columns
        result = self.__getitem__(key)
        if isinstance(result, SimSeries):
            result = result.__call__()
        return result

    def __getitem__(self, key):
        # if key is boolean filter, return the filtered SimDataFrame
        if isinstance(key, Series) or type(key) is np.ndarray:
            if str(key.dtype) == 'bool':
                return SimDataFrame(data=self._get_by_filter(key), **self.params_)

        # if key is pd.Index or pd.MultiIndex return selected rows or columns
        if isinstance(key, Index):
            key_cols = True
            for each in key:
                if each not in self.columns:
                    key_cols = False
                    break
            if key_cols:
                return SimDataFrame(data=self._get_by_column(key), **self.params_)
            else:
                result = SimDataFrame(data=self._get_by_index(key), **self.params_)
                if len(result) == 1:
                    result = _series2frame(result)
                return result

        # here below we try to guess what the user is requesting
        by_index = False
        index_filter = None
        indexes = None
        slices = None
        result = None  # initialize variable

        # convert tuple argument to list
        if type(key) is tuple:
            key = list(key)

        # if key is a string but not a column name, check if it is an item, attribute, pattern, filter or index
        if type(key) is str and key not in self.columns:
            if bool(self.find_keys(key)):  # catch the column names this key represent
                key = list(self.find_keys(key))
            elif key == self.index_name:  # key is the name of the index
                result = self.index
            else:  # key is not a column name
                try:  # to evaluate as a filter
                    result = self._get_by_criteria(key)
                except:
                    try:  # to evaluate as an index value
                        result = self._get_by_index(key)
                    except:
                        raise ValueError(
                            'requested key is not a valid column name, pattern, index or filter criteria:\n   ' + key)
                if result is None:
                    try:
                        result = self._get_by_index(key)
                    except:
                        raise ValueError(
                            'requested key is not a valid column name, pattern, index or filter criteria:\n   ' + key)

        # key is a list, have to check every item in the list
        elif type(key) is list:
            key_list, key, filters, indexes, slices = key, [], [], [], []
            for each in key_list:
                # the key is a column name
                if type(each) is slice:
                    slices += [each]
                elif each in self.columns:
                    key += [each]
                # if key is a string but not a column name, check if it is an item, attribute, pattern, filter or index
                elif type(each) is str:
                    if bool(self.find_keys(each)):  # catch the column names this key represent
                        key += list(self.find_keys(each))
                    else:  # key is not a column name, might be a filter or index
                        try:  # to evaluate as a filter
                            _ = self.filter(each, returnFilter=True)
                            filters += [each]
                        except:
                            try:  # to evaluate as an index value
                                _ = self._get_by_index(each)
                                indexes += [each]
                            except:
                                # discard this item
                                print(' the parameter ' + str(each) + ' is not valid.')

                # must be an index, not a column name o relative, not a filter, not in the index
                else:
                    indexes += [each]

            # get the filter array, if filter criteria was provided
            if bool(filters):
                try:
                    index_filter = self.filter(filters, returnFilter=True)
                except:
                    raise Warning('filter conditions are not valid:\n   ' + ' and '.join(filters))
                if index_filter is not None and not index_filter.any():
                    raise Warning('filter conditions removed every row :\n   ' + ' and '.join(filters))

        # attempt to get the desired keys, first as column names, then as indexes
        if result is not None:
            params_ = self.params_
            params_['index_name'] = None
            params_['units'] = self.get_units(key)
            params_['columns'] = key if type(key) in (list, Index) else [key]
            result = SimDataFrame(data=result, **params_)
        elif bool(key) or key == 0:
            try:
                result = self._get_by_column(key)
            except:
                result = self._get_by_index(key)
                if result is not None: by_index = True
        else:
            result = SimDataFrame(data=self, **self.params_)

        # convert returned object to SimDataFrame or SimSeries accordingly
        if type(result) is DataFrame:
            result_units = self.get_units(result.columns)
            params_ = self.params_
            params_['units'] = result_units
            result = SimDataFrame(data=result, **params_)
        elif type(result) is Series:
            if len(self.get_units()) > 0:
                if result.name is None or result.name not in self.get_units():
                    # this Series is one index for multiple columns
                    try:
                        result_units = self.get_units(result.index)
                    except:
                        result_units = {result.name: 'unitless'}
                else:
                    result_units = self.get_units(result.name)
            else:
                result_units = {result.name: 'unitless'}
            params_ = self.params_
            params_['units'] = result_units
            result = SimSeries(data=result, **params_)

        # apply filter array if applicable
        if index_filter is not None:
            if type(index_filter) is np.ndarray:
                result = result.iloc[index_filter]
            else:
                result = result[index_filter.array]

        # apply indexes and slices
        if bool(indexes) or bool(slices):
            index_slices = indexes + slices
            i_result = _series2frame(result._get_by_index(index_slices[0]))
            if len(index_slices) > 1:
                for i in index_slices[1:]:
                    i_result = i_result.append(_series2frame(result._get_by_index(i)))
            try:
                result = i_result.sort_index()
            except:
                result = i_result

        # if is a single row return it as a DataFrame instead of a Series
        if by_index:
            result = _series2frame(result)

        if type(result) is DataFrame:
            result = SimDataFrame(result, **self.params_)
        elif type(result) is Series:
            result = SimSeries(result, **self.params_)

        return result

    def __setitem__(self, key, value, units=None):
        u_dict = {}
        if type(key) is str:
            key = key.strip()
        if type(value) is tuple and len(value) == 2 and type(value[1]) in [str,
                                                                           dict] and units is None:  # and type(value[0]) in [SimSeries, Series, list, tuple, np.ndarray,float,int,str]
            value, units = value[0], value[1]
        if type(value) is SimDataFrame and len(value.index) == 1 and type(key) is not slice and (
                (key in self.index or pd.to_datetime(key) in self.index) and (
                key not in self.columns and pd.to_datetime(key) not in self.columns)):
            self.loc[key] = value
            return None
        if units is None:
            if type(value) is SimSeries:
                if type(value.units) is str:
                    u_dict = {str(key): value.units}
                elif type(value.units) is dict:
                    u_dict = value.units
                else:
                    u_dict = {str(key): 'unitless'}
                if self.index_units is None and value.indexUnits is not None:
                    self.index_units = value.indexUnits
            elif isinstance(value, SimDataFrame):
                if len(value.columns) == 1:
                    if value.columns[0] in value.units:
                        u_dict = {str(key): value.units[value.columns[0]]}
                    else:
                        u_dict = {str(key): 'unitless'}
                else:
                    u_dict = value.units.copy() if type(value.units) is dict else {str(key): value.units}
                    if value.index.name not in value.columns and value.index.name in u_dict:
                        del u_dict[value.index.name]
                    if key not in u_dict and len(set(u_dict.values())) == 1:
                        u_dict[str(key)] = list(set(u_dict.values()))[0]
                    if self.index_units is None and value.index_units is not None:
                        self.index_units = value.index_units
                    elif self.index_units is not None and value.index_units is not None and self.index_units != value.index_units:
                        if _convertible(value.index_units, self.index_units):
                            try:
                                value.index = _converter(value.index, value.index_units, self.index_units)
                            except:
                                print(
                                    "WARNING: failed to convert the provided index to the units of this SimDataFrame index.")
                        else:
                            print(
                                "WARNING: not able to convert the provided index to the units of this SimDataFrame index.")

            else:
                u_dict = {str(key): 'unitless'}
        elif type(units) is str:
            u_dict = {str(key): units.strip()}
        elif type(units) is dict:
            u_dict = units
        else:
            raise NotImplementedError

        if isinstance(value, SimDataFrame):
            if len(value.columns) == 1:
                value = value.to_simseries()
            elif len(value.columns) > 2:
                for col in value.columns:
                    self.__setitem__(col, value[col])
                return None

        before = len(self.columns)
        super().__setitem__(key, value)
        after = len(self.columns)

        if after == before:
            self.new_units(key, u_dict[key])
        elif after > before:
            for c in range(before, after):
                if self.columns[c] in self.columns[before: after] and self.columns[c] in u_dict:
                    self.new_units(self.columns[c], u_dict[self.columns[c]])
                else:
                    self.new_units(self.columns[c], 'unitless')

    def __add__(self, other):
        # both are SimDataFrame
        if isinstance(other, SimDataFrame):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimDataFrames are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")
            not_fount = 0

            self_i, other_i = self._joined_index(other)
            result = self_i.copy()

            for col in other_i.columns:
                if col in self_i.columns:
                    result[col] = self_i[col] + other_i[col]
                else:
                    not_fount += 1
                    result[col] = other_i[col]

            if not_fount == len(other_i.columns):
                if self_i.name_separator is not None and other_i.name_separator is not None:
                    self_c, other_c, new_names = self_i._common_rename(other_i)

                    # if no columns has common names
                    if new_names is None:
                        if len(other_c.columns) == 1 and not self.auto_append:  # just in case there is only one column in the second operand
                            return self_c + other_c.to_simseries()
                        elif not self.auto_append:
                            raise TypeError("Not possible to operate SimDataFrames if there aren't common columns")
                        else:  # self.autoAppend is True
                            for col in other_i.columns:
                                result[col] = other_i[col]
                    else:
                        if (self_i.columns != self_c.columns).any() or (other_i.columns != other_c.columns).any():
                            result_x = self_c + other_c
                            result_x.rename(columns=new_names, inplace=True)
                        else:
                            result_x = result
                        if self.auto_append:
                            for col in new_names.values():
                                result[col] = result_x[col]
                        else:
                            result = result_x
            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, Series)):
            if type(other) is Series:
                other = SimSeries(other, **self.params_)
            self_i, other_i = self._joined_index(other)
            other_i = other_i.to_simseries()
            result = self_i.copy()
            if self.operate_per_name and other_i.name in self_i.columns:
                result[other_i.name] = self_i[other_i.name] + other_i
            elif self_i.auto_append:
                result[other_i.name] = other_i
            else:
                for col in self_i.columns:
                    result[col] = self_i[col] + other_i
            return result

        # other is Pandas DataFrame
        elif isinstance(other, DataFrame):
            # result = self.DF.add(other, fill_value=0)
            self_c, other_c, new_names = self._common_rename(SimDataFrame(other, **self.params_))
            result = self_c + other_c
            return result if new_names is None else result.rename(columns=new_names)

        # lets Pandas deal with other types, maintain units and dtype
        else:
            result = self.as_DataFrame() + other
            return SimDataFrame(data=result, **self.params_)

    def __sub__(self, other):
        # both are SimDataFrame
        if isinstance(other, SimDataFrame):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimDataFrames are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")
            notFount = 0

            selfI, otherI = self._joined_index(other)
            result = selfI.copy()

            for col in otherI.columns:
                if col in selfI.columns:
                    result[col] = selfI[col] - otherI[col]
                else:
                    notFount += 1
                    result[col] = otherI[col] if selfI.intersection_character in col else -otherI[col]

            if notFount == len(otherI.columns):
                if selfI.name_separator is not None and otherI.name_separator is not None:
                    selfC, otherC, newNames = selfI._common_rename(otherI)

                    # if no columns has common names
                    if newNames is None:
                        if len(otherC.columns) == 1:  # just in case there is only one column in the second operand
                            return selfC - otherC.to_simseries()
                        else:
                            raise TypeError("Not possible to operate SimDataFrames if there aren't common columns")

                    resultX = selfC - otherC
                    resultX.rename(columns=newNames, inplace=True)
                    if self.auto_append:
                        for col in newNames.values():
                            result[col] = resultX[col]
                    else:
                        result = resultX
            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, Series)):
            if type(other) is Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self.operate_per_name and otherI.name in selfI.columns:
                result[otherI.name] = selfI[otherI.name] - otherI
            if self.auto_append:  # elif self.autoAppend:
                result[otherI.name] = -otherI
            else:
                for col in selfI.columns:
                    result[col] = selfI[col] - otherI
            return result

        # other is Pandas DataFrame
        elif isinstance(other, DataFrame):
            # result = self.DF.sub(other, fill_value=0)
            selfC, otherC, newNames = self._common_rename(SimDataFrame(other, **self.params_))
            result = selfC - otherC
            return result if newNames is None else result.rename(columns=newNames)

        # let's Pandas deal with other types, maintain units and dtype
        else:
            result = self.as_DataFrame() - other
            return SimDataFrame(data=result, **self.params_)

    def __mul__(self, other):
        # both are SimDataFrame
        if isinstance(other, SimDataFrame):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimDataFrames are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")

            self_i, other_i = self._joined_index(other)
            result = self_i.copy()

            not_fount = 0
            for col in other_i.columns:
                if col in self_i.columns:
                    result[col] = self_i[col] * other_i[col]
                else:
                    not_fount += 1

            if not_fount == len(other_i.columns):
                if self_i.name_separator is not None and other_i.name_separator is not None:
                    self_c, other_c, new_names = self_i._common_rename(other_i)

                    # if no columns has common names
                    if new_names is None:
                        if len(other_c.columns) == 1:  # just in case there is only one column in the second operand
                            return self_c * other_c.to_simseries()
                        else:
                            raise TypeError("Not possible to operate SimDataFrames if there aren't common columns")

                    result_x = self_c * other_c
                    result_x.rename(columns=new_names, inplace=True)
                    if self.auto_append:
                        for col in new_names.values():
                            if self.intersection_character in col:  # intersectionCharacter = '∩'
                                result[col] = result_x[col]
                    else:
                        result = result_x

            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, Series)):
            if type(other) is Series:
                other = SimSeries(other, **self.params_)
            self_i, other_i = self._joined_index(other)
            result = self_i.copy()
            if self.operate_per_name and other_i.name in self_i.columns:
                result[other_i.name] = self[other_i.name] * other_i
            else:
                for col in self_i.columns:
                    result[col] = self_i[col] * other_i
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, DataFrame):
            return self.__mul__(SimDataFrame(data=other, **self.params_))

        # let's Pandas deal with other types, maintain units and dtype
        else:
            result = self.as_DataFrame() * other
            return SimDataFrame(data=result, **self.params_)



    def __truediv__(self, other):
        # both are SimDataFrame
        if isinstance(other, SimDataFrame):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimDataFrames are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")

            selfI, otherI = self._joined_index(other)
            result = selfI.copy()

            notFount = 0
            for col in otherI.columns:
                if col in selfI.columns:
                    result[col] = selfI[col] / otherI[col]
                else:
                    notFount += 1

            if notFount == len(otherI.columns):
                if self.name_separator is not None and otherI.name_separator is not None:
                    selfC, otherC, newNames = selfI._common_rename(otherI)

                    # if no columns has common names
                    if newNames is None:
                        if len(otherC.columns) == 1:  # just in case there is only one column in the divisor
                            return selfC / otherC.to_simseries()
                        else:
                            raise TypeError("Not possible to operate SimDataFrames if there aren't common columns")

                    resultX = selfC / otherC
                    resultX.rename(columns=newNames, inplace=True)
                    if self.auto_append:
                        for col in newNames.values():
                            if self.intersection_character in col:  # intersectionCharacter = '∩'
                                result[col] = resultX[col]
                    else:
                        result = resultX
            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, Series)):
            if type(other) is Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self.operate_per_name and otherI.name in selfI.columns:
                result[otherI.name] = selfI[otherI.name] / otherI
            else:
                for col in selfI.columns:
                    result[col] = selfI[col] / otherI
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, DataFrame):
            return self.__truediv__(SimDataFrame(data=other, **self.params_))

        # let's Pandas deal with other types, maintain units and dtype
        else:
            result = self.as_DataFrame() / other
            return SimDataFrame(data=result, **self.params_)

    def __floordiv__(self, other):
        # both are SimDataFrame
        if isinstance(other, SimDataFrame):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimDataFrames are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")

            selfI, otherI = self._joined_index(other)
            result = selfI.copy()

            notFount = 0
            for col in otherI.columns:
                if col in selfI.columns:
                    result[col] = selfI[col] // otherI[col]
                else:
                    notFount += 1

            if notFount == len(otherI.columns):
                if selfI.name_separator is not None and otherI.name_separator is not None:
                    selfC, otherC, newNames = selfI._common_rename(otherI)

                    # if no columns has common names
                    if newNames is None:
                        if len(otherC.columns) == 1:  # just in case there is only one column in the second operand
                            return selfC // otherC.to_simseries()
                        else:
                            raise TypeError("Not possible to operate SimDataFrames if there aren't common columns")

                    resultX = selfC // otherC
                    resultX.rename(columns=newNames, inplace=True)
                    if self.auto_append:
                        for col in newNames.values():
                            if self.intersection_character in col:  # intersectionCharacter = '∩'
                                result[col] = resultX[col]
                    else:
                        result = resultX
            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, Series)):
            if type(other) is Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self.operate_per_name and otherI.name in selfI.columns:
                result[otherI.name] = selfI[otherI.name] // otherI
            else:
                for col in self.columns:
                    result[col] = self[col] // other
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, DataFrame):
            return self.__floordiv__(SimDataFrame(data=other, **self.params_))

        # lets Pandas deal with other types, maintain units and dtype
        else:
            result = self.as_DataFrame() // other
            return SimDataFrame(data=result, **self.params_)

    def __mod__(self, other):
        # both are SimDataFrame
        if isinstance(other, SimDataFrame):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimDataFrames are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")

            selfI, otherI = self._joined_index(other)
            result = selfI.copy()

            notFount = 0
            for col in otherI.columns:
                if col in selfI.columns:
                    result[col] = selfI[col] % otherI[col]
                else:
                    notFount += 1

            if notFount == len(otherI.columns):
                if selfI.name_separator is not None and otherI.name_separator is not None:
                    selfC, otherC, newNames = selfI._common_rename(otherI)

                    # if no columns has common names
                    if newNames is None:
                        if len(otherC.columns) == 1:  # just in case there is only one column in the second operand
                            return selfC % otherC.to_simseries()
                        else:
                            raise TypeError("Not possible to operate SimDataFrames if there aren't common columns")

                    resultX = selfC % otherC
                    resultX.rename(columns=newNames, inplace=True)
                    if self.auto_append:
                        for col in newNames.values():
                            if self.intersection_character in col:  # intersectionCharacter = '∩'
                                result[col] = resultX[col]
                    else:
                        result = resultX

            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, Series)):
            if type(other) is Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self.operate_per_name and otherI.name in selfI.columns:
                result[otherI.name] = selfI[other.name] % otherI
            else:
                for col in selfI.columns:
                    result[col] = selfI[col] % otherI
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, DataFrame):
            return self.__mod__(SimDataFrame(data=other, **self.params_))

        # let's Pandas deal with other types, maintain units and dtype
        else:
            result = self.as_DataFrame() % other
            return SimDataFrame(data=result, **self.params_)

    def __pow__(self, other):
        # both are SimDataFrame
        if isinstance(other, SimDataFrame):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimDataFrames are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")

            selfI, otherI = self._joined_index(other)
            result = selfI.copy()

            notFount = 0
            for col in otherI.columns:
                if col in selfI.columns:
                    result[col] = selfI[col] ** otherI[col]
                else:
                    notFount += 1

            if notFount == len(otherI.columns):
                if selfI.name_separator is not None and otherI.name_separator is not None:
                    selfC, otherC, newNames = self._common_rename(otherI)

                    # if no columns has common names
                    if newNames is None:
                        if len(otherC.columns) == 1:  # just in case there is only one column in the second operand
                            return selfC ** otherC.to_simseries()
                        else:
                            raise TypeError("Not possible to operate SimDataFrames if there aren't common columns")

                    resultX = selfC ** otherC
                    resultX.rename(columns=newNames, inplace=True)
                    if self.auto_append:
                        for col in newNames.values():
                            if self.intersection_character in col:  # intersectionCharacter = '∩'
                                result[col] = resultX[col]
                    else:
                        result = resultX

            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, Series)):
            if type(other) is Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self.operate_per_name and otherI.name in selfI.columns:
                result[otherI.name] = self[otherI.name] ** otherI
            else:
                for col in selfI.columns:
                    result[col] = selfI[col] ** otherI
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, DataFrame):
            return self.__pow__(SimDataFrame(data=other, **self.params_))

        # if other is integer or float
        elif type(other) in (int, float):
            result = self.as_DataFrame() ** other
            params_ = self.params_
            params_['units'] = {c: _unit_power(self.get_units(c)[c], other) for c in self.columns}
            return SimDataFrame(data=result, **params_)

        # lets Pandas deal with other types, maintain units and dtype
        else:
            result = self.as_DataFrame() ** other
            return SimDataFrame(data=result, **self.params_)

    def set_index(self, key, drop=False, append=False, inplace=False, verify_integrity=False, **kwargs):
        if type(key) is list:
            if False in [k in self.columns for k in key]:
                k = [str(k) for k in key if k not in self.columns]
                raise ValueError("The key '" + ', '.join(k) + "' is not a column name of this SimDataFrame.")
        elif key not in self.columns:
            raise ValueError("The key '" + str(key) + "' is not a column name of this SimDataFrame.")
        if inplace:
            indexUnits = self.get_units(key)
            super().set_index(key, drop=drop, append=append, inplace=inplace, verify_integrity=verify_integrity,
                              **kwargs)
            self.set_index_units(indexUnits)
        else:
            params_ = self.params_
            params_['index'] = None
            params_['indexName'] = None
            params_['indexUnits'] = self.get_units(key)  # [key]
            return SimDataFrame(data=self.DF.set_index(key, drop=drop, append=append, inplace=inplace,
                                                       verify_integrity=verify_integrity, **kwargs), **params_)

    def set_index_units(self, units):
        if type(units) is str and len(units.strip()) > 0:
            self.index_units = units.strip()
        else:
            raise TypeError("`units` must be a string.")

    def transpose(self):
        params_ = self.params_
        params_['transposed'] = not self.transposed
        return SimDataFrame(data=self.DF.T, **params_)

    def to_pandas(self):
        return self.to_dataframe()

    def as_pandas(self):
        return self.as_dataframe()

    def to_series(self):
        return self.to_simseries().to_series()

    def as_series(self):
        return self.as_simseries().as_series()

    def to_simseries(self):
        if len(self.columns) == 1:
            return self[self.columns[0]]
        if len(self) <= 1:
            return SimSeries(data=Series(self.to_pandas().iloc[0].to_list(),
                                         name=self.index[0],
                                         index=self.columns.to_list()),
                             **self.params_)
        raise TypeError('Not possible to converto to SimSeries')

    def as_simseries(self):
        return self.to_simseries()

    def to_dataframe(self):
        return DataFrame(self.copy())

    def as_dataframe(self):
        return DataFrame(self)

    def to_simdataframe(self):
        return self

    def as_simdataframe(self):
        return self

    def convert(self, units):
        """
        returns the dataframe converted to the requested units if possible,
        else returns None
        """
        if self.transposed:
            return self.transpose().convert(units).transpose()
        elif type(units) is str:
            if len(set(self.units.values())) == 1:
                if _convertible(list(set(self.units.values()))[0], units):
                    params_ = self.params_
                    params_['units'] = units
                    params_['columns'] = self.columns
                    params_['index'] = self.index
                    return SimDataFrame(data=_converter(self, list(set(self.units.values()))[0], units), **params_)
                else:
                    return None
            else:
                result = SimDataFrame(index=self.index, columns=self.columns, **self.params_)
                valid = False
                for col in self.columns:
                    if _convertible(self.get_units(col)[col], units):
                        print(col, units, _convertible(self.get_units(col)[col], units))
                        print(self[col].to(units))
                        result[col] = self[col].to(units)
                        valid = True
                    else:
                        result[col] = self[col]
                if valid:
                    return result
        elif type(units) not in (str, dict) and hasattr(units, '__iter__'):
            result = self.copy()
            valid = False
            for col in self.columns:
                for ThisUnits in units:
                    if _convertible(self.get_units(col)[col], ThisUnits):
                        result[col] = self[col].to(ThisUnits)
                        valid = True
                        break
            if valid:
                return result
            else:
                print('no columns could be to converted to the requested units.')
                return self
        elif type(units) is dict:
            units_dict = {i: v for k, v in units.items() for i in self.find_keys(k)}
            result = self.copy()
            for col in self.columns:
                if col in units_dict and _convertible(self.get_units(col)[col], units_dict[col]):
                    result[col] = self[col].to(units_dict[col])
            return result

    def reindex(self, labels=None, index=None, columns=None, axis=None, **kwargs):
        """
        wrapper for pandas.DataFrame.reindex

        labels : array-like, optional
            New labels / index to conform the axis specified by ‘axis’ to.
        index, columns : array-like, optional(should be specified using keywords)
            New labels / index to conform to. Preferably an Index object to avoid duplicating data
        axis : int or str, optional
            Axis to target. Can be either the axis name(‘index’, ‘columns’) or number(0, 1).
        """
        if labels is None and axis is None and index is not None:
            labels = index
            axis = 0
        elif labels is None and axis is None and columns is not None:
            labels = columns
            axis = 1
        elif labels is not None and axis is None and columns is None and index is None:
            if len(labels) == len(self.index):
                axis = 0
            elif len(labels) == len(self.columns):
                axis = 1
            else:
                raise TypeError("labels does not match neither len(index) or len(columns).")
        axis = clean_axis(axis)
        return SimDataFrame(data=self.to_pandas.reindex(labels=labels, axis=axis, **kwargs), **self.params_)


    # not shared methods
    def to_DataFrameMultiIndex(self):
        return self._DataFrame_with_MultiIndex()

    def reset_index(self, level=None, drop=False, inplace=False, col_level=0, col_fill=''):
        if inplace:
            indexUnits, indexName = self.index_units, None if drop else self.index.name
            super().reset_index(level=level, drop=drop, inplace=inplace, col_level=col_level, col_fill='')
            if type(indexUnits) in (str, dict) and indexName is not None:
                self.set_units(indexUnits, indexName)
            self.index.name = None
        else:
            result = SimDataFrame(
                data=self.DF.reset_index(level=level, drop=drop, inplace=inplace, col_level=col_level, col_fill=''),
                **self.params_)
            if not drop and type(self.index_units) in (str, dict) and self.index.name is not None:
                result.set_units(self.index_units, item=self.index.name)
            result.index.name = None
            return result

    def append(self, other, ignore_index=False, verify_integrity=False, sort=False):
        """
        wrapper of Pandas.DataFrame append method considering the units of both Frames

        Append rows of other to the end of caller, returning a new object.

        Parameters
        ----------
        other : SimDataFrame, SimSeries or DataFrame, Series/dict-like object, or list of these
            The data to append.

        ignore_index : bool, default False
            If True, the resulting axis will be labeled 0, 1, …, n - 1.

        verify_integrity: bool, default False
            If True, raise ValueError on creating index with duplicates.

        sort : bool, default False
            Sort columns if the columns of self and other are not aligned.

        Changed in version 1.0.0: Changed to not sort by default.

        Returns
        -------
            SimDataFrame
        """

        if type(other) in (SimDataFrame, SimSeries):
            otherC = other.copy()
            newUnits = self.get_units(self.columns).copy()
            for col, units in self.get_units(self.columns).items():
                if col in otherC.columns:
                    if units != otherC.get_units(col)[col]:
                        if _convertible(otherC.get_units(col)[col], units):
                            otherC[col] = otherC[col].to(units)
                        else:
                            newUnits[col + '_2nd'] = otherC.get_units(col)[col]
                            otherC.rename(columns={col: col + '_2nd'}, inplace=True)
            for col in otherC.columns:
                if col not in newUnits:
                    newUnits[col] = otherC.get_units(col)[col]
            params_ = self.params_
            params_['units'] = newUnits
            data = pd.concat([self.DF, otherC], axis=0)
            return SimDataFrame(data=data, **params_)
        else:
            # append and return SimDataFrame
            data = pd.concat([self.DF, otherC], axis=0)
            return SimDataFrame(data=data, **self.params_)

    def drop(self, labels=None, axis=0, index=None, columns=None, level=None, inplace=False, errors='raise'):
        axis = clean_axis(axis)
        if labels is not None:
            if axis == 1 and type(labels) is not str and hasattr(labels, '__iter__'):
                labels = list(self.find_keys(labels))
            elif axis == 1 and labels not in self.columns:
                if len(self.find_keys(labels)) > 0:
                    labels = list(self.find_keys(labels))
            elif axis == 0 and labels not in self.index:
                filt = [labels in str(ind) for ind in self.index]
                labels = self.index[filt]
        elif columns is not None:
            if type(columns) is not list and columns not in self.columns:
                if len(self.find_keys(columns)) > 0:
                    columns = list(self.find_keys(columns))
        if inplace:
            super().drop(labels=labels, axis=axis, index=index, columns=columns, level=level, inplace=inplace,
                         errors=errors)
        else:
            return SimDataFrame(data=self.as_pandas().drop(labels=labels, axis=axis, index=index, columns=columns,
                                                           level=level, inplace=inplace, errors=errors),
                                **self.params_)

    def dropna(self, axis='index', how='all', thresh=None, subset=None, inplace=False):
        axis = clean_axis(axis)
        if subset is not None:
            if type(subset) is str and subset in self.columns:
                pass
            elif len(self.find_keys(subset)) > 0:
                subset = list(self.find_keys(subset))
        if inplace:
            super().dropna(axis=axis, how=how, thresh=thresh, subset=subset, inplace=inplace)
        else:
            return SimDataFrame(
                data=self.as_pandas().dropna(axis=axis, how=how, thresh=thresh, subset=subset, inplace=inplace),
                **self.params_)

    def drop_duplicates(self, subset=None, keep='first', inplace=False, ignore_index=False):
        if inplace:
            super().drop_duplicates(subset=subset, keep=keep, inplace=inplace, ignore_index=ignore_index)
        else:
            return SimDataFrame(
                data=self.DF.drop_duplicates(subset=subset, keep=keep, inplace=inplace, ignore_index=ignore_index),
                **self.params_)

    def drop_zeros(self, axis='both', inplace=False):
        """
        drop the axis(rows or columns) where all the values are zeross.

        axis parameter can be:
            'columns' or 1 : removes all the columns fill with zeroes
            'index' or 'rows' 0 : removes all the rows fill with zeroes
            'both' or 2 : removes all the rows and columns fill with zeroes
        """
        axis = clean_axis(axis)
        if inplace:
            if axis in ['both', 2]:
                self.replace(0, np.nan, inplace=True)
                self.dropna(axis='columns', how='all', inplace=True)
                self.dropna(axis='index', how='all', inplace=True)
                self.dropna(axis='columns', how='all', inplace=True)
                self.replace(np.nan, 0, inplace=True)
            elif axis in ['rows', 'row', 'index', 0]:
                self.replace(0, np.nan, inplace=True)
                self.dropna(axis='index', how='all', inplace=True)
                self.replace(np.nan, 0, inplace=True)
            elif axis in ['columns', 'column', 'col', 'cols', 1]:
                self.replace(0, np.nan, inplace=True)
                self.dropna(axis='columns', how='all', inplace=True)
                self.replace(np.nan, 0, inplace=True)
            else:
                raise ValueError(" valid `axis´ argument are 'index', 'columns' or 'both'.")
        else:
            if axis in ['both', 2]:
                return self.replace(0, np.nan).dropna(axis='columns', how='all').dropna(axis='index', how='all').dropna(
                    axis='columns', how='all').replace(np.nan, 0)
            elif axis in ['rows', 'row', 'index', 0]:
                return self.replace(0, np.nan).dropna(axis='index', how='all').replace(np.nan, 0)
            elif axis in ['columns', 'column', 'col', 'cols', 1]:
                return self.replace(0, np.nan).dropna(axis='columns', how='all').replace(np.nan, 0)
            else:
                raise ValueError(" valid `axis´ argument are 'index', 'columns' or 'both'.")

    def dropzeros(self, axis='both'):
        """
        alias for .drop_zeros() method
        """
        return self.drop_zeros(axis=axis)





    def fillna(self, value=None, method=None, axis='index', inplace=False,
               limit=None, downcast=None):
        axis = clean_axis(axis)
        if inplace:
            super().fillna(value=value, method=method, axis=axis, inplace=inplace, limit=limit, downcast=downcast)
        else:
            return SimDataFrame(data=self.DF.fillna(value=value, method=method, axis=axis, inplace=inplace, limit=limit,
                                                    downcast=downcast), **self.params_)

    def interpolate(self, method='slinear', axis='index', limit=None, inplace=False,
                    limit_direction=None, limit_area=None, downcast=None, **kwargs):
        axis = clean_axis(axis)
        if inplace:
            super().interpolate(method=method, axis=axis, limit=limit, inplace=inplace, limit_direction=limit_direction,
                                limit_area=limit_area, downcast=downcast, **kwargs)
        else:
            return SimDataFrame(data=self.DF.interpolate(method=method, axis=axis, limit=limit, inplace=inplace,
                                                         limit_direction=limit_direction, limit_area=limit_area,
                                                         downcast=downcast, **kwargs), **self.params_)

    def replace(self, to_replace=None, value=None, inplace=False, limit=None, regex=False, method='pad'):
        if inplace:
            super().replace(to_replace=to_replace, value=value, inplace=inplace, limit=limit, regex=regex,
                            method=method)
        else:
            return SimDataFrame(
                data=self.DF.replace(to_replace=to_replace, value=value, inplace=inplace, limit=limit, regex=regex,
                                     method=method), **self.params_)

    # def groupby(self, by=None, axis=0, level=None, as_index=True, sort=True, group_keys=True, squeeze=False, observed=False, dropna=True):
    #     axis = clean_axis(axis)
    #     selfGrouped = self.DF.groupby(by=by, axis=axis, level=level, as_index=as_index, sort=sort, group_keys=group_keys, squeeze=squeeze, observed=observed, dropna=dropna)
    #     return SimDataFrame(data=selfGrouped, **self.params_ )

    def daily(self, outBy='mean', datetimeIndex=False, by=None,
              complete_index=False, fillna_method=None, **kwargs):
        """
        return a dataframe with a single row per day.
        index must be a date type.

        available gropuing calculations are:
            first : keeps the fisrt row per day
            last : keeps the last row per day
            max : returns the maximum value per year
            min : returns the minimum value per year
            mean or avg : returns the average value per year
            median : returns the median value per month
            std : returns the standard deviation per year
            sum : returns the summation of all the values per year
            count : returns the number of rows per year

        by :  label or list of labels, optional.
            Used to determine the groups for the groupby.
            If by is a function, it’s called on each value of the object’s index.
            If a dict or Series is passed, the Series or dict VALUES will be used
            to determine the groups (the Series’ values are first aligned; see .align() method).
            If an ndarray is passed, the values are used as-is to determine the groups.
            A label or list of labels may be passed to group by the columns in self.
            Notice that a tuple is interpreted as a (single) key.

        complete_index : bool, optional. Default False
            Will reindex the dataframe to new index containing every day between
            the first and the last dates in the input index.
            If set to True, by default will autocomplete the null values using
            linear interpolation considering the length of time intervals from
            the index.
            This behavior can be changed by setting the `fillna´ parameter.

        fillna_method : str or False, optional. Default is False
            If not False, will fill null values using the indicated method.
            Available method to fill NA are the methods from Pandas fillna and
            Pandas interpolate.
            Methods from fillna:
                'pad' / 'ffill': propagate last valid observation forward to
                                 next valid observation.
                'backfill' / 'bfill': use next valid observation to fill gap.
            Methods from interpolate:
                'linear': Ignore the index and treat the values as equally spaced.
                'time': Works on daily and higher resolution data to interpolate given length of interval.
                'index', 'values': use the actual numerical values of the index.
            Methods from scipy.interpolate.interp1d (passed from interpolate):
                'nearest'
                'zero'
                'slinear'
                'quadratic'
                'cubic'
                'spline'
                'barycentric'
                'polynomial'
                These methods use the numerical values of the index.
                Both 'polynomial' and 'spline' require that you also specify
                an order (int), e.g.
                    df.daily(fillna_method='polynomial', order=5).

        """
        if type(self.index) is not pd.DatetimeIndex:
            raise TypeError('index must be of datetime type.')

        if fillna_method in ['polynomial', 'spline']:
            if 'order' not in kwargs:
                raise ValueError(
                    "The '" + fillna_method + "' fillna_method requieres one additional parameter 'order':\n   df.daily(fillna_method='polynomial', order=5)")
            if type(kwargs['order']) is not int:
                raise ValueError(
                    "The 'order' parameter must be an integer:\n   df.daily(fillna_method='polynomial', order=5)")

        if type(outBy) is bool and type(datetimeIndex) is bool:
            outBy, datetimeIndex = 'mean', outBy
        elif type(outBy) is bool and type(datetimeIndex) is not bool:
            outBy, datetimeIndex = datetimeIndex, outBy

        if by is None:
            by = []
        elif type(by) is not str and hasattr(by, '__iter__'):
            newBy = []
            for each in by:
                if each in self.columns:
                    newBy.append(each)
            by = newBy
        elif by in self.columns:
            by = [by]
        else:
            by = [by]  # raise ValueError(str(by) + ' is not a column in this dataframe')
        userby = by if len(by) > 0 else None
        by = [self.index.year, self.index.month, self.index.day] + by

        result = self.DF.groupby(by=by)
        if outBy == 'first':
            result = result.first()
        elif outBy == 'last':
            result = result.last()
        elif outBy == 'max':
            result = result.max()
        elif outBy == 'min':
            result = result.min()
        elif outBy in ['mean', 'avg']:
            result = result.mean()
        elif outBy == 'median':
            result = result.median()
        elif outBy == 'std':
            result = result.std()
        elif outBy == 'sum':
            result = result.sum()
        elif outBy == 'count':
            result = result.count()
        elif outBy in ['int', 'integrate', 'integral', 'cum', 'cumulative', 'representative']:
            result = self.integrate()
            result = result.DF.groupby(by=by)  # [self.index.year, self.index.month, self.index.day]
            index = DataFrame(data=self.index, index=self.index).groupby(
                by=by)  # [self.index.year, self.index.month, self.index.day]
            index = np.append(index.first().to_numpy(), index.last().to_numpy()[-1])
            deltaindex = np.diff(index)
            if isinstance(self.index, DatetimeIndex):
                deltaindex = deltaindex.astype('timedelta64[s]').astype('float64') / 60 / 60 / 24
            values = result.first().append(result.last().iloc[-1])
            deltavalues = np.diff(values.transpose())
            result = DataFrame(data=(deltavalues / deltaindex).transpose(), index=result.first().index,
                               columns=self.columns)
        else:
            raise ValueError(" outBy parameter is not valid.")

        if complete_index:
            if len(by) > 3:  # user criteria to group by
                indexBackup = pd.MultiIndex.from_tuples([(int(i[0]), int(i[1]), int(i[2])) for i in result.index])
                result.index = pd.MultiIndex.from_tuples([tuple(i[3:]) for i in result.index]) if len(by) > 4 else [i[3]
                                                                                                                    for
                                                                                                                    i in
                                                                                                                    result.index]
                result.index.names = by[3:]
                result = result.reset_index()
            else:
                indexBackup = result.index

            result.index = pd.to_datetime(
                [str(YYYY) + '-' + str(MM).zfill(2) + '-' + str(DD).zfill(2) for YYYY, MM, DD in indexBackup])
            result.index.name = 'DATE'
            if len(by) == 4:
                newDF = None
                for group in result[by[3]].unique():
                    groupDF = result[result[by[3]] == group]
                    if len(groupDF) == 0:
                        continue
                    daily_index = pd.date_range(min(groupDF.index), max(groupDF.index), freq='D')
                    groupDF = groupDF.reindex(index=daily_index)

                    if fillna_method is False:
                        pass
                    elif fillna_method is None:
                        groupDF = groupDF.interpolate(method='time').fillna(method='pad')
                    elif fillna_method in ['pad', 'ffill', 'backfill', 'bfill']:
                        groupDF = groupDF.fillna(method=fillna_method)
                    elif fillna_method in ['linear', 'time', 'index', 'values', 'nearest',
                                           'zero', 'slinear', 'quadratic', 'cubic', 'barycentric']:
                        groupDF = groupDF.interpolate(method=fillna_method).fillna(method='pad')
                    elif fillna_method in ['polynomial', 'spline']:
                        groupDF = groupDF.interpolate(method=fillna_method, order=kwargs['order']).fillna(method='pad')
                    if newDF is None:
                        newDF = groupDF.copy()
                    else:
                        newDF = newDF.append(groupDF)

            elif len(by) == 3:
                daily_index = pd.date_range(min(result.index), max(result.index), freq='D')
                result = result.reindex(index=daily_index)

                if fillna_method is False:
                    pass
                elif fillna_method is None:
                    result = result.interpolate(method='time')
                elif fillna_method in ['pad', 'ffill', 'backfill', 'bfill']:
                    result = result.fillna(method=fillna_method)
                elif fillna_method in ['linear', 'time', 'index', 'values', 'nearest',
                                       'zero', 'slinear', 'quadratic', 'cubic', 'barycentric']:
                    result = result.interpolate(method=fillna_method)
                elif fillna_method in ['polynomial', 'spline']:
                    result = result.interpolate(method=fillna_method, order=kwargs['order'])
            else:
                raise ValueError('Not able to reindex grouping by more than one column.')

            by = [result.index.year, result.index.month, result.index.day] + by[3:]
            result = result.groupby(by=by).first()

        output = SimDataFrame(data=result, **self.params_)
        if userby is None:
            output.index = pd.MultiIndex.from_tuples([(int(y), int(m), int(d)) for y, m, d in output.index])
        elif len(userby) == 1:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]), int(i[1]), int(i[2]), i[3]) for i in output.index])
        else:
            output.index = pd.MultiIndex.from_tuples(
                [(int(i[0]), int(i[1]), int(i[2]),) + tuple(i[3:]) for i in output.index])

        if datetimeIndex:
            if userby is None:
                output.index = pd.to_datetime(
                    [str(YYYY) + '-' + str(MM).zfill(2) + '-' + str(DD).zfill(2) for YYYY, MM, DD in output.index])
                output.index.names = ['DATE']
                output.index.name = 'DATE'
                if 'DATE' not in output.get_units():
                    output.set_units('date', 'DATE')
            elif len(userby) == 1:
                output.index = pd.MultiIndex.from_tuples(
                    [(pd.to_datetime(str(i[0]) + '-' + str(i[1]).zfill(2) + '-' + str(i[2]).zfill(2)), i[3]) for i in
                     output.index])
            else:
                output.index = pd.MultiIndex.from_tuples(
                    [(pd.to_datetime(str(i[0]) + '-' + str(i[1]).zfill(2) + '-' + str(i[2]).zfill(2)),) + tuple(i[3:])
                     for i in output.index])
            if userby is not None:
                output.index.names = ['DATE'] + userby
                output.index.name = 'DATE' + '_' + '_'.join(map(str, userby))
        elif userby is None:
            output.index.names = ['YEAR', 'MONTH', 'DAY']
            output.index.name = 'YEAR_MONTH_DAY'
        else:
            output.index.names = ['YEAR', 'MONTH', 'DAY'] + userby
            output.index.name = 'YEAR_MONTH_DAY' + '_' + '_'.join(map(str, userby))

        if not datetimeIndex:
            if 'YEAR' not in output.get_units():
                output.set_units('year', 'YEAR')
            if 'MONTH' not in output.get_units():
                output.set_units('month', 'MONTH')
            if 'DAY' not in output.get_units():
                output.set_units('day', 'DAY')
        return output

    def monthly(self, outBy='mean', datetimeIndex=False, by=None, day='first'):
        """
        return a dataframe with a single row per month.
        index must be a date type.

        available gropuing calculations are:
            first : keeps the fisrt row per month
            last : keeps the last row per month
            max : returns the maximum value per month
            min : returns the minimum value per month
            mean or avg : returns the average value per month
            median : returns the median value per month
            std : returns the standard deviation per month
            sum : returns the summation of all the values per month
            count : returns the number of rows per month

        datetimeIndex : bool
            if True the index will converted to DateTimeIndex with Day=1 for each month
            if False the index will be a MultiIndex (Year,Month)

        by :  label, or list of labels
            Used to determine the groups for the groupby.
            If by is a function, it’s called on each value of the object’s index.
            If a dict or Series is passed, the Series or dict VALUES will be used
            to determine the groups (the Series’ values are first aligned; see .align() method).
            If an ndarray is passed, the values are used as-is to determine the groups.
            A label or list of labels may be passed to group by the columns in self.
            Notice that a tuple is interpreted as a (single) key.

        day : str or int
            The day of the month to write on the datetime index.
            If integer or string number, this number will be used as the day for the index.
            If string 'first' the first day of the month will be used, always 1.
            If string 'last' the last day of each month will be used.
            Ignored if datetimeIndex is False.
        """
        from .._helpers.daterelated import daysInMonth
        if day is None:
            day = '01'
        elif type(day) in [int, float]:
            if day > 31 or day < 1:
                raise ValueError("'day' must be between 1 and 31")
            day = str(int(day))
        elif type(day) is str:
            if day.strip().isdigit():
                day = day.strip()
                if int(day) > 31 or int(day) < 1:
                    raise ValueError("'day' must be between 1 and 31")
            elif day.strip().lower() == 'first':
                day = '01'
            elif day.strip().lower() == 'last':
                day = day.strip().lower()
            else:
                raise ValueError("'day' parameter must be an integer or the string 'first'")
        else:
            raise ValueError("'day' parameter must be an integer or the string 'first'")
        day = '-' + day.zfill(2)

        if type(outBy) is bool:
            outBy, datetimeIndex = 'mean', outBy

        if by is None:
            by = []
        elif type(by) is not str and hasattr(by, '__iter__'):
            newBy = []
            for each in by:
                if each in self.columns:
                    newBy.append(each)
            by = newBy
        elif by in self.columns:
            by = [by]
        else:
            by = [by]
        userby = by if len(by) > 0 else None
        by = [self.index.year, self.index.month] + by

        try:
            result = self.DF.groupby(by=by)  # [self.index.year, self.index.month]
        except:
            raise TypeError('index must be of datetime type.')
        if outBy == 'first':
            result = result.first()
        elif outBy == 'last':
            result = result.last()
        elif outBy == 'max':
            result = result.max()
        elif outBy == 'min':
            result = result.min()
        elif outBy in ['mean', 'avg']:
            result = result.mean()
        elif outBy == 'median':
            result = result.median()
        elif outBy == 'std':
            result = result.std()
        elif outBy == 'sum':
            result = result.sum()
        elif outBy == 'count':
            result = result.count()
        elif outBy in ['int', 'integrate', 'integral', 'cum', 'cumulative', 'representative']:
            result = self.integrate()
            result = result.DF.groupby(by=by)  # [self.index.year, self.index.month]
            index = DataFrame(data=self.index, index=self.index).groupby(by=by)  # [self.index.year, self.index.month]
            index = np.append(index.first().to_numpy(), index.last().to_numpy()[-1])
            deltaindex = np.diff(index)
            if isinstance(self.index, DatetimeIndex):
                deltaindex = deltaindex.astype('timedelta64[s]').astype('float64') / 60 / 60 / 24
            values = result.first().append(result.last().iloc[-1])
            deltavalues = np.diff(values.transpose())
            result = DataFrame(data=(deltavalues / deltaindex).transpose(), index=result.first().index,
                               columns=self.columns)
        else:
            raise ValueError(" outBy parameter is not valid.")

        output = SimDataFrame(data=result, **self.params_)
        if userby is None:
            output.index = pd.MultiIndex.from_tuples([(int(y), int(m)) for y, m in output.index])
        elif len(userby) == 1:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]), int(i[1]), i[2]) for i in output.index])
        else:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]), int(i[1]),) + tuple(i[2:]) for i in output.index])

        if datetimeIndex:
            if userby is None:
                output.index = pd.to_datetime(
                    [str(YYYY) + '-' + str(MM).zfill(2) + (day if day != '-last' else '-' + str(daysInMonth(MM, YYYY)))
                     for YYYY, MM in output.index])
                output.index.names = ['DATE']
                output.index.name = 'DATE'
                if 'DATE' not in output.get_units():
                    output.set_units('date', 'DATE')
            elif len(userby) == 1:
                # output.index = pd.to_datetime( [ str(i[0])+'-'+str(i[1]).zfill(2)+'-01' for i in output.index ] )
                output.index = pd.MultiIndex.from_tuples([(pd.to_datetime(str(i[0]) + '-' + str(i[1]).zfill(2) + (
                    day if day != '-last' else '-' + str(daysInMonth(i[1], i[0])))), i[2],) for i in output.index])
            else:
                output.index = pd.MultiIndex.from_tuples([(pd.to_datetime(str(i[0]) + '-' + str(i[1]).zfill(2) + (
                    day if day != '-last' else '-' + str(daysInMonth(i[1], i[0])))),) + tuple(i[2:]) for i in
                                                          output.index])
            if userby is not None:
                output.index.names = ['DATE'] + userby
                output.index.name = 'DATE' + '_' + '_'.join(map(str, userby))
        elif userby is None:
            output.index.names = ['YEAR', 'MONTH']
            output.index.name = 'YEAR_MONTH'
        else:
            output.index.names = ['YEAR', 'MONTH'] + userby
            output.index.name = 'YEAR_MONTH' + '_' + '_'.join(map(str, userby))
        if not datetimeIndex:
            if 'YEAR' not in output.get_units():
                output.set_units('year', 'YEAR')
            if 'MONTH' not in output.get_units():
                output.set_units('month', 'MONTH')
        return output

    def yearly(self, outBy='mean', datetimeIndex=False, by=None, day='first', month=None):
        """
        return a dataframe with a single row per year.
        index must be a date type.

        available gropuing calculations are:
            first : keeps the fisrt row
            last : keeps the last row
            max : returns the maximum value per year
            min : returns the minimum value per year
            mean or avg : returns the average value per year
            median : returns the median value per month
            std : returns the standard deviation per year
            sum : returns the summation of all the values per year
            count : returns the number of rows per year
            integrate : calculates the numerical integration over the index (a datetime-index) and returns
            representative : calculates the numerical integration of the column over the index (a datetime-index) and then divide it by the elapsed time on between each pair of rows
            cumsum or cumulative : run cumsum over the columns and then return the last value of each year

        datetimeIndex : bool, optional
            if True the index will converted to DateTimeIndex with Day=1 and Month=1 for each year
            if False the index will be a MultiIndex (Year,Month)

        by :  label, or list of labels, optional
            Used to determine the groups for the groupby.
            If by is a function, it’s called on each value of the object’s index.
            If a dict or Series is passed, the Series or dict VALUES will be used
            to determine the groups (the Series’ values are first aligned; see .align() method).
            If an ndarray is passed, the values are used as-is to determine the groups.
            A label or list of labels may be passed to group by the columns in self.
            Notice that a tuple is interpreted as a (single) key.

        day : str or int, optional
            Ignored if datetimeIndex is False.
            The day of the month to write on the datetime index.
            If integer or string number, this number will be used as the day for the index.
            If string 'first' the first day of the 'month' will be used, always 1.
            If string 'last' the last day of 'month' will be used.
            Default is 'first'.

        month : str or int, optional
            Ignored if datetimeIndex is False.
            The month of the year to write on the datetime index.
            If integer or string number, this number will be used as the month for the index.
            If string 'first' the first month of the year will be used, always 1.
            If string 'last' the last month of the year will be used, always 12.
            Default is None.
        """
        from .._helpers.daterelated import daysInMonth
        monthsnames = {'JAN': 1, 'ENE': 1, 'GEN': 1,
                       'FEB': 2,
                       'MAR': 3,
                       'APR': 4, 'ABR': 4,
                       'MAY': 5,
                       'JUN': 6, 'GIU': 6,
                       'JUL': 7, 'JLY': 7, 'LUG': 7,
                       'AUG': 8, 'AGO': 8,
                       'SEP': 9, 'SET': 9,
                       'OCT': 10, 'OTT': 10,
                       'NOV': 11,
                       'DEC': 12, 'DIC': 12, }
        if month is None:
            if str(day).strip().lower() not in ['first', 'last']:
                raise ValueError("please provide 'month' when requesting a particular day")
        elif type(month) in [int, float]:
            if month > 12 or month < 1:
                raise ValueError("'month' must be between 1 and 12")
            month = str(int(month))
        elif type(month) is str:
            if month.strip().isdigit():
                month = month.strip()
                if int(month) > 12 or int(month) < 1:
                    raise ValueError("'month' must be between 1 and 12")
            elif month.lower() == 'first':
                month = '01'
            elif month.lower() == 'last':
                month = '12'
            elif month.strip().upper()[:3] in monthsnames:
                month = str(monthsnames[month.strip().upper()[:3]])
            else:
                raise ValueError(
                    "'month' parameter must be an integer or the string representing a month, or 'first' or 'last'")
        else:
            raise ValueError(
                "'month' parameter must be an integer or the string representing a month, or 'first' or 'last'")
        if day is None:
            day = '01'
        elif type(day) in [int, float]:
            day = str(int(day))
        elif type(day) is str:
            if day.strip().isdigit():
                day = day.strip()
                if int(day) > 31 or int(day) < 1:
                    raise ValueError("'day' must be between 1 and 31")
            elif day.lower() == 'first':
                day = '01'
                if month is None:
                    month = '01'
            elif day.lower() == 'last':
                if month is None:
                    day = '31'
                    month = '12'
                elif int(month) == 2:
                    day = 'last'
                else:
                    day = str(daysInMonth(int(month)))
            else:
                raise ValueError("'day' parameter must be an integer or the string 'first'")
        else:
            raise ValueError("'day' parameter must be an integer or the string 'first'")

        month = '-' + month.zfill(2)
        day = '-' + day.zfill(2)

        if type(outBy) is bool:
            outBy, datetimeIndex = 'mean', outBy

        if by is None:
            by = []
        elif type(by) is not str and hasattr(by, '__iter__'):
            newBy = []
            for each in by:
                if each in self.columns:
                    newBy.append(each)
            by = newBy
        elif by in self.columns:
            by = [by]
        else:
            by = [by]
        userby = by if len(by) > 0 else None
        by = [self.index.year] + by
        if len(by) == 1:
            by = by[0]

        try:
            result = self.DF.groupby(by=by)  # self.index.year
        except:
            raise TypeError('index must be of datetime type.')
        if outBy == 'first':
            result = result.first()
        elif outBy == 'last':
            result = result.last()
        elif outBy == 'max':
            result = result.max()
        elif outBy == 'min':
            result = result.min()
        elif outBy in ['mean', 'avg']:
            result = result.mean()
        elif outBy == 'median':
            result = result.median()
        elif outBy == 'std':
            result = result.std()
        elif outBy == 'sum':
            result = result.sum()
        elif outBy == 'count':
            result = result.count()
        elif outBy in ['int', 'integrate', 'integral', 'cum', 'cumulative', 'representative', 'rep', 'repr']:
            result = self.integrate()
            result = result.DF.groupby(by=by)  # self.index.year
            index = DataFrame(data=self.index, index=self.index).groupby(by=by)  # self.index.year
            index = np.append(index.first().to_numpy(), index.last().to_numpy()[-1])
            deltaindex = np.diff(index)
            if isinstance(self.index, DatetimeIndex):
                deltaindex = deltaindex.astype('timedelta64[s]').astype('float64') / 60 / 60 / 24
            values = result.first().append(result.last().iloc[-1])
            deltavalues = np.diff(values.transpose())
            result = DataFrame(data=(deltavalues / deltaindex).transpose(), index=result.first().index,
                               columns=self.columns)
        else:
            raise ValueError(" outBy parameter is not valid.")

        output = SimDataFrame(data=result, **self.params_)
        if userby is None:
            output.index = [int(y) for y in output.index]
        elif len(userby) == 1:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]), i[1]) for i in output.index])
        else:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]),) + tuple(i[1:]) for i in output.index])

        if datetimeIndex:
            if userby is None:
                output.index = pd.to_datetime(
                    [str(YYYY) + month + (day if day != '-last' else '-' + str(daysInMonth(month[1:], YYYY))) for YYYY
                     in output.index])
                output.index.names = ['DATE']
                output.index.name = 'DATE'
                if 'DATE' not in output.get_units():
                    output.set_units('date', 'DATE')
            elif len(userby) == 1:
                output.index = pd.MultiIndex.from_tuples([(pd.to_datetime(
                    str(i[0]) + month + (day if day != '-last' else '-' + str(daysInMonth(month[1:], i[0])))), i[1],)
                    for i in output.index])
            else:
                output.index = pd.MultiIndex.from_tuples([(pd.to_datetime(
                    str(i[0]) + month + (day if day != '-last' else '-' + str(daysInMonth(month[1:], i[0])))),) + tuple(
                    i[1:]) for i in output.index])
            if userby is not None:
                output.index.names = ['DATE'] + userby
                output.index.name = 'DATE' + '_' + '_'.join(map(str, userby))
        elif userby is None:
            output.index.names = ['YEAR']
            output.index.name = 'YEAR'
        else:
            output.index.names = ['YEAR', ] + userby
            output.index.name = 'YEAR' + '_' + '_'.join(map(str, userby))
        if not datetimeIndex:
            output.set_units('year', 'YEAR')
            output.index_units = 'year'
        return output

    def aggregate(self, func=None, axis=0, *args, **kwargs):
        axis = clean_axis(axis)
        return SimDataFrame(data=self.DF.aggregate(func=func, axis=axis, *args, **kwargs), **self.params_)

   def rename(self, mapper=None, index=None, columns=None, axis=None, copy=True,
               inplace=False, level=None, errors='ignore'):
        """
        wrapper of rename function from Pandas.

        Alter axes labels.

        Function / dict values must be unique(1-to-1).
        Labels not contained in a dict / Series will be left as-is.
        Extra labels listed don’t throw an error.

        Parameters:
            mapper: dict-like or function
                Dict-like or functions transformations to apply to that axis’ values.
                Use either mapper and axis to specify the axis to target with mapper,
                or index and columns.

            index: dict-like or function
                Alternative to specifying axis(mapper, axis=0 is equivalent to index=mapper).

            columns: dict-like or function
                Alternative to specifying axis(mapper, axis=1 is equivalent to columns=mapper).

            axis: {0 or ‘index’, 1 or ‘columns’}, default 0
                Axis to target with mapper. Can be either the axis name(‘index’, ‘columns’) or number(0, 1). The default is ‘index’.

            copy: bool, default True
                Also copy underlying data.

            inplace:bool, default False
                Whether to apply the chanes directly in the dataframe.
                Always return a new DataFrame.
                If True then value of copy is ignored.

            level: int or level name, default None
                In case of a MultiIndex, only rename labels in the specified level.

            errors: {‘ignore’, ‘raise’}, default ‘ignore’
                If ‘raise’, raise a KeyError when a dict-like mapper, index, or columns
                contains labels that are not present in the Index being transformed.
                If ‘ignore’, existing keys will be renamed and extra keys will be ignored.
        """
        cBefore = list(self.columns)
        if inplace:
            super().rename(mapper=mapper, index=index, columns=columns, axis=axis, copy=copy, inplace=inplace,
                           level=level, errors=errors)
            cAfter = list(self.columns)
        else:
            catch = super().rename(mapper=mapper, index=index, columns=columns, axis=axis, copy=copy, inplace=inplace,
                                   level=level, errors=errors)
            cAfter = list(catch.columns)
        newUnits = {}
        for i in range(len(cBefore)):
            if cBefore[i] in self.units:
                newUnits[cAfter[i]] = self.units[cBefore[i]]
        if inplace:
            self.units = newUnits
            self.spdLocator = _SimLocIndexer("loc", self)
            return None
        else:
            catch.units = newUnits
            catch.spdLocator = _SimLocIndexer("loc", catch)
            return catch

    def renameItem(self, mapper=None, index=None, columns=None, axis=None,
                    copy=True, inplace=False, level=None, errors='ignore'):
        """
        alias for renameItem method.

        Like the regular rename method but renameItem change all the columns or indexes where the item appears.
        The item is the right part of the column or index name:
                main_part:item_part

        Parameters
        ----------
        mapper : dict, optional
            Dict-like transformations to apply to that axis’ values.
            Use either mapper and axis to specify the axis to target with mapper, or index and columns.
        index : TYPE, optional
            Alternative to specifying axis (mapper, axis=0)
        columns : dict, optional
            Alternative to specifying axis (mapper, axis=1)
        axis : {0 or ‘index’, 1 or ‘columns’}, default 1
            Axis to target with mapper.
            Can be either the axis name (‘index’, ‘columns’) or number (0, 1).
            The default is ‘index’.
        copy : bool, default True
            Also copy underlying data.
        inplace : bool, default False
            Whether to return a new DataFrame. If True then value of copy is ignored.
        level : int or level name, default None
            In case of a MultiIndex, only rename labels in the specified level.
            *** NOT YET IMPLEMENTED ***
        errors : TYPE, optional
            If ‘raise’, raise a KeyError when a dict-like mapper, index, or columns
            contains labels that are not present in the Index being transformed.
            If ‘ignore’, existing keys will be renamed and extra keys will be ignored.

        Returns
        -------
        DataFrame or None
            DataFrame with the renamed axis labels or None if inplace=True.

        """
        return self.rename_item(self, mapper=mapper, index=index, columns=columns,
                               axis=axis, copy=copy, inplace=inplace, level=level,
                               errors=errors)

    def rename_item(self, mapper=None, index=None, columns=None, axis=None,
                   copy=True, inplace=False, level=None, errors='ignore'):
        """
        Like the regular rename method but renameItem change all the columns or indexes where the item appears.
        The item is the right part of the column or index name:
                main_part:item_part

        Parameters
        ----------
        mapper : dict, optional
            Dict-like transformations to apply to that axis’ values.
            Use either mapper and axis to specify the axis to target with mapper, or index and columns.
        index : TYPE, optional
            Alternative to specifying axis (mapper, axis=0)
        columns : dict, optional
            Alternative to specifying axis (mapper, axis=1)
        axis : {0 or ‘index’, 1 or ‘columns’}, default 1
            Axis to target with mapper.
            Can be either the axis name (‘index’, ‘columns’) or number (0, 1).
            The default is ‘index’.
        copy : bool, default True
            Also copy underlying data.
        inplace : bool, default False
            Whether to return a new DataFrame. If True then value of copy is ignored.
        level : int or level name, default None
            In case of a MultiIndex, only rename labels in the specified level.
            *** NOT YET IMPLEMENTED ***
        errors : TYPE, optional
            If ‘raise’, raise a KeyError when a dict-like mapper, index, or columns
            contains labels that are not present in the Index being transformed.
            If ‘ignore’, existing keys will be renamed and extra keys will be ignored.

        Returns
        -------
        DataFrame or None
            DataFrame with the renamed axis labels or None if inplace=True.

        """

        def _item_columns(sdf, itemMapper, axis):
            itemsDict = {}
            for item in itemMapper:
                pattern = '*' + sdf.name_separator + str(item)
                keys = tuple(fnmatch.filter(map(str, tuple(sdf.columns if axis == 1 else sdf.index)), pattern))
                kMapper = {k: k.replace(sdf.name_separator + str(item), sdf.name_separator + str(itemMapper[item])) for
                           k in keys}
                itemsDict.update(kMapper)
            return itemsDict

        if mapper is not None:
            if axis is None:
                axis = 1
            elif type(axis) is str:
                axis = {'index': 0, 'columns': 1}
            mapper = _item_columns(self, mapper, axis)
        elif index is not None:
            index = _item_columns(self, index, 0)
        elif columns is not None:
            columns = _item_columns(self, columns, 1)
        return self.rename(mapper=mapper, index=index, columns=columns, axis=axis, copy=copy, inplace=inplace,
                           level=level, errors=errors)






    def _common_rename(self, SimDataFrame1, SimDataFrame2=None, LR=None):
        cha = self.intersection_character

        if LR is not None:
            LR = LR.upper()
            if LR not in 'LR':
                LR = None

        if SimDataFrame2 is None:
            SDF1, SDF2 = self, SimDataFrame1
        else:
            SDF1, SDF2 = SimDataFrame1, SimDataFrame2

        if type(SDF1) is not SimDataFrame:
            raise TypeError("both dataframes to be compared must be SimDataFrames.")
        if type(SDF2) is not SimDataFrame:
            raise TypeError("both dataframes to be compared must be SimDataFrames.")

        if SDF1.name_separator is None or SDF2.name_separator is None:
            raise ValueError("the 'nameSeparator' must not be empty in both SimDataFrames.")

        if LR == 'L' or (LR is None and len(SDF1.left) == 1 and len(SDF2.left) == 1):
            SDF2C = SDF2.copy()
            SDF2C.renameRight(inplace=True)
            SDF1C = SDF1.copy()
            SDF1C.renameRight(inplace=True)
            commonNames = {}
            for c in SDF1C.columns:
                if c in SDF2C.columns:
                    commonNames[c] = SDF1.left[0] + cha + SDF2.left[0] + SDF1.name_separator + c
                else:
                    commonNames[c] = SDF1.left[0] + SDF1.name_separator + c
            for c in SDF2C.columns:
                if c not in SDF1C.columns:
                    commonNames[c] = SDF2.left[0] + SDF1.name_separator + c
            if LR is None and len(commonNames) > 1:
                alternative = self._common_rename(SDF1, SDF2, LR='R')
                if len(alternative[2]) < len(commonNames):
                    return alternative

        elif LR == 'R' or (LR is None and len(SDF1.right) == 1 and len(SDF2.right) == 1):
            SDF2C = SDF2.copy()
            SDF2C.rename_left(inplace=True)
            SDF1C = SDF1.copy()
            SDF1C.renameLeft(inplace=True)
            commonNames = {}
            for c in SDF1C.columns:
                if c in SDF2C.columns:
                    commonNames[c] = c + SDF1.name_separator + SDF1.right[0] + cha + SDF2.right[0]
                else:
                    commonNames[c] = c + SDF1.name_separator + SDF1.right[0]
            for c in SDF2C.columns:
                if c not in SDF1C.columns:
                    commonNames[c] = c + SDF1.name_separator + SDF2.right[0]
            if LR is None and len(commonNames) > 1:
                alternative = self._common_rename(SDF1, SDF2, LR='L')
                if len(alternative[2]) < len(commonNames):
                    return alternative

        else:
            SDF1C, SDF2C = SDF1, SDF2.copy()
            commonNames = None

        return SDF1C, SDF2C, commonNames

    def _joined_index(self, other, *, drop_duplicates=False, keep='first'):
        from .._common.merger import merge_Index
        return merge_Index(self, other, how='outer', drop_duplicates=drop_duplicates, keep=keep)

    def _common_index(self, other, *, drop_duplicates=True, keep='first'):
        from .._common.merger import merge_Index
        return merge_Index(self, other, how='inner', drop_duplicates=drop_duplicates, keep=keep)

    def _merge_index(self, other, how='outer', *, drop_duplicates=True, keep='first'):
        from .._common.merger import merge_Index
        return merge_Index(self, other, how=how, drop_duplicates=drop_duplicates, keep=keep)

    def merge(self, right, how='inner', on=None, left_on=None, right_on=None, left_index=None, right_index=None,
              sort=False, suffixes=('_x', '_y'), copy=True, indicator=False, validate=None):
        from .._common.merger import merge as _merge
        if on is None and left_on is None and right_on is None and right_index is None and left_index is None:
            left_index, right_index = True, True
        return _merge(self, right, how='inner', on=on, left_on=left_on, right_on=right_on, left_index=left_index,
                      right_index=right_index, sort=sort, suffixes=suffixes, copy=copy, indicator=indicator,
                      validate=validate)

    def avg(self, axis=0, **kwargs):
        return self.mean(axis=axis, **kwargs)

    def avg0(self, axis=0, **kwargs):
        return self.mean0(axis=axis, **kwargs)

    def average(self, axis=0, **kwargs):
        return self.mean(axis=axis, **kwargs)

    def average0(self, axis=0, **kwargs):
        return self.mean0(axis=axis, **kwargs)

    def count(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.count(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            newName = '.count'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = self.DF.count(axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_
            params_['units'] = 'dimensionless'
            return SimDataFrame(data=data, **params_)

    def count0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).count(axis=axis, **kwargs)

    def max(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.max(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            newName = '.max'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = self.DF.max(axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def max0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).max(axis=axis, **kwargs)

    def mean(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.mean(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            newName = '.mean'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = self.DF.mean(axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def mean0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).mean(axis=axis, **kwargs)

    def median(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.median(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            newName = '.median'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = self.DF.median(axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def median0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).median(axis=axis, **kwargs)

    def min(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.min(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            new_name = '.min'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                new_name = list(set(self.columns))[0] + new_name
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                new_name = list(set(self.rename_right(inplace=False).columns))[0] + new_name
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                new_name = list(set(self.rename_left(inplace=False).columns))[0] + new_name
            data = self.DF.min(axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def min0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).min(axis=axis, **kwargs)

    def mode(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.mode(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            newName = '.mode'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = self.DF.mode(axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def mode0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).mode(axis=axis, **kwargs)

    def prod(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.prod(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            newName = '.prod'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = self.DF.prod(axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def prod0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).prod(axis=axis, **kwargs)

    def quantile(self, q=0.5, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.quantile(q=q, axis=axis, **kwargs), **self.params_)
        if axis == 1 and hasattr(q, '__iter__'):  # q is a list
            namedecimals = 1
            if 'namedecimals' in kwargs:
                if type(kwargs['namedecimals']) is int:
                    namedecimals = kwargs['namedecimals']
                del kwargs['namedecimals']
            else:
                namedecimals = len(str(q)) - 2
            newNameLambda = lambda q: '.Q' + str(round(q * 100, namedecimals))
            newName = map(newNameLambda, q)
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = [list(set(self.columns))[0] + nm for nm in newName]
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = [list(set(self.rename_right(inplace=False).columns))[0] + nm for nm in newName]
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = [list(set(self.rename_left(inplace=False).columns))[0] + nm for nm in newName]
            data = self.DF.quantile(q=q, axis=axis, **kwargs).transpose()
            data.columns = newName
            # data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)
        elif axis == 1:
            namedecimals = 1
            if 'namedecimals' in kwargs:
                if type(kwargs['namedecimals']) is int:
                    namedecimals = kwargs['namedecimals']
                del kwargs['namedecimals']
            else:
                namedecimals = len(str(q)) - 2
            newName = '.Q' + str(round(q * 100, namedecimals))
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = self.DF.quantile(q=q, axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def quantile0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).quantile(axis=axis, **kwargs)

    def rms(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            result = SimDataFrame(data=(self.DF ** 2), **self.params_).mean(axis=axis, **kwargs)
            return SimDataFrame(data=result.DF ** 0.5, **result._SimParameters)
        if axis == 1:
            newName = '.rms'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = SimDataFrame(data=(self.DF ** 2), **self.params_).mean(axis=axis, **kwargs)
            data.rename(columns={data.columns[0]: newName}, inplace=True)
            data.name = newName
            params_ = data._SimParameters
            params_['name'] = newName
            params_['columns'] = [newName]
            return SimDataFrame(data=data, **params_)

        return (SimDataFrame(data=(self.DF ** 2), **self.params_).mean(axis=axis, **kwargs)) ** 0.5

    def rms0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).rms(axis=axis, **kwargs)

    def std(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.std(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            newName = '.std'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = self.DF.std(axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def std0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).std(axis=axis, **kwargs)

    def sum(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            if len(set(self.get_units(self.columns).values())) == 1:
                params_ = self.params_
                params_['units'] = list(set(self.get_units(self.columns).values()))[0]
                return SimDataFrame(data=self.DF.sum(axis=axis, **kwargs).rename('.sum'), **params_)
            else:
                params_ = self.params_
                if type(params_['units']) is dict:
                    params_['units']['.sum'] = '*units per row'
                return SimDataFrame(data=self.DF.sum(axis=axis, **kwargs).rename('.sum'), **params_)
        if axis == 1:
            newName = '.sum'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            else:
                commonL = commonprefix(list(self.rename_left(inplace=False).columns))
                commonR = commonprefix(list(self.rename_right(inplace=False).columns))
                if len(commonL) >= len(commonR):
                    newName = commonL + newName
                else:
                    newName = commonR + newName
            if len(set(self.get_units(self.columns).values())) == 1:
                data = self.DF.sum(axis=axis, **kwargs)
            else:
                result = self[self.columns[0]]
                units = self.units[self.columns[0]]
                for col in range(1, len(self.columns)):
                    result = result + self[self.columns[col]]
                data = result
            data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)
        if axis == 2:
            return self.sum(axis=1).sum(axis=0)

    def sum0(self, axis=0, **kwargs):
        return self.sum(axis=axis, **kwargs)

    def var(self, axis=0, **kwargs):
        axis = clean_axis(axis)
        if axis == 0:
            return SimDataFrame(data=self.DF.var(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            newName = '.var'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                newName = list(set(self.columns))[0] + newName
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                newName = list(set(self.rename_right(inplace=False).columns))[0] + newName
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                newName = list(set(self.rename_left(inplace=False).columns))[0] + newName
            data = self.DF.var(axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def var0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).var(axis=axis, **kwargs)

    def round(self, decimals=0, **kwargs):
        return SimDataFrame(data=self.DF.round(decimals=decimals, **kwargs), **self.params_)

    def diff(self, periods=1, axis=0, forward=False):
        axis = clean_axis(axis)
        if type(periods) is bool:
            periods, forward = 1, periods
        if axis == 0:
            if forward:
                return SimDataFrame(data=-1 * self.DF.diff(periods=-1 * periods, axis=axis), **self.params_)
            else:
                return SimDataFrame(data=self.DF.diff(periods=periods, axis=axis), **self.params_)
        if axis == 1:
            # newName = '.diff'
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            # if len(set(self.columns ) ) == 1:
            #     newName = list(set(self.columns ))[0]+newName
            # elif len(set(self.renameRight(inplace=False).columns ) ) == 1:
            #     newName = list(set(self.renameRight(inplace=False).columns ))[0]+newName
            # elif len(set(self.renameLeft(inplace=False).columns ) ) == 1:
            #     newName = list(set(self.renameLeft(inplace=False).columns ))[0]+newName
            # else:
            #     newName = [c+'.diff' for c in self.columns]
            if forward:
                data = -1 * self.DF.diff(periods=-1 * periods, axis=axis)
            else:
                data = self.DF.diff(periods=periods, axis=axis)
            # data.columns=newName
            # data.name = newName
            params_ = self.params_
            params_['units'] = units
            return SimDataFrame(data=data, **params_)

    def znorm(self):
        """
        return standard normalization

        """
        return _znorm(self)

    def znorm0(self):
        """
        return standard normalization ignoring zeroes

        """
        return _znorm(self.replace(0, np.nan))

    def minmaxnorm(self):
        """
        return min-max normalization
        """
        return _minmaxnorm(self)

    def minmaxnorm0(self):
        """
        return min-max normalization
        """
        return _minmaxnorm(self.replace(0, np.nan))

    def copy(self, **kwargs):
        return SimDataFrame(data=self.to_DataFrame().copy(True), **self.params_)

    def _get_by_filter(self, key):
        """
        ** helper function to __getitem__ method **

        try to get a filtered DataFrame or Series(.filter[key] )
        """
        if len(key) != len(self.DF):
            raise ValueError('Filter wrong length ' + str(len(key)) + ' instead of ' + str(len(self.DF)))
        if not isinstance(key, (Series, SimSeries)) and type(key) is not np.ndarray:
            raise TypeError("Filter must be a Series or Array")
        else:
            if str(key.dtype) != 'bool':
                raise TypeError("Filter dtype must be 'bool'")

        return self.DF.loc[key]

    def _get_by_criteria(self, key):
        """
        ** helper function to __getitem__ method **

        try to get a filtered DataFrame or Series(.filter[key] )
        """
        return self.filter(key)

    def _get_by_column(self, key):
        """
        ** helper function to __getitem__ method **

        try to get a column by column name(.__getitem__[key] )
        """
        return self.DF.__getitem__(key)

    def _get_by_index(self, key):
        """
        ** helper function to __getitem__ method **

        try to get a row by index value(.loc[key] ) or by position(.iloc[key] )
        """
        # if index is date try to undestand key as a date
        if type(self.index) is DatetimeIndex and type(key) not in [DatetimeIndex, Timestamp, int, float, np.ndarray]:
            try:
                return self._get_by_dateIndex(key)
            except:
                pass

        # try to find key by index value using .loc
        try:
            return self.DF.loc[key]
        except:
            # try to find key by index position using .loc
            try:
                return self.DF.iloc[key]
            except:
                try:
                    return self.DF.loc[:, key]
                except:
                    try:
                        return self.DF.iloc[:, key]
                    except:
                        raise ValueError(' ' + str(key) + ' is not a valid index value or position.')

    def _get_by_dateIndex(self, key):
        """
        ** helper function to __getitem__ method **

        try to get a row by index value(.loc[key] ) or by position(.iloc[key] )
        """
        if type(self.index) is DatetimeIndex:
            if type(key) in [DatetimeIndex, Timestamp, np.datetime64, np.ndarray, dt.date]:
                try:
                    return self.DF.loc[key]
                except:
                    pass

            if type(key) is not str and (is_date(key) or type(key) not in [DatetimeIndex, Timestamp]):
                try:
                    return self.DF.loc[key]
                except:
                    try:
                        return self.DF.iloc[key]
                    except:
                        pass

            if type(key) is str and len(
                    multisplit(key, ('==', '!=', '>=', '<=', '<>', '><', '>', '<', '=', ' '))) == 1 and is_date(key):
                try:
                    key = strDate(key)
                except:
                    try:
                        key = strDate(key, formatIN=is_date(key, returnFormat=True), formatOUT='DD-MMM-YYYY')
                    except:
                        raise Warning('\n Not able to undertand the key as a date.\n')
                try:
                    return self.DF.loc[key]
                except:
                    pass

            if type(key) is str:
                keyParts = multisplit(key, ('==', '!=', '>=', '<=', '<>', '><', '>', '<', '=', ' '))
                keySearch = ''
                datesDict = {}
                temporal = SimDataFrame(index=self.index, **self.params_)
                datesN = len(self)
                for P in range(len(keyParts)):
                    if is_date(keyParts[P]):
                        keySearch += ' D' + str(P)
                        datesDict['D' + str(P)] = keyParts[P]
                        temporal.__setitem__('D' + str(P), DatetimeIndex([Timestamp(
                            strDate(keyParts[P], formatIN=is_date(keyParts[P], returnFormat=True),
                                    formatOUT='YYYY-MMM-DD'))] * datesN).to_numpy())
                    else:
                        keySearch += ' ' + keyParts[P]
                datesFilter = temporal.filter(keySearch, returnFilter=True)
                return self.DF.iloc[datesFilter.array]

            else:
                return self.DF.iloc[key]

    def _columns_name_and_units_to_MultiIndex(self):
        out = []  # out = {}
        units = self.get_units()
        if units is None or len(units) == 0:
            return self.columns  # there are not units, return column names as they are
        if len(self.columns) == 0:
            return self.columns  # is an empty DataFrame
        for col in self.columns:
            if col in units:
                out.append((col, units[col]))  # out[col] = units[col]
            else:
                out.append((col, None))  # out[col] = None
        out = pd.MultiIndex.from_tuples(out)  # out = pd.MultiIndex.from_tuples(out.items())
        return out

    def _DataFrame_with_MultiIndex(self):
        if self.transposed:
            result = self.DF.copy()
            units = []
            for i in result.index:
                if i in self.units:
                    units.append(self.units[i])
                else:
                    units.append('unitless')
            joker = ('*', '@', '$', '-', '%', '_', ' ')
            for unitsCol in [s + 'units' for s in joker] + [s + 'units' + s for s in joker] + [s + 'UNITS' for s in
                                                                                               joker] + [s + 'UNITS' + s
                                                                                                         for s in
                                                                                                         joker]:
                if unitsCol not in result.columns:
                    result[unitsCol] = units
                    break
                elif list(result[unitsCol]) == units:
                    break
            result.index.name = None
            return result
        else:
            result = self.to_dataframe()
            new_name = self._columns_name_and_units_to_MultiIndex()
            result.columns = new_name
            return result

    def _repr_html_(self):
        """
        Return a html representation for a particular DataFrame, with Units.
        """
        return self._DataFrame_with_MultiIndex()._repr_html_()

    @property
    def wells(self):
        if self.name_separator in [None, '', False]:
            return []
        objs = []
        for each in list(self.columns):
            if type(each) is str and self.name_separator in each and each[0] == 'W':
                objs += [each.split(self.name_separator)[-1]]
        return tuple(set(objs))

    @property
    def groups(self):
        if self.name_separator in [None, '', False]:
            return []
        objs = []
        for each in list(self.columns):
            if type(each) is str and self.name_separator in each and each[0] == 'G':
                objs += [each.split(self.name_separator)[-1]]
        return tuple(set(objs))

    # @property
    # def items(self):
    #     return self.left



    @property
    def regions(self):
        if self.name_separator in [None, '', False]:
            return []
        objs = []
        for each in list(self.columns):
            if type(each) is str and self.name_separator in each and each[0] == 'R':
                objs += [each.split(self.name_separator)[-1]]
        return tuple(set(objs))



    @property
    def attributes(self):
        if self.name_separator in [None, '', False]:
            return {col: [] for col in self.columns}
        atts = {}
        for each in list(self.columns):
            if type(each) is str and self.name_separator in each:
                if type(each) is str and each.split(self.name_separator)[0] in atts:
                    atts[each.split(self.name_separator)[0]] += [each.split(self.name_separator)[-1]]
                else:
                    atts[each.split(self.name_separator)[0]] = [each.split(self.name_separator)[-1]]
            else:
                if each not in atts:
                    atts[each] = []
        for att in atts:
            atts[att] = list(set(atts[att]))
        return atts

    @property
    def properties(self):
        if len(self.attributes.keys()) > 0:
            return tuple(self.attributes.keys())
        else:
            return tuple()



    def get_keys(self, pattern=None):
        """
        Will return a tuple of all the key names in case.

        If the pattern variable is different from None only keys
        matching the pattern will be returned; the matching is based
        on fnmatch():
            Pattern     Meaning
            *           matches everything
            ?           matches any single character
            [seq]       matches any character in seq
            [!seq]      matches any character not in seq

        """
        if pattern is not None and type(pattern) is not str and type(pattern) not in [int, float]:
            raise TypeError(
                'pattern argument must be a string.\nreceived ' + str(type(pattern)) + ' with value ' + str(pattern))
        if type(pattern) in [int, float]:
            if pattern in self.columns:
                return self[pattern]
            else:
                raise KeyError("The requested key: " + str(pattern) + "is not present in this SimDataFrame.")
        if pattern is None:
            return list(self.columns)
        else:
            return list(fnmatch.filter(map(str, tuple(self.columns)), pattern))

    def find_keys(self, criteria=None):
        """
        Will return a tuple of all the key names in case.

        If criteria is provided, only keys matching the pattern will be returned.
        Accepted criterias can be:
            > well, group or region names.
              All the keys related to that name will be returned
            > attributes.
              All the keys related to that attribute will be returned
            > a fmatch compatible pattern:
                Pattern     Meaning
                *           matches everything
                ?           matches any single character
                [seq]       matches any character in seq
                [!seq]      matches any character not in seq

            additionally, ! can be prefixed to a key to return other keys but
            that particular one:
                '!KEY'     will return every key but not 'KEY'.
                           It will only work with a single key.
        """
        if criteria is None:
            return tuple(self.columns)
        keys = []
        if type(criteria) is str and len(criteria.strip()) > 0:
            if criteria.strip()[0] == '!' and len(criteria.strip()) > 1:
                keys = list(self.columns)
                keys.remove(criteria[1:])
                return tuple(keys)
            criteria = [criteria]
        elif type(criteria) is not list:
            try:
                criteria = list(criteria)
            except:
                pass
        for key in criteria:
            if type(key) is str and key not in self.columns:
                if key in self.wells or key in self.groups or key in self.regions:
                    keys += list(self.get_keys('*' + self.name_separator + key))
                elif key in self.attributes:
                    keys += list(self.keygen(key, self.attributes[key]))
                else:
                    keys += list(self.get_keys(key))
            elif type(key) is str and key in self.columns:
                keys += [key]
            else:
                keys += list(self.find_keys(key))
        return tuple(keys)

    def get_units(self, items=None):
        """
        returns a dictionary with the units for the selected 'items' (or columns)
        or for all the columns in this SimDataFrame

        Parameters
        ----------
        items : str of iterable (i.e. list), optional
            The columns or items to return their units.
            The default is None, and then al the entire units dictionary will be returned.

        Returns
        -------
        dict
            A dictionary {column:units}
        """
        if self.units is None:
            self.units = {}

        if items is None:
            return self.units.copy()
        u_dict = {}
        if not isinstance(items, (list, tuple, dict, set, Index)):
            items = [items]
        for each in items:
            if each in self.units:
                u_dict[each] = self.units[each]
            elif each in self.wells or each in self.groups or each in self.regions:
                for Key in self.get_keys('*' + self.name_separator + each):
                    u_dict[each] = self.units[each]
            elif each in self.attributes:
                for att in self.keygen(each, self.attributes[each]):
                    if att in self.units:
                        u_dict[att] = self.units[att]
                    else:
                        u_dict[att] = 'unitless'
            elif len(self.get_keys(each)) > 0:
                for key in self.get_keys(each):
                    u_dict[key] = self.units[key] if key in self.units else ''
        return u_dict

    def get_units_string(self, items=None):
        if len(self.get_units(items)) == 1:
            return list(self.get_units(items).values())[0]
        elif len(set(self.get_units(items).values())) == 1:
            return list(set(self.get_units(items).values()))[0]

    def set_units(self, units, item=None):
        """
        This method can be used to define the units related to the values of a column (item).

        Parameters
        ----------
        units : str or list of str
            the units to be assigned
        item : str, optional
            The name of the column to apply the units.
            The default is None. In this case the unit

        Raises
        ------
        ValueError
            when units can't be applied.
        TypeError
            when units or item has the wrong format.

        Returns
        -------
        None.

        """
        if item is not None and item not in self.columns and item != self.index.name and item not in self.index.names:
            if units in self.columns or units == self.index.name or units in self.index.names:
                return self.set_units(item, units)
            raise ValueError("the required item '" + str(item) + "' is not in this SimDataFrame.")
        if type(units) not in (str, dict) and hasattr(units, '__iter__'):
            if item is not None and type(item) is not str and hasattr(item, '__iter__'):
                if len(item) == len(units):
                    return self.set_units(dict(zip(item, units)))
                else:
                    raise ValueError("both units and item must have the same length.")
            elif item is None:
                if len(units) == len(self.columns):
                    return self.set_units(dict(zip(list(self.columns), units)))
                else:
                    raise ValueError(
                        "units list must be the same length of columns in the SimDataFrame or must be followed by a list of items.")
            else:
                raise TypeError("if units is a list, items must be a list of the same length.")

        if type(units) is dict:
            if len([k for k in units.keys() if k in (self.index if self.transposed else self.columns)]) >= len(
                    [u for u in units.values() if u in (self.index if self.transposed else self.columns)]):
                ku = True
            else:
                ku = False
            if ku:
                for k, u in units.items():
                    self.set_units(u, k)
                return None
            else:
                for u, k in units.items():
                    self.set_units(u, k)
                return None

        if self.units is None:
            self.units = {}

        if type(self.units) is dict:
            if not self.transposed:
                if item is None and len(self.columns) > 1:
                    raise ValueError("This SimDataFrame has multiple columns, item parameter must be provided.")
                elif item is None and len(self.columns) == 1:
                    return self.set_units(units, [list(self.columns)[0]])
                elif item is not None:
                    if item in self.columns:
                        if units is None:
                            self.units[item] = None
                        elif type(units) is str:
                            self.units[item] = units.strip()
                        else:
                            raise TypeError("units must be a string.")
                    if item == self.index.name:
                        self.index_units = units.strip()
                        self.units[item] = units.strip()
                    if item in self.index.names:
                        self.units[item] = units.strip()
            else:  # if self.transposed:
                if item is None and len(self.index) > 1:
                    raise ValueError("item must not be None")
                elif item is None and len(self.index) == 1:
                    return self.set_units(units, [list(self.index)[0]])
                elif item is not None:
                    if item in self.index:
                        if units is None:
                            self.units[item] = None
                        elif type(units) is str:
                            self.units[item] = units.strip()
                        else:
                            raise TypeError("units must be a string.")
                    if item == self.index.name:
                        self.index_units = units.strip()
                        self.units[item] = units.strip()
                    if item in self.index.names:
                        self.units[item] = units.strip()

    def keys_by_units(self):
        """
        returns a dictionary of the units present in the SimDataFrame as keys
        and a list of the columns that has that units.
        """
        kDic = {}
        for k, v in self.units.items():
            if v in kDic:
                kDic[v] += [k]
            else:
                kDic[v] = [k]
        return kDic

    def new_units(self, key, units):
        if type(key) is str:
            key = key.strip()
        if type(units) is str:
            units = units.strip()

        if self.units is None:
            self.units = {}

        if key not in self.units:
            self.units[key] = units
        else:
            if units != self.units[key] and self.verbose:
                print("overwritting existing units for key '" + key + "': " + self.units[key] + ' -> ' + units)
            self.units[key] = units

    def is_key(self, Key):
        if type(Key) != str or len(Key) == 0:
            return False
        if Key in self.get_keys():
            return True
        else:
            return False

    def keygen(self, mainKeys=[], itemKeys=[]):
        """
        returns the combination of every key in keys with all the items.
        keys and items must be list of strings
        """
        if type(itemKeys) is str:
            itemKeys = [itemKeys]
        if type(mainKeys) is str:
            mainKeys = [mainKeys]
        ListOfKeys = []
        for k in mainKeys:
            k.strip(self.name_separator)
            if self.is_key(k):
                ListOfKeys.append(k)
            for i in itemKeys:
                i = i.strip(self.name_separator)
                if self.is_key(k + self.name_separator + i):
                    ListOfKeys.append(k + self.name_separator + i)
                elif k[0].upper() == 'W':
                    wells = self.get_wells(i)
                    if len(wells) > 0:
                        for w in wells:
                            if self.is_key(k + self.name_separator + w):
                                ListOfKeys.append(k + self.name_separator + w)
                elif k[0].upper() == 'R':
                    pass
                elif k[0].upper() == 'G':
                    pass
        return ListOfKeys

    def filter(self, conditions=None, **kwargs):
        """
        Returns a filtered SimDataFrame based on conditions argument.

        To filter over a column simply use the name of the column in the
        condition:
            'NAME>0'

        In case the column name has white spaces, enclose it in ' or " or [ ]:
            "'BLANK SPACE'>0"
            '"BLANK SPACE">0'
            '[BLANK SPACE]>0'

        To set several conditions together the operatos 'and' and 'or'
        are accepted:
            'NAME>0 and LAST>0'

        To filter only over the index set the condition directly:
            '>0'
        or use the key '.index' or '.i' to refer to the index of the SimDataFrame.

        To remove null values append '.notnull' to the column name:
            'NAME.notnull'
        To keep only null values append '.null' to the column name:
            'NAME'.null

        In case the filter criteria is applied on a DataFrame, not a Series,
        the resulting filter needs to be aggregated into a single column.
        By default, the aggregation criteria will return True if any of the
        columns is True.
        This aggregation behaviour can be changed to return True only if all
        the columns are True:
            'MULTIPLE_COLUMNS'.any  needs just one column True to return True
            'MULTIPLE_COLUMNS'.any  needs all the columns True to return True

        """
        returnString = False
        if 'returnString' in kwargs:
            returnString = bool(kwargs['returnString'])
        returnFilter = False
        if 'returnFilter' in kwargs:
            returnFilter = bool(kwargs['returnFilter'])
        returnFrame = False
        if 'returnFrame' in kwargs:
            returnFrame = bool(kwargs['returnFrame'])
        if not returnFilter and not returnString and 'returnFrame' not in kwargs:
            returnFrame = True

        specialOperation = ['.notnull', '.null', '.isnull', '.abs']
        numpyOperation = ['.sqrt', '.log10', '.log2', '.log', '.ln']
        pandasAggregation = ['.any', '.all']
        PandasAgg = ''
        last = ['']

        def KeyToString(filterStr, key, PandasAgg):
            if len(key) > 0:
                # catch particular operations performed by Pandas
                foundSO, foundNO = '', ''
                if key in specialOperation:
                    if filterStr[-1] == ' ':
                        filterStr = filterStr.rstrip()
                    filterStr += key + '()'
                else:
                    for SO in specialOperation:
                        if key.strip().endswith(SO):
                            key = key[:-len(SO)]
                            foundSO = (SO if SO != '.null' else '.isnull') + '()'
                            break
                # catch particular operations performed by Numpy
                if key in numpyOperation:
                    raise ValueError("wrong syntax for '" + key + "(blank space before) in:\n   " + conditions)
                else:
                    for NO in numpyOperation:
                        if key.strip().endswith(NO):
                            key = key[:-len(NO)]
                            NO = '.log' if NO == '.ln' else NO
                            filterStr += 'np' + NO + '('
                            foundNO = ' )'
                            break
                # catch aggregation operations performed by Pandas
                if key in pandasAggregation:
                    PandasAgg = key + '(axis=1)'
                else:
                    for PA in pandasAggregation:
                        if key.strip().endswith(PA):
                            PandasAgg = PA + '(axis=1)'
                            break
                # if key is the index
                if key in ['.i', '.index']:
                    filterStr = filterStr.rstrip()
                    filterStr += ' self.DF.index'
                # if key is a column
                elif key in self.columns:
                    filterStr = filterStr.rstrip()
                    filterStr += " self.DF['" + key + "']"
                # key might be a wellname, attribute or a pattern
                elif len(self.find_keys(key)) == 1:
                    filterStr = filterStr.rstrip()
                    filterStr += " self.DF['" + self.find_keys(key)[0] + "']"
                elif len(self.find_keys(key)) > 1:
                    filterStr = filterStr.rstrip()
                    filterStr += " self.DF[" + str(list(self.find_keys(key))) + "]"
                    PandasAgg = '.any(axis=1)'
                else:
                    filterStr += ' ' + key
                filterStr = filterStr.rstrip()
                filterStr += foundSO + foundNO
                key = ''
                last.append('key')
            return filterStr, key, PandasAgg

        if type(conditions) is not str:
            if type(conditions) is not list:
                try:
                    conditions = list(conditions)
                except:
                    raise TypeError('conditions argument must be a string.')
            conditions = ' and '.join(conditions)

        conditions = conditions.strip() + ' '

        # find logical operators and translate to correct key
        AndOrNot = False
        if ' and ' in conditions:
            conditions = conditions.replace(' and ', ' & ')
        if ' or ' in conditions:
            conditions = conditions.replace(' or ', ' | ')
        if ' not ' in conditions:
            conditions = conditions.replace(' not ', ' ~ ')
        if '&' in conditions:
            AndOrNot = True
        elif '|' in conditions:
            AndOrNot = True
        elif '~' in conditions:
            AndOrNot = True

        # create Pandas compatible condition string
        filterStr = ' ' + '(' * AndOrNot
        key = ''
        cond, oper = '', ''
        i = 0
        while i < len(conditions):

            # catch logital operators
            if conditions[i] in ['&', "|", '~']:
                filterStr, key, PandasAgg = KeyToString(filterStr, key, PandasAgg)
                filterStr = filterStr.rstrip()
                auto = ' self.DF.index' if last[-1] in ['(', 'cond', 'oper'] else ''
                filterStr += auto + ' )' + PandasAgg + ' ' + conditions[i] + '('
                last.append('log')
                PandasAgg = ''
                i += 1
                continue

            # catch enclosed strings
            if conditions[i] in ['"', "'", '[']:
                if conditions[i] in ['"', "'"]:
                    try:
                        f = conditions.index(conditions[i], i + 1)
                    except:
                        raise ValueError('wring syntax, closing ' + conditions[i] + ' not found in:\n   ' + conditions)
                else:
                    try:
                        f = conditions.index(']', i + 1)
                    except:
                        raise ValueError("wring syntax, closing ']' not found in:\n   " + conditions)
                if f > i + 1:
                    key = conditions[i + 1:f]
                    filterStr, key, PandasAgg = KeyToString(filterStr, key, PandasAgg)
                    i = f + 1
                    continue

            # pass blank spaces
            if conditions[i] == ' ':
                filterStr, key, PandasAgg = KeyToString(filterStr, key, PandasAgg)
                if len(filterStr) > 0 and filterStr[-1] != ' ':
                    filterStr += ' '
                i += 1
                continue

            # pass parenthesis
            if conditions[i] in ['(', ')']:
                if conditions[i] == ')' and filterStr.rstrip()[-1] == '(':
                    filterStr = filterStr.rstrip()[:-1]
                    last.pop()
                else:
                    if last[-1] in ['cond', 'oper']: key = 'self.DF.index'
                    filterStr, key, PandasAgg = KeyToString(filterStr, key, PandasAgg)
                    filterStr += conditions[i]
                    last.append(conditions[i])
                i += 1
                continue

            # catch conditions
            if conditions[i] in ['=', '>', '<', '!']:
                cond = ''
                f = i + 1
                while conditions[f] in ['=', '>', '<', '!']:
                    f += 1
                cond = conditions[i:f]
                if cond == '=':
                    cond = '=='
                elif cond in ['=>', '=<', '=!']:
                    cond = cond[::-1]
                elif cond in ['><', '<>']:
                    cond = '!='
                if key == '': key = 'self.DF.index'
                filterStr, key, PandasAgg = KeyToString(filterStr, key, PandasAgg)
                filterStr = filterStr.rstrip()
                filterStr += ' ' + cond
                last.append('cond')
                i += len(cond)
                continue

            # catch operations
            if conditions[i] in ['+', '-', '*', '/', '%', '^']:
                oper = ''
                f = i + 1
                while conditions[f] in ['+', '-', '*', '/', '%', '^']:
                    f += 1
                oper = conditions[i:f]
                oper = oper.replace('^', '**')
                if last[-1] not in ['key']: key = 'self.DF.index'
                filterStr, key, PandasAgg = KeyToString(filterStr, key, PandasAgg)
                filterStr = filterStr.rstrip()
                filterStr += ' ' + oper
                last.append('oper')
                i += len(oper)
                continue

            # catch other characters
            else:
                key += conditions[i]
                i += 1
                continue

        # clean up
        filterStr = filterStr.strip()
        # check missing key, means .index by default
        if filterStr[0] in ['=', '>', '<', '!']:
            filterStr = 'self.DF.index ' + filterStr
        elif filterStr[-1] in ['=', '>', '<', '!']:
            filterStr = filterStr + ' self.DF.index'
        # close last parethesis and aggregation
        filterStr += ' )' * bool(AndOrNot + bool(PandasAgg)) + PandasAgg
        # open parenthesis for aggregation, if needed
        if not AndOrNot and bool(PandasAgg):
            filterStr = '(' + filterStr

        retTuple = []
        if returnString:
            retTuple += [filterStr]
        if returnFilter or returnFrame:
            try:
                filterArray = eval(filterStr)
            except:
                return None
        if returnFilter:
            retTuple += [filterArray]
        if returnFrame:
            retTuple += [self.DF[filterArray]]

        if len(retTuple) == 1:
            return retTuple[0]
        else:
            return tuple(retTuple)

    def integrate(self, method='trapz', at=None):
        """
        Calculates numerical integration, using trapezoidal method,
        or constant value of the columns values over the index values.

        method parameter can be: 'trapz' to use trapezoidal method
                                 'const' or 'avg' constant vale multiplied
                                         by delta-index
                                 'month' constant value multiplied by days in month
                                         index must be a datetime-index
                                 'year'  constant value multiplied by days in year
                                         index must be a datetime-index
                                         or integer representing a year

        at parameter defines the row where cumulative will written, only for the
        'const' method
            Possible values are: 'same' to write the cumulative in the same row
                                        of the input value, considering the cumulative
                                        is at the end of the period represented by the row index.
                                 'next' to write the cumulative in the next row, considering the
                                        cumulative is reached at the instant represented
                                        by the row index.

        Returns a new SimDataFrame
        """
        from .common.daterelated import days_in_month, days_in_year

        method = method.lower().strip()

        sl1 = slice(0, -1)
        sl2 = slice(1, len(self))

        if method[0] == 't':
            pass
            # sl1 = slice(0,-1)
            # sl2 = slice(1,len(self))
        elif method[0] in 'ac':
            if at is None:
                at = 'next'
            elif str(at).lower().strip() not in ['same', 'next']:
                raise ValueError("parameter 'at' must be 'same' or 'next'.")
            else:
                at = str(at).lower().strip()
            # sl1 = slice(1,len(self))
            # sl2 = slice(0,-1)
        elif method[0] in 'my':
            pass
        else:
            raise ValueError("'method' parameter must be 'trapz' or 'const'")

        if len(self) < 2:
            print("less than two rows, nothing to integrate.")
            return None

        if method[0] in 'tac':
            dt = np.diff(self.index)
            dt_units = self.index_units
            if str(dt.dtype).startswith('timedelta'):
                dt = dt.astype('timedelta64[s]').astype('float64') / 60 / 60 / 24
                dt_units = 'DAYS'
        elif method[0] in 'm':
            dt = days_in_month(self.index)
            dt_units = 'DAYS'
        elif method[0] in 'y':
            dt = days_in_year(self.index)
            dt_units = 'DAYS'

        if method[0] in 't':
            v_min = np.minimum(self.DF[sl1].set_index(self.index[sl2]), self.DF[sl2])
            v_max = np.maximum(self.DF[sl1].set_index(self.index[sl2]), self.DF[sl2])
            cumulative = (dt * v_min.transpose()).transpose() + (dt * (v_max - v_min).transpose() / 2.0).transpose()
        elif method[0] in 'ac':
            if at == 'same':
                cumulative = (dt * (self.DF[sl1]).transpose()).transpose()  # [sl2]
            if at == 'next':
                cumulative = (dt * (self.DF[sl1].set_index(self.index[sl2])).transpose()).transpose()
        elif method[0] in 'm':
            cumulative = (dt * self.DF.transpose()).transpose()

        new_units = {}
        for C, U in self.units.items():
            if U is None:
                new_units[C] = None
            elif len(U.split('/')) == 2 and (U.split('/')[-1].upper() == dt_units.upper() or (
                    U.split('/')[-1].upper() in ['DAY', 'DAYS'] and dt_units.upper() == 'DAYS')):
                new_units[C] = U.split('/')[0]
            else:
                new_units[C] = U + '*' + dt_units

        params_ = self.params_
        params_['units'] = new_units

        if method[0] in 't' or (method[0] in 'ac' and at == 'next'):
            if str(dt.dtype).startswith('timedelta'):
                first_row = DataFrame(dict(zip(self.columns, [0.0] * len(self.columns))), index=['0']).set_index(
                    DatetimeIndex([self.index[0]]))
            else:
                first_row = DataFrame(dict(zip(self.columns, [0.0] * len(self.columns))), index=[self.index[0]])
            return SimDataFrame(data=np.cumsum(first_row.append(cumulative)), **params_)
        elif method[0] in 'ac' and at == 'same':
            if str(dt.dtype).startswith('timedelta'):
                last_row = DataFrame(dict(zip(self.columns, [0.0] * len(self.columns))),
                                    index=[str(len(self) - 1)]).set_index(DatetimeIndex([self.index[-1]]))
            else:
                last_row = DataFrame(dict(zip(self.columns, [0.0] * len(self.columns))), index=[self.index[-1]])
            return SimDataFrame(data=np.cumsum(cumulative.append(last_row)), **params_)
        else:
            return SimDataFrame(data=np.cumsum(cumulative), **params_)

    def differenciate(self, na_position='last'):
        """
        Calculates numerical differentiation of the columns values over the index values.

        Returns a new SimDataFrame
        """
        # method=method.lower().strip()

        if len(self) < 2:
            print("less than two rows, nothing to differenciate.")
            return None

        dt = np.diff(self.index)
        dtUnits = self.index_units
        if str(dt.dtype).startswith('timedelta'):
            dt = dt.astype('timedelta64[s]').astype('float64') / 60 / 60 / 24
            dtUnits = 'DAYS'

        diff = np.diff(self.DF.to_numpy(), axis=0)
        diff = diff / dt.reshape(-1, 1)

        newUnits = {}
        if self.units is not None:
            for C, U in self.units.items():
                if U is None:
                    newUnits[C] = str(U) + '/' + str(dtUnits)
                elif len(U.split('/')) == 2 and (U.split('/')[-1].upper() == dtUnits.upper() or (
                        U.split('/')[-1].upper() in ['DAY', 'DAYS'] and dtUnits.upper() == 'DAYS')):
                    newUnits[C] = U + '/' + U.split('/')[-1]
                elif len(U.split('*')) == 2 and (U.split('*')[-1].upper() == dtUnits.upper() or (
                        U.split('*')[-1].upper() in ['DAY', 'DAYS'] and dtUnits.upper() == 'DAYS')):
                    newUnits[C] = U.split('*')[0]
                else:
                    newUnits[C] = str(U) + '/' + str(dtUnits)

        if na_position == 'first':
            if str(dt.dtype).startswith('timedelta'):
                NaNRow = DataFrame(dict(zip(self.columns, [None] * len(self.columns))), index=['0']).set_index(
                    DatetimeIndex([self.index[0]]))
            else:
                NaNRow = DataFrame(dict(zip(self.columns, [None] * len(self.columns))), index=[self.index[0]])
            diff = DataFrame(data=diff, index=self.index[1:], columns=self.columns)
            diff = NaNRow.append(diff)
        else:
            if str(dt.dtype).startswith('timedelta'):
                NaNRow = DataFrame(dict(zip(self.columns, [None] * len(self.columns))), index=['0']).set_index(
                    DatetimeIndex([self.index[-1]]))
            else:
                NaNRow = DataFrame(dict(zip(self.columns, [None] * len(self.columns))), index=[self.index[-1]])
            diff = DataFrame(data=diff, index=self.index[:-1], columns=self.columns)
            diff = diff.append(NaNRow)

        params_ = self.params_
        params_['units'] = newUnits
        params_['indexUnits'] = self.index_units
        return SimDataFrame(data=diff, **params_)

    def sort_values(self, by=None, axis='--auto', ascending=True, inplace=False, kind='quicksort', na_position='last',
                    ignore_index=False, key=None):
        if by is None and axis == '--auto':
            if len(self.index) == 1 and len(self.columns) > 1:
                result = SimDataFrame(data=self.DF.T[self.DF.T.columns[0]].sort_values(axis=0,
                                                                                       ascending=ascending,
                                                                                       inplace=False,
                                                                                       kind=kind,
                                                                                       na_position=na_position,
                                                                                       ignore_index=ignore_index,
                                                                                       key=key).T,
                                      **self.params_)
                if inplace:
                    self = result
                    return result
                else:
                    return result
            elif len(self.index) > 1 and len(self.columns) == 1:
                if inplace:
                    super().sort_values(by=self.columns[0], axis=0, ascending=ascending, inplace=inplace, kind=kind,
                                        na_position=na_position, ignore_index=ignore_index, key=key)
                    return None
                else:
                    return SimDataFrame(
                        data=self.DF.sort_values(by=self.columns[0], axis=0, ascending=ascending, inplace=inplace,
                                                 kind=kind, na_position=na_position, ignore_index=ignore_index,
                                                 key=key), **self.params_)
            else:
                if axis == '--auto':
                    axis = 0
                if inplace:
                    super().sort_values(axis=axis, ascending=ascending, inplace=inplace, kind=kind,
                                        na_position=na_position, ignore_index=ignore_index, key=key)
                    return None
                else:
                    return SimDataFrame(
                        data=self.DF.sort_values(axis=axis, ascending=ascending, inplace=inplace, kind=kind,
                                                 na_position=na_position, ignore_index=ignore_index, key=key),
                        **self.params_)
        else:
            if axis == '--auto':
                axis = 0
            if inplace:
                super().sort_values(by=by, axis=axis, ascending=ascending, inplace=inplace, kind=kind,
                                    na_position=na_position, ignore_index=ignore_index, key=key)
                return None
            else:
                return SimDataFrame(
                    data=self.DF.sort_values(by=by, axis=axis, ascending=ascending, inplace=inplace, kind=kind,
                                             na_position=na_position, ignore_index=ignore_index, key=key),
                    **self.params_)






    def melt(self, **kwargs):
        from .common.shape import melt
        melted = melt(self, full_output=False)
        if len(melted[melted.columns[-1]].unique()) == 1:
            params_ = self.params_
            params_['units'] = {melted.columns[0]: melted[melted.columns[-1]].unique()[0]}
            return SimDataFrame(data=melted.iloc[:, :-1], **params_)
        else:
            return melted





    def slope(self, x=None, y=None, window=None, slope=True, intercept=False):
        """
        Calculates the slope of column Y vs column X or vs index if 'x' is None

        Parameters
        ----------
        x : str, optional
            The name of the column to be used as X.
            If None, the index of the DataFrame will be used as X.
            The default is None.
        y : str, optional
            The name of the column to be used as Y.
            If None, the first argument will be considered as Y (not as X).
            The default is None.
        window : int, float or str, optional
            The half-size of the rolling window to calculate the slope.
            if None : the slope will be calculated from the entire dataset.
            if int : window rows before and after of each row will be used to calculate the slope
            if float : the window size will be variable, with window values of X arround each row's X. Not compatible with datetime columns
            if str : the window string will be used as timedelta arround the datetime X
            The default is None.
        slope : bool, optional
            Set it True to return the slope of the linear fit. The default is True.
        intercept : bool, optional
            Set it True to return the intersect of the linear fit. The default is False.
        if both slope and intercept are True, a tuple of both results will be returned

        Returns
        -------
        numpy array
            The array containing the desired output.

        """
        params_ = self.params_
        if x is not None and y is not None:
            if x in self.columns and y in self.columns:
                xUnits = str(self.get_units(x)[x])
            elif x in self.columns and y not in self.columns:
                xUnits = str(self.index_units)
        else:
            xUnits = str(self.index_units)
        for col in self.columns:
            if col is not None and len(self.get_units(col)) == 1:
                params_['units']['slope_of_' + str(col)] = str(self.get_units(col)[col]) + '/' + xUnits
        names = ['slope_of_' + str(col) for col in self.columns]
        slopeDF = _slope(df=self, x=x, y=y, window=window, slope=slope, intercept=intercept)
        return SimDataFrame(data=slopeDF, index=self.index, columns=names, **params_)

    def plot(self, y=None, x=None, others=None, figsize=None, dpi=None, **kwargs):
        """
        wrapper of Pandas plot method, with some superpowers

        Parameters
        ----------
        y : string, list or index; optional
            Column name to plot. The default is None.
        x : string, optional
            The columns to be used for x coordinates. The default is the index.
        others : SimDataFrame, SimSeries, DataFrame or Series; optional
            Other Frames to include in the plot, for the same selected columns. The default is None.
        figsize : (float, float), optional
            Width, height in inches.
            It will be passed to matplotlib.pyplot.figure to create the figure.
            Only valid for a new figure ('figure' keyword not found in kwargs).
        dpi : float, optional
            The resolution of the figure in dots-per-inch.
            It will be passed to matplotlib.pyplot.figure to create the figure.
            Only valid for a new figure ('figure' keyword not found in kwargs).
        xMin, xMin, yMin, yMax : as per values of X or Y axes.
            A shorcut to xlim and ylim matplotlib keywords,
            must be provided as keyword arguments.
        **kwargs : matplotlib_keyword='paramenter'
            any other keyword argument for matplolib.

        Returns
        -------
        matplotlib AxesSubplot.
        """
        y = self.columns if y is None else [y] if type(y) is str else y
        y = [i for i in y if i != x] if x is not None else y

        if 'xMin' in kwargs:
            if 'xlim' in kwargs:
                kwargs['xlim'] = (kwargs['xMin'], kwargs['xlim'][1])
            else:
                kwargs['xlim'] = (kwargs['xMin'], None)
            del kwargs['xMin']
        if 'xMax' in kwargs:
            if 'xlim' in kwargs:
                kwargs['xlim'] = (kwargs['xlim'][0], kwargs['xMax'])
            else:
                kwargs['xlim'] = (None, kwargs['xMax'])
            del kwargs['xMax']
        if 'yMin' in kwargs:
            if 'ylim' in kwargs:
                kwargs['ylim'] = (kwargs['yMin'], kwargs['ylim'][1])
            else:
                kwargs['ylim'] = (kwargs['yMin'], None)
            del kwargs['yMin']
        if 'yMax' in kwargs:
            if 'ylim' in kwargs:
                kwargs['ylim'] = (kwargs['ylim'][0], kwargs['yMax'])
            else:
                kwargs['ylim'] = (None, kwargs['yMax'])
            del kwargs['yMax']

        if type(others) is str:
            marker = [m for m in '.,ov^<>12348spP*hH+xXDd|_' if m in others]
            if len(marker) > 0:
                kwargs['marker'] = marker[0]
            linestyle = [l for l in ['--', '-', '-.', ':'] if l in others]
            if len(linestyle) > 0:
                kwargs['linestyle'] = linestyle[0]
            else:
                kwargs['linestyle'] = 'None'
            color = [c for c in 'bgrcmykw' if c in others]
            if len(color) > 0:
                if 'marker' in kwargs:
                    kwargs['markerfacecolor'] = color[0]
                kwargs['color'] = color[0]
            others = None

        if figsize is not None or dpi is not None:
            if 'figure' not in kwargs and 'ax' not in kwargs:
                kwargs['figure'], kwargs['ax'] = plt.subplots(figsize=figsize, dpi=dpi)

        labels = None
        if others is None:
            if 'labels' in kwargs:
                if type(kwargs['labels']) is not list:
                    kwargs['labels'] = [kwargs['labels']]
                if len(kwargs['labels']) == len(y):
                    labels = kwargs['labels']
                del kwargs['labels']
            if 'ylabel' not in kwargs:
                kwargs['ylabel'] = ('\n').join(
                    [str(yi) + (' [' + str(self.get_units(yi)[yi]) + ']') if self.get_units(yi)[yi] is not None else ''
                     for yi in y])
            if x is not None:
                if x in self.columns:
                    if labels is None:
                        fig = self.DF.plot(x=x, y=y, **kwargs)
                    else:
                        fig = self.DF.plot(x=x, y=y, label=labels, **kwargs)
                    plt.tight_layout()
                    return fig
                else:
                    raise ValueError("Required 'x', " + str(x) + " is not a column name in this SimDataFrame")
            else:
                if labels is None:
                    fig = self[y].DF.plot(**kwargs)
                else:
                    fig = self[y].DF.plot(label=labels, **kwargs)
                plt.tight_layout()
                return fig
        else:
            if type(others) not in (list, tuple):
                others = [others]
            if len(others) > 10 and 'legend' not in kwargs:
                kwargs['legend'] = False
            if 'labels' in kwargs:
                if type(kwargs['labels']) is list:
                    if len(kwargs['labels']) == len(others) + 1:
                        if len(y) == 1:
                            labels = [(la if type(la) is list else [str(la)]) for la in kwargs['labels']]
                        else:
                            labels = [(la if type(la) is list else [str(ys) + ' ' + str(la) for ys in y]) for la in
                                      kwargs['labels']]
                del kwargs['labels']
            if 'ax' in kwargs and kwargs['ax'] is not None:
                if labels is None:
                    kwargs['ax'] = self.plot(y=y, x=x, others=None, **kwargs)
                else:
                    kwargs['ax'] = self.plot(y=y, x=x, others=None, label=labels[0], **kwargs)
            else:
                fig = self.plot(y=y, x=x, others=None, **kwargs)
                kwargs['ax'] = fig

            labcount = 0
            for oth in others:
                labcount += 1
                if type(oth) in (SimDataFrame, SimSeries):
                    newY = [ny for ny in self.columns if ny in oth]
                    if labels is None:
                        kwargs['ax'] = oth[newY].to(self.get_units()).plot(y=y, x=x, others=None, **kwargs)
                    else:
                        kwargs['ax'] = oth[newY].to(self.get_units()).plot(y=y, x=x, others=None,
                                                                           label=labels[labcount], **kwargs)
                elif isinstance(oth, DataFrame):
                    newY = [ny for ny in self.columns if ny in oth]
                    if labels is None:
                        kwargs['ax'] = oth[newY].plot(**kwargs)
                    else:
                        kwargs['ax'] = oth[newY].plot(label=labels[labcount], **kwargs)
                elif isinstance(oth, Series):
                    if labels is None:
                        kwargs['ax'] = oth.plot(**kwargs)
                    else:
                        kwargs['ax'] = oth.plot(label=labels[labcount], **kwargs)
                else:
                    raise TypeError("others must be SimDataFrame, DataFrame, SimSeries or Series")
            return kwargs['ax']

    def to_SimationResults(self):
        """
        loads the current frame into a SimulationResults excelObject.

        return XLSX instance from Simulation Results
        """
        from datafiletoolbox.SimulationResults.excelObject import XLSX
        return XLSX(frames=self)

    def info(self, *args, **kwargs):
        """
        wrapper for pandas.DataFrame.info() but with Units.
        """

        def fillblank(string, length):
            if len(string.strip()) > length:
                return string.strip() + ' '
            return string.strip() + ' ' * (length - len(string.strip()) + 1)

        print(type(self))
        print(str(type(self.DF.index)).split('.')[-1][:-2] + ': ' + str(len(self)) + ' entries, ' + str(
            self.index[0]) + ' to ' + str(self.index[-1]))

        columns = [str(col) for col in self.columns]
        notnulls = [str(self.iloc[:, col].notnull().sum()) for col in range(len(self.columns))]
        dtypes = [str(self.iloc[:, col].dtype) for col in range(len(self.columns))]
        units = [str(self.units[col]) for col in self.columns]

        print('Data columns (total ' + str(len(columns)) + ' columns):')

        line = ' ' + fillblank('#', len(str(len(columns))))
        line = line + ' ' + fillblank('Column', max(len('Column'), max(map(len, columns))))
        line = line + ' ' + fillblank('Non-Null Count',
                                      max(len('Non-Null Count'), len(str(len(self))) + len(' non-null')))
        line = line + ' ' + fillblank('Dtype', max(len('Dtype'), max(map(len, dtypes))))
        line = line + ' ' + fillblank('Units', max(len('Units'), max(map(len, units))))
        print(line)

        line = fillblank('---', len(str(len(columns))))
        line = line + ' ' + fillblank('------', max(map(len, columns)))
        line = line + ' ' + fillblank('--------------', len(str(len(self))) + len(' non-null '))
        line = line + ' ' + fillblank('-----', max(map(len, dtypes)))
        line = line + ' ' + fillblank('-----', max(map(len, units)))
        print(line)

        for i in range(len(columns)):
            line = ' ' + fillblank(str(i), max(len('# '), len(str(len(columns)))))
            line = line + ' ' + fillblank(columns[i], max(len('Column'), max(map(len, columns))))
            line = line + ' ' + fillblank(notnulls[i] + ' non-null',
                                          max(len('Non-Null Count'), len(str(len(self))) + len(' non-null')))
            line = line + ' ' + fillblank(dtypes[i], max(len('Dtype'), max(map(len, dtypes))))
            line = line + ' ' + fillblank(units[i], max(len('Units'), max(map(len, units))))
            print(line)

        print('dtypes: ' + ', '.join([each + '(' + str(dtypes.count(each)) + ')' for each in sorted(set(dtypes))]))

        print('memory usage: ' + str(int(getsizeof(self) / 1024 / 1024 * 10) / 10) + '+ MB')

        return None

    def well_status(self, inplace=False):
        """
        define if a well if producer or injector at each row

        Parameters
        ----------
        inplace : bool, optional
            apply the results to the original dataframe. The default is False.

        Returns
        -------
        SimDataFrame
            with a new categorical column for each well 'WSTATUS'
            containing the string 'PRODUCER' or 'INJECTOR'.

        """
        tempdf = SimDataFrame(self)

        for w in tempdf.wells:
            try:
                temp = tempdf['W?PR*:' + str(w)]
                tempdf['_PROD:' + str(w)] = (temp != 0).sum(axis=1)
            except:
                tempdf['_PROD:' + str(w)] = 0
            try:
                temp = tempdf['W?IR*:' + str(w)]
                tempdf['_INJE:' + str(w)] = (temp != 0).sum(axis=1)
            except:
                tempdf['_INJE:' + str(w)] = 0

            tempdf['WSTATUS:' + str(w)] = [
                'PRODUCER' if tempdf['_PROD:' + str(w)].iloc[i] > tempdf['_INJE:' + str(w)].iloc[i] else 'INJECTOR' if
                tempdf['_PROD:' + str(w)].iloc[i] < tempdf['_INJE:' + str(w)].iloc[i] else None for i in
                range(len(tempdf))]

        tempdf['WSTATUS:' + str(w)] = tempdf['WSTATUS:' + str(w)].fillna(method='ffill').fillna(method='bfill').astype(
            'category')

        if inplace:
            self['WSTATUS:' + str(w)] = tempdf['WSTATUS:' + str(w)]
        else:
            return tempdf.drop(columns=['_INJE:' + str(w), '_PROD:' + str(w)], inplace=True)

    # def rolling(self, window, min_periods=None, center=False, win_type=None, on=None, axis=0, closed=None, method='single'):
    #     return SimRolling(self.df, window, min_periods=min_periods, center=center, win_type=win_type, on=on, axis=axis, closed=closed, method=method,
    #         SimParameters=self.params_,
    #         )
