# -*- coding: utf-8 -*-
"""
Tests for unit-preservation through rolling/expanding/ewm/resample/query/eval/join/merge.
"""

import pytest
import pandas as pd
from simpandas import SimDataFrame, SimSeries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df():
    """Simple two-column SimDataFrame with different units per column."""
    idx = pd.date_range('2020-01-01', periods=6, freq='D')
    return SimDataFrame({'pressure': [100, 110, 120, 130, 140, 150],
                         'rate':     [10,  12,  11,  13,  14,  15]},
                        units={'pressure': 'bar', 'rate': 'm3/d'},
                        index=idx)


def _make_series():
    idx = pd.date_range('2020-01-01', periods=6, freq='D')
    return SimSeries([1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                     name='flow', units='m3/d', index=idx)


# ---------------------------------------------------------------------------
# Rolling
# ---------------------------------------------------------------------------

class TestRolling:
    def test_rolling_mean_returns_simdataframe(self):
        df = _make_df()
        result = df.rolling(2).mean()
        assert isinstance(result, SimDataFrame)

    def test_rolling_mean_preserves_units(self):
        df = _make_df()
        result = df.rolling(2).mean()
        units = result.get_units()
        assert units.get('pressure') == 'bar'
        assert units.get('rate') == 'm3/d'

    def test_rolling_sum_preserves_units(self):
        df = _make_df()
        result = df.rolling(2).sum()
        units = result.get_units()
        assert units.get('pressure') == 'bar'

    def test_rolling_std_returns_simdataframe(self):
        df = _make_df()
        result = df.rolling(3).std()
        assert isinstance(result, SimDataFrame)

    def test_rolling_series_returns_simseries(self):
        s = _make_series()
        result = s.rolling(2).mean()
        assert isinstance(result, SimSeries)

    def test_rolling_series_preserves_units(self):
        s = _make_series()
        result = s.rolling(2).mean()
        assert result.get_units().get('flow') == 'm3/d'


# ---------------------------------------------------------------------------
# Expanding
# ---------------------------------------------------------------------------

class TestExpanding:
    def test_expanding_mean_returns_simdataframe(self):
        df = _make_df()
        result = df.expanding().mean()
        assert isinstance(result, SimDataFrame)

    def test_expanding_mean_preserves_units(self):
        df = _make_df()
        result = df.expanding().mean()
        units = result.get_units()
        assert units.get('pressure') == 'bar'
        assert units.get('rate') == 'm3/d'

    def test_expanding_series_preserves_units(self):
        s = _make_series()
        result = s.expanding().mean()
        assert isinstance(result, SimSeries)
        assert result.get_units().get('flow') == 'm3/d'


# ---------------------------------------------------------------------------
# EWM
# ---------------------------------------------------------------------------

class TestEwm:
    def test_ewm_mean_returns_simdataframe(self):
        df = _make_df()
        result = df.ewm(span=3).mean()
        assert isinstance(result, SimDataFrame)

    def test_ewm_mean_preserves_units(self):
        df = _make_df()
        result = df.ewm(span=3).mean()
        units = result.get_units()
        assert units.get('pressure') == 'bar'
        assert units.get('rate') == 'm3/d'

    def test_ewm_series_preserves_units(self):
        s = _make_series()
        result = s.ewm(span=3).mean()
        assert isinstance(result, SimSeries)
        assert result.get_units().get('flow') == 'm3/d'


# ---------------------------------------------------------------------------
# Resample
# ---------------------------------------------------------------------------

class TestResample:
    def test_resample_mean_returns_simdataframe(self):
        df = _make_df()
        result = df.resample('2D').mean()
        assert isinstance(result, SimDataFrame)

    def test_resample_mean_preserves_units(self):
        df = _make_df()
        result = df.resample('2D').mean()
        units = result.get_units()
        assert units.get('pressure') == 'bar'
        assert units.get('rate') == 'm3/d'

    def test_resample_sum_preserves_units(self):
        df = _make_df()
        result = df.resample('3D').sum()
        units = result.get_units()
        assert units.get('pressure') == 'bar'

    def test_resample_reduces_rows(self):
        df = _make_df()
        result = df.resample('2D').mean()
        assert result.shape[0] == 3  # 6 days / 2 = 3 bins

    def test_resample_series_returns_simseries(self):
        s = _make_series()
        result = s.resample('2D').mean()
        assert isinstance(result, SimSeries)

    def test_resample_series_preserves_units(self):
        s = _make_series()
        result = s.resample('2D').mean()
        assert result.get_units().get('flow') == 'm3/d'


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class TestQuery:
    def test_query_returns_simdataframe(self):
        df = _make_df()
        result = df.query('pressure > 120')
        assert isinstance(result, SimDataFrame)

    def test_query_preserves_units(self):
        df = _make_df()
        result = df.query('pressure > 120')
        units = result.get_units()
        assert units.get('pressure') == 'bar'
        assert units.get('rate') == 'm3/d'

    def test_query_filters_correctly(self):
        df = _make_df()
        result = df.query('pressure > 120')
        assert (result['pressure'] > 120).all()

    def test_query_preserves_column_count(self):
        df = _make_df()
        result = df.query('rate >= 12')
        assert set(result.columns) == {'pressure', 'rate'}


# ---------------------------------------------------------------------------
# Eval
# ---------------------------------------------------------------------------

class TestEval:
    def test_eval_returns_simdataframe(self):
        df = _make_df()
        result = df.eval('ratio = pressure / rate')
        assert isinstance(result, SimDataFrame)

    def test_eval_adds_computed_column(self):
        df = _make_df()
        result = df.eval('ratio = pressure / rate')
        assert 'ratio' in result.columns

    def test_eval_preserves_existing_units(self):
        df = _make_df()
        result = df.eval('ratio = pressure / rate')
        units = result.get_units()
        assert units.get('pressure') == 'bar'
        assert units.get('rate') == 'm3/d'


# ---------------------------------------------------------------------------
# Join
# ---------------------------------------------------------------------------

class TestJoin:
    def test_join_returns_simdataframe(self):
        df1 = SimDataFrame({'pressure': [100, 110, 120]}, units='bar',
                           index=pd.date_range('2020-01-01', periods=3, freq='D'))
        df2 = SimDataFrame({'rate': [10, 11, 12]}, units='m3/d',
                           index=pd.date_range('2020-01-01', periods=3, freq='D'))
        result = df1.join(df2)
        assert isinstance(result, SimDataFrame)

    def test_join_merges_columns(self):
        df1 = SimDataFrame({'pressure': [100, 110, 120]}, units='bar',
                           index=pd.date_range('2020-01-01', periods=3, freq='D'))
        df2 = SimDataFrame({'rate': [10, 11, 12]}, units='m3/d',
                           index=pd.date_range('2020-01-01', periods=3, freq='D'))
        result = df1.join(df2)
        assert 'pressure' in result.columns
        assert 'rate' in result.columns

    def test_join_preserves_left_units(self):
        df1 = SimDataFrame({'pressure': [100, 110, 120]}, units='bar',
                           index=pd.date_range('2020-01-01', periods=3, freq='D'))
        df2 = SimDataFrame({'rate': [10, 11, 12]}, units='m3/d',
                           index=pd.date_range('2020-01-01', periods=3, freq='D'))
        result = df1.join(df2)
        assert result.get_units().get('pressure') == 'bar'


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

class TestMerge:
    def test_merge_returns_simdataframe(self):
        df1 = SimDataFrame({'key': [1, 2, 3], 'pressure': [100, 110, 120]},
                           units={'key': 'unitless', 'pressure': 'bar'})
        df2 = SimDataFrame({'key': [1, 2, 3], 'rate': [10, 11, 12]},
                           units={'key': 'unitless', 'rate': 'm3/d'})
        result = df1.merge(df2, on='key')
        assert isinstance(result, SimDataFrame)

    def test_merge_combines_columns(self):
        df1 = SimDataFrame({'key': [1, 2, 3], 'pressure': [100, 110, 120]},
                           units={'key': 'unitless', 'pressure': 'bar'})
        df2 = SimDataFrame({'key': [1, 2, 3], 'rate': [10, 11, 12]},
                           units={'key': 'unitless', 'rate': 'm3/d'})
        result = df1.merge(df2, on='key')
        assert 'pressure' in result.columns
        assert 'rate' in result.columns

    def test_merge_preserves_left_units(self):
        df1 = SimDataFrame({'key': [1, 2, 3], 'pressure': [100, 110, 120]},
                           units={'key': 'unitless', 'pressure': 'bar'})
        df2 = SimDataFrame({'key': [1, 2, 3], 'rate': [10, 11, 12]},
                           units={'key': 'unitless', 'rate': 'm3/d'})
        result = df1.merge(df2, on='key')
        assert result.get_units().get('pressure') == 'bar'
