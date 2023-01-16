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
s0 = Series(
    data=[1/12, 2/12, 0.25, 0.5, 1.0, 1.5, 2.0],
    )
s1 = Series(
    data=[1/12, 2/12, 0.25, 0.5, 1.0, 1.5, 2.0],
    name='room'
    )
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
y = units(1.0, 'yd')
f = units(1.0, 'ft')
i = units(3.0, 'in')
t = units(3.5, 'h')


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
## add
### add SimSeries
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
assert test.name == 'table+cookware:forks'
assert test.units == ss5.units

### add Series
test = ss1+s0
assert (test == ss1.as_pandas() + s0).all()
assert test.name is None
assert test.units == ss1.units

test = ss2+s0
assert (test == ss2.as_pandas() + s0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2+s1
assert (test == ss2.as_pandas() + s1).all()
assert test.name == ss2.name + '+' + s1.name
assert test.units == ss2.units

test = s0+ss1
assert (test == ss1.as_pandas() + s0).all()
assert test.name is None
assert test.units == ss1.units

test = s0+ss2
assert (test == ss2.as_pandas() + s0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = s1+ss2
assert (test == ss2.as_pandas() + s1).all()
assert test.name == s1.name + '+' + ss2.name
assert test.units == ss2.units

### add int
test = ss2 + 0
assert (test == ss2).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 0 + ss2
assert (test == ss2).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2 + 5
assert (test == ss2.to_numpy()+5).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5 + ss2
assert (test == 5+ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units

### add float
test = ss2 + 5.0
assert (test == ss2.to_numpy()+5.0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5.0 + ss2
assert (test == 5.0+ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units

### add Unyt
test = ss2 + y
assert (test == ss2.to_numpy()+1).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = y + ss2
assert (test == 1+ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == y.units

test = ss4 + y
assert (test == ss4.to_numpy()+1*12*3).all()
assert test.name == ss4.name
assert test.units == ss4.units

test = y + ss4
assert (test == 1+ss4.to_numpy()/12/3).all()
assert test.name == ss4.name
assert test.units == y.units

test = f + ss4
assert (test == f.values + ss4.to_numpy()/12).all()
assert test.name == ss4.name
assert test.units == f.units

test = ss4 + f
assert (test == ss4.to_numpy() + f.values*12).all()
assert test.name == ss4.name
assert test.units == ss4.units

test = m + ss3
assert (test == m.values + ss3.to_numpy()*0.3048).all()
assert test.name == ss3.name
assert test.units == m.units

test = ss3 + m
expected = (ss3.to_numpy() + m.values/0.3048).round(6)
assert (abs(test.to_numpy() - expected) < 1e-6).all()
assert test.name == ss3.name
assert test.units == ss3.units



## sub
### sub SimSeries
test = ss1-ss1
assert (test == ss1.as_pandas() - ss1.as_pandas()).all()
assert test.name is None
assert test.units == 'ft'

test = ss1-ss2
assert (test == ss1.to_numpy() - convert(ss2.to_numpy(), ss2.units, ss1.units)).all()
assert test.name == ss2.name
assert test.units == ss1.units

test = ss2-ss1
assert (test == ss2.to_numpy() - convert(ss1.to_numpy(), ss1.units, ss2.units)).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2-ss6
assert (test == ss2.to_numpy() - convert(ss6.to_numpy(), ss6.units, ss2.units)).all()
assert test.name == ss2.name + '-' + ss6.name
assert test.units == ss2.units

test = ss6-ss2
assert (test == ss6.to_numpy() - convert(ss2.to_numpy(), ss2.units, ss6.units)).all()
assert test.name == ss6.name + '-' + ss2.name
assert test.units == ss6.units

test = ss3-ss4
assert (test == ss3.to_numpy() - convert(ss4.to_numpy(), ss4.units, ss3.units)).all()
assert test.name == 'cookware:knifes-forks'
assert test.units == ss3.units

test = ss4-ss3
assert (test == ss4.to_numpy() - convert(ss3.to_numpy(), ss3.units, ss4.units)).all()
assert test.name == 'cookware:forks-knifes'
assert test.units == ss4.units

test = ss4-ss5
assert (test == ss4.to_numpy() - convert(ss5.to_numpy(), ss5.units, ss4.units)).all()
assert test.name == 'cookware-table:forks'
assert test.units == ss4.units

test = ss5-ss4
assert (test == ss5.to_numpy() - convert(ss4.to_numpy(), ss4.units, ss5.units)).all()
assert test.name == 'table-cookware:forks'
assert test.units == ss5.units

### sub Series
test = ss1-s0
assert (test == ss1.as_pandas() - s0).all()
assert test.name is None
assert test.units == ss1.units

test = ss2-s0
assert (test == ss2.as_pandas() - s0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2-s1
assert (test == ss2.as_pandas() - s1).all()
assert test.name == ss2.name + '-' + s1.name
assert test.units == ss2.units

test = s0-ss1
assert (test == ss1.as_pandas() - s0).all()
assert test.name is None
assert test.units == ss1.units

test = s0-ss2
assert (test == s0 - ss2.as_pandas()).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = s1-ss2
assert (test == s1 - ss2.as_pandas()).all()
assert test.name == s1.name + '-' + ss2.name
assert test.units == ss2.units

### sub int
test = ss2 - 0
assert (test == ss2).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 0 - ss2
assert (test == ss2.neg()).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2 - 5
assert (test == ss2.to_numpy()-5).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5 - ss2
assert (test == 5-ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units

### sub float
test = ss2 - 5.0
assert (test == ss2.to_numpy()-5.0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5.0 - ss2
assert (test == 5.0-ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units

### sub Unyt
test = ss2 - y
assert (test == ss2.to_numpy()-1).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = y - ss2
assert (test == 1-ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == y.units

test = ss4 - y
assert (test == ss4.to_numpy()-1*12*3).all()
assert test.name == ss4.name
assert test.units == ss4.units

test = y - ss4
assert (test == 1-ss4.to_numpy()/12/3).all()
assert test.name == ss4.name
assert test.units == y.units

test = f - ss4
assert (test == f.values - ss4.to_numpy()/12).all()
assert test.name == ss4.name
assert test.units == f.units

test = ss4 - f
assert (test == ss4.to_numpy() - f.values*12).all()
assert test.name == ss4.name
assert test.units == ss4.units

test = m - ss3
assert (test == m.values - ss3.to_numpy()*0.3048).all()
assert test.name == ss3.name
assert test.units == m.units

test = ss3 - m
expected = (ss3.to_numpy() - m.values/0.3048).round(6)
assert (abs(test.to_numpy() - expected) < 1e-6).all()
assert test.name == ss3.name
assert test.units == ss3.units



## mul
### mul SimSeries
test = ss1*ss1
assert (test == ss1.as_pandas() * ss1.as_pandas()).all()
assert test.name is None
assert test.units == 'ft2'

test = ss1*ss2
assert (test == ss1.to_numpy() * convert(ss2.to_numpy(), ss2.units, ss1.units)).all()
assert test.name == ss2.name
assert test.units == ss1.units + '2'

test = ss2*ss1
assert (test == ss2.to_numpy() * convert(ss1.to_numpy(), ss1.units, ss2.units)).all()
assert test.name == ss2.name
assert test.units == ss2.units + '2'

test = ss2*ss6
assert (test == ss2.to_numpy() * convert(ss6.to_numpy(), ss6.units, ss2.units)).all()
assert test.name == ss2.name + '*' + ss6.name
assert test.units == ss2.units + '2'

test = ss6*ss2
assert (test == ss6.to_numpy() * convert(ss2.to_numpy(), ss2.units, ss6.units)).all()
assert test.name == ss6.name + '*' + ss2.name
assert test.units == ss6.units + '2'

test = ss3*ss4
assert (test == ss3.to_numpy() * convert(ss4.to_numpy(), ss4.units, ss3.units)).all()
assert test.name == 'cookware:knifes*forks'
assert test.units == ss3.units + '2'

test = ss4*ss3
assert (test == ss4.to_numpy() * convert(ss3.to_numpy(), ss3.units, ss4.units)).all()
assert test.name == 'cookware:forks*knifes'
assert test.units == ss4.units + '2'

test = ss4*ss5
assert (test == ss4.to_numpy() * convert(ss5.to_numpy(), ss5.units, ss4.units)).all()
assert test.name == 'cookware*table:forks'
assert test.units == ss4.units + '2'

test = ss5*ss4
assert (test == ss5.to_numpy() * convert(ss4.to_numpy(), ss4.units, ss5.units)).all()
assert test.name == 'table*cookware:forks'
assert test.units == ss5.units + '2'

### mul Series
test = ss1*s0
assert (test == ss1.as_pandas() * s0).all()
assert test.name is None
assert test.units == ss1.units

test = ss2*s0
assert (test == ss2.as_pandas() * s0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2*s1
assert (test == ss2.as_pandas() * s1).all()
assert test.name == ss2.name + '*' + s1.name
assert test.units == ss2.units

test = s0*ss1
assert (test == ss1.as_pandas() * s0).all()
assert test.name is None
assert test.units == ss1.units

test = s0*ss2
assert (test == ss2.as_pandas() * s0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = s1*ss2
assert (test == ss2.as_pandas() * s1).all()
assert test.name == s1.name + '*' + ss2.name
assert test.units == ss2.units

### mul int
test = ss2 * 0
assert (test == 0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 0 * ss2
assert (test == 0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2 * 1
assert (test == ss2).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 1 * ss2
assert (test == ss2).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2 * 5
assert (test == ss2.to_numpy()*5).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5 * ss2
assert (test == 5*ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units

### mul float
test = ss2 * 5.0
assert (test == ss2.to_numpy()*5.0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5.0 * ss2
assert (test == 5.0*ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units

### mul Unyt
test = ss2 * y
assert (test == ss2.to_numpy()*1).all()
assert test.name == ss2.name
assert test.units == ss2.units + '2'

test = y * ss2
assert (test == 1*ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == y.units + '2'

test = ss4 * y
assert (test == ss4.to_numpy()*1*12*3).all()
assert test.name == ss4.name
assert test.units == ss4.units + '2'

test = y * ss4
assert (test == 1*ss4.to_numpy()/12/3).all()
assert test.name == ss4.name
assert test.units == y.units + '2'

test = f * ss4
assert (test == f.values * ss4.to_numpy()/12).all()
assert test.name == ss4.name
assert test.units == f.units + '2'

test = ss4 * f
assert (test == ss4.to_numpy() * f.values*12).all()
assert test.name == ss4.name
assert test.units == ss4.units + '2'

test = m * ss3
expected = (m.values * ss3.to_numpy()*0.3048).round(6)
assert (test == expected).all()
assert test.name == ss3.name
assert test.units == m.units + '2'

test = ss3 * m
expected = (ss3.to_numpy() * m.values/0.3048).round(6)
assert (test - expected < 1e-6).all()
assert test.name == ss3.name
assert test.units == ss3.units + '2'

test = ss3 * t
assert (test == ss3.to_numpy() * t.values).all()
assert test.name == ss3.name
assert test.units == ss3.units + '*' + t.units

test = t * ss3
assert (test == t.values * ss3.to_numpy()).all()
assert test.name == ss3.name
assert test.units == t.units + '*' + ss3.units



## div
### div SimSeries
test = ss1/ss1
assert (test == ss1.as_pandas() / ss1.as_pandas()).all()
assert test.name is None
assert test.units == 'ft/ft'

test = ss1/ss2
assert (test == ss1.to_numpy() / convert(ss2.to_numpy(), ss2.units, ss1.units)).all()
assert test.name == ss2.name
assert test.units == ss1.units + '/' + ss1.units

test = ss2/ss1
assert (test == ss2.to_numpy() / convert(ss1.to_numpy(), ss1.units, ss2.units)).all()
assert test.name == ss2.name
assert test.units == ss2.units + '/' + ss2.units

test = ss2/ss6
assert (test == ss2.to_numpy() / convert(ss6.to_numpy(), ss6.units, ss2.units)).all()
assert test.name == ss2.name + '/' + ss6.name
assert test.units == ss2.units + '/' + ss2.units

test = ss6/ss2
assert (test == ss6.to_numpy() / convert(ss2.to_numpy(), ss2.units, ss6.units)).all()
assert test.name == ss6.name + '/' + ss2.name
assert test.units == ss6.units + '/' + ss6.units

test = ss3/ss4
assert (test == ss3.to_numpy() / convert(ss4.to_numpy(), ss4.units, ss3.units)).all()
assert test.name == 'cookware:knifes/forks'
assert test.units == ss3.units + '/' + ss3.units

test = ss4/ss3
assert (test == ss4.to_numpy() / convert(ss3.to_numpy(), ss3.units, ss4.units)).all()
assert test.name == 'cookware:forks/knifes'
assert test.units == ss4.units + '/' + ss4.units

test = ss4/ss5
assert (test == ss4.to_numpy() / convert(ss5.to_numpy(), ss5.units, ss4.units)).all()
assert test.name == 'cookware/table:forks'
assert test.units == ss4.units + '/' + ss4.units

test = ss5/ss4
assert (test == ss5.to_numpy() / convert(ss4.to_numpy(), ss4.units, ss5.units)).all()
assert test.name == 'table/cookware:forks'
assert test.units == ss5.units + '/' + ss5.units

### div Series
test = ss1/s0
assert (test == ss1.as_pandas() / s0).all()
assert test.name is None
assert test.units == ss1.units

test = ss2/s0
assert (test == ss2.as_pandas() / s0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2/s1
assert (test == ss2.as_pandas() / s1).all()
assert test.name == ss2.name + '/' + s1.name
assert test.units == ss2.units

test = s0/ss1
assert (test == s0 / ss1.as_pandas()).all()
assert test.name is None
assert test.units == ss1.units + '-1'

test = s0/ss2
assert (test == s0 / ss2.as_pandas()).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

test = s1/ss2
assert (test == s1 / ss2.as_pandas()).all()
assert test.name == s1.name + '/' + ss2.name
assert test.units == ss2.units + '-1'

### div int
test = 0 / ss2
assert (test == 0).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

test = ss2 / 1
assert (test == ss2).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 1 / ss2
assert (test == 1/ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

test = ss2 / 5
assert (test == ss2.to_numpy()/5).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5 / ss2
expected = 5 / ss2.to_numpy()
assert (test - expected < 1e-6).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

### div float
test = ss2 / 5.0
assert (test == ss2.to_numpy()/5.0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5.0 / ss2
expected = 5.0 / ss2.to_numpy()
assert (test - expected < 1e-6).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

### div Unyt
test = ss2 / y
assert (test == ss2.to_numpy()/1).all()
assert test.name == ss2.name
assert test.units == ss2.units + '/' + ss2.units

test = y / ss2
assert (test == y.value/ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units + '/' + ss2.units

test = ss2 / i
expected = ss2.to_numpy() / (i.value/12/3)
assert (test - expected < 1e-6).all()
assert test.name == ss2.name
assert test.units == ss2.units + '/' + ss2.units

test = i / ss2
expected = i.value / (ss2.to_numpy()*3*12)
assert (test == expected).all()
assert test.name == ss2.name
assert test.units == i.units + '/' + i.units

test = ss4 / y
assert (test == ss4.to_numpy()/y.value/12/3).all()
assert test.name == ss4.name
assert test.units == ss4.units + '/' + ss4.units

test = y / ss4
expected = y.value / (ss4.to_numpy()/12/3)
assert (test == expected).all()
assert test.name == ss4.name
assert test.units == y.units + '/' + y.units

test = f / ss4
expected = f.values / (ss4.to_numpy()/12)
assert (test == expected).all()
assert test.name == ss4.name
assert test.units == f.units + '/' + f.units

test = ss4 / f
expected = ss4.to_numpy() / (f.values*12)
assert (test == expected).all()
assert test.name == ss4.name
assert test.units == ss4.units + '/' + ss4.units

test = m / ss3
expected = m.values / (ss3.to_numpy()*0.3048)
assert (test - expected < 1e-6).all()
assert test.name == ss3.name
assert test.units == m.units + '/' + m.units

test = ss3 / m
expected = ss3.to_numpy() / (m.values/0.3048)
assert (test - expected < 1e-6).all()
assert test.name == ss3.name
assert test.units == ss3.units + '/' + ss3.units

test = ss3 / t
assert (test == ss3.to_numpy() / t.values).all()
assert test.name == ss3.name
assert test.units == ss3.units + '/' + t.units

test = t / ss3
expected = t.values / ss3.to_numpy()
assert (test - expected < 1e-6).all()
assert test.name == ss3.name
assert test.units == t.units + '/' + ss3.units



## floordiv
### floordiv SimSeries
test = ss1//s0
assert (test == ss1.as_pandas() // s0).all()
assert test.name is None
assert test.units == ss1.units

test = ss2//s0
assert (test == ss2.as_pandas() // s0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2//s1
assert (test == ss2.as_pandas() // s1).all()
assert test.name == ss2.name + '/' + s1.name
assert test.units == ss2.units

test = s0//ss1
assert (test == s0 // ss1.as_pandas()).all()
assert test.name is None
assert test.units == ss1.units + '-1'

test = s0//ss2
assert (test == s0 // ss2.as_pandas()).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

test = s1//ss2
assert (test == s1 // ss2.as_pandas()).all()
assert test.name == s1.name + '/' + ss2.name
assert test.units == ss2.units + '-1'

### div int
test = 0 // ss2
assert (test == 0).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

test = ss2 // 1
assert (test == ss2).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 1 // ss2
assert (test == 1//ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

test = ss2 // 5
assert (test == ss2.to_numpy()//5).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5 // ss2
expected = 5 // ss2.to_numpy()
assert (test - expected < 1e-6).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

### div float
test = ss2 // 5.0
assert (test == ss2.to_numpy()//5.0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5.0 // ss2
expected = 5.0 // ss2.to_numpy()
assert (test - expected < 1e-6).all()
assert test.name == ss2.name
assert test.units == ss2.units + '-1'

### div Unyt
test = ss2 // y
assert (test == ss2.to_numpy()//1).all()
assert test.name == ss2.name
assert test.units == ss2.units + '/' + ss2.units

test = y // ss2
expected = y.value // ss2.to_numpy()
assert (test == expected).all()
assert test.name == ss2.name
assert test.units == ss2.units + '/' + ss2.units

test = ss2 // i
expected = ss2.to_numpy() // (i.value/12/3)
assert (test - expected < 1e-6).all()
assert test.name == ss2.name
assert test.units == ss2.units + '/' + ss2.units

test = i // ss2
expected = i.value // (ss2.to_numpy()*3*12)
assert (test == expected).all()
assert test.name == ss2.name
assert test.units == i.units + '/' + i.units

test = ss4 // y
expected = ss4.to_numpy() // (y.value*12*3)
assert (test == expected).all()
assert test.name == ss4.name
assert test.units == ss4.units + '/' + ss4.units

test = y // ss4
expected = y.value // (ss4.to_numpy()/12/3)
assert (test == expected).all()
assert test.name == ss4.name
assert test.units == y.units + '/' + y.units

test = f // ss4
expected = f.values // (ss4.to_numpy()/12)
assert (test == expected).all()
assert test.name == ss4.name
assert test.units == f.units + '/' + f.units

test = ss4 // f
expected = ss4.to_numpy() // (f.values*12)
assert (test == expected).all()
assert test.name == ss4.name
assert test.units == ss4.units + '/' + ss4.units

test = m // ss3
expected = m.values // (ss3.to_numpy()*0.3048)
assert (test - expected < 1e-6).all()
assert test.name == ss3.name
assert test.units == m.units + '/' + m.units

test = ss3 // m
expected = ss3.to_numpy() // (m.values/0.3048)
assert (test - expected < 1e-6).all()
assert test.name == ss3.name
assert test.units == ss3.units + '/' + ss3.units

test = ss3 // t
assert (test == ss3.to_numpy() // t.values).all()
assert test.name == ss3.name
assert test.units == ss3.units + '/' + t.units

test = t // ss3
expected = t.values // ss3.to_numpy()
assert (test - expected < 1e-6).all()
assert test.name == ss3.name
assert test.units == t.units + '/' + ss3.units



## mod
### mod SimSeries
test = ss1%ss1
assert (test == ss1.as_pandas() % ss1.as_pandas()).all()
assert test.name is None
assert test.units == ss1.units

test = ss1%ss2
assert (test == ss1.to_numpy() % convert(ss2.to_numpy(), ss2.units, ss1.units)).all()
assert test.name == ss2.name
assert test.units == ss1.units

test = ss2%ss1
assert (test == ss2.to_numpy() % convert(ss1.to_numpy(), ss1.units, ss2.units)).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2%ss6
assert (test == ss2.to_numpy() % convert(ss6.to_numpy(), ss6.units, ss2.units)).all()
assert test.name == ss2.name + '%' + ss6.name
assert test.units == ss2.units

test = ss6%ss2
assert (test == ss6.to_numpy() % convert(ss2.to_numpy(), ss2.units, ss6.units)).all()
assert test.name == ss6.name + '%' + ss2.name
assert test.units == ss6.units

test = ss3%ss4
assert (test == ss3.to_numpy() % convert(ss4.to_numpy(), ss4.units, ss3.units)).all()
assert test.name == 'cookware:knifes%forks'
assert test.units == ss3.units

test = ss4%ss3
assert (test == ss4.to_numpy() % convert(ss3.to_numpy(), ss3.units, ss4.units)).all()
assert test.name == 'cookware:forks%knifes'
assert test.units == ss4.units

test = ss4%ss5
assert (test == ss4.to_numpy() % convert(ss5.to_numpy(), ss5.units, ss4.units)).all()
assert test.name == 'cookware%table:forks'
assert test.units == ss4.units

test = ss5%ss4
assert (test == ss5.to_numpy() % convert(ss4.to_numpy(), ss4.units, ss5.units)).all()
assert test.name == 'table%cookware:forks'
assert test.units == ss5.units

### mod Series
test = ss1%s0
assert (test == ss1.as_pandas() % s0).all()
assert test.name is None
assert test.units == ss1.units

test = ss2%s0
assert (test == ss2.as_pandas() % s0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2%s1
assert (test == ss2.as_pandas() % s1).all()
assert test.name == ss2.name + '%' + s1.name
assert test.units == ss2.units

# test = s0%ss1
# assert (test == ss1.as_pandas() % s0).all()
# assert test.name is None
# assert test.units == ss1.units

# test = s0%ss2
# assert (test == ss2.as_pandas() % s0).all()
# assert test.name == ss2.name
# assert test.units == ss2.units

# test = s1%ss2
# assert (test == ss2.as_pandas() % s1).all()
# assert test.name == s1.name + '%' + ss2.name
# assert test.units == ss2.units

### mul int
test = 0 % ss2
assert (test == 0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2 % 1
assert (test == ss2.to_numpy() % 1).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 1 % ss2
assert (test == 1 % ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = ss2 % 5
assert (test == ss2.to_numpy()%5).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5 % ss2
assert (test == 5%ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units

### mul float
test = ss2 % 5.0
assert (test == ss2.to_numpy()%5.0).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = 5.0 % ss2
assert (test == 5.0%ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == ss2.units

### mul Unyt
test = ss2 % y
assert (test == ss2.to_numpy()%1).all()
assert test.name == ss2.name
assert test.units == ss2.units

test = y % ss2
assert (test == y.value % ss2.to_numpy()).all()
assert test.name == ss2.name
assert test.units == y.units

test = ss4 % y
assert (test == ss4.to_numpy()%(1*12*3)).all()
assert test.name == ss4.name
assert test.units == ss4.units

test = y % ss4
assert (test == y.value % (ss4.to_numpy()/12/3)).all()
assert test.name == ss4.name
assert test.units == y.units

test = f * ss4
assert (test == f.values * ss4.to_numpy()/12).all()
assert test.name == ss4.name
assert test.units == f.units

test = ss4 * f
assert (test == ss4.to_numpy() * f.values*12).all()
assert test.name == ss4.name
assert test.units == ss4.units

test = m * ss3
expected = (m.values * ss3.to_numpy()*0.3048).round(6)
assert (test == expected).all()
assert test.name == ss3.name
assert test.units == m.units

test = ss3 * m
expected = (ss3.to_numpy() * m.values/0.3048).round(6)
assert (test - expected < 1e-6).all()
assert test.name == ss3.name
assert test.units == ss3.units

test = ss3 * t
assert (test == ss3.to_numpy() * t.values).all()
assert test.name == ss3.name
assert test.units == ss3.units + '*' + t.units

test = t * ss3
assert (test == t.values * ss3.to_numpy()).all()
assert test.name == ss3.name
assert test.units == t.units + '*' + ss3.units
