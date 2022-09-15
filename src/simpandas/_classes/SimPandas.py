#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martin Carlos Araya
"""

__version__ = '0.80.1'
__release__ = 20220907
__all__ = ['SimSeries', 'SimDataFrame', 'znorm', 'minmaxnorm']

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
from unyts._convert import convertUnit_for_SimPandas as convertUnit
from unyts._operations import unitProduct, unitDivision, unitBase
from unyts._convert import convertible as convertibleUnits
#from .._common.units import convertUnit, unitProduct, unitDivision, convertible as convertibleUnits, unitBase
from .._common.slope import slope as _slope
from .._common.stringformat import multisplit, isDate, date as strDate
from .._common.merger import merge_Index