# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martin Carlos Araya
"""

__version__ = '0.90.12'
__release__ = 20260502
__all__ = ['SimSeries']

import logging

from pandas import Series, DataFrame, Index
from pandas.errors import IndexingError, InvalidIndexError
from io import StringIO
from shutil import get_terminal_size
from pandas._config import get_option
import fnmatch
import warnings

from .common.lazy_unyts import convertible as _convertible, convert_for_SimPandas as _converter, unit_product as _unit_product, unit_division as _unit_division, unit_base as _unit_base, unit_power as _unit_power, unit_addition as _unit_addition, unit_base_power as _unit_base_power, unitless_names as _unitless_names, number, units, is_Unit, Unit

from .basics import SimBasics
from .common.helpers import clean_axis as _clean_axis, string_new_name as _string_new_name
from .common.slope import slope as _slope
from .common.daterelated import is_date_string, to_datetime
from .indexer import _SimLocIndexer, _iSimLocIndexer
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
    units : str, optional
        Units for the Series. Can be any string, but only units accepted by 
        the UnitConverter will be considered for arithmetic operations.
    dtype : str, numpy.dtype, or ExtensionDtype, optional
        Data type to force.
    name : str, optional
        Name of the Series.
    copy : bool, default False
        Copy data from inputs.
    verbose : bool, default False
        Enable verbose logging for operations.
    index_units : str, optional
        Units for the index.
    name_separator : str, default ':'
        Character used to separate name components.
    intersection_character : str, default '&'
        Character used for intersection operations.
    auto_append : bool, default False
        Automatically append units to names.
    operate_per_name : bool, default False
        Perform operations per name component.
    transposed : bool, default False
        Whether the Series is transposed.
    meta : dict, optional
        Additional metadata.
    source_path : str, optional
        Path to the source file.
    return_singles : bool, optional
        Whether to return single values.

    See Also
    --------
    SimDataFrame : Two-dimensional unit-aware DataFrame.
    pandas.Series : Base pandas Series class.

    Truthiness
    ----------
    Because ``SimSeries`` inherits from ``pandas.Series``, evaluating it as a
    boolean (e.g. ``series or {}``) raises ``ValueError`` on multi-element
    series. Use ``series.empty``, ``len(series) == 0``, or an explicit
    ``series if series is not None else {}`` instead.
    
    Examples
    --------
    >>> import simpandas as sp
    >>> s = sp.SimSeries([1, 2, 3], units='m')
    >>> s.get_units()
    'm'
    """
    _metadata = ['units',
                 'verbose',
                 'index_units_',
                 'name_separator',
                 'intersection_character',
                 'spdLocator',
                 'spdiLocator',
                 #'columns',
                 'meta',
                 'source_path',
                 '_auto_append_',
                 '_operate_per_name_',
                 '_transposed_',
                 '_reverse_',
                 '_return_singles_']

    def __init__(self,
                 data=None,
                 index=None,
                 columns=None,
                 units=None,
                 dtype=None,
                 name=None,
                 copy=False,
                 fastpath=False,  # deprecated; kept for API compat but no longer forwarded to pandas
                 verbose=False,
                 index_name=None,
                 index_units=None,
                 name_separator=None,
                 intersection_character=None,
                 auto_append=False,
                 operate_per_name=False,
                 transposed=False,
                 meta=None,
                 source_path=None,
                 return_singles=None,
                 *args, **kwargs):

        # Initialize attributes needed by units property FIRST using object.__setattr__ to bypass pandas
        object.__setattr__(self, '_transposed_', bool(transposed))
        object.__setattr__(self, '_units_', {})
        object.__setattr__(self, 'verbose', bool(verbose))
        object.__setattr__(self, 'index_units_', None)
        object.__setattr__(self, 'name_separator', None)
        object.__setattr__(self, 'intersection_character', intersection_character if type(intersection_character) is str else '&')
        object.__setattr__(self, 'spdLocator', _SimLocIndexer("loc", self))
        object.__setattr__(self, 'spdiLocator', _iSimLocIndexer("iloc", self))
        object.__setattr__(self, 'meta', meta)
        object.__setattr__(self, 'source_path', source_path)
        object.__setattr__(self, '_auto_append_', bool(auto_append))
        object.__setattr__(self, '_operate_per_name_', bool(operate_per_name))
        object.__setattr__(self, '_reverse_', kwargs['reverse'] if 'reverse' in kwargs else False)
        object.__setattr__(self, '_return_singles_', True if return_singles is None else bool(return_singles))

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

        # initialize Series
        super().__init__(data=data, index=index, dtype=dtype, name=name, copy=copy)

        # get name
        if self.name is None or (type(self.name) is str and self.name.strip() == ''):
            if type(units) is dict and len(units) == 1:
                self.name = list(units.keys())[0]

        #self.columns = Index([self.name]) if columns is None else columns

        # set units
        if units is not None:
            self.set_units(units)

        # get index_units
        if index_units is None:
            if self.index.name is not None and self.index.name in self.units:
                self.index_units_ = self.units[self.index.name]
            elif hasattr(data, 'index_units'):
                self.index_units_ = data.index_units.copy() if type(data.index_units) is dict else data.index_units
        elif type(index_units) is str:
            self.index_units_ = index_units
        else:
            raise TypeError("`index_units` must be a string.")

        # override index.name with index_name
        if index_name is not None:
            if type(self.units) is dict and self.index.name in self.units:
                self._units_[index_name] = self.units[self.index.name]
            self.index.name = index_name

        # change Index to SimIndex
        self.index = SimIndex(self.index, units=self.index_units)

    @property
    def _class(self):
        return SimSeries

    @property
    def _constructor(self):
        return _simseries_constructor_with_fallback

    @property
    def _constructor_expanddim(self):
        from simpandas.frame import SimDataFrame
        return SimDataFrame

    @property
    def columns(self):
        return Index([self.name])
    @columns.setter
    def columns(self, columns):
        if type(columns) is str:
            if columns == self.name:
                return
            else:
                self.rename(columns, inplace=True)
        elif hasattr(columns, '__iter__'):
            if len(columns) == 1:
                self.rename(columns[0], inplace=True)
            else:
                raise ValueError(f"SimSeries can only take one column name, {len(columns)} items were received.")
        else:
            self.rename(columns, inplace=True)

    @property
    def units(self):
        """Return units as str, dict, or None (SimSeries backward-compatible behavior).

        SimSeries stores units as a plain string or dict internally.  Returning
        a ColumnUnits here would break the many type(self.units) is str/dict
        checks used throughout series arithmetic and conversion logic.
        """
        if not hasattr(self, '_units_'):
            object.__setattr__(self, '_units_', {})
        raw = self._units_
        if raw is None:
            return None
        if isinstance(raw, str):
            return raw
        if isinstance(raw, dict):
            return raw
        # list (rare for series — positional units)
        if isinstance(raw, list):
            labels = list(self.columns)
            if len(raw) < len(labels):
                raw = list(raw) + [None] * (len(labels) - len(raw))
            elif len(raw) > len(labels):
                raw = raw[:len(labels)]
            return dict(zip(labels, raw))
        return {}

    @units.setter
    def units(self, units) -> None:
        self.set_units(units)

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
            params = self.params_
            params['return_singles'] = False
            return SimDataFrame(
                data=self.values.reshape(1, self.values.size),
                index=[self.name],
                columns=self.index,
                **params)

    def as_simdataframe(self):
        return self.to_simdataframe()

    def as_dict(self, data_only: bool = False) -> dict:
        """Convert this SimSeries to a dictionary.

        Parameters
        ----------
        data_only : bool, default False
            If True, return a plain ``{index_val: raw_value}`` dict (no
            unit metadata — same as ``dict(self)``).
            If False (default), return ``{index_val: unyts_value}`` where
            each value is a ``unyts`` instance carrying its own unit.
            This makes the conversion reversible via ``SimSeries.from_dict()``.

        Returns
        -------
        dict
            When ``data_only=True``: ``{index_val: raw_value, ...}``
            When ``data_only=False``: ``{index_val: unyts_instance, ...}``
            Returns ``{}`` if the series is empty.

        See Also
        --------
        SimSeries.from_dict : Reconstruct a SimSeries from a unyts-valued dict.

        Examples
        --------
        >>> ss = SimSeries([100, 200], index=[0.0, 1.0],
        ...               units='psi', name='BHP')
        >>> d = ss.as_dict()
        >>> d[0.0]
        100_psi
        >>> d[0.0].value
        100
        >>> d[0.0].units
        'psi'
        >>> reconstructed = SimSeries.from_dict(d, name='BHP')
        >>> (reconstructed == ss).all()
        True
        """
        if self.empty:
            return {}

        if data_only:
            return dict(self)

        from .common.lazy_unyts import units as _units

        unit_str = self.units if isinstance(self.units, str) else None
        result = {}
        for idx_val, data_val in self.items():
            if unit_str and unit_str != 'unitless':
                result[idx_val] = _units(data_val, unit_str)
            else:
                result[idx_val] = data_val
        return result

    @classmethod
    def from_dict(cls, d: dict, name: str = None,
                  index_name: str = None, index_units: str = None) -> 'SimSeries':
        """Reconstruct a SimSeries from a dict with unyts-valued entries.

        Parameters
        ----------
        d : dict
            A dict produced by :meth:`as_dict` (``data_only=False``).
            Values may be ``unyts`` instances or plain numbers.
        name : str, optional
            Name for the resulting SimSeries.
        index_name : str, optional
            Name for the index.
        index_units : str, optional
            Units for the index.

        Returns
        -------
        SimSeries

        See Also
        --------
        SimSeries.as_dict : Produce the unyts-valued dict.

        Examples
        --------
        >>> from unyts import units
        >>> d = {0.0: units(100, 'psi'), 1.0: units(200, 'psi')}
        >>> ss = SimSeries.from_dict(d, name='BHP')
        >>> ss.units
        'psi'
        """
        from .common.lazy_unyts import is_Unit

        if not d:
            return cls(data=None, name=name, dtype=object)

        index = list(d.keys())
        values = list(d.values())

        # Extract units from unyts instances if present
        unit_str = None
        raw_values = []
        for v in values:
            if is_Unit(v):
                if unit_str is None:
                    unit_str = v.units
                raw_values.append(v.value)
            else:
                raw_values.append(v)

        return cls(
            data=raw_values,
            index=index,
            units=unit_str,
            name=name,
            index_name=index_name,
            index_units=index_units,
        )

    def __call__(self, key=None):
        """
        Returns the series values, a NumPy array or number without units.

        Special-case: if ``key`` is itself a Series or DataFrame, this
        method is being called by pandas' ``apply_if_callable`` inside
        ``.mask()`` / ``.where()`` / ``.assign()`` etc.  Return ``self``
        so pandas treats this SimSeries as a non-callable value.
        """
        if key is None:
            return self.values
        import pandas as pd
        if isinstance(key, (pd.Series, pd.DataFrame)):
            return self
        return self[key].values

    def __getitem__(self, key=None):
        from .frame import SimDataFrame
        # Use getattr to avoid converting self.index to SimIndex, which breaks
        # regular Index-based access (e.g. index=['a'] after aggregation)
        index_name = getattr(self.index, 'name', None)
        index_units = getattr(self.index, 'units', self.index_units)

        def index_params_():
            params_ = self.params_
            params_['name'] = index_name
            params_['units'] = index_units
            params_['index_name'] = None
            params_['index_units'] = None
            return params_

        if key is None:
            return self
        elif type(key) is str and key not in self.index and key == self.name:
            return self
        elif type(key) is str and index_name is not None and key == index_name:
            params_ = index_params_()
            return SimSeries(data=self.index.to_numpy(),
                             index=range(len(self.index)),
                             **params_)
        elif type(key) is list and key in [[], [self.name]]:
            return self.as_simdataframe()
        elif type(key) is list and index_name is not None and key == [index_name]:
            params_ = index_params_()
            return SimDataFrame(data={index_name: self.index.to_numpy()},
                                index=range(len(self.index)),
                                **params_)
        elif isinstance(key, str) and 'date' in self.index.dtype.name and is_date_string(key) and to_datetime(key, errors='coerce') in self.index:
            result = self.loc[to_datetime(key)]
        else:
            try:
                result = self.loc[key]
            except (KeyError, IndexingError, TypeError):
                try:
                    result = self.iloc[key]
                except (IndexError, KeyError, IndexingError, TypeError):
                    if type(key) is tuple:
                        try:
                            return self[list(key)]
                        except (IndexError, InvalidIndexError):
                            pass
                    try:
                        result = self.as_simdataframe()[key]
                    except:
                        raise KeyError("the requested Key is not a valid index or name: " + str(key))
        if self._return_singles_ and isinstance(result, Series) and len(result) == 1:
            if type(result.iloc[0]) in number:
                result = units(result.iloc[0], result.get_units_string(), name={'index': key, 'name':self.name})
            else:
                result = result.iloc[0]
        return result

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

        self.as_series().to_string(
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

    def __setitem__(self, key, value, units=None):
        if type(value) is tuple and units is None and len(value) == 2 and type(value[1]) in [str, list, dict]:
            value, units = value[0], value[1]
        if units is not None:
            if type(self.units) is str or type(self.units) is dict and self.name in self.units:
                self_units = self.units if type(self.units) is str else self.units[self.name]
                if _convertible(units, self_units):
                    value = _converter(value, units, self_units)
                else:
                    warnings.warn(f"not possible to convert value from {units} to {self_units}")
                    self.units = {i: self.units for i in self.index}
                    self.units[key] = units
            elif key in self.units:
                self.units[key] = units
        super().__setitem__(key, value)

    def _arithmethic_operation(self, other, operation: str=None, level=None, fill_value=None, axis=0,
                               intersection_character=None):
        def _units_operation(a, b, operation):
            if operation in ['+', '-']:
                return _unit_addition(a, b)
            elif operation in ['*']:
                return _unit_product(a, b)
            elif operation in ['/', '//']:
                return _unit_division(a, b)
            elif operation in ['**', '^']:
                return _unit_power(a, b)
            elif operation in ['%']:
                return a
            elif operation in ['==', '!=', '>=', '<=', '>', '<']:
                return 'unitless'
            else:
                raise ValueError("Unknown operation")

        params_ = self.params_
        _products = ['*', '/', '//', '%']
        valid_operations = {
            # operator, Series.method, proposed fill_value
            '+': [Series.add, 'Addition', 0],
            '-': [Series.sub, 'Subtraction', 0],
            '*': [Series.mul, 'Product', 1],
            '/': [Series.truediv, 'Division', None],
            '//': [Series.floordiv, 'Floor Division', None],
            '%': [Series.mod, 'Module', None],
            '**': [Series.pow, 'Power', None],
            '^': [Series.pow, 'Power', None],
            '==': [Series.eq, 'Equality', None],
            '!=': [Series.ne, 'Inequality', None],
            '>=': [Series.ge, 'Greater or Equal', None],
            '<=': [Series.le, 'Lower or Equal', None],
            '>': [Series.gt, 'Greater', None],
            '<': [Series.lt, 'Lower', None],
        }
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

            # calculate the operation, if both have string type units
            if type(self.units) is str and type(other.units) is str:
                new_name = _string_new_name(
                    self._common_rename(other, intersection_character=intersection_character, return_names_dict_only=True),
                    intersection_character=intersection_character)
                params_['units'] = _units_operation(self.units, other.units, operation)
                if self.units == other.units:
                    result = op_method(self.as_pandas(), other.as_pandas(), level=level, fill_value=fill_value, axis=axis)
                elif _convertible(other.units, self.units):
                    other_c = _converter(other.as_pandas(), other.units, self.units,
                                         print_conversion_path=self.verbose)
                    result = op_method(self.as_pandas(), other_c, level=level, fill_value=fill_value, axis=axis)
                elif _convertible(self.units, other.units):
                    self_c = _converter(self.as_pandas(), self.units, other.units,
                                        print_conversion_path=self.verbose)
                    result = op_method(other.as_pandas(), self_c, level=level, fill_value=fill_value, axis=axis)
                    params_['units'] = _units_operation(other.units, self.units, operation)
                elif operation in _products and _convertible(_unit_base(other.units), _unit_base(self.units)):
                    other_c = _converter(other.as_pandas(), _unit_base(other.units), _unit_base(self.units),
                                         print_conversion_path=self.verbose)
                    result = op_method(self.as_pandas(), other_c, level=level, fill_value=fill_value, axis=axis)
                elif operation in _products and _convertible(_unit_base(self.units), _unit_base(other.units)):
                    self_c = _converter(self.as_pandas(), _unit_base(self.units), _unit_base(other.units),
                                        print_conversion_path=self.verbose)
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
                        raise NotImplementedError(f'{op_label} of SimSeries with different units is not implemented.')
                params_['name'] = new_name
                result = self._class(data=result, **params_)
            elif type(self.units) is dict and type(other.units) is dict:
                result = self.to_SimDataFrame()._arithmethic_operation(other.to_SimDataFrame(), operation=operation,
                                                                       level=level, fill_value=fill_value, axis=axis,
                                                                       intersection_character=intersection_character
                                                                       ).to_SimSeries()
            else:
                raise NotImplementedError(f'not implemented operation for SimSeries with {self.units} and {other.units} type of units definition.')

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

        if operation == '//':
            params_['dtype'] = result.dtype
        else:
            params_['dtype'] = self.dtype if result.astype(self.dtype).equals(result) else result.dtype
        self._reverse_ = False
        return self._class(data=result, **params_)

    def _logical_operation(self, other, operation:str=None, level=None, fill_value=None, axis=0, precision:int=None):
        if operation not in ['>', '<', '==', '<=', '>=', '!=']:
            raise ValueError("`operation` must be a string representing a logical operation.")
        operation = {
            '==': Series.eq,
            '!=': Series.ne,
            '>=': Series.ge,
            '<=': Series.le,
            '>': Series.gt,
            '<': Series.lt,
        }[operation]
        if precision is None and _convertible(self.units, other.units):
            return operation(self.as_pandas(), other.to(self.units).as_pandas(),
                             level=level, fill_value=fill_value, axis=axis)
        elif precision is None:
            warnings.warn(f"not possible to convert `other` units ({other.units}) to {self.units}'")
            return operation(self.as_pandas(), other.as_pandas(),
                             level=level, fill_value=fill_value, axis=axis)
        elif type(precision) is not int:
            raise ValueError("`precision` must be an integer.")
        elif _convertible(self.units, other.units):
            return operation(self.as_pandas().round(precision), other.to(self.units).as_pandas().round(precision),
                             level=level, fill_value=fill_value, axis=axis)
        else:
            warnings.warn(f"not possible to convert `other` units ({other.units}) to {self.units}'")
            return operation(self.as_pandas().round(precision), other.as_pandas().round(precision),
                             level=level, fill_value=fill_value, axis=axis)

    def rolling(self, *args, **kwargs):
        """Return a rolling window proxy that preserves SimPandas metadata on outputs."""
        from .frame import _SimWindowProxy
        return _SimWindowProxy(super().rolling(*args, **kwargs), self)

    def expanding(self, *args, **kwargs):
        """Return an expanding window proxy that preserves SimPandas metadata on outputs."""
        from .frame import _SimWindowProxy
        return _SimWindowProxy(super().expanding(*args, **kwargs), self)

    def ewm(self, *args, **kwargs):
        """Return an EWM window proxy that preserves SimPandas metadata on outputs."""
        from .frame import _SimWindowProxy
        return _SimWindowProxy(super().ewm(*args, **kwargs), self)

    def groupby(self, *args, **kwargs):
        """Return a GroupBy proxy that preserves SimPandas metadata on outputs."""
        from .frame import _SimGroupBy
        return _SimGroupBy(super().groupby(*args, **kwargs), self)

    def resample(self, *args, **kwargs):
        """Return a Resample proxy that preserves SimPandas metadata on outputs."""
        from .frame import _SimResampleProxy
        return _SimResampleProxy(super().resample(*args, **kwargs), self)

    def between(self, left, right, inclusive='both'):
        """Return boolean SimSeries indicating whether each element is between left and right."""
        return self._rewrap(self.as_series().between(left, right, inclusive=inclusive))

    def unique(self):
        """Return unique values as a numpy array."""
        return self.as_pandas().unique()

    def astype(self, dtype, copy=True, errors='raise'):
        params_ = self.params_
        params_['dtype'] = dtype
        return self._class(data=self.as_pandas().astype(dtype), **params_)

    def copy(self, deep=True):
        if type(self.units) is dict:
            params_ = self.params_
            params_['units'] = self.units.copy()
            return SimSeries(data=self.as_pandas().copy(deep), **params_)
        return SimSeries(data=self.as_pandas().copy(deep), **self.params_)

    def convert(self, units):
        """
        returns the SimSeries converted to the requested units if possible, if not, returns the original values.
        """
        if isinstance(units, (Unit, SimSeries)):
            units = units.units
        if type(units) is str and type(self.units) is str:
            if _convertible(self.units, units):
                params_ = self.params_
                params_['units'] = units
                return self._class(data=_converter(self.as_pandas(), self.units, units,
                                                   print_conversion_path=self.verbose),
                                   **params_)
            else:
                return self
        elif type(units) is str and type(self.units) is dict and len(set(self.units.values())) == 1:
            params_ = self.params_
            params_['units'] = units
            return self._class(data=_converter(self.as_pandas(), list(set(self.units.values()))[0], units,
                                               print_conversion_path=self.verbose),
                               **params_)
        elif type(units) is dict:
            return self.to_simdataframe().convert(units).to_simseries()
        else:
            return self

    def corr(self, other, method='pearson', min_periods=None):
        return self.as_pandas().corr(other.as_pandas() if isinstance(other, SimSeries) else other,
                                     method=method, min_periods=min_periods)

    def drop(self, labels=None, axis=0, index=None, columns=None, level=None, inplace=False, errors='raise'):
        axis = _clean_axis(axis)
        if inplace:
            super().drop(labels=labels, axis=axis, index=index, columns=columns,
                         level=level, inplace=inplace, errors=errors)
        else:
            return SimSeries(data=self.as_pandas().drop(labels=labels, axis=axis, index=index, columns=columns,
                                                        level=level, inplace=inplace, errors=errors),
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

    def eq(self, other, level=None, fill_value=None, axis=0, precision:int=None):
        return self._logical_operation(other=other, operation='==', level=level, fill_value=fill_value, axis=axis,
                                       precision=precision)
    def ge(self, other, level=None, fill_value=None, axis=0, precision:int=None):
        return self._logical_operation(other=other, operation='>=', level=level, fill_value=fill_value, axis=axis,
                                       precision=precision)

    def gt(self, other, level=None, fill_value=None, axis=0, precision:int=None):
        return self._logical_operation(other=other, operation='>', level=level, fill_value=fill_value, axis=axis,
                                       precision=precision)

    def le(self, other, level=None, fill_value=None, axis=0, precision:int=None):
        return self._logical_operation(other=other, operation='<=', level=level, fill_value=fill_value, axis=axis,
                                       precision=precision)

    def lt(self, other, level=None, fill_value=None, axis=0, precision:int=None):
        return self._logical_operation(other=other, operation='<', level=level, fill_value=fill_value, axis=axis,
                                       precision=precision)

    def ne(self, other, level=None, fill_value=None, axis=0, precision:int=None):
        return self._logical_operation(other=other, operation='!=', level=level, fill_value=fill_value, axis=axis,
                                       precision=precision)

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
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg, special_operation, numpy_operation, pandas_aggregation, caller=self, conditions=conditions)
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
                    filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg, special_operation, numpy_operation, pandas_aggregation, caller=self, conditions=conditions)
                    i = f + 1
                    continue

            # pass blank spaces
            if conditions[i] == ' ':
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg, special_operation, numpy_operation, pandas_aggregation, caller=self, conditions=conditions)
                if len(filter_str) > 0 and filter_str[-1] != ' ':
                    filter_str += ' '
                i += 1
                continue

            # pass parenthesis
            if conditions[i] in ['(', ')']:
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg, special_operation, numpy_operation, pandas_aggregation, caller=self, conditions=conditions)
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
                if key == '':
                    key = 'self.as_series().index'
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg, special_operation, numpy_operation, pandas_aggregation, caller=self, conditions=conditions)
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
                filter_str, key, pandas_agg = key_to_string(filter_str, key, pandas_agg, special_operation, numpy_operation, pandas_aggregation, caller=self, conditions=conditions)
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
            filter_str = 'self.as_series().index ' + filter_str
        elif filter_str[-1] in ['=', '>', '<', '!']:
            filter_str = filter_str + ' self.as_series().index'
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
            filtered = self.as_pandas()[filter_array]
            ret_tuple += [self._rewrap(filtered)]

        if len(ret_tuple) == 1:
            return ret_tuple[0]
        else:
            return tuple(ret_tuple)

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
        unit_base, unit_power = _unit_base_power(self.get_UnitsString())
        prod_units = unit_base
        if unit_base in _unitless_names:
            prod_units = unit_base
        else:
            parenthesis = False
            for s in '*/+-':
                if s in unit_base:
                    parenthesis = True
            if parenthesis:
                prod_units = '(' + unit_base + ')' + str(unit_power * len(self))
            else:
                prod_units = unit_base + str(unit_power * len(self))
        return units(self.as_pandas().prod(axis=axis, **kwargs), prod_units)

    def quantile(self, q=0.5, axis=0, **kwargs):
        return units(self.as_pandas().quantile(q, **kwargs), self.get_UnitsString())

    def sum(self, axis=0, **kwargs):
        return units(self.as_pandas().sum(axis=axis, **kwargs), self.get_UnitsString())

    def std(self, axis=0, **kwargs):
        return units(self.as_pandas().std(axis=axis, **kwargs), self.get_UnitsString())

    def var(self, axis=0, **kwargs):
        return units(self.as_pandas().var(axis=axis, **kwargs), _unit_product(self.get_UnitsString(), self.get_UnitsString()))

    def round(self, decimals=0, **kwargs):
        return units(self.as_pandas().round(decimals=decimals, **kwargs), self.get_UnitsString())

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

    def get_units(self, items=None, include_index=False):
        """
        Returns the units for the SimSeries.

        Parameters
        ----------
        items : str or list of str, optional
            Ignored, this parameter is kept for compatibility with SimDataFrame. The default is None.
        include_index : bool, optional
            When True, the index units (if any) are appended to the returned
            dict under the index name.  Defaults to False so that
            ``SimSeries(data, units=ss.get_units())`` only receives column
            units and does not accidentally inject index units as column units.

        Returns
        -------
        dict
            A dictionary with series.name as key and its units as value.
            When ``include_index=True``, the index name/units pair is also
            included.

        """
        if self.units is None:
            units_dict = {self.name: 'unitless'}
        elif type(self.units) is str or (type(self.units) is dict and len(self.units) == 0):
            units_dict = {self.name: self.units}
        elif type(self.units) is dict:
            units_dict = self.units.copy()
        else:
            raise TypeError("unexpected type of .units attribute")

        if include_index:
            if self.index_units is None:
                pass
            elif self.index.name is None:
                if '_index_' in units_dict and units_dict['_index_'] == self.index_units:
                    self.index_name = '_index_'
                elif '_index_' not in units_dict:
                    self.index_name = '_index_'
                    units_dict['_index_'] = self.index_units
                else:
                    logging.warning("The index of the SimSeries doesn't have a name, and the generic name `_index_` is already in use.")
            elif self.index_name not in units_dict:
                units_dict[self.index_name] = self.index_units
            elif self.index_units != units_dict[self.index_name]:
                if self.index_name not in self.columns:
                    units_dict[self.index_name] = self.index_units
                else:
                    units_dict[str(self.index_name) + '_index_'] = self.index_units
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

        # Handle ColumnUnits: extract the unit for this series' name, or take first
        from .common.units import ColumnUnits
        if isinstance(units, ColumnUnits):
            if self.name is not None and self.name in units:
                units = units[self.name]
            elif len(units) > 0:
                units = units.to_list()[0]
            else:
                units = None

        if self.units is None or type(self.units) is str:
            if units is None:
                object.__setattr__(self, '_units_', None)
                return
            elif type(units) is str:
                object.__setattr__(self, '_units_', units.strip())
                return
            elif type(units) is dict:
                old_units = self.units
                try:
                    object.__setattr__(self, '_units_', {})
                    return self.set_units(units)
                except:
                    object.__setattr__(self, '_units_', old_units)
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
                    try:
                        self.set_units(u, k)
                    except:
                        pass
            elif type(units) is str:
                if item is None:
                    object.__setattr__(self, '_units_', units.strip())
                    return
                else:
                    if type(item) not in (str, dict) and hasattr(item, '__iter__'):
                        units = units.strip()
                        for i in item:
                            if i in self._units_:
                                self._units_[i] = units
                    elif type(item) is str:
                        if item in self._units_:
                            self._units_[item] = units
                        elif item in self.columns or item in self.index:
                            self._units_[item] = units

            if item is None and len(self.columns) > 1:
                raise ValueError("More than one column in this SimSeries, item must not be None")
            elif item is None and type(units) is str and len(self.columns) == 1:
                # assign directly to the sole column instead of recursing
                col = list(self.columns)[0]
                if units is None:
                    self._units_[col] = None
                else:
                    self._units_[col] = units.strip()
                return
            elif item is not None:
                if item in self.columns:
                    if units is None:
                        self._units_[item] = None
                    elif type(units) is str:
                        self._units_[item] = units.strip()
                    else:
                        raise TypeError("units must be a string.")
                if item == self.index.name:
                    self.index_units = units.strip()
                    self._units_[item] = units.strip()
                elif item in self.index.names:
                    self._units_[item] = units.strip()
                elif item in self.index:
                    self._units_[item] = units.strip()

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

    def reindex(self, index=None, **kwargs):
        """
        wrapper for pandas.Series.reindex

        index : array-like, optional
            New labels / index to conform to, should be specified using keywords.
            Preferably an Index object to avoid duplicating data.
        """
        return SimSeries(data=self.to_pandas().reindex(index=index, **kwargs), **self.params_)

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
                object.__setattr__(self, '_units_', new_units)
                self.spdLocator = _SimLocIndexer("loc", self)
                return None
            else:
                catch.units = new_units
                catch.spdLocator = _SimLocIndexer("loc", catch)
                return catch
        elif type(index) in (str, int, float):
            if inplace:
                self.name = index.strip()
                self.spdLocator = _SimLocIndexer("loc", self)
                return None
            else:
                catch = self.copy()
                catch.name = index
                catch.spdLocator = _SimLocIndexer("loc", catch)
                return catch
        else:
            return self

    def set_index(self, name):
        self.set_index_name(name)

    def get_index_units(self):
        if not isinstance(self.index, SimIndex) and type(self.index_units_) in [dict, str]:
            self.index = SimIndex(self.index, units=self.index_units_)
        elif isinstance(self.index, SimIndex) and (type(self.index.units) is str and len(self.index.units) > 0
                or type(self.index.units) is dict):
            self.index_units_ = self.index.units
        return self.index_units_

    def set_index_units(self, units):
        if hasattr(units, 'units') and type(units.units) is str:
            units = units.units
        elif hasattr(units, 'unit') and type(units.unit) is str:
            units = units.unit
        if type(units) is str and len(units.strip()) > 0:
            self.index_units_ = units.strip()
        elif type(units) is dict and len(units) == len(self.index):
            self.index_units_ = units.copy()
        else:
            raise TypeError("`units` must be a string or a dictionary with pair key: units for each item in the index.")
        if not isinstance(self.index, SimIndex) and type(self.index_units_) in [dict, str]:
            self.index = SimIndex(self.index, units=self.index_units_)
        elif type(self.index_units_) in [dict, str]:
            self.index.units = self.index_units_

    def transpose(self):
        return self

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
        if self.name is not None and len(str(self.get_units(self.name))) == 1 and self.index_units is not None:
            unit_val = self.get_units(self.name)
            if isinstance(unit_val, dict):
                unit_val = unit_val.get(self.name)
            if type(params_['units']) is dict:
                params_['units'][self.name] = str(unit_val) + '/' + str(self.index_units)
            else:
                params_['units'] = str(unit_val) + '/' + str(self.index_units)
        params_['name'] = 'slope_of_' + (self.name)
        slope_series= _slope(df=self, x=x, y=y, window=window, slope=slope, intercept=intercept)
        return SimSeries(data=slope_series, index=self.index, **params_)

    def sort_values(self, axis=0, ascending=True, inplace=False, kind='quicksort',
                    na_position='last', ignore_index=False, key=None):
        if inplace:
            super().sort_values(axis=axis, ascending=ascending, inplace=inplace,
                                kind=kind, na_position=na_position, ignore_index=ignore_index, key=key)
            return None
        else:
            return SimSeries(
                data=self.as_series().sort_values(axis=axis, ascending=ascending,
                                                  inplace=inplace, kind=kind,
                                                  na_position=na_position,
                                                  ignore_index=ignore_index,
                                                  key=key),
                **self.params_)

    def plot(self, y=None, x=None, others=None, label=None, **kwargs):
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
        label : str, optional
            Override the legend label for this series in the chart.
            When provided, replaces the default series name in the legend.
        **kwargs : TYPE
            any other keyword argument for matplolib.

        Returns
        -------
        matplotlib AxesSubplot.
        """
        return self.sdf.plot(y=y, x=x, others=others, labels=[label] if label is not None else None, **kwargs)
