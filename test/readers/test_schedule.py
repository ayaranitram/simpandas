# -*- coding: utf-8 -*-
"""Tests for the schedule keywords reader."""

import pandas as pd
from simpandas import SimDataFrame, read_auto, read_schedule


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


def test_read_auto_dispatches_data_to_schedule(tmp_path):
    data_text = """RUNSPEC
UNITS METRIC
GRID
SCHEDULE
DATES
 01 JAN 2020 /
/
WCONPROD
 'WELL-1' OPEN ORAT 100 10 0 /
/
"""
    data_path = tmp_path / 'TEST.DATA'
    data_path.write_text(data_text)

    sdf = read_auto(str(data_path))
    assert isinstance(sdf, SimDataFrame)
    assert sdf.units['OIL rate'] == 'SM3/DAY'
    assert sdf.units['GAS rate'] == 'SM3/DAY'
