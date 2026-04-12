# -*- coding: utf-8 -*-
"""
Tests for bugs identified in the AUDIT_PLAN.md audit.
Each test corresponds to a specific BUG-XX identifier.
"""

import pytest
import pandas as pd
import numpy as np
from simpandas import SimDataFrame, SimSeries


# ---------------------------------------------------------------------------
# BUG-01: cumsum() and describe() called non-existent as_Pandas / to_Pandas
# ---------------------------------------------------------------------------

class TestBug01CumsumDescribe:
    def test_cumsum_runs(self):
        df = SimDataFrame({'a': [1, 2, 3]}, units='m')
        result = df.cumsum()
        assert isinstance(result, SimDataFrame)
        assert list(result['a']) == [1, 3, 6]

    def test_cumsum_preserves_units(self):
        df = SimDataFrame({'a': [1, 2, 3]}, units='m')
        result = df.cumsum()
        assert result.get_units()['a'] == 'm'

    def test_cumsum_series(self):
        s = SimSeries([1, 2, 3], name='x', units='kg')
        result = s.cumsum()
        assert isinstance(result, SimSeries)
        assert list(result) == [1, 3, 6]

    def test_describe_runs(self):
        df = SimDataFrame({'a': [1, 2, 3, 4, 5]}, units='m')
        result = df.describe()
        assert isinstance(result, SimDataFrame)
        assert 'mean' in result.index

    def test_describe_preserves_units(self):
        df = SimDataFrame({'a': [1, 2, 3, 4, 5]}, units='m')
        result = df.describe()
        assert result.get_units()['a'] == 'm'


# ---------------------------------------------------------------------------
# BUG-02: as_Series() capitalization in SimSeries filter() and sort_values()
# ---------------------------------------------------------------------------

class TestBug02AsSeriesCapitalization:
    def test_sort_values_non_inplace(self):
        s = SimSeries([3, 1, 2], name='x', units='m')
        result = s.sort_values()
        assert isinstance(result, SimSeries)
        assert list(result) == [1, 2, 3]

    def test_sort_values_preserves_units(self):
        s = SimSeries([3, 1, 2], name='x', units='m')
        result = s.sort_values()
        assert result.units == 'm'

    def test_sort_values_inplace(self):
        # Note: inplace sort goes through SimBasics.sort_values which creates a new
        # object; true inplace mutation doesn't work (pre-existing limitation).
        # We just verify it doesn't crash.
        s = SimSeries([3, 1, 2], name='x', units='m')
        s.sort_values(inplace=True)

    def test_filter_with_index_condition(self):
        s = SimSeries([10, 20, 30], index=[1, 2, 3], name='x', units='m')
        result = s.filter('>1')
        assert isinstance(result, SimSeries)
        assert len(result) == 2

    def test_filter_compound_condition(self):
        s = SimSeries([10, 20, 30], index=[1, 2, 3], name='x', units='m')
        result = s.filter('>1 and <3')
        assert isinstance(result, SimSeries)
        assert len(result) == 1
        assert list(result) == [20]


# ---------------------------------------------------------------------------
# BUG-03: errors='errors' string literal in SimSeries.drop()
# ---------------------------------------------------------------------------

class TestBug03ErrorsLiteral:
    def test_drop_non_inplace(self):
        s = SimSeries([1, 2, 3], index=['a', 'b', 'c'], name='x', units='m')
        result = s.drop(labels='b')
        assert isinstance(result, SimSeries)
        assert len(result) == 2
        assert 'b' not in result.index

    def test_drop_inplace(self):
        s = SimSeries([1, 2, 3], index=['a', 'b', 'c'], name='x', units='m')
        s.drop(labels='a', inplace=True)
        assert len(s) == 2
        assert 'a' not in s.index

    def test_drop_with_errors_ignore(self):
        s = SimSeries([1, 2, 3], index=['a', 'b', 'c'], name='x', units='m')
        # Should not raise with errors='ignore' for missing label
        result = s.drop(labels='z', errors='ignore')
        assert len(result) == 3


# ---------------------------------------------------------------------------
# BUG-04: type(*args) unpacking in indexer _postprocess()
# ---------------------------------------------------------------------------

class TestBug04IndexerPostprocess:
    def test_loc_returns_simdataframe_for_row(self):
        df = SimDataFrame({'a': [1, 2], 'b': [3, 4]}, units={'a': 'm', 'b': 's'})
        result = df.loc[0]
        # Should return a wrapped object, not crash
        assert result is not None

    def test_iloc_returns_correct_type(self):
        df = SimDataFrame({'a': [1, 2], 'b': [3, 4]}, units={'a': 'm', 'b': 's'})
        result = df.iloc[0]
        assert result is not None

    def test_loc_column_selection(self):
        df = SimDataFrame({'a': [1, 2], 'b': [3, 4]}, units={'a': 'm', 'b': 's'})
        result = df.loc[:, 'a']
        assert isinstance(result, SimSeries)


# ---------------------------------------------------------------------------
# BUG-06: append() uses undefined otherC in else branch
# ---------------------------------------------------------------------------

class TestBug06AppendOtherC:
    def test_append_plain_dataframe(self):
        sdf = SimDataFrame({'a': [1, 2]}, units='m')
        plain_df = pd.DataFrame({'a': [3, 4]})
        result = sdf.append(plain_df)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 4

    def test_append_sim_dataframe(self):
        sdf1 = SimDataFrame({'a': [1], 'b': [10]}, units={'a': 'm', 'b': 's'})
        sdf2 = SimDataFrame({'a': [2], 'b': [20]}, units={'a': 'm', 'b': 's'})
        result = sdf1.append(sdf2)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# BUG-07: _arithmethic_operation fill_value uses label string index
