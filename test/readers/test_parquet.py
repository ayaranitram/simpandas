# -*- coding: utf-8 -*-
"""
Tests for Parquet reader/writer with units support.
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from simpandas import SimDataFrame

# skip all tests if pyarrow is not available
pyarrow = pytest.importorskip('pyarrow')


@pytest.fixture
def sample_sdf():
    df = pd.DataFrame({
        'pressure': [100.0, 200.0, 300.0],
        'temperature': [25.0, 30.0, 35.0],
        'volume': [1.0, 1.5, 2.0],
    })
    return SimDataFrame(data=df, units={'pressure': 'psi', 'temperature': 'degF', 'volume': 'bbl'})


@pytest.fixture
def parquet_path():
    fd, path = tempfile.mkstemp(suffix='.parquet')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestParquetRoundTrip:

    def test_write_read_round_trip(self, sample_sdf, parquet_path):
        from simpandas.writers.parquet import write_parquet
        from simpandas.readers.parquet import read_parquet

        write_parquet(sample_sdf, parquet_path)
        result = read_parquet(parquet_path)

        assert isinstance(result, SimDataFrame)
        assert list(result.columns) == ['pressure', 'temperature', 'volume']
        np.testing.assert_array_almost_equal(result['pressure'].values, [100, 200, 300])

    def test_units_preserved(self, sample_sdf, parquet_path):
        from simpandas.writers.parquet import write_parquet
        from simpandas.readers.parquet import read_parquet

        write_parquet(sample_sdf, parquet_path)
        result = read_parquet(parquet_path)

        assert result.units is not None
        u = result.units
        if isinstance(u, dict):
            assert u.get('pressure') == 'psi'
            assert u.get('temperature') == 'degF'
            assert u.get('volume') == 'bbl'

    def test_to_parquet_method(self, sample_sdf, parquet_path):
        sample_sdf.to_parquet(parquet_path)
        assert os.path.isfile(parquet_path)

    def test_read_plain_parquet(self, parquet_path):
        """Read a plain Parquet file with no simpandas metadata."""
        from simpandas.readers.parquet import read_parquet

        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        df.to_parquet(parquet_path)

        result = read_parquet(parquet_path)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2

    def test_units_override(self, sample_sdf, parquet_path):
        from simpandas.writers.parquet import write_parquet
        from simpandas.readers.parquet import read_parquet

        write_parquet(sample_sdf, parquet_path)
        result = read_parquet(parquet_path, units={'pressure': 'bar'})
        u = result.units if isinstance(result.units, dict) else {}
        assert u.get('pressure') == 'bar'
