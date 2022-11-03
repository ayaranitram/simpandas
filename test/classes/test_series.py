# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 19:01:26 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas import SimSeries
from pandas import Series

data = {
    'col1': list(range(5)),
    'col2': [0.0153, 5.1476, 1.1537, 0.1432, 15.1588],
    'col3': list('abcde')
    }

units = {
    'col1': 'l',
    'col2': 'ft',
    }



assert type(SimSeries()) is SimSeries
assert len(SimSeries()) == 0

ss = SimSeries(
    data=[0.0153, 5.1476, 1.1537, 0.1432, 15.1588],
    units='ft'
    )