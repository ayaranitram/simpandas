# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.83.7'
__release__ = 20230227
__all__ = ['SimDataFrame']

import logging
from warnings import warn
from os.path import commonprefix
import pandas as pd
import fnmatch
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
from unyts.converter import convertible as _convertible, convert_for_SimPandas as _converter
from unyts.operations import unit_power as _unit_power, unit_addition as _unit_addition, unit_product as _unit_product, \
    unit_division as _unit_division
from unyts.dictionaries import unitless_names as _unitless_names
from unyts.helpers.common_classes import number
from unyts import Unit, units

from .basics import SimBasics
from .common.slope import slope as _slope
from .common.stringformat import multisplit as _multisplit, is_date as _is_date, date as _date
from .common.math import znorm as _znorm, minmaxnorm as _minmaxnorm, jitter as _jitter
from .indexer import _SimLocIndexer, _iSimLocIndexer
from .index import SimIndex
from .series import SimSeries
from .common.helpers import clean_axis as _clean_axis

logging.basicConfig(level=logging.INFO)


def _series_to_frame(a_SimSeries, params_=None):
    """
    when a row is extracted from a DataFrame, Pandas returns a Series in wich
    the columns of the DataFrame are converted to the indexes of the Series and
    the extracted index from the DataFrame is set as the Name of the Series.

    This function returns the proper DataFrame view of such Series.

    Works with SimSeries as well as with Pandas standard Series
    """
    if isinstance(a_SimSeries, pd.DataFrame):
        if params_ is None:
            return a_SimSeries
        else:
            return SimDataFrame(a_SimSeries, **params_)
    if type(a_SimSeries) is pd.Series and params_ is not None:
        a_SimSeries = SimSeries(a_SimSeries)
    if type(a_SimSeries) is SimSeries:
        if params_ is None:
            params_ = a_SimSeries.params_
        try:
            return SimDataFrame(data=dict(zip(list(a_SimSeries.index),
                                              a_SimSeries.to_list())),
                                index=[a_SimSeries.name],
                                **params_)
        except:
            return a_SimSeries
    if type(a_SimSeries) is pd.Series:
        try:
            return pd.DataFrame(data=dict(zip(list(a_SimSeries.index),
                                           a_SimSeries.to_list()
                                           )
                                       ),
                             index=a_SimSeries.columns)
        except:
            return a_SimSeries


