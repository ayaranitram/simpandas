# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martin Carlos Araya
"""

__version__ = '0.80.1'
__release__ = 20220907

import numpy as np

def jitter(df, std=0.10):
    import numpy as np
    jit = np.random.randn(len(df), len(df.columns))
    jit = (jit * std) + 1
    return df * jit