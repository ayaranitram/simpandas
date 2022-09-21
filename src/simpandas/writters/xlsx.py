# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 11:08:06 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.1.1'
__release__ = 20220921
__all__ = ['write_excel']

import fnmatch
import pandas as pd

def write_excel(sdf, excel_writer, split_by=None, sheet_name=None, na_rep='',
                float_format=None, columns=None, header=True, units=True, index=True,
                index_label=None, startrow=0, startcol=0, engine=None,
                merge_cells=True, encoding=None, inf_rep='inf', verbose=True,
                freeze_panes=None, sort=None):
    """
    Wrapper of .to_excel method from Pandas.
    On top of Pandas method this method is able to split the data into different
    sheets based on the column names. See paramenters `split_by´ and `sheet_name´.

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
    # if header is not requiered and sheet_name is str, directly pass it to Pandas
    if(not header and type(sheet_name) is str ) or(not units and type(sheet_name) is str ):
        sdf.DF.to_excel(excel_writer, sheet_name=sheet_name, na_rep=na_rep, float_format=float_format, columns=columns, header=False, index=index, index_label=index_label, startrow=startrow, startcol=startcol, engine=engine, merge_cells=merge_cells, encoding=encoding, inf_rep=inf_rep, verbose=verbose, freeze_panes=freeze_panes)

    # helper function
    firstChar = lambda s : str(s)[0]
    lastChar = lambda s : str(s)[-1]
    iChar = lambda s : lambda i : str(s)[:i] if i>0 else str(s)[i:]

    # define the columns to be exported
    if type(columns) is str:
        columns = [columns]
    if columns is None:
        cols = list(sdf.columns)
    else:
        cols = columns.copy()

    # validate split_by parameter
    if type(split_by) is not str and split_by is not None:
        raise ValueError(" `split_by´ parameter must be 'left', 'right', 'first' or None.")

    if type(split_by) is str:
        split_by = split_by.strip().lower()
    if split_by is not None and(len(split_by) == 0 or split_by == 'none' ):
        split_by = None

    # define the split and sheet(s) name(s)
    if split_by is None : # no split_by, use a single sheet
        if sheet_name is None : # generate the sheet name
            if len(sdf[cols].left) == 1:
                names = sdf[cols].left
            elif len(sdf[cols].right) == 1:
                names = sdf[cols].right
            elif len(set(map(firstChar, cols))) == 1:
                names = list(set(map(firstChar, cols)))[0]
                if names == 'F':
                    names =('FIELD', )
                elif names == 'W':
                    names =('WELLS', )
                elif names == 'G':
                    names =('GROUPS', )
                elif names == 'R':
                    names =('REGIONS', )
                elif names == 'C':
                    names =('CONNECTIONS', )
                else:
                    names =('Sheet1', )
            else:
                names =('Sheet1', )
        else: # use the provided sheet_name
            if type(sheet_name) is not str:
                raise TypeError("'sheet_name' must be a string.")
            if len(sheet_name) > 32 and verbose:
                print(" the sheet_name '"+sheet_name+"' is longer than 32 characters, \n will be but to the first 32 characters: '"+sheet_name[:32]+"'")
            names =(sheet_name[:32], )

    elif type(split_by) is str:
        if split_by == 'left':
            names = tuple(sorted(sdf[cols].left))
        elif split_by == 'right':
            names = tuple(sorted(sdf[cols].right))
        elif split_by == 'first':
            names = tuple(sorted(set(map(firstChar, cols))))
        elif split_by == 'last':
            names = tuple(sorted(set(map(lastChar, cols))))

    elif type(split_by) is int:
        if split_by == 0:
            raise ValueError(" integer `split_by´ parameter must be positive or negative, not zero.")
        else:
            names = tuple(sorted(set([iChar(c)(split_by) for c in cols] )))

    else:
        raise ValueError(" `split_by´ parameter must be 'left', 'right', 'first', 'last', an integer or None.")

    # initialize an instance of ExcelWriter or use the instance provided
    from pandas import ExcelWriter
    if isinstance(excel_writer, ExcelWriter):
        SDFwriter = excel_writer
    elif type(excel_writer) is str:
        if excel_writer.strip().lower().endswith('.xlsx'):
            pass # ok
        elif excel_writer.strip().lower().endswith('.xls'):
            if verbose:
                print(" the file")
        SDFwriter = ExcelWriter(excel_writer, engine='xlsxwriter')
    else:
        raise ValueError(" `excel_writer´ parameter must be a string path to an .xlsx file or an ExcelWriter instance.")

    headerRows = 2 if header is True else 0

    if index:
        if sdf.index.name is None:
            indexName =('', )
        if type(sdf.index) is pd.core.indexes.multi.MultiIndex:
            indexName = tuple(sdf.index.names)
        else:
            indexName =(sdf.index.name, )
        indexUnits = '' if sdf.indexUnits is None else sdf.indexUnits
        indexCols = len(sdf.index.names) if type(sdf.index) is pd.core.indexes.multi.MultiIndex else 1

    if freeze_panes is None:
        freeze_panes =(startrow+headerRows, startcol+(indexCols if index else 0))

    # if single name, simpy write the output using .to_excel method from Pandas
    for i in range(len(names)):

        # get the columns for this sheet
        if split_by is None:
            if sort is None:
                colselect = tuple(cols)
            elif int(sort) > 0:
                colselect = tuple(sorted(cols))
            elif int(sort) < 0:
                colselect = tuple(sorted(cols)[::-1])
            else:
                colselect = tuple(cols)

        elif split_by == 'left':
            if sort is None:
                colselect = tuple(sorted(fnmatch.filter(cols, names[i]+'*' )))
            elif int(sort) > 0:
                colselect = tuple(sorted(fnmatch.filter(cols, names[i]+'*' )))
            elif int(sort) < 0:
                colselect = tuple(sorted(fnmatch.filter(cols, names[i]+'*' ))[::-1])
            else:
                colselect = tuple(fnmatch.filter(cols, names[i]+'*' ))

        elif split_by == 'right':
            if sort is None:
                colselect = tuple(sorted(fnmatch.filter(cols, '*'+names[i] )))
            elif int(sort) > 0:
                colselect = tuple(sorted(fnmatch.filter(cols, '*'+names[i] )))
            elif int(sort) < 0:
                colselect = tuple(sorted(fnmatch.filter(cols, '*'+names[i] ))[::-1])
            else:
                colselect = tuple(fnmatch.filter(cols, '*'+names[i] ))

        elif split_by == 'first':
            if sort is None:
                colselect = tuple(sorted(fnmatch.filter(cols, names[i][0]+'*' )))
            elif int(sort) > 0:
                colselect = tuple(sorted(fnmatch.filter(cols, names[i][0]+'*' )))
            elif int(sort) < 0:
                colselect = tuple(sorted(fnmatch.filter(cols, names[i][0]+'*' ))[::-1])
            else:
                colselect = tuple(fnmatch.filter(cols, names[i][0]+'*' ))

        elif split_by == 'last':
            if sort is None:
                colselect = tuple(sorted(fnmatch.filter(cols, '*'+names[i][-1] )))
            elif int(sort) > 0:
                colselect = tuple(sorted(fnmatch.filter(cols, '*'+names[i][-1] )))
            elif int(sort) < 0:
                colselect = tuple(sorted(fnmatch.filter(cols, '*'+names[i][-1] ))[::-1])
            else:
                colselect = tuple(fnmatch.filter(cols, names[i][0]+'*' ))

        # write the sheet to the ExcelWriter
        sdf.DF.to_excel(SDFwriter, sheet_name=names[i], na_rep=na_rep, float_format=float_format, columns=colselect, header=False, index=index, index_label=index_label, startrow=startrow+headerRows, startcol=startcol, engine=engine, merge_cells=merge_cells, encoding=encoding, inf_rep=inf_rep, verbose=verbose, freeze_panes=freeze_panes)

        # Get the xlsxwriter workbook and worksheet objects.
        SDFworkbook  = SDFwriter.book
        SDFworksheet = SDFwriter.sheets[names[i]]

        if header:
            header_format = SDFworkbook.add_format({'bold': True, 'font_size':11})
            units_format = SDFworkbook.add_format({'italic': True})

            # add the index name and units to the header
            if index:
                colselect = indexName+colselect

            # write the column header, name and units
            for c in range(len(colselect)):
                colUnit = ''
                if colselect[c] in sdf.units:
                    colUnit = sdf.units[colselect[c]]
                SDFworksheet.write(startrow, startcol+c, colselect[c], header_format)
                SDFworksheet.write(startrow+1, startcol+c, colUnit, units_format)

    if isinstance(excel_writer, ExcelWriter):
        return SDFwriter
    elif type(excel_writer) is str:
        SDFwriter.save()