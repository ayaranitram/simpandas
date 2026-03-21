# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 22:34:40 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
from simpandas import SimDataFrame, SimSeries
from pandas import DataFrame
from unyts import units as u


def test_units_preservation():
    data = {'A': [1,2,3,4,5],
            'B': [1.0, 2.0, 3.0, 4.0, 5.0],
            'C': [100, 200, 300, 400, 500],
            'D': [3, 6, 12, 24, 36]}
    units_dict = {'A': 'ml',
             'B': 'cc',
             'C': 'cm',
             'D': 'in'}

    sdf = SimDataFrame(data, units=units_dict)
    assert sdf.get_units()['A'] == 'ml'
    assert sdf.get_units()['B'] == 'cc'


def test_direct_unit_arithmetic():
    sdf = SimDataFrame({'C': [100, 200, 300]}, units={'C': 'cm'})
    result = sdf['C'] ** 3
    assert isinstance(result, SimSeries)


def test_copy_preserves_units():
    sdf = SimDataFrame({'a': [1,2]}, units='kg')
    sdf2 = sdf.copy()
    assert sdf2.get_units()['a'] == 'kg'


def test_describe():
    sdf = SimDataFrame({'x': [1,2,3,4,5]}, units='m')
    desc = sdf.describe()
    assert isinstance(desc, SimDataFrame)
