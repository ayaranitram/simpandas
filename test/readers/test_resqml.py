# -*- coding: utf-8 -*-
"""
Tests for RESQML reader/writer.

Requires ``h5py`` (skipped if not available).
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from simpandas import SimDataFrame

h5py = pytest.importorskip('h5py')


@pytest.fixture
def resqml_dir():
    """Return a temp directory for RESQML output files."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    # cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_sdf():
    df = pd.DataFrame({
        'pressure': [100.0, 200.0, 300.0],
        'temperature': [25.0, 30.0, 35.0],
    }, index=pd.date_range('2024-01-01', periods=3))
    return SimDataFrame(data=df, units={'pressure': 'psi', 'temperature': 'degF'})


class TestResqmlWriter:

    def test_write_epc(self, sample_sdf, resqml_dir):
        from simpandas.writers.resqml import write_resqml

        epc_path = os.path.join(resqml_dir, 'test.epc')
        write_resqml(sample_sdf, epc_path)

        assert os.path.isfile(epc_path)
        h5_path = os.path.join(resqml_dir, 'test.h5')
        assert os.path.isfile(h5_path)

    def test_epc_is_valid_zip(self, sample_sdf, resqml_dir):
        from simpandas.writers.resqml import write_resqml
        import zipfile

        epc_path = os.path.join(resqml_dir, 'test.epc')
        write_resqml(sample_sdf, epc_path)

        assert zipfile.is_zipfile(epc_path)
        with zipfile.ZipFile(epc_path, 'r') as zf:
            names = zf.namelist()
            assert '[Content_Types].xml' in names
            assert '_rels/.rels' in names

    def test_to_resqml_method(self, sample_sdf, resqml_dir):
        epc_path = os.path.join(resqml_dir, 'test.epc')
        sample_sdf.to_resqml(epc_path)
        assert os.path.isfile(epc_path)


class TestResqmlReader:

    def test_read_written_epc(self, sample_sdf, resqml_dir):
        from simpandas.writers.resqml import write_resqml
        from simpandas.readers.resqml import read_resqml

        epc_path = os.path.join(resqml_dir, 'test.epc')
        write_resqml(sample_sdf, epc_path)

        result = read_resqml(epc_path)
        assert isinstance(result, SimDataFrame)
        # should have the same columns
        assert 'pressure' in result.columns
        assert 'temperature' in result.columns

    def test_file_not_found(self):
        from simpandas.readers.resqml import read_resqml
        with pytest.raises(FileNotFoundError):
            read_resqml('/nonexistent/file.epc')


class TestResqmlRoundTrip:

    def test_values_preserved(self, sample_sdf, resqml_dir):
        from simpandas.writers.resqml import write_resqml
        from simpandas.readers.resqml import read_resqml

        epc_path = os.path.join(resqml_dir, 'test.epc')
        write_resqml(sample_sdf, epc_path)
        result = read_resqml(epc_path)

        np.testing.assert_array_almost_equal(
            result['pressure'].values.astype(float), [100, 200, 300]
        )
        np.testing.assert_array_almost_equal(
            result['temperature'].values.astype(float), [25, 30, 35]
        )

    def test_numeric_index_sdf(self, resqml_dir):
        """RESQML round-trip with a numeric (non-datetime) index."""
        from simpandas.writers.resqml import write_resqml
        from simpandas.readers.resqml import read_resqml

        df = pd.DataFrame({'depth': [100.0, 200.0]})
        sdf = SimDataFrame(data=df, units={'depth': 'm'})

        epc_path = os.path.join(resqml_dir, 'numeric.epc')
        write_resqml(sdf, epc_path)
        result = read_resqml(epc_path)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2
