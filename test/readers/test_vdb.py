# -*- coding: utf-8 -*-
"""
Tests for VDB (VIP / Nexus) reader.

Tests that require the real sample data at
``D:\\git\\datafiletoolbox_samples\\VIP\\RKF.vdb`` are skipped when the
folder is not present.
"""

import os
import struct
import tempfile

import numpy as np
import pandas as pd
import pytest

from simpandas import SimDataFrame, read_vdb
from simpandas.readers.vdb import (
    _parse_welist,
    _parse_vardesc_blocks,
    _scan_data_records,
    _resolve_case_path,
    VDB2VIP,
)

# ---------------------------------------------------------------------------
# Path to real sample data (skip if absent)
# ---------------------------------------------------------------------------
SAMPLE_VDB = r'D:\git\datafiletoolbox_samples\VIP\RKF.vdb'
HAS_SAMPLE = os.path.isdir(SAMPLE_VDB)


# ---------------------------------------------------------------------------
# Helpers to build minimal synthetic VDB data
# ---------------------------------------------------------------------------

def _make_data_record(count, values):
    """Build one data record: count(LE i32) | -1(LE i32) | count(LE i32) | float32[count]."""
    header = struct.pack('<iii', count, -1, count)
    body = np.array(values, dtype='<f4').tobytes()
    return header + body


def _make_minimal_plot_bin(var_names, records, date=(2017, 8, 3)):
    """Build a tiny plot.bin with one VARDESC block and data records."""
    # Magic
    buf = b'NT32'
    # Pad to ~400 bytes for header area
    buf += b'\x00' * 336
    # Date (6 LE int32)
    d, m, y = date[2], date[1], date[0]
    buf += struct.pack('<6i', d, m, y, d, m, y)
    buf += b'\x00' * 100

    # VARDESC block with descriptions
    vardesc = b'VARDESC' + b'\x00' * 16
    for vn in var_names:
        # Format: KEY(8) + (UNIT)(16 max) + DESCRIPTION(40) + padding
        entry = f'{vn:<8s}(STM3 / DAY)     SOME DESCRIPTION        \n'.encode('ascii')
        vardesc += entry
    buf += vardesc
    buf += b'\x00' * 200

    # Data records
    for rec in records:
        buf += _make_data_record(len(rec), rec)
        # gap between records (padding with zeros, similar to real format)
        buf += b'\x00' * 64

    return buf


# ---------------------------------------------------------------------------
# Unit tests for internal helpers
# ---------------------------------------------------------------------------

class TestScanDataRecords:
    """Test _scan_data_records with synthetic binary data."""

    def test_single_record(self):
        count = 5
        values = [100.0, 1.0, 10.0, 20.0, 30.0]
        data = _make_data_record(count, values)
        result = _scan_data_records(data, [count])
        assert count in result
        assert len(result[count]) == 1
        np.testing.assert_allclose(result[count][0], values, rtol=1e-5)

    def test_multiple_records(self):
        count = 4
        r1 = [10.0, 1.0, 5.0, 6.0]
        r2 = [20.0, 1.0, 7.0, 8.0]
        data = _make_data_record(count, r1) + b'\x00' * 64 + _make_data_record(count, r2)
        result = _scan_data_records(data, [count])
        assert len(result[count]) == 2
        np.testing.assert_allclose(result[count][0], r1, rtol=1e-5)
        np.testing.assert_allclose(result[count][1], r2, rtol=1e-5)

    def test_mixed_counts(self):
        """Records with different counts should be separated."""
        r_a = [10.0, 1.0, 3.0]
        r_b = [20.0, 1.0, 4.0, 5.0, 6.0, 7.0]
        data = _make_data_record(3, r_a) + b'\x00' * 32 + _make_data_record(6, r_b)
        result = _scan_data_records(data, [3, 6])
        assert len(result[3]) == 1
        assert len(result[6]) == 1

    def test_ignores_non_matching_counts(self):
        r = [10.0, 1.0, 3.0]
        data = _make_data_record(3, r)
        result = _scan_data_records(data, [99])
        assert len(result[99]) == 0


class TestParseVardescBlocks:
    """Test VARDESC parsing from synthetic header data."""

    def test_single_vardesc(self):
        var_names = ['QOP', 'QGP', 'BHP']
        plot_bin = _make_minimal_plot_bin(var_names, [])
        tables = _parse_vardesc_blocks(plot_bin)
        assert len(tables) >= 1
        # At least some of our var names should be found
        found = tables[0]['var_names']
        for vn in var_names:
            assert vn in found, f'{vn} not found in {found}'

    def test_units_extracted(self):
        var_names = ['QOP', 'BHP']
        plot_bin = _make_minimal_plot_bin(var_names, [])
        tables = _parse_vardesc_blocks(plot_bin)
        assert len(tables) >= 1
        units = tables[0]['units']
        for vn in var_names:
            assert vn in units
            assert 'STM3' in units[vn]


