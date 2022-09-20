# -*- coding: utf-8 -*-
"""
Created on Wed Aug  3 20:24:36 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.1.1'
__release__ = 20220919

from ..classes.frame import SimDataFrame

__all__ = ['read_excel']


def read_excel(io, sheet_name=None, header=0, names=None, index_col=None, usecols=None, squeeze=None, dtype=None, engine=None, converters=None, true_values=None, false_values=None, skiprows=None, nrows=None, na_values=None, keep_default_na=True, na_filter=True, verbose=False, parse_dates=False, date_parser=None, thousands=None, decimal='.', comment=None, skipfooter=0, convert_float=None, mangle_dupe_cols=True, storage_options=None,
units=1, speak=False, indexName=None, indexUnits=None, nameSeparator=None, intersectionCharacter='∩', autoAppend=False, transposed=False, operatePerName=False, *args, **kwargs):
    """
    wrapper of pandas.read_excel enhanced with units support

    Return:
        SimDataFrame
    """
    import pandas

    dateunits = ['date']  #,'fecha']
    speak = bool(speak)

    if type(units) is int:
        if units < 0:
            raise ValueError("'units' parameter must be positive")
        if type(header) is int:
            if header == units:
                if speak:
                    print(" > same row will be used as header and as units.")
            else:
                header = [header, units]
        elif type(header) is list:
            if len(header) == 1 and units in header:
                if speak:
                    print(" > same row will be used as header and as units.")
                header = header[0]
            else:
                header += [units]

    excelread = pandas.read_excel(io, sheet_name=sheet_name, header=header, names=names, index_col=index_col, usecols=usecols, squeeze=False, dtype=dtype, engine=engine, converters=converters, true_values=true_values, false_values=false_values, skiprows=skiprows, nrows=nrows, na_values=na_values, keep_default_na=keep_default_na, na_filter=na_filter, verbose=verbose, parse_dates=parse_dates, date_parser=date_parser, thousands=thousands, comment=comment, skipfooter=skipfooter, mangle_dupe_cols=mangle_dupe_cols, storage_options=storage_options)  # convert_float=convert_float, decimal=decimal

    if type(excelread) is not dict:
        excelread = {'onesheet':excelread}

    output = {}
    for name,df in excelread.items():

        if type(units) is list:
            if len(units) == len(df.columns):
                dataunits = {df.columns[i]:units[i] for i in len(units)}
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
            if str(indexUnits).lowrt().strip() not in dateunits:
                indexUnits = 'date'

        output[name] = SimDataFrame(data=df, units=dataunits, speak=speak, indexName=indexName, indexUnits=indexUnits, nameSeparator=nameSeparator, intersectionCharacter=intersectionCharacter, autoAppend=autoAppend, transposed=transposed, operatePerName=operatePerName, *args, **kwargs)

        if bool(squeeze):
            output[name] = output[name].squeeze()

    if len(output) == 1:
        return output[name]
    else:
        return output