# -*- coding: utf-8 -*-
"""
Created on Thu Sep 29 19:03:52 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.6'
__release__ = 20230104

from pandas import Series, DataFrame
from simpandas import SimSeries


def _get_units(data, units, columns=None):
    """catch units or get from data if it is SimDataFrame or SimSeries"""


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

