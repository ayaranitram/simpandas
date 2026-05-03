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


# ===========================================================================
# deduplicate_columns tests
# ===========================================================================

def test_deduplicate_columns_no_duplicates_returns_self():
    df = SimDataFrame({'a': [1, 2], 'b': [3, 4]}, units={'a': 'm', 'b': 'ft'})
    result = df.deduplicate_columns()
    assert list(result.columns) == ['a', 'b']
    assert result is df  # same object: no-op path


def test_deduplicate_columns_renames_duplicates():
    df = SimDataFrame(
        {'a': [1, 2], 'b': [3, 4], 'a_dup': [5, 6]},
        units={'a': 'm', 'b': 'ft', 'a_dup': 'cm'},
    )
    # Rename column to create an actual duplicate
    df.columns = ['a', 'b', 'a']
    df._units_ = ['m', 'ft', 'cm']

    result = df.deduplicate_columns()
    assert list(result.columns) == ['a', 'b', 'a_1']


def test_deduplicate_columns_preserves_positional_units():
    df = SimDataFrame(
        {'a': [1, 2], 'b': [3, 4], 'a_dup': [5, 6]},
        units={'a': 'm', 'b': 'ft', 'a_dup': 'cm'},
    )
    df.columns = ['a', 'b', 'a']
    df._units_ = ['m', 'ft', 'cm']

    result = df.deduplicate_columns()
    units_list = list(result._units_)
    assert units_list[0] == 'm'   # original 'a'
    assert units_list[1] == 'ft'  # 'b'
    assert units_list[2] == 'cm'  # renamed 'a_1'


def test_deduplicate_columns_inplace():
    df = SimDataFrame(
        {'a': [1, 2], 'b': [3, 4], 'a_dup': [5, 6]},
        units={'a': 'm', 'b': 'ft', 'a_dup': 'cm'},
    )
    df.columns = ['a', 'b', 'a']
    df._units_ = ['m', 'ft', 'cm']

    ret = df.deduplicate_columns(inplace=True)
    assert ret is None
    assert list(df.columns) == ['a', 'b', 'a_1']


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


# ---------------------------------------------------------------------------
# SimDataFrame.reindex tests
# ---------------------------------------------------------------------------

def test_reindex_positional_different_length():
    """reindex(positional_labels) with a different-length DatetimeIndex must
    not raise TypeError — it should default to axis=0 (rows)."""
    import numpy as np
    idx1 = pd.date_range('2020-01-01', periods=5, freq='D')
    idx2 = pd.date_range('2020-01-01', periods=10, freq='D')
    sdf = SimDataFrame({'A': np.ones(5), 'B': np.zeros(5)},
                       index=idx1, units={'A': 'm', 'B': 's'})
    result = sdf.reindex(idx2)
    assert result.shape == (10, 2)
    assert isinstance(result, SimDataFrame)
    assert result.units['A'] == 'm'


def test_reindex_index_keyword():
    """reindex(index=...) should reindex rows."""
    import numpy as np
    idx1 = pd.date_range('2020-01-01', periods=5, freq='D')
    idx2 = pd.date_range('2020-01-01', periods=8, freq='D')
    sdf = SimDataFrame({'A': np.ones(5)}, index=idx1, units='m')
    result = sdf.reindex(index=idx2)
    assert result.shape == (8, 1)
    assert isinstance(result, SimDataFrame)


def test_reindex_columns_keyword():
    """reindex(columns=...) should reindex columns."""
    import numpy as np
    sdf = SimDataFrame({'A': np.ones(3), 'B': np.zeros(3)},
                       units={'A': 'm', 'B': 's'})
    result = sdf.reindex(columns=['A', 'C'])
    assert list(result.columns) == ['A', 'C']
    assert result.shape == (3, 2)
    assert isinstance(result, SimDataFrame)


def test_reindex_both_axes():
    """reindex(index=..., columns=...) should reindex both axes at once."""
    import numpy as np
    idx1 = pd.date_range('2020-01-01', periods=5, freq='D')
    idx2 = pd.date_range('2020-01-01', periods=3, freq='D')
    sdf = SimDataFrame({'A': np.ones(5), 'B': np.zeros(5)},
                       index=idx1, units={'A': 'm', 'B': 's'})
    result = sdf.reindex(index=idx2, columns=['A', 'C'])
    assert result.shape == (3, 2)
    assert list(result.columns) == ['A', 'C']
    assert isinstance(result, SimDataFrame)


# ---------------------------------------------------------------------------
# SimSeries.get_units tests
# ---------------------------------------------------------------------------

def test_get_units_no_index_leak():
    """get_units() must not include index units by default."""
    ss = SimSeries([1.0, 2.0, 3.0], name='pressure', units='bar',
                   index=pd.Index([0.0, 1.0, 2.0], name='depth'),
                   index_units='m')
    result = ss.get_units()
    assert 'depth' not in result, 'Index units must not appear in get_units() by default'
    assert result == {'pressure': 'bar'}


def test_get_units_include_index():
    """get_units(include_index=True) must include index units."""
    ss = SimSeries([1.0, 2.0, 3.0], name='pressure', units='bar',
                   index=pd.Index([0.0, 1.0, 2.0], name='depth'),
                   index_units='m')
    result = ss.get_units(include_index=True)
    assert 'depth' in result
    assert result['depth'] == 'm'
    assert result['pressure'] == 'bar'


def test_get_units_no_index_units():
    """get_units() when index_units is None must still work cleanly."""
    ss = SimSeries([1.0, 2.0], name='flow', units='m3/d')
    result = ss.get_units()
    assert result == {'flow': 'm3/d'}
