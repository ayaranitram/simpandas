import pandas as pd
import pytest
from simpandas.common.filters import zeros

def test_zeros_dataframe():
    df = pd.DataFrame({'a':[0,0],'b':[1,0]})
    out = zeros(df, axis=0)
    assert isinstance(out, pd.Series)
    assert out['a']
    assert not out['b']

def test_zeros_series():
    s = pd.Series([0,0,0])
    out = zeros(s, axis=1)
    assert out.dtype == bool
