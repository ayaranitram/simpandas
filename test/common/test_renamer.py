# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 18:24:20 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas.common.renamer import left, right, rename_left, rename_right, common_rename, deduplicate_column_names
from simpandas import SimSeries, SimDataFrame
from pandas import Series, DataFrame

s = Series(range(4), index=list('abcd'), name='abcd:0-3')
d = DataFrame({'abcd:0-3': [0, 1, 2, 3], '1234:a-d': list('abcd')}, index=range(4))
ss = SimSeries(range(4), index=list('abcd'), name='abcd:0-3', units='m', name_separator=':')
sd = SimDataFrame({'abcd:0-3': [0, 1, 2, 3], '1234:a-d': list('abcd')}, index=range(4),
                  units={'abcd:0-3': 'm', '1234:a-d': ''}, name_separator=':')


def test_left():
    assert left(s) == {'abcd:0-3': 'abcd:0-3'}
    assert left(s, ':') == {'abcd:0-3': 'abcd'}
    assert left(s, '_') == {'abcd:0-3': 'abcd:0-3'}
    assert left(d) == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
    assert left(d, ':') == {'abcd:0-3': 'abcd', '1234:a-d': '1234'}
    assert left(d, '_') == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
    assert left(ss) == {'abcd:0-3': 'abcd'}
    assert left(ss, ':') == {'abcd:0-3': 'abcd'}
    assert left(ss, '_') == {'abcd:0-3': 'abcd:0-3'}
    assert left(sd) == {'abcd:0-3': 'abcd', '1234:a-d': '1234'}
    assert left(sd, ':') == {'abcd:0-3': 'abcd', '1234:a-d': '1234'}
    assert left(sd, '_') == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}


def test_right():
    assert right(s) == {'abcd:0-3': 'abcd:0-3'}
    assert right(s, ':') == {'abcd:0-3': '0-3'}
    assert right(s, '_') == {'abcd:0-3': 'abcd:0-3'}
    assert right(d) == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
    assert right(d, ':') == {'abcd:0-3': '0-3', '1234:a-d': 'a-d'}
    assert right(d, '_') == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}
    assert right(ss) == {'abcd:0-3': '0-3'}
    assert right(ss, ':') == {'abcd:0-3': '0-3'}
    assert right(ss, '_') == {'abcd:0-3': 'abcd:0-3'}
    assert right(sd) == {'abcd:0-3': '0-3', '1234:a-d': 'a-d'}
    assert right(sd, ':') == {'abcd:0-3': '0-3', '1234:a-d': 'a-d'}
    assert right(sd, '_') == {'abcd:0-3': 'abcd:0-3', '1234:a-d': '1234:a-d'}


def test_rename_left():
    assert rename_left(s).name == s.name
    assert rename_left(s, ':').name == s.name.split(':')[0]
    assert rename_left(ss).name == s.name.split(':')[0]
    assert rename_left(ss, ':').name == s.name.split(':')[0]
    assert rename_left(ss, '_').name == s.name
    assert list(rename_left(d).columns) == ['abcd:0-3', '1234:a-d']
    assert list(rename_left(d, ':').columns) == ['abcd', '1234']
    assert list(rename_left(sd).columns) == ['abcd', '1234']
    assert list(rename_left(sd, ':').columns) == ['abcd', '1234']
    assert list(rename_left(sd, '_').columns) == ['abcd:0-3', '1234:a-d']


def test_rename_right():
    assert rename_right(s).name == s.name
    assert rename_right(s, ':').name == s.name.split(':')[1]
    assert rename_right(ss).name == s.name.split(':')[1]
    assert rename_right(ss, ':').name == s.name.split(':')[1]
    assert rename_right(ss, '_').name == s.name
    assert list(rename_right(d).columns) == ['abcd:0-3', '1234:a-d']
    assert list(rename_right(d, ':').columns) == ['0-3', 'a-d']
    assert list(rename_right(sd).columns) == ['0-3', 'a-d']
    assert list(rename_right(sd, ':').columns) == ['0-3', 'a-d']
    assert list(rename_right(sd, '_').columns) == ['abcd:0-3', '1234:a-d']


