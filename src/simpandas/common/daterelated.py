# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.2'
__release__ = 20220919

import datetime as dt
from pandas import Timestamp, DatetimeIndex, Series, to_datetime
import numpy as np
from ..classes.series import SimSeries


def daysInYear(year):
    """
    returns the number of days in a particular year

    Parameters
    ----------
    year : int, date, datetime or array-like of int, date, or datetime
        The year to calculate the number of days.
        Can a single year, represented as an integer or as date or datetime object
        Also, list or array of year is accepted.

    Returns
    -------
    int or array of ints, according to the input
    """
    if type(year) in (int,float):
        return dt.date(int(year), 12, 31).timetuple().tm_yday
    if type(year) in (dt.date, dt.datetime):
        return dt.date(year.timetuple().tm_year, 12, 31).timetuple().tm_yday
    if type(year) is Timestamp:
        return dt.date(year.year,12,31).timetuple().tm_yday

    if type(year) in (list, tuple, np.ndarray):
        if np.array(year).dtype in ('int','int64','float','float64'):
            return np.array([ dt.date(int(Y), 12, 31).timetuple().tm_yday for Y in year ], dtype=int)
        elif 'datetime' in str(np.array(year).dtype):
            return np.array([ dt.date(Y.astype(object).timetuple().tm_year, 12, 31).timetuple().tm_yday for Y in year ], dtype=int)
        elif len(set(map(type,year))) == 1 and list(set(map(type,year)))[0] in (dt.date, dt.datetime):
            return np.array([ dt.date(Y.timetuple().tm_year, 12, 31).timetuple().tm_yday for Y in year ], dtype=int)
        elif len(set(map(type,year))) == 2 and list(set(map(type,year)))[0] in (dt.date, dt.datetime) and list(set(map(type,year)))[1] in (dt.date, dt.datetime):
            return np.array([ dt.date(Y.timetuple().tm_year, 12, 31).timetuple().tm_yday for Y in year ], dtype=int)
    if isinstance(year,DatetimeIndex):
        return np.array([ dt.date(Y.year, 12, 31).timetuple().tm_yday for Y in year ], dtype=int)

    if isinstance(year,SimSeries):
        params = year._SimParameters
        params['name'] = 'DaysInYear'
        params['units'] = 'days'
        return SimSeries(data=np.array([ dt.date(Y.year, 12, 31).timetuple().tm_yday for Y in year ], dtype=int), index=year.index, **params)

    if isinstance(year, Series):
        return Series(data=np.array([dt.date(Y.year, 12, 31).timetuple().tm_yday for Y in year], dtype=int), index=year.index)

    raise ValueError("input 'year' is not a valid date or year integer")

