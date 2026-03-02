# -*- coding: utf-8 -*-
"""
Created on Thu Nov 17 00:32:09 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
from simpandas import SimDataFrame, SimSeries
import pandas as pd


def test_basic_creation():
    df = SimDataFrame({'a':[1,2,3]}, units='m')
    assert isinstance(df, SimDataFrame)
    assert df.get_units()['a']=='m'
    assert df.to_pandas().equals(pd.DataFrame({'a':[1,2,3]}))


def test_head_tail():
    df = SimDataFrame({'a':[1,2,3,4,5]}, units='kg')
    assert df.head(2).shape[0]==2
    assert df.tail(2).shape[0]==2


def test_arithmetic():
    df = SimDataFrame({'x':[1,2],'y':[3,4]}, units={'x':'m','y':'m'})
    s = df.add(df)
    assert 'x' in s
    assert s['x'].iloc[0]==2


def test_concat():
    df1 = SimDataFrame({'a':[1]}, units='m')
    df2 = SimDataFrame({'a':[2]}, units='m')
    out = df1.concat(df2)
    assert isinstance(out, SimDataFrame)
    assert out.shape[0]==2


def test_loc_set_get():
    df = SimDataFrame({'a':[1]}, units='m')
    df.loc[0,'a'] = (5,'m')
    assert df.loc[0,'a']==5
    df.loc[1,'b'] = (3,'s')
    assert df.get_units()['b']=='s'


def test_iloc_set_get():
    df = SimDataFrame({'a':[1],'b':[2]}, units={'a':'m','b':'s'})
    df.iloc[0,0] = (10,'m')
    assert df.iloc[0,0]==10


def test_series_conversion():
    df = SimDataFrame({'a':[1,2]}, units='m')
    s = df['a']
    assert isinstance(s, SimSeries)