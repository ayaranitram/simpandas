# -*- coding: utf-8 -*-
"""
Eclipse binary summary reader (.SMSPEC + .UNSMRY / S0001..SNNN).

Reads the SMSPEC header and UNSMRY data files produced by reservoir
simulators (Eclipse, OPM Flow, ECHELON, etc.) and returns a ``SimDataFrame``
with properly labelled columns and units.

No external dependencies beyond NumPy and pandas.
"""

__version__ = '0.1.1'
__release__ = 20260420

from simpandas.frame import SimDataFrame

__all__ = ['read_summary']


# ---------------------------------------------------------------------------
# Low-level binary helpers
# ---------------------------------------------------------------------------

import struct
import numpy as np

# Eclipse keyword data types → struct format + item size
_DTYPE_MAP = {
    b'INTE': ('>i', 4),   # big-endian int32
    b'REAL': ('>f', 4),   # big-endian float32
    b'DOUB': ('>d', 8),   # big-endian float64
    b'CHAR': ('8s', 8),   # 8-byte ASCII string
    b'C008': ('8s', 8),   # 8-byte string (ECHELON/OPM variant of CHAR)
    b'LOGI': ('>i', 4),   # logical stored as int32
    b'MESS': (None, 0),   # message keyword (no data)
}

# Maximum items per sub-record (Fortran block size limit)
_MAX_ITEMS = {
    b'INTE': 1000,
    b'REAL': 1000,
    b'DOUB': 1000,
    b'CHAR': 105,
    b'C008': 105,          # same chunking as CHAR
    b'LOGI': 1000,
    b'MESS': 0,
}


def _read_record(fh):
    """Read one Fortran unformatted record (head-marker, payload, tail-marker)."""
    head = fh.read(4)
    if len(head) < 4:
        return None
    nbytes = struct.unpack('>i', head)[0]
    payload = fh.read(nbytes)
    fh.read(4)  # tail marker
    return payload


