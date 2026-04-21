# -*- coding: utf-8 -*-
"""
Tests for HDF5 reader/writer round-trip.

Requires ``h5py``.  Tests are skipped if it is not installed.
"""

import os

import pandas as pd
import pytest

h5py = pytest.importorskip("h5py")

from simpandas import SimDataFrame, SimSeries, read_hdf5
from simpandas.writers.h5 import write_hdf5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sdf(named_index=False, index_units=None):
    data = {'pressure': [100.0, 200.0, 300.0],
            'temperature': [25.0, 30.0, 35.0]}
    kwargs = {'units': {'pressure': 'psi', 'temperature': 'degF'}}
    if named_index:
        idx = pd.Index([0.0, 1.0, 2.0], name='time')
        kwargs['index'] = idx
    if index_units:
        kwargs['index_units'] = index_units
    return SimDataFrame(data=data, **kwargs)


def _make_ss():
    return SimSeries(data=[1.0, 2.0, 3.0], name='rate', units='bbl/d')


# ===========================================================================
# Writer sanity checks
# ===========================================================================

class TestWriteHDF5:

    def test_creates_file(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'out.h5')
        write_hdf5(sdf, path)
        assert os.path.exists(path)

    def test_group_contents(self, tmp_path):
        sdf = _make_sdf(named_index=True, index_units='days')
        path = str(tmp_path / 'out.h5')
        write_hdf5(sdf, path)
        with h5py.File(path, 'r') as f:
            grp = f['simpandas']
            assert 'data' in grp
            assert 'columns' in grp
            assert 'index' in grp
            assert 'units' in grp
            assert 'index_units' in grp.attrs
            assert 'index_name' in grp.attrs

    def test_write_series(self, tmp_path):
        ss = _make_ss()
        path = str(tmp_path / 'series.h5')
        write_hdf5(ss, path)
        assert os.path.exists(path)


# ===========================================================================
# Round-trip tests
# ===========================================================================

class TestHDF5RoundTrip:

    def test_basic(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'rt.h5')
        sdf.to_hdf5(path)
        result = read_hdf5(path)
        assert isinstance(result, SimDataFrame)
        assert list(result.columns) == ['pressure', 'temperature']
        assert result.units['pressure'] == 'psi'
        assert result.units['temperature'] == 'degF'
        assert len(result) == 3
        assert result['pressure'].iloc[0] == pytest.approx(100.0)

    def test_with_index(self, tmp_path):
        sdf = _make_sdf(named_index=True, index_units='days')
        path = str(tmp_path / 'rt_idx.h5')
        sdf.to_hdf5(path)
        result = read_hdf5(path)
        assert isinstance(result, SimDataFrame)
        assert result.index.name == 'time'
        assert result.index_units == 'days'
        assert result.units['pressure'] == 'psi'
        assert len(result) == 3

    def test_custom_group(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'rt_grp.h5')
        sdf.to_hdf5(path, group='mydata')
        result = read_hdf5(path, group='mydata')
        assert result.units['pressure'] == 'psi'

    def test_series_round_trip(self, tmp_path):
        ss = _make_ss()
        path = str(tmp_path / 'rt_series.h5')
        ss.to_hdf5(path)
        result = read_hdf5(path)
        assert isinstance(result, SimDataFrame)
        assert 'rate' in result.columns
        assert result.units['rate'] == 'bbl/d'
        assert len(result) == 3

    def test_data_integrity(self, tmp_path):
        sdf = _make_sdf()
        path = str(tmp_path / 'rt_data.h5')
        sdf.to_hdf5(path)
        result = read_hdf5(path)
        rdf_src = sdf.as_dataframe()
        rdf_res = result.as_dataframe()
        for col in rdf_src.columns:
            for i in range(len(rdf_src)):
                assert rdf_res[col].iloc[i] == pytest.approx(rdf_src[col].iloc[i])