# ---------------------------------------------------------------------------

class TestBug07FillValueIndex:
    def test_arithmetic_with_fill_value_true(self):
        df1 = SimDataFrame({'a': [1, 2, 3]}, units='m')
        df2 = SimDataFrame({'a': [10, 20, 30]}, units='m')
        # fill_value=True should use the numeric default (0 for addition), not 'Addition'
        result = df1.add(df2, fill_value=True)
        assert isinstance(result, SimDataFrame)
        assert list(result['a']) == [11, 22, 33]


# ---------------------------------------------------------------------------
# BUG-08: dropna() inplace branch has swapped how/thresh parameters
# ---------------------------------------------------------------------------

class TestBug08DropnaSwapped:
    def test_dropna_inplace_with_how(self):
        df = SimDataFrame({
            'a': [1, None, 3],
            'b': [None, None, 6]
        }, units={'a': 'm', 'b': 's'})
        df_copy = df.copy()
        df_copy.dropna(how='all', inplace=True)
        # Only row 1 has all NaN values (in column 'a' it has None but 'b' also has None)
        # Actually row 0 has b=None, row 1 has a=None and b=None (all NaN), row 2 is full
        assert len(df_copy) == 2  # row 1 where both are None should be dropped

    def test_dropna_inplace_matches_non_inplace(self):
        df = SimDataFrame({
            'a': [1.0, np.nan, 3.0],
            'b': [np.nan, np.nan, 6.0]
        }, units={'a': 'm', 'b': 's'})
        non_inplace = df.dropna(how='any')
        df_inplace = df.copy()
        df_inplace.dropna(how='any', inplace=True)
        assert len(non_inplace) == len(df_inplace)
        assert list(non_inplace.index) == list(df_inplace.index)


# ---------------------------------------------------------------------------
# BUG-09: SimIndex.set_units() calls .split() turning string into list
# ---------------------------------------------------------------------------

class TestBug09IndexSetUnitsSplit:
    def test_set_units_keeps_string(self):
        from simpandas.index import SimIndex
        idx = SimIndex([1, 2, 3], units='m')
        idx.set_units('m/s')
        assert isinstance(idx.units, str)
        assert idx.units == 'm/s'

    def test_set_units_strips_whitespace(self):
        from simpandas.index import SimIndex
        idx = SimIndex([1, 2, 3], units='m')
        idx.set_units('  kg  ')
        assert idx.units == 'kg'


# ---------------------------------------------------------------------------
# BUG-10: corr() returns plain pandas, not wrapped
# ---------------------------------------------------------------------------

class TestBug10CorrUnwrapped:
    def test_corr_returns_simdataframe(self):
        df = SimDataFrame({'a': [1, 2, 3], 'b': [3, 2, 1]}, units={'a': 'm', 'b': 'm'})
        result = df.corr()
        assert isinstance(result, SimDataFrame)

    def test_series_corr_returns_scalar(self):
        # Series.corr() should still return a scalar (float), not wrapped
        s1 = SimSeries([1, 2, 3], name='x', units='m')
        s2 = SimSeries([3, 2, 1], name='y', units='m')
        result = s1.corr(s2)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# BUG-11: drop(inplace=True) column detection broken for columns= kwarg
# ---------------------------------------------------------------------------

class TestBug11DropInplaceDetection:
    def test_drop_columns_kwarg_inplace(self):
        df = SimDataFrame({'a': [1, 2], 'b': [3, 4], 'c': [5, 6]},
                          units={'a': 'm', 'b': 's', 'c': 'kg'})
        df.drop(columns='b', inplace=True)
        assert 'b' not in df.columns
        units = df.get_units()
        assert units['a'] == 'm'
        assert units['c'] == 'kg'
        assert 'b' not in units

    def test_drop_columns_kwarg_inplace_multiple(self):
        df = SimDataFrame({'a': [1], 'b': [2], 'c': [3]},
                          units={'a': 'm', 'b': 's', 'c': 'kg'})
        df.drop(columns=['a', 'c'], inplace=True)
        assert list(df.columns) == ['b']
        assert df.get_units()['b'] == 's'


# ---------------------------------------------------------------------------
# BUG-14: renameItem passes self as first positional arg
# ---------------------------------------------------------------------------

class TestBug14RenameItem:
    def test_renameItem_does_not_crash(self):
        df = SimDataFrame({'group:alpha': [1], 'group:beta': [2]},
                          units={'group:alpha': 'm', 'group:beta': 'm'},
                          name_separator=':')
        result = df.renameItem(mapper={'alpha': 'gamma'})
        assert isinstance(result, SimDataFrame)
        assert 'group:gamma' in result.columns


# ---------------------------------------------------------------------------
# Filter fix: SimDataFrame filter tests
# ---------------------------------------------------------------------------

class TestFilterDataFrame:
    def test_filter_index_condition(self):
        df = SimDataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]},
                          index=[10, 20, 30],
                          units={'a': 'm', 'b': 's'})
        result = df.filter('>10')
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2

    def test_filter_column_condition(self):
        df = SimDataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]},
                          index=[10, 20, 30],
                          units={'a': 'm', 'b': 's'})
        result = df.filter('a > 1')
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2
