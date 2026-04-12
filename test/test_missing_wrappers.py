# -*- coding: utf-8 -*-
"""Tests for newly added pandas method wrappers.

Each test verifies the method returns the correct Sim type with metadata preserved.
"""
import numpy as np
import pandas as pd
import pytest
from simpandas import SimDataFrame, SimSeries


# ---------------------------------------------------------------------------
# ffill / bfill
# ---------------------------------------------------------------------------

class TestFfillBfill:
    def test_ffill_dataframe(self):
        df = SimDataFrame({'a': [1, np.nan, 3], 'b': [np.nan, 5, 6]},
                          units={'a': 'm', 'b': 's'})
        result = df.ffill()
        assert isinstance(result, SimDataFrame)
        assert result.units == {'a': 'm', 'b': 's'}
        assert result['a'].iloc[1] == 1  # forward filled

    def test_bfill_dataframe(self):
        df = SimDataFrame({'a': [1, np.nan, 3], 'b': [np.nan, 5, 6]},
                          units={'a': 'm', 'b': 's'})
        result = df.bfill()
        assert isinstance(result, SimDataFrame)
        assert result.units == {'a': 'm', 'b': 's'}
        assert result['b'].iloc[0] == 5  # backward filled

    def test_ffill_series(self):
        s = SimSeries([1, np.nan, 3], name='x', units='m')
        result = s.ffill()
        assert isinstance(result, SimSeries)
        assert result.units == 'm'
        assert result.iloc[1] == 1

    def test_bfill_series(self):
        s = SimSeries([np.nan, 2, 3], name='x', units='m')
        result = s.bfill()
        assert isinstance(result, SimSeries)
        assert result.units == 'm'
        assert result.iloc[0] == 2

    def test_ffill_inplace(self):
        df = SimDataFrame({'a': [1, np.nan, 3]}, units={'a': 'm'})
        df.ffill(inplace=True)
        assert df['a'].iloc[1] == 1


# ---------------------------------------------------------------------------
# pct_change
# ---------------------------------------------------------------------------

class TestPctChange:
    def test_pct_change_dataframe(self):
        df = SimDataFrame({'a': [10, 20, 40]}, units={'a': 'm'})
        result = df.pct_change()
        assert isinstance(result, SimDataFrame)
        assert result.units == {'a': 'dimensionless'}

    def test_pct_change_series(self):
        s = SimSeries([10, 20, 40], name='x', units='m')
        result = s.pct_change()
        assert isinstance(result, SimSeries)
        assert result.units == 'dimensionless'
        assert result.iloc[1] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# combine_first
# ---------------------------------------------------------------------------

class TestCombineFirst:
    def test_combine_first_dataframe(self):
        df1 = SimDataFrame({'a': [1, np.nan, 3]}, units={'a': 'm'})
        df2 = SimDataFrame({'a': [10, 20, 30]}, units={'a': 'km'})
        result = df1.combine_first(df2)
        assert isinstance(result, SimDataFrame)
        assert result['a'].iloc[1] == 20  # filled from df2

    def test_combine_first_with_pandas(self):
        df1 = SimDataFrame({'a': [1, np.nan]}, units={'a': 'm'})
        df2 = pd.DataFrame({'a': [10, 20]})
        result = df1.combine_first(df2)
        assert isinstance(result, SimDataFrame)


# ---------------------------------------------------------------------------
# isin
# ---------------------------------------------------------------------------

class TestIsin:
    def test_isin_dataframe(self):
        df = SimDataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]},
                          units={'a': 'm', 'b': 's'})
        result = df.isin([1, 5])
        assert isinstance(result, SimDataFrame)
        assert result['a'].iloc[0] == True
        assert result['a'].iloc[1] == False

    def test_isin_series(self):
        s = SimSeries([1, 2, 3], name='x', units='m')
        result = s.isin([1, 3])
        assert isinstance(result, SimSeries)
        assert result.iloc[0] == True
        assert result.iloc[1] == False


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------

