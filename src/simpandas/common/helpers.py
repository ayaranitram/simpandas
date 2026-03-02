# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.5'
__release__ = 20230223
__all__ = ['clean_axis', 'string_new_name', 'type_of_frame', 'main_key', 'item_key', 'hashable']


import pandas as pd


def clean_axis(axis=None):
    """Normalize various axis specifiers to integer codes.

    The function accepts strings like ``'row'``, ``'columns'``, boolean or
    numeric values and returns ``0`` for rows, ``1`` for columns, and
    ``2`` for both axes.  This mirrors the behaviour of several SimPandas
    functions that accept ``axis`` arguments.

    Parameters
    ----------
    axis : {None, int, float, bool, str}
        Axis specifier to clean.

    Returns
    -------
    int
        Normalised axis code (0, 1, or 2).
    """
    if axis is None:
        return 0
    if type(axis) is str and axis.lower() in ['row', 'rows', 'ind', 'index']:
        return 0
    if type(axis) is str and axis.lower() in ['col', 'cols', 'column', 'columns']:
        return 1
    if type(axis) is str and axis.lower() in ['both', 'rows&cols', 'cols&rows', 'all']:
        return 2
    if type(axis) is bool:
        return int(axis)
    if type(axis) is float:
        return int(axis)
    return axis


def string_new_name(new_name, intersection_character='∩'):
    """Generate a combined name from a mapping of original to new names.

    This is used when constructing intersection/union names for columns.

    Parameters
    ----------
    new_name : dict
        Mapping from original label to proposed new label.
    intersection_character : str, optional
        Character used to join multiple unique values.

    Returns
    -------
    str
        Single string representing the set of new names.
    """
    if len(new_name) == 1:
        return list(new_name.values())[0]
    else:
        return intersection_character.join(map(str, dict.fromkeys(new_name.values())))


def type_of_frame(frame):
    """Return the class corresponding to a DataFrame-like object.

    Parameters
    ----------
    frame : object
        Attempt to detect if ``frame`` is a SimSeries, SimDataFrame, pandas
        Series, or pandas DataFrame.

    Returns
    -------
    type
        One of ``SimSeries``, ``SimDataFrame``, ``pandas.Series`` or
        ``pandas.DataFrame``.

    Raises
    ------
    TypeError
        If ``frame`` is not a recognised type.
    """
    from simpandas import SimSeries, SimDataFrame
    from pandas import Series, DataFrame
    try:
        if frame._isSimSeries:
            return SimSeries
    except:
        try:
            if frame._isSimDataFrame:
                return SimDataFrame
        except:
            if type(frame) is Series:
                return Series
            elif type(frame) is DataFrame:
                return DataFrame
            else:
                raise TypeError('frame is not an instance of Pandas or SimPandas frames')


def main_key(key, clean=True, nameSeparator=':'):
    """Extract the 'main' portion of a compound name string.

    Given strings or iterable keys of the form ``MAIN:ITEM``, returns the
    part before the separator.  Works on scalars, lists, tuples or pandas
    Series objects.

    Parameters
    ----------
    key : str or iterable or pandas.Series
        Input key(s).
    clean : bool, default True
        Whether to deduplicate the output when a list/tuple is supplied.
    nameSeparator : str, default ':'
        Separator used between main and item components.

    Returns
    -------
    str or list
        Extracted main part(s).
    """
    if type(key) is str:
        if len(key.strip()) > 0:
            return key.strip().split(nameSeparator)[0]
        else:
            return ''
    if type(key) is tuple and len(key) == 2:
        return main_key(str(key[0]), clean=clean, nameSeparator=nameSeparator)
    if type(key) is list or type(key) is tuple:
        results = []
        for K in key:
            results.append(main_key(K))
        if clean:
            return list(set(results))
        else:
            return list(results)
    if isinstance(key, pd.Series):
        return main_key(key.name)


def item_key(key, clean=True, nameSeparator=':'):
    """Extract the 'item' portion of a compound name string.

    Similar to :func:`main_key` but returns the substring after the
    ``nameSeparator``.

    Parameters
    ----------
    key : str or iterable or pandas.Series
        Input key(s).
    clean : bool, default True
        Whether to deduplicate the output when a list/tuple is supplied.
    nameSeparator : str, default ':'
        Separator used between main and item components.

    Returns
    -------
    str or list
        Extracted item part(s).
    """
    if type(key) is str:
        if len(key.strip()) > 0:
            if nameSeparator in key.strip():
                return key.strip().split(nameSeparator)[-1]
        else:
            return ''
    if type(key) is tuple and len(key) == 2:
        return item_key(str(key[0]), clean=clean, nameSeparator=nameSeparator)
    if type(key) is list or type(key) is tuple:
        results = []
        for K in key:
            results.append(item_key(K))
        if clean:
            return list(set(results))
        else:
            return list(results)
    if isinstance(key, pd.Series):
        return item_key(key.name)


def hashable(x):
    """Determine whether `v` can be hashed."""
    try:
        hash(x)
    except TypeError:
        return False
    return True
