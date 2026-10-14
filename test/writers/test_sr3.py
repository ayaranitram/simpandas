# -*- coding: utf-8 -*-
"""Tests for the CMG SR3 writer (round-trips through ``read_sr3``)."""

import os

import numpy as np
import pandas as pd
import pytest

h5py = pytest.importorskip('h5py')

from simpandas import SimDataFrame, read_sr3, write_sr3

_REAL_SAMPLE = os.path.join(os.path.dirname(__file__), '..', '..', 'gm_spe3_pedersen84.sr3')


def _frame(units=None, columns=None):
    idx = pd.DatetimeIndex(['2020-01-01', '2020-01-31', '2020-03-01 12:00'], name='DATE')
    data = {
        'BHP:PROD1': [3000.0, 2950.0, 2900.0],
        'OILRATSC:PROD1': [500.0, 480.0, 460.0],
        'OILRATSC:INJ1': [0.0, 0.0, 0.0],
    }
    if columns:
        data = {c: data['BHP:PROD1'] for c in columns}
    df = pd.DataFrame(data, index=idx)
    return SimDataFrame(df, units=units or {c: 'psi' if c.startswith('BHP') else 'bbl/day' for c in df.columns},
                        index_units='date')


def test_roundtrip_values_units_dates(tmp_path):
    path = str(tmp_path / 'out.sr3')
    sdf = _frame()
    write_sr3(sdf, path)
    back = read_sr3(path)
    assert set(sdf.columns) <= set(back.columns)  # SR3 stores a full variables x origins grid
    assert back['BHP:INJ1'].isna().all()
    np.testing.assert_allclose(back['BHP:PROD1'].values, [3000.0, 2950.0, 2900.0])
    assert back.get_units()['BHP:PROD1'] == 'psi'
    assert back.get_units()['OILRATSC:PROD1'] == 'bbl/day'
    assert list(back.index) == list(sdf.index)


def test_to_sr3_method(tmp_path):
    path = str(tmp_path / 'out.sr3')
    _frame().to_sr3(path)
    assert read_sr3(path).shape == (3, 4)


def test_units_are_converted_to_file_output_units(tmp_path):
    path = str(tmp_path / 'out.sr3')
    sdf = _frame(units={'BHP:PROD1': 'kPa', 'OILRATSC:PROD1': 'bbl/day', 'OILRATSC:INJ1': 'bbl/day'})
    write_sr3(sdf, path)
    back = read_sr3(path)
    assert back.get_units()['BHP:PROD1'] == 'psi'
    np.testing.assert_allclose(back['BHP:PROD1'].values, np.array([3000.0, 2950.0, 2900.0]) * 0.1450377, rtol=1e-4)


def test_layer_columns(tmp_path):
    path = str(tmp_path / 'out.sr3')
    sdf = _frame(columns=['STATUS:PROD1:7,3,2', 'STATUS:PROD1:7,3,1'], units={})
    write_sr3(sdf, path)
    with h5py.File(path, 'r') as f:
        assert [o.decode() for o in f['TimeSeries/LAYERS/Origins'][:]] == ['PROD1{7,3,2}', 'PROD1{7,3,1}']
        assert f['TimeSeries/LAYERS/LayerTable'][1]['Connect To'] == 1
    assert 'STATUS:PROD1:7,3,2' in read_sr3(path).columns


def test_category_override_and_default(tmp_path):
    path = str(tmp_path / 'out.sr3')
    write_sr3(_frame(), path, categories={'INJ1': 'GROUPS'})
    parts = read_sr3(path, merge=False)
    assert set(parts) == {'WELLS', 'GROUPS'}
    assert 'OILRATSC:INJ1' in parts['GROUPS'].columns


def test_unknown_keyword_keeps_unit(tmp_path):
    path = str(tmp_path / 'out.sr3')
    sdf = _frame(columns=['MYVAR:PROD1'], units={'MYVAR:PROD1': 'ft'})
    write_sr3(sdf, path)
    assert read_sr3(path).get_units()['MYVAR:PROD1'] == 'ft'


def test_nan_rows_are_preserved(tmp_path):
    path = str(tmp_path / 'out.sr3')
    sdf = _frame()
    sdf.iloc[1, 0] = np.nan
    write_sr3(sdf, path)
    back = read_sr3(path)
    assert np.isnan(back['BHP:PROD1'].values[1])


def test_non_datetime_index_requires_start_date(tmp_path):
    sdf = SimDataFrame(pd.DataFrame({'BHP:PROD1': [1.0, 2.0]}, index=[0.0, 30.0]), units={'BHP:PROD1': 'psi'})
    with pytest.raises(ValueError):
        write_sr3(sdf, str(tmp_path / 'out.sr3'))
    write_sr3(sdf, str(tmp_path / 'out.sr3'), start_date='2020-01-01')
    assert read_sr3(str(tmp_path / 'out.sr3')).index[1] == pd.Timestamp('2020-01-31')


@pytest.mark.skipif(not os.path.exists(_REAL_SAMPLE), reason='real SR3 sample not available')
def test_real_file_roundtrip(tmp_path):
    src = read_sr3(_REAL_SAMPLE)
    path = str(tmp_path / 'out.sr3')
    write_sr3(src, path)
    back = read_sr3(path)
    assert set(back.columns) == set(src.columns)
    a, b = src.as_pandas(), back.as_pandas()[src.columns]
    np.testing.assert_allclose(a.values, b.values)
    assert (a.index == b.index).all()
