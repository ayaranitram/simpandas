# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martin Carlos Araya
"""

__version__ = '0.81.6'
__release__ = 20230202
__all__ = ['SimSeries']

from pandas import Series, DataFrame, Index
from io import StringIO
from shutil import get_terminal_size
from pandas._config import get_option
import fnmatch
import numpy as np
import pandas as pd
import warnings

from unyts.converter import convertible as _convertible, convert_for_SimPandas as _converter
from unyts.operations import unit_product as _unit_product, unit_division as _unit_division, unit_base as _unit_base, \
    unit_power as _unit_power, unit_addition as _unit_addition
from unyts.dictionaries import unitless_names as _unitless_names
from unyts import units, is_Unit, Unit

from .basics import SimBasics
from .common.helpers import clean_axis as _clean_axis, string_new_name as _string_new_name
from .common.math import znorm as _znorm, minmaxnorm as _minmaxnorm, jitter as _jitter
from .common.slope import slope as _slope
from .indexer import _SimLocIndexer
from .index import SimIndex

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
                 'spdLocator',
                 'columns',
                 'meta',
                 'source_path',
                 '_auto_append_',
                 '_operate_per_name_',
                 '_transposed_',
                 '_reverse_',]

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
                 meta=None,
                 source_path=None,
                 *args, **kwargs):

        self.units = {}
        self.verbose = bool(verbose)
        self.index_units = None
        self.name_separator = None
        self.intersection_character = intersection_character if type(intersection_character) is str else '∩'
        self.spdLocator = _SimLocIndexer("loc", self)
        self.meta = meta
        self.source_path = source_path
        self._auto_append_ = bool(auto_append)
        self._operate_per_name_ = bool(operate_per_name)
        self._transposed_ = bool(transposed)
        self._reverse_ = kwargs['reverse'] if 'reverse' in kwargs else False

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

        # catch index units if index is instance of SimIndex
        if index_units is None and hasattr(index, 'units'):
            index_units = index.units

        # initialize pd.Series
        super().__init__(data=data, index=index, dtype=dtype, name=name, copy=copy, fastpath=fastpath)

        # get name
        if self.name is None or (type(self.name) is str and self.name.strip() == ''):
            if type(units) is dict and len(units) == 1:
                self.name = list(units.keys())[0]

        self.columns = Index([self.name]) if columns is None else columns

        # set units
        if units is not None:
            self.set_units(units)

        # get index_units
        if index_units is None:
            if self.index.name is not None and self.index.name in self.units:
                self.index_units = self.units[self.index.name]
            elif hasattr(data, 'index_units'):
                self.index_units = data.index_units.copy() if type(data.index_units) is dict else data.index_units
        elif type(index_units) is str:
            self.index_units = index_units
        else:
            raise TypeError("`indexUnitx` must be a string.")

        # override index.name with index_name
        if index_name is not None:
            if type(self.units) is dict and self.index.name in self.units:
                self.units[index_name] = self.units[self.index.name]
            self.index.name = index_name

        # change pd.Index to SimIndex
        self.index = SimIndex(self.index, units=self.index_units)

    @property
    def type(self):
        return 'SimSeries'    

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

    def __call__(self, key=None):
        """
        Returns the series values, a NumPy array or number without units.
        """
        if key is None:
            return self.values
        else:
            return self[key].values

    def __getitem__(self, key=None):
        # ensure self.index is SimIndex
        if not hasattr(self.index, 'units'):
            self.index = SimIndex(self.index, units=self.index_units)
        def index_params_():
            params_ = self.params_.copy()
            params_['name'] = self.index.name
            params_['units'] = self.index.units
            params_['index_name'] = None
            params_['index_units'] = None
            return params_

        if key is None:
            return self
        elif type(key) is str and key.strip() == self.name and not key.strip() in self.index:
            return self
        elif type(key) is str and key == self.index.name:
            params_ = index_params_()
            return SimSeries(data=self.index.to_numpy(),
                             index=range(len(self.index)),
                             **params_)
        elif type(key) is list and key in [[], [self.name]]:
            return self.as_simdataframe()
        elif type(key) is list and key == [self.index.name]:
            params_ = index_params_()
            return SimDataFrame(data={self.index.name: self.index.to_numpy()},
                                index=range(len(self.index)),
                                **params_)
        else:
            try:
                return self.loc[key]
            except KeyError:
                try:
                    return self.iloc[key]
                except IndexError:
                    raise KeyError("the requested Key is not a valid index or name: " + str(key))

    def astype(self, dtype, copy=True, errors='raise'):
        params_ = self.params_.copy()
        params_['dtype'] = dtype
        return self._class(data=self.as_pandas().astype(dtype), **params_)

    def _arithmethic_operation(self, other, operation: str = None, level=None, fill_value=None, axis=0,
                               intersection_character=None):
        def _units_operation(a, b, operation):
            if operation in ['+', '-']:
                return _unit_addition(a, b)
            elif operation in ['*']:
                return _unit_product(a, b)
            elif operation in ['/', '//']:
                return _unit_division(a, b)
            elif operation in ['**']:
                return _unit_power(a, b)
            elif operation in ['%']:
                return a
            else:
                raise ValueError("Unknown operation")

        params_ = self.params_.copy()
        _products = ['*', '/', '//', '%']
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

        # both SimSeries
        if isinstance(other, SimSeries):
            if self.index.name is not None and other.index.name is not None and self.index.name != other.index.name:
                warnings.warn("indexes of both SimSeries are not of the same kind:\n   '" +
                              self.index.name + "' != '" + other.index.name + "'")

            # ensure other.index is SimIndex
            if not hasattr(other.index, 'units'):
                other.index = SimIndex(other.index, units=other.index_units)

            # convert other.index.units if required and possible
            if self.index.units == other.index.units:
                pass
            elif self.index.units not in _unitless_names and other.index.units not in _unitless_names and \
                    _convertible(other.index.units, self.index.units):
                other = other.index_to(self.index.units)

            if type(self.units) is str and type(other.units) is str:
                new_name = _string_new_name(
                    self._common_rename(other, intersection_character=intersection_character, return_names_dict_only=True),
                    intersection_character=intersection_character)
                params_['units'] = _units_operation(self.units, other.units, operation)
                if self.units == other.units:
                    result = op_method(self.as_pandas(), other.as_pandas(), level=level, fill_value=fill_value, axis=axis)
                elif _convertible(other.units, self.units):
                    other_c = _converter(other.as_pandas(), other.units, self.units, self.verbose)
                    result = op_method(self.as_pandas(), other_c, level=level, fill_value=fill_value, axis=axis)
                elif _convertible(self.units, other.units):
                    self_c = _converter(self.as_pandas(), self.units, other.units, self.verbose)
                    result = op_method(other.as_pandas(), self_c, level=level, fill_value=fill_value, axis=axis)
                    params_['units'] = _units_operation(other.units, self.units, operation)
                elif operation in _products and _convertible(_unit_base(other.units), _unit_base(self.units)):
                    other_c = _converter(other.as_pandas(), _unit_base(other.units), _unit_base(self.units),
                                         self.verbose)
                    result = op_method(self.as_pandas(), other_c, level=level, fill_value=fill_value, axis=axis)
                elif operation in _products and _convertible(_unit_base(self.units), _unit_base(other.units)):
                    self_c = _converter(self.as_pandas(), _unit_base(self.units), _unit_base(other.units), self.verbose)
                    result = op_method(other.as_pandas(), self_c, level=level, fill_value=fill_value, axis=axis)
                    params_['units'] = _units_operation(other.units, self.units, operation)
                else:
                    result = op_method(self.as_pandas(), other.as_pandas(), level=level, fill_value=fill_value, axis=axis)
                    if type(self.units) is str and type(other.units) is str:
                        params_['units'] = self.units + operation + other.units
                    elif type(self.units) is dict and len(self.units) == 1 and type(other.units) is str:
                        params_['units'] = self.get_units_string() + operation + other.units
                    elif type(other.units) is dict and len(other.units) == 1 and type(self.units) is str:
                        params_['units'] = self.units + operation + other.get_units_string()
                    elif type(self.units) is dict and len(self.units) == 1 and type(other.units) is dict and len(
                            other.units) == 1:
                        params_['units'] = self.get_units_string() + operation + other.get_units_string()
                    elif type(self.units) is dict and type(other.units) is dict:
                        params_['units'] = self.units.copy()
                        for k, u in other.units.items():
                            if k in params_['units']:
                                params_['units'][k] = params_['units'][k] + operation + u
                            else:
                                params_['units'][k] = u
                    else:
                        raise NotImplementedError(op_label + ' of SimSeries with different units is not implemented.')
                params_['name'] = new_name
                result = self._class(data=result, **params_)
            else:
                raise NotImplementedError

        # other is Pandas Series
        elif isinstance(other, Series):
            result = op_method(self.as_pandas(), other, level=level, fill_value=fill_value, axis=axis)
            new_name = _string_new_name(
                self._common_rename(self._class(other), intersection_character=intersection_character,
                                    return_names_dict_only=True),
                intersection_character=intersection_character)
            params_['name'] = new_name

        # other is int or float
        elif type(other) in (int, float, complex):
            result = op_method(self.as_pandas(), other, level=level, fill_value=fill_value, axis=axis)

        # other is instance of unyts
        elif is_Unit(other):
            if type(self.units) is str:
                if self._reverse_:
                    params_['units'] = _units_operation(other.units, self.units, operation)
                else:
                    params_['units'] = _units_operation(self.units, other.units, operation)
                if _convertible(other.unit, self.units):
                    result = op_method(self.as_pandas(), other.to(self.units).value, level=level, fill_value=fill_value, axis=axis)
                elif operation in _products:
                    result = op_method(self.as_pandas(), other.value, level=level, fill_value=fill_value, axis=axis)
                else:
                    raise NotImplementedError(op_label + " of SimSeries with not convertible Unyts is not implemented.")
            else:
                result = op_method(self.as_simdataframe().as_pandas(), other, level=level, fill_value=fill_value, axis=axis).as_simseries()

        # lets Pandas deal with other types, maintain units, dtype and name
        else:
            result = op_method(self.as_pandas(), other, level=level, fill_value=fill_value, axis=axis)

        if operation in ['//']:
            params_['dtype'] = result.dtype
        else:
            params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
        self._reverse_ = False
        return self._class(data=result, **params_)

    def __add__(self, other):
        return self._arithmethic_operation(other, operation='+', fill_value=0)
    def __sub__(self, other):
        return self._arithmethic_operation(other, operation='-', fill_value=0)

    def __mul__(self, other):
        return self._arithmethic_operation(other, operation='*', fill_value=1)

    def __truediv__(self, other):
        return self._arithmethic_operation(other, operation='/', fill_value=None)

    def __floordiv__(self, other):
        return self._arithmethic_operation(other, operation='//', fill_value=None, intersection_character='/')
    def __mod__(self, other):
        return self._arithmethic_operation(other, operation='%', fill_value=None)

    def __pow__(self, other):
        return self._arithmethic_operation(other, operation='**', fill_value=None)

    def set_index(self, name):
        self.set_index_name(name)

    def set_index_units(self, units):
        if hasattr(units, 'units') and type(units.units) is str:
            units = units.units
        elif hasattr(units, 'unit') and type(units.unit) is str:
            units = units.unit
        if type(units) is str and len(units.strip()) > 0:
            self.index_units = units.strip()
        elif type(units) is dict and len(units) == len(self.index):
            self.index_units = units
        else:
            raise TypeError("`units` must be a string or a dictionary with pair key: units for each item in the index.")
        if not isinstance(self.index, SimIndex) and type(self.index_units) is str:
            self.index = SimIndex(self.index, units=self.index_units)
        elif type(self.index_units) is str:
            self.index.set_units(self.index_units)

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
        returns the SimSeries converted to the requested units if possible, if not, returns the original values.
        """
        if isinstance(units, (Unit, SimSeries)):
            units = units.units
        if type(units) is str and type(self.units) is str:
            if _convertible(self.units, units):
                params_ = self.params_.copy()
                params_['units'] = units
                return self._class(data=_converter(self.as_pandas(), self.units, units, self.verbose), **params_)
            else:
                return self
        elif type(units) is str and type(self.units) is dict and len(set(self.units.values())) == 1:
            params_ = self.params_.copy()
            params_['units'] = units
            return self._class(data=_converter(self.as_pandas(), list(set(self.units.values()))[0], units, self.verbose), **params_)
        elif type(units) is dict:
            return self.to_simdataframe().convert(units).to_simseries()
        else:
            return self

    def reindex(self, index=None, **kwargs):
        """
        wrapper for pandas.Series.reindex

        index : array-like, optional
            New labels / index to conform to, should be specified using keywords.
            Preferably an Index object to avoid duplicating data.
        """
        return SimSeries(data=self.to_pandas().reindex(index=index, **kwargs), **self.params_)


    # not shared methods
    #@property
    #def columns(self):
    #    return Index([self.name])

    def drop(self, labels=None, axis=0, index=None, columns=None, level=None, inplace=False, errors='raise'):
        axis = _clean_axis(axis)
        if inplace:
            super().drop(labels=labels, axis=axis, index=index, columns=columns,
                         level=level, inplace=inplace, errors='errors')
        else:
            return SimSeries(data=self.as_pandas().drop(labels=labels, axis=axis, index=index, columns=columns,
                                                        level=level, inplace=inplace, errors='errors'),
                             **self.params_)

    def dropna(self, axis=0, inplace=False, how=None):
        axis = _clean_axis(axis)
        if inplace:
            super().dropna(axis=axis, inplace=inplace, how=how)
        else:
            return SimSeries(
                data=self.as_pandas().dropna(axis=axis, inplace=inplace, how=how),
                **self.params_)

    def drop_zeros(self, axis=None, inplace=False):
        """
        drop the rows where the values are zeross.
        """
        filt = self.zeros(axis=0)
        if inplace:
            self.drop(columns=filt[filt == True].index, inplace=True)
        else:
            return self.drop(columns=filt[filt == True].index, inplace=False)

    def rms(self, axis=0, **kwargs):
        return units((((self.as_pandas()) ** 2).mean(axis=axis, **kwargs)) ** 0.5,
                     self.get_UnitsString())

    def min(self, axis=0, **kwargs):
        return units(self.as_pandas().min(axis=axis, **kwargs), self.get_UnitsString())

    def max(self, axis=0, **kwargs):
        return units(self.as_pandas().max(axis=axis, **kwargs), self.get_UnitsString())

    def mean(self, axis=0, **kwargs):
        return units(self.as_pandas().mean(axis=axis, **kwargs), self.get_UnitsString())

    def mode(self, axis=0, **kwargs):
        return units(self.as_pandas().mode(axis=axis, **kwargs), self.get_UnitsString())

    def prod(self, axis=0, **kwargs):
        from unyts.operations import unit_base_power
        from unyts.units.unitless import unitless_names
        unit_base, unit_power = unit_base_power(self.get_UnitsString())
        prod_units = unit_base if unit_base in unitless_names else (unit_base + str(unit_power * len(self)))
        return units(self.as_pandas().prod(axis=axis, **kwargs), prod_units)

    def quantile(self, q=0.5, axis=0, **kwargs):
        return units(self.as_pandas().quantile(q, axis=axis, **kwargs), self.get_UnitsString())

    def sum(self, axis=0, **kwargs):
        return units(self.as_pandas().sum(axis=axis, **kwargs), self.get_UnitsString())

    def std(self, axis=0, **kwargs):
        return units(self.as_pandas().std(axis=axis, **kwargs), self.get_UnitsString())

    def var(self, axis=0, **kwargs):
        return units(self.as_pandas().var(axis=axis, **kwargs), self.get_UnitsString())

    def round(self, decimals=0, **kwargs):
        return units(self.as_pandas().round(decimals=decimals, **kwargs), self.get_UnitsString())

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
            if len(index) == 1 and list(index.keys())[0] not in self.index:
                return self.rename(list(index.values())[0], axis=axis, copy=copy, inplace=inplace, level=level,
                                   errors=errors)
            col_before = list(self.index)
            if inplace:
                super().rename(index=index, axis=axis, copy=copy, inplace=inplace, level=level, errors=errors)
                col_after = list(self.index)
            else:
                catch = super().rename(index=index, axis=axis, copy=copy, inplace=inplace, level=level, errors=errors)
                col_after = list(catch.index)

            new_units = {}
            for i in range(len(col_before)):
                new_units[col_after[i]] = self.units[col_before[i]]
            if inplace:
                self.units = new_units
                self.spdLocator = _SimLocIndexer("loc", self)
                return None
            else:
                catch.units = new_units
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
            units_dict = {self.name: 'unitless'}
        elif type(self.units) is str:
            units_dict = {self.name: self.units}
        elif type(self.units) is dict:
            units_dict = {each: (self.units[each] if each in self.units else 'unitless') for each in self.index }
        else:
            units_dict = self.units.copy() if type(self.units) is dict else {self.name: self.units}
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
        if item is not None and type(item) in (str, int, float) and item not in self.columns and item not in self.index:
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
                    return self.set_units(units)
                except:
                    self.units = old_units
                    raise ValueError("not able to process dictionary of units.")
            else:
                raise TypeError("units must be a string.")

        elif type(self.units) is dict:
            if type(units) not in (str, dict) and hasattr(units, '__iter__'):
                if item is not None and type(item) not in (str, dict) and hasattr(item, '__iter__'):
                    if len(item) == len(units):
                        return self.set_units(dict(zip(item, units)))
                    else:
                        raise ValueError("both units and item must have the same length.")
                elif item is None:
                    if len(units) == len(self.columns):
                        return self.set_units(dict(zip(list(self.columns), units)))
                    else:
                        raise ValueError(
                            "units list must be the same length of columns in the SimSeries or must be followed by a list of items.")
                else:
                    raise TypeError("if units is a list, items must be a list of the same length.")
            elif type(units) is dict:
                for k, u in units.items():
                    self.set_units(u, k)
            elif type(units) is str:
                if item is None:
                    self.units = units.strip()
                else:
                    if type(item) not in (str, dict) and hasattr(item, '__iter__'):
                        units = units.strip()
                        for i in item:
                            if i in self.units:
                                self.units[i] = units
                    elif type(item) is str:
                        if item in self.units:
                            self.units[item] = units
                        elif item in self.columns or item in self.index:
                            self.units[item] = units

            if item is None and len(self.columns) > 1:
                raise ValueError("More than one column in this SimSeries, item must not be None")
            elif item is None and len(self.columns) == 1:
                return self.set_units(units, list(self.columns)[0])
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
                elif item in self.index.names:
                    self.units[item] = units.strip()
                elif item in self.index:
                    self.units[item] = units.strip()

    def copy(self):
        if type(self.units) is dict:
            params_ = self.params_.copy()
            params_['units'] = self.units.copy()
            return SimSeries(data=self.as_pandas().copy(True), **params_)
        return SimSeries(data=self.as_pandas().copy(True), **self.params_)

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
        if 'return_series' in kwargs:
            return_frame = bool(kwargs['return_series'])
        if not return_filter and not return_string and ('return_series' not in kwargs or 'return_frame' not in kwargs):
            return_frame = True

        special_operation = ['.notnull', '.null', '.isnull', '.abs']
        numpy_operation = ['.sqrt', '.log10', '.log2', '.log', '.ln']
        pandas_aggregation = ['.any', '.all']
        pandas_agg = ''

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
                filter_str += ' )' + pandas_agg + ' ' + conditions[i] + '('
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
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg)
                filter_str += conditions[i]
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
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg)
                filter_str = filter_str.rstrip()
                filter_str += ' ' + cond
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
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg)
                filter_str = filter_str.rstrip()
                filter_str += ' ' + oper
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
            filter_str = 'self.as_Series().index ' + filter_str
        elif filter_str[-1] in ['=', '>', '<', '!']:
            filter_str = filter_str + ' self.as_Series().index'
        # close last parethesis and aggregation
        filter_str += ' )' * bool(and_or_not + bool(pandas_agg)) + pandas_agg
        # open parenthesis for aggregation, if needed
        if not and_or_not and bool(pandas_agg):
            filter_str = '(' + filter_str

        ret_tuple = []

        if return_string:
            ret_tuple += [filter_str]
        filter_array = eval(filter_str)
        if return_filter:
            ret_tuple += [filter_array]
        if return_frame:
            ret_tuple += [self.as_pandas()[filter_array]]

        if len(ret_tuple) == 1:
            return ret_tuple[0]
        else:
            return tuple(ret_tuple)

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



    def daily(self, agg='mean', datetime_index=False):
        """
        return a Series with a single row per day.
        index must be a date type.

        available grouping calculations are:
            first : keeps the first row per day
            last : keeps the last row per day
            max : returns the maximum value per year
            min : returns the minimum value per year
            mean or avg : returns the average value per year
            median : returns the median value per month
            std : returns the standard deviation per year
            sum : returns the summation of all the values per year
            count : returns the number of rows per year
        """
        return self.to_SimDataFrame().daily(agg=agg, datetime_index=datetime_index).to_simseries()

    def monthly(self, agg='mean', datetime_index=False):
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
            if True the index will be converted to DateTimeIndex with Day=1 for each month
            if False the index will be a MultiIndex (Year,Month)
        """
        return self.to_SimDataFrame().monthly(agg=agg, datetime_index=datetime_index).to_simseries()

    def yearly(self, agg='mean', datetime_index=False):
        """
        return a dataframe with a single row per year.
        index must be a date type.

        available grouping calculations are:
            first : keeps the first row
            last : keeps the last row
            max : returns the maximum value per year
            min : returns the minimum value per year
            mean or avg : returns the average value per year
            median : returns the median value per month
            std : returns the standard deviation per year
            sum : returns the summation of all the values per year
            count : returns the number of rows per year

        datetimeIndex : bool
            if True the index will be converted to DateTimeIndex with Day=1 and Month=1 for each year
            if False the index will be a MultiIndex (Year,Month)
        """
        return self.to_SimDataFrame().yearly(agg=agg, datetime_index=datetime_index).to_simseries()

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
        params_ = self.params_.copy()
        if self.name is not None and len(self.get_units(self.name)) == 1 and self.index_units is not None:
            if type(params_['units']) is dict:
                params_['units'][self.name] = str(self.get_units(self.name)[self.name]) + '/' + str(self.index_units)
            else:
                params_['units'] = str(self.get_units(self.name)[self.name]) + '/' + str(self.index_units)
        params_['name'] = 'slope_of_' + (self.name)
        slope_series= _slope(df=self, x=x, y=y, window=window, slope=slope, intercept=intercept)
        return SimSeries(data=slope_series, index=self.index, **params_)

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
