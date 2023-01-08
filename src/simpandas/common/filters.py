# -*- coding: utf-8 -*-
"""
Created on Sun Jan 08 11:10:15 2023

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.81.0'
__release__ = 20230108
__all__ = ['zeros']


def zeros(series_or_frame, axis=None, value=0):
    """
    Finds the columns or rows where all its values are equal to `value` (by default is 0).
    Returns a Series with bool indicating True at the columns or rows that match the condition.

    Parameters
    ----------
    axis = int or str
        0 for rows,
        1 for columns

    Returns
    -------
        Series
    """
    if axis is None:
        if hasattr(series_or_frame, 'columns'):
            axis = 1 if axis is None and len(series_or_frame.columns) == 1 else 0
        else:
            axis = 1
    axis = _clean_axis(axis)
    if axis == 2:
        return zeros(axis=0, value=value) + zero(axis=1, value=value)
    if hasattr(series_or_frame, 'columns'):
        limit = len(series_or_frame) if axis == 0 else len(series_or_frame.columns)
    else:
        limit = len(series_or_frame)
    return (series_or_frame == value).sum(axis=axis) == limit


def key_to_string(filter_str, key, pandas_agg):
    if len(key) > 0:
        # catch particular operations performed by Pandas
        found_so, found_no = '', ''
        if key in special_operation:
            if filter_str[-1] == ' ':
                filter_str = filter_str.rstrip()
            filter_str += key + '()'
        else:
            for SO in special_operation:
                if key.strip().endswith(SO):
                    key = key[:-len(SO)]
                    found_so = (SO if SO != '.null' else '.isnull') + '()'
                    break
        # catch particular operations performed by Numpy
        if key in numpy_operation:
            raise ValueError("wrong syntax for '" + key + "(blank space before) in:\n   " + conditions)
        else:
            for no in numpy_operation:
                if key.strip().endswith(no):
                    key = key[:-len(no)]
                    no = '.log' if no == '.ln' else no
                    filter_str += 'np' + no + '('
                    found_no = ' )'
                    break
        # catch aggregation operations performed by Pandas
        if key in pandas_aggregation:
            pandas_agg = key + '(axis=1)'
        else:
            for pa in pandas_aggregation:
                if key.strip().endswith(pa):
                    pandas_agg = pa + '(axis=1)'
                    break
        # if key is the index
        if key in ['.i', '.index']:
            filter_str = filter_str.rstrip()
            filter_str += ' self.as_pandas().index'
        # if key is a column
        elif key in self.columns:
            filter_str = filter_str.rstrip()
            filter_str += " self.as_pandas()['" + key + "']"
        # key might be a wellname, attribute or a pattern
        elif len(self.find_Keys(key)) == 1:
            filter_str = filter_str.rstrip()
            filter_str += " self.as_pandas()['" + self.find_Keys(key)[0] + "']"
        elif len(self.find_Keys(key)) > 1:
            filter_str = filter_str.rstrip()
            filter_str += " self.as_pandas()[" + str(list(self.find_Keys(key))) + "]"
            pandas_agg = '.any(axis=1)'
        else:
            filter_str += ' ' + key
        filter_str = filter_str.rstrip()
        filter_str += found_so + found_no
        key = ''
    return filter_str, key, pandas_agg
