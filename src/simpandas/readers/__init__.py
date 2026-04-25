# -*- coding: utf-8 -*-
"""
Created on Wed Aug  3 20:24:36 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.1.5'
__release__ = 20260418

from simpandas.readers.xlsx import read_excel
from simpandas.readers.csv import read_csv
from simpandas.readers.json import read_json
from simpandas.readers.h5 import read_hdf5
from simpandas.readers.summary import read_summary
from simpandas.readers.vdb import read_vdb
from simpandas.readers.parquet import read_parquet
from simpandas.readers.prodml import read_prodml
from simpandas.readers.witsml import read_witsml
from simpandas.readers.resqml import read_resqml
from simpandas.readers.schedule import read_schedule


def read_auto(path, **kwargs):
    """
    Detect the file format from *path* and dispatch to the appropriate reader.

    Supported formats
    -----------------
    .xlsx, .xls, .xlsm, .xlsb  →  read_excel
    .csv, .tsv, .txt            →  read_csv
    .json                       →  read_json
    .h5, .hdf5, .he5            →  read_hdf5
    .smspec, .unsmry            →  read_summary
    .data                       →  read_schedule
    .vdb  (file or folder)      →  read_vdb
    .parquet                    →  read_parquet
    .xml (PRODML)               →  read_prodml  (default for .xml)
    .xml (WITSML, keyword)      →  read_witsml  (pass format='witsml')
    .epc                        →  read_resqml

    For ambiguous formats (e.g. ``.xml``) pass ``format='prodml'`` or
    ``format='witsml'`` to override the default dispatch.

    All extra keyword arguments are forwarded to the selected reader.

    Parameters
    ----------
    path : str or path-like
        Path to the file (or folder for VDB) to read.
    **kwargs
        Forwarded to the underlying reader.  Use ``format='witsml'`` or
        ``format='prodml'`` to disambiguate ``.xml`` files.

    Returns
    -------
    SimDataFrame

    Raises
    ------
    ValueError
        If the extension is not recognised and no ``format`` override is given.
    """
    import os

    fmt = kwargs.pop('format', None)

    path_str = str(path)
    _, ext = os.path.splitext(path_str)
    ext = ext.lower()

    # --- VDB: may be a directory with no extension or with .vdb extension ---
    if ext == '.vdb' or (not ext and os.path.isdir(path_str)):
        return read_vdb(path, **kwargs)

    # --- format override (useful for .xml disambiguation) ---
    if fmt is not None:
        fmt = fmt.lower()
        _fmt_map = {
            'excel': read_excel,
            'xlsx': read_excel,
            'xls': read_excel,
            'csv': read_csv,
            'json': read_json,
            'hdf5': read_hdf5,
            'h5': read_hdf5,
            'summary': read_summary,
            'smspec': read_summary,
            'unsmry': read_summary,
            'vdb': read_vdb,
            'parquet': read_parquet,
            'schedule': read_schedule,
            'data': read_schedule,
            'prodml': read_prodml,
            'witsml': read_witsml,
            'resqml': read_resqml,
            'epc': read_resqml,
        }
        if fmt not in _fmt_map:
            raise ValueError(
                f"Unknown format '{fmt}'. Valid values: {sorted(_fmt_map)}"
            )
        return _fmt_map[fmt](path, **kwargs)

    # --- extension-based dispatch ---
    _ext_map = {
        '.xlsx':  read_excel,
        '.xls':   read_excel,
        '.xlsm':  read_excel,
        '.xlsb':  read_excel,
        '.csv':   read_csv,
        '.tsv':   read_csv,
        '.txt':   read_csv,
        '.json':  read_json,
        '.h5':    read_hdf5,
        '.hdf5':  read_hdf5,
        '.he5':   read_hdf5,
        '.smspec': read_summary,
        '.unsmry': read_summary,
        '.parquet': read_parquet,
        '.data': read_schedule,
        '.xml':   read_prodml,   # default; override with format='witsml'
        '.epc':   read_resqml,
    }

    if ext not in _ext_map:
        raise ValueError(
            f"Cannot determine reader for extension '{ext}'. "
            "Pass format='<name>' to override, or use a specific reader directly."
        )

    return _ext_map[ext](path, **kwargs)
