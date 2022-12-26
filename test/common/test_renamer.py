# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 18:24:20 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas.common.renamer import left, right, renameLeft, renameRight, commonRename
from simpandas import SimSeries, SimDataFrame
from pandas import Series, DataFrame

s = Series(range(4), index=list('abcd'), name='abcd:0-3')

assert left(s) == {'abcd:0-3': 'abcd:0-3'}
assert right(s) == {'abcd:0-3': 'abcd:0-3'}
assert left(s, ':') == {'abcd:0-3': 'abcd'}
assert right(s, ':') == {'abcd:0-3': '0-3'}
assert left(s, '_') == {'abcd:0-3': 'abcd:0-3'}
assert right(s, '_') == {'abcd:0-3': 'abcd:0-3'}
assert renameLeft(s).name == s.name
assert renameRight(s).name == s.name
assert renameLeft(s, ':').name == s.name.split(':')[0]
assert renameRight(s, ':').name == s.name.split(':')[1]

d = DataFrame({'abcd:0-3': [0, 1, 2, 3], '1234:a-d': list('abcd')}, index=range(4))

assert left(d) == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
assert right(d) == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
assert left(d, ':') == {'abcd:0-3': 'abcd', '1234:a-d': '1234'}
assert right(d, ':') == {'abcd:0-3': '0-3', '1234:a-d': 'a-d'}
assert left(d, '_') == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
assert right(d, '_') == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
assert list(renameLeft(d).columns) == ['abcd:0-3', '1234:a-d']
assert list(renameRight(d).columns) == ['abcd:0-3', '1234:a-d']
assert list(renameLeft(d, ':').columns) == ['abcd', '1234']
assert list(renameRight(d, ':').columns) == ['0-3', 'a-d']

ss = SimSeries(range(4), index=list('abcd'), name='abcd:0-3', units='m', name_separator=':')

assert left(ss) == {'abcd:0-3': 'abcd'}
assert right(ss) == {'abcd:0-3': '0-3'}
assert left(ss, ':') == {'abcd:0-3': 'abcd'}
assert right(ss, ':') == {'abcd:0-3': '0-3'}
assert left(ss, '_') == {'abcd:0-3': 'abcd:0-3'}
assert right(ss, '_') == {'abcd:0-3': 'abcd:0-3'}
assert renameLeft(ss).name == s.name
assert renameRight(ss).name == s.name
assert renameLeft(ss, ':').name == s.name.split(':')[0]
assert renameRight(ss, ':').name == s.name.split(':')[1]

sd = SimDataFrame({'abcd:0-3': [0, 1, 2, 3], '1234:a-d': list('abcd')}, index=range(4), units={'abcd:0-3': 'm', '1234:a-d': ''}, name_separator=':')

assert left(sd) == {'abcd:0-3': 'abcd', '1234:a-d': '1234'}
assert right(sd) == {'abcd:0-3': '0-3', '1234:a-d': 'a-d'}
assert left(sd, ':') == {'abcd:0-3': 'abcd', '1234:a-d': '1234'}
assert right(sd, ':') == {'abcd:0-3': '0-3', '1234:a-d': 'a-d'}
assert left(sd, '_') == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
assert right(sd, '_') == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
assert list(renameLeft(sd).columns) == ['abcd:0-3', '1234:a-d']
assert list(renameRight(d).columns) == ['abcd:0-3', '1234:a-d']
assert list(renameLeft(d, ':').columns) == ['abcd', '1234']
assert list(renameRight(d, ':').columns) == ['0-3', 'a-d']