def daysInMonth(month, year=None):
    """
    returns the number of days in a particular month of particular year

    Parameters
    ----------
    month : str, int, date, datetime or array-like of int, date, or datetime
        The month to calculate the number of days.
        Can a single month, represented as an integer or as date or datetime object
        Also, list or array of months is accepted.
    year : integer, optional
        If 'month' is provided as integer, year can be used to specify the year
        when to calculate the number of days in the month.
        This is only useful for February

    Returns
    -------
    int or array of ints, according to the input
    """
    daysinmonths = {1:31,
                    2:28,
                    3:31,
                    4:30,
                    5:31,
                    6:30,
                    7:31,
                    8:31,
                    9:30,
                    10:31,
                    11:30,
                    12:31}
    monthsnames = {'JAN':1,
                   'ENE':1,
                   'GEN':1,
                   'FEB':2,
                   'MAR':3,
                   'APR':4,
                   'ABR':4,
                   'MAY':5,
                   'JUN':6,
                   'GIU':6,
                   'JUL':7,
                   'JLY':7,
                   'LUG':7,
                   'AUG':8,
                   'AGO':8,
                   'SEP':9,
                   'SET':9,
                   'OCT':10,
                   'OTT':10,
                   'NOV':11,
                   'DEC':12,
                   'DIC':12,
                   }
    if type(month) is str:
        if month.upper() in monthsnames:
            month = monthsnames[month.upper()]
        elif month.isdigit():
            return daysInMonth(int(month), year)
        elif year is None:
            try:
                month = to_datetime(month)
                return daysInMonth(month.month,month.year)
            except:
                raise ValueError("input 'month' not recognized.")
        else:
            raise ValueError("input 'month' not recognized.")

    if type(month) in (int, float):
        if year is None:
            return daysinmonths[int(month)]
        if type(year) is not int:
            raise ValueError("input 'year' is not a valid year integer")
        if dt.date(int(year), 12, 31).timetuple().tm_yday == 366 and month == 2:
            return 29
        else:
            return daysinmonths[int(month)]

    if type(month) in (dt.date, dt.datetime):
        return daysInMonth(month.timetuple().tm_mon, month.timetuple().tm_year)

    if type(month) is Timestamp:
        return daysInMonth(month.month, month.year)

    if isinstance(month,DatetimeIndex):
        return np.array([ daysInMonth(M.month, M.year) for M in month ], dtype=int)

    if type(month) in (list, tuple):
        month = np.array(month)

    if str(month.dtype).startswith('date'):
        return np.array([ daysInMonth(M.month, M.year) for M in to_datetime(month) ], dtype=int)
    if str(month.dtype) in ('int','int64','float','float64'):
        if len(month.shape) == 1:
            return np.array([ daysInMonth(M) for M in month ], dtype=int)
        elif month.shape[1] == 2:
            return np.array([ daysInMonth(M[0], M[1]) for M in month ], dtype=int)

    # if type(month) is np.ndarray:
    #     if np.array(month).dtype in ('int','int64','float','float64'):
    #         return np.array([ daysInMonth(M,year) for M in month ], dtype=int)
    #     elif 'datetime' in str(np.array(year).dtype):
    #         return np.array([ M.astype(object).timetuple().tm_mon for M in month ], dtype=int)
    #     elif len(set(map(type,month))) == 1 and list(set(map(type,month)))[0] in (dt.date, dt.datetime):
    #         return np.array([ M.timetuple().tm_mon for M in month ], dtype=int)
    #     elif len(set(map(type,month))) == 2 and list(set(map(type,month)))[0] in (dt.date, dt.datetime) and list(set(map(type,month)))[1] in (dt.date, dt.datetime):
    #         return np.array([ M.timetuple().tm_mon for M in month ], dtype=int)

    if isinstance(month, SimSeries):
        params = month._SimParameters
        params['name'] = 'DaysInMonth'
        params['units'] = 'days'
        return SimSeries(data=np.array([ daysInMonth(M.month) for M in month ], dtype=int), index=month.index, **params)

    if isinstance(month, Series):
        return Series(data=np.array([ M.month for M in month ], dtype=int), index=month.index)

    raise ValueError("input 'month' is not a valid date or month integer")

def realYear(date):
    """
    returns a float corresponding for the year and the fraction of year represented by the date.

    Parameters
    ----------
    date : date, datetime, or array of date objects

    Returns
    -------
    float
    """
    if type(date) in (dt.date, dt.datetime):
        return date.timetuple().tm_year + (date.timetuple().tm_yday -1) / dt.date(date.timetuple().tm_year, 12, 31).timetuple().tm_yday
    if type(date) is Timestamp:
        return date.year + (dt.date(date.year,date.month,date.day).timetuple().tm_yday -1) / dt.date(date.year, 12, 31).timetuple().tm_yday

    if type(date) is np.ndarray and 'datetime' in str(np.array(date).dtype):
            return np.array([Y.year + (dt.date(Y.year, Y.month, Y.day).timetuple().tm_yday -1) / dt.date(Y.year, 12, 31).timetuple().tm_yday for Y in to_datetime(date)], dtype=float)
    if type(date) in (list, tuple):
        if len(set(map(type, date))) == 1 and list(set(map(type,date)))[0] in (dt.date, dt.datetime):
            return np.array([Y.timetuple().tm_year + (Y.timetuple().tm_yday -1) / dt.date(Y.timetuple().tm_year, 12, 31).timetuple().tm_yday for Y in date], dtype=float)
        elif len(set(map(type,date))) == 2 and list(set(map(type,date)))[0] in (dt.date, dt.datetime) and list(set(map(type,date)))[1] in (dt.date, dt.datetime):
            return np.array([Y.timetuple().tm_year + (Y.timetuple().tm_yday -1) / dt.date(Y.timetuple().tm_year, 12, 31).timetuple().tm_yday for Y in date], dtype=float)
    if isinstance(date,DatetimeIndex):
        return np.array([ Y.year + (dt.date(Y.year,Y.month,Y.day).timetuple().tm_yday -1) / dt.date(Y.year, 12, 31).timetuple().tm_yday for Y in date], dtype=float)

    if isinstance(date,SimSeries):
        params = date._SimParameters
        params['name'] = 'Year'
        params['units'] = 'year'
        return SimSeries(data=realYear(date.to_Pandas()), **params)

    if isinstance(date,Series):
        return Series(data=np.array([Y.year + dt.date(Y.year, Y.month, Y.day).timetuple().tm_yday / dt.date(Y.year, 12, 31).timetuple().tm_yday for Y in date], dtype=float), index=date.index)