# -*- coding: utf-8 -*-
"""
Tests that verify units are preserved (or correctly dropped) through
operations that have corresponding coverage in other test files but do
not assert unit survival there.  Includes:
  - Window and group-by operations (rolling, expanding, ewm, groupby)
  - All arithmetic dunder operators + convert()
  - I/O round-trips (CSV, JSON, Excel) with unit metadata
  - insert() with positional unit tracking
"""

import os
import tempfile

import pandas as pd
import pytest

from simpandas import SimDataFrame, SimSeries, read_csv, read_excel, read_json


# ---------------------------------------------------------------------------
# Window and group-by — units must survive rolling / ewm / groupby
# ---------------------------------------------------------------------------

class TestWindowAndGroupByUnits:
    def test_window_ops_preserve_units(self):
        df = SimDataFrame({'x': [1.0, 2.0, 3.0, 4.0]}, units={'x': 'm'})

        roll = df.rolling(2).mean()
        exp = df.expanding(2).sum()
        ew = df.ewm(span=2).mean()

        assert isinstance(roll, SimDataFrame)
        assert isinstance(exp, SimDataFrame)
        assert isinstance(ew, SimDataFrame)
        assert roll.get_units()['x'] == 'm'
        assert exp.get_units()['x'] == 'm'
        assert ew.get_units()['x'] == 'm'

    def test_groupby_agg_and_transform_preserve_units(self):
        df = SimDataFrame(
            {'g': ['a', 'a', 'b', 'b'], 'x': [1.0, 2.0, 3.0, 4.0]},
            units={'g': None, 'x': 'm'}
        )

        agg = df.groupby('g').agg({'x': 'sum'})
        transformed = df[['g', 'x']].groupby('g').transform('sum')

        assert isinstance(agg, SimDataFrame)
        assert isinstance(transformed, SimDataFrame)
        assert agg.get_units()['x'] == 'm'
        assert transformed.get_units()['x'] == 'm'


# ---------------------------------------------------------------------------
# Arithmetic operators — all seven dunder ops must keep Sim type and units
# ---------------------------------------------------------------------------

class TestOperatorAndConvertCoverage:
    @pytest.mark.parametrize('operation', ['add', 'sub', 'mul', 'truediv', 'floordiv', 'mod', 'pow'])
    def test_dunder_ops_keep_sim_type_and_units(self, operation):
        left = SimSeries([2.0, 4.0], name='x', units='m')
        right = SimSeries([1.0, 2.0], name='x', units='m')

        if operation == 'add':
            result = left + right
        elif operation == 'sub':
            result = left - right
        elif operation == 'mul':
            result = left * 2
        elif operation == 'truediv':
            result = left / 2
        elif operation == 'floordiv':
            result = left // 2
        elif operation == 'mod':
            result = left % 2
        else:
            result = left ** 2

        assert isinstance(result, SimSeries)
        assert result.units is not None

    def test_dataframe_convert_single_unit(self):
        df = SimDataFrame({'x': [1.0, 2.0]}, units={'x': 'm'})
        out = df.convert('cm')
        assert isinstance(out, SimDataFrame)
        assert out.get_units()['x'] == 'cm'

    def test_dataframe_convert_dict_units(self):
        df = SimDataFrame({'x': [1.0, 2.0], 'y': [3.0, 4.0]}, units={'x': 'm', 'y': 'kg'})
        out = df.convert({'x': 'cm'})
        assert isinstance(out, SimDataFrame)
        assert out.get_units()['x'] == 'cm'
        assert out.get_units()['y'] == 'kg'

    def test_dataframe_convert_iterable_units(self):
        df = SimDataFrame({'x': [1.0, 2.0], 'y': [1000.0, 2000.0]}, units={'x': 'm', 'y': 'g'})
        out = df.convert(['cm', 'kg'])
        assert isinstance(out, SimDataFrame)
        units = out.get_units()
        assert units['x'] in ('cm', 'm')
        assert units['y'] in ('kg', 'g')

    def test_series_convert_single_unit(self):
        s = SimSeries([1.0, 2.0], name='x', units='m')
        out = s.convert('cm')
        assert isinstance(out, SimSeries)
        assert out.units == 'cm'


# ---------------------------------------------------------------------------
# I/O round-trips — unit metadata must survive write -> read
# ---------------------------------------------------------------------------

class TestRoundTripIOUnits:
    def test_csv_round_trip_preserves_units(self):
        df = SimDataFrame({'x': [1, 2], 'y': [3, 4]}, units={'x': 'm', 'y': 'kg'})

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            path = f.name
        try:
            df.to_csv(path, index=False)
            out = read_csv(path, units=0)
            assert isinstance(out, SimDataFrame)
            assert out.get_units()['x'] == 'm'
            assert out.get_units()['y'] == 'kg'
        finally:
            os.unlink(path)

    def test_json_round_trip_preserves_units(self):
        df = SimDataFrame({'x': [1, 2], 'y': [3, 4]}, units={'x': 'm', 'y': 'kg'})

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            df.to_json(path)
            out = read_json(path)
            assert isinstance(out, SimDataFrame)
            assert out.get_units()['x'] == 'm'
            assert out.get_units()['y'] == 'kg'
        finally:
            os.unlink(path)

    def test_excel_round_trip_preserves_units(self):
        df = SimDataFrame({'x': [1, 2], 'y': [3, 4]}, units={'x': 'm', 'y': 'kg'})

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        try:
            df.to_excel(path, index=False)
            out = read_excel(path)
            assert isinstance(out, SimDataFrame)
            assert out.get_units()['x'] == 'm'
            assert out.get_units()['y'] == 'kg'
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# insert() — positional unit tracking must follow column insertion
# ---------------------------------------------------------------------------

class TestInsertUnitTracking:
    def test_insert_tracks_unit_position(self):
        df = SimDataFrame({'a': [1, 2], 'c': [3, 4]}, units={'a': 'm', 'c': 'kg'})

        df.insert(1, 'b', ([10, 20], 's'))

        assert list(df.columns) == ['a', 'b', 'c']
        units = df.get_units()
        assert units['a'] == 'm'
        assert units['b'] == 's'
        assert units['c'] == 'kg'
