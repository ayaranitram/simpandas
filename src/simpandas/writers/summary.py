# -*- coding: utf-8 -*-
"""
Eclipse binary summary writer (.SMSPEC + .UNSMRY).

Writes a SimDataFrame into the pair of binary files that reservoir
simulators (Eclipse, OPM Flow, etc.) consume.

No external dependencies beyond NumPy and pandas.
"""

__version__ = '0.1.0'
__release__ = 20260418

__all__ = ['write_summary']

import struct
import numpy as np


# ---------------------------------------------------------------------------
# Low-level binary helpers
# ---------------------------------------------------------------------------

def _write_record(fh, payload: bytes):
    """Write one Fortran unformatted record (head-marker, payload, tail-marker)."""
    n = len(payload)
    marker = struct.pack('>i', n)
    fh.write(marker)
    fh.write(payload)
    fh.write(marker)


def _write_keyword(fh, keyword: str, dtype_tag: bytes, data):
    """Write a full Eclipse keyword block (header + data sub-records).

    Parameters
    ----------
    keyword : str  (max 8 chars, will be space-padded)
    dtype_tag : bytes  (b'INTE', b'REAL', b'DOUB', b'CHAR', b'LOGI', b'MESS')
    data : list  (Python ints, floats, or strings depending on dtype_tag)
    """
    count = len(data)

    # --- header record ---------------------------------------------------
    kw_bytes = keyword.encode('ascii').ljust(8)[:8]
    header = kw_bytes + struct.pack('>i', count) + dtype_tag
    _write_record(fh, header)

    if count == 0:
        return

    # --- data sub-records ------------------------------------------------
    max_items = {
        b'INTE': 1000,
        b'REAL': 1000,
        b'DOUB': 1000,
        b'CHAR': 105,
        b'LOGI': 1000,
    }.get(dtype_tag, 1000)

    offset = 0
    while offset < count:
        chunk = data[offset:offset + max_items]
        if dtype_tag == b'CHAR':
            buf = b''.join(s.encode('ascii', errors='replace').ljust(8)[:8]
                           for s in chunk)
        elif dtype_tag == b'INTE':
            buf = struct.pack(f'>{len(chunk)}i', *[int(x) for x in chunk])
        elif dtype_tag == b'REAL':
            buf = struct.pack(f'>{len(chunk)}f', *[float(x) for x in chunk])
        elif dtype_tag == b'DOUB':
            buf = struct.pack(f'>{len(chunk)}d', *[float(x) for x in chunk])
        elif dtype_tag == b'LOGI':
            buf = struct.pack(f'>{len(chunk)}i', *[int(bool(x)) for x in chunk])
        else:
            buf = b''
        _write_record(fh, buf)
        offset += max_items


# ---------------------------------------------------------------------------
# Column-name decomposition
# ---------------------------------------------------------------------------