class TestCompare:
    def test_compare_dataframe(self):
        df1 = SimDataFrame({'a': [1, 2, 3]}, units={'a': 'm'})
        df2 = SimDataFrame({'a': [1, 5, 3]}, units={'a': 'm'})
        result = df1.compare(df2)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 1  # only row 1 differs

    def test_compare_series(self):
        s1 = SimSeries([1, 2, 3], name='x', units='m')
        s2 = SimSeries([1, 5, 3], name='x', units='m')
        result = s1.compare(s2)
        # Series.compare returns a DataFrame with columns ('self', 'other')
        assert isinstance(result, (SimSeries, SimDataFrame, pd.DataFrame))


# ---------------------------------------------------------------------------
# swaplevel
# ---------------------------------------------------------------------------

class TestSwaplevel:
    def test_swaplevel_dataframe(self):
        idx = pd.MultiIndex.from_tuples([('a', 1), ('a', 2), ('b', 1)], names=['x', 'y'])
        df = SimDataFrame({'val': [10, 20, 30]}, index=idx, units={'val': 'm'})
        result = df.swaplevel(0, 1)
        assert isinstance(result, SimDataFrame)
        assert result.index.names == ['y', 'x']


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_update_inplace(self):
        df = SimDataFrame({'a': [1, 2, 3]}, units={'a': 'm'})
        df2 = pd.DataFrame({'a': [10, np.nan, 30]})
        df.update(df2)
        assert isinstance(df, SimDataFrame)
        assert df['a'].iloc[0] == 10
        assert df['a'].iloc[1] == 2  # NaN in other → not updated
        assert df.units == {'a': 'm'}


# ---------------------------------------------------------------------------
# align
# ---------------------------------------------------------------------------

class TestAlign:
    def test_align_dataframe(self):
        df1 = SimDataFrame({'a': [1, 2]}, index=[0, 1], units={'a': 'm'})
        df2 = SimDataFrame({'a': [3, 4]}, index=[1, 2], units={'a': 'm'})
        left, right = df1.align(df2, join='outer')
        assert isinstance(left, SimDataFrame)
        assert isinstance(right, SimDataFrame)
        assert len(left) == 3
        assert len(right) == 3

    def test_align_with_pandas(self):
        df1 = SimDataFrame({'a': [1, 2]}, index=[0, 1], units={'a': 'm'})
        df2 = pd.DataFrame({'a': [3, 4]}, index=[1, 2])
        left, right = df1.align(df2, join='outer')
        assert isinstance(left, SimDataFrame)


# ---------------------------------------------------------------------------
# resample
# ---------------------------------------------------------------------------

class TestResample:
    def test_resample_dataframe(self):
        idx = pd.date_range('2020-01-01', periods=6, freq='h')
        df = SimDataFrame({'val': [1, 2, 3, 4, 5, 6]}, index=idx,
                          units={'val': 'm'})
        result = df.resample('2h').mean()
        assert isinstance(result, SimDataFrame)
        assert len(result) == 3

    def test_resample_series(self):
        idx = pd.date_range('2020-01-01', periods=6, freq='h')
        s = SimSeries([1, 2, 3, 4, 5, 6], index=idx, name='val', units='m')
        result = s.resample('2h').sum()
        assert isinstance(result, SimSeries)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# between (Series-only)
# ---------------------------------------------------------------------------

class TestBetween:
    def test_between_series(self):
        s = SimSeries([1, 5, 10, 15], name='x', units='m')
        result = s.between(5, 10)
        assert isinstance(result, SimSeries)
        assert list(result) == [False, True, True, False]

    def test_between_inclusive(self):
        s = SimSeries([1, 5, 10, 15], name='x', units='m')
        result = s.between(5, 10, inclusive='neither')
        assert isinstance(result, SimSeries)
        assert list(result) == [False, False, False, False]


# ---------------------------------------------------------------------------
# asfreq
# ---------------------------------------------------------------------------

class TestAsfreq:
    def test_asfreq_dataframe(self):
        idx = pd.date_range('2020-01-01', periods=3, freq='D')
        df = SimDataFrame({'val': [1, 2, 3]}, index=idx, units={'val': 'm'})
        result = df.asfreq('12h')
        assert isinstance(result, SimDataFrame)
        assert len(result) == 5  # 3 days at 12h freq = 5 entries
