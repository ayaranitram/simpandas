# -*- coding: utf-8 -*-
"""
Eclipse binary summary writer (.SMSPEC + .UNSMRY).

Writes a SimDataFrame into the pair of binary files that reservoir
simulators (Eclipse, OPM Flow, etc.) consume.

No external dependencies beyond NumPy and pandas.
"""

__version__ = '0.1.1'
__release__ = 20260420

__all__ = ['write_summary']

import struct
import re
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
        b'C008': 105,
        b'LOGI': 1000,
    }.get(dtype_tag, 1000)

    offset = 0
    while offset < count:
        chunk = data[offset:offset + max_items]
        if dtype_tag in (b'CHAR', b'C008'):
            buf = b''.join((s or '').encode('ascii', errors='replace').ljust(8)[:8]
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

def _decompose_column(col_name, sep=':', nx=1, ny=1):
    """Split a SimPandas column name into Eclipse summary vector components.

    The decomposition mirrors the naming conventions used by the reader,
    including LGR (Local Grid Refinement) vectors:

    * ``FOPR``                   → ``('FOPR', '', 0, '', -1, -1, -1)``
    * ``WBHP:PROD1``             → ``('WBHP', 'PROD1', 0, '', -1, -1, -1)``
    * ``WBHP:PROD1:LGR1``        → ``('WBHP', 'PROD1', 0, 'LGR1', -1, -1, -1)``
    * ``COPR:PROD1:3``           → ``('COPR', 'PROD1', 3, '', -1, -1, -1)``
    * ``COPR:PROD1:LGR1:3``      → ``('COPR', 'PROD1', 3, 'LGR1', -1, -1, -1)``
    * ``BPR:3,4,5``              → ``('BPR',  '', linearised_num, '', -1, -1, -1)``
    * ``BPR:LGR1:2,3,1``         → ``('BPR',  '', 0, 'LGR1', 2, 3, 1)``
    * ``RPR:5``                  → ``('RPR',  '', 5, '', -1, -1, -1)``

    Parameters
    ----------
    col_name : str
    sep : str
    nx, ny : int
        Grid dimensions for encoding main-grid B-vector ``i,j,k`` as a
        linearised NUMS value.

    Returns
    -------
    tuple : (keyword, wgname, num, lgr_name, numlx, numly, numlz)
        ``numlx/numly/numlz`` are -1 for non-LGR vectors.
    """
    parts = col_name.split(sep)
    keyword = parts[0]
    wgname = ''
    num = 0
    lgr_name = ''
    lx = ly = lz = -1
    kw_prefix = keyword[0].upper() if keyword else 'X'

    if len(parts) == 1:
        # Bare keyword (TIME, FOPR, …)
        pass
    elif len(parts) == 2:
        tail = parts[1]
        if kw_prefix == 'B' and ',' in tail:
            # Main-grid B-vector: KEYWORD:i,j,k → linearised NUMS
            ijk = [int(x) for x in tail.split(',')]
            if len(ijk) == 3:
                i, j, k = ijk
                num = (i - 1) + (j - 1) * nx + (k - 1) * nx * ny + 1
        elif kw_prefix in ('R', 'A'):
            # Region / Aquifer: always KEYWORD:NUM
            try:
                num = int(tail)
            except ValueError:
                wgname = tail
        else:
            # Could be KEYWORD:WGNAME or KEYWORD:NUM
            try:
                num = int(tail)
            except ValueError:
                wgname = tail
    elif len(parts) == 3:
        if kw_prefix == 'B' and ',' in parts[2]:
            # LGR B-vector: KEYWORD:LGRNAME:ix,iy,iz
            lgr_name = parts[1]
            ijk = [int(x) for x in parts[2].split(',')]
            if len(ijk) == 3:
                lx, ly, lz = ijk
        else:
            # KEYWORD:WGNAME:NUM  (completion, main grid)
            # or KEYWORD:WGNAME:LGRNAME  (well/group in LGR)
            wgname = parts[1]
            try:
                num = int(parts[2])
            except ValueError:
                lgr_name = parts[2]
    elif len(parts) >= 4:
        # KEYWORD:WGNAME:LGRNAME:NUM  (completion in LGR)
        wgname = parts[1]
        lgr_name = parts[2]
        try:
            num = int(parts[3])
        except ValueError:
            pass

    return keyword, wgname, num, lgr_name, lx, ly, lz


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_summary(sdf, smspec_path, unsmry_path=None, startdat=None,
                  dimens=None, style='OPM'):
    """
    Write a SimDataFrame to Eclipse binary summary format.

    Produces a pair of files:

    * ``<smspec_path>``  – the SMSPEC header (KEYWORDS, NAMES/WGNAMES, NUMS,
      LGRS, NUMLX, NUMLY, NUMLZ, UNITS, STARTDAT, DIMENS)
    * ``<unsmry_path>``  – the unified UNSMRY data (SEQHDR + repeating
      MINISTEP / PARAMS records)

    The column names are decomposed using the SimPandas ``name_separator``
    (default ``:``) into KEYWORD, WGNAME, NUM and (when present) LGR info.

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
        minute, microsecond]``).  When ``None`` and the index is a
        DatetimeIndex the start date is derived from the first entry;
        otherwise ``[1, 1, 1900]`` is used.
    dimens : list or tuple of ints, optional
        ``[nx, ny, nz]`` grid dimensions.  Required for correct
        round-trip of B-prefix (block) vectors.  When ``None`` the
        dimensions are inferred from the maximum ``i,j,k`` found in
        column names (which is only exact when at least the corner
        block is present).
    style : str, default ``'OPM'``
        Output format style.

        * ``'OPM'``     – writes entity names as ``NAMES`` (dtype ``C008``);
          compatible with OPM Flow, ECHELON and our reader.
        * ``'ECLIPSE'`` – writes entity names as ``WGNAMES`` (dtype ``CHAR``);
          required by classic Eclipse 100/300.

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

    # ---- Gather units (handle dict or positional list) ------------------
    col_units_list = None  # positional list (used when ColumnUnits detected)
    try:
        raw_units = sdf.units
        if isinstance(raw_units, dict):
            col_units = dict(raw_units)
        elif hasattr(raw_units, 'to_list'):  # ColumnUnits – preserve positional order
            col_units_list = raw_units.to_list()
            col_units = {}
        elif isinstance(raw_units, (list, tuple)):
            col_units = dict(zip(df.columns, raw_units))
        else:
            col_units = {}
    except Exception:
        col_units = {}

    # ---- Drop time/date columns that must not be written as data vectors --
    # DATE is always Timestamp-valued (can't be stored as REAL PARAMS).
    # The keyword that becomes the leading PARAMS entry (TIME when index is DATE
    # or TIME; YEARS when index is YEARS) would produce a duplicate SMSPEC entry
    # if also present as a data column, so it is dropped too.
    # Other time vectors (e.g. YEARS when TIME is the index, or TIME when YEARS
    # is the index) are legitimate data vectors and must be preserved.
    _idx_name = (df.index.name or '').upper()
    _leading_time_kw = 'YEARS' if _idx_name in ('YEARS', 'YEAR') else 'TIME'
    _drop_cols = [c for c in df.columns
                  if c.upper() == 'DATE' or c.upper() == _leading_time_kw]
    if _drop_cols:
        _drop_set = set(_drop_cols)
        if col_units_list is not None:
            col_units_list = [u for c, u in zip(df.columns, col_units_list)
                               if c not in _drop_set]
        else:
            col_units = {k: v for k, v in col_units.items() if k not in _drop_set}
        df = df.drop(columns=_drop_cols)

    index_units_val = getattr(sdf, 'index_units', None) or 'DAYS'

    # Retrieve meta dict from the source SimDataFrame (set by read_summary)
    _meta = getattr(sdf, 'meta', None) or {}

    # ---- Handle DATE (datetime) index → convert to TIME (float days) ----
    time_kw = 'TIME'
    time_values = None          # filled below when index is datetime
    derived_startdat = None

    index_name = df.index.name or ''

    if isinstance(df.index, pd.DatetimeIndex) or index_name.upper() == 'DATE':
        # Convert DatetimeIndex → float TIME in days since start_date
        dt_index = pd.DatetimeIndex(df.index)
        start_date = dt_index[0]
        time_values = (dt_index - start_date).total_seconds() / 86400.0
        derived_startdat = [start_date.day, start_date.month, start_date.year]
        if start_date.hour or start_date.minute or start_date.second:
            derived_startdat += [start_date.hour, start_date.minute,
                                 start_date.second * 1_000_000]
        index_units_val = 'DAYS'
        time_kw = 'TIME'
    elif index_name.upper() in ('YEARS', 'YEAR'):
        time_kw = 'YEARS'
    elif index_name.upper() == 'TIME':
        time_kw = 'TIME'

    if startdat is None:
        if derived_startdat:
            startdat = derived_startdat
        elif isinstance(_meta, dict) and _meta.get('startdat'):
            startdat = _meta['startdat']
        else:
            startdat = [1, 1, 1900]  # Eclipse default start date

    # ---- Determine grid dimensions for B-vector encoding ----------------
    if dimens is not None:
        nx, ny, nz = int(dimens[0]), int(dimens[1]), int(dimens[2])
    elif isinstance(_meta, dict) and _meta.get('dimens'):
        nx, ny, nz = [int(v) for v in _meta['dimens']]
    else:
        # Infer from max i,j,k in B-vector column names
        max_i, max_j, max_k = 1, 1, 1
        _ijk_re = re.compile(r'^B\w*' + re.escape(sep) + r'(\d+),(\d+),(\d+)$')
        for col in df.columns:
            m = _ijk_re.match(col)
            if m:
                max_i = max(max_i, int(m.group(1)))
                max_j = max(max_j, int(m.group(2)))
                max_k = max(max_k, int(m.group(3)))
        nx, ny, nz = max_i, max_j, max_k

    # ---- Build SMSPEC vectors -------------------------------------------
    # The TIME vector is always the first entry (comes from the index).
    keywords  = [time_kw]
    wgnames   = ['']
    nums_list = [0]
    units_out = [index_units_val]
    lgrs_list  = ['']
    numlx_list = [-1]
    numly_list = [-1]
    numlz_list = [-1]

    _col_idx = 0
    for col in df.columns:
        kw, wg, num, lgr, lx, ly, lz = _decompose_column(col, sep, nx=nx, ny=ny)
        keywords.append(kw)
        wgnames.append(wg)
        nums_list.append(num)
        lgrs_list.append(lgr)
        numlx_list.append(lx)
        numly_list.append(ly)
        numlz_list.append(lz)
        units_out.append(col_units_list[_col_idx] if col_units_list is not None
                          else (col_units.get(col) or ''))
        _col_idx += 1

    nlist = len(keywords)

    # Encode wgnames: empty / 'FIELD' → ':+:+:+:+'
    wgnames_enc = []
    for wg in wgnames:
        if wg.upper() in ('FIELD', '') or not wg:
            wgnames_enc.append(':+:+:+:+')
        else:
            wgnames_enc.append(wg)

    # ---- Write SMSPEC ---------------------------------------------------
    with open(smspec_path, 'wb') as fh:
        # RESTART (empty, 9 items for compatibility)
        _write_keyword(fh, 'RESTART', b'CHAR', [''] * 9)

        # DIMENS: nlist, nx, ny, nz, ?, ?
        _write_keyword(fh, 'DIMENS', b'INTE', [nlist, nx, ny, nz, 0, -1])

        # KEYWORDS
        _write_keyword(fh, 'KEYWORDS', b'CHAR', keywords)

        # Entity names: NAMES (C008) for OPM/ECHELON, WGNAMES (CHAR) for Eclipse
        if style.upper() == 'OPM':
            _write_keyword(fh, 'NAMES', b'C008', wgnames_enc)
        else:
            _write_keyword(fh, 'WGNAMES', b'CHAR', wgnames_enc)

        # NUMS
        _write_keyword(fh, 'NUMS', b'INTE', nums_list)

        # LGR metadata (written even when all empty / -1 for format completeness)
        _write_keyword(fh, 'LGRS',  b'CHAR', lgrs_list)
        _write_keyword(fh, 'NUMLX', b'INTE', numlx_list)
        _write_keyword(fh, 'NUMLY', b'INTE', numly_list)
        _write_keyword(fh, 'NUMLZ', b'INTE', numlz_list)

        # UNITS
        _write_keyword(fh, 'UNITS', b'CHAR', units_out)

        # STARTDAT
        _write_keyword(fh, 'STARTDAT', b'INTE', [int(x) for x in startdat])

    # ---- Write UNSMRY ---------------------------------------------------
    with open(unsmry_path, 'wb') as fh:
        # SEQHDR – unified-file marker
        _write_keyword(fh, 'SEQHDR', b'INTE', [0])

        for step_idx in range(len(df)):
            # MINISTEP
            _write_keyword(fh, 'MINISTEP', b'INTE', [step_idx])

            # PARAMS – float array: [time_value, col0, col1, ...]
            if time_values is not None:
                time_val = float(time_values[step_idx])
            else:
                time_val = float(df.index[step_idx])
            row_vals = [time_val] + [float(v) for v in df.iloc[step_idx].values]
            _write_keyword(fh, 'PARAMS', b'REAL', row_vals)