def _decompose_column(col_name, sep=':'):
    """Split a SimPandas column name into (KEYWORD, WGNAME, NUM).

    Convention examples::

        FOPR:FIELD   → ('FOPR',    'FIELD', 0)
        WBHP:PROD1   → ('WBHP',    'PROD1', 0)
        COPR:PROD1:3 → ('COPR',    'PROD1', 3)
        RPR:5        → ('RPR',     '',       5)
        TIME         → ('TIME',    '',       0)

    Returns
    -------
    tuple of (str, str, int)
    """
    parts = col_name.split(sep)
    keyword = parts[0]
    wgname = ''
    num = 0

    if len(parts) == 1:
        pass
    elif len(parts) == 2:
        # Could be KEYWORD:WGNAME or KEYWORD:NUM
        try:
            num = int(parts[1])
        except ValueError:
            wgname = parts[1]
    elif len(parts) >= 3:
        wgname = parts[1]
        try:
            num = int(parts[2])
        except ValueError:
            pass

    return keyword, wgname, num


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_summary(sdf, smspec_path, unsmry_path=None, startdat=None):
    """
    Write a SimDataFrame to Eclipse binary summary format.

    Produces a pair of files:

    * ``<smspec_path>``  – the SMSPEC header (KEYWORDS, WGNAMES, NUMS,
      UNITS, STARTDAT, DIMENS)
    * ``<unsmry_path>``  – the unified UNSMRY data (SEQHDR + repeating
      MINISTEP / PARAMS records)

    The column names are decomposed using the SimPandas ``name_separator``
    (default ``:``) into KEYWORD, WGNAME and NUM.

    Parameters
    ----------
    sdf : SimDataFrame
        The data to write.  The index is treated as the TIME vector and
        is prepended as the first item in each PARAMS record.
    smspec_path : str or path-like
        Destination path for the SMSPEC file.
    unsmry_path : str or path-like or None
        Destination path for the UNSMRY file.  When ``None`` the path
        is derived by replacing ``.SMSPEC`` with ``.UNSMRY``.
    startdat : list or tuple of ints, optional
        ``[day, month, year]`` (optionally ``[day, month, year, hour,
        minute, microsecond]``).  When ``None``, ``[1, 1, 2000]`` is
        used as a default.

    Returns
    -------
    None
    """
    import os
    import pandas as pd

    smspec_path = str(smspec_path)
    if unsmry_path is None:
        base, ext = os.path.splitext(smspec_path)
        if ext.upper() == '.SMSPEC':
            unsmry_path = base + ext.replace('SMSPEC', 'UNSMRY').replace('smspec', 'unsmry')
        else:
            unsmry_path = smspec_path + '.UNSMRY'
    else:
        unsmry_path = str(unsmry_path)

    # Normalise to plain DataFrame
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

    sep = getattr(sdf, 'name_separator', ':') or ':'

    # Gather units
    try:
        raw_units = sdf.units
        if isinstance(raw_units, dict):
            col_units = dict(raw_units)
        else:
            col_units = {}
    except Exception:
        col_units = {}

    index_units_val = getattr(sdf, 'index_units', None) or 'DAYS'

    # ----- build SMSPEC vectors ------------------------------------------
    # The TIME vector is always the first entry (comes from the index).
    time_kw = 'TIME'
    index_name = df.index.name
    if index_name and index_name.upper() in ('YEARS', 'YEAR'):
        time_kw = 'YEARS'
    elif index_name and index_name.upper() == 'TIME':
        time_kw = 'TIME'

    keywords = [time_kw]
    wgnames = ['']
    nums_list = [0]
    units_out = [index_units_val]

    for col in df.columns:
        kw, wg, num = _decompose_column(col, sep)
        keywords.append(kw)
        wgnames.append(wg)
        nums_list.append(num)
        units_out.append(col_units.get(col, ''))

    nlist = len(keywords)

    # Encode wgnames: field-level → ':+:+:+:+'
    wgnames_enc = []
    for wg in wgnames:
        if wg.upper() in ('FIELD', '') or not wg:
            wgnames_enc.append(':+:+:+:+')
        else:
            wgnames_enc.append(wg)

    if startdat is None:
        startdat = [1, 1, 2000]

    # ----- write SMSPEC --------------------------------------------------
    with open(smspec_path, 'wb') as fh:
        # RESTART (empty, 9 items for compatibility)
        _write_keyword(fh, 'RESTART', b'CHAR', [''] * 9)

        # DIMENS: nlist, nx, ny, nz, ?, ?   (only nlist matters for summary)
        _write_keyword(fh, 'DIMENS', b'INTE', [nlist, 1, 1, 1, 0, -1])

        # KEYWORDS
        _write_keyword(fh, 'KEYWORDS', b'CHAR', keywords)

        # WGNAMES
        _write_keyword(fh, 'WGNAMES', b'CHAR', wgnames_enc)

        # NUMS
        _write_keyword(fh, 'NUMS', b'INTE', nums_list)

        # UNITS
        _write_keyword(fh, 'UNITS', b'CHAR', units_out)

        # STARTDAT
        _write_keyword(fh, 'STARTDAT', b'INTE', [int(x) for x in startdat])

    # ----- write UNSMRY --------------------------------------------------
    with open(unsmry_path, 'wb') as fh:
        # SEQHDR – unified-file marker
        _write_keyword(fh, 'SEQHDR', b'INTE', [0])

        for step_idx in range(len(df)):
            # MINISTEP
            _write_keyword(fh, 'MINISTEP', b'INTE', [step_idx])

            # PARAMS – float array: [time_value, col0, col1, ...]
            time_val = float(df.index[step_idx])
            row_vals = [time_val] + [float(v) for v in df.iloc[step_idx].values]
            _write_keyword(fh, 'PARAMS', b'REAL', row_vals)
