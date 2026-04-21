# -*- coding: utf-8 -*-
"""
Tests for Eclipse binary summary reader/writer round-trip.

These tests do NOT require a real simulator; they exercise the binary
format produced by ``write_summary`` and consumed by ``read_summary``.
"""

import os

import numpy as np
import pandas as pd
import pytest

from simpandas import SimDataFrame, read_summary
from simpandas.writers.summary import write_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_reservoir_sdf():
    """Return a small SimDataFrame that mimics reservoir summary data."""
    idx = pd.Index([0.0, 30.0, 60.0, 90.0], name='TIME')
    data = {
        'FOPR':       [1000.0, 980.0, 960.0, 940.0],
        'FWPR':       [50.0,   55.0,  60.0,  65.0],
        'WBHP:PROD1': [3000.0, 2950.0, 2900.0, 2850.0],
        'WBHP:PROD2': [3100.0, 3050.0, 3000.0, 2950.0],
    }
    units = {
        'FOPR':       'STB/DAY',
        'FWPR':       'STB/DAY',
        'WBHP:PROD1': 'PSIA',
        'WBHP:PROD2': 'PSIA',
    }
    return SimDataFrame(data=data, index=idx,
                        units=units, index_units='DAYS',
                        name_separator=':')


def _make_region_sdf():
    """SimDataFrame with region-level vectors."""
    idx = pd.Index([0.0, 30.0], name='TIME')
    data = {
        'RPR:1': [4000.0, 3900.0],
        'RPR:2': [4100.0, 3950.0],
    }
    units = {'RPR:1': 'PSIA', 'RPR:2': 'PSIA'}
    return SimDataFrame(data=data, index=idx,
                        units=units, index_units='DAYS',
                        name_separator=':')


def _make_completion_sdf():
    """SimDataFrame with completion-level vectors (KEYWORD:WELL:NUM)."""
    idx = pd.Index([0.0, 30.0], name='TIME')
    data = {
        'COPR:PROD1:1': [500.0, 480.0],
        'COPR:PROD1:2': [300.0, 290.0],
    }
    units = {'COPR:PROD1:1': 'STB/DAY', 'COPR:PROD1:2': 'STB/DAY'}
    return SimDataFrame(data=data, index=idx,
                        units=units, index_units='DAYS',
                        name_separator=':')


# ===========================================================================
# Writer sanity checks
# ===========================================================================

class TestWriteSummary:

    def test_creates_files(self, tmp_path):
        sdf = _make_reservoir_sdf()
        smspec = str(tmp_path / 'TEST.SMSPEC')
        write_summary(sdf, smspec)
        assert os.path.exists(smspec)
        unsmry = str(tmp_path / 'TEST.UNSMRY')
        assert os.path.exists(unsmry)

    def test_explicit_unsmry_path(self, tmp_path):
        sdf = _make_reservoir_sdf()
        smspec = str(tmp_path / 'CASE.SMSPEC')
        unsmry = str(tmp_path / 'CASE.UNSMRY')
        write_summary(sdf, smspec, unsmry_path=unsmry)
        assert os.path.exists(smspec)
        assert os.path.exists(unsmry)


# ===========================================================================
# Round-trip tests
# ===========================================================================

