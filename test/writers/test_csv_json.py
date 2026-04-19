# -*- coding: utf-8 -*-
"""
Tests for CSV and JSON writers and round-trip compatibility with readers.
"""

import json
import os
import tempfile

import pandas as pd
import pytest

from simpandas import SimDataFrame, SimSeries, read_csv, read_json
from simpandas.writers.csv import write_csv
from simpandas.writers.json import write_json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sdf(named_index=False, index_units=None):
    """Return a small SimDataFrame for testing."""
    data = {'pressure': [100.0, 200.0, 300.0],
            'temperature': [25.0, 30.0, 35.0]}
    kwargs = {'units': {'pressure': 'psi', 'temperature': 'degF'}}
    if named_index:
        idx = pd.Index([0, 1, 2], name='time')
        kwargs['index'] = idx
    if index_units:
        kwargs['index_units'] = index_units
    return SimDataFrame(data=data, **kwargs)


def _make_ss():
    """Return a small SimSeries for testing."""
    return SimSeries(data=[1.0, 2.0, 3.0], name='rate', units='bbl/d')


# ===========================================================================
# CSV writer tests
# ===========================================================================

class TestWriteCSV:

    def test_write_csv_string(self):
        sdf = _make_sdf()
        result = write_csv(sdf, index=False)
        assert isinstance(result, str)
        lines = result.strip().splitlines()
        # header + units row + 3 data rows
        assert len(lines) == 5
        assert 'pressure' in lines[0]
        assert 'psi' in lines[1]

    def test_write_csv_file(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'out.csv')
        write_csv(sdf, path, index=False)
        assert os.path.exists(path)
        content = open(path).read()
        assert 'psi' in content
        assert 'degF' in content

    def test_write_csv_no_units(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'nounits.csv')
        write_csv(sdf, path, units=False, index=False)
        content = open(path).read()
        assert 'psi' not in content

    def test_write_csv_with_named_index(self):
        sdf = _make_sdf(named_index=True, index_units='days')
        result = write_csv(sdf, index=True)
        lines = result.strip().splitlines()
        # First column should be 'time'
        assert lines[0].startswith('time')
        # Units row should contain 'days'
        assert 'days' in lines[1]

    def test_write_csv_series(self):
        ss = _make_ss()
        result = write_csv(ss, index=False)
        lines = result.strip().splitlines()
        # header + units row + 3 data rows
        assert len(lines) == 5
        assert 'bbl/d' in result


# ===========================================================================
# CSV round-trip tests
# ===========================================================================

class TestCSVRoundTrip:

    def test_round_trip_basic(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'rt.csv')
        sdf.to_csv(path, index=False)
        result = read_csv(path, units=0)
        assert isinstance(result, SimDataFrame)
        assert list(result.columns) == ['pressure', 'temperature']
        assert result.units['pressure'] == 'psi'
        assert result.units['temperature'] == 'degF'
        assert len(result) == 3
        assert result['pressure'].iloc[0] == pytest.approx(100.0)

    def test_round_trip_with_index(self, tmp_path):
        sdf = _make_sdf(named_index=True, index_units='days')
        path = str(tmp_path / 'rt_idx.csv')
        sdf.to_csv(path, index=True)
        result = read_csv(path, units=0, index_col=0)
        assert isinstance(result, SimDataFrame)
        assert result.index.name == 'time'
        assert result.index_units == 'days'
        assert 'pressure' in result.columns
        assert result.units['pressure'] == 'psi'
        assert len(result) == 3

    def test_round_trip_no_units(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'rt_no.csv')
        sdf.to_csv(path, units=False, index=False)
        result = read_csv(path, units=None)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 3

    def test_round_trip_series(self, tmp_path):
        ss = _make_ss()
        path = str(tmp_path / 'rt_series.csv')
        ss.to_csv(path, index=False)
        result = read_csv(path, units=0)
        assert isinstance(result, SimDataFrame)
        assert 'rate' in result.columns
        assert result.units['rate'] == 'bbl/d'
        assert len(result) == 3


# ===========================================================================
# JSON writer tests
# ===========================================================================

class TestWriteJSON:

    def test_write_json_string(self):
        sdf = _make_sdf()
        result = write_json(sdf)
        payload = json.loads(result)
        assert 'data' in payload
        assert 'units' in payload
        assert payload['units']['pressure'] == 'psi'

    def test_write_json_file(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'out.json')
        write_json(sdf, path)
        assert os.path.exists(path)
        with open(path) as f:
            payload = json.load(f)
        assert payload['units']['temperature'] == 'degF'

    def test_write_json_index_units(self):
        sdf = _make_sdf(named_index=True, index_units='days')
        result = write_json(sdf)
        payload = json.loads(result)
        assert payload['index_units'] == 'days'

    def test_write_json_series(self):
        ss = _make_ss()
        result = write_json(ss)
        payload = json.loads(result)
        assert 'data' in payload
        assert payload['units']['rate'] == 'bbl/d'


# ===========================================================================
# JSON round-trip tests
# ===========================================================================

class TestJSONRoundTrip:

    def test_round_trip_basic(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'rt.json')
        sdf.to_json(path)
        result = read_json(path)
        assert isinstance(result, SimDataFrame)
        assert result.units['pressure'] == 'psi'
        assert result.units['temperature'] == 'degF'
        assert len(result) == 3
        assert result['pressure'].iloc[0] == pytest.approx(100.0)

    def test_round_trip_index_units(self, tmp_path):
        sdf = _make_sdf(named_index=True, index_units='days')
        path = str(tmp_path / 'rt_iu.json')
        sdf.to_json(path)
        result = read_json(path)
        assert isinstance(result, SimDataFrame)
        assert result.index_units == 'days'
        assert result.units['pressure'] == 'psi'

    def test_round_trip_string(self):
        sdf = _make_sdf()
        json_str = sdf.to_json()
        result = read_json(json_str)
        assert isinstance(result, SimDataFrame)
        assert result.units['pressure'] == 'psi'

    def test_round_trip_series(self, tmp_path):
        ss = _make_ss()
        path = str(tmp_path / 'rt_series.json')
        ss.to_json(path)
        result = read_json(path)
        assert isinstance(result, SimDataFrame)
        assert result.units['rate'] == 'bbl/d'
