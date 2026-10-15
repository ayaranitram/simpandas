# -*- coding: utf-8 -*-
"""Tests for the schedule keywords reader."""

from pathlib import Path

import pandas as pd
from simpandas import SimDataFrame, read_auto, read_schedule


def test_read_schedule_complete_field_deck():
    data_path = Path(__file__).parent.parent / '_testing_data' / 'SAMPLE_SCHEDULE.DATA'
    sdf = read_schedule(str(data_path))

    assert isinstance(sdf, SimDataFrame)
    assert set(sdf['keyword']) == {'WCONHIST', 'WCONINJH', 'WCONPROD', 'WCONINJE'}
    assert set(sdf['well']) == {'WELL-1', 'WELL-2', 'WELL-3'}
    assert len(sdf) == 15
    expected_dates = [
        pd.Timestamp('2020-01-01'),
        pd.Timestamp('2020-01-01'),
        pd.Timestamp('2020-01-01'),
        pd.Timestamp('2020-02-01'),
        pd.Timestamp('2020-02-01'),
        pd.Timestamp('2020-02-01'),
        pd.Timestamp('2020-04-01'),
        pd.Timestamp('2020-04-01'),
        pd.Timestamp('2020-04-01'),
        pd.Timestamp('2021-01-01'),
        pd.Timestamp('2021-01-01'),
        pd.Timestamp('2021-01-01'),
        pd.Timestamp('2021-02-01'),
        pd.Timestamp('2021-02-01'),
        pd.Timestamp('2021-02-01'),
    ]
    assert sdf['date'].tolist() == expected_dates
    assert sdf.units['OIL rate'] == 'STB/DAY'
    assert sdf.units['WATER rate'] == 'STB/DAY'


def test_read_schedule_detects_field_units(tmp_path):
    data_text = """RUNSPEC
UNITS FIELD
GRID
SCHEDULE
DATES
 01 JAN 2020 /
/
WCONPROD
 'WELL-1' OPEN ORAT 100 10 0 /
/
WCONHIST
 'WELL-1' OPEN ORAT 100 10 0 /
/
WCONINJH
 'WELL-1' OPEN RATE 20 100 200 /
/
WCONINJE
 'WELL-1' OPEN RATE 20 /
/
"""
    data_path = tmp_path / 'TEST.DATA'
    data_path.write_text(data_text)

    sdf = read_schedule(str(data_path))
    assert isinstance(sdf, SimDataFrame)
    assert 'keyword' in sdf.columns
    assert 'date' in sdf.columns
    assert 'well' in sdf.columns
    assert sdf.units['OIL rate'] == 'STB/DAY'
    assert sdf.units['WATER rate'] == 'STB/DAY'
    assert sdf.units['GAS rate'] == 'MSCF/DAY'


def test_read_schedule_repeats_dates_for_time_and_tstep(tmp_path):
    data_text = """RUNSPEC
FIELD
GRID
SCHEDULE
START
 1 JAN 2020 /
WCONHIST
 'WELL-1' OPEN ORAT 100 /
 'WELL-2' OPEN ORAT 200 /
/
WCONINJH
 'WELL-3' WATER OPEN 300 100 20 /
/
TIME
 30 /
/
WCONHIST
 'WELL-1' OPEN ORAT 110 /
 'WELL-2' OPEN ORAT 210 /
/
WCONINJH
 'WELL-3' WATER OPEN 310 110 21 /
/
TSTEP
 30 /
/
WCONHIST
 'WELL-1' OPEN ORAT 120 /
 'WELL-2' OPEN ORAT 220 /
/
WCONINJH
 'WELL-3' WATER OPEN 320 120 22 /
/
END
"""
    data_path = tmp_path / 'TIME_TSTEP.DATA'
    data_path.write_text(data_text)

    sdf = read_schedule(data_path)
    expected_dates = [
        pd.Timestamp('2020-01-01'),
        pd.Timestamp('2020-01-01'),
        pd.Timestamp('2020-01-01'),
        pd.Timestamp('2020-01-31'),
        pd.Timestamp('2020-01-31'),
        pd.Timestamp('2020-01-31'),
        pd.Timestamp('2020-03-01'),
        pd.Timestamp('2020-03-01'),
        pd.Timestamp('2020-03-01'),
    ]
    assert sdf['date'].tolist() == expected_dates


def test_read_auto_dispatches_data_to_schedule(tmp_path):
    data_text = """RUNSPEC
UNITS METRIC
GRID
SCHEDULE
DATES
 01 JAN 2020 /
/
WCONHIST
 'WELL-1' OPEN ORAT 100 10 0 /
/
"""
    data_path = tmp_path / 'TEST.DATA'
    data_path.write_text(data_text)

    sdf = read_auto(str(data_path))
    assert isinstance(sdf, SimDataFrame)
    assert sdf.units['OIL rate'] == 'SM3/DAY'
    assert sdf.units['GAS rate'] == 'SM3/DAY'
