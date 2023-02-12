# -*- coding: utf-8 -*-
"""
Created on Mon Aug 22 23:11:38 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.83.0'
__release__ = 20230111
__all__ = ['_SimLocIndexer']

from pandas.core.indexing import _LocIndexer  #, _iLocIndexer
import pandas as pd
from warnings import warn
from unyts.converter import convertible as _convertible, convert_for_SimPandas as _converter
from unyts import units, Unit
from unyts.helpers.common_classes import number

class _SimLocIndexer(_LocIndexer):

    def __init__(self, *args):
        from .frame import SimDataFrame
        from .series import SimSeries
        self.spd = args[1]
        super().__init__(*args)

    def __getitem__(self, *args):
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        result = super().__getitem__(*args)
        if isinstance(result, pd.Series) and len(result) == 1:
            result = result.iloc[0]
        if isinstance(result, (pd.Series, pd.DataFrame)):
            if type(self.spd) is SimSeries:
                return self.spd._class(data=result, **self.spd.params_)
            elif type(self.spd) is SimDataFrame and type(*args) is not tuple and isinstance(result, pd.Series):
                return self.spd._class(data=dict(zip(result.index,result.values)),index=[result.name], **self.spd.params_)
            elif type(self.spd) is SimDataFrame and type(*args) is not tuple and isinstance(result, pd.DataFrame):
                return self.spd._class(data=result, **self.spd.params_)
            elif type(self.spd) is SimDataFrame and type(*args) is tuple and len(*args) > 1 and type(args[0][-1]) in (list,tuple,slice) and isinstance(result, pd.DataFrame):
                return self.spd._class(data=result, **self.spd.params_)
            else:
                result = self.spd._class(data=result.values,index=result.index, **self.spd.params_)
                result.rename(columns=dict(zip(result.columns,self.spd[[args[0][-1]]].columns)),inplace=True)
                result.set_units(self.spd.get_units(self.spd[[args[0][-1]]].columns))
                return result
        elif type(result) in number:
            return units(result, self.spd.get_units_string(args[0]))
        else:
            return result

    def __setitem__(self, key, value):  #, units=None):
        from .frame import SimDataFrame
        from .series import SimSeries
        if isinstance(value, Unit):
            if key[1] in self.spd.columns and self.spd.get_units_string(key[1]) is not None:
                value = value.to(self.spd.get_units_string(key[1])).value
            elif key[1] in self.spd.columns and self.spd.get_units_string(key[1]) is None:
                value = value.value
            else:  # if key[1] not in self.spd.columns:
                value = (value.value, value.unit)

        elif type(value) in (SimSeries, SimDataFrame):
            value = value.to(self.spd.get_units())
        if type(value) is SimDataFrame and len(value.index) == 1:
            value = value.to_SimSeries()

        # check if received value is tuple (value, units)
        newUnits = False
        if type(value) is tuple and len(value) == 2:
            if key[1] not in self.spd.columns or not isinstance(self.spd.loc[key], (pd.Series, SimSeries, pd.DataFrame, SimDataFrame)) or (
                    isinstance(self.spd.loc[key], (pd.Series, SimSeries, pd.DataFrame, SimDataFrame)) and type(value[0]) is not str and hasattr(value[0],'__iter__') and len(self.spd.loc[key]) == len(value[0])):
                value, units = value[0], value[1]
                if key[1] not in self.spd.columns or self.spd.get_units(key[1])[key[1]] is None or self.spd.get_units(key[1])[key[1]].lower() in ('dimensionless', 'unitless', 'none', ''):
                    newUnits = True
                else:
                    if units == self.spd.get_units(key[1])[key[1]]:
                        pass
                    elif _convertible(units, self.spd.get_units(key[1])[key[1]]):
                        value = _converter(value, units, self.spd.get_units(key[1])[key[1]], self.spd.verbose)
                    else:
                        warn(' Not able to convert ' + str(units) + ' to ' + str(self.spd.get_units(key[1])[key[1]]))
        super().__setitem__(key, value)
        if newUnits:
            self.spd.set_units({key[1]:units})

# class _iSimLocIndexer(_iLocIndexer):
#     def __init__(self, *args):
#         self.spd = args[1]
#         super().__init__(*args)

#     def __getitem__(self, *args):
#         result = super().__getitem__(*args)
#         if isinstance(result,(Series,DataFrame)):
#             if type(self.spd) is SimSeries:
#                 return self.spd._class(data=result, **self.spd._SimParameters)

#             elif type(self.spd) is SimDataFrame and type(*args) is not tuple and isinstance(result, Series):
#                 return self.spd._class(data=dict(zip(result.index,result.values)),index=[result.name], **self.spd._SimParameters)
#             elif type(self.spd) is SimDataFrame and type(*args) is not tuple and isinstance(result, DataFrame):
#                 return self.spd._class(data=result, **self.spd._SimParameters)
#             elif type(self.spd) is SimDataFrame and type(*args) is tuple and len(*args) > 1 and type(args[0][-1]) in (list,tuple,slice) and isinstance(result, DataFrame):
#                 return self.spd._class(data=result, **self.spd._SimParameters)
#             else:
#                 result = self.spd._class(data=result.values,index=result.index, **self.spd._SimParameters)
#                 result.rename(columns=dict(zip(result.columns,self.spd[[args[0][-1]]].columns)),inplace=True)
#                 result.set_units(self.spd.get_units(self.spd[[args[0][-1]]].columns))
#                 return result
#         else:
#             return result

#     def __setitem__(self, key, value):  #, units=None):
#         if type(value) in (SimSeries,SimDataFrame):
#             value = value.to(self.spd.get_Units())
#         if type(value) is SimDataFrame and len(value.index) == 1:
#             value = value.to_SimSeries()

#         # check if received value is tuple (value,units)
#         if type(value) is tuple and len(value) == 2:
#             if not isinstance(self.spd.loc[key], (Series,SimSeries,DataFrame,SimDataFrame)) or (
#                     isinstance(self.spd.loc[key], (Series,SimSeries,DataFrame,SimDataFrame)) and type(value[0]) is not str and not hasattr(value[0],'__iter__') and len(self.spd.loc[key]) == len(value[0])):
#                 value, units = value[0], value[1]
#                 if key[1] not in self.spd.columns or self.spd.get_Units(key[1])[key[1]] is None or self.spd.get_Units(key[1])[key[1]].lower() in ('dimensionless', 'unitless', 'none', ''):
#                     newUnits = True
#                 else:
#                     newUnits = False
#                     if _convertibleUnits(units, self.spd.get_Units(key[1])):
#                         value = convertUnits(value,units,self.spd.get_Units(key[1]))
#         super().__setitem__(key, value)
#         if newUnits:
#             self.spd.set_Units({key[1]:units})


# class SimRolling(Rolling):
#     def __init__(self, df, window, min_periods=None, center=False, win_type=None, on=None, axis=0, closed=None, method='single', SimParameters=None):
#         super().__init__(window, min_periods=min_periods, center=center, win_type=win_type, on=on, axis=axis, closed=closed, method=method)
#         self.params_ =  SimParameters

#     def _resolve_output(self, out: DataFrame, obj: DataFrame) -> DataFrame:
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
