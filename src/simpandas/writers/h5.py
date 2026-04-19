# -*- coding: utf-8 -*-
"""
HDF5 writer with units support for SimPandas.

Requires the ``h5py`` package (optional dependency).
"""

__version__ = '0.1.0'
__release__ = 20260418

__all__ = ['write_hdf5']


def write_hdf5(sdf, filepath, group='simpandas', compression='gzip'):
    """
    Write a SimDataFrame (or SimSeries) to an HDF5 file with units metadata.

    Layout inside the file::

        /<group>/
            data          float64[N, C]   – the numeric values
            columns       str[C]          – column names
            index         [N]             – index values
            units         str[C]          – per-column unit strings
            @index_units  str             – attribute with index unit
            @index_name   str             – attribute with index name

    Files produced by this function are read back with
    ``simpandas.read_hdf5(path)`` (or ``simpandas.readers.h5.read_hdf5``).

    Parameters
    ----------
    sdf : SimDataFrame or SimSeries
        The object to write.
    filepath : str or path-like
        Destination ``.h5`` file.  Overwrites if it exists.
    group : str, default ``'simpandas'``
        HDF5 group name to store the datasets under.
    compression : str or None, default ``'gzip'``
        Compression filter applied to the data dataset.

    Returns
    -------
    None
    """
    try:
        import h5py
    except ImportError:
        raise ImportError(
            "The h5py package is required for HDF5 support. "
            "Install it with:  pip install h5py"
        )

    import numpy as np
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

    # Gather metadata
    try:
        raw_units = sdf.units
        if isinstance(raw_units, dict):
            col_units = raw_units
        elif isinstance(raw_units, str) and hasattr(sdf, 'name') and sdf.name is not None:
            col_units = {sdf.name: raw_units}
        else:
            col_units = {}
    except Exception:
        col_units = {}

    index_units_val = getattr(sdf, 'index_units', None)
    index_name = df.index.name

    with h5py.File(filepath, 'w') as f:
        grp = f.create_group(group)

        # --- data -----------------------------------------------------------
        data_arr = df.values.astype(np.float64)
        grp.create_dataset('data', data=data_arr, compression=compression)

        # --- columns ---------------------------------------------------------
        col_bytes = np.array([str(c) for c in df.columns], dtype=h5py.string_dtype())
        grp.create_dataset('columns', data=col_bytes)

        # --- index -----------------------------------------------------------
        idx_vals = df.index.values
        if idx_vals.dtype.kind in ('U', 'S', 'O'):
            idx_ds = np.array([str(v) for v in idx_vals], dtype=h5py.string_dtype())
        else:
            idx_ds = idx_vals
        grp.create_dataset('index', data=idx_ds, compression=compression)

        # --- units -----------------------------------------------------------
        unit_strs = [str(col_units.get(c) or '') for c in df.columns]
        grp.create_dataset('units',
                           data=np.array(unit_strs, dtype=h5py.string_dtype()))

        # --- scalar attributes -----------------------------------------------
        if index_units_val:
            grp.attrs['index_units'] = str(index_units_val)
        if index_name is not None:
            grp.attrs['index_name'] = str(index_name)