def _read_keyword(fh):
    """Read one Eclipse keyword block (header + data sub-records).

    Returns ``(keyword, count, dtype_tag, data_list)`` or ``None`` at EOF.
    """
    header = _read_record(fh)
    if header is None:
        return None

    keyword = header[:8].decode('ascii').strip()
    count = struct.unpack('>i', header[8:12])[0]
    dtype_tag = header[12:16]

    fmt, item_size = _DTYPE_MAP.get(dtype_tag, (None, 0))
    max_items = _MAX_ITEMS.get(dtype_tag, 1000)

    if count == 0 or fmt is None:
        return keyword, count, dtype_tag, []

    data = []
    remaining = count
    while remaining > 0:
        chunk_count = min(remaining, max_items)
        rec = _read_record(fh)
        if rec is None:
            break
        if dtype_tag in (b'CHAR', b'C008'):
            for i in range(chunk_count):
                s = rec[i * 8:(i + 1) * 8].decode('ascii', errors='replace').strip()
                data.append(s)
        else:
            arr = np.frombuffer(rec, dtype=fmt, count=chunk_count)
            data.extend(arr.tolist())
        remaining -= chunk_count

    return keyword, count, dtype_tag, data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_summary(smspec_path,
                 unsmry_path=None,
                 nameSeparator=':',
                 intersectionCharacter=None,
                 autoAppend=False,
                 operatePerName=False,
                 verbose=False):
    """
    Read Eclipse binary summary files into a SimDataFrame.

    Parameters
    ----------
    smspec_path : str or path-like
        Path to the ``.SMSPEC`` file.  The matching ``.UNSMRY`` is
        auto-discovered when *unsmry_path* is ``None``.
    unsmry_path : str or path-like or None
        Explicit path to the unified summary file.  When ``None`` the
        function derives the path by replacing ``.SMSPEC`` with
        ``.UNSMRY`` (case-insensitive).
    nameSeparator : str, default ``':'``
        Character used to join KEYWORD and WGNAME into column names.
    intersectionCharacter, autoAppend, operatePerName, verbose
        Forwarded to the ``SimDataFrame`` constructor.

    Returns
    -------
    SimDataFrame
        Columns follow the ``KEYWORD:WGNAME`` convention (e.g.
        ``FOPR:FIELD``, ``WBHP:PROD1``).  Column units come from the
        SMSPEC UNITS keyword.  The index is ``TIME`` (or ``YEARS``)
        if such a vector is present.

    Notes
    -----
    The reader handles:

    * Unified summary files (``.UNSMRY``)
    * Multiple PARAMS records (one per report step)
    * WGNAMES containing the ``':+:+:+:+'`` sentinel (mapped to
      ``'FIELD'``)
    * NUMS > 0 appended for block / region / completion vectors

    It intentionally ignores restart chains and multiple-file
    (non-unified) summary sets beyond a single pair of files.
    """
    import os
    import pandas as pd

    smspec_path = str(smspec_path)

    # ----- auto-discover UNSMRY path -------------------------------------
    if unsmry_path is None:
        base, ext = os.path.splitext(smspec_path)
        # Handle both .SMSPEC and .smspec
        if ext.upper() == '.SMSPEC':
            for candidate_ext in ('.UNSMRY', '.unsmry'):
                candidate = base + candidate_ext
                if os.path.isfile(candidate):
                    unsmry_path = candidate
                    break
        if unsmry_path is None:
            # Try replacing SMSPEC portion of extension for non-standard names
            for old, new in [('.SMSPEC', '.UNSMRY'), ('.smspec', '.unsmry')]:
                candidate = smspec_path.replace(old, new)
                if candidate != smspec_path and os.path.isfile(candidate):
                    unsmry_path = candidate
                    break
        if unsmry_path is None:
            raise FileNotFoundError(
                f"Could not find a matching UNSMRY file for '{smspec_path}'. "
                "Pass unsmry_path explicitly."
            )
    else:
        unsmry_path = str(unsmry_path)

    # ----- read SMSPEC ---------------------------------------------------
    keywords = []
    wgnames = []
    nums = []
    units_list = []
    lgrs = []
    numlx = []
    numly = []
    numlz = []
    nlist = 0
    nx, ny, nz = 1, 1, 1   # grid dimensions for block-vector decoding
    startdat = None

    with open(smspec_path, 'rb') as fh:
        while True:
            result = _read_keyword(fh)
            if result is None:
                break
            kw, count, dtype_tag, data = result
            if kw == 'DIMENS':
                nlist = int(data[0])
                # DIMENS = [nlist, NX, NY, NZ, ...]
                if len(data) >= 4:
                    nx = max(1, int(data[1]))
                    ny = max(1, int(data[2]))
                    nz = max(1, int(data[3]))
            elif kw == 'KEYWORDS':
                keywords = data[:nlist] if nlist else data
            elif kw == 'WGNAMES':
                wgnames = data[:nlist] if nlist else data
            elif kw == 'NAMES':
                # Some simulators (e.g. ECHELON) use NAMES (type C008) instead
                # of WGNAMES.  Only use it when WGNAMES was not already found.
                if not wgnames:
                    wgnames = data[:nlist] if nlist else data
            elif kw == 'NUMS':
                nums = [int(x) for x in (data[:nlist] if nlist else data)]
            elif kw == 'LGRS':
                lgrs = data[:nlist] if nlist else data
            elif kw == 'NUMLX':
                numlx = [int(x) for x in (data[:nlist] if nlist else data)]
            elif kw == 'NUMLY':
                numly = [int(x) for x in (data[:nlist] if nlist else data)]
            elif kw == 'NUMLZ':
                numlz = [int(x) for x in (data[:nlist] if nlist else data)]
            elif kw == 'UNITS':
                units_list = data[:nlist] if nlist else data
            elif kw == 'STARTDAT':
                startdat = data

    if not keywords:
        raise ValueError(f"No KEYWORDS record found in '{smspec_path}'.")

    nlist = len(keywords)

    # Pad lists to nlist length
    while len(wgnames) < nlist:
        wgnames.append('')
    while len(nums) < nlist:
        nums.append(0)
    while len(units_list) < nlist:
        units_list.append('')
    while len(lgrs) < nlist:
        lgrs.append('')
    while len(numlx) < nlist:
        numlx.append(-1)
    while len(numly) < nlist:
        numly.append(-1)
    while len(numlz) < nlist:
        numlz.append(-1)

    # ----- build column names (None = skip this SMSPEC item) ------------
    sep = nameSeparator if nameSeparator else ':'
    col_names = []   # one entry per SMSPEC item; None means skip
    for i in range(nlist):
        kw = keywords[i]
        wg = wgnames[i]
        num = nums[i]
        lgr = lgrs[i].strip() if i < len(lgrs) else ''
        lx  = numlx[i] if i < len(numlx) else -1
        ly  = numly[i] if i < len(numly) else -1
        lz  = numlz[i] if i < len(numlz) else -1
        is_lgr = bool(lgr)

        # Build composite name using keyword prefix to determine structure.
        # In Eclipse SMSPEC the NUMS value means different things:
        #   F      – field-level, no entity          → bare keyword
        #   W / G  – well/group seq. number (ignore) → KEYWORD:WGNAME
        #   C / S  – completion / segment number     → KEYWORD:WGNAME:NUM
        #   R / A  – region / aquifer number         → KEYWORD:NUM
        #   B      – linearised grid block index     → KEYWORD:i,j,k
        kw_prefix = kw[0].upper() if kw else 'X'

        # -32767 is the Eclipse NUMS sentinel for "no number"; treat as 0.
        if num == -32767:
            num = 0

        # Sentinel WGNAME (':+:+:+:+' or empty) on a non-F keyword means
        # the entry has no real entity name → skip it entirely.
        is_sentinel = wg.startswith(':+')  # or (not wg and kw_prefix in ('W', 'G'))  # discard empty wgnames only for W and G keywords

        #print(f"DEBUG: kw='{kw}', wg='{wg}', num={num}, kw_prefix={kw_prefix}, is_sentinel={is_sentinel}")
        
        if kw in ('TIME', 'YEARS', 'DAY', 'MONTH', 'YEAR'):
            # Time vectors: bare keyword, no entity
            col_names.append(kw)
        elif kw_prefix == 'F':
            # Field-level vector: bare keyword, no entity appended
            col_names.append(kw)
        elif kw_prefix in ('R', 'A'):
            # Region / Aquifer: KEYWORD:NUM  (sentinel WGNAME is normal)
            if num > 0:
                col_names.append(f'{kw}{sep}{num}')
            else:
                col_names.append(None)
        elif kw_prefix == 'B':
            # Block vector: sentinel WGNAME is normal
            if is_lgr and lx > 0 and ly > 0 and lz > 0:
                # LGR block: NUMLX/NUMLY/NUMLZ give coordinates directly
                col_names.append(f'{kw}{sep}{lgr}{sep}{lx},{ly},{lz}')
            elif num > 0:
                # Main-grid block: decode linearised index → i,j,k (1-based)
                n0 = num - 1
                bi = (n0 % nx) + 1
                bj = ((n0 // nx) % ny) + 1
                bk = (n0 // (nx * ny)) + 1
                col_names.append(f'{kw}{sep}{bi},{bj},{bk}')
            else:
                col_names.append(None)
        elif is_sentinel and kw_prefix in ('W', 'G', 'C', 'S'):
            # Sentinel WGNAME on W/G/C/S vector → no real entity, skip
            col_names.append(None)
        elif kw_prefix in ('W', 'G'):
            if wg:
                if is_lgr:
                    # Well / Group scoped to an LGR: KEYWORD:WGNAME:LGRNAME
                    col_names.append(f'{kw}{sep}{wg}{sep}{lgr}')
                else:
                    # Well / Group: KEYWORD:WGNAME
                    col_names.append(f'{kw}{sep}{wg}')
            else:
                # keyword with no WGNAME → no real entity, skip
                col_names.append(None)
        elif kw_prefix in ('C', 'S'):
            if is_lgr:
                # Completion / Segment in LGR: KEYWORD:WGNAME:LGRNAME[:NUM]
                if num > 0:
                    col_names.append(f'{kw}{sep}{wg}{sep}{lgr}{sep}{num}')
                else:
                    col_names.append(f'{kw}{sep}{wg}{sep}{lgr}')
            elif num > 0:
                # Completion / Segment: KEYWORD:WGNAME:NUM
                col_names.append(f'{kw}{sep}{wg}{sep}{num}')
            else:
                col_names.append(None)
        elif num > 0 and wg and not is_sentinel:
            # Generic vector with entity name and qualifier
            col_names.append(f'{kw}{sep}{wg}{sep}{num}')
        elif num > 0 and (not wg or is_sentinel):
            col_names.append(f'{kw}{sep}{num}')
        elif wg and not is_sentinel:
            col_names.append(f'{kw}{sep}{wg}')
        else:
            col_names.append(f'{kw}')

    # Indices of items that should appear in the output DataFrame
    keep_idx = [i for i, name in enumerate(col_names) if name is not None]
    kept_names = [col_names[i] for i in keep_idx]

    units_dict = {}
    for name, u in zip(kept_names, [units_list[i] for i in keep_idx]):
        if u:
            units_dict[name] = u.strip()

    # ----- read UNSMRY ---------------------------------------------------
    rows = []
    with open(unsmry_path, 'rb') as fh:
        while True:
            result = _read_keyword(fh)
            if result is None:
                break
            kw, count, dtype_tag, data = result
            if kw == 'PARAMS':
                # Each PARAMS record has nlist float values
                rows.append(data[:nlist])
            # SEQHDR, MINISTEP, etc. are silently skipped

    if not rows:
        raise ValueError(f"No PARAMS records found in '{unsmry_path}'.")

    # ----- assemble DataFrame --------------------------------------------
    arr = np.array(rows, dtype=np.float64)
    # Select only the kept columns (skip sentinel / null entries)
    arr = arr[:, keep_idx]
    df = pd.DataFrame(arr, columns=kept_names)

    # ----- drop fully-duplicate columns (same name, same unit, same data) --
    # Build a fingerprint per column position and keep only the first
    # occurrence of each (name, unit, data) triple.
    seen = {}        # fingerprint → first column position kept
    drop_positions = set()
    col_list = list(df.columns)
    for pos, col in enumerate(col_list):
        unit = units_dict.get(col, None)
        # Use a tuple of rounded values as a fast data fingerprint;
        # np.round avoids float noise from different REAL encodings.
        data_key = tuple(np.round(df.iloc[:, pos].values, decimals=6))
        fp = (col, unit, data_key)
        if fp in seen:
            drop_positions.add(pos)
        else:
            seen[fp] = pos

    if drop_positions:
        keep_positions = [p for p in range(len(col_list)) if p not in drop_positions]
        df = df.iloc[:, keep_positions]
        # Re-derive units_dict from the surviving columns
        surviving_cols = list(df.columns)
        units_dict = {c: units_dict[c] for c in surviving_cols if c in units_dict}

    # ----- compute DATE column from STARTDAT + TIME (days) --------------
    # STARTDAT layout: [day, month, year] or [day, month, year, hour, min, us]
    if startdat and len(startdat) >= 3:
        try:
            day   = int(startdat[0])
            month = int(startdat[1])
            year  = int(startdat[2])
            hour  = int(startdat[3]) if len(startdat) > 3 else 0
            minute = int(startdat[4]) if len(startdat) > 4 else 0
            # startdat[5] is microseconds in Eclipse; convert to seconds
            second = int(startdat[5]) // 1_000_000 if len(startdat) > 5 else 0
            start_date = pd.Timestamp(year=year, month=month, day=day,
                                      hour=hour, minute=minute, second=second)
            time_col_name = next((c for c in ('TIME', 'YEARS') if c in df.columns), None)
            if time_col_name is not None:
                if time_col_name == 'YEARS':
                    delta_days = (df[time_col_name] * 365.25).round().astype('int64')
                else:
                    delta_days = df[time_col_name].round().astype('int64')
                df.insert(0, 'DATE',
                          start_date + pd.to_timedelta(delta_days, unit='D'))
                units_dict['DATE'] = 'datetime'
        except Exception:
            pass  # malformed STARTDAT; silently skip DATE column

    # Promote DATE, TIME or YEARS to index if present
    index_units = None
    for time_col in ('DATE', 'TIME', 'YEARS'):
        if time_col in df.columns:
            df = df.set_index(time_col)
            index_units = units_dict.pop(time_col, None)
            break

    sim_kwargs = {'units': units_dict}
    if index_units:
        sim_kwargs['index_units'] = index_units
    if nameSeparator is not None:
        sim_kwargs['name_separator'] = nameSeparator
    if intersectionCharacter is not None:
        sim_kwargs['intersection_character'] = intersectionCharacter
    sim_kwargs['auto_append'] = autoAppend
    sim_kwargs['operate_per_name'] = operatePerName
    sim_kwargs['verbose'] = verbose

    # Preserve grid dimensions and start date so the writer can re-use them.
    sim_kwargs['meta'] = {
        'dimens': [nx, ny, nz],
        'startdat': [int(x) for x in startdat] if startdat else None,
    }

    return SimDataFrame(data=df, **sim_kwargs)
