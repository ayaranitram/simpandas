# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.2'
__release__ = 20220920
__all__ = ['jitter', 'znorm', 'minmaxnorm']

import numpy as np

def jitter(df, std=0.10):
    jit = np.random.randn(len(df), len(df.columns))
    jit = (jit * std) + 1
    return df * jit


def znorm(df):
    return (df - df.mean()) / df.std()


def minmaxnorm(df):
    return (df - df.min()) / (df.max() - df.min())