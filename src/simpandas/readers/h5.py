# -*- coding: utf-8 -*-
"""
HDF5 reader with units support for SimPandas.

Requires the ``h5py`` package (optional dependency).
"""

__version__ = '0.1.0'
__release__ = 20260418

from simpandas.frame import SimDataFrame

__all__ = ['read_hdf5']


def read_hdf5(filepath,
              group='simpandas',
              units=None,
              indexUnits=None,
              nameSeparator=None,
              intersectionCharacter=None,
              autoAppend=False,
              operatePerName=False,
              verbose=False):
    """
    Read an HDF5 file into a SimDataFrame with units support.

    Supports two layouts:

    1. **SimPandas layout** (default) – produced by ``SimDataFrame.to_hdf5()``.
       The file contains a group (default ``'simpandas'``) with:

       * ``data``   – a 2-D float dataset (rows × columns)
       * ``columns`` – a 1-D string dataset with column names
       * ``index``  – a 1-D dataset with the index values
       * ``units``  – a 1-D string dataset with per-column unit strings
       * ``index_units`` – scalar attribute on the group (optional)

    2. **Plain layout** – any HDF5 file where *group* contains a 2-D
       ``data`` dataset and optionally ``columns``/``index`` datasets.
       Units can be supplied via the *units* parameter.

    Parameters
    ----------
    filepath : str or path-like
        Path to the ``.h5`` file.
    group : str, default ``'simpandas'``
        HDF5 group that contains the datasets.
    units : dict or None
        Override / supply column → unit mapping.
    indexUnits : str or None
        Override / supply index units.
    nameSeparator, intersectionCharacter, autoAppend, operatePerName, verbose
        Forwarded to the ``SimDataFrame`` constructor.

    Returns
    -------
    SimDataFrame
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

    with h5py.File(filepath, 'r') as f:
        grp = f[group]

        # --- data -----------------------------------------------------------
        data = grp['data'][()]                       # numpy array

        # --- columns ---------------------------------------------------------
        if 'columns' in grp:
            columns = [c.decode() if isinstance(c, bytes) else str(c)
                       for c in grp['columns'][()]]
        else:
            columns = [f'col_{i}' for i in range(data.shape[1])]

        # --- index -----------------------------------------------------------
        if 'index' in grp:
            raw_idx = grp['index'][()]
            # Decode bytes coming from h5py
            if raw_idx.dtype.kind in ('S', 'O'):
                raw_idx = [v.decode() if isinstance(v, bytes) else str(v)
                           for v in raw_idx]
            index = pd.Index(raw_idx)
        else:
            index = None

        # --- index name ------------------------------------------------------
        index_name = None
        if 'index_name' in grp.attrs:
            index_name = grp.attrs['index_name']
            if isinstance(index_name, bytes):
                index_name = index_name.decode()

        # --- units -----------------------------------------------------------
        if units is None and 'units' in grp:
            raw_units = grp['units'][()]
            unit_list = [u.decode() if isinstance(u, bytes) else str(u)
                         for u in raw_units]
            units = {col: (u if u else None) for col, u in zip(columns, unit_list)}

        if indexUnits is None and 'index_units' in grp.attrs:
            iu = grp.attrs['index_units']
            if isinstance(iu, bytes):
                iu = iu.decode()
            if iu:
                indexUnits = iu

    df = pd.DataFrame(data, columns=columns, index=index)
    if index_name is not None:
        df.index.name = index_name

    # Attempt numeric conversion for every column
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass

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
