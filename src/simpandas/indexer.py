# -*- coding: utf-8 -*-
"""
Created on Mon Aug 22 23:11:38 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.91.0'
__release__ = 20260503
__all__ = ['_SimLocIndexer']

import logging
from pandas.core.indexing import _LocIndexer, _iLocIndexer
import pandas as pd
from .common.lazy_unyts import convertible as _convertible, convert_for_SimPandas as _converter, units, Unit
from .common.daterelated import is_date_string, to_datetime
from .common.units import ColumnUnits

logging.basicConfig(level=logging.INFO)


class _SimBaseIndexer(object):
    """Shared logic for SimSeries/SimDataFrame indexers.

    Provides _postprocess which wraps pandas outputs back into Sim types and
    handles unit tagging of scalars.
    """
    def _postprocess(self, result, args):
        """Convert raw pandas/indexer output into appropriate Sim object.

        Parameters
        ----------
        result : any
            Value returned by pandas indexing.
        args : tuple
            Original arguments passed to the indexer (used for unit lookup).
        """
        from .frame import SimDataFrame, _series_to_frame
        from .series import SimSeries
        if isinstance(result, pd.Series) and len(result) == 1:
            result = result.iloc[0]
        # if the result is a scalar number, wrap it with units
        from numbers import Number
        if isinstance(result, Number):

            key = args[0]

            def _get_series_value_unit(ser):
                try:
                    units_map = ser.get_units()
                except Exception:
                    return None

                if ser.name is not None:
                    if isinstance(units_map, (dict, ColumnUnits)) and ser.name in units_map:
                        return units_map[ser.name]

                # prefer a non-index unit if possible
                if isinstance(units_map, (dict, ColumnUnits)):
                    index_keys = {getattr(ser, 'index_name', None), '_index_'}
                    for ukey, uval in units_map.items():
                        if ukey in index_keys:
                            continue
                        return uval
                return None

            unit_str = None
            if isinstance(self.spd, SimSeries):
                unit_str = _get_series_value_unit(self.spd)

                # If we have a date-like key lookup (index selection), we should not use index/date units for value conversion.
                if isinstance(unit_str, str) and unit_str.lower() in ('date', 'datetime'):
                    unit_str = None

                if unit_str is None:
                    if self.spd.name is not None:
                        tmp = self.spd.get_units_string(self.spd.name)
                    else:
                        tmp = self.spd.get_units_string()

                    if isinstance(tmp, str) and tmp.lower() not in ('date', 'datetime'):
                        unit_str = tmp

            elif isinstance(key, tuple) and len(key) >= 2:
                unit_str = self.spd.get_units_string(key[1])
            else:
                unit_str = self.spd.get_units_string(key)

            # if somehow unit_str is still index-related, avoid converting date-index string to Date
            if isinstance(unit_str, str) and unit_str.lower() in ('date', 'datetime'):
                # try value unit if available but not date/datetime
                alt_unit = None
                if isinstance(self.spd, SimSeries):
                    alt_unit = _get_series_value_unit(self.spd)
                    if isinstance(alt_unit, str) and alt_unit.lower() in ('date', 'datetime'):
                        alt_unit = None

                if alt_unit is not None:
                    unit_str = alt_unit
                else:
                    unit_str = None

            if isinstance(unit_str, str):
                return units(result, unit_str)
            return result  # no valid unit string, return raw scalar
        if isinstance(result, (pd.Series, pd.DataFrame)):
            if type(result) is pd.DataFrame:
                return SimDataFrame(data=result, **self.spd.params_)
            if type(self.spd) is SimSeries:
                return SimSeries(data=result, **self.spd.params_)
            elif type(args[0]) is not tuple and isinstance(result, pd.Series):  # type(self.spd) is SimDataFrame
                return _series_to_frame(result, self.spd.params_)
            elif type(args[0]) is tuple and len(args[0]) == 2:
                return SimSeries(data=result, **self.spd.params_)
            else:
                return self.spd._class(data=result, **self.spd.params_)
        else:
            return result


class _SimLocIndexer(_SimBaseIndexer, _LocIndexer):
    """Enhanced ``.loc`` indexer for Sim objects.

    Overrides ``__getitem__`` and ``__setitem__`` to perform unit conversion,
    propagate metadata and support setting tuples ``(value, unit)``.
    """

    def __init__(self, *args):
        # args[1] is the SimSeries/SimDataFrame instance
        self.spd = args[1]
        super().__init__(*args)

    def __getitem__(self, *args):
        """Indexing access for ``.loc``.

        Converts SimSeries arguments to pandas before delegating, then
        postprocesses the result.
        """
        from .frame import SimDataFrame, _series_to_frame
        from .series import SimSeries
        if type(args[0]) is SimSeries:
            if len(args) > 1:
                args = (args[0].as_pandas(), ) + args[1:]
            else:
                args = (args[0].as_pandas(), )
        if type(args[0]) is not slice and type(args[0]) is tuple and len(args[0]) == 2:
            row_key, col_key = args[0]
            if isinstance(col_key, str) and col_key not in self.spd.columns:
                try:
                    maybe_col = self.spd[col_key]
                    if isinstance(maybe_col, SimSeries):
                        result = self.spd.as_pandas().loc[row_key, maybe_col.name]
                    elif isinstance(maybe_col, SimDataFrame):
                        result = self.spd.as_pandas().loc[row_key, list(maybe_col.columns)]
                    else:
                        result = self.spd.as_pandas().loc[args[0]]
                except Exception:
                    result = self.spd.as_pandas().loc[args[0]]
            else:
                result = self.spd.as_pandas().loc[args[0]]
        elif 'date' in self.spd.index.dtype.name and ('date' in args[0].dtype.name if hasattr(args[0], 'dtype') else '') and args[0] in self.spd.index:
            result = self.spd.as_pandas().loc[args[0]]
        elif 'date' in self.spd.index.dtype.name and isinstance(args[0], str) and is_date_string(args[0]) and to_datetime(args[0], errors='coerce') in self.spd.index:
            result = self.spd.as_pandas().loc[to_datetime(args[0], errors='coerce')]
        else:
            result = super().__getitem__(*args)
        return self._postprocess(result, args)

    def __setitem__(self, key, value):
        from .frame import SimDataFrame
        from .series import SimSeries
        if isinstance(value, Unit):
            if len(key) > 1 and key[1] in self.spd.columns and self.spd.get_units_string(key[1]) is not None:
                value = value.to(self.spd.get_units_string(key[1]))
                if hasattr(value, 'value'):
                    value = value.value
            elif len(key) > 1 and key[1] in self.spd.columns and self.spd.get_units_string(key[1]) is None:
                value = value.value
            else:  # if key[1] not in self.spd.columns:
                value = (value.value, value.unit)
        elif type(value) in (SimSeries, SimDataFrame):
            value = value.to(self.spd.get_units())
        if type(value) is SimDataFrame and len(value.index) == 1:
            value = value.to_SimSeries()

        if type(key) is tuple and type(key[0]) is SimSeries:
            if len(key) > 1:
                key = (key[0].as_pandas(), ) + key[1:]
            else:
                key = (key[0].as_pandas(), )
        elif type(key) is SimSeries:
            key = key.as_pandas()

        # check if received value is tuple (value, units)
        new_units = False
        if type(key) is tuple and len(key) >= 2 and type(value) is tuple and len(value) == 2:
            _target = self.spd.as_pandas().loc[key] if key[1] in self.spd.columns else None
            if key[1] not in self.spd.columns or not isinstance(_target,
                                                                (pd.Series, pd.DataFrame)) or (
                    isinstance(_target, (pd.Series, pd.DataFrame)) and type(
                value[0]) is not str and hasattr(value[0], '__iter__') and len(_target) == len(value[0])):
                value, new_unit_str = value[0], value[1]
                existing_unit = self.spd.get_units_string(key[1]) if key[1] in self.spd.columns else None
                if key[1] not in self.spd.columns or existing_unit is None or \
                        existing_unit.lower() in ('dimensionless', 'unitless', 'none', ''):
                    new_units = True
                else:
                    if new_unit_str == existing_unit:
                        pass
                    elif _convertible(new_unit_str, existing_unit):
                        value = _converter(value, new_unit_str, existing_unit,
                                           print_conversion_path=self.spd.verbose)
                    else:
                        logging.warning(' Not able to convert ' + str(new_unit_str) + ' to ' + str(existing_unit))
        super().__setitem__(key, value)
        if new_units:
            self.spd.set_units({key[1]: new_unit_str})


class _iSimLocIndexer(_SimBaseIndexer, _iLocIndexer):
    """Enhanced ``.iloc`` indexer for Sim objects.

    Works similarly to ``_SimLocIndexer`` but uses integer positional
    indexing.
    """
    def __init__(self, *args):
        self.spd = args[1]
        super().__init__(*args)

    def __getitem__(self, *args):
        """Get item via positional index.
        """
        result = self.spd.as_pandas().iloc[args[0]]
        return self._postprocess(result, args)

    def __setitem__(self, key, value):
        from .frame import SimDataFrame
        from .series import SimSeries
        if type(value) in (SimSeries, SimDataFrame):
            value = value.to(self.spd.get_units())
        if type(value) is SimDataFrame and len(value.index) == 1:
            value = value.to_SimSeries()

        # check if received value is tuple (value,units)
        new_units = False
        if type(key) is tuple and len(key) >= 2 and type(value) is tuple and len(value) == 2:
            col_name = self.spd.columns[key[1]] if isinstance(key[1], int) else key[1]
            _target = self.spd.as_pandas().iloc[key]
            if not isinstance(_target, (pd.Series, pd.DataFrame)) or (
                    isinstance(_target, (pd.Series, pd.DataFrame)) and type(
                value[0]) is not str and hasattr(value[0], '__iter__') and len(_target) == len(value[0])):
                value, new_unit_str = value[0], value[1]
                existing_unit = self.spd.get_units_string(col_name) if col_name in self.spd.columns else None
                if col_name not in self.spd.columns or existing_unit is None or \
                        existing_unit.lower() in ('dimensionless', 'unitless', 'none', ''):
                    new_units = True
                else:
                    if _convertible(new_unit_str, existing_unit):
                        value = _converter(value, new_unit_str, existing_unit,
                                           print_conversion_path=self.spd.verbose)
        super().__setitem__(key, value)
        if new_units:
            self.spd.set_units({col_name: new_unit_str})

# class SimRolling(Rolling):
#     def __init__(self, df, window, min_periods=None, center=False, win_type=None, on=None, axis=0, closed=None, method='single', SimParameters=None):
#         super().__init__(window, min_periods=min_periods, center=center, win_type=win_type, on=on, axis=axis, closed=closed, method=method)
#         self.params_ =  SimParameters

#     def _resolve_output(self, out: pd.DataFrame, obj: pd.DataFrame) -> pd.DataFrame:
#         from pandas.core.base import DataError
#         """Validate and finalize result."""
#         if out.shape[1] == 0 and obj.shape[1] > 0:
#             raise DataError("No numeric types to aggregate")
#         elif out.shape[1] == 0:
#             return obj.astype("float64")

#         self._insert_on_column(out, obj)
#         if self.params__ is not None:
#             out =  SimDataFrame(out, **self.params_)
#         return out
