# -*- coding: utf-8 -*-
"""
Tests for newly added features: groupby, ewm, method overrides, I/O, etc.
"""

import pytest
import pandas as pd
import numpy as np
import os
import tempfile

from simpandas import SimDataFrame, SimSeries, read_csv, read_json


@pytest.fixture
def sample_df():
    return SimDataFrame(
        {'a': [1, 2, 3, 4, 5],
         'b': [10.0, 20.0, 30.0, 40.0, 50.0],
         'g': ['x', 'x', 'y', 'y', 'y']},
        units={'a': 'm', 'b': 'kg', 'g': None}
    )


@pytest.fixture
def sample_series():
    return SimSeries([1, 2, 3, 4, 5], units='m', name='dist')


# ─── GroupBy ────────────────────────────────────────────────────────────────

class TestGroupBy:
    def test_groupby_sum(self, sample_df):
        result = sample_df[['a', 'b', 'g']].groupby('g').sum()
        assert isinstance(result, SimDataFrame)
        assert 'a' in result.columns

    def test_groupby_mean(self, sample_df):
        result = sample_df[['a', 'b', 'g']].groupby('g').mean()
        assert isinstance(result, SimDataFrame)

    def test_groupby_std(self, sample_df):
        result = sample_df[['a', 'b', 'g']].groupby('g').std()
        assert isinstance(result, SimDataFrame)

    def test_groupby_agg(self, sample_df):
        result = sample_df[['a', 'b', 'g']].groupby('g').agg('sum')
        assert isinstance(result, SimDataFrame)

    def test_groupby_apply(self, sample_df):
        result = sample_df[['a', 'b', 'g']].groupby('g').apply(lambda x: x.as_pandas().sum())
        # apply result is wrapped
        assert result is not None

    def test_groupby_transform(self, sample_df):
        result = sample_df[['a', 'b', 'g']].groupby('g').transform('sum')
        assert isinstance(result, SimDataFrame)

    def test_groupby_filter(self, sample_df):
        result = sample_df[['a', 'b', 'g']].groupby('g').filter(lambda x: len(x) > 1)
        assert isinstance(result, SimDataFrame)

    def test_groupby_iter(self, sample_df):
        groups = list(sample_df[['a', 'b', 'g']].groupby('g'))
        assert len(groups) == 2
        for key, group in groups:
            assert isinstance(group, SimDataFrame)

    def test_groupby_len(self, sample_df):
        gb = sample_df[['a', 'b', 'g']].groupby('g')
        assert len(gb) == 2

    def test_groupby_getitem(self, sample_df):
        gb = sample_df[['a', 'b', 'g']].groupby('g')['a']
        result = gb.sum()
        assert result is not None


# ─── EWM ────────────────────────────────────────────────────────────────────

class TestEWM:
    def test_ewm_mean(self):
        df = SimDataFrame({'x': [1, 2, 3, 4, 5]}, units='m')
        result = df.ewm(span=3).mean()
        assert isinstance(result, SimDataFrame)
        assert len(result) == 5

    def test_ewm_var(self):
        df = SimDataFrame({'x': [1.0, 2.0, 3.0, 4.0, 5.0]}, units='m')
        result = df.ewm(span=3).var()
        assert isinstance(result, SimDataFrame)

    def test_series_ewm(self, sample_series):
        result = sample_series.ewm(span=3).mean()
        assert isinstance(result, SimSeries)


# ─── Rolling / Expanding on Series ──────────────────────────────────────────

class TestSeriesWindowOps:
    def test_series_rolling(self, sample_series):
        result = sample_series.rolling(2).mean()
        assert isinstance(result, SimSeries)

    def test_series_expanding(self, sample_series):
        result = sample_series.expanding(2).sum()
        assert isinstance(result, SimSeries)


# ─── Method overrides (SimBasics) ───────────────────────────────────────────

