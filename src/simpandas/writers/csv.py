# -*- coding: utf-8 -*-
"""
CSV writer with units support for SimPandas.
"""

__version__ = '0.1.0'
__release__ = 20260418

__all__ = ['write_csv']


def write_csv(sdf, path_or_buf=None, units=True, index=True, **kwargs):
    """
    Write a SimDataFrame or SimSeries to CSV with an optional units row.

    When ``units=True`` (the default), column units are embedded as the
    first data row (row 0 after the header).  To read the file back::

        simpandas.read_csv(path, units=0)

    When ``index=True`` (the default), the DataFrame index is promoted
    to a regular column so that its units appear in the units row as
    well.  To restore the index on read-back pass ``index_col=0``::

        simpandas.read_csv(path, units=0, index_col=0)

    Parameters
    ----------
    sdf : SimDataFrame or SimSeries
        The object to write.
    path_or_buf : str, path object, or file-like, optional
        File path or object.  If ``None`` the CSV is returned as a string.
    units : bool, default True
        Whether to embed a units row in the output.
    index : bool, default True
        Whether to include the index as the first column(s).
    **kwargs
        Additional keyword arguments forwarded to
        ``pandas.DataFrame.to_csv``.

    Returns
    -------
    None or str
        ``None`` when writing to a file; the CSV string otherwise.
    """
    import pandas as pd

    # Normalise to a plain DataFrame
    if hasattr(sdf, 'as_dataframe'):
        df = sdf.as_dataframe()
    elif hasattr(sdf, 'as_pandas'):
        result = sdf.as_pandas()
        if isinstance(result, pd.Series):
            df = result.to_frame()
        else:
            df = result
    else:
        df = pd.DataFrame(sdf)

    # If units are not requested, delegate directly
    if not units:
        return df.to_csv(path_or_buf, index=index, **kwargs)

    # Gather column-level units
    col_units_list = None  # positional list (used when ColumnUnits detected)
    try:
        raw_units = sdf.units
        if isinstance(raw_units, dict):
            col_units = raw_units
        elif hasattr(raw_units, 'to_list'):  # ColumnUnits – preserve positional order
            col_units_list = raw_units.to_list()
            col_units = {}
        elif isinstance(raw_units, str) and hasattr(sdf, 'name') and sdf.name is not None:
            col_units = {sdf.name: raw_units}
        else:
            col_units = {}
    except Exception:
        col_units = {}

    # Gather index units
    index_units_val = getattr(sdf, 'index_units', None)

    # Nothing to embed → plain write
    if not col_units and not col_units_list and not index_units_val:
        return df.to_csv(path_or_buf, index=index, **kwargs)

    col_units = dict(col_units)  # defensive copy

    if index:
        # Promote the index to a regular column so its units
        # appear in the units row alongside data columns.
        idx_name = df.index.name
        df = df.reset_index()
        if col_units_list is None:
            if idx_name is not None and index_units_val:
                col_units[idx_name] = index_units_val
            elif idx_name is None and index_units_val:
                # reset_index() creates a column named 'index' when name is None
                generated = df.columns[0]
                col_units[generated] = index_units_val

    # Build the units row (one value per column, matching column order)
    if col_units_list is not None:
        idx_unit = str(index_units_val or '') if index else None
        unit_vals = ([idx_unit] if idx_unit is not None else []) + \
                    [str(u or '') for u in col_units_list]
    else:
        unit_vals = [str(col_units.get(c) or '') for c in df.columns]
    unit_row = pd.DataFrame([unit_vals], columns=df.columns)
    combined = pd.concat([unit_row, df], ignore_index=True)

    # Always write with index=False because the original index has already
    # been promoted to a column (when requested) or excluded.
    return combined.to_csv(path_or_buf, index=False, **kwargs)
