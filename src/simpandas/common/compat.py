# -*- coding: utf-8 -*-
"""
Pandas compatibility layer for supporting both pandas 1.x and 2.x

Created on March 3, 2026
@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.84.0'
__release__ = 20260303
__all__ = ['concat_compat', 'PANDAS_VERSION', 'PANDAS_GE_20']

import pandas as pd
from packaging import version

# Detect pandas version
PANDAS_VERSION = version.parse(pd.__version__)
PANDAS_GE_20 = PANDAS_VERSION >= version.parse("2.0.0")


def concat_compat(objs, ignore_index=False, sort=False, **kwargs):
    """
    Compatibility wrapper for concatenating pandas objects.
    
    This function provides a unified interface for concatenating DataFrames
    and Series that works with both pandas 1.x and 2.x. It replaces the
    deprecated DataFrame.append() and Series.append() methods.
    
    Parameters
    ----------
    objs : list of DataFrame/Series, or single DataFrame/Series
        Objects to concatenate. If a single object is provided, it will
        be returned as-is.
    ignore_index : bool, default False
        If True, do not use the index values along the concatenation axis.
    sort : bool, default False
        Sort non-concatenation axis if it is not already aligned.
    **kwargs : dict
        Additional keyword arguments to pass to pd.concat()
        
    Returns
    -------
    DataFrame or Series
        Concatenated object
        
    Examples
    --------
    Replace deprecated append():
    >>> # Old (deprecated in pandas 2.0):
    >>> # df = df1.append(df2)
    >>> 
    >>> # New (compatible with pandas 1.x and 2.x):
    >>> df = concat_compat([df1, df2], ignore_index=True)
    
    Notes
    -----
    The deprecated DataFrame.append() method was removed in pandas 2.0.
    This wrapper ensures code works with both pandas 1.x and 2.x by
    using pd.concat() with appropriate parameters.
    """
    # If objs is not a list, return it as-is (edge case)
    if not isinstance(objs, (list, tuple)):
        return objs
    
    # If only one object, return it directly
    if len(objs) == 1:
        return objs[0]
    
    # Use pd.concat for all pandas versions
    # The function signature is compatible across 1.x and 2.x
    return pd.concat(objs, ignore_index=ignore_index, sort=sort, **kwargs)


def append_compat(original, other, ignore_index=False, sort=False):
    """
    Compatibility wrapper that mimics the old DataFrame.append() behavior.
    
    This function provides backward compatibility for code using the
    deprecated append() method. It internally uses concat_compat().
    
    Parameters
    ----------
    original : DataFrame or Series
        The original object to append to
    other : DataFrame, Series, or list of such
        Object(s) to append
    ignore_index : bool, default False
        If True, do not use the index values
    sort : bool, default False
        Sort non-concatenation axis if not aligned
        
    Returns
    -------
    DataFrame or Series
        Concatenated result
        
    Examples
    --------
    >>> # Replace: result = df.append(other_df)
    >>> result = append_compat(df, other_df)
    """
    if isinstance(other, (list, tuple)):
        objs = [original] + list(other)
    else:
        objs = [original, other]
    
    return concat_compat(objs, ignore_index=ignore_index, sort=sort)