class TestMethodOverrides:
    def test_apply(self, sample_df):
        result = sample_df[['a', 'b']].apply(lambda x: x * 2)
        assert isinstance(result, SimDataFrame)

    def test_transform(self, sample_df):
        result = sample_df[['a', 'b']].transform(lambda x: x * 2)
        assert isinstance(result, SimDataFrame)

    def test_pipe(self, sample_df):
        result = sample_df[['a', 'b']].pipe(lambda df: df * 2)
        assert isinstance(result, SimDataFrame)

    def test_map(self, sample_df):
        result = sample_df[['a', 'b']].map(lambda x: x * 2)
        assert isinstance(result, SimDataFrame)

    def test_where(self):
        df = SimDataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]}, units={'a': 'm', 'b': 'kg'})
        cond = df.as_pandas() > 2
        result = df.where(cond)
        assert isinstance(result, SimDataFrame)

    def test_mask(self):
        df = SimDataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]}, units={'a': 'm', 'b': 'kg'})
        cond = df.as_pandas() > 2
        result = df.mask(cond, other=-1)
        assert isinstance(result, SimDataFrame)

    def test_sample(self, sample_df):
        result = sample_df.sample(n=2)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2

    def test_cummax(self, sample_df):
        result = sample_df[['a', 'b']].cummax()
        assert isinstance(result, SimDataFrame)

    def test_cummin(self, sample_df):
        result = sample_df[['a', 'b']].cummin()
        assert isinstance(result, SimDataFrame)

    def test_cumprod(self):
        df = SimDataFrame({'a': [1, 2, 3]}, units='m')
        result = df.cumprod()
        assert isinstance(result, SimDataFrame)

    def test_skew(self, sample_df):
        result = sample_df[['a', 'b']].skew()
        # skew returns a Series when axis=0
        assert result is not None

    def test_kurtosis(self, sample_df):
        result = sample_df[['a', 'b']].kurtosis()
        assert result is not None

    def test_kurt_alias(self, sample_df):
        result = sample_df[['a', 'b']].kurt()
        assert result is not None

    def test_sem(self, sample_df):
        result = sample_df[['a', 'b']].sem()
        assert result is not None

    def test_idxmin(self, sample_df):
        result = sample_df[['a', 'b']].idxmin()
        assert result is not None

    def test_idxmax(self, sample_df):
        result = sample_df[['a', 'b']].idxmax()
        assert result is not None

    def test_rank(self, sample_df):
        result = sample_df[['a', 'b']].rank()
        assert isinstance(result, SimDataFrame)

    def test_clip(self, sample_df):
        result = sample_df[['a', 'b']].clip(lower=2, upper=4)
        assert isinstance(result, SimDataFrame)

    def test_abs(self):
        df = SimDataFrame({'a': [-1, 2, -3]}, units='m')
        result = df.abs()
        assert isinstance(result, SimDataFrame)
        assert result['a'].iloc[0] == 1

    def test_round(self):
        df = SimDataFrame({'a': [1.123, 2.456]}, units='m')
        result = df.round(1)
        assert isinstance(result, SimDataFrame)

    def test_drop_duplicates(self):
        df = SimDataFrame({'a': [1, 1, 2]}, units='m')
        result = df.drop_duplicates()
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2

    def test_sort_values(self, sample_df):
        result = sample_df.sort_values('a', ascending=False)
        assert isinstance(result, SimDataFrame)
        assert result['a'].iloc[0] == 5

    def test_sort_index(self, sample_df):
        result = sample_df.sort_index(ascending=False)
        assert isinstance(result, SimDataFrame)

    def test_nlargest(self, sample_df):
        result = sample_df.nlargest(2, columns='a')
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2

    def test_nsmallest(self, sample_df):
        result = sample_df.nsmallest(2, columns='a')
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2

    def test_value_counts(self):
        s = SimSeries([1, 1, 2, 3, 3, 3], units='m', name='x')
        result = s.value_counts()
        assert result is not None

    def test_nunique(self, sample_df):
        result = sample_df[['a', 'b']].nunique()
        assert result is not None

    def test_astype_frame(self):
        df = SimDataFrame({'a': [1, 2, 3]}, units='m')
        result = df.astype(float)
        assert isinstance(result, SimDataFrame)

    def test_explode(self):
        df = SimDataFrame({'a': [[1, 2], [3]]})
        result = df.explode('a')
        assert isinstance(result, SimDataFrame)
        assert len(result) == 3


# ─── Series-specific ────────────────────────────────────────────────────────

class TestSeriesSpecific:
    def test_unique(self, sample_series):
        result = sample_series.unique()
        assert len(result) == 5

    def test_series_groupby(self):
        s = SimSeries([1, 2, 3, 4], units='m', name='val')
        groups = ['a', 'a', 'b', 'b']
        result = s.groupby(groups).sum()
        assert result is not None


# ─── DataFrame-specific overrides ───────────────────────────────────────────

