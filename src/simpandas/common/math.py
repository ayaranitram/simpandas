# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.8'
__release__ = 20260503
__all__ = ['jitter', 'znorm', 'minmaxnorm']

import numpy as np


def jitter(df, std=0.10):
    """Apply random jitter to a DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame or SimDataFrame
        Input data.
    std : float, optional
        Standard deviation of the random noise multiplier. The default is
        0.10, meaning values are perturbed by roughly ±10%.

    Returns
    -------
    same type as ``df``
        DataFrame with jitter applied elementwise.
    """
    jit = np.random.randn(len(df), len(df.columns))
    jit = (jit * std) + 1
    return df * jit


def znorm(df):
    """Z-score normalize each column of a DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame or SimDataFrame
        Input data.

    Returns
    -------
    same type as ``df``
        Normalized data where each column has mean 0 and standard deviation 1.
    """
    return (df - df.mean()) / df.std()


def minmaxnorm(df):
    """Min-max normalize each column of a DataFrame to the range [0, 1].

    Parameters
    ----------
    df : pandas.DataFrame or SimDataFrame
        Input data.

    Returns
    -------
    same type as ``df``
        Normalized data where each column is rescaled to lie between 0 and 1.
    """
    return (df - df.min()) / (df.max() - df.min())
