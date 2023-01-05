# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martin Carlos Araya
"""

__version__ = '0.80.10'
__release__ = 20230104
__all__ = ['SimSeries']

from pandas import Series, DataFrame, Index
from io import StringIO
from shutil import get_terminal_size
from pandas._config import get_option
import fnmatch
import numpy as np
import warnings
from warnings import warn

from unyts.converter import convertible, convert_for_SimPandas as _converter
from unyts.operations import unit_product as _unit_product, unit_division as _unit_division, unit_base as _unit_base, \
    unit_power as _unit_power
from unyts import units

from simpandas.basics import SimBasics
from simpandas.common._internal_processes import _set_index_name, _describe, _parameters2dict, _contains, \
    _set_name_separator, _get_name_separator
from simpandas.common.helpers import clean_axis, string_new_name
from simpandas.common.math import znorm as _znorm, minmaxnorm as _minmaxnorm, jitter as _jitter
from simpandas.common.slope import slope as _slope
from simpandas.indexer import _SimLocIndexer

_SERIES_WARNING_MSG = """\
    You are passing unitless data to the SimSeries constructor. Currently,
    it falls back to returning a pandas Series. But in the future, we will start
    to raise a TypeError instead."""


def _simseries_constructor_with_fallback(data=None, index=None, units=None, **kwargs):
    """
    A flexible constructor for SimSeries._constructor, which needs to be able
    to fall back to a Series(if a certain operation does not produce
    units)
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=_SERIES_WARNING_MSG,
                category=FutureWarning,
                module="SimPandas[.*]",
            )
            return SimSeries(data=data,
                             index=index,
                             units=units,
                             **kwargs)
    except TypeError:
        return Series(data=data,
                      index=index,
                      **kwargs)


