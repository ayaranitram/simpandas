# -*- coding: utf-8 -*-
"""Tests for simpandas.common.units.ColumnUnits."""

import pytest
from simpandas.common.units import ColumnUnits
from simpandas import ColumnUnits as ColumnUnits_top  # also importable from top level


# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------

def test_empty():
    cu = ColumnUnits()
    assert len(cu) == 0
    assert list(cu) == []
    assert cu.to_list() == []
    assert cu.to_dict() == {}


def test_basic_unique_keys():
    cu = ColumnUnits(['A', 'B', 'C'], ['m', 's', 'kg'])
    assert len(cu) == 3
    assert cu['A'] == 'm'
    assert cu['B'] == 's'
    assert cu['C'] == 'kg'


def test_default_none_values():
    cu = ColumnUnits(['X', 'Y'])
    assert cu['X'] is None
    assert cu['Y'] is None


def test_mismatched_lengths_raises():
    with pytest.raises(ValueError):
        ColumnUnits(['A', 'B'], ['m'])


# ---------------------------------------------------------------------------
# Duplicate-key behaviour
# ---------------------------------------------------------------------------

def test_duplicate_keys_getitem_returns_first():
    cu = ColumnUnits(['PRES', 'TEMP', 'PRES'], ['MPa', 'degC', 'psia'])
    assert cu['PRES'] == 'MPa'


def test_duplicate_keys_get_all():
    cu = ColumnUnits(['PRES', 'TEMP', 'PRES'], ['MPa', 'degC', 'psia'])
    assert cu.get_all('PRES') == ['MPa', 'psia']
    assert cu.get_all('TEMP') == ['degC']


def test_get_all_missing_key():
    cu = ColumnUnits(['A'], ['m'])
    assert cu.get_all('Z') == []


# ---------------------------------------------------------------------------
# Iteration
# ---------------------------------------------------------------------------

def test_iter_yields_all_names_including_duplicates():
    names = ['A', 'B', 'A']
    cu = ColumnUnits(names, ['m', 's', 'ft'])
    assert list(cu) == names


def test_contains():
    cu = ColumnUnits(['A', 'B'], ['m', 's'])
    assert 'A' in cu
    assert 'Z' not in cu


# ---------------------------------------------------------------------------
# iloc accessor
# ---------------------------------------------------------------------------

def test_iloc_read():
    cu = ColumnUnits(['A', 'B', 'A'], ['m', 's', 'ft'])
    assert cu.iloc[0] == 'm'
    assert cu.iloc[1] == 's'
    assert cu.iloc[2] == 'ft'


def test_iloc_write():
    cu = ColumnUnits(['A', 'B'], ['m', 's'])
    cu.iloc[0] = 'km'
    assert cu.iloc[0] == 'km'
    assert cu['A'] == 'km'


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def test_to_list():
    cu = ColumnUnits(['A', 'B', 'A'], ['m', 's', 'ft'])
    assert cu.to_list() == ['m', 's', 'ft']


def test_to_dict_unique():
    cu = ColumnUnits(['A', 'B'], ['m', 's'])
    assert cu.to_dict() == {'A': 'm', 'B': 's'}


def test_to_dict_duplicate_last_wins():
    cu = ColumnUnits(['A', 'B', 'A'], ['m', 's', 'ft'])
    d = cu.to_dict()
    assert d['A'] == 'ft'   # last value wins
    assert d['B'] == 's'


def test_to_series():
    import pandas as pd
    cu = ColumnUnits(['A', 'B'], ['m', 's'])
    s = cu.to_series()
    assert isinstance(s, pd.Series)
    assert s.name == 'units'
    assert list(s.index) == ['A', 'B']
    assert list(s.values) == ['m', 's']


def test_to_series_duplicate_keys():
    import pandas as pd
    cu = ColumnUnits(['A', 'A'], ['m', 'ft'])
    s = cu.to_series()
    assert len(s) == 2
    assert list(s.values) == ['m', 'ft']


# ---------------------------------------------------------------------------
# Construction class methods
# ---------------------------------------------------------------------------

def test_from_dict():
    cu = ColumnUnits.from_dict({'A': 'm', 'B': 's'})
    assert cu['A'] == 'm'
    assert cu['B'] == 's'


def test_from_lists():
    cu = ColumnUnits.from_lists(['A', 'B'], ['m', 's'])
    assert cu.to_list() == ['m', 's']


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------

def test_eq_column_units():
    cu1 = ColumnUnits(['A', 'B'], ['m', 's'])
    cu2 = ColumnUnits(['A', 'B'], ['m', 's'])
    assert cu1 == cu2


def test_eq_dict():
    cu = ColumnUnits(['A', 'B'], ['m', 's'])
    assert cu == {'A': 'm', 'B': 's'}


def test_neq_column_units():
    cu1 = ColumnUnits(['A', 'B'], ['m', 's'])
    cu2 = ColumnUnits(['A', 'B'], ['m', 'kg'])
    assert cu1 != cu2


# ---------------------------------------------------------------------------
# names / values_list properties
# ---------------------------------------------------------------------------

def test_names_property():
    cu = ColumnUnits(['A', 'B', 'A'], ['m', 's', 'ft'])
    assert cu.names == ['A', 'B', 'A']


def test_values_list_property():
    cu = ColumnUnits(['A', 'B'], ['m', 's'])
    assert cu.values_list == ['m', 's']


# ---------------------------------------------------------------------------
# _sync internal helper
# ---------------------------------------------------------------------------

def test_sync_extend():
    cu = ColumnUnits(['A', 'B'], ['m', 's'])
    cu._sync(['A', 'B', 'C'])
    assert len(cu) == 3
    assert cu.iloc[2] is None
    assert cu._names == ['A', 'B', 'C']


def test_sync_truncate():
    cu = ColumnUnits(['A', 'B', 'C'], ['m', 's', 'kg'])
    cu._sync(['A', 'B'])
    assert len(cu) == 2
    assert cu.to_list() == ['m', 's']


def test_sync_same_length():
    cu = ColumnUnits(['A', 'B'], ['m', 's'])
    cu._sync(['X', 'Y'])
    assert cu._names == ['X', 'Y']
    assert cu.to_list() == ['m', 's']


# ---------------------------------------------------------------------------
# repr / str
# ---------------------------------------------------------------------------

def test_repr():
    cu = ColumnUnits(['A'], ['m'])
    assert repr(cu) == "ColumnUnits({'A': 'm'})"


def test_str():
    cu = ColumnUnits(['A'], ['m'])
    assert str(cu) == repr(cu)


# ---------------------------------------------------------------------------
# top-level import
# ---------------------------------------------------------------------------

def test_top_level_import():
    assert ColumnUnits_top is ColumnUnits
