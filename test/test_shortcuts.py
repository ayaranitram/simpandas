# -*- coding: utf-8 -*-
"""
Tests for SimSeries / SimDataFrame shortcut methods and aliases that are
not covered elsewhere in the test suite:
  - Precision-equality shortcuts  (eq0..eq6, ge0..ge6, etc.)
  - Property shortcuts             (.s, .df, .ss, .sdf)
"""

import pytest

from simpandas import SimDataFrame, SimSeries


# ---------------------------------------------------------------------------
# Precision shortcuts — eq0/eq1/.../eq6 and ge0/ge1/.../ge6
# ---------------------------------------------------------------------------

class TestPrecisionShortcuts:
    @pytest.mark.parametrize('method_name', [
        'eq0', 'eq1', 'eq2', 'eq3', 'eq4', 'eq6',
        'ge0', 'ge1', 'ge2', 'ge3', 'ge4', 'ge6',
    ])
    def test_precision_shortcuts_return_boolean_series(self, method_name):
        s = SimSeries([1.001, 1.500], name='x', units='m')
        other = SimSeries([1.0, 1.0], name='x', units='m')
        result = getattr(s, method_name)(other)
        assert len(result) == 2
        assert result.isin([True, False]).all()


# ---------------------------------------------------------------------------
# Property shortcuts — .s, .df, .ss, .sdf
# ---------------------------------------------------------------------------

class TestPropertyShortcuts:
    def test_property_shortcuts(self):
        import pandas as pd
        df = SimDataFrame({'a': [1, 2]}, units='m')

        assert isinstance(df.s, pd.Series)
        assert isinstance(df.df, pd.DataFrame)
        assert isinstance(df.ss, pd.Series)
        assert isinstance(df.sdf, SimDataFrame)
