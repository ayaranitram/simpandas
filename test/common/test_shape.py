import pandas as pd
import pytest
from simpandas.common.shape import melt, pivot

# simple dataset for melt/pivot

def test_melt_basic():
    df = pd.DataFrame({'A_1':[1,2], 'A_2':[3,4]})
    out = melt(df)
    assert 'value' in out.columns or 'A' in out.columns
    # ensure returned dataframe has expected length
    assert len(out) == 4

def test_pivot_basic():
    df = pd.DataFrame({'time':[0,1,0,1], 'item':['x','x','y','y'], 'value':[1,2,3,4]})
    out = pivot(df, item='item', index='time', values='value')
    assert out.shape == (2,2)
    assert 'value:x' in out.columns
