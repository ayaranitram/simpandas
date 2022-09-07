# -*- coding: utf-8 -*-
"""
Created on Mon Aug 22 23:11:38 2022

@author: Martin Carlos Araya
"""

__version__ = '0.80.1'
__release__ = 20220822
__all__ = ['SimSeries']

from pandas import Series, DataFrame, DatetimeIndex, Timestamp, Index
import warnings
from sys import getsizeof
from io import StringIO
from shutil import get_terminal_size
from pandas._config import get_option
from pandas.io.formats import console
from pandas.core import indexing
from os.path import commonprefix
import pandas as pd
import fnmatch
import warnings
from pandas import Series, DataFrame, DatetimeIndex, Timestamp, Index
# from pandas.core.groupby.generic import DataFrameGroupBy
# from pandas.core.window.rolling import Rolling
import numpy as np
import datetime as dt
from warnings import warn
import matplotlib.pyplot as plt
from .._common.units import unit  # to use unit.isUnit method
from .._common.units import convertUnit, unitProduct, unitDivision, convertible as convertibleUnits, unitBase
from .._common.slope import slope as _slope
from .._common.stringformat import multisplit, isDate, date as strDate


from ._simseries import SimSeries
from ._simdataframe import SimDataFrame

class _SimLocIndexer(indexing._LocIndexer):
    def __init__(self, *args):
        self.spd = args[1]
        super().__init__(*args)

    def __getitem__(self, *args):
        result = super().__getitem__(*args)
        if isinstance(result,(Series,DataFrame)):
            if type(self.spd) is SimSeries:
                return self.spd._class(data=result, **self.spd._SimParameters)

            elif type(self.spd) is SimDataFrame and type(*args) is not tuple and isinstance(result,Series):
                return self.spd._class(data=dict(zip(result.index,result.values)),index=[result.name], **self.spd._SimParameters)
            elif type(self.spd) is SimDataFrame and type(*args) is not tuple and isinstance(result,DataFrame):
                return self.spd._class(data=result, **self.spd._SimParameters)
            elif type(self.spd) is SimDataFrame and type(*args) is tuple and len(*args) > 1 and type(args[0][-1]) in (list,tuple,slice) and isinstance(result,DataFrame):
                return self.spd._class(data=result, **self.spd._SimParameters)
            else:
                result = self.spd._class(data=result.values,index=result.index, **self.spd._SimParameters)
                result.rename(columns=dict(zip(result.columns,self.spd[[args[0][-1]]].columns)),inplace=True)
                result.set_units(self.spd.get_units(self.spd[[args[0][-1]]].columns))
                return result
        else:
            return result

    def __setitem__(self, key, value):  #, units=None):
        if type(value) in (SimSeries, SimDataFrame):
            value = value.to(self.spd.get_Units())
        if type(value) is SimDataFrame and len(value.index) == 1:
            value = value.to_SimSeries()

        # check if received value is tuple (value,units)
        newUnits = False
        if type(value) is tuple and len(value) == 2:
            if key[1] not in self.spd.columns or not isinstance(self.spd.loc[key],(Series,SimSeries,DataFrame,SimDataFrame)) or (
                    isinstance(self.spd.loc[key],(Series,SimSeries,DataFrame,SimDataFrame)) and type(value[0]) is not str and hasattr(value[0],'__iter__') and len(self.spd.loc[key]) == len(value[0])):
                value, units = value[0], value[1]
                if key[1] not in self.spd.columns or self.spd.get_Units(key[1])[key[1]] is None or self.spd.get_Units(key[1])[key[1]].lower() in ('dimensionless', 'unitless', 'none', ''):
                    newUnits = True
                else:
                    if units == self.spd.get_Units(key[1])[key[1]]:
                        pass
                    elif convertibleUnits(units, self.spd.get_Units(key[1])[key[1]]):
                        value = convertUnit(value,units,self.spd.get_Units(key[1])[key[1]],self.spd.speak)
                    else:
                        warn(' Not able to convert ' + str(units) + ' to ' + str(self.spd.get_Units(key[1])[key[1]]))
        super().__setitem__(key, value)
        if newUnits:
            self.spd.set_Units({key[1]:units})