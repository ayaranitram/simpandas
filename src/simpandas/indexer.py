# -*- coding: utf-8 -*-
"""
Created on Mon Aug 22 23:11:38 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.83.2'
__release__ = 20230221
__all__ = ['_SimLocIndexer']

import logging
from pandas.core.indexing import _LocIndexer, _iLocIndexer
import pandas as pd
from unyts.converter import convertible as _convertible, convert_for_SimPandas as _converter
from unyts import units, Unit
from unyts.helpers.common_classes import number

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


class _SimBaseIndexer(object):
    def _postprocess(self, result, args):
        from .frame import SimDataFrame, _series_to_frame
        from .series import SimSeries
        if isinstance(result, pd.Series) and len(result) == 1:
            result = result.iloc[0]
        if type(result) in number:
            return units(result, self.spd.get_units_string(args[0]))
        if isinstance(result, (pd.Series, pd.DataFrame)):
            if type(result) is pd.DataFrame:
                return SimDataFrame(data=result, **self.spd.params_)
            if type(self.spd) is SimSeries:
                return SimSeries(data=result, **self.spd.params_)
            elif type(*args) is not tuple and isinstance(result, pd.Series):  # type(self.spd) is SimDataFrame
                return _series_to_frame(result, self.spd.params_)
            elif type(*args) is tuple and len(*args) == 2:
                return SimSeries(data=result, **self.spd.params_)
            else:
                return self.spd._class(data=result, **self.spd.params_)
        else:
            return result


class _SimLocIndexer(_SimBaseIndexer, _LocIndexer):

    def __init__(self, *args):
        self.spd = args[1]
        super().__init__(*args)

    def __getitem__(self, *args):
        from .frame import SimDataFrame, _series_to_frame
        from .series import SimSeries
        if type(args[0]) is SimSeries:
            if len(args) > 1:
                args = (args[0].as_pandas(), ) + args[1:]
            else:
                args = (args[0].as_pandas(), )
        elif type(args) is SimSeries:
            args = args.as_pandas()
        if type(args[0]) is not slice and type(args[0]) is tuple and len(args[0]) == 2:
            result = super().__getitem__(args[0][0])
            if type(self.spd) is SimDataFrame and type(result) is SimSeries:
                result = _series_to_frame(result, self.spd.params_)
            return result.__getitem__(args[0][1])
        else:
            result = super().__getitem__(*args)
        return self._postprocess(result, args)

    def __setitem__(self, key, value):
        from .frame import SimDataFrame
        from .series import SimSeries
        if isinstance(value, Unit):
            if len(key) > 1 and key[1] in self.spd.columns and self.spd.get_units_string(key[1]) is not None:
                value = value.to(self.spd.get_units_string(key[1])).value
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
        if type(value) is tuple and len(value) == 2:
            if key[1] not in self.spd.columns or not isinstance(self.spd.loc[key],
                                                                (pd.Series, SimSeries, pd.DataFrame, SimDataFrame)) or (
                    isinstance(self.spd.loc[key], (pd.Series, SimSeries, pd.DataFrame, SimDataFrame)) and type(
                value[0]) is not str and hasattr(value[0], '__iter__') and len(self.spd.loc[key]) == len(value[0])):
                value, units = value[0], value[1]
                if key[1] not in self.spd.columns or self.spd.get_units(key[1])[key[1]] is None or \
                        self.spd.get_units(key[1])[key[1]].lower() in ('dimensionless', 'unitless', 'none', ''):
                    new_units = True
                else:
                    if units == self.spd.get_units(key[1])[key[1]]:
                        pass
                    elif _convertible(units, self.spd.get_units(key[1])[key[1]]):
                        value = _converter(value, units, self.spd.get_units(key[1])[key[1]],
                                           print_conversion_path=self.spd.verbose)
                    else:
                        logging.warning(' Not able to convert ' + str(units) + ' to ' + str(self.spd.get_units(key[1])[key[1]]))
        super().__setitem__(key, value)
        if new_units:
            self.spd.set_units({key[1]: units})


class _iSimLocIndexer(_SimBaseIndexer, _iLocIndexer):
    def __init__(self, *args):
        self.spd = args[1]
        super().__init__(*args)

    def __getitem__(self, *args):
        result = self.spd.as_pandas().iloc[args[0]]
        return self._postprocess(result, args)

    def __setitem__(self, key, value):
        from .frame import SimDataFrame
        from .series import SimSeries
        if type(value) in (pd.SimSeries, pd.SimDataFrame):
            value = value.to(self.spd.get_Units())
        if type(value) is SimDataFrame and len(value.index) == 1:
            value = value.to_SimSeries()

        # check if received value is tuple (value,units)
        if type(value) is tuple and len(value) == 2:
            if not isinstance(self.spd.loc[key], (pd.Series, SimSeries, pd.DataFrame, SimDataFrame)) or (
                    isinstance(self.spd.loc[key], (pd.Series, SimSeries, pd.DataFrame, SimDataFrame)) and type(
                value[0]) is not str and not hasattr(value[0], '__iter__') and len(self.spd.loc[key]) == len(value[0])):
                value, units = value[0], value[1]
                if key[1] not in self.spd.columns or self.spd.get_Units(key[1])[key[1]] is None or \
                        self.spd.get_Units(key[1])[key[1]].lower() in ('dimensionless', 'unitless', 'none', ''):
                    new_units = True
                else:
                    new_units = False
                    if _convertible(units, self.spd.get_Units(key[1])):
                        value = _converter(value, units, self.spd.get_Units(key[1]),
                                           print_conversion_path=self.spd.verbose)
        super().__setitem__(key, value)
        if new_units:
            self.spd.set_Units({key[1]: units})

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
