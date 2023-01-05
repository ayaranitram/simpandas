# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.9'
__release__ = 20221003
__all__ = ['SimBasics']

import fnmatch

import numpy as np
from simpandas.indexer import _SimLocIndexer
from simpandas.common.daterelated import days_in_year, real_year, days_in_month
from simpandas.common.math import znorm as _znorm, minmaxnorm as _minmaxnorm, jitter as _jitter
from warnings import warn


class SimBasics(object):
    """

    """

    def __init__(self):
        self.units = {}
        self.verbose = False
        self.index_units = None
        self.name_separator = ':'
        self.intersection_character = '∩'
        self.auto_append = False
        self.operate_per_name = False
        self.transposed = False
        self.spdLocator = None
        self.name = None

    @property
    def loc(self) -> _SimLocIndexer:
        """
        wrapper for .loc indexing
        """
        return self.spdLocator

    # @property
    # def iloc(self) -> _iSimLocIndexer:
    #     """
    #     wrapper for .iloc indexing
    #     """
    #     return self.spdiLocator

    def params_(self):
        return {'units': self.units.copy() if type(self.units) is dict else self.units,
                'name': self.name,
                'verbose': self.verbose if hasattr(self, 'verbose') else False,
                'index_name': self.index.name,
                'index_units': self.index_units if hasattr(self, 'index_units') else None,
                'name_separator': self.name_separator if hasattr(self, 'name_separator') else None,
                'intersection_character': self.intersection_character if hasattr(self,
                                                                                 'intersection_character') else '∩',
                'auto_append': self.auto_append if hasattr(self, 'auto_append') else False,
                'operate_per_name': self.operate_per_name if hasattr(self, 'operate_per_name') else False,
                'transposed': self.transposed if hasattr(self, 'transposed') else False,
                }

    def concat(self, objs, axis=0, join='outer', ignore_index=False,
               keys=None, levels=None, names=None, verify_integrity=False,
               sort=False, copy=True, squeeze=True):
        """
        wrapper of pandas.concat enhanced with units support

        Return:
            SimDataFrame
        """
        from .common.merger import concat as _concat
        if type(objs) not in [list, SimDataFrame, DataFrame, SimSeries, Series]:
            raise TypeError("objs must be a list of DataFrames or SimDataFrames")
        if len(objs) == 1:
            print("WARNING: only 1 DataFrame received.")
            return [objs][0]
        if type(objs) is not list:
            objs = [objs]
        return _concat([self] + objs, axis=axis, join=join,
                       ignore_index=ignore_index, keys=keys, levels=levels,
                       names=names, verify_integrity=verify_integrity,
                       sort=sort, copy=copy, squeeze=squeeze)

    @property
    def _SimParameters(self):
        return self.params_

    def describe(self, *args, **kwargs):
        return self._class(data=self.to_Pandas().describe(*args, **kwargs),
                           **self.params_)

    def head(self, n=5):
        """
        Return the first n rows.

        This function returns first n rows from the object based on position. It is useful for quickly verifying data, for example, after sorting or appending rows.

        For negative values of n, this function returns all rows except the last n rows, equivalent to df[n:].

        Parameters:
        ----------
            n : int, default 5
            Number of rows to select.

        Returns
        -------
            type of caller
            The first n rows of the caller object.
        """
        return self._class(data=self.to_pandas().head(n), **self.params_)

    def tail(self, n=5):
        """
        Return the last n rows.

        This function returns last n rows from the object based on position. It is useful for quickly verifying data, for example, after sorting or appending rows.

        For negative values of n, this function returns all rows except the first n rows, equivalent to df[n:].

        Parameters:
        ----------
            n : int, default 5
            Number of rows to select.

        Returns
        -------
            type of caller
            The last n rows of the caller object.
        """
        return self._class(data=self.to_pandas().tail(n), **self.params_)

    def cumsum(self, skipna=True, *args, **kwargs):
        """
        Return cumulative sum over a SimDataFrame.

        Returns a SimDataFrame or SimSeries of the same size containing the cumulative sum.

        Parameters:
            axis : {0 or ‘index’, 1 or ‘columns’}, default 0
                The index or the name of the axis. 0 is equivalent to None or ‘index’.

        skipna: bool, default True
            Exclude NA/null values. If an entire row/column is NA, the result will be NA.

        *args, **kwargs
            Additional keywords have no effect but might be accepted for compatibility with NumPy.

        Returns
            SimSeries or SimDataFrame
            Return cumulative sum of Series or DataFrame.
        """
        return self._class(data=self.as_Pandas().cumsum(skipna=skipna, *args, **kwargs), **self.params_)

    def set_index_name(self, name):
        if type(name) is str and len(name.strip()) > 0:
            self.index.name = name.strip()

    def __contains__(self, item):
        if item in self.columns:
            return True
        elif item in self.index:
            return True
        else:
            return False

    def __neg__(self):
        return self._class(data=self.as_Pandas().__neg__(), **self.params_)

    def __int__(self):
        return self._class(data=self.as_Pandas().astype(int), **self.params_)

    def __abs__(self):
        return self._class(data=abs(self.as_Pandas()), **self.params_)

    def __radd__(self, other):
        return self.__add__(other)

    def __rsub__(self, other):
        return self.__neg__().__add__(other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __rtruediv__(self, other):
        return self.__pow__(-1).__mul__(other)

    def __rfloordiv__(self, other):
        return self.__pow__(-1).__mul__(other).__int__()

    def set_name_separator(self, separator):
        if type(separator) is str and len(separator) > 0:
            if separator in '=-+&*/!%':
                print(
                    "The separator '" + separator + "' could be confused with operators.\n it is recommended to use ':' as separator.")
            self.name_separator = separator
        else:
            raise TypeError("The `separator` must be a string.")

    def get_name_separator(self):
        if self.name_separator in [None, '', False]:
            warn(" NameSeparator is not defined.")
            return ''
        else:
            return self.name_separator

    def to_Pandas(self):
        return self.to_pandas()

    def toPandas(self):
        return self.to_pandas()

    def as_Pandas(self):
        return self.as_pandas()

    def asPandas(self):
        return self.as_pandas()

    def to_Series(self):
        return self.to_series()

    def toSeries(self):
        return self.to_series()

    def as_Series(self):
        return self.as_series()

    def asSeries(self):
        return self.as_series()

    def to_SimSeries(self):
        return self.to_simseries()

    def toSimSeries(self):
        return self.to_simseries()

    def as_SimSeries(self):
        return self.as_simseries()

    def asSimSeries(self):
        return self.as_simseries()

    def to_DataFrame(self):
        return self.to_dataframe()

    def toDataFrame(self):
        return self.to_dataframe()

    def as_DataFrame(self):
        return self.as_dataframe()

    def asDataFrame(self):
        return self.as_dataframe()

    def to_SimDataFrame(self):
        return self.to_simdataframe()

    def toSimDataFrame(self):
        return self.to_simdataframe()

    def as_SimDataFrame(self):
        return self.as_simdataframe()

    def asSimDataFrame(self):
        return self.as_simdataframe()

    @property
    def Series(self):
        return self.as_series()

    @property
    def s(self):
        return self.as_series()

    @property
    def S(self):
        return self.as_series()

    @property
    def DataFrame(self):
        return self.as_dataframe()

    @property
    def df(self):
        return self.as_dataframe()

    @property
    def DF(self):
        return self.as_dataframe()

    @property
    def SimDataFrame(self):
        return self.as_simdataframe()

    @property
    def sdf(self):
        return self.as_simdataframe()

    @property
    def SDF(self):
        return self.as_simdataframe()

    def squeeze(self, axis=None):
        """
        wrapper of pandas.squeeze

        SimSeries with a single element and no units (or unitless) are squeezed to a scalar.
        SimSeries without units or unitless are squeezed to a Series.
        SimDataFrame without units or unitless are squeezed to a DataFrame.
        SimDataFrame with a single row or column are squeezed to a SimSeries.
        SimDataFrame with a single row or column and without units or unitless are squeezed to a Series.
        SimDataFrame with a single element and no units (or unitless) are squeezed to a scalar.

        Parameters
        ----------
        axis : {0 or ‘index’, 1 or ‘columns’, None}, default None
            A specific axis to squeeze. By default, all length-1 axes are squeezed., optional

        Returns
        -------
        SimDataFrame, DataFrame, SimSeries, Series, or scalar
            The projection after squeezing axis or all the axes and units

        """
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        if self._class is SimDataFrame:
            if len(self.columns) == 1 or len(self.index) == 1:
                return self.to_simseries().squeeze()
            elif len(self.get_units()) == 0 or \
                    np.array([(u is None or str(u).lower().strip() in ['unitless', 'dimensionless']) for u in
                              self.get_units().values()]).all():
                return self.as_DataFrame()
            else:
                return self
        elif self._class is SimSeries:
            if len(self) == 1:
                if len(self.get_units()) == 0 or np.array(
                        [(u is None or str(u).lower().strip() in ['unitless', 'dimensionless']) for u in
                         self.get_units().values()]).all():
                    return self.iloc[0]
            elif len(self.get_units()) == 0 or np.array(
                    [(u is None or str(u).lower().strip() in ['unitless', 'dimensionless']) for u in
                     self.get_units().values()]).all():
                return self.as_Series()
            elif type(self.get_units()) is dict and len(set(self.get_units(self.index).values())) == 1:
                params_ = self.params_.copy()
                params_['units'] = list(set(self.get_units(self.index).values()))[0]
                return SimSeries(self.as_Series(), **params_)
            else:
                return self
        else:
            return self

    @property
    def T(self):
        return self.transpose()

    def rename_right(self, inplace=False):
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        if self.name_separator in [None, '', False]:
            return self
        objs = {each: None if each is None else each.split(self.name_separator)[-1] for each in self.columns}
        if self._class is SimDataFrame:
            if len(set(objs.keys())) != len(set(objs.values())):
                objs = dict(zip(objs.keys(), objs.keys()))
        elif self._class is SimSeries:
            if len(self.columns) == 1:
                objs = list(objs.values())[0]
        if inplace:
            self.rename(columns=objs, inplace=inplace)
        else:
            return self.rename(columns=objs, inplace=inplace)

    def rename_left(self, inplace=False):
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        if self.name_separator in [None, '', False]:
            return self
        objs = {each: None if each is None else each.split(self.name_separator)[0] for each in self.columns}
        if self._class is SimDataFrame:
            if len(set(objs.keys())) != len(set(objs.values())):
                objs = dict(zip(objs.keys(), objs.keys()))
        elif self._class is SimSeries:
            if len(self.columns) == 1:
                objs = list(objs.values())[0]
        if inplace:
            self.rename(columns=objs, inplace=inplace)
        else:
            return self.rename(columns=objs, inplace=inplace)

    def renameRight(self, inplace=False):
        return self.rename_right(inplace=inplace)

    def renameLeft(self, inplace=False):
        return self.rename_left(inplace=inplace)

    def shift(self, periods=1, freq=None, axis=0, fill_value=None):
        """
        wrapper for Pandas shift method

        Shift index by desired number of periods with an optional time freq.

        When freq is not passed, shift the index without realigning the data.
        If freq is passed (in this case, the index must be date or datetime,
        or it will raise a NotImplementedError), the index will be increased using the periods and the freq. freq can be inferred when specified as “infer” as long as either freq or inferred_freq attribute is set in the index.

        Parameters
periodsint
Number of periods to shift. Can be positive or negative.

freqDateOffset, tseries.offsets, timedelta, or str, optional
Offset to use from the tseries module or time rule (e.g. ‘EOM’). If freq is specified then the index values are shifted but the data is not realigned. That is, use freq if you would like to extend the index when shifting and preserve the original data. If freq is specified as “infer” then it will be inferred from the freq or inferred_freq attributes of the index. If neither of those attributes exist, a ValueError is thrown.

axis{0 or ‘index’, 1 or ‘columns’, None}, default None
Shift direction.

fill_valueobject, optional
The scalar value to use for newly introduced missing values. the default depends on the dtype of self. For numeric data, np.nan is used. For datetime, timedelta, or period data, etc. NaT is used. For extension dtypes, self.dtype.na_value is used.

Changed in version 1.1.0.

Returns
SimDataFrame
Copy of input object, shifted.

        """
        return self._class(data=self.as_Pandas().shift(periods=periods, freq=freq, axis=axis, fill_value=fill_value),
                           **self.params_)

    def to(self, units):
        """
        returns the dataframe converted to the requested units if possible, if not, returns the original values.
        """
        return self.convert(units)

    @property
    def index_name(self):
        return self.index.name

    @property
    def right(self):
        if self.name_separator is None or self.name_separator is False or self.name_separator in ['']:
            return list(self.columns)
        else:
            return list(set([None if each is None else each.split(self.name_separator)[-1] for each in self.columns]))

    @property
    def left(self):
        if self.name_separator is None or self.name_separator is False or self.name_separator in ['']:
            return list(self.columns)
        else:
            return list(set([None if each is None else each.split(self.name_separator)[0] for each in self.columns]))

    def get_wells(self, pattern=None):
        """
        Will return a tuple of all the well names in case.

        If the pattern variable is different from None only wells
        matching the pattern will be returned; the matching is based
        on fnmatch():
            Pattern     Meaning
            *           matches everything
            ?           matches any single character
            [seq]       matches any character in seq
            [!seq]      matches any character not in seq

        """
        if pattern is not None and type(pattern) is not str:
            raise TypeError('pattern argument must be a string.')
        if pattern is None:
            return tuple(self.wells)
        else:
            return tuple(fnmatch.filter(self.wells, pattern))

    def get_groups(self, pattern=None):
        """
        Will return a tuple of all the group names in case.

        If the pattern variable is different from None only groups
        matching the pattern will be returned; the matching is based
        on fnmatch():
            Pattern     Meaning
            *           matches everything
            ?           matches any single character
            [seq]       matches any character in seq
            [!seq]      matches any character not in seq

        """
        if pattern is not None and type(pattern) is not str:
            raise TypeError('pattern argument must be a string.')
        if pattern is None:
            return self.groups
        else:
            return tuple(fnmatch.filter(self.groups, pattern))

    def get_regions(self, pattern=None):
        """
        Will return a tuple of all the region names in case.

        If the pattern variable is different from None only regions
        matching the pattern will be returned; the matching is based
        on fnmatch():
            Pattern     Meaning
            *           matches everything
            ?           matches any single character
            [seq]       matches any character in seq
            [!seq]      matches any character not in seq
        """
        if pattern is not None and type(pattern) is not str:
            raise TypeError('pattern argument must be a string.')
        if pattern is None:
            return self.regions
        else:
            return tuple(fnmatch.filter(self.regions, pattern))

    def get_attributes(self, pattern=None):
        """
        Will return a dictionary of all the attributes names in case as keys
        and their related items as values.

        If the pattern variable is different from None only attributes
        matching the pattern will be returned; the matching is based
        on fnmatch():
            Pattern     Meaning
            *           matches everything
            ?           matches any single character
            [seq]       matches any character in seq
            [!seq]      matches any character not in seq
        """
        if pattern is None:
            return tuple(self.attributes.keys())
        else:
            return tuple(fnmatch.filter(tuple(self.attributes.keys()), pattern))

    def days_in_year(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an array of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        params_ = self.params_
        params_['index'] = self.index
        params_['name'] = 'days_in_year'
        if type(params_['units']) is dict:
            params_['units']['days_in_year'] = 'days'
        else:
            params_['units'] = 'days'
        if column is not None:
            if type(column) is str and column in self.columns:
                if self[column].dtype in ('int', 'int64') and self[column].min() > 0:
                    params_['name'] = 'days_in_year'
                    params_['units'] = 'days'
                    return SimSeries(data=days_in_year(self[column].to_numpy()), **params_)
                elif 'datetime' in str(self[column].dtype):
                    return days_in_year(self[column])
                else:
                    raise ValueError('selected column is not a valid date or year integer')
            elif type(column) is str and column not in self.columns:
                raise ValueError('the selected column is not in this SimDataFrame')
            elif type(column) is not str and hasattr(column, '__iter__'):
                result = SimDataFrame(data={}, index=self.index, **self.params_)
                for col in column:
                    if col in self.columns:
                        result[col] = days_in_year(self[col])
                        result.set_units('days', col)
                return result
        else:
            params_['name'] = 'days_in_year'
            params_['index'] = self.index
            params_['index_units'] = self.index_units
            params_['units'] = 'days'
            if self.index.dtype in ('int', 'int64') and self.index.min() > 0:
                return SimSeries(data=list(days_in_year(self.index.to_numpy())), **params_)
            elif 'datetime' in str(self.index.dtype):
                return SimSeries(data=list(days_in_year(self.index)), **params_)
            else:
                raise ValueError('index is not a valid date or year integer')

    def jitter(self, std=0.10):
        """
        add jitter the values of the SimSeries or SimDataFrame
        """
        return _jitter(self, std)

    def real_year(self, column=None):
        """
        returns a SimSeries with the year and cumulative days as fraction

        Parameters
        ----------
        column : str
            The selected column must be a datetime array.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        from simpandas.frame import SimDataFrame
        from simpandas.series import SimSeries
        params_ = self.params_
        params_['index'] = self.index
        params_['name'] = 'realYear'
        params_['units'] = 'Years'
        if column is not None:
            if type(column) is str and column in self.columns:
                if 'datetime' in str(self[column].dtype):
                    return SimSeries(data=real_year(self[column]), **params_)
                else:
                    raise ValueError('selected column is not a valid date format')
            elif type(column) is str and column not in self.columns:
                raise ValueError('the selected column is not in this SimDataFrame')
            elif type(column) is not str and hasattr(column, '__iter__'):
                result = SimDataFrame(data={}, index=self.index, **self.params_)
                for col in column:
                    if col in self.columns:
                        result[col] = real_year(self[col])
                return result
        else:
            if 'datetime' in str(self.index.dtype):
                return SimSeries(data=list(real_year(self.index)), **params_)
            else:
                raise ValueError('index is not a valid date or year integer')

    # function alias
    def daysInYear(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an array of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.days_in_year(column=column)

    def daysinyear(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an array of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.days_in_year(column=column)

    def DaysInYear(self, column=None):
        """
        returns a SimSeries with the number of days in a particular year

        Parameters
        ----------
        column : str
            The selected column must be an array of dtype integer, date, datetime containing
            the year to calculate the number of day.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.days_in_year(column=column)

    def realYear(self, column=None):
        """
        returns a SimSeries with the year and cumulative days as fraction

        Parameters
        ----------
        column : str
            The selected column must be a datetime array.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.real_year(column=column)

    def realyear(self, column=None):
        """
        returns a SimSeries with the year and cumulative days as fraction

        Parameters
        ----------
        column : str
            The selected column must be a datetime array.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.real_year(column=column)

    def RealYear(self, column=None):
        """
        returns a SimSeries with the year and cumulative days as fraction

        Parameters
        ----------
        column : str
            The selected column must be a datetime array.

        Returns
        -------
        a new SimSeries with the resulting array and same index as the input.
        """
        return self.real_year(column=column)

    def to_excel(self, excel_writer, split_by=None, sheet_name=None, na_rep='',
                 float_format=None, columns=None, header=True, units=True, index=True,
                 index_label=None, startrow=0, startcol=0, engine=None,
                 merge_cells=True, encoding=None, inf_rep='inf', verbose=True,
                 freeze_panes=None, sort=None):
        """
        Wrapper of .to_excel method from Pandas.
        On top of Pandas method this method is able to split the data into different
        sheets based on the column names. See parameters `split_by` and `sheet_name`.

        Write {klass} to an Excel sheet.
        To write a single {klass} to an Excel .xlsx file it is only necessary to
        specify a target file name. To write to multiple sheets it is necessary to
        create an `ExcelWriter` object with a target file name, and specify a sheet
        in the file to write to.
        Multiple sheets may be written to by specifying unique `sheet_name`.
        With all data written to the file it is necessary to save the changes.
        Note that creating an `ExcelWriter` object with a file name that already
        exists will result in the contents of the existing file being erased.

        Parameters
        ----------
        excel_writer : str or ExcelWriter object from Pandas.
            File path or existing ExcelWriter.
        split_by: None, positive or negative integer or str 'left', 'right' or 'first'. Default is None
            If is string 'left' or 'right', creates a sheet grouping the columns by
            the corresponding left:right part of the column name.
            If is string 'first', creates a sheet grouping the columns by
            the first character of the column name.
            If None, all the columns will go into the same sheet.
            if integer i > 0, creates a sheet grouping the columns by the 'i' firsts
            characters of the column name indicated by the integer.
            if integer i < 0, creates a sheet grouping the columns by the 'i' last
            the number characters of the column name indicated by the integer.
        sheet_name : None or str, default None
            Name of sheet which will contain DataFrame.
            If None:
                the `left` or `right` part of the name will be used if is unique,
                or 'FIELD', 'WELLS', 'GROUPS' or 'REGIONS' if all the column names
                start with 'F', 'W', 'G' or 'R'.
            else 'Sheet1' will be used.
        na_rep : str, default ''
            Missing data representation.
        float_format : str, optional
            Format string for floating point numbers. For example
            ``float_format="%.2f"`` will format 0.1234 to 0.12.
        columns : sequence or list of str, optional
            Columns to write.
        header : bool or list of str, default True
            Write out the column names. If a list of string is given it is
            assumed to be aliases for the column names.
        units : bool, default True
            Write the units of the column under the header name.
        index : bool, default True
            Write row names(index).
        index_label : str or sequence, optional
            Column label for index column(s) if desired. If not specified, and
            `header` and `index` are True, then the index names are used. A
            sequence should be given if the DataFrame uses MultiIndex.
        startrow : int, default 0
            Upper left cell row to dump data frame.
        startcol : int, default 0
            Upper left cell column to dump data frame.
        engine : str, optional
            Write engine to use, 'openpyxl' or 'xlsxwriter'. You can also set this
            via the options ``io.excel.xlsx.writer``, ``io.excel.xls.writer``, and
            ``io.excel.xlsm.writer``.
        merge_cells : bool, default True
            Write MultiIndex and Hierarchical Rows as merged cells.
        encoding : str, optional
            Encoding of the resulting excel file. Only necessary for xlwt,
            other writers support unicode natively.
        inf_rep : str, default 'inf'
            Representation for infinity(there is no native representation for
            infinity in Excel).
        verbose : bool, default True
            Display more information in the error logs.
        freeze_panes : tuple of int(length 2), optional
            Specifies the one-based bottommost row and rightmost column that
            is to be frozen.
        sort: None, bool or int
            if None, default behaviour depends on split_by parameter:
                if split_by is None will keep the current order of the columns in the SimDataFrame.
                if split_by is not None will sort alphabetically ascending the names of the columns.
            if True (bool) will sort the columns alphabetically ascending.
            if False (bool) will maintain the current order.
            if int > 0 will sort the columns alphabetically ascending.
            if int < 0 will sort the columns alphabetically descending.
            if int == 0 will keep the current order of the columns.

        """
        return self.to_SimDataFrame().to_excel(excel_writer,
                                               split_by=split_by,
                                               sheet_name=sheet_name,
                                               na_rep=na_rep,
                                               float_format=float_format,
                                               columns=columns,
                                               header=header,
                                               units=units,
                                               index=index,
                                               index_label=index_label,
                                               startrow=startrow,
                                               startcol=startcol,
                                               engine=engine,
                                               merge_cells=merge_cells,
                                               encoding=encoding,
                                               inf_rep=inf_rep,
                                               verbose=verbose,
                                               freeze_panes=freeze_panes,
                                               sort=sort)
