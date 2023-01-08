# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 19:01:26 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas import SimSeries
from pandas import Series

assert type(SimSeries()) is SimSeries
assert len(SimSeries()) == 0

ss1 = SimSeries(
    data=[0.0153, 5.1476, 1.1537, 0.1432, 15.1588],
    units='ft'
    )

ss2 = SimSeries(
    data=[0.25, 73, 20.0, 9.87, 1000.0],
    units='cm',
    name='length'
    )

ss3 = SimSeries(
    data=[0.0153, 5.1476, 1.1537, 0.1432, 15.1588],
    index=range(1,6),
    index_units='m',
    index_name='metros',
    units={'length':'ft'}
    )

# ss4 = SimSeries(
#     data=[0.0153, 5.1476, 1.1537, 0.1432, 15.1588],
#     index=list('abcde'),
#     units={'a':'yd', 'b':'in', 'c':'ft', 'd':'m', 'e':'cm'}
#     )

ss1 + ss2
