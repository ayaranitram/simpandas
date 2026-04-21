# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 22:34:40 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
from simpandas import SimDataFrame, SimSeries
from pandas import DataFrame
import sys
import subprocess
import textwrap
import simpandas.common.lazy_unyts as lazy_unyts


def test_lazy_unyts_import():
    # Ensure simpandas does not import unyts at module import time
    code = textwrap.dedent('''
import sys
sys.modules.pop('unyts', None)
import simpandas
print('loaded:' + str('unyts' in sys.modules))
from simpandas import SimDataFrame
sdf = SimDataFrame({'a': [1, 2]}, units=None)
print('after_create:' + str('unyts' in sys.modules))
try:
    sdf.loc[0, 'a'] = (3, 'm')
except Exception:
    pass
print('after_conversion:' + str('unyts' in sys.modules))
''')
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True)
    assert 'loaded:False' in result.stdout
    assert 'after_create:False' in result.stdout
    assert 'after_conversion:True' in result.stdout


def test_lazy_unyts_convertible_warmup_retry(monkeypatch):
    class _FailOnce:
        def __init__(self):
            self.calls = 0

        def __call__(self, *args, **kwargs):
            self.calls += 1
            return self.calls > 1

    state = {'warmups': 0}
    fail_once = _FailOnce()

    monkeypatch.setattr(
        lazy_unyts,
        '_load_unyts',
        lambda: {
            'convertible': fail_once,
            'convert_for_SimPandas': lambda *a, **k: state.__setitem__('warmups', state['warmups'] + 1),
        },
    )

    assert lazy_unyts.convertible('stb/day', 'sm3/day') is True
    assert state['warmups'] == 1


def test_series_index_units_do_not_get_used_for_scalar():
    from simpandas import SimSeries
    from pandas import date_range

    s = SimSeries([1, 2, 3], index=date_range('2100-01-08', periods=3), units='m', index_units='date')
    val = s['2100-01-08']
    assert hasattr(val, 'unit') and str(val.unit) == 'm'
    assert float(val.value) == 1.0


def test_datetime_index_explicit_selection_in_dataframe():
    from simpandas import SimDataFrame
    from pandas import date_range

    df = SimDataFrame({'v': [1, 2, 3]}, index=date_range('2100-01-08', periods=3), units={'v': 'm'}, index_units='date')
    val = df.loc['2100-01-08', 'v']
    assert hasattr(val, 'unit') and str(val.unit) == 'm'
    assert float(val.value) == 1.0


def test_units_preservation():
    data = {'A': [1,2,3,4,5],
            'B': [1.0, 2.0, 3.0, 4.0, 5.0],
            'C': [100, 200, 300, 400, 500],
            'D': [3, 6, 12, 24, 36]}
    units_dict = {'A': 'ml',
             'B': 'cc',
             'C': 'cm',
             'D': 'in'}

    sdf = SimDataFrame(data, units=units_dict)
    assert sdf.get_units()['A'] == 'ml'
    assert sdf.get_units()['B'] == 'cc'


def test_direct_unit_arithmetic():
    sdf = SimDataFrame({'C': [100, 200, 300]}, units={'C': 'cm'})
    result = sdf['C'] ** 3
    assert isinstance(result, SimSeries)


def test_copy_preserves_units():
    sdf = SimDataFrame({'a': [1,2]}, units='kg')
    sdf2 = sdf.copy()
    assert sdf2.get_units()['a'] == 'kg'


def test_describe():
    sdf = SimDataFrame({'x': [1,2,3,4,5]}, units='m')
    desc = sdf.describe()
    assert isinstance(desc, SimDataFrame)
