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


# prepare SimSeries
ss1 = SimSeries(
    data=[1/12, 2/12, 0.25, 0.5, 1.0, 1.5, 2.0],
    units='ft',
    )
ss2 = SimSeries(
    data=[1, 2, 3, 6, 12, 18, 24],
    units='yd',
    name='garden',
    )
ss3 = SimSeries(
    data=[1/12, 2/12, 0.25, 0.5, 1.0, 1.5, 2.0],
    units='ft',
    name='cookware:knifes'
    )
ss4 = SimSeries(
    data=[1, 2, 3, 6, 12, 18, 24],
    units='in',
    name='cookware:forks',
    )
ss5 = SimSeries(
    data=[1, 2, 3, 6, 12, 18, 24],
    units='in',
    name='table:forks',
    )
ss6 = SimSeries(
    data=[1, 2, 3, 6, 12, 18, 24],
    units='m',
    name='pool',
    )
m = units(1.0, 'm')
z = units(0.0, 'mm')
i = units(1.0, 'yd')
f = units(1.0, 'ft')


# call the series to return the values
assert ss1(5) == 1.5
assert ss2(2) == 3
assert (ss1() == ss1.values).all()


# get item
assert ss1[5] == units(1.5, 'ft')
assert ss2[0] == units(1, 'yd')
assert (ss2[1:3] == SimSeries(data=[2, 3, 6], units='in', index=[1, 2, 3])).all()
assert (ss2[1:3] == SimSeries(data=ss2.to_pandas().loc[1:3], units='in')).all()

# operations with SimSeries
# add
test = ss1+ss1
assert (test == ss1.as_pandas() + ss1.as_pandas()).all()
assert test.name is None
assert test.units == 'ft'

test = ss1+ss2
assert (test == ss1.to_numpy() + convert(ss2.to_numpy(), ss2.units, ss1.units)).all()
assert test.name == ss2.name
assert test.units == ss1.units

test = ss2+ss1
assert (test == ss2.to_numpy() + convert(ss1.to_numpy(), ss1.units, ss2.units)).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2+ss6
assert (test == ss2.to_numpy() + convert(ss6.to_numpy(), ss6.units, ss2.units)).all()
assert test.name == ss2.name + '+' + ss6.name
assert test.units == ss2.units

test = ss6+ss2
assert (test == ss6.to_numpy() + convert(ss2.to_numpy(), ss2.units, ss6.units)).all()
assert test.name == ss6.name + '+' + ss2.name
assert test.units == ss6.units

test = ss3+ss4
assert (test == ss3.to_numpy() + convert(ss4.to_numpy(), ss4.units, ss3.units)).all()
assert test.name == 'cookware:knifes+forks'
assert test.units == ss3.units

test = ss4+ss3
assert (test == ss4.to_numpy() + convert(ss3.to_numpy(), ss3.units, ss4.units)).all()
assert test.name == 'cookware:forks+knifes'
assert test.units == ss4.units

test = ss4+ss5
assert (test == ss4.to_numpy() + convert(ss5.to_numpy(), ss5.units, ss4.units)).all()
assert test.name == 'cookware+table:forks'
assert test.units == ss4.units

test = ss5+ss4
assert (test == ss5.to_numpy() + convert(ss4.to_numpy(), ss4.units, ss5.units)).all()
assert (ss5+ss4).name == 'table+cookware:forks'
assert test.units == ss5.units

test = ss2 + 0
assert (test == ss2).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 0 + ss2
assert (test == ss2).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2 + i
assert (test == ss2.to_numpy()+1).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = i + ss2
assert (test == 1+ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == i.units

test = ss4 + i
assert (test == ss4.to_numpy()+1*12*3).all()
assert test.name == ss4.name
assert test.units == ss4.units

test = i + ss4
assert (test == 1+ss4.to_numpy()/12/3).all()
assert test.name == ss4.name
assert test.units == i.units



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
assert ((ss1 * f) == ss1).all()
assert (ss1 * f).units == 'ft2'
assert ((ss1 / f) == ss1).all()
assert (ss1 / f).units == 'ft/ft'
assert ((ss1 // f) == ss1.astype(int)).all()
assert (ss1 // f).units == 'ft/ft'
assert ((ss1 ** f) == ss1).all()
assert (ss1 ** f).units == 'ft^ft'


