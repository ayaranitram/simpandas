# -*- coding: utf-8 -*-
"""
Created on Thu Sep 29 19:03:52 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.6'
__release__ = 20220927

import pandas as pd

def _get_units(data, units, columns=None):
    # catch units or get from data if it is SimDataFrame or SimSeries

    if units is None and hasattr(data, 'units'):
        try:
            return data.get_units()
        except:
            pass

    if hasattr(units, '__len__') and len(units) == 0:
        return 'unitless'

    if type(units) is dict and len(units) > 0:
        if isinstance(data, Series):
            return {data.name: }
        elif isinstance(data, DataFrame):
            return {col: 'unitless' for col in data.columns}
        elif type(data) is dict:
            return {key: 'unitless' for key in data.keys()}






    uName = None

    uDict = None
    if type(units) is dict and len(units) > 0:
        uDict, units = units, None
        if len(uDict) == 1:
            if type(uDict[list(uDict.keys())[0]]) is str:
                uName = list(uDict.keys())[0]
                units = uDict[uName].strip()

    elif type(units) is str and len(units.strip()) > 0:
        self.units = units.strip()
    elif (units is None or (type(units) is dict and len(units) > 0)) and (type(data) is SimSeries and data.units is not None):
        if type(data.units) is str:
            units = data.units
            if indexUnits is None:
                indexUnits = data.index_units
                self.index_units = indexUnits
        elif type(data.units) is dict:
            units = data.units.copy()
            if data.index.name not in units:
                    units[data.index.name] = data.index_units
    else:
        self.units = 'unitless'


def _get_index_atts(data=None, index=None, units=None, **kwargs):
    """
    get the input data, index and units and return the index with its name and units
    """

    # catch index attributes from input parameters
    indexInput = None
    if index is not None:
        indexInput = index
    elif 'index' in kwargs and kwargs['index'] is not None:
        indexInput = kwargs['index']
    elif len(args) >= 3 and args[2] is not None:
        indexInput = args[2]

    if type(indexInput) in (Series, DataFrame) and type(indexInput.name) is str and len(data.index.name) > 0:
            indexInput = indexInput.name

    elif type(data) in (SimSeries, SimDataFrame) and type(data.index.name) is str and len(data.index.name) > 0:
        indexInput = data.index.name
        self.index_units = data.index_units.copy() if type(data.index_units) is dict else data.index_units