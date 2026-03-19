import pytest
import pandas as pd
import numpy as np
from simpandas.common.slope import slope

def test_slope_simple():
    df = pd.DataFrame({'y':[0,1,2,3]})
    # slope against index should be 1
    s = slope(df)
    assert pytest.approx(s, rel=1e-6) == 1

def test_slope_with_xy():
    df = pd.DataFrame({'x':[0,1,2],'y':[0,2,4]})
    s = slope(df, x='x', y='y')
    assert pytest.approx(s, rel=1e-6) == 2

def test_slope_window():
    df = pd.DataFrame({'y':[0,2,4,6,8]})
    s = slope(df, window=3)
    assert isinstance(s, np.ndarray)
    assert len(s) == 5