class SimSeries(SimBasics, Series):
    """
    A Series object designed to store data with units.

    Parameters
    ----------
    data : array-like, dict, scalar value
        The data to store in the SimSeries.
    index : array-like or Index
        The index for the SimSeries.
    units : string or dictionary of units(optional)
        Can be any string, but only units acepted by the UnitConverter will
        be considered when doing arithmetic calculations with other SimSeries
        or SimDataFrames.

    kwargs
        Additional arguments passed to the Series constructor,
         e.g. ``name``.

    See Also
    --------
    SimDataFrame
    pandas.Series

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
                 'columns']

    def __init__(self,
                 data=None,
                 index=None,
                 columns=None,
                 units=None,
                 dtype=None,
                 name=None,
                 copy=False,
                 fastpath=False,
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
        self.spdLocator = _SimLocIndexer("loc", self)
        self.transposed = bool(transposed)
        self.columns = name if columns is None else columns

        # data validaton
        if isinstance(data, DataFrame) and len(data.columns) > 1:
            raise ValueError("'data' parameter can be an instance of DataFrame but must have only one column.")

        # get units from data if it is SimDataFrame or SimSeries
        if units is None or (type(units) in [list, dict] and len(units) == 0):
            if hasattr(data, 'get_units'):
                units = data.get_units()
        elif type(units) is dict and len(units) == 1:
            units, name = list(units.values())[0], list(units.keys())[0] if name is None else name
        elif type(units) is str:
            units = units.strip()

        # get nameSeparator
        if name_separator is None and hasattr(data, 'nameSeparator'):
            name_separator = data.nameSeparator
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

        # initialize pd.Series
        super().__init__(data=data, index=index, dtype=dtype, name=name, copy=copy, fastpath=fastpath)

        # get name
        if self.name is None or (type(self.name) is str and self.name.strip() == ''):
            if type(units) is dict and len(units) == 1:
                self.name = list(units.keys())[0]

        # set units
        self.set_units(units)

        # get indexUnits
        if index_units is None:
            if self.index.name is not None and self.index.name in self.units:
                self.index_units = self.units[self.index.name]
            elif hasattr(data, 'indexUnits'):
                self.index_units = data.indexUnits.copy() if type(data.indexUnits) is dict else data.indexUnits
        elif type(index_units) is str:
            self.index_units = index_units
        else:
            raise TypeError("`indexUnitx` must be a string.")

        # override index.name with indexName
        if index_name is not None:
            if type(self.units) is dict and self.index.name in self.units:
                self.units[index_name] = self.units[self.index.name]
            self.index.name = index_name

    @property
    def _constructor(self):
        return _simseries_constructor_with_fallback

    @property
    def _constructor_expanddim(self):
        from simpandas.frame import SimDataFrame
        return SimDataFrame

    @property
    def _class(self):
        return SimSeries

    def __repr__(self) -> str:
        """
        Return a string representation for a particular Series, with Units.
        """

        # taken from Pandas Series
        buf = StringIO("")
        width, height = get_terminal_size()
        max_rows = (
            height
            if get_option("display.max_rows") == 0
            else get_option("display.max_rows")
        )
        min_rows = (
            height
            if get_option("display.max_rows") == 0
            else get_option("display.min_rows")
        )
        show_dimensions = get_option("display.show_dimensions")

        self.to_string(
            buf=buf,
            name=self.name,
            dtype=self.dtype,
            min_rows=min_rows,
            max_rows=max_rows,
            length=show_dimensions,
        )
        result = buf.getvalue()

        if type(self.units) is str:
            return result + ', units: ' + self.units
        elif type(self.units) is dict:
            result = result.split('\n')
            for n in range(len(result) - 1):
                keys = result[n] + ' '
                i, f = 0, 0
                while i < len(keys):
                    f = keys.index(' ', i)
                    key = keys[i:f]
                    if key == '...':
                        i = len(keys)
                        continue
                    while key not in self.index and f <= len(keys):
                        f = keys.index(' ', f + 1) if ' ' in keys[f + 1:] else len(keys) + 1
                        key = keys[i:f]
                    if key not in self.index:
                        i = len(keys)
                        continue
                    if key in self.units and self.units[key] is not None:
                        result[n] += '    ' + self.units[key].strip()
                    i = len(keys)
            result = '\n'.join(result)
            return '\n' + result
        else:
            return result

    def __call__(self):
        if len(self.get_units()) == 1:
            return units(self.values, self.get_UnitsString())
        else:
            return self.values

    def __getitem__(self, key=None):
        if key is None:
            return self
        if type(key) is str and key.strip() == self.name and not key.strip() in self.index:
            return self
        else:
            try:
                return self.loc[key]
            except KeyError:
                try:
                    return self.iloc[key]
                except IndexError:
                    raise KeyError("the requested Key is not a valid index or name: " + str(key))

    def __add__(self, other):
        params_ = self.params_
        # both SimSeries
        if isinstance(other, SimSeries):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimSeries are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")
            if type(self.units) is str and type(other.units) is str:
                new_name = string_new_name(self._common_rename(other)[2])
                if self.units == other.units:
                    result = self.S.add(other.S, fill_value=0)
                elif convertible(other.units, self.units):
                    other_c = _convert(other, other.units, self.units, self.verbose)
                    result = self.S.add(other_c.S, fill_value=0)
                elif convertible(self.units, other.units):
                    self_c = _convert(self, self.units, other.units, self.verbose)
                    result = other.S.add(self_c.S, fill_value=0)
                    params_['units'] = other.units
                else:
                    result = self.S.add(other.S, fill_value=0)
                    params_['units'] = self.units + '+' + other.units
                try:
                    params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
                except ValueError:
                    params_['dtype'] = result.dtype
                except TypeError:
                    params_['dtype'] = result.dtype
                params_['name'] = new_name
                return SimSeries(data=result, **params_)
            else:
                raise NotImplementedError

        # other is Pandas Series
        elif isinstance(other, Series):
            return 'series'
            result = self.S.add(other, fill_value=0)
            new_name = string_new_name(self._common_rename(SimSeries(other, **self.params_))[2])
            try:
                params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
            except ValueError:
                params_['dtype'] = result.dtype
            params_['name'] = new_name
            return SimSeries(data=result, **params_)

        return 'other'
        # lets Pandas deal with other types, maintain units, dtype and name
        result = self.as_Series() + other
        try:
            params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
        except ValueError:
            params_['dtype'] = result.dtype
        return SimSeries(data=result, **params_)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        params_ = self.params_
        # both SimSeries
        if isinstance(other, SimSeries):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimSeries are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")
            if type(self.units) is str and type(other.units) is str:
                new_name = string_new_name(self._common_rename(other)[2])
                if self.units == other.units:
                    result = self.sub(other, fill_value=0)
                elif convertible(other.units, self.units):
                    otherC = _convert(other, other.units, self.units, self.verbose)
                    result = self.sub(otherC, fill_value=0)
                elif convertible(self.units, other.units):
                    selfC = _convert(self, self.units, other.units, self.verbose)
                    result = selfC.sub(other, fill_value=0)
                    params_['units'] = other.units
                else:
                    result = self.sub(other, fill_value=0)
                    params_['units'] = self.units + '-' + other.units
                try:
                    params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
                except ValueError:
                    params_['dtype'] = result.dtype
                except TypeError:
                    params_['dtype'] = result.dtype
                params_['name'] = new_name
                return SimSeries(data=result, **params_)
            else:
                raise NotImplementedError

        # other is Pandas Series
        elif isinstance(other, Series):
            result = self.S.sub(other, fill_value=0)
            new_name = string_new_name(self._common_rename(SimSeries(other, **self.params_))[2])
            try:
                params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
            except ValueError:
                params_['dtype'] = result.dtype
            params_['name'] = new_name
            return SimSeries(data=result, **params_)

        # lets Pandas deal with other types, maintain units and dtype
        result = self.as_Series() - other
        try:
            params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
        except ValueError:
            params_['dtype'] = result.dtype
        return SimSeries(data=result, **params_)

    def __rsub__(self, other):
        return self.__neg__().__add__(other)

    def __mul__(self, other):
        params_ = self.params_
        # both SimSeries
        if isinstance(other, SimSeries):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimSeries are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")
            if type(self.units) is str and type(other.units) is str:
                params_['units'] = _unit_product(self.units, other.units)
                new_name = string_new_name(self._common_rename(other)[2])
                if self.units == other.units:
                    result = self.mul(other)
                elif convertible(other.units, self.units):
                    other_c = _convert(other, other.units, self.units, self.verbose)
                    result = self.mul(other_c)
                elif convertible(self.units, other.units):
                    self_c = _convert(self, self.units, other.units, self.verbose)
                    result = other.mul(self_c)
                    params_['units'] = _unit_product(other.units, self.units)
                elif convertible(other.units, _unit_base(self.units)):
                    other_c = _convert(other, other.units, _unit_base(self.units), self.verbose)
                    result = self.mul(other_c)
                elif convertible(self.units, _unit_base(other.units)):
                    self_c = _convert(self, self.units, _unit_base(other.units), self.verbose)
                    result = other.mul(self_c)
                    params_['units'] = _unit_product(other.units, self.units)
                else:
                    result = self.mul(other)
                    params_['units'] = self.units + '*' + other.units
                try:
                    params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
                except ValueError:
                    params_['dtype'] = result.dtype
                except TypeError:
                    params_['dtype'] = result.dtype
                params_['name'] = new_name
                return SimSeries(data=result, **params_)
            else:
                raise NotImplementedError

        # lets Pandas deal with other types(types with no units), maintain units and dtype
        result = self.as_Series() * other
        params_['dtype'] = self.dtype if (result.astype(self.dtype).equals(result)) else result.dtype
        return SimSeries(data=result, **params_)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        params_ = self.params_
        # both SimSeries
        if isinstance(other, SimSeries):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimSeries are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")
            if type(self.units) is str and type(other.units) is str:
                new_name = string_new_name(self._common_rename(other)[2])
                params_['units'] = _unit_division(self.units, other.units)
                if self.units == other.units:
                    result = self.truediv(other)
                elif convertible(other.units, self.units):
                    other_c = _convert(other, other.units, self.units, self.verbose)
                    result = self.truediv(other_c)
                elif convertible(self.units, other.units):
                    self_c = _convert(self, self.units, other.units, self.verbose)
                    result = self_c.truediv(other)
                    params_['units'] = _unit_division(other.units, self.units)
                elif convertible(other.units, _unit_base(self.units)):
                    other_c = _convert(other, other.units, _unit_base(self.units), self.verbose)
                    result = self.truediv(other_c)
                elif convertible(self.units, _unit_base(other.units)):
                    self_c = _convert(self, self.units, _unit_base(other.units), self.verbose)
                    result = self_c.truediv(other)
                    params_['units'] = _unit_division(other.units, self.units)
                else:
                    result = self.truediv(other)
                    params_['units'] = self.units + '/' + other.units
                try:
                    params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
                except ValueError:
                    params_['dtype'] = result.dtype
                except TypeError:
                    params_['dtype'] = result.dtype
                params_['name'] = new_name
                return SimSeries(data=result, **params_)
            else:
                raise NotImplementedError

        # lets Pandas deal with other types(types with no units), maintain units and dtype
        result = self.as_Series() / other
        try:
            params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
        except ValueError:
            params_['dtype'] = result.dtype
        return SimSeries(data=result, **params_)

    def __rtruediv__(self, other):
        return self.__pow__(-1).__mul__(other)

    def __floordiv__(self, other):
        params_ = self.params_
        # both SimSeries
        if isinstance(other, SimSeries):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimSeries are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")
            if type(self.units) is str and type(other.units) is str:
                params_['units'] = _unit_division(self.units, other.units)
                new_name = string_new_name(self._common_rename(other)[2])
                if self.units == other.units:
                    result = self.floordiv(other)
                elif convertible(other.units, self.units):
                    other_c = _convert(other, other.units, self.units, self.verbose)
                    result = self.floordiv(other_c)
                elif convertible(self.units, other.units):
                    self_c = _convert(self, self.units, other.units, self.verbose)
                    result = other.floordiv(self_c)
                    params_['units'] = _unit_division(other.units, self.units)
                elif convertible(other.units, _unit_base(self.units)):
                    other_c = _convert(other, other.units, _unit_base(self.units), self.verbose)
                    result = self.floordiv(other_c)
                elif convertible(self.units, _unit_base(other.units)):
                    self_c = _convert(self, self.units, _unit_base(other.units), self.verbose)
                    result = other.floordiv(self_c)
                    params_['units'] = _unit_division(other.units, self.units)
                else:
                    result = self.floordiv(other)
                    params_['units'] = self.units + '/' + other.units
                params_[
                    'dtype'] = result.dtype  # self.dtype if result.astype(self.dtype).equals(result) else result.dtype
                params_['name'] = new_name
                return SimSeries(data=result, **params_)
            else:
                raise NotImplementedError

        # let's Pandas deal with other types(types with no units), maintain units and dtype
        result = self.as_Series() // other
        params_['dtype'] = result.dtype
        return SimSeries(data=result, **params_)

    def __rfloordiv__(self, other):
        return self.__pow__(-1).__mul__(other).__int__()

    def __mod__(self, other):
        params_ = self.params_
        # both are SimSeries
        if isinstance(other, SimSeries):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimSeries are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")
            if type(self.units) is str and type(other.units) is str:
                newName = string_new_name(self._common_rename(other)[2])
                if self.units == other.units:
                    result = self.mod(other)
                elif convertible(other.units, self.units):
                    otherC = _convert(other, other.units, self.units, self.verbose)
                    result = self.mod(otherC)
                elif convertible(self.units, other.units):
                    selfC = _convert(self, self.units, other.units, self.verbose)
                    result = other.mod(selfC)
                    params_['units'] = other.units
                else:
                    result = self.mod(other)
                try:
                    params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
                except ValueError:
                    params_['dtype'] = result.dtype
                except TypeError:
                    params_['dtype'] = result.dtype
                params_['name'] = newName
                return SimSeries(data=result, **params_)
            else:
                raise NotImplementedError

        # let's Pandas deal with other types, maintain units and dtype
        result = self.as_Series() % other
        try:
            params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
        except ValueError:
            params_['dtype'] = result.dtype
        return SimSeries(data=result, **params_)

    def __pow__(self, other):
        params_ = self.params_
        # both SimSeries
        if isinstance(other, SimSeries):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                Warning(
                    "indexes of both SimSeries are not of the same kind:\n   '" + self.index.name + "' != '" + other.index.name + "'")
            if type(self.units) is str and type(other.units) is str:
                params_['units'] = self.units + '^' + other.units
                newName = string_new_name(self._common_rename(other)[2])
                if self.units == other.units:
                    result = self.pow(other)
                elif convertible(other.units, self.units):
                    otherC = _convert(other, other.units, self.units, self.verbose)
                    result = self.pow(otherC)
                    params_['units'] = self.units + '^' + self.units
                elif convertible(self.units, other.units):
                    selfC = _convert(self, self.units, other.units, self.verbose)
                    result = other.pow(selfC)
                    params_['units'] = other.units + '^' + other.units
                else:
                    result = self.pow(other)
                try:
                    params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
                except ValueError:
                    params_['dtype'] = result.dtype
                except TypeError:
                    params_['dtype'] = result.dtype
                params_['name'] = newName
                return SimSeries(data=result, **params_)
            else:
                raise NotImplementedError

        # if other is integer or float
        elif type(other) in (int, float):
            result = self.as_Series() ** other
            params_ = self.params_
            params_['units'] = {c: _unit_power(self.get_units(c)[c], other) for c in self.columns}
            return SimSeries(data=result, **params_)

        # let's Pandas deal with other types(types with no units), maintain units and dtype
        result = self.as_Series() ** other
        try:
            params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
        except ValueError:
            params_['dtype'] = result.dtype
        return SimSeries(data=result, **params_)

    def set_index(self, name):
        self.set_index_name(name)

    def set_index_units(self, units):
        if type(units) is str and len(units.strip()) > 0:
            self.index_units = units.strip()
        elif type(units) is dict and len(units) == len(self.index):
            self.index_units = units
        else:
            raise TypeError("`units` must be a string or a dictionary with pair key: units for each item in the index.")

    def transpose(self):
        return self

    def to_pandas(self):
        return self.to_series()

    def as_pandas(self):
        return self.as_series()

    def to_series(self):
        return Series(self.copy())

    def as_series(self):
        return Series(self)

    def to_simseries(self):
        return self

    def as_simseries(self):
        return self

    def to_dataframe(self):
        return self.to_simdataframe().to_dataframe()

    def as_dataframe(self):
        return self.as_simdataframe().as_dataframe()

    def to_simdataframe(self):
        from .frame import SimDataFrame
        if type(self.units) is str:
            return SimDataFrame(data=self)
        elif type(self.units) is dict:
            return SimDataFrame(
                data=self.values.reshape(1, self.values.size),
                index=[self.name],
                columns=self.index,
                **self.params_)

    def as_simdataframe(self):
        return self.to_simdataframe()

    def convert(self, units):
        """
        returns the series converted to the requested units if possible,
        else returns None
        """
        if type(units) is str and type(self.units) is str:
            if convertible(self.units, units):
                params_ = self.params_
                params_['units'] = units
                return SimSeries(data=_converter(self.S, self.units, units, self.verbose), **params_)
        if type(units) is str and type(self.units) is dict and len(set(self.units.values())) == 1:
            params_ = self.params_
            params_['units'] = units
            return SimSeries(data=_converter(self.S, list(set(self.units.values()))[0], units, self.verbose), **params_)
        if type(units) is dict:
            return self.to_simdataframe().convert(units).to_simseries()

    def reindex(self, index=None, **kwargs):
        """
        wrapper for pandas.Series.reindex

        index : array-like, optional
            New labels / index to conform to, should be specified using keywords.
            Preferably an Index object to avoid duplicating data.
        """
        return SimSeries(data=self.to_pandas().reindex(index=index, **kwargs), **self.params_)

    # not shared methods
    @property
    def columns(self):
        return Index([self.name])

    def drop(self, labels=None, axis=0, index=None, columns=None, level=None, inplace=False, errors='raise'):
        axis = clean_axis(axis)
        if inplace:
            super().drop(labels=labels, axis=axis, index=index, columns=columns,
                         level=level, inplace=inplace, errors='errors')
        else:
            return SimSeries(data=self.as_pandas().drop(labels=labels, axis=axis, index=index, columns=columns,
                                                        level=level, inplace=inplace, errors='errors'),
                             **self.params_)

    def dropna(self, axis=0, inplace=False, how=None):
        axis = clean_axis(axis)
        if inplace:
            super().dropna(axis=axis, inplace=inplace, how=how)
        else:
            return SimSeries(
                data=self.as_pandas().dropna(axis=axis, inplace=inplace, how=how),
                **self.params_)





    def to_excel(self, excel_writer, split_by=None, sheet_name=None, na_rep='',
                 float_format=None, columns=None, header=True, units=True, index=True,
                 index_label=None, startrow=0, startcol=0, engine=None,
                 merge_cells=True, encoding=None, inf_rep='inf', verbose=True,
                 freeze_panes=None, sort=None):
        """
        Wrapper of .to_excel method from Pandas.
        On top of Pandas method this method is able to split the data into different
        sheets based on the column names. See paramenters `split_by´ and `sheet_name´.

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

    def _common_rename(self, SimSeries1, SimSeries2=None, LR=None):
        cha = self.intersection_character

        if LR is not None:
            LR = LR.upper()
            if LR not in 'LR':
                LR = None

        if SimSeries2 is None:
            SDF1, SDF2 = self, SimSeries1
        else:
            SDF1, SDF2 = SimSeries1, SimSeries2

        if type(SDF1) is not SimSeries:
            raise TypeError("both series to be compared must be SimSeries.")
        if type(SDF2) is not SimSeries:
            raise TypeError("both series to be compared must be SimSeries.")

        if SDF1.name_separator is None or SDF2.name_separator is None:
            raise ValueError("the 'nameSeparator' must not be empty in both SimSeries.")

        if LR == 'L' or (LR is None and len(SDF1.left) == 1 and len(SDF2.left) == 1):
            SDF2C = SDF2.copy()
            SDF2C.renameRight(inplace=True)
            SDF1C = SDF1.copy()
            SDF1C.renameRight(inplace=True)
            commonNames = {}
            for c in SDF1C.columns:
                if c in SDF2C.columns:
                    commonNames[c] = str(SDF1.left[0]) + str(cha) + str(SDF2.left[0]) + str(SDF1.name_separator) + str(
                        c)
                else:
                    commonNames[c] = str(SDF1.left[0]) + str(SDF1.name_separator) + str(c)
            for c in SDF2C.columns:
                if c not in SDF1C.columns:
                    commonNames[c] = str(SDF2.left[0]) + str(SDF1.name_separator) + str(c)
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
                    commonNames[c] = str(c) + str(SDF1.name_separator) + str(SDF1.right[0]) + str(cha) + str(
                        SDF2.right[0])
                else:
                    commonNames[c] = str(c) + str(SDF1.name_separator) + str(SDF1.right[0])
            for c in SDF2C.columns:
                if c not in SDF1C.columns:
                    commonNames[c] = str(c) + str(SDF1.name_separator) + str(SDF2.right[0])
            if LR is None and len(commonNames) > 1:
                alternative = self._common_rename(SDF1, SDF2, LR='L')
                if len(alternative[2]) < len(commonNames):
                    return alternative

        else:
            SDF1C, SDF2C = SDF1, SDF2.copy()
            commonNames = None

        # check if proposed names are not repetitions of original names
        for name in commonNames:
            if self.name_separator is str and len(self.name_separator) > 0 and self.name_separator in commonNames[name]:
                if commonNames[name].split(self.name_separator)[0] == commonNames[name].split(self.name_separator)[
                    1] and \
                        commonNames[name].split(self.name_separator)[0] == name:
                    commonNames[name] = name

        return SDF1C, SDF2C, commonNames

    def rename(self, index=None, *, axis=None, copy=True, inplace=False, level=None, errors='ignore', **kwargs):
        """
        wrapper of rename function from Pandas.

        Alter Series index labels or name.

        Function / dict values must be unique (1-to-1).
        Labels not contained in a dict / Series will be left as-is.
        Extra labels listed don’t throw an error.

        Alternatively, change Series.name with a scalar value.

        See the user guide for more.

        Parameters
        axis{0 or “index”}
        Unused. Accepted for compatibility with DataFrame method only.

        indexscalar, hashable sequence, dict-like or function, optional
        Functions or dict-like are transformations to apply to the index.
        Scalar or hashable sequence-like will alter the Series.name attribute.

        **kwargs
        Additional keyword arguments passed to the function. Only the “inplace” keyword is used.

        Returns
        Series or None
        Series with index labels or name altered or None if inplace=True.
        """

        # for compatibility with SimDataFrame
        if 'columns' in kwargs and index is None:
            index = kwargs['columns']
            del kwargs['columns']

        if type(index) is dict:
            if len(index) == 1 and list(index.keys()) not in self.index:
                return self.rename(list(index.values())[0], axis=axis, copy=copy, inplace=inplace, level=level,
                                   errors=errors)
            cBefore = list(self.index)
            if inplace:
                super().rename(index=index, axis=axis, copy=copy, inplace=inplace, level=level, errors=errors)
                cAfter = list(self.index)
            else:
                catch = super().rename(index=index, axis=axis, copy=copy, inplace=inplace, level=level, errors=errors)
                cAfter = list(catch.index)

            newUnits = {}
            for i in range(len(cBefore)):
                newUnits[cAfter[i]] = self.units[cBefore[i]]
            if inplace:
                self.units = newUnits
                self.spdLocator = _SimLocIndexer("loc", self)
                return None
            else:
                catch.units = newUnits
                catch.spdLocator = _SimLocIndexer("loc", catch)
                return catch
        elif type(index) is str:
            if inplace:
                self.name = index.strip()
                self.spdLocator = _SimLocIndexer("loc", self)
                return None
            else:
                catch = self.copy()
                catch.name = index
                catch.spdLocator = _SimLocIndexer("loc", catch)
                return catch


    # def resample(self, rule, axis=0, closed=None, label=None, convention='start', kind=None, loffset=None, base=None, on=None, level=None, origin='start_day', offset=None):
    #     axis = clean_axis(axis)
    #     return SimSeries(data=self.S.resample(rule, axis=axis, closed=closed, label=label, convention=convention, kind=kind, loffset=loffset, base=base, on=on, level=level, origin=origin, offset=offset), **self.params_ )





    @property
    def wells(self):
        objs = []
        if type(self.name) is str:
            if self.name_separator in self.name and self.name[0] == 'W':
                objs = [self.name.split(self.name_separator)[-1]]
        elif type(self.index[-1]) is str:
            for each in list(self.index):
                if self.name_separator in each and each[0] == 'W':
                    objs.append(each.split(self.name_separator)[-1])
        return tuple(set(objs))

    # @property
    # def items(self):
    #     return self.left


    @property
    def groups(self):
        if self.name_separator in [None, '', False]:
            return []
        objs = []
        if type(self.name) is str:
            if self.name_separator in self.name and self.name[0] == 'G':
                objs = [self.name.split(self.name_separator)[-1]]
        elif type(self.index[-1]) is str:
            for each in list(self.index):
                if self.name_separator in each and each[0] == 'G':
                    objs.append(each.split(self.name_separator)[-1])
        return tuple(set(objs))

    @property
    def regions(self):
        if self.name_separator in [None, '', False]:
            return []
        objs = []
        if type(self.name) is str:
            if self.name_separator in self.name and self.name[0] == 'R':
                objs = [self.name.split(self.name_separator)[-1]]
        elif type(self.index[-1]) is str:
            for each in list(self.index):
                if self.name_separator in each and each[0] == 'R':
                    objs.append(each.split(self.name_separator)[-1])
        return tuple(set(objs))

    @property
    def attributes(self):
        if self.name_separator in [None, '', False]:
            return {col: [] for col in self.columns}
        atts = {}
        for each in list(self.get_keys()):
            if self.name_separator in each:
                if each.split(self.name_separator)[0] in atts:
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
        if pattern is not None and type(pattern) is not str:
            raise TypeError(
                'pattern argument must be a string.\nreceived ' + str(type(pattern)) + ' with value ' + str(pattern))
        if type(self.name) is str:
            keys = [self.name]
        else:
            keys = list(self.index)
        if pattern is None:
            return keys
        else:
            return list(fnmatch.filter(keys, pattern))

    def diff(self, periods=1, forward=False):
        if type(periods) is bool:
            periods, forward = 1, periods
        if forward:
            return SimSeries(
                data=-1 * self.as_Series().diff(periods=-1 * periods),
                **self.params_)
        else:
            return SimSeries(
                data=self.as_Series().diff(periods=periods),
                **self.params_)



    def avg(self, axis=0, **kwargs):
        return self.mean(axis=axis, **kwargs)

    def avg0(self, axis=0, **kwargs):
        return self.mean0(axis=axis, **kwargs)

    def average(self, axis=0, **kwargs):
        return self.mean(axis=axis, **kwargs)

    def average0(self, axis=0, **kwargs):
        return self.mean0(axis=axis, **kwargs)

    def count0(self, **kwargs):
        return self.replace(0, np.nan).count(**kwargs)

    def max0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).max(axis=axis, **kwargs)

    def mean0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).mean(axis=axis, **kwargs)

    def median0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).median(axis=axis, **kwargs)

    def min0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).min(axis=axis, **kwargs)

    def mode0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).mode(axis=axis, **kwargs)

    def prod0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).prod(axis=axis, **kwargs)

    def quantile0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).quantile(axis=axis, **kwargs)

    def rms(self, axis=0, **kwargs):
        return (self ** 2).mean(axis=axis, **kwargs) ** 0.5

    def rms0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).rms(axis=axis, **kwargs)

    def std0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).std(axis=axis, **kwargs)

    def sum0(self, axis=0, **kwargs):
        return self.sum(axis=axis, **kwargs)

    def var0(self, axis=0, **kwargs):
        return self.replace(0, np.nan).var(axis=axis, **kwargs)

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

    def get_Units(self, items=None):
        return self.get_units()

    def get_units(self, items=None):
        """
        returns the units for the selected 'items' or for all the columns in the SimDataFrame.

        Parameters
        ----------
        items : str or list of str, optional
            Ignored, this parameter is kept for compatibility with SimDataFrame. The default is None.

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        if self.units is None:
            return 'unitless'
        elif type(self.units) is str and type(self.name) is str:
            uDic = {str(self.name): self.units}
        elif type(self.units) is dict:
            uDic = {}
            for each in self.index:
                if each in self.units:
                    uDic[each] = self.units[each]
                else:
                    uDic[each] = 'unitless'
        else:
            return self.units.copy() if type(self.units) is dict else self.units
        return uDic

    def set_units(self, units, item=None):
        """
        Alias of .set_Units method.
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
        return self.set_Units(units=units, item=item)

    def set_Units(self, units, item=None):
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
        if item is not None and type(item) in (str, int, float) and item not in self.columns:
            raise ValueError("the required item '" + str(item) + "' is not in this SimSeries")

        if self.units is None or type(self.units) is str:
            if units is None:
                self.units = None
            elif type(units) is str:
                self.units = units.strip()
            elif type(units) is dict:
                old_units = self.units
                try:
                    self.units = {}
                    return self.set_Units(units)
                except:
                    self.units = old_units
                    raise ValueError("not able to process dictionary of units.")
            else:
                raise TypeError("units must be a string.")

        elif type(self.units) is dict:
            if type(units) not in (str, dict) and hasattr(units, '__iter__'):
                if item is not None and type(item) not in (str, dict) and hasattr(item, '__iter__'):
                    if len(item) == len(units):
                        return self.set_Units(dict(zip(item, units)))
                    else:
                        raise ValueError("both units and item must have the same length.")
                elif item is None:
                    if len(units) == len(self.columns):
                        return self.set_Units(dict(zip(list(self.columns), units)))
                    else:
                        raise ValueError(
                            "units list must be the same length of columns in the SimSeries or must be followed by a list of items.")
                else:
                    raise TypeError("if units is a list, items must be a list of the same length.")
            elif type(units) is dict:
                for k, u in units.items():
                    self.set_Units(u, k)
            elif type(units) is str:
                if item is None:
                    self.units = units.strip()
                else:
                    if type(item) not in (str, dict) and hasattr(item, '__iter__'):
                        units = units.strip()
                        for i in item:
                            if i in self.units:
                                self.units[i] = units
                    elif type(item) not in dict:
                        if item in self.units:
                            self.units[item] = units

            if item is None and len(self.columns) > 1:
                raise ValueError("More than one column in this SimSeries, item must not be None")
            elif item is None and len(self.columns) == 1:
                return self.set_Units(units, [list(self.columns)[0]])
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

    def get_UnitsString(self, items=None):
        if len(self.get_units(items)) == 1:
            return list(self.get_units(items).values())[0]
        elif len(set(self.get_units(items).values())) == 1:
            return list(set(self.get_units(items).values()))[0]

    def copy(self):
        if type(self.units) is dict:
            params_ = self.params_
            params_['units'] = self.units.copy()
            return SimSeries(data=self.to_Series().copy(True), **params_)
        return SimSeries(data=self.to_Series().copy(True), **self.params_)

    def filter(self, conditions=None, **kwargs):
        """
        Returns a filtered SimSeries based on conditions argument.

        To filter over the series simply define the
        condition:
            '>0'

        To set several conditions together the operatos 'and' and 'or'
        are accepted:
            '>0 and <1000'

        To filter only over the index set the condition directly:
            '>0'
        or use the key '.index' or '.i' to refer to the index of the SimSeries.

        To remove null values append '.notnull' to the column name:
            'NAME.notnull'
        To keep only null values append '.null' to the column name:
            'NAME'.null
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
        if 'returnSeries' in kwargs:
            returnFrame = bool(kwargs['returnSeries'])
        if not returnFilter and not returnString and ('returnSeries' not in kwargs or 'returnFrame' not in kwargs):
            returnFrame = True

        specialOperation = ['.notnull', '.null', '.isnull', '.abs']
        numpyOperation = ['.sqrt', '.log10', '.log2', '.log', '.ln']
        pandasAggregation = ['.any', '.all']
        PandasAgg = ''

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
                    filterStr += ' self.as_Series().index'
                # if key is a column
                elif key in self.columns:
                    filterStr = filterStr.rstrip()
                    filterStr += " self.as_Series()['" + key + "']"
                # key might be a wellname, attribute or a pattern
                elif len(self.find_Keys(key)) == 1:
                    filterStr = filterStr.rstrip()
                    filterStr += " self.as_Series()['" + self.find_Keys(key)[0] + "']"
                elif len(self.find_Keys(key)) > 1:
                    filterStr = filterStr.rstrip()
                    filterStr += " self.as_Series()[" + str(list(self.find_Keys(key))) + "]"
                    PandasAgg = '.any(axis=1)'
                else:
                    filterStr += ' ' + key
                filterStr = filterStr.rstrip()
                filterStr += foundSO + foundNO
                key = ''
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
                filterStr += ' )' + PandasAgg + ' ' + conditions[i] + '('
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
                filterStr, key, PandasAgg = KeyToString(filterStr, key, PandasAgg)
                filterStr += conditions[i]
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
                filterStr, key, PandasAgg = KeyToString(filterStr, key, PandasAgg)
                filterStr = filterStr.rstrip()
                filterStr += ' ' + cond
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
                filterStr, key, PandasAgg = KeyToString(filterStr, key, PandasAgg)
                filterStr = filterStr.rstrip()
                filterStr += ' ' + oper
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
            filterStr = 'self.as_Series().index ' + filterStr
        elif filterStr[-1] in ['=', '>', '<', '!']:
            filterStr = filterStr + ' self.as_Series().index'
        # close last parethesis and aggregation
        filterStr += ' )' * bool(AndOrNot + bool(PandasAgg)) + PandasAgg
        # open parenthesis for aggregation, if needed
        if not AndOrNot and bool(PandasAgg):
            filterStr = '(' + filterStr

        retTuple = []

        if returnString:
            retTuple += [filterStr]
        filterArray = eval(filterStr)
        if returnFilter:
            retTuple += [filterArray]
        if returnFrame:
            retTuple += [self.as_Series()[filterArray]]

        if len(retTuple) == 1:
            return retTuple[0]
        else:
            return tuple(retTuple)

    def sort_values(self, axis=0, ascending=True, inplace=False, kind='quicksort',
                    na_position='last', ignore_index=False, key=None):
        if inplace:
            super().sort_values(axis=axis, ascending=ascending, inplace=inplace,
                                kind=kind, na_position=na_position, ignore_index=ignore_index, key=key)
            return None
        else:
            return SimSeries(
                data=self.as_Series().sort_values(axis=axis, ascending=ascending,
                                                  inplace=inplace, kind=kind,
                                                  na_position=na_position,
                                                  ignore_index=ignore_index,
                                                  key=key),
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
        return SimSeries(data=self.as_Series().head(n),
                         **self.params_)

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
        return SimSeries(data=self.as_Series().tail(n),
                         **self.params_)

    def concat(self, objs, axis=0, join='outer', ignore_index=False,
               keys=None, levels=None, names=None, verify_integrity=False,
               sort=False, copy=True, squeeze=True):
        """
        wrapper of pandas.concat enhaced with units support

        Return:
            SimDataFrame
        """
        return self.to_SimDataFrame().concat(
            objs, axis=axis, join=join, ignore_index=ignore_index, keys=keys,
            levels=levels, names=names, verify_integrity=verify_integrity,
            sort=sort, copy=copy, squeeze=squeeze)

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
        return SimSeries(data=self.as_Series().cumsum(skipna=skipna, *args, **kwargs), **self.params_)

    def jitter(self, std=0.10):
        """
        add jitter the values of the SimSeries
        """
        return _jitter(self, std)

    def daily(self, outBy='mean', datetimeIndex=False):
        """
        return a Series with a single row per day.
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
        """
        return self.to_SimDataFrame().daily(outBy=outBy, datetimeIndex=datetimeIndex).to_simseries()

    def monthly(self, outBy='mean', datetimeIndex=False):
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
        """
        return self.to_SimDataFrame().monthly(outBy=outBy, datetimeIndex=datetimeIndex).to_simseries()

    def yearly(self, outBy='mean', datetimeIndex=False):
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

        datetimeIndex : bool
            if True the index will converted to DateTimeIndex with Day=1 and Month=1 for each year
            if False the index will be a MultiIndex (Year,Month)
        """
        return self.to_SimDataFrame().yearly(outBy=outBy, datetimeIndex=datetimeIndex).to_simseries()

    def DaysInYear(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.daysInYear(column=column)

    def daysinyear(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.daysInYear(column=column)

    def daysInYear(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        from .._helpers.daterelated import daysInYear
        params_ = self.params_
        if 'units' in params_:
            if type(params_['units']) is str:
                params_['units'] = 'days'
            else:
                params_['units']['DaysInYear'] = 'days'
        else:
            params_['units'] = 'days'
        params_['name'] = 'DaysInYear'
        params_['index'] = self.index
        if column is not None:
            if type(column) is str and column in self.columns:
                if self[column].dtype in ('int', 'int64') and self[column].min() > 0:
                    return SimSeries(data=daysInYear(self[column].values), **params_)
                elif 'datetime' in str(self[column].dtype):
                    return daysInYear(self[column])
                else:
                    raise ValueError('selected column is not a valid date or year integer')
            elif type(column) is str and column not in self.columns:
                raise ValueError('the selected column is not in this SimDataFrame')
            elif hasattr(column, '__iter__'):
                result = self.SimDataFrame(data={}, index=self.index, **self.params_)
                for col in column:
                    if col in self.columns:
                        result[col] = daysInYear(self[col])
                return result
        else:
            if self.dtype in ('int', 'int64') and self.min() > 0:
                return SimSeries(data=list(daysInYear(self.values)), **params_)
            elif 'datetime' in str(self.dtype):
                return daysInYear(self)
            elif self.index.dtype in ('int', 'int64') and self.index.min() > 0:
                # params_['units'] = self.units.copy() if type(self.units) is dict else self.units
                # params_['name'] = self.name
                # params_['indexName'] = 'DaysInYear'
                # params_['indexUnits'] = 'days'
                return SimSeries(data=list(daysInYear(self.index.to_numpy())), **params_)
            elif 'datetime' in str(self.index.dtype):
                # params_['units'] = self.units.copy() if type(self.units) is dict else self.units
                # params_['name'] = self.name
                # params_['indexName'] = 'DaysInYear'
                # params_['indexUnits'] = 'days'
                return SimSeries(data=list(daysInYear(self.index)), **params_)
            else:
                raise ValueError('index is not a valid date or year integer')

    def RealYear(self, column=None):
        return self.realYear(column)

    def realyear(self, column=None):
        return self.realYear(column)

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
        from .._helpers.daterelated import realYear, daysInYear
        from .frame import SimDataFrame
        params_ = self.params_
        params_['index'] = self.index
        params_['name'] = 'realYear'
        params_['units'] = 'Years'
        if column is not None:
            if type(column) is str and column in self.columns:
                if 'datetime' in str(self[column].dtype):
                    return realYear(self[column])
                else:
                    raise ValueError('selected column is not a valid date format')
            elif type(column) is str and column not in self.columns:
                raise ValueError('the selected column is not in this SimDataFrame')
            elif hasattr(column, '__iter__'):
                result = SimDataFrame(data={}, index=self.index, **self.params_)
                for col in column:
                    if col in self.columns:
                        result[col] = daysInYear(self[col])
                return result
        else:
            if 'datetime' in str(self.index.dtype):
                return SimSeries(data=list(realYear(self.index)), **params_)
            else:
                raise ValueError('index is not a valid date or year integer')

    def integrate(self, method='trapz', at=None):
        """
        Calculates numerical integration, using trapezoidal method,
        or constant value of the columns values over the index values.

        method parameter can be: 'trapz' to use trapezoidal method
                                 'const' to constant vale multiplied
                                         by delta-index

        Returns a new SimSeries
        """
        return self.to_SimDataFrame().integrate(method=method, at=at).to_simseries()

    def differenciate(self, na_position='last'):
        """
        Calculates numerical differentiation of the columns values over the index values.

        Returns a new SimDataFrame
        """
        return self.to_SimDataFrame().differenciate(na_position=na_position).to_simseries()

    def plot(self, y=None, x=None, others=None, **kwargs):
        """
        wrapper of Pandas plot method, with some superpowers

        Parameters
        ----------
        y : string, list or index; optional
            column name to plot. The default is None.
        x : string, optional
            the columns to be used for x coordinates. The default is the index.
        others : SimDataFrame, SimSeries, DataFrame or Series; optional
            other Frames to include in the plot, for the same selected columns. The default is None.
        **kwargs : TYPE
            any other keyword argument for matplolib.

        Returns
        -------
        matplotlib AxesSubplot.
        """
        return self.sdf.plot(y=y, x=x, others=others, **kwargs)

    def info(self, *args, **kwargs):
        """
        .info method implemented for SimSeries for compatibility with SimDataFrame.
        """
        return self.to_SimDataFrame().info()

    def slope(self, x=None, y=None, window=None, slope=True, intercept=False):
        """
        calculates the slope of the series vs its index.

        Calculates the slope of column Y vs column X or vs index if 'x' is None

        Parameters
        ----------
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

        x : kept for compatibility with SimDataFrame
        y : kept for compatibility with SimDataFrame

        Returns
        -------
        numpy array
            The array containing the desired output.

        """
        if window is None and x is not None and y is None:
            window, x = x, None
        params_ = self.params_
        if self.name is not None and len(self.get_units(self.name)) == 1 and self.index_units is not None:
            if type(params_['units']) is dict:
                params_['units'][self.name] = str(self.get_units(self.name)[self.name]) + '/' + str(self.index_units)
            else:
                params_['units'] = str(self.get_units(self.name)[self.name]) + '/' + str(self.index_units)
        params_['name'] = 'slope_of_' + (self.name)
        slopeS = _slope(df=self, x=x, y=y, window=window, slope=slope, intercept=intercept)
        return SimSeries(data=slopeS, index=self.index, **params_)
