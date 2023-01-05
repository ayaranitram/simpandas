# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.9'
__release__ = 20221003
__all__ = ['SimBasics']

import fnmatch

import numpy as np
from simpandas.indexer import _SimLocIndexer
from warnings import warn


class SimBasics(object):
    """

    """
    def __init__(self):
        self.units = {}
        self.verbose = False
        self.index_units = None
        self.name_separator = ':'
        self.intersection_character = '∩'
        self.auto_append = False
        self.operate_per_name = False
        self.transposed = False
        self.spdLocator = None
        self.name = None

    @property
    def loc(self) -> _SimLocIndexer:
        """
        wrapper for .loc indexing
        """
        return self.spdLocator

    # @property
    # def iloc(self) -> _iSimLocIndexer:
    #     """
    #     wrapper for .iloc indexing
    #     """
    #     return self.spdiLocator

    def params_(self):
        return {'units': self.units.copy() if type(self.units) is dict else self.units,
                'name': self.name,
                'verbose': self.verbose if hasattr(self, 'verbose') else False,
                'index_name': self.index.name,
                'index_units': self.index_units if hasattr(self, 'index_units') else None,
                'name_separator': self.name_separator if hasattr(self, 'name_separator') else None,
                'intersection_character': self.intersection_character if hasattr(self, 'intersection_character') else '∩',
                'auto_append': self.auto_append if hasattr(self, 'auto_append') else False,
                'operate_per_name': self.operate_per_name if hasattr(self, 'operate_per_name') else False,
                'transposed': self.transposed if hasattr(self, 'transposed') else False,
                }

    @property
    def _SimParameters(self):
        return self.params_

    def describe(self, *args, **kwargs):
        return self._class(data=self.to_Pandas().describe(*args, **kwargs),
                           **self.params_)

    def set_index_name(self, name):
        if type(name) is str and len(name.strip()) > 0:
            self.index.name = name.strip()

    def __contains__(self, item):
        if item in self.columns:
            return True
        elif item in self.index:
            return True
        else:
            return False

    def __neg__(self):
        return self._class(data=self.as_Pandas().__neg__(), **self.params_)

    def __int__(self):
        return self._class(data=self.as_Pandas().astype(int), **self.params_)

    def __abs__(self):
        return self._class(data=abs(self.as_Pandas()), **self.params_)

    def set_name_separator(self, separator):
        if type(separator) is str and len(separator) > 0:
            if separator in '=-+&*/!%':
                print(
                    "The separator '" + separator + "' could be confused with operators.\n it is recommended to use ':' as separator.")
            self.name_separator = separator
        else:
            raise TypeError("The `separator` must be a string.")

    def get_name_separator(self):
        if self.name_separator in [None, '', False]:
            warn(" NameSeparator is not defined.")
            return ''
        else:
            return self.name_separator

    def to_Pandas(self):
        return self.to_pandas()

    def toPandas(self):
        return self.to_pandas()

    def as_Pandas(self):
        return self.as_pandas()

    def asPandas(self):
        return self.as_pandas()

    def to_Series(self):
        return self.to_series()

    def toSeries(self):
        return self.to_series()

    def as_Series(self):
        return self.as_series()

    def asSeries(self):
        return self.as_series()

    def to_SimSeries(self):
        return self.to_simseries()

    def toSimSeries(self):
        return self.to_simseries()

    def as_SimSeries(self):
        return self.as_simseries()

    def asSimSeries(self):
        return self.as_simseries()

    def to_DataFrame(self):
        return self.to_dataframe()

    def toDataFrame(self):
        return self.to_dataframe()
    def as_DataFrame(self):
        return self.as_dataframe()

    def asDataFrame(self):
        return self.as_dataframe()

    def to_SimDataFrame(self):
        return self.to_simdataframe()

    def toSimDataFrame(self):
        return self.to_simdataframe()

    def as_SimDataFrame(self):
        return self.as_simdataframe()

    def asSimDataFrame(self):
        return self.as_simdataframe()

    @property
    def Series(self):
        return self.as_series()

    @property
    def s(self):
        return self.as_series()

    @property
    def S(self):
        return self.as_series()

    @property
    def DataFrame(self):
        return self.as_dataframe()

    @property
    def df(self):
        return self.as_dataframe()

    @property
    def DF(self):
        return self.as_dataframe()

    @property
    def SimDataFrame(self):
        return self.as_simdataframe()

    @property
    def sdf(self):
        return self.as_simdataframe()

    @property
    def SDF(self):
        return self.as_simdataframe()

    def squeeze(self, axis=None):
        """
        wrapper of pandas.squeeze

        SimSeries with a single element and no units (or unitless) are squeezed to a scalar.
        SimSeries without units or unitless are squeezed to a Series.
        SimDataFrame without units or unitless are squeezed to a DataFrame.
        SimDataFrame with a single row or column are squeezed to a SimSeries.
        SimDataFrame with a single row or column and without units or unitless are squeezed to a Series.
        SimDataFrame with a single element and no units (or unitless) are squeezed to a scalar.

        Parameters
        ----------
        axis : {0 or ‘index’, 1 or ‘columns’, None}, default None
            A specific axis to squeeze. By default, all length-1 axes are squeezed., optional

        Returns
        -------
        SimDataFrame, DataFrame, SimSeries, Series, or scalar
            The projection after squeezing axis or all the axes and units

        """
        from simpandas import SimSeries, SimDataFrame
        if self._class is SimDataFrame:
            if len(self.columns) == 1 or len(self.index) == 1:
                return self.to_simseries().squeeze()
            elif len(self.get_units()) == 0 or \
                    np.array([(u is None or str(u).lower().strip() in ['unitless', 'dimensionless']) for u in
                              self.get_units().values()]).all():
                return self.as_DataFrame()
            else:
                return self
        elif self._class is SimSeries:
            if len(self) == 1:
                if len(self.get_units()) == 0 or np.array(
                        [(u is None or str(u).lower().strip() in ['unitless', 'dimensionless']) for u in
                         self.get_units().values()]).all():
                    return self.iloc[0]
            elif len(self.get_units()) == 0 or np.array(
                    [(u is None or str(u).lower().strip() in ['unitless', 'dimensionless']) for u in
                     self.get_units().values()]).all():
                return self.as_Series()
            elif type(self.get_units()) is dict and len(set(self.get_units(self.index).values())) == 1:
                params_ = self.params_.copy()
                params_['units'] = list(set(self.get_units(self.index).values()))[0]
                return SimSeries(self.as_Series(), **params_)
            else:
                return self
        else:
            return self

    @property
    def T(self):
        return self.transpose()

    def rename_right(self, inplace=False):
        from simpandas import SimSeries, SimDataFrame
        if self.name_separator in [None, '', False]:
            return self
        objs = {each: None if each is None else each.split(self.name_separator)[-1] for each in self.columns}
        if self._class is SimDataFrame:
            if len(set(objs.keys())) != len(set(objs.values())):
                objs = dict(zip(objs.keys(), objs.keys()))
        elif self._class is SimSeries:
            if len(self.columns) == 1:
                objs = list(objs.values())[0]
        if inplace:
            self.rename(columns=objs, inplace=inplace)
        else:
            return self.rename(columns=objs, inplace=inplace)

    def rename_left(self, inplace=False):
        from simpandas import SimSeries, SimDataFrame
        if self.name_separator in [None, '', False]:
            return self
        objs = {each: None if each is None else each.split(self.name_separator)[0] for each in self.columns}
        if self._class is SimDataFrame:
            if len(set(objs.keys())) != len(set(objs.values())):
                objs = dict(zip(objs.keys(), objs.keys()))
        elif self._class is SimSeries:
            if len(self.columns) == 1:
                objs = list(objs.values())[0]
        if inplace:
            self.rename(columns=objs, inplace=inplace)
        else:
            return self.rename(columns=objs, inplace=inplace)

    def renameRight(self, inplace=False):
        return self.rename_right(inplace=inplace)
    def renameLeft(self, inplace=False):
        return self.rename_left(inplace=inplace)

    def shift(self, periods=1, freq=None, axis=0, fill_value=None):
        """
        wrapper for Pandas shift method

        Shift index by desired number of periods with an optional time freq.

        When freq is not passed, shift the index without realigning the data.
        If freq is passed (in this case, the index must be date or datetime,
        or it will raise a NotImplementedError), the index will be increased using the periods and the freq. freq can be inferred when specified as “infer” as long as either freq or inferred_freq attribute is set in the index.

        Parameters
periodsint
Number of periods to shift. Can be positive or negative.

freqDateOffset, tseries.offsets, timedelta, or str, optional
Offset to use from the tseries module or time rule (e.g. ‘EOM’). If freq is specified then the index values are shifted but the data is not realigned. That is, use freq if you would like to extend the index when shifting and preserve the original data. If freq is specified as “infer” then it will be inferred from the freq or inferred_freq attributes of the index. If neither of those attributes exist, a ValueError is thrown.

axis{0 or ‘index’, 1 or ‘columns’, None}, default None
Shift direction.

fill_valueobject, optional
The scalar value to use for newly introduced missing values. the default depends on the dtype of self. For numeric data, np.nan is used. For datetime, timedelta, or period data, etc. NaT is used. For extension dtypes, self.dtype.na_value is used.

Changed in version 1.1.0.

Returns
SimDataFrame
Copy of input object, shifted.

        """
        return self._class(data=self.as_Pandas().shift(periods=periods, freq=freq, axis=axis, fill_value=fill_value),
                            **self.params_)

    def to(self, units):
        """
        returns the dataframe converted to the requested units if possible, if not, returns the original values.
        """
        return self.convert(units)

    @property
    def index_name(self):
        return self.index.name

    @property
    def right(self):
        if self.name_separator is None or self.name_separator is False or self.name_separator in ['']:
            return list(self.columns)
        else:
            return list(set([None if each is None else each.split(self.name_separator)[-1] for each in self.columns]))

    @property
    def left(self):
        if self.name_separator is None or self.name_separator is False or self.name_separator in ['']:
            return list(self.columns)
        else:
            return list(set([None if each is None else each.split(self.name_separator)[0] for each in self.columns]))

    def get_wells(self, pattern=None):
        """
        Will return a tuple of all the well names in case.

        If the pattern variable is different from None only wells
        matching the pattern will be returned; the matching is based
        on fnmatch():
            Pattern     Meaning
            *           matches everything
            ?           matches any single character
            [seq]       matches any character in seq
            [!seq]      matches any character not in seq

        """
        if pattern is not None and type(pattern) is not str:
            raise TypeError('pattern argument must be a string.')
        if pattern is None:
            return tuple(self.wells)
        else:
            return tuple(fnmatch.filter(self.wells, pattern))

    def get_groups(self, pattern=None):
        """
        Will return a tuple of all the group names in case.

        If the pattern variable is different from None only groups
        matching the pattern will be returned; the matching is based
        on fnmatch():
            Pattern     Meaning
            *           matches everything
            ?           matches any single character
            [seq]       matches any character in seq
            [!seq]      matches any character not in seq

        """
        if pattern is not None and type(pattern) is not str:
            raise TypeError('pattern argument must be a string.')
        if pattern is None:
            return self.groups
        else:
            return tuple(fnmatch.filter(self.groups, pattern))

    def get_regions(self, pattern=None):
        """
        Will return a tuple of all the region names in case.

        If the pattern variable is different from None only regions
        matching the pattern will be returned; the matching is based
        on fnmatch():
            Pattern     Meaning
            *           matches everything
            ?           matches any single character
            [seq]       matches any character in seq
            [!seq]      matches any character not in seq
        """
        if pattern is not None and type(pattern) is not str:
            raise TypeError('pattern argument must be a string.')
        if pattern is None:
            return self.regions
        else:
            return tuple(fnmatch.filter(self.regions, pattern))

    def get_attributes(self, pattern=None):
        """
        Will return a dictionary of all the attributes names in case as keys
        and their related items as values.

        If the pattern variable is different from None only attributes
        matching the pattern will be returned; the matching is based
        on fnmatch():
            Pattern     Meaning
            *           matches everything
            ?           matches any single character
            [seq]       matches any character in seq
            [!seq]      matches any character not in seq
        """
        if pattern is None:
            return tuple(self.attributes.keys())
        else:
            return tuple(fnmatch.filter(tuple(self.attributes.keys()), pattern))