# -*- coding: utf-8 -*-
"""
Created on Wed Aug  3 20:24:36 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.1.6'
__release__ = 20260503

from simpandas.frame import SimDataFrame
from simpandas.common.compat import PANDAS_GE_20

__all__ = ['read_excel']


def read_excel(io,
               sheet_name=None,
               header=0,
               names=None,
               index_col=None,
               usecols=None,
               dtype=None,
               engine=None,
               converters=None,
               true_values=None,
               false_values=None,
               skiprows=None,
               nrows=None,
               na_values=None,
               keep_default_na=True,
               na_filter=True,
               verbose=False,
               parse_dates=False,
               date_format=None,
               thousands=None,
               decimal='.',
               comment=None,
               skipfooter=0,
               convert_float=None,
               mangle_dupe_cols=True,
               storage_options=None,
               units=1,
               indexName=None,
               indexUnits=None,
               nameSeparator=None,
               intersectionCharacter='∩',
               autoAppend=False,
               transposed=False,
               operatePerName=False,
               squeeze=None,
               *args, **kwargs):
    """
    Wrapper of pandas.read_excel enhanced with units support.

    All standard pandas.read_excel parameters are accepted.  The additional
    simpandas-specific parameters below control how the resulting
    SimDataFrame is constructed.

    Parameters (simpandas extensions)
    ----------------------------------
    units : int, list, str, dict or None, default 1
        Specifies the column units.
        - ``int``: row index (0-based) in the Excel sheet that contains unit
          labels.  That row is extracted as units and dropped from the data.
          ``1`` means the second row (immediately below the header) is the
          units row.
        - ``list``: one unit string per column, in column order.
        - ``str``: a single unit string applied to every column.
        - ``dict``: a mapping of ``{column_name: unit}``.
        - ``None``: no units metadata is attached.
    indexName : str or None, default None
        Name to assign to the resulting index.
    indexUnits : str or None, default None
        Units of the index (e.g. ``'date'`` or ``'days'``).
    nameSeparator : str or None, default None
        Separator used to split column names into *attribute* and *item*
        parts (e.g. ``':'`` gives ``'WOPR:WELL-1'`` → attribute ``'WOPR'``,
        item ``'WELL-1'``).  When ``None`` the SimDataFrame default is used.
    intersectionCharacter : str, default ``'∩'``
        Character used to join column names when two SimDataFrames are
        combined (intersected).  This is the ``intersection_character``
        parameter of SimDataFrame.  The default for ``read_excel`` is
        ``'∩'``; the SimDataFrame constructor default is ``'&'``.
    autoAppend : bool, default False
        When ``True``, new columns are automatically appended to the
        existing units registry during assignment operations.
    transposed : bool, default False
        When ``True``, the data are treated as transposed (rows are
        attributes, columns are time-steps).
    operatePerName : bool, default False
        When ``True``, arithmetic operations are applied per-name group
        rather than element-wise across the whole frame.
    squeeze : bool or None, default None
        Deprecated.  If truthy, a single-column result is squeezed to a
        SimSeries.  Ignored when ``None`` or ``False``.

    Returns
    -------
    SimDataFrame or dict of SimDataFrame
        A single SimDataFrame when the file contains one sheet, or a dict
        keyed by sheet name when multiple sheets are read.
    """
    import pandas

    dateunits = ['date']  #,'fecha']
    verbose = bool(verbose)

    if type(units) is int:
        if units < 0:
            raise ValueError("'units' parameter must be positive")
        if type(header) is int:
            if header == units:
                if verbose:
                    print(" > same row will be used as header and as units.")
            else:
                header = [header, units]
        elif type(header) is list:
            if len(header) == 1 and units in header:
                if verbose:
                    print(" > same row will be used as header and as units.")
                header = header[0]
            else:
                header += [units]

    excelread_kwargs = dict(
        sheet_name=sheet_name, header=header, names=names, index_col=index_col,
        usecols=usecols, dtype=dtype, engine=engine, converters=converters,
        true_values=true_values, false_values=false_values, skiprows=skiprows, nrows=nrows,
        na_values=na_values, keep_default_na=keep_default_na, na_filter=na_filter,
        verbose=verbose, parse_dates=parse_dates, thousands=thousands,
        comment=comment, skipfooter=skipfooter, storage_options=storage_options,
    )
    if PANDAS_GE_20:
        excelread_kwargs['date_format'] = date_format
    else:
        # pandas < 2.0 uses date_parser; ignore date_format silently
        pass

    excelread = pandas.read_excel(io, **excelread_kwargs)

    if type(excelread) is not dict:
        excelread = {'onesheet':excelread}

    output = {}
    for name,df in excelread.items():

        if type(units) is list:
            if len(units) == len(df.columns):
                dataunits = {df.columns[i]:units[i] for i in range(len(units))}
            else:
                raise ValueError("if 'units' is a list, it must be same length as the columns of the dataframe")
        elif type(units) is str:
            dataunits = units
        elif type(units) is int:
            if type(header) is list:
                if len(header) == 2:
                    dataunits = {}
                    newcols = []
                    for col in df.columns:
                        if str(col[-1]).startswith('Unnamed:'):
                            nc = str(col[0]).strip()
                            dataunits[nc] = 'unitless'
                            newcols.append(nc)
                        else:
                            nc = str(col[0]).strip()
                            dataunits[nc] = str(col[-1]).strip()
                            newcols.append(nc)
                elif len(header) > 2:
                    dataunits = {}
                    newcols = []
                    for col in df.columns:
                        if str(col[-1]).startswith('Unnamed:'):
                            nc = col[:-1]
                            dataunits[nc] = 'unitless'
                            newcols.append(nc)
                        else:
                            nc = col[:-1]
                            dataunits[nc] = str(col[-1]).strip()
                            newcols.append(nc)
                    newcols = pandas.MultiIndex.from_tuples(newcols)
                df.columns = newcols
            elif type(header) is int:
                dataunits = {c:str(c) for c in df.columns}

        elif units is None:
            dataunits = None
        else:
            dataunits = units

        if isinstance(df,pandas.DataFrame):
            for colN in range(len(df.columns)):
                if str(df.iloc[:,colN].dtype).startswith('date'):
                    col = df.columns[colN]
                    if type(dataunits) is not dict:
                        dataunits = {c:dataunits for c in df.columns}
                    if col in dataunits:
                        if str(dataunits[col]).lower().strip() not in dateunits:
                            dataunits[col] = 'date'
                    else:
                        dataunits[col] = 'date'
        elif isinstance(df,pandas.Series):
            if str(df.dtype).startswith('date'):
                if df.name is not None:
                    dataunits = {df.name:'date'}
        if str(df.index.dtype).startswith('date'):
            if str(indexUnits).lower().strip() not in dateunits:
                indexUnits = 'date'

        output[name] = SimDataFrame(data=df,
                                    units=dataunits,
                                    verbose=verbose,
                                    index_name=indexName,
                                    index_units=indexUnits,
                                    name_separator=nameSeparator,
                                    intersection_character=intersectionCharacter,
                                    auto_append=autoAppend,
                                    transposed=transposed,
                                    operate_per_name=operatePerName,
                                    *args, **kwargs)

        if bool(squeeze) and isinstance(output[name], SimDataFrame):
            squeezed = output[name].squeeze()
            if not isinstance(squeezed, SimDataFrame):
                output[name] = squeezed

    if len(output) == 1:
        return output[name]
    else:
        return output