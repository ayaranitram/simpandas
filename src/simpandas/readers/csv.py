# -*- coding: utf-8 -*-
"""
CSV reader with units support for SimPandas.
"""

__version__ = '0.1.1'
__release__ = 20260503

from simpandas.frame import SimDataFrame

__all__ = ['read_csv']


def read_csv(filepath_or_buffer,
             units=None,
             indexUnits=None,
             nameSeparator=None,
             intersectionCharacter=None,
             autoAppend=False,
             operatePerName=False,
             verbose=False,
             *args, **kwargs):
    """
    Read a CSV file into a SimDataFrame, with optional units support.

    If ``units`` is an integer, that row number (0-based, after the header)
    is treated as a units row and extracted from the data.
    If ``units`` is a dict, it maps column names to unit strings.
    If ``units`` is None, no units are attached.

    Parameters
    ----------
    filepath_or_buffer : str, path object, or file-like
        Path to the CSV file.
    units : int, dict, or None
        If int, the row containing units (0-based after header).
        If dict, maps column names to unit strings.
        If None, no units.
    indexUnits : str or None
        Units for the index column.
    nameSeparator : str or None
        Separator for structured column names.
    intersectionCharacter : str or None
        Character used for name intersections.
    autoAppend : bool
        Whether to auto-append on assignment.
    operatePerName : bool
        Whether to operate per structured name.
    verbose : bool
        Whether to print info messages.
    *args, **kwargs
        Additional arguments passed to pandas.read_csv.

    Returns
    -------
    SimDataFrame
    """
    import pandas as pd

    if isinstance(units, int):
        # When units is an int we need all columns visible to extract the
        # units row, so we temporarily remove ``index_col`` from the kwargs
        # and re-apply it after extraction.
        index_col = kwargs.pop('index_col', None)

        # Read the file; the units row is at position `units` after the header
        df = pd.read_csv(filepath_or_buffer, *args, **kwargs)
        if units < len(df):
            units_row = df.iloc[units]
            units_dict = {}
            for col in df.columns:
                val = str(units_row[col]).strip() if pd.notna(units_row[col]) else None
                if val and val.lower() not in ('', 'nan', 'none', 'unitless'):
                    units_dict[col] = val
                else:
                    units_dict[col] = None
            df = df.drop(df.index[units]).reset_index(drop=True)
            # Try to convert numeric columns
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass

            # Re-apply index_col now that units have been extracted
            if index_col is not None:
                if isinstance(index_col, int):
                    idx_col_name = df.columns[index_col]
                else:
                    idx_col_name = index_col
                # Promote the column's unit to indexUnits when not set
                if indexUnits is None and idx_col_name in units_dict:
                    indexUnits = units_dict.pop(idx_col_name)
                elif idx_col_name in units_dict:
                    units_dict.pop(idx_col_name)
                df = df.set_index(idx_col_name)

            units = units_dict
        else:
            units = None
            # Still honour index_col even when no units row was found
            if index_col is not None:
                if isinstance(index_col, int):
                    df = df.set_index(df.columns[index_col])
                else:
                    df = df.set_index(index_col)
    else:
        df = pd.read_csv(filepath_or_buffer, *args, **kwargs)

    sim_kwargs = {}
    if units is not None:
        sim_kwargs['units'] = units
    if indexUnits is not None:
        sim_kwargs['index_units'] = indexUnits
    if nameSeparator is not None:
        sim_kwargs['name_separator'] = nameSeparator
    if intersectionCharacter is not None:
        sim_kwargs['intersection_character'] = intersectionCharacter
    sim_kwargs['auto_append'] = autoAppend
    sim_kwargs['operate_per_name'] = operatePerName
    sim_kwargs['verbose'] = verbose

    return SimDataFrame(data=df, **sim_kwargs)
