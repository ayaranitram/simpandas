# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.2'
__release__ = 20220919
__all__ = ['clean_axis', 'stringNewName', 'typeOfFrame']


def clean_axis(axis=None):
    if axis is None:
        return 0
    if type(axis) is str and axis.lower() in ['row', 'rows', 'ind', 'index']:
        return 0
    if type(axis) is str and axis.lower() in ['col', 'cols', 'column', 'columns']:
        return 1
    if type(axis) is bool:
        return int(axis)
    if type(axis) is float:
        return int(axis)
    return axis


def stringNewName(newName):
    if len(newName) == 1:
        return list(newName.values())[0]
    else:
        return '∩'.join(map(str,set(newName.values())))


def typeOfFrame(frame):
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