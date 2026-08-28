# -*- coding: utf-8 -*-
"""
Tests for the CMG SR3 reader.

These tests do NOT rely on any real simulator output; they build a minimal
synthetic HDF5 file that mimics the relevant parts of the SR3 schema
(General/UnitsTable, General/NameRecordTable, General/MasterTimeTable and
TimeSeries/<CATEGORY>/{Origins,Variables,Data,Timesteps}) and then exercise
``read_sr3`` against it.
"""

import numpy as np
import pytest

h5py = pytest.importorskip('h5py')

from simpandas import SimDataFrame
from simpandas.readers.sr3 import read_sr3


def _make_sr3(path):
    """Write a minimal synthetic .sr3 (HDF5) file for testing."""
    with h5py.File(path, 'w') as f:
        general = f.create_group('General')

        units_dtype = np.dtype([
            ('Index', 'u1'),
            ('Dimensionality', 'S28'),
            ('Internal Unit', 'S20'),
            ('Output Unit', 'S20'),
        ])
        units_table = np.array([
            (1, b'Time', b'day', b'day'),
            (3, b'Pressure', b'psi', b'psi'),
            (11, b'Well Liquid Volume', b'ft3', b'bbl'),
            (13, b'Well Rate Time', b'day', b'day'),
        ], dtype=units_dtype)
        general.create_dataset('UnitsTable', data=units_table)

        name_dtype = np.dtype([
            ('Keyword', 'S23'),
            ('Dimensionality', 'S18'),
        ])
        name_records = np.array([
            (b'BHP', b'3|'),
            (b'OILRATSC', b'11|-13|'),
            (b'WELLSTATE', b''),
        ], dtype=name_dtype)
        general.create_dataset('NameRecordTable', data=name_records)

        time_dtype = np.dtype([
            ('Index', '<u4'),
            ('Offset in days', '<f8'),
            ('Date', '<f8'),
        ])
        master_time = np.array([
            (0, 0.0, 20200101.0),
            (1, 30.0, 20200131.0),
            (2, 60.0, 20200301.0),
        ], dtype=time_dtype)
        general.create_dataset('MasterTimeTable', data=master_time)

        wells = f.create_group('TimeSeries/WELLS')
        wells.create_dataset('Origins', data=np.array([b'PROD1', b'INJ1'], dtype='S100'))
        wells.create_dataset('Variables', data=np.array([b'BHP', b'OILRATSC', b'WELLSTATE'], dtype='S14'))
        # shape (n_timesteps, n_vars, n_origins)
        data = np.array([
            [[3000.0, 0.0], [500.0, 0.0], [1.0, 2.0]],
            [[2950.0, 0.0], [480.0, 0.0], [1.0, 2.0]],
            [[2900.0, 0.0], [460.0, 0.0], [1.0, 2.0]],
        ])
        wells.create_dataset('Data', data=data)
        wells.create_dataset('Timesteps', data=np.array([0, 1, 2], dtype='u4'))

    return path


@pytest.fixture
def sr3_path(tmp_path):
    return _make_sr3(str(tmp_path / 'synthetic.sr3'))


def test_read_sr3_returns_simdataframe(sr3_path):
    sdf = read_sr3(sr3_path)
    assert isinstance(sdf, SimDataFrame)
    assert sdf.shape == (3, 6)
    assert 'BHP:PROD1' in sdf.columns
    assert 'OILRATSC:INJ1' in sdf.columns


def test_read_sr3_units(sr3_path):
    sdf = read_sr3(sr3_path)
    units = sdf.get_units()
    assert units['BHP:PROD1'] == 'psi'
    assert units['OILRATSC:PROD1'] == 'bbl/day'
    assert units.get('WELLSTATE:PROD1') is None


def test_read_sr3_values_and_index(sr3_path):
    sdf = read_sr3(sr3_path)
    assert list(sdf['BHP:PROD1'].values) == [3000.0, 2950.0, 2900.0]
    assert sdf.index[0].year == 2020 and sdf.index[0].month == 1 and sdf.index[0].day == 1


def test_read_sr3_merge_false_returns_dict(sr3_path):
    result = read_sr3(sr3_path, merge=False)
    assert isinstance(result, dict)
    assert set(result.keys()) == {'WELLS'}
    assert isinstance(result['WELLS'], SimDataFrame)


def test_read_sr3_missing_category_raises(sr3_path):
    with pytest.raises(ValueError):
        read_sr3(sr3_path, categories=['GROUPS'], merge=True)