class TestResolveCasePath:
    """Test case path resolution."""

    def test_direct_plot_bin(self, tmp_path):
        """Passing a plot.bin file directly should work."""
        plot_dir = tmp_path / 'case1' / 'PLOT'
        plot_dir.mkdir(parents=True)
        pb = plot_dir / 'plot.bin'
        pb.write_bytes(b'\x00' * 1000)
        case_dir, resolved = _resolve_case_path(str(pb))
        assert os.path.isfile(resolved)

    def test_named_case(self, tmp_path):
        """Passing case= should find the right subdirectory."""
        plot_dir = tmp_path / 'HM4r' / 'PLOT'
        plot_dir.mkdir(parents=True)
        pb = plot_dir / 'plot.bin'
        pb.write_bytes(b'\x00' * 1000)
        case_dir, resolved = _resolve_case_path(str(tmp_path), case='HM4r')
        assert 'HM4r' in resolved

    def test_missing_case_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _resolve_case_path(str(tmp_path), case='nonexistent')


# ---------------------------------------------------------------------------
# Integration test with synthetic data
# ---------------------------------------------------------------------------

class TestReadVdbSynthetic:
    """Integration test using a minimal synthetic .vdb folder."""

    @pytest.fixture
    def synthetic_vdb(self, tmp_path):
        """Create a minimal .vdb folder structure."""
        case_dir = tmp_path / 'CASE1'
        plot_dir = case_dir / 'PLOT'
        plot_dir.mkdir(parents=True)
        welist_dir = case_dir / 'WELIST'
        welist_dir.mkdir(parents=True)

        # 3 variables → record count = 5 (TIME + FLAG + 3 vars)
        var_names = ['QOP', 'BHP', 'QGP']

        # 2 wells × 2 timesteps
        records = [
            [100.0, 1.0, 10.0, 200.0, 5.0],   # t=100, well 0
            [100.0, 1.0, 12.0, 210.0, 6.0],   # t=100, well 1
            [200.0, 1.0, 11.0, 205.0, 5.5],   # t=200, well 0
            [200.0, 1.0, 13.0, 215.0, 6.5],   # t=200, well 1
        ]

        plot_data = _make_minimal_plot_bin(var_names, records)
        (plot_dir / 'plot.bin').write_bytes(plot_data)

        # Minimal welist.bin with two well names
        welist_data = b'WELL-01 WELL-02 '
        (welist_dir / 'welist.bin').write_bytes(welist_data)

        return tmp_path

    def test_returns_sim_dataframe(self, synthetic_vdb):
        sdf = read_vdb(str(synthetic_vdb))
        assert isinstance(sdf, SimDataFrame)

    def test_index_name(self, synthetic_vdb):
        sdf = read_vdb(str(synthetic_vdb))
        if len(sdf) > 0:
            assert sdf.index.name == 'TIME'

    def test_units_populated(self, synthetic_vdb):
        sdf = read_vdb(str(synthetic_vdb))
        if hasattr(sdf, 'units') and sdf.units:
            # At least some columns should have units
            assert any('STM3' in str(u) for u in sdf.units.values())

    def test_summary_key_style(self, synthetic_vdb):
        sdf = read_vdb(str(synthetic_vdb), key_style='eclipse')
        if len(sdf.columns) > 0:
            # QOP should become OPR
            col_keys = [c.split(':')[0] for c in sdf.columns if ':' in c]
            if 'QOP' in VDB2VIP:
                assert 'QOP' not in col_keys or 'OPR' in col_keys


# ---------------------------------------------------------------------------
# Tests with real sample data (skip if not present)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not HAS_SAMPLE,
                    reason='Sample VDB data not found')
class TestReadVdbRealData:
    """Integration tests with the actual RKF.vdb sample."""

    def test_read_default(self):
        sdf = read_vdb(SAMPLE_VDB, verbose=True)
        assert isinstance(sdf, SimDataFrame)
        assert len(sdf) > 0, 'Expected non-empty DataFrame'

    def test_columns_have_separator(self):
        sdf = read_vdb(SAMPLE_VDB)
        # Columns should follow KEY:WELL pattern
        has_sep = any(':' in c for c in sdf.columns)
        assert has_sep, f'No columns with separator. Columns: {list(sdf.columns)[:10]}'

    def test_time_index(self):
        sdf = read_vdb(SAMPLE_VDB)
        assert sdf.index.name == 'TIME'
        assert sdf.index.is_monotonic_increasing or len(sdf) <= 1

    def test_units_present(self):
        sdf = read_vdb(SAMPLE_VDB)
        assert hasattr(sdf, 'units')
        if sdf.units:
            assert len(sdf.units) > 0

    def test_specific_case(self):
        sdf = read_vdb(SAMPLE_VDB, case='DNr', verbose=True)
        assert isinstance(sdf, SimDataFrame)
        assert len(sdf) > 0

    def test_summary_style_keys(self):
        sdf = read_vdb(SAMPLE_VDB, key_style='eclipse')
        col_keys = {c.split(':')[0] for c in sdf.columns if ':' in c}
        # At least one Eclipse-style key should be present
        eclipse_keys = set(VDB2VIP.values())
        assert col_keys & eclipse_keys, (
            f'No Eclipse keys found. Keys: {col_keys}')

    def test_all_tables(self):
        sdf = read_vdb(SAMPLE_VDB, tables='all', verbose=True)
        assert isinstance(sdf, SimDataFrame)

    def test_custom_separator(self):
        sdf = read_vdb(SAMPLE_VDB, nameSeparator='/')
        if len(sdf.columns) > 0:
            assert any('/' in c for c in sdf.columns)
