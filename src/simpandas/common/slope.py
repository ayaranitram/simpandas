# -*- coding: utf-8 -*-
"""
Created on Sun Jan 23 22:38:16 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.5.1'
__release__ = 20220920
__all__ = ['slope']

import numpy as np
import pandas as pd
import warnings


def slope(df, x=None, y=None, window=None, slope=True, intercept=False):
    """
    Calculates the slope of column Y vs column X or vs index if 'x' is None

    Parameters
    ----------
    df : DataFrame or SimDataFrame
        The DataFrame to work with.
    x : str, optional
        The name of the column to be used as X.
        If None, the index of the DataFrame will be used as X.
        The default is None.
    y : str, optional
        The name of the column to be used as Y.
        If None, the first argument will be considered as Y (not as X).
        The default is None.
    window : int, float or str, optional
        The half-size of the rolling window to calculate the slope.
        if None : the slope will be calculated from the entire dataset.
        if int : window rows before and after of each row will be used to calculate the slope
        if float : the window size will be variable, with window values of X arround each row's X. Not compatible with datetime columns
        if str : the window string will be used as timedelta arround the datetime X
        The default is None.
    slope : bool, optional
        Set it True to return the slope of the linear fit. The default is True.
    intercept : bool, optional
        Set it True to return the intersect of the linear fit. The default is False.
    if both slope and intercept are True, a tuple of both results will be returned

    Returns
    -------
    numpy array
        The array containing the desired output.

    """
    # def _deltaDate(datetime):
    #     return np.cumsum(np.array([0] + list(datetime.astype('timedelta64[s]').astype(float)/60/60/24)))

    # def _checkDateTime(data):
    #     if isinstance(data, pd.Series):
    #         return _deltaDate(data)
    #     if 'datetime'

    warnings.simplefilter('ignore', np.RankWarning)

    # understanding input paramenters
    df = df.squeeze()
    if isinstance(df, (pd.Series,)):
        if window is None and y is None and x is not None:
            window, x = x, None
    elif x is not None and y is None and window is None:
        if x not in df.columns:
            window, x = x, None
    elif x is not None and y is not None and window is None and y not in df.columns:
        y, window = None, y


    # if window is None, calculate the slope for the entire dataset
    if window is None:

        if x is None:
            if isinstance(df.index, pd.DatetimeIndex):
                #xx = _deltaDate(df.index)
                xx = np.cumsum(np.array([0] + list(np.diff(df.index).astype('timedelta64[s]').astype(float)/60/60/24)))
            else:
                xx = df.index.to_numpy()
        else:
            if 'datetime' in str(df[x].dtype):
                #xx = _deltaDate(df[x])
                xx = np.cumsum(np.array([0] + list(np.diff(df[x]).astype('timedelta64[s]').astype(float)/60/60/24)))
            else:
                xx = df[x].to_numpy()

        if y is None:
            if isinstance(df, (pd.Series,)):
                if 'datetime' in str(df.dtype):
                    #yy = _deltaDate(df)
                    yy = np.cumsum(np.array([0] + list(np.diff(df).astype('timedelta64[s]').astype(float)/60/60/24)))
                else:
                    yy = df.to_numpy()
            elif x is not None and x in df.columns:
                if len(df.columns) == 2:
                    dfs = df.drop(columns=x).squeeze()
                    if 'datetime' in str(dfs.dtype):
                        #yy = _deltaDate(dfs)
                        yy = np.cumsum(np.array([0] + list(np.diff(dfs).astype('timedelta64[s]').astype(float)/60/60/24)))
                    else:
                        yy = dfs.to_numpy()
                    del dfs
                elif len(df.columns) == 1:
                    dfs = df.squeeze()
                    if 'datetime' in str(dfs.dtype):
                        #yy = _deltaDate(dfs)
                        yy = np.cumsum(np.array([0] + list(np.diff(dfs).astype('timedelta64[s]').astype(float)/60/60/24)))
                    else:
                        yy = dfs.to_numpy()
                    del dfs
                else:
                    yy = df.drop(columns=x).to_numpy()
            else:
                if len(df.columns) == 1:
                    dfs = df.squeeze()
                    if 'datetime' in str(dfs.dtype):
                        #yy = _deltaDate(dfs)
                        yy = np.cumsum(np.array([0] + list(np.diff(dfs).astype('timedelta64[s]').astype(float)/60/60/24)))
                    else:
                        yy = dfs.to_numpy()
                    del dfs
                else:
                    yy = df.to_numpy()
        else:
            if len(df[y]) == 1:
                dfs = df.squeeze()
                if 'datetime' in str(dfs.dtype):
                    #yy = _deltaDate(dfs)
                    yy = np.cumsum(np.array([0] + list(np.diff(dfs).astype('timedelta64[s]').astype(float)/60/60/24)))
                else:
                    yy = dfs.to_numpy()
                del dfs


        if slope and intercept:
            return np.polyfit(xx, yy, 1, full=False)
        elif slope and not intercept:
            return np.polyfit(xx, yy, 1, full=False)[0]
        elif not slope and intercept:
            return np.polyfit(xx, yy, 1, full=False)[1]
        else:
            return None


    # calculate slope every N (window) rows
    elif type(window) is int:

        if x is None:
            if isinstance(df.index, pd.DatetimeIndex):
                #xx = [np.cumsum(np.array([0] + list(np.diff(df.index[max(0,ii-window):min(len(df),ii+window)]).astype('timedelta64[s]').astype(float)/60/60/24))) for ii in range(len(df))]
                xx = [np.cumsum(np.diff(np.array(list(df.index[0:1]) + list(df.index[max(0,ii-window):min(len(df),ii+window)]))).astype('timedelta64[s]').astype(float)/60/60/24) for ii in range(len(df))]
            else:
                xx = [df.iloc[max(0,ii-window):min(ii+window,len(df))].index for ii in range(len(df))]
        else:
            if 'datetime' in str(df[x].dtype):
                #xx = [np.cumsum(np.array([0] + list(np.diff(df.iloc[max(0,ii-window):min(len(df),ii+window)][x]).astype('timedelta64[s]').astype(float)/60/60/24))) for ii in range(len(df))]
                xx = [np.cumsum(np.diff(np.array(list(df.iloc[0:1]) + list(df.iloc[max(0,ii-window):min(len(df),ii+window)][x]))).astype('timedelta64[s]').astype(float)/60/60/24) for ii in range(len(df))]
            else:
                xx = [df.iloc[max(0,ii-window):min(ii+window,len(df))][x] for ii in range(len(df))]

        if y is None:
            if isinstance(df, (pd.Series,)):
                yy = [df.iloc[max(0,ii-window):min(len(df),ii+window)].to_numpy() for ii in range(len(df))]
            elif x is not None and x in df.columns:
                dfs = df.drop(columns=x).squeeze()
                yy = [dfs.iloc[max(0,ii-window):min(len(dfs),ii+window)].to_numpy() for ii in range(len(dfs))]
            else:
                yy = [df.iloc[max(0,ii-window):min(len(df),ii+window)].to_numpy() for ii in range(len(df))]
        else:
            if isinstance(df, (pd.Series,)):
                yy = [df.iloc[max(0,ii-window):min(len(df),ii+window)].to_numpy() for ii in range(len(df))]
            else:
                yy = [df.iloc[max(0,ii-window):min(len(df),ii+window)][y].to_numpy() for ii in range(len(df))]


    # window is a str representing a timedelta
    elif type(window) is str:
        if ((x is None and isinstance(df.index,pd.DatetimeIndex)) or (x is not None and 'datetime' in str(df[x].dtype))):
            window = pd.to_timedelta(window)
        else:
            raise ValueError('string window, representing timedelta, only works with datetime index or X column.')

        if x is None:
            xx = [np.cumsum(np.diff(np.array(list(df.index[0:1]) + list(df[(df.index>=(df.index[ii]-window)) & (df.index<=(df.index[ii]+window))].index))).astype('timedelta64[s]').astype(float)/60/60/24) for ii in range(len(df))]
        else:
            xx = [np.cumsum(np.diff(np.array(list(df.iloc[0:1][x]) + list(df[(df.index>=(df.index[ii]-window)) & (df.index<=(df.index[ii]+window))][x]))).astype('timedelta64[s]').astype(float)/60/60/24) for ii in range(len(df))]

        if y is None:
            if isinstance(df, (pd.Series,)):
                yy = [df[(df.index>=(df.index[ii]-window)) & (df.index<=(df.index[ii]+window))].to_numpy() for ii in range(len(df))]
            elif x is not None and x in df.columns:
                dfs = df.drop(columns=x).squeeze()
                yy = [dfs[(dfs.index>=(dfs.index[ii]-window)) & (dfs.index<=(dfs.index[ii]+window))].to_numpy() for ii in range(len(dfs))]
            else:
                yy = [df[(df.index>=(df.index[ii]-window)) & (df.index<=(df.index[ii]+window))].to_numpy() for ii in range(len(df))]
        else:
            if isinstance(df, (pd.Series,)):
                yy = [df[(df.index>=(df.index[ii]-window)) & (df.index<=(df.index[ii]+window))].to_numpy() for ii in range(len(df))]
            else:
                yy = [df[(df.index>=(df.index[ii]-window)) & (df.index<=(df.index[ii]+window))][y].to_numpy() for ii in range(len(df))]


    else:
        raise NotImplementedError("'window' must be int, float, str or None.")

    polys = np.array([np.polyfit(xx[ii], yy[ii], 1, full=False) for ii in range(len(xx))])

    warnings.simplefilter('default', np.RankWarning)

    if slope and intercept:
        return polys
    elif slope and not intercept:
        return polys[:,0]
    elif not slope and intercept:
        return polys[:,1]