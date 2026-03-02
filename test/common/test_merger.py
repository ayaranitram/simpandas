import pytest
import pandas as pd
from simpandas.common.merger import concat, merge_index, merge_units
from simpandas import SimDataFrame, SimSeries

def test_concat_basic():
    df1 = SimDataFrame({'a':[1]}, units='m')
    df2 = SimDataFrame({'a':[2]}, units='m')
    out = concat([df1, df2])
    assert isinstance(out, SimDataFrame)
    assert out.shape[0] == 2

def test_concat_type_error():
    with pytest.raises(TypeError):
        concat('not a list')

def test_merge_units_two():
    df1 = SimDataFrame({'a':[1]}, units='m')
    df2 = SimDataFrame({'b':[2]}, units='s')
    merged = merge_units(df1, df2)
    assert merged['a']=='m' and merged['b']=='s'

def test_merge_index_simple():
    left = pd.Series([1,2], index=[0,1])
    right = pd.Series([3,4], index=[1,2])
    l2, r2 = merge_index(left, right)
    assert 0 in l2.index and 2 in r2.index

def test_merge_index_invalid_how():
    with pytest.raises(ValueError):
        merge_index(pd.Series([1]), pd.Series([2]), how='bad')
