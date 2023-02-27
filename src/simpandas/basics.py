# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.83.11'
__release__ = 20230227
__all__ = ['SimBasics']

import fnmatch
import logging
import numpy as np
import pandas as pd
from sys import getsizeof
from warnings import warn
from unyts import is_Unit
from unyts.converter import convertible as _convertible
from unyts.operations import unit_inverse as _unit_inverse
from unyts.dictionaries import unitless_names as _unitless_names
from unyts import Unit
from .indexer import _SimLocIndexer, _iSimLocIndexer
from .common.daterelated import days_in_year, real_year, days_in_month, check_day, check_month
from .common.math import znorm as _znorm, minmaxnorm as _minmaxnorm, jitter as _jitter
from .common.renamer import right as _right, left as _left, common_rename as _common_rename
from .common.helpers import clean_axis as _clean_axis, hashable

logging.basicConfig(level=logging.INFO)


class SimType(type):
    def __repr__(self):
        return self.__name__


class SimBasics(object, metaclass=SimType):

    def __contains__(self, item):
        if item in self.columns:
            return True
        elif item in self.index:
            return True
        elif item == self.index.name:
            return True
        else:
            return False

    def _reverse(self):
        self._reverse_ = not self._reverse_
        return self

    @property
    def _SimParameters(self):
        return self.params_

    @property
    def loc(self) -> _SimLocIndexer:
        """
        wrapper for .loc indexing
        """
        return self.spdLocator

    @property
    def iloc(self) -> _iSimLocIndexer:
        """
        wrapper for .iloc indexing
        """
        return self.spdiLocator

    def isna(self):
        return self.as_pandas().isna()

    def concat(self, objs, axis=0, join='outer', ignore_index=False,
               keys=None, levels=None, names=None, verify_integrity=False,
               sort=False, copy=True, squeeze=True):
        """
        wrapper of pandas.concat enhanced with units support

        Return:
            SimDataFrame
        """
        from simpandas.common.merger import concat as _concat
        from simpandas import SimDataFrame, SimSeries
        from pandas import DataFrame, Series

        if type(objs) is list:
            for each in objs:
                if not isinstance(each, (SimDataFrame, DataFrame, SimSeries, Series)):
                    raise TypeError("`objs` must be a list of Series, DataFrames, SimSeries or SimDataFrames")
        elif not isinstance(objs, (SimDataFrame, DataFrame, SimSeries, Series)):
            raise TypeError("objs must be a list of DataFrames or SimDataFrames")
        else:
            objs = [objs]

        if len(objs) == 1:
            warn("WARNING: only 1 DataFrame received, nothing to concatenate!")
            return [objs][0]

        return _concat([self] + objs, axis=axis, join=join,
                       ignore_index=ignore_index, keys=keys, levels=levels,
                       names=names, verify_integrity=verify_integrity,
                       sort=sort, copy=copy, squeeze=squeeze)

    def auto_append(self, switch: bool = None) -> None:
        if switch is not None:
            self._auto_append_ = bool(switch)
        logging.info("`auto_append` is", self._auto_append_)

    def copy(self, deep=True):
        return self._class(data=self.as_pandas().copy(deep=deep), **self.params_)

    def cumsum(self, skipna=True, *args, **kwargs):
        """
        Return cumulative sum over a SimDataFrame.

        Returns a SimDataFrame or SimSeries of the same size containing the cumulative sum.

        Parameters:
            axis : {0 or ‘index’, 1 or ‘columns’}, default 0
                The index or the name of the axis. 0 is equivalent to None or ‘index’.

        skipna: bool, default True
            Exclude NA/null values. If an entire row/column is NA, the result will be NA.

        *args, **kwargs
            Additional keywords have no effect but might be accepted for compatibility with NumPy.

        Returns
            SimSeries or SimDataFrame
            Return cumulative sum of Series or DataFrame.
        """
        return self._class(data=self.as_Pandas().cumsum(skipna=skipna, *args, **kwargs), **self.params_)

    def describe(self, *args, **kwargs):
        return self._class(data=self.to_Pandas().describe(*args, **kwargs),
                           **self.params_)

    def head(self, n=5):
        """
        Return the first n rows.

        This function returns first n rows from the object based on position. It is useful for quickly verifying data, for example, after sorting or appending rows.

        For negative values of n, this function returns all rows except the last n rows, equivalent to df[n:].

        Parameters:
        ----------
            n : int, default 5
            Number of rows to select.

        Returns
        -------
            type of caller
            The first n rows of the caller object.
        """
        return self._class(data=self.to_pandas().head(n), **self.params_)

    def operate_per_name(self, switch: bool = None) -> None:
        if switch is not None:
            self._operate_per_name_ = bool(switch)
        logging.info("`operate_per_name` is", self._operate_per_name_)

    @property
    def params_(self):
        return {'name': self.name,
                'units': self.get_units() if type(self.units) is dict else self.units,
                'index_name': self.index.name,
                'index_units': self.index_units if hasattr(self, 'index_units') else None,
                'name_separator': self.name_separator if hasattr(self, 'name_separator') else None,
                'intersection_character': self.intersection_character if hasattr(self,
                                                                                 'intersection_character') else '∩',
                'verbose': self.verbose if hasattr(self, 'verbose') else False,
                'auto_append': self._auto_append_ if hasattr(self, '_auto_append_') else \
                    self.auto_append if hasattr(self, 'auto_append') else False,  # option to cover old versions of SimSeries and SimDataFrames
                'operate_per_name': self._operate_per_name_ if hasattr(self, '_operate_per_name_') else \
                    self.operate_per_name if hasattr(self, 'operate_per_name') else False,  # option to cover old versions of SimSeries and SimDataFrames
                'transposed': self._transposed_ if hasattr(self, '_transposed_') else \
                    self.transposed if hasattr(self, 'transposed') else False,  # option to cover old versions of SimSeries and SimDataFrames
                'reverse': self._reverse_ if hasattr(self, '_reverse_') else \
                    self.reverse if hasattr(self, 'reverse') else False,  # option to cover old versions of SimSeries and SimDataFrames
                'meta': self.meta if hasattr(self, 'meta') else False,
                'source_path': self.source_path if hasattr(self, 'source_path') else None,
                }

    def tail(self, n=5):
        """
        Return the last n rows.

        This function returns last n rows from the object based on position. It is useful for quickly verifying data, for example, after sorting or appending rows.

        For negative values of n, this function returns all rows except the first n rows, equivalent to df[n:].

        Parameters:
        ----------
            n : int, default 5
            Number of rows to select.

        Returns
        -------
            type of caller
            The last n rows of the caller object.
        """
        return self._class(data=self.to_pandas().tail(n), **self.params_)

    def int(self):
        return self.astype(int)

    def inv(self):
        params_ = self.params_.copy()
        if type(self.units) is str:
            params_['units'] = _unit_inverse(self.units)
        elif type(self.units) is dict:
            params_['units'] = {k: _unit_inverse(self.units[k]) for k in self.units}
        return self._class(data=1/self.as_pandas(), **params_)

    def neg(self):
        return self.__neg__()

    def add(self, other, level=None, fill_value=None, axis=0, intersection_character=None):
        return self._arithmethic_operation(other, operation='+', level=level, fill_value=fill_value, axis=axis, intersection_character=intersection_character)

    def sub(self, other, level=None, fill_value=None, axis=0, intersection_character=None):
        return self._arithmethic_operation(other, operation='-', level=level, fill_value=fill_value, axis=axis, intersection_character=intersection_character)

    def mul(self, other, level=None, fill_value=None, axis=0, intersection_character=None):
        return self._arithmethic_operation(other, operation='*', level=level, fill_value=fill_value, axis=axis, intersection_character=intersection_character)

    def truediv(self, other, level=None, fill_value=None, axis=0, intersection_character=None):
        return self._arithmethic_operation(other, operation='/', level=level, fill_value=fill_value, axis=axis, intersection_character=intersection_character)

    def div(self, other, level=None, fill_value=None, axis=0, intersection_character=None):
        return self.truediv(other, level=level, fill_value=fill_value, axis=axis, intersection_character=intersection_character)

    def floordiv(self, other, level=None, fill_value=None, axis=0, intersection_character=None):
        return self._arithmethic_operation(other, operation='//', level=level, fill_value=fill_value, axis=axis, intersection_character=intersection_character)

    def mod(self, other, level=None, fill_value=None, axis=0, intersection_character=None):
        return self._arithmethic_operation(other, operation='%', level=level, fill_value=fill_value, axis=axis, intersection_character=intersection_character)

    def pow(self, other, level=None, fill_value=None, axis=0, intersection_character=None):
        return self._arithmethic_operation(other, operation='**', level=level, fill_value=fill_value, axis=axis, intersection_character=intersection_character)

    def __neg__(self):
        return self._class(data=self.as_pandas().__neg__(), **self.params_)

    def __abs__(self):
        return self._class(data=abs(self.as_pandas()), **self.params_)

    def __radd__(self, other):
        if is_Unit(other):
            if _convertible(self.units, other.units):
                return self.to(other.units)._reverse().__add__(other)
            else:
                raise NotImplementedError("Addition of SimSeries with not convertible Unyts is not implemented.")
        return self._reverse().__add__(other)

    def __rsub__(self, other):
        if is_Unit(other):
            if _convertible(self.units, other.units):
                return self.to(other.units).__neg__()._reverse().add(other, intersection_character='-')
            else:
                raise NotImplementedError("Subtraction of SimSeries with not convertible Unyts is not implemented.")
        return self.__neg__()._reverse().add(other, intersection_character='-')

    def __rmul__(self, other):
        if is_Unit(other):
            return self.to(other.units)._reverse().__mul__(other)
        else:
            return self._reverse().__mul__(other)

    def __rtruediv__(self, other):
        if is_Unit(other):
            return self.to(other.units).inv()._reverse().mul(other, intersection_character='/')
        else:
            return self.inv()._reverse().mul(other, intersection_character='/')

    def __rfloordiv__(self, other):
        if is_Unit(other):
            return self.to(other.units).inv()._reverse().mul(other, intersection_character='/').astype(int)
        else:
            return self.inv()._reverse().mul(other, intersection_character='/').astype(int)

    def __rmod__(self, other):
        params_ = self.params_.copy()
        if hasattr(other, 'name') and type(other.name) is str:
            params_['name'] = other.name
        if is_Unit(other):
            params_['units'] = other.units
            result = self.to(other.units).as_pandas().__rmod__(other.value)
            return self._class(data=result, **params_)
        else:
            params_['units'] = None
            return self._class(data=self.as_pandas().__rmod__(other), **params_)

    def __matmul__(self, other):
        if is_Unit(other):
            result = self.__truediv__(other.value)
            if other.units not in _unitless_names:
                if type(self.units) is str:
                    result.units = self.units + '/' + other.units
                elif type(self.units) is dict:
                    result.units = {k: (str(u) + '/' + other.units) for k, u in self.units.items()}
            return result
        else:
            return super().__matmul__(other)

    def __rmatmul__(self, other):
        if is_Unit(other):
            result = self.inv().__mul__(other.value)
            if other.units not in _unitless_names:
                if type(self.units) is str:
                    result.units = other.units + '/' + self.units
                elif type(self.units) is dict:
                    result.units = {k: (other.units + '/' + str(u)) for k, u in self.units.items()}
            return result
        else:
            return super().__rmatmul__(other)

    def avg(self, axis=0, **kwargs):
        return self.mean(axis=axis, **kwargs)

    def avg0(self, axis=0, **kwargs):
        return self.mean0(axis=axis, **kwargs)

    def average(self, axis=0, **kwargs):
        return self.mean(axis=axis, **kwargs)

    def average0(self, axis=0, **kwargs):
        return self.mean0(axis=axis, **kwargs)

    def mean0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).mean(axis=axis, **kwargs)

    def median0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).median(axis=axis, **kwargs)

    def mode0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).mode(axis=axis, **kwargs)

    def count0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).count(axis=axis, **kwargs)

    def min0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).min(axis=axis, **kwargs)

    def max0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).max(axis=axis, **kwargs)

    def prod0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).prod(axis=axis, **kwargs)

    def quantile0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).quantile(axis=axis, **kwargs)

    def rms0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).rms(axis=axis, **kwargs)

    def std0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).std(axis=axis, **kwargs)

    def sum0(self, axis=0, **kwargs):
        return self.sum(axis=axis, **kwargs)

    def var0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).var(axis=axis, **kwargs)

    def diff(self, periods=1, axis=0, forward=False):
        axis = _clean_axis(axis)
        if type(periods) is bool:
            periods, forward = 1, periods
        if axis == 0:
            if forward:
                return self._class(data=-1 * self.as_pandas().diff(periods=-1 * periods, axis=axis), **self.params_)
            else:
                return self._class(data=self.as_pandas().diff(periods=periods, axis=axis), **self.params_)
        if axis == 1:
            if len(set(self.get_units(self.columns).values())) == 1:
                units = list(set(self.get_units(self.columns).values()))[0]
            else:
                units = 'dimensionless'
            if forward:
                data = -1 * self.as_pandas().diff(periods=-1 * periods, axis=axis)
            else:
                data = self.as_pandas().diff(periods=periods, axis=axis)
            params_ = self.params_
            params_['units'] = units
            return self._class(data=data, **params_)

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

    def jitter(self, std=0.10):
        """
        add jitter the values of the SimSeries or SimDataFrame
        """
        return _jitter(self, std)

    def _extract_keys_initial(self, initial):
        if self.name_separator in [None, False, '']:
            raise ValueError("`.name_separator` must not be a not empty string.")
        if len(self.columns) == 1 and type(self.columns[0]) is not str:
            if type(self.name) is str:
                if self.name.split(self.name_separator)[0] == initial:
                    objs = [self.name.split(self.name_separator)[-1]]
                else:
                    objs = []
            else:
                objs = [each.split(self.name_separator)[-1] for each in self.index if
                        self.name_separator in each and each[0] == initial]
        else:
            objs = [each.split(self.name_separator)[-1] for each in self.columns if
                    self.name_separator in each and each[0] == initial]
        return list(set(objs))

    @property
    def wells(self):
        if self.name_separator in [None, '', False]:
            return []
        return self._extract_keys_initial('W')

    @property
    def groups(self):
        if self.name_separator in [None, '', False]:
            return []
        return self._extract_keys_initial('G')

    @property
    def regions(self):
        if self.name_separator in [None, '', False]:
            return []
        return self._extract_keys_initial('R')

    @property
    def attributes(self):
        if self.name_separator in [None, '', False]:
            return {col: [] for col in self.columns}
        atts = {}
        for each in list(self.columns):
            if type(each) is str and self.name_separator in each:
                if each.split(self.name_separator)[0] in atts:
                    atts[each.split(self.name_separator)[0]].append(each.split(self.name_separator)[-1])
                else:
                    atts[each.split(self.name_separator)[0]] = [each.split(self.name_separator)[-1]]
            else:
                if each not in atts:
                    atts[each] = []
        atts = {att: list(set(atts[att])) for att in atts}
        return atts

    @property
    def properties(self):
        if len(self.attributes.keys()) > 0:
            return list(self.attributes.keys())
        else:
            return []

    def set_name_separator(self, separator):
        if type(separator) is str and len(separator) > 0:
            if separator in '=-+&*/!%':
                logging.warning(
                    "The separator '" + separator + "' could be confused with operators.\n it is recommended to use ':' as separator.")
            self.name_separator = separator
        else:
            raise TypeError("The `separator` must be a string.")

    def get_name_separator(self):
        if self.name_separator in [None, '', False]:
            warn("`name_separator` is not defined.")
            return ''
        else:
            return self.name_separator

    def interpolate(self, method='slinear', axis='index', limit=None, inplace=False,
                    limit_direction=None, limit_area=None, downcast=None, **kwargs):
        axis = _clean_axis(axis)
        if inplace:
            super().interpolate(method=method, axis=axis, limit=limit, inplace=inplace, limit_direction=limit_direction,
                                limit_area=limit_area, downcast=downcast, **kwargs)
        else:
            return self._class(data=self.as_pandas().interpolate(method=method, axis=axis, limit=limit, inplace=inplace,
                                                         limit_direction=limit_direction, limit_area=limit_area,
                                                         downcast=downcast, **kwargs), **self.params_)

    def fillna(self, value=None, method=None, axis='index', inplace=False,
               limit=None, downcast=None):
        axis = _clean_axis(axis)
        if inplace:
            super().fillna(value=value, method=method, axis=axis, inplace=inplace, limit=limit, downcast=downcast)
        else:
            return self._class(data=self.as_pandas().fillna(value=value, method=method, axis=axis, inplace=inplace, limit=limit,
                                                    downcast=downcast), **self.params_)

    def replace(self, to_replace=None, value=None, inplace=False, limit=None, regex=False, method='pad'):
        if inplace:
            super().replace(to_replace=to_replace, value=value, inplace=inplace, limit=limit, regex=regex,
                            method=method)
        else:
            return self._class(
                data=self.as_pandas().replace(to_replace=to_replace, value=value, inplace=inplace, limit=limit, regex=regex,
                                     method=method), **self.params_)

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
    def ss(self):
        return self.to_simseries()

    @property
    def SS(self):
        return self.to_simseries()

    @property
    def SimDataFrame(self):
        return self.as_simdataframe()

    @property
    def sdf(self):
        return self.as_simdataframe()

    @property
    def SDF(self):
        return self.as_simdataframe()

    def zeros(self, axis=None, value=0):
        """
        Finds the columns or rows where all its values are equal to `value` (by default is 0).
        Returns a Series with bool indicating True at the columns or rows that match the condition.

        Parameters
        ----------
        axis = int or str
            0 for rows,
            1 for columns

        Returns
        -------
            Series
        """
        axis = 1 if axis is None and len(self.columns) == 1 else 0
        axis = _clean_axis(axis)
        if axis == 2:
            return self.zeros(axis=0, value=value) + self.zero(axis=1, value=value)
        limit = len(self) if axis == 0 else len(self.columns)
        return (self==value).sum(axis=axis) == limit

    def dropzeros(self, axis=None):
        """
        alias for .drop_zeros() method
        """
        return self.drop_zeros(axis=axis)

    def dropZeros(self, axis=None):
        """
        alias for .drop_zeros() method
        """
        return self.drop_zeros(axis=axis)

    def aggregate(self, func=None, axis=0, *args, **kwargs):
        axis = _clean_axis(axis)
        return self._class(data=self.to_pandas().aggregate(func=func, axis=axis, *args, **kwargs), **self.params_)

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
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
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

    @property
    def right(self):
        return list(set(_right(self, self.name_separator).values()))

    @property
    def left(self):
        return list(set(_left(self, self.name_separator).values()))

    def rename_right(self, inplace=False):
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        if self.name_separator in [None, '', False]:
            warn("`name_separator` is not defined. Set it using `.set_name_separator('string')`")
            return self
        new_names = _right(self, self.name_separator)
        if self._class is SimDataFrame:
            if len(set(new_names.keys())) != len(set(new_names.values())):
                new_names = dict(zip(new_names.keys(), new_names.keys()))
        elif self._class is SimSeries:
            if len(self.columns) == 1:
                new_names = list(new_names.values())[0]
        if inplace:
            self.rename(columns=new_names, inplace=True)
        else:
            return self.rename(columns=new_names, inplace=False)

    def rename_left(self, inplace=False):
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        if self.name_separator in [None, '', False]:
            warn("`name_separator` is not defined. Set it using `.set_name_separator('string')`")
            return self
        new_names = _left(self, self.name_separator)
        if self._class is SimDataFrame:
            if len(set(new_names.keys())) != len(set(new_names.values())):
                new_names = dict(zip(new_names.keys(), new_names.keys()))
        elif self._class is SimSeries:
            if len(self.columns) == 1:
                new_names = list(new_names.values())[0]
        if inplace:
            self.rename(columns=new_names, inplace=True)
        else:
            return self.rename(columns=new_names, inplace=False)

    def renameRight(self, inplace=False):
        return self.rename_right(inplace=inplace)

    def renameLeft(self, inplace=False):
        return self.rename_left(inplace=inplace)

    def _common_rename(self, other,
                      intersection_character=None,
                      other_name_separator=None,
                      complex_names=False,
                      **kwargs):
        if intersection_character is None:
            intersection_character = self.intersection_character
        if hasattr(other, 'name_separator') and other.name_separator is not None:
            other_name_separator = other.name_separator
        elif other_name_separator is None:
            other_name_separator = self.name_separator
            logging.warning("'other' does not have `.name_separator` attribute or it is defined as None, my `.name_separator` will be used: '" + str(self.name_separator) + "'.")
        if self._reverse_:
            return _common_rename(other, self,
                                  intersection_character=intersection_character,
                                  name_separator_2=other_name_separator,
                                  complex_names=complex_names,
                                  **kwargs)
        else:
            return _common_rename(self, other,
                                  intersection_character=intersection_character,
                                  name_separator_2=other_name_separator,
                                  complex_names=complex_names,
                                  **kwargs)

    def _joined_index(self, other, *, drop_duplicates=False, keep='first'):
        from .common.merger import merge_index
        return merge_index(self, other, how='outer', drop_duplicates=drop_duplicates, keep=keep)

    def _common_index(self, other, *, drop_duplicates=True, keep='first'):
        from .common.merger import merge_index
        return merge_index(self, other, how='inner', drop_duplicates=drop_duplicates, keep=keep)

    def _merge_index(self, other, how='outer', *, drop_duplicates=True, keep='first'):
        from .common.merger import merge_index
        return merge_index(self, other, how=how, drop_duplicates=drop_duplicates, keep=keep)

    def merge(self, right, how='inner', on=None, left_on=None, right_on=None, left_index=None, right_index=None,
              sort=False, suffixes=('_x', '_y'), copy=True, indicator=False, validate=None):
        from .common.merger import merge as _merge
        if on is None and left_on is None and right_on is None and right_index is None and left_index is None:
            left_index, right_index = True, True
        return _merge(self, right, how='inner', on=on, left_on=left_on, right_on=right_on, left_index=left_index,
                      right_index=right_index, sort=sort, suffixes=suffixes, copy=copy, indicator=indicator,
                      validate=validate)

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
        return self._class(data=self.as_pandas().shift(periods=periods, freq=freq, axis=axis, fill_value=fill_value),
                           **self.params_)

    def to(self, units):
        """
        returns the dataframe converted to the requested units if possible, if not, returns the original values.
        """
        return self.convert(units)

    def index_to(self, units):
        """
        returns the dataframe with the index converted to the requested units if possible, if not, returns the original values.
        """
        if _convertible(self.index_units, units):
            params_ = self.params_.copy()
            params_['index_name'] = self.index_name if self.index.name is None else self.index.name
            params_['index_units'] = units
            if self.index.name in params_['units']:
                params_['units'][self.index.name] = units
            data = self.as_pandas().copy()
            data.index = self.index.to(units)
            return self._class(data=data, **params_)
        else:
            return self

    def like(self, units):
        """
        returns the dataframe replacing its units by the requested `units`.
        NO CONVERSION IS APPLIED!
        """
        result = self.copy()
        result.set_units(units)
        return result

    @property
    def index_name(self):
        return self.index.name

    @index_name.setter
    def index_name(self, name):
        self.set_index_name(name)

    @property
    def index_units(self):
        return self.get_index_units()

    @index_units.setter
    def index_units(self, units):
        return self.set_index_units(units)

    def set_index_name(self, name):
        if type(name) is str and len(name.strip()) > 0:
            self.index.name = name.strip()
        elif name is None:
            logging.warning("The index_name has been set to `None`.")
        elif name == '':
            logging.warning("The index_name has been set to an empty string.")
        else:
            try:
                self.index.name = name
            except:
                raise ValueError("Not valid index name.")

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

    def days_in_year(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an array of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        params_ = self.params_
        params_['index'] = self.index
        params_['name'] = 'days_in_year'
        if type(params_['units']) is dict:
            params_['units']['days_in_year'] = 'days'
        else:
            params_['units'] = 'days'
        if column is not None:
            if type(column) is str and column in self.columns:
                if self[column].dtype in ('int', 'int64') and self[column].min() > 0:
                    params_['name'] = 'days_in_year'
                    params_['units'] = 'days'
                    return SimSeries(data=days_in_year(self[column].to_numpy()), **params_)
                elif 'datetime' in str(self[column].dtype):
                    return days_in_year(self[column])
                else:
                    raise ValueError('selected column is not a valid date or year integer')
            elif type(column) is str and column not in self.columns:
                raise ValueError('the selected column is not in this SimDataFrame')
            elif type(column) is not str and hasattr(column, '__iter__'):
                result = SimDataFrame(data={}, index=self.index, **self.params_)
                for col in column:
                    if col in self.columns:
                        result[col] = days_in_year(self[col])
                        result.set_units('days', col)
                return result
        else:
            params_['name'] = 'days_in_year'
            params_['index'] = self.index
            params_['index_units'] = self.index_units
            params_['units'] = 'days'
            if self.index.dtype in ('int', 'int64') and self.index.min() > 0:
                return SimSeries(data=list(days_in_year(self.index.to_numpy())), **params_)
            elif 'datetime' in str(self.index.dtype):
                return SimSeries(data=list(days_in_year(self.index)), **params_)
            else:
                raise ValueError('index is not a valid date or year integer')

    def real_year(self, column=None):
        """
        returns a SimSeries with the year and cumulative days as fraction

        Parameters
        ----------
        column : str
            The selected column must be a datetime array.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        params_ = self.params_
        params_['index'] = self.index
        params_['name'] = 'realYear'
        params_['units'] = 'Years'
        if column is not None:
            if type(column) is str and column in self.columns:
                if 'datetime' in str(self[column].dtype):
                    return SimSeries(data=real_year(self[column]), **params_)
                else:
                    raise ValueError('selected column is not a valid date format')
            elif type(column) is str and column not in self.columns:
                raise ValueError('the selected column is not in this SimDataFrame')
            elif type(column) is not str and hasattr(column, '__iter__'):
                result = SimDataFrame(data={}, index=self.index, **self.params_)
                for col in column:
                    if col in self.columns:
                        result[col] = real_year(self[col])
                return result
        else:
            if 'datetime' in str(self.index.dtype):
                return SimSeries(data=list(real_year(self.index)), **params_)
            else:
                raise ValueError('index is not a valid date or year integer')

    # function alias
    def daysInYear(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an array of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.days_in_year(column=column)

    def daysinyear(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an array of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.days_in_year(column=column)

    def DaysInYear(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an array of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.days_in_year(column=column)

    def realYear(self, column=None):
        """
        returns a SimSeries with the year and cumulative days as fraction

        Parameters
        ----------
        column : str
            The selected column must be a datetime array.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.real_year(column=column)

    def realyear(self, column=None):
        """
        returns a SimSeries with the year and cumulative days as fraction

        Parameters
        ----------
        column : str
            The selected column must be a datetime array.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.real_year(column=column)

    def RealYear(self, column=None):
        """
        returns a SimSeries with the year and cumulative days as fraction

        Parameters
        ----------
        column : str
            The selected column must be a datetime array.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.real_year(column=column)

    def _check_by(self, by, raise_by_error=True):
        # if not isinstance(self.index, pd.DatetimeIndex):
        #     original = self.index
        #     try:
        #         self.index = pd.to_datetime(['-'.join(map(str, i)) for i in self.index])
        #     except:
        #         if raise_by_error:
        #             raise TypeError("index must be `DatetimeIndex`.")
        #         else:
        #             logging.warning("index must be `DatetimeIndex`.")
        # else:
        #     original = None

        if by is None:
            by = []
        elif type(by) is not str and hasattr(by, '__iter__'):
            new_by = []
            for each in by:
                if not hashable(each):
                    each = tuple(each)
                if each in self.columns:
                    new_by.append(each)
                elif isinstance(self.index, pd.DatetimeIndex) and each in [self.index.year, self.index.month, self.index.day]:
                    new_by.append(each)
                elif isinstance(self.index, pd.MultiIndex) and each in [self.index.get_level_values(i) for i in range(len(self.index.levels))] + list(self.index.levels):
                    new_by.append(each)
                elif raise_by_error:
                    raise ValueError("The column '" + str(each) + "' is not present in this frame")
                else:
                    logging.warning("The column '" + str(by) + "' is not present in this frame")
            by = new_by
        elif by in self.columns:
            by = [by]
        elif raise_by_error:
            raise ValueError("The column '" + str(by) + "' is not present in this frame")
        else:
            by = []
            logging.warning("The column '" + str(by) + "' is not present in this frame")
        user_by = by if len(by) > 0 else None

        # if original is not None:
        #     self.index = original
        return by, user_by

    def _aggregated_calculation(self, by, agg):
        result = self.as_pandas().groupby(by=by)
        params_ = self.params_.copy()
        if agg == 'first':
            result = result.first()
        elif agg == 'last':
            result = result.last()
        elif agg == 'max':
            result = result.max()
        elif agg == 'min':
            result = result.min()
        elif agg in ['mean', 'avg']:
            result = result.mean()
        elif agg == 'median':
            result = result.median()
        elif agg == 'std':
            result = result.std()
        elif agg == 'sum':
            result = result.sum()
        elif agg == 'count':
            result = result.count()
        elif agg[:3] == 'int':  # from 'integrate', 'integral'
            result = self.integrate()
            #params_['units'] = result.get_units()
        elif agg[:3] == 'rep':  # from 'representative'
            result = self.integrate()
            result = result.as_pandas().groupby(by=by)  # self.index.year
            index = pd.DataFrame(data=self.index, index=self.index).groupby(by=by)  # self.index.year
            index = np.append(index.first().to_numpy(), index.last().to_numpy()[-1])
            delta_index = np.diff(index)
            if isinstance(self.index, pd.DatetimeIndex):
                delta_index = delta_index.astype('timedelta64[s]').astype('float64') / 60 / 60 / 24
            values = result.first().append(result.last().iloc[-1])
            delta_values = np.diff(values.transpose())
            result = pd.DataFrame(data=(delta_values / delta_index).transpose(), index=result.first().index,
                               columns=self.columns)
            #params_['units'] = result.get_units()
        elif agg in ['cum', 'cumulative']:
            result = self.cumsum()
        else:
            raise ValueError("`agg` parameter is not valid.")
        return self._class(data=result, **params_)

    def _fill_daily(self, group_by=None, fillna_method=False, raise_by_error=True, **kwargs):
        """
        Fill the gaps in DateTimeIndex, completing the missing days in the index and populating the missing values if requiered.

        Returns
        -------

        """
        result = self.copy()

        # if not isinstance(result.index, pd.DatetimeIndex):
        #     if len(result.index) > 0 and len(result.index[0]) == 3:
        #         try:
        #             result.index = pd.to_datetime(['-'.join(map(str,i)) for i in result.index])
        #         except:
        #             raise TypeError("Index must be DateTimeIndex.")
        #     else:
        #         raise TypeError("Index must be DateTimeIndex.")

        # time_by = [result.index.year, result.index.month, result.index.day]
        # group_by, _ = result._check_by(group_by, raise_by_error=raise_by_error)
        # for tb in time_by:
        #     try:
        #         if tb in group_by:
        #             _ = group_by.remove(tb)
        #     except ValueError:
        #         if tuple(tb) in [tuple(g) for g in group_by]:
        #             _ = group_by.remove(tuple(tb))
                    
        # by = time_by if group_by is None else time_by + group_by

        by = group_by

        if len(by) > 3:  # user criteria to group by
            index_backup = pd.MultiIndex.from_tuples([(int(i[0]), int(i[1]), int(i[2])) for i in self.index])
            result.index.names = by[3:]
            result.index = pd.MultiIndex.from_tuples([tuple(i[3:]) for i in result.index]) if len(by) > 4 else [i[3] for i in result.index]
            result = result.reset_index()
        else:
            index_backup = result.index

        result.index = pd.to_datetime(['-'.join(map(str,i)) for i in index_backup])
        result.index.name = 'DATE'
        if len(by) == 4:
            new_df = None
            for group in result[by[3]].unique():
                group_df = result[result[by[3]] == group]
                if len(group_df) == 0:
                    continue
                daily_index = pd.date_range(min(group_df.index), max(group_df.index), freq='D')
                group_df = group_df.reindex(index=daily_index)

                if fillna_method is False:
                    pass
                elif fillna_method is None:
                    group_df = group_df.interpolate(method='time').fillna(method='pad')
                elif fillna_method in ['pad', 'ffill', 'backfill', 'bfill']:
                    group_df = group_df.fillna(method=fillna_method)
                elif fillna_method in ['linear', 'time', 'index', 'values', 'nearest',
                                       'zero', 'slinear', 'quadratic', 'cubic', 'barycentric']:
                    group_df = group_df.interpolate(method=fillna_method).fillna(method='pad')
                elif fillna_method in ['polynomial', 'spline']:
                    group_df = group_df.interpolate(method=fillna_method, order=kwargs['order']).fillna(method='pad')
                if new_df is None:
                    new_df = group_df.copy()
                else:
                    new_df = new_df.append(group_df)
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
            raise NotImplementedError('Not able to reindex grouping by more than one column.')

        by = [result.index.year, result.index.month, result.index.day] + by[3:]
        result = result.groupby(by=by).first()
        return result

    def _fill_timely(self, group_by=None, fillna_method=False, raise_by_error=True, freq=None, **kwargs):
        """
        Fill the gaps in DateTimeIndex, completing the missing days in the index and populating the missing values if requiered.

        Returns
        -------

        """
        if freq is None:
            raise ValueError('`freq` parameter must not be None.')

        result = self.copy()

        by = group_by

        if len(by) > 3:  # user criteria to group by
            index_backup = pd.MultiIndex.from_tuples([(int(i[0]), int(i[1]), int(i[2])) for i in self.index])
            result.index.names = by[3:]
            result.index = pd.MultiIndex.from_tuples([tuple(i[3:]) for i in result.index]) if len(by) > 4 else [i[3] for
                                                                                                                i in
                                                                                                                result.index]
            result = result.reset_index()
        else:
            index_backup = result.index

        result.index = pd.to_datetime(['-'.join(map(str, i)) for i in index_backup])
        result.index.name = 'DATE'
        if len(by) == 4:
            new_df = None
            for group in result[by[3]].unique():
                group_df = result[result[by[3]] == group]
                if len(group_df) == 0:
                    continue
                new_index = pd.date_range(min(group_df.index), max(group_df.index), freq=freq)
                group_df = group_df.reindex(index=new_index)

                if fillna_method is False:
                    pass
                elif fillna_method is None:
                    group_df = group_df.interpolate(method='time').fillna(method='pad')
                elif fillna_method in ['pad', 'ffill', 'backfill', 'bfill']:
                    group_df = group_df.fillna(method=fillna_method)
                elif fillna_method in ['linear', 'time', 'index', 'values', 'nearest',
                                       'zero', 'slinear', 'quadratic', 'cubic', 'barycentric']:
                    group_df = group_df.interpolate(method=fillna_method).fillna(method='pad')
                elif fillna_method in ['polynomial', 'spline']:
                    group_df = group_df.interpolate(method=fillna_method, order=kwargs['order']).fillna(method='pad')
                if new_df is None:
                    new_df = group_df.copy()
                else:
                    new_df = new_df.append(group_df)
        elif len(by) == 3:
            new_index = pd.date_range(min(result.index), max(result.index), freq=freq)
            result = result.reindex(index=new_index)
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
            raise NotImplementedError('Not able to reindex grouping by more than one column.')

        by = [result.index.year, result.index.month, result.index.day] + by[3:]
        result = result.groupby(by=by).first()
        return result

    def _make_day(self, day: str, MM:int, YYYY: int) -> str:
        if day not in ['-first', '-last', '-max', '-mid']:
            if int(day.strip('-')) >= 1 and int(day.strip('-')) <= 28:
                return day
            if int(day.strip('-')) <= 0:
                return '-01'
            last_day_of_month = days_in_month(MM, YYYY)
            if int(day.strip('-')) <= last_day_of_month:
                return day
            else:
                return '-' + str(last_day_of_month)
        if day == '-first':
            return '-' + str(self.index.where((self.index.year == YYYY) & (self.index.month == MM)).min().day).zfill(2)
        elif day ==  '-last':
            return '-' + str(self.index.where((self.index.year == YYYY) & (self.index.month == MM)).max().day).zfill(2)
        elif day == '-max':
            return '-' + str(days_in_month(MM, YYYY))
        elif day == '-mid':
            return '-14' if MM == 2 else '-15'

    def _make_month(self, month: str, YYYY: int) -> str:
        if month not in ['-first', '-last', '-max', '-mid']:
            if int(month.strip('-')) >= 1 and int(month.strip('-')) <= 12:
                return month
            if int(month.strip('-')) <= 0:
                return '-01'
            else:  # int(month.strip('-')) > 12
                return '-12'
        if month == '-first':
            return '-' + str(self.index.where(self.index.year == YYYY).min().month).zfill(2)
        elif month ==  '-last':
            return '-' + str(self.index.where(self.index.year == YYYY).max().month).zfill(2)
        elif month == '-max':
            return '-12'
        elif month == '-mid':
            return '-07'

    def _make_month_day(self, day: str, month: str, YYYY: int) -> str:
        MM = self._make_month(month, YYYY)
        DD = '-01' if month == '-mid' else self._make_day(day, int(MM[1:]), YYYY)
        return MM + DD

    def daily(self, agg='mean', datetime_index=True, by=None,
              complete_index=False, fillna_method=None, raise_by_error=True, **kwargs):
        """
        return a dataframe with a single row per day.
        index must be a date type.

        available gropuing calculations are:
            first : keeps the fisrt row per day
            last : keeps the last row per day
            max : returns the maximum value per day
            min : returns the minimum value per day
            mean or avg : returns the average value per day
            median : returns the median value per day
            std : returns the standard deviation per day
            sum : returns the summation of all the values per day
            count : returns the number of rows per day
            integrate : calculates the numerical integration per day, over the index (a datetime-index)
            representative : calculates the representative mean per day, as the numerical integration of the column over the index (a datetime-index) then divided by the elapsed time between the first and las row of each day
            cumsum or cumulative : run cumsum per day, over the columns and then return the last value of each year

        datetime_index : bool
            if True the index will converted to DateTimeIndex
            if False the index will be a MultiIndex (Year, Month, Day)

        by : label or list of labels, optional.
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
            This behavior can be changed by setting the `fillna_method` parameter.

        fillna_method : str or False, optional. Default is False
            Ignored if `complete_index` is False
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
        if not isinstance(self.index, pd.DatetimeIndex):
            raise TypeError('index must be of datetime type.')

        if fillna_method in ['polynomial', 'spline']:
            if 'order' not in kwargs:
                raise ValueError(
                    "The '" + fillna_method + "' fillna_method requieres one additional parameter 'order':\n   df.daily(fillna_method='polynomial', order=5)")
            if type(kwargs['order']) is not int:
                raise ValueError(
                    "The 'order' parameter must be an integer:\n   df.daily(fillna_method='polynomial', order=5)")

        if type(agg) is bool and type(datetime_index) is not bool:
            agg, datetime_index = datetime_index, agg
        elif type(agg) is bool and datetime_index is True:
            agg, datetime_index = 'mean', agg

        raise_by_error = bool(raise_by_error)

        by, user_by = self._check_by(by, raise_by_error=raise_by_error)
        by = [self.index.year, self.index.month, self.index.day] + by

        output = self._aggregated_calculation(by, agg)

        if complete_index:
            output = output._fill_daily(group_by=by, fillna_method=fillna_method, raise_by_error=raise_by_error)

        if user_by is None:
            output.index = pd.MultiIndex.from_tuples([(int(y), int(m), int(d)) for y, m, d in output.index])
        elif len(user_by) == 1:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]), int(i[1]), int(i[2]), i[3]) for i in output.index])
        else:
            output.index = pd.MultiIndex.from_tuples(
                [(int(i[0]), int(i[1]), int(i[2]),) + tuple(i[3:]) for i in output.index])

        if datetime_index:
            if user_by is None:
                output.index = pd.to_datetime(
                    [str(YYYY) + '-' + str(MM).zfill(2) + '-' + str(DD).zfill(2) for YYYY, MM, DD in output.index])
                output.index.names = ['DATE']
                output.index.name = 'DATE'
                if 'DATE' not in output.get_units():
                    output.set_units('date', 'DATE')
            elif len(user_by) == 1:
                output.index = pd.MultiIndex.from_tuples(
                    [(pd.to_datetime(str(i[0]) + '-' + str(i[1]).zfill(2) + '-' + str(i[2]).zfill(2)), i[3]) for i in
                     output.index])
            else:
                output.index = pd.MultiIndex.from_tuples(
                    [(pd.to_datetime(str(i[0]) + '-' + str(i[1]).zfill(2) + '-' + str(i[2]).zfill(2)),) + tuple(i[3:])
                     for i in output.index])
            if user_by is not None:
                output.index.names = ['DATE'] + user_by
                output.index.name = 'DATE' + '_' + '_'.join(map(str, user_by))
        elif user_by is None:
            output.index.names = ['YEAR', 'MONTH', 'DAY']
            output.index.name = 'YEAR_MONTH_DAY'
        else:
            output.index.names = ['YEAR', 'MONTH', 'DAY'] + user_by
            output.index.name = 'YEAR_MONTH_DAY' + '_' + '_'.join(map(str, user_by))

        if not datetime_index:
            if 'YEAR' not in output.get_units():
                output.set_units('year', 'YEAR')
            if 'MONTH' not in output.get_units():
                output.set_units('month', 'MONTH')
            if 'DAY' not in output.get_units():
                output.set_units('day', 'DAY')

        return output

    def monthly(self, agg='mean', datetime_index=False, by=None, day=None,
                complete_index=False, fillna_method=None, raise_by_error=True):
        """
        Return a dataframe with a single row per month.
        index must be a date type.

        available gropuing aggregations are:
            first : keeps the fisrt row per month
            last : keeps the last row per month
            max : returns the maximum value per month
            min : returns the minimum value per month
            mean or avg : returns the average value per month
            median : returns the median value per month
            std : returns the standard deviation per month
            sum : returns the summation of all the values per month
            count : returns the number of rows per month
            integrate : calculates the numerical integration per month, over the index (a datetime-index)
            representative : calculates the representative mean per month, as the numerical integration of the column over the index (a datetime-index) then divided by the elapsed time between the first and last rows of each month
            cumsum or cumulative : run cumsum per month, over the columns and then return the last value of each year
            date : keep the value at the exact day and month requested by `day` and `month`

        datetimeIndex : bool
            if True the index will converted to DateTimeIndex with Day=`day` for each month
            if False the index will be a MultiIndex (Year, Month)

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
            If string 'first' the first day in the data for the month will be used.
            If string 'last' the last day in the data for each month will be used.
            If string 'max' the number of days of each month will be used (28, 29, 30 or 31).
            Setting a not None `day` parameter will turn datetimeIndex True.

        complete_index : bool, optional. Default False
            Will reindex the dataframe to new index containing every day between
            the first and the last dates in the input index.
            If set to True, by default will autocomplete the null values using
            linear interpolation considering the length of time intervals from
            the index.
            This behavior can be changed by setting the `fillna_method` parameter.

        fillna_method : str or False, optional. Default is `time` first filling remaining NaN with `pad`.
            Ignored if `complete_index` is False
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
                    df.monthly(fillna_method='polynomial', order=5).

        """
        if not isinstance(self.index, pd.DatetimeIndex):
            raise TypeError('index must be of datetime type.')

        if type(agg) is int and day is None:
            agg, day = 'mean', agg

        if type(agg) is bool and type(datetime_index) is not bool:
            if type(datetime_index) is str:
                agg, datetime_index = datetime_index, agg
            if type(datetime_index) is int:
                agg, datetime_index, day = 'mean', True, datetime_index
        elif type(agg) is bool and datetime_index is False:
            agg, datetime_index = 'mean', agg

        if type(datetime_index) is not bool:
            if day is None:
                day = datetime_index
            datetime_index = True

        if day is not None:
            datetime_index = True

        if complete_index:
            output = self.daily(agg=agg, datetime_index=True, by=by,
                       complete_index=True, fillna_method=fillna_method, raise_by_error=raise_by_error)
        else:
            output = self

        day = check_day(day)
        by, user_by = output._check_by(by, raise_by_error=bool(raise_by_error))
        by = [output.index.year, output.index.month] + by

        output = output._aggregated_calculation(by, agg)

        if user_by is None:
            output.index = pd.MultiIndex.from_tuples([(int(y), int(m)) for y, m in output.index])
        elif len(user_by) == 1:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]), int(i[1]), i[2]) for i in output.index])
        else:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]), int(i[1]),) + tuple(i[2:]) for i in output.index])

        if datetime_index:
            if user_by is None:
                output.index = pd.to_datetime(
                    [str(YYYY) + '-' +
                     str(MM).zfill(2) +
                     self._make_day(day, MM, YYYY)
                     for YYYY, MM in output.index])
                output.index.names = ['DATE']
                output.index.name = 'DATE'
                if 'DATE' not in output.get_units():
                    output.set_units('date', 'DATE')
            elif len(user_by) == 1:
                output.index = pd.MultiIndex.from_tuples([
                    (pd.to_datetime(
                        str(i[0]) + '-' +
                        str(i[1]).zfill(2) +
                        self._make_day(day, i[1], i[0])
                    ), i[2],)
                    for i in output.index])
            else:
                output.index = pd.MultiIndex.from_tuples([
                    (pd.to_datetime(
                        str(i[0]) + '-' +
                        str(i[1]).zfill(2) +
                        self._make_day(day, i[1], i[0])),
                    ) + tuple(i[2:])
                    for i in output.index])
            if user_by is not None:
                output.index.names = ['DATE'] + user_by
                output.index.name = 'DATE' + '_' + '_'.join(map(str, user_by))
        elif user_by is None:
            output.index.names = ['YEAR', 'MONTH']
            output.index.name = 'YEAR_MONTH'
        else:
            output.index.names = ['YEAR', 'MONTH'] + user_by
            output.index.name = 'YEAR_MONTH' + '_' + '_'.join(map(str, user_by))
        if not datetime_index:
            if 'YEAR' not in output.get_units():
                output.set_units('year', 'YEAR')
            if 'MONTH' not in output.get_units():
                output.set_units('month', 'MONTH')
        return output

    def yearly(self, agg='mean', datetime_index=False, by=None, day=None, month=None,
               complete_index=False, fillna_method=None, raise_by_error=True):
        """
        return a dataframe with a single row per year.
        index must be a date type.

        available gropuing aggregations are:
            first : keeps the fisrt row
            last : keeps the last row
            max : returns the maximum value per year
            min : returns the minimum value per year
            mean or avg : returns the average value per year
            median : returns the median value per year
            std : returns the standard deviation per year
            sum : returns the summation of all the values per year
            count : returns the number of rows per year
            integrate : calculates the numerical integration per year, over the index (a datetime-index)
            representative : calculates the representative mean per year, as the numerical integration of the column over the index (a datetime-index) then divided by the elapsed time between the first and last row of each year
            cumsum or cumulative : run cumsum per year, over the columns and then return the last value of each year
            date : keep the value at the exact day and month requested by `day` and `month`

        datetime_index : bool, optional
            if True the index will converted to DateTimeIndex with Day=`day` and Month=`month` for each year
            if False the index will be a integer (Year)

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

        complete_index : bool, optional. Default False
            Will reindex the dataframe to new index containing every day between
            the first and the last dates in the input index.
            If set to True, by default will autocomplete the null values using
            linear interpolation considering the length of time intervals from
            the index.
            This behavior can be changed by setting the `fillna_method` parameter.

        fillna_method : str or False, optional. Default is `time` first filling remaining NaN with `pad`.
            Ignored if `complete_index` is False
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
                    df.yearly(fillna_method='polynomial', order=5).

        """
        if not isinstance(self.index, pd.DatetimeIndex):
            raise TypeError('index must be of datetime type.')

        if type(agg) is int and month is None:
            agg, month = 'mean', agg

        if type(agg) is bool and type(datetime_index) is not bool:
            if type(datetime_index) is str:
                agg, datetime_index = datetime_index, agg
            if type(datetime_index) is int:
                agg, datetime_index, month = 'mean', True, datetime_index
        elif type(agg) is bool and datetime_index is False:
            agg, datetime_index = 'mean', agg

        if type(datetime_index) is not bool:
            if day is None:
                day = datetime_index
            if month is None:
                month = datetime_index
            datetime_index = True

        if day is not None and month is None:
            month = day
        if month is not None:
            datetime_index = True
            if day is None and type(month) is str and not month.isdigit():
                day = month

        if complete_index:
            output = self.daily(agg=agg, datetime_index=True, by=by,
                       complete_index=True, fillna_method=fillna_method, raise_by_error=raise_by_error)
        else:
            output = self

        day = check_day(day)
        month = check_month(month)
        by, user_by = output._check_by(by, raise_by_error=bool(raise_by_error))
        by = [output.index.year] + by
        if len(by) == 1:
            by = by[0]

        output = output._aggregated_calculation(by, agg)

        if user_by is None:
            output.index = [int(y) for y in output.index]
        elif len(user_by) == 1:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]), i[1]) for i in output.index])
        else:
            output.index = pd.MultiIndex.from_tuples([(int(i[0]),) + tuple(i[1:]) for i in output.index])

        if datetime_index:
            if user_by is None:
                output.index = pd.to_datetime([str(YYYY) +
                                               self._make_month_day(day, month, YYYY)
                                               for YYYY in output.index])
                output.index.names = ['DATE']
                output.index.name = 'DATE'
                if 'DATE' not in output.get_units():
                    output.set_units('date', 'DATE')
            elif len(user_by) == 1:
                output.index = pd.MultiIndex.from_tuples([(pd.to_datetime(
                    str(i[0]) + self._make_month_day(day, month, i[0])), i[1],)
                    for i in output.index])
            else:
                output.index = pd.MultiIndex.from_tuples([(pd.to_datetime(
                    str(i[0]) + self._make_month_day(day, month, i[0])),) + tuple(
                    i[1:]) for i in output.index])
            if user_by is not None:
                output.index.names = ['DATE'] + user_by
                output.index.name = 'DATE' + '_' + '_'.join(map(str, user_by))
        elif user_by is None:
            output.index.names = ['YEAR']
            output.index.name = 'YEAR'
        else:
            output.index.names = ['YEAR', ] + user_by
            output.index.name = 'YEAR' + '_' + '_'.join(map(str, user_by))
        if not datetime_index:
            output.set_units('year', 'YEAR')
            output.index_units = 'year'
        return output

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
                                         index must be a DatetimeIndex
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
        method = method.lower().strip()

        sl1 = slice(0, -1)
        sl2 = slice(1, len(self))

        if method[0] == 't':
            pass
        elif method[0] in 'ac':
            if at is None:
                at = 'next'
            elif str(at).lower().strip() not in ['same', 'next']:
                raise ValueError("parameter 'at' must be 'same' or 'next'.")
            else:
                at = str(at).lower().strip()
        elif method[0] in 'my':
            pass
        else:
            raise ValueError("'method' parameter must be 'trapz' or 'const'")

        if len(self) < 2:
            warn("less than two rows, nothing to integrate.")
            return self

        if method[0] in 'tac':
            dt = np.diff(self.index)
            dt_units = self.index_units
            if str(dt.dtype).startswith('timedelta'):
                dt = dt.astype('timedelta64[s]').astype('float64') / 60 / 60 / 24
                dt_units = 'days'
        elif method[0] in 'm':
            dt = days_in_month(self.index)
            dt_units = 'days'
        elif method[0] in 'y':
            dt = days_in_year(self.index)
            dt_units = 'days'

        if method[0] in 't':
            v_min = np.minimum(self.as_pandas()[sl1].set_index(self.index[sl2]), self.as_pandas()[sl2])
            v_max = np.maximum(self.as_pandas()[sl1].set_index(self.index[sl2]), self.as_pandas()[sl2])
            cumulative = (dt * v_min.transpose()).transpose() + (dt * (v_max - v_min).transpose() / 2.0).transpose()
        elif method[0] in 'ac':
            if at == 'same':
                cumulative = (dt * (self.as_pandas()[sl1]).transpose()).transpose()
            if at == 'next':
                cumulative = (dt * (self.as_pandas()[sl1].set_index(self.index[sl2])).transpose()).transpose()
        elif method[0] in 'm':
            cumulative = (dt * self.as_pandas().transpose()).transpose()

        new_units = {}
        for col, unit in self.units.items():
            if unit is None:
                new_units[col] = None
            elif len(unit.split('/')) == 2 and (unit.split('/')[-1].lower() == dt_units.lower() or (
                    unit.split('/')[-1].lower() in ['day', 'days'] and dt_units.lower() == 'days')):
                new_units[col] = unit.split('/')[0]
            else:
                new_units[col] = unit + '*' + dt_units

        params_ = self.params_
        params_['units'] = new_units

        if method[0] in 't' or (method[0] in 'ac' and at == 'next'):
            if str(dt.dtype).startswith('timedelta'):
                first_row = pd.DataFrame(dict(zip(self.columns, [0.0] * len(self.columns))),
                                         index=['0']).set_index(pd.DatetimeIndex([self.index[0]]))
            else:
                first_row = pd.DataFrame(dict(zip(self.columns, [0.0] * len(self.columns))), index=[self.index[0]])
            return self._class(data=np.cumsum(first_row.append(cumulative)), **params_)
        elif method[0] in 'ac' and at == 'same':
            if str(dt.dtype).startswith('timedelta'):
                last_row = pd.DataFrame(dict(zip(self.columns, [0.0] * len(self.columns))),
                                    index=[str(len(self) - 1)]).set_index(pd.DatetimeIndex([self.index[-1]]))
            else:
                last_row = pd.DataFrame(dict(zip(self.columns, [0.0] * len(self.columns))), index=[self.index[-1]])
            return self._class(data=np.cumsum(cumulative.append(last_row)), **params_)
        else:
            return self._class(data=np.cumsum(cumulative), **params_)

    def differentiate(self, na_position='last'):
        """
        Calculates numerical differentiation of the columns values over the index values.

        Returns a new SimDataFrame
        """
        if len(self) < 2:
            logging.warning("Less than two rows, nothing to differenciate.")
            return self

        dt = np.diff(self.index)
        dt_units = self.index_units
        if str(dt.dtype).startswith('timedelta'):
            dt = dt.astype('timedelta64[s]').astype('float64') / 60 / 60 / 24
            dt_units = 'days'

        diff = np.diff(self.as_pandas().to_numpy(), axis=0)
        diff = diff / dt.reshape(-1, 1)

        new_units = {}
        if self.units is not None:
            for col, unit in self.units.items():
                if unit is None:
                    new_units[col] = str(unit) + '/' + str(dt_units)
                elif len(unit.split('/')) == 2 and (unit.split('/')[-1].lower() == dt_units.lower() or (
                        unit.split('/')[-1].lower() in ['day', 'days'] and dt_units.lower() == 'days')):
                    new_units[col] = unit + '/' + unit.split('/')[-1]
                elif len(unit.split('*')) == 2 and (unit.split('*')[-1].lower() == dt_units.lower() or (
                        unit.split('*')[-1].lower() in ['day', 'days'] and dt_units.lower() == 'dsys')):
                    new_units[col] = unit.split('*')[0]
                else:
                    new_units[col] = str(unit) + '/' + str(dt_units)

        if na_position == 'first':
            if str(dt.dtype).startswith('timedelta'):
                nan_row = pd.DataFrame(dict(zip(self.columns, [None] * len(self.columns))), index=['0']).set_index(
                    pd.DatetimeIndex([self.index[0]]))
            else:
                nan_row = pd.DataFrame(dict(zip(self.columns, [None] * len(self.columns))), index=[self.index[0]])
            diff = pd.DataFrame(data=diff, index=self.index[1:], columns=self.columns)
            diff = nan_row.append(diff)
        else:
            if str(dt.dtype).startswith('timedelta'):
                nan_row = pd.DataFrame(dict(zip(self.columns, [None] * len(self.columns))), index=['0']).set_index(
                    pd.DatetimeIndex([self.index[-1]]))
            else:
                nan_row = pd.DataFrame(dict(zip(self.columns, [None] * len(self.columns))), index=[self.index[-1]])
            diff = pd.DataFrame(data=diff, index=self.index[:-1], columns=self.columns)
            diff = diff.append(nan_row)

        params_ = self.params_
        params_['units'] = new_units
        params_['index_units'] = self.index_units
        return self._class(data=diff, **params_)

    def get_units_string(self, items=None):
        items_units_dict = self.get_units(items)
        if None in items_units_dict and items_units_dict[None] is None:
            del items_units_dict[None]
        if len(items_units_dict) == 0:
            return 'unitless'
        if items is None and 'SimSeries' in str(type(self)) and len(items_units_dict) <= 2:
            if self.name in items_units_dict:
                return items_units_dict[self.name]
            else:
                return list(items_units_dict.values())[0]
        elif len(set(items_units_dict.values())) == 1:
            return list(set(items_units_dict.values()))[0]
        else:
            result = list(items_units_dict.values())[0]
            logging.warning("More than one units found for the item '" + str(items) + "', returning the first one: '" + str(result) + "'." )
            return result

    def get_UnitsString(self, items=None):
        return self.get_units_string(items)
    def set_Units(self, units, item=None):
        """
        Alias of .set_units method.
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
        return self.set_units(units=units, item=item)

    def to_excel(self, excel_writer, split_by=None, sheet_name=None, na_rep='',
                 float_format=None, columns=None, header=True, units=True, index=True,
                 index_label=None, startrow=0, startcol=0, engine=None,
                 merge_cells=True, encoding=None, inf_rep='inf', verbose=True,
                 freeze_panes=None, sort=None):
        """
        Wrapper of .to_excel method from Pandas.
        On top of Pandas method this method is able to split the data into different
        sheets based on the column names. See parameters `split_by` and `sheet_name`.

        Write {klass} to an Excel sheet.
        To write a single {klass} to an Excel .xlsx file it is only necessary to
        specify a target file name. To write to multiple sheets it is necessary to
        create an `ExcelWriter` object with a target file name, and specify a sheet
        in the file to write to.
        Multiple sheets may be written to by specifying unique `sheet_name`.
        With all data written to the file it is necessary to save the changes.
        Note that creating an `ExcelWriter` object with a file name that already
        exists will result in the contents of the existing file being erased.

        Parameters
        ----------
        excel_writer : str or ExcelWriter object from Pandas.
            File path or existing ExcelWriter.
        split_by: None, positive or negative integer or str 'left', 'right' or 'first'. Default is None
            If is string 'left' or 'right', creates a sheet grouping the columns by
            the corresponding left:right part of the column name.
            If is string 'first', creates a sheet grouping the columns by
            the first character of the column name.
            If None, all the columns will go into the same sheet.
            if integer i > 0, creates a sheet grouping the columns by the 'i' firsts
            characters of the column name indicated by the integer.
            if integer i < 0, creates a sheet grouping the columns by the 'i' last
            the number characters of the column name indicated by the integer.
        sheet_name : None or str, default None
            Name of sheet which will contain DataFrame.
            If None:
                the `left` or `right` part of the name will be used if is unique,
                or 'FIELD', 'WELLS', 'GROUPS' or 'REGIONS' if all the column names
                start with 'F', 'W', 'G' or 'R'.
            else 'Sheet1' will be used.
        na_rep : str, default ''
            Missing data representation.
        float_format : str, optional
            Format string for floating point numbers. For example
            ``float_format="%.2f"`` will format 0.1234 to 0.12.
        columns : sequence or list of str, optional
            Columns to write.
        header : bool or list of str, default True
            Write out the column names. If a list of string is given it is
            assumed to be aliases for the column names.
        units : bool, default True
            Write the units of the column under the header name.
        index : bool, default True
            Write row names(index).
        index_label : str or sequence, optional
            Column label for index column(s) if desired. If not specified, and
            `header` and `index` are True, then the index names are used. A
            sequence should be given if the DataFrame uses MultiIndex.
        startrow : int, default 0
            Upper left cell row to dump data frame.
        startcol : int, default 0
            Upper left cell column to dump data frame.
        engine : str, optional
            Write engine to use, 'openpyxl' or 'xlsxwriter'. You can also set this
            via the options ``io.excel.xlsx.writer``, ``io.excel.xls.writer``, and
            ``io.excel.xlsm.writer``.
        merge_cells : bool, default True
            Write MultiIndex and Hierarchical Rows as merged cells.
        encoding : str, optional
            Encoding of the resulting excel file. Only necessary for xlwt,
            other writers support unicode natively.
        inf_rep : str, default 'inf'
            Representation for infinity(there is no native representation for
            infinity in Excel).
        verbose : bool, default True
            Display more information in the error logs.
        freeze_panes : tuple of int(length 2), optional
            Specifies the one-based bottommost row and rightmost column that
            is to be frozen.
        sort: None, bool or int
            if None, default behaviour depends on split_by parameter:
                if split_by is None will keep the current order of the columns in the SimDataFrame.
                if split_by is not None will sort alphabetically ascending the names of the columns.
            if True (bool) will sort the columns alphabetically ascending.
            if False (bool) will maintain the current order.
            if int > 0 will sort the columns alphabetically ascending.
            if int < 0 will sort the columns alphabetically descending.
            if int == 0 will keep the current order of the columns.

        """
        return self.to_SimDataFrame().to_excel(excel_writer,
                                               split_by=split_by,
                                               sheet_name=sheet_name,
                                               na_rep=na_rep,
                                               float_format=float_format,
                                               columns=columns,
                                               header=header,
                                               units=units,
                                               index=index,
                                               index_label=index_label,
                                               startrow=startrow,
                                               startcol=startcol,
                                               engine=engine,
                                               merge_cells=merge_cells,
                                               encoding=encoding,
                                               inf_rep=inf_rep,
                                               verbose=verbose,
                                               freeze_panes=freeze_panes,
                                               sort=sort)

    def info(self, *args, **kwargs):
        """
        wrapper for pandas.DataFrame.info() but with Units.
        """

        def fillblank(string, length):
            if len(string.strip()) > length:
                return string.strip() + ' '
            return string.strip() + ' ' * (length - len(string.strip()) + 1)

        logging.warning(str(type(self.as_pandas().index)).split('.')[-1][:-2] + ': ' + str(len(self)) + ' entries, ' + str(
            self.index[0]) + ' to ' + str(self.index[-1]))

        columns = [str(col) for col in self.columns]
        notnulls = [str(self.iloc[:, col].notnull().sum()) for col in range(len(self.columns))]
        dtypes = [str(self.iloc[:, col].dtype) for col in range(len(self.columns))]
        units = [str(self.units[col]) for col in self.columns]

        logging.warning('Data columns (total ' + str(len(columns)) + ' columns):')

        line = ' ' + fillblank('#', len(str(len(columns))))
        line = line + ' ' + fillblank('Column', max(len('Column'), max(map(len, columns))))
        line = line + ' ' + fillblank('Non-Null Count',
                                      max(len('Non-Null Count'), len(str(len(self))) + len(' non-null')))
        line = line + ' ' + fillblank('Dtype', max(len('Dtype'), max(map(len, dtypes))))
        line = line + ' ' + fillblank('Units', max(len('Units'), max(map(len, units))))

        line = fillblank('---', len(str(len(columns))))
        line = line + ' ' + fillblank('------', max(map(len, columns)))
        line = line + ' ' + fillblank('--------------', len(str(len(self))) + len(' non-null '))
        line = line + ' ' + fillblank('-----', max(map(len, dtypes)))
        line = line + ' ' + fillblank('-----', max(map(len, units)))

        for i in range(len(columns)):
            line = ' ' + fillblank(str(i), max(len('# '), len(str(len(columns)))))
            line = line + ' ' + fillblank(columns[i], max(len('Column'), max(map(len, columns))))
            line = line + ' ' + fillblank(notnulls[i] + ' non-null',
                                          max(len('Non-Null Count'), len(str(len(self))) + len(' non-null')))
            line = line + ' ' + fillblank(dtypes[i], max(len('Dtype'), max(map(len, dtypes))))
            line = line + ' ' + fillblank(units[i], max(len('Units'), max(map(len, units))))

        logging.warning('dtypes: ' + ', '.join([each + '(' + str(dtypes.count(each)) + ')' for each in sorted(set(dtypes))]))

        logging.warning('memory usage: ' + str(int(getsizeof(self) / 1024 / 1024 * 10) / 10) + '+ MB')

        return None