class TestDataFrameOverrides:
    def test_join(self):
        df1 = SimDataFrame({'a': [1, 2, 3]}, units='m')
        df2 = pd.DataFrame({'b': [4, 5, 6]})
        result = df1.join(df2)
        assert isinstance(result, SimDataFrame)
        assert 'b' in result.columns

    def test_stack(self):
        df = SimDataFrame({'a': [1, 2], 'b': [3, 4]}, units={'a': 'm', 'b': 's'})
        result = df.stack()
        assert result is not None

    def test_unstack(self):
        df = SimDataFrame({'a': [1, 2], 'b': [3, 4]}, units={'a': 'm', 'b': 's'})
        stacked = df.stack()
        if hasattr(stacked, 'unstack'):
            result = stacked.unstack()
            assert result is not None

    def test_pivot_table(self):
        df = SimDataFrame({'g': ['x', 'x', 'y'], 'v': [1, 2, 3]}, units={'g': None, 'v': 'm'})
        result = df.pivot_table(values='v', index='g', aggfunc='sum')
        assert isinstance(result, SimDataFrame)

    def test_melt(self):
        df = SimDataFrame({'a': [1, 2], 'b': [3, 4]}, units={'a': 'm', 'b': 's'})
        result = df.as_dataframe().melt()
        # Verify the underlying operation works
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4

    def test_merge(self):
        df1 = SimDataFrame({'key': [1, 2], 'a': [10, 20]}, units={'key': None, 'a': 'm'})
        df2 = pd.DataFrame({'key': [1, 2], 'b': [30, 40]})
        result = df1.merge(df2, on='key')
        assert isinstance(result, SimDataFrame)
        assert 'b' in result.columns

    def test_query(self):
        df = SimDataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]}, units={'a': 'm', 'b': 'kg'})
        result = df.query('a > 1')
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2

    def test_eval(self):
        df = SimDataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]}, units={'a': 'm', 'b': 'kg'})
        result = df.eval('c = a + b')
        assert isinstance(result, SimDataFrame)
        assert 'c' in result.columns

    def test_iterrows(self):
        df = SimDataFrame({'a': [1, 2], 'b': [3, 4]}, units={'a': 'm', 'b': 's'})
        rows = list(df.iterrows())
        assert len(rows) == 2
        for idx, row in rows:
            assert isinstance(row, SimSeries)

    def test_itertuples(self):
        df = SimDataFrame({'a': [1, 2], 'b': [3, 4]})
        tuples = list(df.itertuples())
        assert len(tuples) == 2

    def test_pivot(self):
        df = SimDataFrame({'foo': ['one', 'two'], 'bar': ['A', 'B'], 'baz': [1, 2]})
        result = df.pivot(index='foo', columns='bar', values='baz')
        assert isinstance(result, SimDataFrame)


# ─── CSV I/O ────────────────────────────────────────────────────────────────

class TestCSVIO:
    def test_to_csv_and_read_csv(self, sample_df):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            path = f.name
        try:
            sample_df[['a', 'b']].to_csv(path)
            result = read_csv(path, units=0)
            assert isinstance(result, SimDataFrame)
        finally:
            os.unlink(path)

    def test_read_csv_no_units(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('x,y\n1,2\n3,4\n')
            path = f.name
        try:
            result = read_csv(path)
            assert isinstance(result, SimDataFrame)
            assert len(result) == 2
        finally:
            os.unlink(path)

    def test_read_csv_with_dict_units(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write('x,y\n1,2\n3,4\n')
            path = f.name
        try:
            result = read_csv(path, units={'x': 'm', 'y': 'kg'})
            assert isinstance(result, SimDataFrame)
            assert result.get_units()['x'] == 'm'
        finally:
            os.unlink(path)


# ─── JSON I/O ───────────────────────────────────────────────────────────────

class TestJSONIO:
    def test_to_json_and_read_json(self):
        df = SimDataFrame({'a': [1, 2, 3], 'b': [4.0, 5.0, 6.0]},
                          units={'a': 'm', 'b': 'kg'})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            df.to_json(path)
            result = read_json(path)
            assert isinstance(result, SimDataFrame)
            assert result.get_units().get('a') == 'm'
        finally:
            os.unlink(path)

    def test_to_json_string(self):
        df = SimDataFrame({'a': [1, 2]}, units='m')
        json_str = df.to_json()
        assert isinstance(json_str, str)
        import json
        payload = json.loads(json_str)
        assert 'data' in payload
        assert 'units' in payload

    def test_read_json_plain_pandas(self):
        import json
        data = {'a': {'0': 1, '1': 2}, 'b': {'0': 3, '1': 4}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            result = read_json(path, units={'a': 'm'})
            assert isinstance(result, SimDataFrame)
        finally:
            os.unlink(path)