class TestSummaryRoundTrip:

    def test_basic_field_and_well(self, tmp_path):
        sdf = _make_reservoir_sdf()
        smspec = str(tmp_path / 'TEST.SMSPEC')
        sdf.to_summary(smspec)

        result = read_summary(smspec)
        assert isinstance(result, SimDataFrame)
        # Reader computes DATE from STARTDAT + TIME → DATE becomes the index
        assert result.index.name == 'DATE'
        # All data columns present (TIME is also kept as a column)
        rdf = result.as_dataframe()
        for col in ('FOPR', 'FWPR', 'WBHP:PROD1', 'WBHP:PROD2'):
            assert col in rdf.columns, f'{col} missing'
        # Units preserved
        assert result.units['FOPR'] == 'STB/DAY'
        assert result.units['WBHP:PROD1'] == 'PSIA'
        # Row count
        assert len(result) == 4
        # Data values (float32 round-trip loses some precision)
        assert rdf['FOPR'].iloc[0] == pytest.approx(1000.0, rel=1e-5)
        assert rdf['WBHP:PROD2'].iloc[-1] == pytest.approx(2950.0, rel=1e-5)

    def test_index_values(self, tmp_path):
        sdf = _make_reservoir_sdf()
        smspec = str(tmp_path / 'IDX.SMSPEC')
        sdf.to_summary(smspec)
        result = read_summary(smspec)
        # Reader computes DATE from default STARTDAT [1,1,1900] + TIME (Eclipse default)
        # 1900 is not a leap year: Jan=31d, Feb=28d, so +60d lands on Mar 2
        expected_dates = pd.to_datetime(['1900-01-01', '1900-01-31',
                                         '1900-03-02', '1900-04-01'])
        for i, d in enumerate(expected_dates):
            assert result.index[i] == d

    def test_region_vectors(self, tmp_path):
        sdf = _make_region_sdf()
        smspec = str(tmp_path / 'REG.SMSPEC')
        sdf.to_summary(smspec)
        result = read_summary(smspec)
        rdf = result.as_dataframe()
        # Region vectors: RPR:1, RPR:2
        assert 'RPR:1' in rdf.columns
        assert 'RPR:2' in rdf.columns
        assert result.units['RPR:1'] == 'PSIA'
        assert rdf['RPR:1'].iloc[0] == pytest.approx(4000.0, rel=1e-5)

    def test_completion_vectors(self, tmp_path):
        sdf = _make_completion_sdf()
        smspec = str(tmp_path / 'COMP.SMSPEC')
        sdf.to_summary(smspec)
        result = read_summary(smspec)
        rdf = result.as_dataframe()
        assert 'COPR:PROD1:1' in rdf.columns
        assert 'COPR:PROD1:2' in rdf.columns
        assert result.units['COPR:PROD1:1'] == 'STB/DAY'
        assert rdf['COPR:PROD1:1'].iloc[0] == pytest.approx(500.0, rel=1e-5)

    def test_name_separator(self, tmp_path):
        sdf = _make_reservoir_sdf()
        smspec = str(tmp_path / 'SEP.SMSPEC')
        sdf.to_summary(smspec)
        result = read_summary(smspec, nameSeparator=':')
        assert result.name_separator == ':'

    def test_startdat(self, tmp_path):
        sdf = _make_reservoir_sdf()
        smspec = str(tmp_path / 'START.SMSPEC')
        sdf.to_summary(smspec, startdat=[15, 6, 2020])
        # Should still read correctly
        result = read_summary(smspec)
        assert len(result) == 4

    def test_data_integrity_all_columns(self, tmp_path):
        """Verify all values survive the round-trip within float32 tolerance."""
        sdf = _make_reservoir_sdf()
        smspec = str(tmp_path / 'INTEG.SMSPEC')
        sdf.to_summary(smspec)
        result = read_summary(smspec)
        rdf_src = sdf.as_dataframe()
        rdf_res = result.as_dataframe()
        for col in rdf_src.columns:
            for i in range(len(rdf_src)):
                assert rdf_res[col].iloc[i] == pytest.approx(
                    rdf_src[col].iloc[i], rel=1e-5
                ), f'{col}[{i}] mismatch'

    def test_block_vectors(self, tmp_path):
        """B-prefix vectors with i,j,k survive the round-trip."""
        idx = pd.Index([0.0, 30.0], name='TIME')
        data = {
            'BPR:1,1,1': [5000.0, 4900.0],
            'BPR:2,1,1': [5100.0, 4950.0],
        }
        units = {'BPR:1,1,1': 'PSIA', 'BPR:2,1,1': 'PSIA'}
        sdf = SimDataFrame(data=data, index=idx,
                           units=units, index_units='DAYS',
                           name_separator=':')
        smspec = str(tmp_path / 'BLK.SMSPEC')
        sdf.to_summary(smspec, dimens=[2, 1, 1])
        result = read_summary(smspec)
        rdf = result.as_dataframe()
        assert 'BPR:1,1,1' in rdf.columns
        assert 'BPR:2,1,1' in rdf.columns
        assert rdf['BPR:1,1,1'].iloc[0] == pytest.approx(5000.0, rel=1e-5)

    def test_date_index_roundtrip(self, tmp_path):
        """A SimDataFrame with DATE index survives read→write→read."""
        dates = pd.to_datetime(['2020-06-01', '2020-07-01',
                                '2020-08-01', '2020-09-01'])
        idx = pd.DatetimeIndex(dates, name='DATE')
        data = {'FOPR': [1000.0, 980.0, 960.0, 940.0]}
        units = {'FOPR': 'STB/DAY'}
        sdf = SimDataFrame(data=data, index=idx,
                           units=units, index_units='datetime',
                           name_separator=':')
        smspec = str(tmp_path / 'DT.SMSPEC')
        sdf.to_summary(smspec)
        result = read_summary(smspec)
        assert result.index.name == 'DATE'
        assert len(result) == 4
        rdf = result.as_dataframe()
        assert 'FOPR' in rdf.columns
        assert rdf['FOPR'].iloc[0] == pytest.approx(1000.0, rel=1e-5)
        # Start date should match first original date
        assert result.index[0] == pd.Timestamp('2020-06-01')

    def test_meta_dimens_roundtrip(self, tmp_path):
        """dimens stored in meta by read_summary is reused by write_summary."""
        # Step 1: write with explicit dimens
        idx = pd.Index([0.0, 30.0], name='TIME')
        data = {'BPR:2,3,1': [5000.0, 4900.0]}
        units = {'BPR:2,3,1': 'PSIA'}
        sdf = SimDataFrame(data=data, index=idx,
                           units=units, index_units='DAYS',
                           name_separator=':')
        smspec1 = str(tmp_path / 'META1.SMSPEC')
        sdf.to_summary(smspec1, dimens=[3, 4, 2])

        # Step 2: read back (meta now contains dimens=[3,4,2])
        result = read_summary(smspec1)
        assert result.meta['dimens'] == [3, 4, 2]

        # Step 3: re-write WITHOUT explicit dimens; meta should carry them
        smspec2 = str(tmp_path / 'META2.SMSPEC')
        result.to_summary(smspec2)
        result2 = read_summary(smspec2)
        rdf = result2.as_dataframe()
        assert 'BPR:2,3,1' in rdf.columns
        assert rdf['BPR:2,3,1'].iloc[0] == pytest.approx(5000.0, rel=1e-5)

    def test_meta_startdat_roundtrip(self, tmp_path):
        """startdat stored in meta by read_summary is reused by write_summary."""
        sdf = _make_reservoir_sdf()
        smspec1 = str(tmp_path / 'SD1.SMSPEC')
        sdf.to_summary(smspec1, startdat=[15, 6, 2020])

        result = read_summary(smspec1)
        assert result.meta['startdat'] == [15, 6, 2020]

        # Re-write without explicit startdat
        smspec2 = str(tmp_path / 'SD2.SMSPEC')
        result.to_summary(smspec2)
        result2 = read_summary(smspec2)
        # The DATE index should start from 2020-06-15
        assert result2.index[0] == pd.Timestamp('2020-06-15')