df1 = DataFrame(data={'p1:a1': [1, 2, 3], 'p1:a2': [3, 4, 5]})
df2 = DataFrame(data={'p2:a1': [1, 2, 3], 'p2:a2': [3, 4, 5]})
df3 = DataFrame(data={'p1:a1': [1, 2, 3], 'p2:a1': [5, 6, 7]})
df4 = DataFrame(data={'p1:a2': [1, 2, 3], 'p2:a2': [5, 6, 7]})


def test_common_rename():
    test = common_rename(df1, df2, name_separator_1=':', name_separator_2=':', return_names_dict_only=True)
    assert test == {'a1': 'p1&p2:a1', 'a2': 'p1&p2:a2'}

    test = common_rename(df1, df2, name_separator_1=':', name_separator_2=':', complex_names=True)
    assert list(test[0].columns) == ['p1&p2:a1', 'p1&p2:a2']
    assert list(test[1].columns) == ['p1&p2:a1', 'p1&p2:a2']
    assert test[2] == {'a1': 'p1&p2:a1', 'a2': 'p1&p2:a2'}

    test = common_rename(df1, df2, name_separator_1=':', name_separator_2=':')
    assert list(test[0].columns) == ['a1', 'a2']
    assert list(test[1].columns) == ['a1', 'a2']
    assert test[2] == {'a1': 'p1&p2:a1', 'a2': 'p1&p2:a2'}

    test = common_rename(df3, df4, name_separator_1=':', name_separator_2=':', return_names_dict_only=True)
    assert test == {'p1': 'p1:a1&a2', 'p2': 'p2:a1&a2'}

    test = common_rename(df3, df4, name_separator_1=':', name_separator_2=':', complex_names=True)
    assert list(test[0].columns) == ['p1', 'p2']
    assert list(test[1].columns) == ['p1', 'p2']
    assert test[2] == {'p1': 'p1:a1&a2', 'p2': 'p2:a1&a2'}

    test = common_rename(df3, df4, name_separator_1=':', name_separator_2=':')
    assert list(test[0].columns) == ['p1', 'p2']
    assert list(test[1].columns) == ['p1', 'p2']
    assert test[2] == {'p1': 'p1:a1&a2', 'p2': 'p2:a1&a2'}

    test = common_rename(df1, df3, name_separator_1=':', name_separator_2=':')
    assert list(test[0].columns) == ['p1:a1', 'p1:a2']
    assert list(test[1].columns) == ['p1:a1', 'p2:a1']


# ===========================================================================
# deduplicate_column_names tests
# ===========================================================================

def test_deduplicate_no_duplicates():
    names = ['A', 'B', 'C']
    assert deduplicate_column_names(names) == ['A', 'B', 'C']


def test_deduplicate_simple_duplicates():
    assert deduplicate_column_names(['A', 'B', 'A', 'A']) == ['A', 'B', 'A_1', 'A_2']


def test_deduplicate_all_same():
    assert deduplicate_column_names(['X', 'X', 'X']) == ['X', 'X_1', 'X_2']


def test_deduplicate_collision_guard():
    # 'A_1' already exists, so the renamed 'A' should skip to 'A_2'
    assert deduplicate_column_names(['A', 'A_1', 'A']) == ['A', 'A_1', 'A_2']


def test_deduplicate_empty():
    assert deduplicate_column_names([]) == []


def test_deduplicate_single():
    assert deduplicate_column_names(['only']) == ['only']


def test_deduplicate_preserves_first_occurrence():
    result = deduplicate_column_names(['BHP', 'BHP', 'BHP'])
    assert result[0] == 'BHP'
    assert result[1] == 'BHP_1'
    assert result[2] == 'BHP_2'
    assert len(result) == len(set(result)), 'result must have no duplicates'
