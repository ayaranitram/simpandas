# -*- coding: utf-8 -*-
"""
Created on Thu Sep 29 19:03:52 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.6'
__release__ = 20230104

from pandas import Series, DataFrame
from simpandas import SimSeries, SimDataFrame
from simpandas.common.units import ColumnUnits


def _get_units(data, units, columns=None):
    """catch units or get from data if it is SimDataFrame or SimSeries"""
    if units is not None:
        if isinstance(units, (dict, ColumnUnits)):
            return units
        if isinstance(units, str):
            if columns is not None:
                return {col: units for col in columns}
            return units
        return units
    if hasattr(data, 'get_units'):
        return data.get_units()
    if hasattr(data, 'units'):
        return data.units
    return {}


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

    if type(indexInput) in (Series, DataFrame) and type(indexInput.name) is str and len(data.index.name) > 0:
        indexInput = indexInput.name

    elif type(data) in (SimSeries, SimDataFrame) and type(data.index.name) is str and len(data.index.name) > 0:
        indexInput = data.index.name

    return indexInput
