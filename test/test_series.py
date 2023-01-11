# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 19:01:26 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas import SimSeries
from pandas import Series
import numpy as np
from unyts import convert, units

# assert default parameters
assert type(SimSeries()) is SimSeries
assert len(SimSeries()) == 0
assert SimSeries().units == {}
assert SimSeries().verbose is False
assert SimSeries().index_units is None
assert SimSeries().name_separator == ':'
assert SimSeries().intersection_character == '∩'
assert SimSeries().auto_append is False
assert SimSeries().operate_per_name is False
assert SimSeries().transposed is False
assert str(SimSeries().dtype) == 'object'
assert SimSeries()._class is SimSeries

# prepare a SimSeries
ss1 = SimSeries(
    data=[0.0153, 5.1476, 1.1537, 0.1432, 15.1588],
    units='ft',
    )
ss2 = SimSeries(
    data=[0.25, 73, 20.0, 9.87, 1000.0],
    units='in',
    name='length',
    )
u = units(1.0, 'm')
z = units(0.0, 'mm')
ft = units(1.0, 'yd')

# get item
ss1[1]

# operations with SimSeries
assert ((ss1 + 0) == ss1).all()
assert ((ss1 - 0) == ss1).all()
assert ((ss1 * 1) == ss1).all()
assert ((ss1 / 1) == ss1).all()
assert ((ss1 // 1) == ss1.astype(int)).all()
assert ((ss1 ** 1) == ss1).all()
assert (ss1 ** 1).units == 'ft'
assert ((ss1 ** 2) == ss1.as_pandas() ** 2).all()
assert (ss1 ** 2).units == 'ft2'


assert ((ss1 + z) == ss1).all()
assert ((ss1 - z) == ss1).all()
assert ((ss1 * ft) == ss1).all()
assert (ss1 * ft).units == 'ft2'
assert ((ss1 / ft) == ss1).all()
assert (ss1 / ft).units == 'ft/ft'
assert ((ss1 // ft) == ss1.astype(int)).all()
assert (ss1 // ft).units == 'ft/ft'
assert ((ss1 ** ft) == ss1).all()
assert (ss1 ** ft).units == 'ft^ft'


ss3 = SimSeries(
    data=[0.0153, 5.1476, 1.1537, 0.1432, 15.1588],
    index=range(1, 6),
    index_units='m',
    index_name='metros',
    units={'length': 'ft'}
    )

# ss4 = SimSeries(
#     data=[0.0153, 5.1476, 1.1537, 0.1432, 15.1588],
#     index=list('abcde'),
#     units={'a':'yd', 'b':'in', 'c':'ft', 'd':'m', 'e':'cm'}
#     )

