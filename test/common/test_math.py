import pytest
from simpandas.common.math import jitter, znorm, minmaxnorm
import pandas as pd
import numpy as np

def test_jitter_preserves_shape():
    df = pd.DataFrame({'a':[1,2,3],'b':[4,5,6]})
    out = jitter(df, std=0.0)  # with zero noise should equal original
    assert out.shape == df.shape
    # values may not equal exactly but std=0 should leave them identical
    assert out.equals(df)

def test_znorm():
    df = pd.DataFrame({'x':[1,2,3,4]})
    z = znorm(df)
    assert pytest.approx(z.mean().iloc[0], rel=1e-6) == 0
    assert pytest.approx(z.std().iloc[0], rel=1e-6) == 1

def test_minmaxnorm():
    df = pd.DataFrame({'x':[2,4,6]})
    m = minmaxnorm(df)
    assert m['x'].min() == 0
    assert m['x'].max() == 1