class SimDataFrame(SimBasics, pd.DataFrame):
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
                 'index_units_',
                 'name_separator',
                 'intersection_character',
                 'spdLocator',
                 'spdiLocator',
                 'name',
                 'meta',
                 'source_path',
                 '_auto_append_',
                 '_operate_per_name_',
                 '_transposed_',
                 '_reverse_']

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
                 transposed_=False,
                 meta=None,
                 source_path=None,
                 *args, **kwargs):

        self.units = {}
        self.verbose = bool(verbose)
        self.index_units_ = None
        self.name_separator = None
        self.intersection_character = intersection_character if type(intersection_character) is str else '∩'
        self.spdLocator = _SimLocIndexer("loc", self)
        self.spdiLocator = _iSimLocIndexer("iloc", self)
        self.name = name
        self.meta = meta
        self.source_path = source_path
        self._auto_append_ = bool(auto_append)
        self._operate_per_name_ = bool(operate_per_name)
        self._transposed_ = bool(transposed_)
        self._reverse_ = kwargs['reverse'] if 'reverse' in kwargs else False

        # get units from data if it is SimDataFrame or SimSeries
        if units is None or (type(units) in [list, dict] and len(units) == 0):
            if hasattr(data, 'get_units'):
                units = data.get_units()
        elif type(units) is str:
            units = units.strip()

        # get name_separator
        if name_separator is None and hasattr(data, 'name_separator'):
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

        # catch index name as index argument
        if type(index) is str:
            set_index_, index = index, None
            if index_name is None:
                index_name = set_index_
        else:
            set_index_ = False

        # catch index units if index is instance of SimIndex
        if index_units is None and hasattr(index, 'units'):
            index_units = index.units

        # initialize pd.DataFrame
        if isinstance(data, SimBasics):
            pd_data = data.to_pandas()
        else:
            pd_data = data
        super().__init__(data=pd_data, index=index, columns=columns, dtype=dtype, copy=copy)

        # set catched index (if catched)
        if bool(set_index_) and set_index_ in self.columns:
            super().set_index(set_index_, inplace=True)

        # override index.name with index_name
        if index_name is not None:
            if self.index.name in self.units:
                self.units[index_name] = self.units[self.index.name]
            self.index.name = index_name

        # set units
        self.set_units(units)

        # get index_units
        if index_units is None:
            if self.index.name is not None and self.index.name in self.units:
                self.index_units_ = self.units[self.index.name]
            elif hasattr(data, 'index_units'):
                self.index_units_ = data.index_units.copy() if type(data.index_units) is dict else data.index_units
        else:  # override index.units with index_units
            self.index_units = index_units
            if self.index.name in self.units:
                self.units[self.index.name] = index_units

        # change pd.Index to SimIndex
        self.index = SimIndex(self.index, units=self.index_units_)

    @property
    def type(self):
        return 'SimDataFrame'

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
        if isinstance(key, pd.Series) or type(key) is np.ndarray:
            if str(key.dtype) == 'bool':
                return SimDataFrame(data=self._get_by_filter(key), **self.params_)

        # if key is pd.Index or pd.MultiIndex return selected rows or columns
        if isinstance(key, pd.Index):
            key_cols = True
            for each in key:
                if each not in self.columns:
                    key_cols = False
                    break
            if key_cols:
                return SimDataFrame(data=self._get_by_column(key), **self.params_)
            else:
                result, by_index = self._get_by_index(key)
                if by_index:
                    result = _series_to_frame(result, self.params_)
                else:
                    result = SimDataFrame(data=result, **self.params_)
                return result

        # here below we try to guess what the user is requesting
        by_index = False
        index_filter = None
        indexes = None
        result = None  # initialize variable

        # convert tuple argument to list
        if type(key) is tuple:
            key = list(key)

        # if key is a string but not a column name, check if it is an item, attribute, pattern, filter or index
        if type(key) is str and key not in self.columns:
            if bool(self.find_keys(key)):  # catch the column names this key represent
                key = list(self.find_keys(key))
            elif key in [self.index.name, self.index_name]:  # key is the name of the index
                return SimSeries(data=self.index.values,
                                 name=self.index.name,
                                 units=self.index.units if type(self.index) is SimIndex else self.index_units)
            else:  # key is not a column name
                try:  # to evaluate as a filter
                    result = self._get_by_criteria(key)
                except:
                    try:  # to evaluate as an index value
                        result, by_index = self._get_by_index(key)
                    except:
                        raise KeyError(
                            'The requested key is not a valid column name, pattern, index or filter criteria:\n   ' + key)

        # key is a list, have to check every item in the list
        elif type(key) is list:
            key_list, key, filters, indexes = key, [], [], []
            for each in key_list:
                # the key is a column name
                if type(each) is slice:
                    _temp_result, _temp_by_index  = self._get_by_index(each)
                    if _temp_by_index:
                        indexes += list(_temp_result.index)
                    else:
                        key += list(_temp_result.columns)
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
                                _temp_result, _temp_by_index  = self._get_by_index(each)
                                if _temp_by_index:
                                    if isinstance(_temp_result, pd.DataFrame):
                                        indexes += list(_temp_result.index)
                                    elif isinstance(self, pd.DataFrame):
                                        indexes += [_temp_result.name]
                                    else:
                                        indexes += list(_temp_result.index)
                                else:
                                    key += list(_temp_result.columns)
                            except:
                                # discard this item
                                logging.error('The parameter ' + str(each) + ' is not valid.')

                # must be an index, not a column name o relative, not a filter, not in the index
                else:
                    indexes += [each]

            # get the filter array, if filter criteria was provided
            if bool(filters):
                try:
                    index_filter = self.filter(filters, returnFilter=True)
                except:
                    warn('filter conditions are not valid:\n   ' + ' and '.join(filters))
                if index_filter is not None and not index_filter.any():
                    warn('filter conditions removed every row :\n   ' + ' and '.join(filters))

        # in case already got results, postprocess it
        # if type(key) is list and len(key) == 1:
        #     key = key[0]
        if result is not None:
            params_ = self.params_
            if by_index:
                result = _series_to_frame(result, params_)
            else:
                result = SimDataFrame(data=result, **params_)
        elif bool(key) or key in [0]:
            # attempt to get the desired keys, first as column names, then as indexes
            try:
                result = self._get_by_column(key)
            except:
                try:
                    result, by_index = self._get_by_index(key)
                except:
                    if key is None:
                        raise KeyError("None is not a valid column name, pattern, index or filter criteria.")
                    else:
                        raise KeyError(
                            'The requested key is not a valid column name, pattern, index or filter criteria:\n   ' + key)
        else:
            if key is None:
                raise KeyError("None is not a valid column name, pattern, index or filter criteria.")
            else:
                raise KeyError(
                    'The requested key is not a valid column name, pattern, index or filter criteria:\n   ' + key)

        # convert returned object to SimDataFrame or SimSeries accordingly
        if type(result) is pd.DataFrame:
            result = SimDataFrame(data=result, **self.params_)
        elif type(result) is pd.Series:
            if len(self.get_units()) > 0:
                if result.name is None or result.name not in self.get_units():
                    # this pd.Series is one index for multiple columns
                    try:
                        result_units = self.get_units(result.index)
                    except:
                        result_units = {result.name: 'unitless'}
                else:
                    result_units = self.get_units_string(result.name)
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
        if bool(indexes):
            if type(result) is SimDataFrame:
                i_result, by_index = result._get_by_index(indexes)
            else:
                i_result, by_index = result[indexes], False
            if by_index and isinstance(i_result, (pd.Series, SimSeries)):
                i_result = _series_to_frame(i_result, self.params_)
            try:
                result = i_result.sort_index()
            except:
                result = i_result

        # if is a single row return it as a DataFrame instead of a pd.Series
        if by_index and isinstance(result, (pd.Series, SimSeries)):
            result = _series_to_frame(result)

        if isinstance(result, pd.Series) and len(result) == 1:
            if type(result.iloc[0]) in number:
                result = units(result.iloc[0], result.get_units_string())
            else:
                result = result.iloc[0]
        elif isinstance(result, pd.DataFrame) and len(result) == 1 and len(result.columns) == 1:
            if type(result.iloc[0, 0]) in number:
                result = units(result.iloc[0, 0], self.get_units_string(list(result.columns)[0]))
            else:
                result = result.iloc[0, 0]
        elif type(result) is pd.DataFrame:
            result = SimDataFrame(result, **self.params_)
        elif type(result) is pd.Series:
            result = SimSeries(result, **self.params_)
        return result

    def __setitem__(self, key, value, units=None):
        u_dict = {}
        if type(key) is str:
            key = key.strip()
        if type(value) is tuple and len(value) == 2 and type(value[1]) in [str,
                                                                           dict] and units is None:  # and type(value[0]) in [SimSeries, pd.Series, list, tuple, np.ndarray,float,int,str]
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
                if self.index_units is None and value.index_units is not None:
                    self.index_units = value.index_units
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
                                value.index = _converter(value.index, value.index_units, self.index_units,
                                                         print_conversion_path=self.verbose)
                            except:
                                warn(
                                    "WARNING: failed to convert the provided index to the units of this SimDataFrame index.")
                        else:
                            warn(
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

    def _arithmethic_operation(self, other, operation: str = None, level=None, fill_value=None, axis=0,
                               intersection_character=None):
        def _units_operation(a, b, operation):
            if operation in ['+', '-', '%']:
                return _unit_addition(a, b)
            elif operation in ['*']:
                return _unit_product(a, b)
            elif operation in ['/', '//']:
                return _unit_division(a, b)
            elif operation in ['**']:
                return _unit_power(a, b)
            else:
                raise ValueError("Unknown operation")

        params_ = self.params_.copy()
        _products = ['*', '/', '//']
        valid_operations = {# operator, pd.Series.method, proposed fill_value
                            '+': [pd.Series.add, 'Addition', 0],
                            '-': [pd.Series.sub, 'Subtraction', 0],
                            '*': [pd.Series.mul, 'Product', 1],
                            '/': [pd.Series.truediv, 'Division', None],
                            '//': [pd.Series.floordiv, 'Floor Division', None],
                            '%': [pd.Series.mod, 'Module', None],
                            '**': [pd.Series.pow, 'Power', None],
                            '^': [pd.Series.pow, 'Power', None]}
        assert operation in valid_operations
        intersection_character = operation if intersection_character is None else intersection_character
        op_method = valid_operations[operation][0]
        op_label = valid_operations[operation][1]
        fill_value = valid_operations[operation][1] if fill_value is True else fill_value

        # ensure self.index is SimIndex
        if not hasattr(self.index, 'units'):
            self.index = SimIndex(self.index, units=self.index_units)

        # both are SimDataFrame
        if isinstance(other, SimDataFrame):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimDataFrames are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")

            # ensure other.index is SimIndex
            if not hasattr(other.index, 'units'):
                other.index = SimIndex(other.index, units=other.index_units)

            # convert other.index.units if required and possible
            if self.index.units == other.index.units:
                pass
            elif self.index.units not in _unitless_names and other.index.units not in _unitless_names and \
                    _convertible(other.index.units, self.index.units):
                other = other.index_to(self.index.units)

            not_fount = 0
            self_i, other_i = self._joined_index(other)
            result = self_i.copy()

            for col in other_i.columns:
                if col in self_i.columns:
                    result[col] = self_i[col]._arithmethic_operation(other_i[col],
                                                                     operation=operation,
                                                                     level=level,
                                                                     fill_value=fill_value,
                                                                     axis=0,
                                                                     intersection_character=intersection_character)
                else:
                    not_fount += 1
                    result[col] = other_i[col]

            if not_fount == len(other_i.columns):
                if self_i.name_separator is not None and other_i.name_separator is not None:
                    self_c, other_c, new_names = self_i._common_rename(other_i)

                    # if no columns has common names
                    if new_names is None:
                        if len(other_c.columns) == 1 and not self._auto_append_:  # just in case there is only one column in the second operand
                            return self_c._arithmethic_operation(other_c.to_simseries(),
                                                                 operation=operation,
                                                                 level=level,
                                                                 fill_value=fill_value,
                                                                 axis=0,
                                                                 intersection_character=intersection_character)
                        elif not self._auto_append_:
                            raise NotImplementedError("Not possible to operate SimDataFrames if there aren't common columns.")
                        else:  # self._auto_append_ is True
                            for col in other_i.columns:
                                result[col] = other_i[col]
                    else:
                        if (self_i.columns != self_c.columns).any() or (other_i.columns != other_c.columns).any():
                            result_x = self_c + other_c
                            result_x.rename(columns=new_names, inplace=True)
                        else:
                            result_x = result
                        if self._auto_append_:
                            for col in new_names.values():
                                result[col] = result_x[col]
                        else:
                            result = result_x
            return result


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
                        if len(other_c.columns) == 1 and not self._auto_append_:  # just in case there is only one column in the second operand
                            return self_c + other_c.to_simseries()
                        elif not self._auto_append_:
                            raise TypeError("Not possible to operate SimDataFrames if there aren't common columns")
                        else:  # self._auto_append_ is True
                            for col in other_i.columns:
                                result[col] = other_i[col]
                    else:
                        if (self_i.columns != self_c.columns).any() or (other_i.columns != other_c.columns).any():
                            result_x = self_c + other_c
                            result_x.rename(columns=new_names, inplace=True)
                        else:
                            result_x = result
                        if self._auto_append_:
                            for col in new_names.values():
                                result[col] = result_x[col]
                        else:
                            result = result_x
            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, pd.Series)):
            if type(other) is pd.Series:
                other = SimSeries(other, **self.params_)
            self_i, other_i = self._joined_index(other)
            other_i = other_i.to_simseries()
            result = self_i.copy()
            if self._operate_per_name_ and other_i.name in self_i.columns:
                result[other_i.name] = self_i[other_i.name] + other_i
            elif self_i._auto_append_:
                result[other_i.name] = other_i
            else:
                for col in self_i.columns:
                    result[col] = self_i[col] + other_i
            return result

        # other is Pandas DataFrame
        elif isinstance(other, pd.DataFrame):
            # result = self.as_pandas().add(other, fill_value=0)
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
                    if self._auto_append_:
                        for col in newNames.values():
                            result[col] = resultX[col]
                    else:
                        result = resultX
            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, pd.Series)):
            if type(other) is pd.Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self._operate_per_name_ and otherI.name in selfI.columns:
                result[otherI.name] = selfI[otherI.name] - otherI
            if self._auto_append_:  # elif self._auto_append_:
                result[otherI.name] = -otherI
            else:
                for col in selfI.columns:
                    result[col] = selfI[col] - otherI
            return result

        # other is Pandas DataFrame
        elif isinstance(other, pd.DataFrame):
            # result = self.as_pandas().sub(other, fill_value=0)
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
                    if self._auto_append_:
                        for col in new_names.values():
                            if self.intersection_character in col:  # intersection_character = '∩'
                                result[col] = result_x[col]
                    else:
                        result = result_x

            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, pd.Series)):
            if type(other) is pd.Series:
                other = SimSeries(other, **self.params_)
            self_i, other_i = self._joined_index(other)
            result = self_i.copy()
            if self._operate_per_name_ and other_i.name in self_i.columns:
                result[other_i.name] = self[other_i.name] * other_i
            else:
                for col in self_i.columns:
                    result[col] = self_i[col] * other_i
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, pd.DataFrame):
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
                    if self._auto_append_:
                        for col in newNames.values():
                            if self.intersection_character in col:  # intersection_character = '∩'
                                result[col] = resultX[col]
                    else:
                        result = resultX
            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, pd.Series)):
            if type(other) is pd.Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self._operate_per_name_ and otherI.name in selfI.columns:
                result[otherI.name] = selfI[otherI.name] / otherI
            else:
                for col in selfI.columns:
                    result[col] = selfI[col] / otherI
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, pd.DataFrame):
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
                    if self._auto_append_:
                        for col in newNames.values():
                            if self.intersection_character in col:  # intersection_character = '∩'
                                result[col] = resultX[col]
                    else:
                        result = resultX
            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, pd.Series)):
            if type(other) is pd.Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self._operate_per_name_ and otherI.name in selfI.columns:
                result[otherI.name] = selfI[otherI.name] // otherI
            else:
                for col in self.columns:
                    result[col] = self[col] // other
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, pd.DataFrame):
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
                    if self._auto_append_:
                        for col in newNames.values():
                            if self.intersection_character in col:  # intersection_character = '∩'
                                result[col] = resultX[col]
                    else:
                        result = resultX

            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, pd.Series)):
            if type(other) is pd.Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self._operate_per_name_ and otherI.name in selfI.columns:
                result[otherI.name] = selfI[other.name] % otherI
            else:
                for col in selfI.columns:
                    result[col] = selfI[col] % otherI
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, pd.DataFrame):
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
                    if self._auto_append_:
                        for col in newNames.values():
                            if self.intersection_character in col:  # intersection_character = '∩'
                                result[col] = resultX[col]
                    else:
                        result = resultX

            return result

        # other is SimSeries
        elif isinstance(other, (SimSeries, pd.Series)):
            if type(other) is pd.Series:
                other = SimSeries(other, **self.params_)
            selfI, otherI = self._joined_index(other)
            result = selfI.copy()
            if self._operate_per_name_ and otherI.name in selfI.columns:
                result[otherI.name] = self[otherI.name] ** otherI
            else:
                for col in selfI.columns:
                    result[col] = selfI[col] ** otherI
            return result

        # if other is Pandas DataFrame, convert it to SimDataFrame to be able to deal with
        elif isinstance(other, pd.DataFrame):
            return self.__pow__(SimDataFrame(data=other, **self.params_))

        # if other is integer or float
        elif type(other) in (int, float):
            result = self.as_DataFrame() ** other
            params_ = self.params_.copy()
            params_['units'] = {c: _unit_power(self.get_units(c)[c], other) for c in self.columns}
            return SimDataFrame(data=result, **params_)

        # lets Pandas deal with other types, maintain units and dtype
        else:
            result = self.as_DataFrame() ** other
            return SimDataFrame(data=result, **self.params_)

    def set_index(self, key, drop=True, append=False, inplace=False, verify_integrity=False, **kwargs):
        if type(key) is list:
            if False in [k in self.columns for k in key]:
                k = [str(k) for k in key if k not in self.columns]
                raise ValueError("The key '" + ', '.join(k) + "' is not a column name of this SimDataFrame.")
        elif key not in self.columns:
            raise ValueError("The key '" + str(key) + "' is not a column name of this SimDataFrame.")
        if inplace:
            index_units = self.get_units(key)[key]
            super().set_index(key, drop=drop, append=append, inplace=inplace, verify_integrity=verify_integrity,
                              **kwargs)
            self.set_index_units(index_units)
        else:
            params_ = self.params_.copy()
            params_['index'] = None
            params_['index_name'] = key
            params_['index_units'] = self.get_units(key)[key]
            return SimDataFrame(data=self.as_pandas().set_index(key, drop=drop, append=append, inplace=inplace,
                                                       verify_integrity=verify_integrity, **kwargs), **params_)

    def get_index_units(self):
        if not isinstance(self.index, SimIndex) and type(self.index_units_) is str:
            self.index = SimIndex(self.index, units=self.index_units_)
        elif isinstance(self.index, SimIndex) and type(self.index.units) is str and len(self.index.units) > 0:
            self.index_units_ = self.index.units
        return self.index_units_

    def set_index_units(self, units):
        if hasattr(units, 'units') and type(units.units) is str:
            units = units.units
        elif hasattr(units, 'unit') and type(units.unit) is str:
            units = units.unit
        if type(units) is str and len(units.strip()) > 0:
            self.index_units_ = units.strip()
        else:
            raise TypeError("`units` must be a not-empty string.")
        if not isinstance(self.index, SimIndex) and type(self.index_units_) is str:
            self.index = SimIndex(self.index, units=self.index_units_)
        elif type(self.index_units_) is str:
            self.index.set_units(self.index_units_)

    def transpose(self):
        params_ = self.params_.copy()
        params_['transposed'] = not self._transposed_
        return SimDataFrame(data=self.as_pandas().T, **params_)

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
            return SimSeries(data=pd.Series(self.to_pandas().iloc[0].to_list(),
                                         name=self.index[0],
                                         index=self.columns.to_list()),
                             **self.params_)
        raise TypeError('Not possible to converto to SimSeries')

    def as_simseries(self):
        return self.to_simseries()

    def to_dataframe(self):
        return pd.DataFrame(self.copy())

    def as_dataframe(self):
        return pd.DataFrame(self)

    def to_simdataframe(self):
        return self

    def as_simdataframe(self):
        return self

    def convert(self, units):
        """
        returns the SimDataFrame converted to the requested units if possible,
        else returns None
        """
        if isinstance(units, (Unit, SimSeries, SimDataFrame)):
            units = units.units
        if self._transposed_:
            return self.transpose().convert(units).transpose()
        elif type(units) is str:
            if len(set(self.units.values())) == 1:
                if _convertible(list(set(self.units.values()))[0], units):
                    params_ = self.params_.copy()
                    params_['units'] = units
                    params_['columns'] = self.columns
                    params_['index'] = self.index
                    return SimDataFrame(data=_converter(self, list(set(self.units.values()))[0],
                                                        units, print_conversion_path=self.verbose),
                                        **params_)
                else:
                    return None
            else:
                result = SimDataFrame(index=self.index, columns=self.columns, **self.params_)
                valid = False
                for col in self.columns:
                    if _convertible(self.get_units(col)[col], units):
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
                logging.warning('No columns could be to converted to the requested units.')
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
        axis = _clean_axis(axis)
        return SimDataFrame(data=self.to_pandas().reindex(labels=labels, axis=axis, **kwargs), **self.params_)


    # not shared methods
    def to_DataFrameMultiIndex(self):
        return self._DataFrame_with_MultiIndex()

    def reset_index(self, level=None, drop=False, inplace=False, col_level=0, col_fill=''):
        if inplace:
            index_units, index_name = self.index_units, None if drop else self.index.name
            super().reset_index(level=level, drop=drop, inplace=inplace, col_level=col_level, col_fill='')
            if type(index_units) in (str, dict) and index_name is not None:
                self.set_units(index_units, index_name)
            self.index = SimIndex(self.index, units=None)
        else:
            params_ = self.params_
            params_['index_name'] = None
            params_['index_units'] = None
            result = SimDataFrame(
                data=self.as_pandas().reset_index(level=level, drop=drop, inplace=inplace, col_level=col_level, col_fill=''),
                **params_)
            if not drop and type(self.index_units) in (str, dict) and self.index.name is not None:
                result.set_units(self.index_units, item=self.index.name)
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
            params_ = self.params_.copy()
            params_['units'] = newUnits
            data = pd.concat([self.as_pandas(), otherC], axis=0)
            return SimDataFrame(data=data, **params_)
        else:
            # append and return SimDataFrame
            data = pd.concat([self.as_pandas(), otherC], axis=0)
            return SimDataFrame(data=data, **self.params_)

    def drop(self, labels=None, axis=0, index=None, columns=None, level=None, inplace=False, errors='raise'):
        axis = _clean_axis(axis)
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

    def dropna(self, axis=0, how='all', thresh=None, subset=None, inplace=False):
        axis = _clean_axis(axis)
        if subset is not None:
            if type(subset) is str and subset in self.columns:
                pass
            elif len(self.find_keys(subset)) > 0:
                subset = list(self.find_keys(subset))
        if inplace:
            if thresh is None:
                super().dropna(axis=axis, thresh=thresh, subset=subset, inplace=inplace)
            else:
                super().dropna(axis=axis, how=how, subset=subset, inplace=inplace)
        else:
            if thresh is None:
                data = self.as_pandas().dropna(axis=axis, how=how, subset=subset, inplace=inplace)
            else:
                data = self.as_pandas().dropna(axis=axis, thresh=thresh, subset=subset, inplace=inplace)
            return SimDataFrame(data=data, **self.params_)

    def drop_duplicates(self, subset=None, keep='first', inplace=False, ignore_index=False):
        if inplace:
            super().drop_duplicates(subset=subset, keep=keep, inplace=inplace, ignore_index=ignore_index)
        else:
            return SimDataFrame(
                data=self.as_pandas().drop_duplicates(subset=subset, keep=keep, inplace=inplace, ignore_index=ignore_index),
                **self.params_)

    def drop_zeros(self, axis=None, inplace=False):
        """
        drop the axis(rows or columns) where all the values are zeross.

        axis parameter can be:
            'columns' or 1 : removes all the columns fill with zeroes
            'index' or 'rows' 0 : removes all the rows fill with zeroes
            'both' or 2 : removes all the rows and columns fill with zeroes
        """
        axis = _clean_axis(axis)
        if inplace:
            if axis == 2:
                filt = self.zeros(axis=0)
                self.drop(columns=filt[filt == True].index, inplace=True)
                filt = self.zeros(axis=1)
                self.drop(index=filt[filt == True].index, inplace=True)
                filt = self.zeros(axis=0)
                self.drop(columns=filt[filt == True].index, inplace=True)
            elif axis == 0:
                filt = self.zeros(axis=0)
                self.drop(columns=filt[filt == True].index, inplace=True)
            elif axis == 1:
                filt = self.zeros(axis=1)
                self.drop(index=filt[filt == True].index, inplace=True)
            else:
                raise ValueError(" valid `axis` argument are 0 or 'index', 1 or 'columns' or 2 for 'both'.")
        else:
            if axis == 2:
                filt = self.zeros(axis=0)
                temp = self.drop(columns=filt[filt == True].index, inplace=False)
                filt = temp.zeros(axis=1)
                temp = temp.drop(index=filt[filt == True].index, inplace=False)
                filt = temp.zeros(axis=0)
                return temp.drop(columns=filt[filt == True].index, inplace=False)
            elif axis == 0:
                filt = self.zeros(axis=0)
                return self.drop(columns=filt[filt == True].index, inplace=False)
            elif axis == 1:
                filt = self.zeros(axis=1)
                return self.drop(index=filt[filt == True].index, inplace=False)
            else:
                raise ValueError(" valid `axis´ argument are 'index', 'columns' or 'both'.")

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
        col_before = list(self.columns)
        if inplace:
            super().rename(mapper=mapper, index=index, columns=columns, axis=axis, copy=copy, inplace=inplace,
                           level=level, errors=errors)
            col_after = list(self.columns)
        else:
            catch = super().rename(mapper=mapper, index=index, columns=columns, axis=axis, copy=copy, inplace=inplace,
                                   level=level, errors=errors)
            col_after = list(catch.columns)
        new_units = {}
        for i in range(len(col_before)):
            if col_before[i] in self.units:
                new_units[col_after[i]] = self.units[col_before[i]]
        if inplace:
            self.units = new_units
            self.spdLocator = _SimLocIndexer("loc", self)
            return None
        else:
            catch.units = new_units
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

    def count(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=self.as_pandas().count(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            new_name = '.count'
            if len(set(self.columns)) == 1:
                new_name = list(set(self.columns))[0] + new_name
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                new_name = list(set(self.rename_right(inplace=False).columns))[0] + new_name
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                new_name = list(set(self.rename_left(inplace=False).columns))[0] + new_name
            data = self.as_pandas().count(axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = 'dimensionless'
            return self._class(data=data, **params_)

    def rms(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=((self.as_pandas() ** 2).mean(axis=axis, **kwargs)) ** 0.5, **self.params_)
        if axis == 1:
            new_name = '.rms'
            if len(set(self.columns)) == 1:
                new_name = list(set(self.columns))[0] + new_name
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                new_name = list(set(self.rename_right(inplace=False).columns))[0] + new_name
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                new_name = list(set(self.rename_left(inplace=False).columns))[0] + new_name
            data = self._class(data=(self.as_pandas() ** 2), **self.params_).mean(axis=axis, **kwargs)
            data.rename(columns={data.columns[0]: new_name}, inplace=True)
            data.name = new_name
            params_ = data.params_
            params_['name'] = new_name
            params_['columns'] = [new_name]
            return self._class(data=data, **params_)

    def min(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=self.as_pandas().min(axis=axis, **kwargs), **self.params_)
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
            data = self.as_pandas().min(axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)

    def max(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=self.as_pandas().max(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            new_name = '.max'
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
            data = self.as_pandas().max(axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)

    def mean(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=self.as_pandas().mean(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            new_name = '.mean'
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
            data = self.as_pandas().mean(axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)

    def median(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=self.as_pandas().median(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            new_name = '.median'
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
            data = self.as_pandas().median(axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)

    def mode(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=self.as_pandas().mode(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            new_name = '.mode'
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
            data = self.as_pandas().mode(axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)

    def prod(self, axis=0, **kwargs):
        from unyts.operations import unit_base_power
        from unyts.units.unitless import unitless_names
        axis = _clean_axis(axis)
        if axis == 0:
            params_ = self.params_.copy()
            for key in params_['units']:
                if params_['units'][key] is not None:
                    unit_base, unit_power = unit_base_power(params_['units'][key])
                    if unit_base in unitless_names:
                        params_['units'][key] = unit_base
                    else:
                        params_['units'][key] = unit_base + str(unit_power * len(self))
            return self._class(data=self.as_pandas().prod(axis=axis, **kwargs), **params_)
        if axis == 1:
            new_name = '.prod'
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
            data = self.as_pandas().prod(axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)

    def quantile(self, q=0.5, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=self.as_pandas().quantile(q=q, axis=axis, **kwargs), **self.params_)
        if axis == 1 and hasattr(q, '__iter__'):  # q is a list
            namedecimals = 1
            if 'namedecimals' in kwargs:
                if type(kwargs['namedecimals']) is int:
                    namedecimals = kwargs['namedecimals']
                del kwargs['namedecimals']
            else:
                namedecimals = len(str(q)) - 2
            new_name_lambda = lambda q: '.Q' + str(round(q * 100, namedecimals))
            new_name = map(new_name_lambda, q)
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if len(set(self.columns)) == 1:
                new_name = [list(set(self.columns))[0] + nm for nm in new_name]
            elif len(set(self.rename_right(inplace=False).columns)) == 1:
                new_name = [list(set(self.rename_right(inplace=False).columns))[0] + nm for nm in new_name]
            elif len(set(self.rename_left(inplace=False).columns)) == 1:
                new_name = [list(set(self.rename_left(inplace=False).columns))[0] + nm for nm in new_name]
            data = self.as_pandas().quantile(q=q, axis=axis, **kwargs).transpose()
            data.columns = new_name
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)
        elif axis == 1:
            namedecimals = 1
            if 'namedecimals' in kwargs:
                if type(kwargs['namedecimals']) is int:
                    namedecimals = kwargs['namedecimals']
                del kwargs['namedecimals']
            else:
                namedecimals = len(str(q)) - 2
            new_name = '.Q' + str(round(q * 100, namedecimals))
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
            data = self.as_pandas().quantile(q=q, axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)

    def std(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=self.as_pandas().std(axis=axis, **kwargs), **self.params_)
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
            data = self.as_pandas().std(axis=axis, **kwargs)
            data.columns = [newName]
            data.name = newName
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)

    def sum(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            if len(set(self.get_units(self.columns).values())) == 1:
                params_ = self.params_.copy()
                params_['units'] = list(set(self.get_units(self.columns).values()))[0]
                return self._class(data=self.as_pandas().sum(axis=axis, **kwargs).rename('.sum'), **params_)
            else:
                params_ = self.params_.copy()
                if type(params_['units']) is dict:
                    params_['units']['.sum'] = '*units per row'
                return self._class(data=self.as_pandas().sum(axis=axis, **kwargs).rename('.sum'), **params_)
        if axis == 1:
            new_name = '.sum'
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
            else:
                common_l = commonprefix(list(self.rename_left(inplace=False).columns))
                common_r = commonprefix(list(self.rename_right(inplace=False).columns))
                if len(common_l) >= len(common_r):
                    new_name = common_l + new_name
                else:
                    new_name = common_r + new_name
            if len(set(self.get_units(self.columns).values())) == 1:
                data = self.as_pandas().sum(axis=axis, **kwargs)
            else:
                i = 0
                while self.columns[i] not in self.units:
                    i += 1
                result = self[self.columns[i]]
                units = self.units[self.columns[i]]
                for col in (j for j in range(len(self.columns)) if j != i):
                    result = result + self[self.columns[col]]
                data = result
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)
        if axis == 2:
            return self.sum(axis=1).sum(axis=0)

    def var(self, axis=0, **kwargs):
        axis = _clean_axis(axis)
        if axis == 0:
            return self._class(data=self.as_pandas().var(axis=axis, **kwargs), **self.params_)
        if axis == 1:
            new_name = '.var'
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
            data = self.as_pandas().var(axis=axis, **kwargs)
            data.columns = [new_name]
            data.name = new_name
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=data, **params_)

    def round(self, decimals=0, **kwargs):
        return self._class(data=self.as_pandas().round(decimals=decimals, **kwargs), **self.params_)

    def _get_by_filter(self, key):
        """
        ** helper function to __getitem__ method **

        try to get a filtered DataFrame or Series(.filter[key] )
        """
        if not isinstance(key, (SimSeries, pd.Series)) and type(key) is not np.ndarray:
            raise TypeError("Filter must be a Series or Array")
        else:
            if str(key.dtype) != 'bool':
                raise TypeError("Filter dtype must be 'bool'")
        if len(key) == len(self):
            return self.loc[key]
        elif len(key) == len(self.columns):
            return self.iloc[:, [i for i in range(len(key)) if bool(key.values[i])]]
        else:
            raise ValueError('Filter wrong length ' + str(len(key)) + ' instead of ' + str(len(self)))

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
        return self.as_pandas().__getitem__(key)

    def _get_by_index(self, key):
        """
        ** helper function to __getitem__ method **

        try to get a row by index value(.loc[key] ) or by position(.iloc[key] )
        """
        # if index is date try to undestand key as a date
        if type(self.index) is pd.DatetimeIndex and type(key) not in [pd.DatetimeIndex, pd.Timestamp, int, float, np.ndarray]:
            try:
                return (self._get_by_dateIndex(key), True)
            except:
                pass

        # try to find key by index value using .loc
        try:
            return (self.as_pandas().loc[key], True,)
        except:
            # try to find key by index position using .loc
            try:
                return (self.as_pandas().iloc[key], True,)
            except:
                try:
                    return (self.as_pandas().loc[:, key], False,)
                except:
                    try:
                        return (self.as_pandas().iloc[:, key], False,)
                    except:
                        raise ValueError(' ' + str(key) + ' is not a valid index value or position.')

    def _get_by_dateIndex(self, key):
        """
        ** helper function to __getitem__ method **

        try to get a row by index value(.loc[key] ) or by position(.iloc[key] )
        """
        if type(self.index) is pd.DatetimeIndex:
            if type(key) in [pd.DatetimeIndex, pd.Timestamp, np.datetime64, np.ndarray, dt.date]:
                try:
                    return self.as_pandas().loc[key]
                except:
                    pass

            if type(key) is not str and (_is_date(key) or type(key) not in [pd.DatetimeIndex, pd.Timestamp]):
                try:
                    return self.as_pandas().loc[key]
                except:
                    try:
                        return self.as_pandas().iloc[key]
                    except:
                        pass

            if type(key) is str and len(
                    _multisplit(key, ('==', '!=', '>=', '<=', '<>', '><', '>', '<', '=', ' '))) == 1 and _is_date(key):
                try:
                    key = _date(key, speak=self.verbose)
                except:
                    try:
                        key = _date(key, formatIN=_is_date(key, returnFormat=True), formatOUT='DD-MMM-YYYY', speak=self.verbose)
                    except:
                        raise Warning('\n Not able to undertand the key as a date.\n')
                try:
                    return self.as_pandas().loc[key]
                except:
                    pass

            if type(key) is str:
                keyParts = _multisplit(key, ('==', '!=', '>=', '<=', '<>', '><', '>', '<', '=', ' '))
                keySearch = ''
                datesDict = {}
                temporal = SimDataFrame(index=self.index, **self.params_)
                datesN = len(self)
                for P in range(len(keyParts)):
                    if _is_date(keyParts[P]):
                        keySearch += ' D' + str(P)
                        datesDict['D' + str(P)] = keyParts[P]
                        temporal.__setitem__('D' + str(P), pd.DatetimeIndex([pd.Timestamp(
                            _date(keyParts[P], formatIN=_is_date(keyParts[P], returnFormat=True, speak=self.verbose),
                                  formatOUT='YYYY-MMM-DD'))] * datesN).to_numpy())
                    else:
                        keySearch += ' ' + keyParts[P]
                datesFilter = temporal.filter(keySearch, returnFilter=True)
                return self.as_pandas().iloc[datesFilter.array]

            else:
                return self.as_pandas().iloc[key]

    def _columns_name_and_units_to_MultiIndex(self):
        out = []  # out = {}
        units = self.get_units()
        if units is None or len(units) == 0:
            return self.columns  # there are not units, return column names as they are
        if len(self.columns) == 0:
            return self.columns  # is an empty pd.DataFrame
        for col in self.columns:
            if col in units:
                out.append((col, units[col]))  # out[col] = units[col]
            else:
                out.append((col, None))  # out[col] = None
        out = pd.MultiIndex.from_tuples(out)  # out = pd.MultiIndex.from_tuples(out.items())
        return out

    def _DataFrame_with_MultiIndex(self):
        if self._transposed_:
            result = self.as_pandas().copy()
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
            result.index = self.index
            return result

    def _repr_html_(self):
        """
        Return a html representation for a particular DataFrame, with Units.
        """
        return self._DataFrame_with_MultiIndex()._repr_html_()

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
        if pattern is not None and type(pattern) not in [str, int, float]:
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
            self.units = {col: 'unitless' for col in self.columns}

        if items is None:
            units_dict = self.units.copy()
            if self.index_name not in units_dict:
                units_dict[self.index_name] = self.index_units
            elif self.index_units != units_dict[self.index_name]:
                if self.index_name not in self.columns:
                    self.units[self.index_name] = self.index_units
                else:
                    units_dict[str(self.index_name) + '_index_'] = self.index_units
        else:
            units_dict = {}
            if not isinstance(items, (list, tuple, dict, set, pd.Index)):
                items = [items]
            for each in items:
                if each in self.units:
                    units_dict[each] = self.units[each]
                elif each in self.wells or each in self.groups or each in self.regions:
                    for Key in self.get_keys('*' + self.name_separator + each):
                        units_dict[each] = self.units[each]
                elif each in self.attributes:
                    for att in self.keygen(each, self.attributes[each]):
                        if att in self.units:
                            units_dict[att] = self.units[att]
                        else:
                            units_dict[att] = 'unitless'
                elif len(self.get_keys(each)) > 0:
                    for key in self.get_keys(each):
                        units_dict[key] = self.units[key] if key in self.units else ''
                elif each == self.index.name:
                    units_dict[each] == self.index_units
        return units_dict

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
        if units is None and item is None:
            return None

        if item is not None and \
            units is not None and \
            type(item) is not str and hasattr(units, '__iter__') and \
            type(units) not in (str, dict) and hasattr(units, '__iter__'):
            if len(item) == len(units):
                return self.set_units(dict(zip(item, units)))
            else:
                raise ValueError("both units and item must have the same length.")
        elif item is not None and \
            type(item) is not str and hasattr(item, '__iter__') and \
            type(units) is str:
            return self.set_units({i: units for i in item})
        elif item is not None and \
            item not in list(self.columns) + [self.index_name] + [self.index.name] + self.index.names:
            if units in self.columns or units == self.index.name or units in self.index.names:
                return self.set_units(item, units)
            else:
                ValueError("the required item '" + str(item) + "' is not in this SimDataFrame.")

        if type(units) not in (str, dict, pd.Series, SimSeries) and hasattr(units, '__iter__'):
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

        if isinstance(units, pd.Series):
            units = units.to_dict()

        if type(units) is dict:
            if len([k for k in units.keys() if k in (self.index if self._transposed_ else self.columns)]) >= len(
                    [u for u in units.values() if u in (self.index if self._transposed_ else self.columns)]):
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
            
        elif type(units) is str:
            self.units[item] = units.strip().strip('[').strip(']')
        elif units is None:
            pass  # units = 'unitless'
        else:
            raise TypeError("units must be a string.")

        if self.units is None:
            self.units = {}

        # if type(self.units) is dict:
        if not self._transposed_:
            if item is None and None not in self.columns and units is not None:
                self.units[item] = units
            elif item is None and units is not None and len(self.columns) > 1:
                raise ValueError("This SimDataFrame has multiple columns, item parameter must be provided.")
            elif item is None and len(self.columns) == 1:
                return self.set_units(units, [list(self.columns)[0]])
            elif item is not None:
                if item in self.columns:
                    self.units[item] = units
                elif item == self.index.name:
                    self.index_units = units
                    self.units[item] = units
                elif item in self.index.names:
                    self.units[item] = units
        else:  # if self._transposed_:
            if item is None and len(self.index) > 1:
                raise ValueError("item must not be None")
            elif item is None and len(self.index) == 1:
                return self.set_units(units, [list(self.index)[0]])
            elif item is not None:
                if item in self.index:
                    self.units[item] = units
                elif item == self.index.name:
                    self.index_units = units
                    self.units[item] = units
                elif item in self.index.names:
                    self.units[item] = units

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
                logging.warning("Overwritting existing units for key '" + key + "': " + self.units[key] + ' -> ' + units)
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
        from simpandas.common.filters import key_to_string

        return_string = False
        if 'return_string' in kwargs:
            return_string = bool(kwargs['return_string'])
        return_filter = False
        if 'return_filter' in kwargs:
            return_filter = bool(kwargs['return_filter'])
        return_frame = False
        if 'return_frame' in kwargs:
            return_frame = bool(kwargs['return_frame'])
        if not return_filter and not return_string and 'return_frame' not in kwargs:
            return_frame = True

        special_operation = ['.notnull', '.null', '.isnull', '.abs']
        numpy_operation = ['.sqrt', '.log10', '.log2', '.log', '.ln']
        pandas_aggregation = ['.any', '.all']
        pandas_agg = ''
        last = ['']

        if type(conditions) is not str:
            if type(conditions) is not list:
                try:
                    conditions = list(conditions)
                except:
                    raise TypeError('conditions argument must be a string.')
            conditions = ' and '.join(conditions)

        conditions = conditions.strip() + ' '

        # find logical operators and translate to correct key
        and_or_not = False
        if ' and ' in conditions:
            conditions = conditions.replace(' and ', ' & ')
        if ' or ' in conditions:
            conditions = conditions.replace(' or ', ' | ')
        if ' not ' in conditions:
            conditions = conditions.replace(' not ', ' ~ ')
        if '&' in conditions:
            and_or_not = True
        elif '|' in conditions:
            and_or_not = True
        elif '~' in conditions:
            and_or_not = True

        # create Pandas compatible condition string
        filter_str = ' ' + '(' * and_or_not
        key = ''
        cond, oper = '', ''
        i = 0
        while i < len(conditions):

            # catch logital operators
            if conditions[i] in ['&', "|", '~']:
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg)
                filter_str = filter_str.rstrip()
                auto = ' self.as_pandas().index' if last[-1] in ['(', 'cond', 'oper'] else ''
                filter_str += auto + ' )' + pandas_agg + ' ' + conditions[i] + '('
                last.append('log')
                pandas_agg = ''
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
                    filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg)
                    i = f + 1
                    continue

            # pass blank spaces
            if conditions[i] == ' ':
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg)
                if len(filter_str) > 0 and filter_str[-1] != ' ':
                    filter_str += ' '
                i += 1
                continue

            # pass parenthesis
            if conditions[i] in ['(', ')']:
                if conditions[i] == ')' and filter_str.rstrip()[-1] == '(':
                    filter_str = filter_str.rstrip()[:-1]
                    last.pop()
                else:
                    if last[-1] in ['cond', 'oper']:
                        key = 'self.as_pandas().index'
                    filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg)
                    filter_str += conditions[i]
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
                if key == '':
                    key = 'self.as_pandas().index'
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg)
                filter_str = filter_str.rstrip()
                filter_str += ' ' + cond
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
                if last[-1] not in ['key']:
                    key = 'self.as_pandas().index'
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg)
                filter_str = filter_str.rstrip()
                filter_str += ' ' + oper
                last.append('oper')
                i += len(oper)
                continue

            # catch other characters
            else:
                key += conditions[i]
                i += 1
                continue

        # clean up
        filter_str = filter_str.strip()
        # check missing key, means .index by default
        if filter_str[0] in ['=', '>', '<', '!']:
            filter_str = 'self.as_pandas().index ' + filter_str
        elif filter_str[-1] in ['=', '>', '<', '!']:
            filter_str = filter_str + ' self.as_pandas().index'
        # close last parethesis and aggregation
        filter_str += ' )' * bool(and_or_not + bool(pandas_agg)) + pandas_agg
        # open parenthesis for aggregation, if needed
        if not and_or_not and bool(pandas_agg):
            filter_str = '(' + filter_str

        ret_tuple = []
        if return_string:
            ret_tuple += [filter_str]
        if return_filter or return_frame:
            try:
                filter_array = eval(filter_str)
            except:
                return None
        if return_filter:
            ret_tuple += [filter_array]
        if return_frame:
            ret_tuple += [self.as_pandas()[filter_array]]

        if len(ret_tuple) == 1:
            return ret_tuple[0]
        else:
            return tuple(ret_tuple)




    def sort_values(self, by=None, axis='--auto', ascending=True, inplace=False, kind='quicksort', na_position='last',
                    ignore_index=False, key=None):
        axis = _clean_axis(axis)
        if by is None and axis == '--auto':
            if len(self.index) == 1 and len(self.columns) > 1:
                result = SimDataFrame(data=self.as_pandas().T[self.as_pandas().T.columns[0]].sort_values(axis=0,
                                                                                       ascending=ascending,
                                                                                       inplace=False,
                                                                                       kind=kind,
                                                                                       na_position=na_position,
                                                                                       ignore_index=ignore_index,
                                                                                       key=key).T,
                                      **self.params_)
                if inplace:
                    self = result
                    return None
                else:
                    return result
            elif len(self.index) > 1 and len(self.columns) == 1:
                if inplace:
                    super().sort_values(by=self.columns[0], axis=0, ascending=ascending, inplace=inplace, kind=kind,
                                        na_position=na_position, ignore_index=ignore_index, key=key)
                    return None
                else:
                    return SimDataFrame(
                        data=self.as_pandas().sort_values(by=self.columns[0], axis=0, ascending=ascending, inplace=inplace,
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
                        data=self.as_pandas().sort_values(axis=axis, ascending=ascending, inplace=inplace, kind=kind,
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
                    data=self.as_pandas().sort_values(by=by, axis=axis, ascending=ascending, inplace=inplace, kind=kind,
                                             na_position=na_position, ignore_index=ignore_index, key=key),
                    **self.params_)

    def melt(self, **kwargs):
        from simpandas.common.shape import melt
        melted = melt(self, full_output=False)
        if len(melted[melted.columns[-1]].unique()) == 1:
            params_ = self.params_.copy()
            params_['units'] = {melted.columns[0]: melted[melted.columns[-1]].unique()[0]}
            return SimDataFrame(data=melted.iloc[:, :-1], **params_)
        else:
            return melted

    def slope(self, x=None, y=None, axis=None, window=None, slope=True, intercept=False):
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
        axis = _clean_axis(axis)
        if axis == 1:
            return self.transpose().slope(x=x, y=y, axis=0, window=window, slope=slope, intercept=intercept).transpose()

        params_ = self.params_.copy()
        if x is not None and y is not None:
            if x in self.columns and y in self.columns:
                x_units = str(self.get_units(x)[x])
            elif x in self.columns and y not in self.columns:
                x_units = str(self.index_units)
        else:
            x_units = str(self.index_units)
        for col in self.columns:
            if col is not None and len(self.get_units(col)) == 1:
                params_['units']['slope_of_' + str(col)] = str(self.get_units(col)[col]) + '/' + x_units
        names = ['slope_of_' + str(col) for col in self.columns]
        slope_df = _slope(df=self, x=x, y=y, window=window, slope=slope, intercept=intercept)
        return SimDataFrame(data=slope_df, index=self.index, columns=names, **params_)

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
                        fig = self.as_pandas().plot(x=x, y=y, **kwargs)
                    else:
                        fig = self.as_pandas().plot(x=x, y=y, label=labels, **kwargs)
                    plt.tight_layout()
                    return fig
                else:
                    raise ValueError("Required 'x', " + str(x) + " is not a column name in this SimDataFrame")
            else:
                if labels is None:
                    fig = self[y].as_pandas().plot(**kwargs)
                else:
                    fig = self[y].as_pandas().plot(label=labels, **kwargs)
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
                elif isinstance(oth, pd.DataFrame):
                    newY = [ny for ny in self.columns if ny in oth]
                    if labels is None:
                        kwargs['ax'] = oth[newY].plot(**kwargs)
                    else:
                        kwargs['ax'] = oth[newY].plot(label=labels[labcount], **kwargs)
                elif isinstance(oth, pd.Series):
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
