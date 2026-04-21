import pytest
import simpandas as spd
import pandas as pd


def test_loc_indexer_basic():
    df = spd.SimDataFrame({'A':[1,2,3], 'B':[3,2,1]},
                          units={'A':'m', 'B': 'in'},
                          index=['2023-01-01', '2023-01-05', '2023-01-07'])
    assert df.loc['2023-01-01', 'A'] == 1


def test_loc_unit_conversion():
    df = spd.SimDataFrame({'A':[1,2,3]}, units={'A':'m'})
    df.loc[0, 'A'] = (1000, 'mm')
    assert df.loc[0, 'A'] == 1


def test_loc_new_column_units():
    df = spd.SimDataFrame({'A':[1]}, units={'A':'m'})
    df.loc[0, 'B'] = (5, 's')
    assert df.get_units()['B'] == 's'


def test_iloc_basic():
    df = spd.SimDataFrame({'A':[1,2],'B':[3,4]}, units={'A':'m','B':'s'})
    assert df.iloc[0, 0] == 1


def test_iloc_set():
    df = spd.SimDataFrame({'A':[1,2]}, units={'A':'m'})
    df.iloc[0, 0] = 10
    assert df.iloc[0, 0] == 10

