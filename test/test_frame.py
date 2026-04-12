# -*- coding: utf-8 -*-
"""
Created on Thu Nov 17 00:32:09 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
from simpandas import SimDataFrame, SimSeries
import pandas as pd


def test_basic_creation():
    df = SimDataFrame({'a':[1,2,3]}, units='m')
    assert isinstance(df, SimDataFrame)
    assert df.get_units()['a']=='m'
    assert df.to_pandas().equals(pd.DataFrame({'a':[1,2,3]}))


def test_head_tail():
    df = SimDataFrame({'a':[1,2,3,4,5]}, units='kg')
    assert df.head(2).shape[0]==2
    assert df.tail(2).shape[0]==2


def test_arithmetic():
    df = SimDataFrame({'x':[1,2],'y':[3,4]}, units={'x':'m','y':'m'})
    s = df.add(df)
    assert 'x' in s
    assert s['x'].iloc[0]==2


def test_concat():
    df1 = SimDataFrame({'a':[1]}, units='m')
    df2 = SimDataFrame({'a':[2]}, units='m')
    out = df1.concat(df2)
    assert isinstance(out, SimDataFrame)
    assert out.shape[0]==2


def test_loc_set_get():
    df = SimDataFrame({'a':[1]}, units='m')
    df.loc[0,'a'] = (5,'m')
    assert df.loc[0,'a']==5
    df.loc[1,'b'] = (3,'s')
    assert df.get_units()['b']=='s'


def test_iloc_set_get():
    df = SimDataFrame({'a':[1],'b':[2]}, units={'a':'m','b':'s'})
    df.iloc[0,0] = (10,'m')
    assert df.iloc[0,0]==10


def test_series_conversion():
    df = SimDataFrame({'a':[1,2]}, units='m')
    s = df['a']
    assert isinstance(s, SimSeries)

def test_groupby_sum_with_units_no_crash():
    sdf = SimDataFrame(
        {
            'group': ['A', 'A', 'B', 'B', 'C', 'C'],
            'value': [10, 20, 30, 40, 50, 60],
            'weight': [1, 2, 3, 4, 5, 6],
        },
        units={'value': 'm', 'weight': 'kg'},
    )

    grouped = sdf.groupby('group').sum(numeric_only=True)

    assert isinstance(grouped, (SimDataFrame, pd.DataFrame))
    assert grouped.loc['A', 'value'] == 30
    assert grouped.loc['C', 'weight'] == 11

    if hasattr(grouped, 'get_units'):
        units_dict = grouped.get_units()
        assert units_dict.get('value') == 'm'
        assert units_dict.get('weight') == 'kg'


def test_set_index_inplace_units_preserves_units():
    df = SimDataFrame({'a': [1, 2, 3], 'b': [10, 20, 30]}, units={'a': 'm', 'b': 'cm'})

    df_noninplace = df.set_index('a')
    assert df_noninplace.index.units == 'm'
    assert df_noninplace.get_units()['b'] == 'cm'

    df_inplace = df.copy()
    df_inplace.set_index('a', inplace=True)
    assert df_inplace.index.units == 'm'
    assert df_inplace.get_units()['b'] == 'cm'

    assert df_noninplace.get_units() == df_inplace.get_units()


def test_lazy_unyts_convertible_warmup(monkeypatch):
    from simpandas.common import lazy_unyts

    sequence = []

    def fake_convertible(from_unit, to_unit):
        sequence.append(('convertible', from_unit, to_unit))
        # first call: False (cache warmup path), second call: True
        return len([c for c in sequence if c[0] == 'convertible']) > 1

    def fake_convert_for_SimPandas(value, from_unit, to_unit):
        sequence.append(('convert_for_SimPandas', value, from_unit, to_unit))
        return 0.158987

    # override loader to use fakes
    def fake_load_unyts():
        return {
            'convertible': fake_convertible,
            'convert_for_SimPandas': fake_convert_for_SimPandas,
            'unit_power': lambda *a, **k: None,
            'unit_addition': lambda *a, **k: None,
            'unit_product': lambda *a, **k: None,
            'unit_division': lambda *a, **k: None,
            'unit_inverse': lambda *a, **k: None,
            'unit_base': lambda *a, **k: None,
            'unit_base_power': lambda *a, **k: None,
            'unitless_names': set(),
            'number': set(),
            'units': lambda *a, **k: None,
            'Unit': object,
            'is_Unit': lambda x: False,
        }

    monkeypatch.setattr(lazy_unyts, '_load_unyts', fake_load_unyts)

    assert lazy_unyts.convertible('stb/day', 'sm3/day') is True
    assert sequence == [
        ('convertible', 'stb/day', 'sm3/day'),
        ('convert_for_SimPandas', 1, 'stb/day', 'sm3/day'),
        ('convertible', 'stb/day', 'sm3/day')
    ]

