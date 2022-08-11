# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martin Carlos Araya
"""

from pandas import Series, DataFrame, DatetimeIndex, Timestamp, Index
import warnings

def _simseries_constructor_with_fallback(data=None, index=None, units=None, **kwargs):
    """
    A flexible constructor for SimSeries._constructor, which needs to be able
    to fall back to a Series(if a certain operation does not produce
    units)
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=_SERIES_WARNING_MSG,
                category=FutureWarning,
                module="SimPandas[.*]",
            )
            return SimSeries(data=data, index=index, units=units, **kwargs)
    except TypeError:
        return Series(data=data, index=index, **kwargs)


def _Series2Frame(aSimSeries):
    """
    when a row is extracted from a DataFrame, Pandas returns a Series in wich
    the columns of the DataFrame are converted to the indexes of the Series and
    the extracted index from the DataFrame is set as the Name of the Series.

    This function returns the proper DataFrame view of such Series.

    Works with SimSeries as well as with Pandas standard Series
    """
    if isinstance(aSimSeries, DataFrame):
        return aSimSeries
    if type(aSimSeries) is SimSeries:
        try:
            return SimDataFrame(data=dict(zip(list(aSimSeries.index), aSimSeries.to_list())), units=aSimSeries.get_Units(), index=aSimSeries.columns, speak=aSimSeries.speak, indexName=aSimSeries.index.name, indexUnits=aSimSeries.indexUnits, nameSeparator=aSimSeries.nameSeparator, intersectionCharacter=aSimSeries.intersectionCharacter, autoAppend=aSimSeries.autoAppend, operatePerName=aSimSeries.operatePerName)
        except:
            return aSimSeries
    if type(aSimSeries) is Series:
        try:
            return DataFrame(data=dict(zip(list(aSimSeries.index), aSimSeries.to_list())), index=aSimSeries.columns)
        except:
            return aSimSeries


class SimSeries(Series):
    """
    A Series object designed to store data with units.

    Parameters
    ----------
    data : array-like, dict, scalar value
        The data to store in the SimSeries.
    index : array-like or Index
        The index for the SimSeries.
    units : string or dictionary of units(optional)
        Can be any string, but only units acepted by the UnitConverter will
        be considered when doing arithmetic calculations with other SimSeries
        or SimDataFrames.

    kwargs
        Additional arguments passed to the Series constructor,
         e.g. ``name``.

    See Also
    --------
    SimDataFrame
    pandas.Series

    """
    _metadata = ["units", "speak", 'indexUnits', 'nameSeparator', 'intersectionCharacter', 'autoAppend', 'spdLocator', 'operatePerName']  #, 'spdiLocator']