# -*- coding: utf-8 -*-
"""
Eclipse binary summary reader (.SMSPEC + .UNSMRY / S0001..SNNN).

Reads the SMSPEC header and UNSMRY data files produced by reservoir
simulators (Eclipse, OPM Flow, ECHELON, etc.) and returns a ``SimDataFrame``
with properly labelled columns and units.

No external dependencies beyond NumPy and pandas.
"""

__version__ = '0.1.0'
__release__ = 20260418

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
    b'LOGI': ('>i', 4),   # logical stored as int32
    b'MESS': (None, 0),   # message keyword (no data)
}

# Maximum items per sub-record (Fortran block size limit)
_MAX_ITEMS = {
    b'INTE': 1000,
    b'REAL': 1000,
    b'DOUB': 1000,
    b'CHAR': 105,
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
        if dtype_tag == b'CHAR':
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
    nlist = 0
    startdat = None

    with open(smspec_path, 'rb') as fh:
        while True:
            result = _read_keyword(fh)
            if result is None:
                break
            kw, count, dtype_tag, data = result
            if kw == 'DIMENS':
                nlist = int(data[0])
            elif kw == 'KEYWORDS':
                keywords = data[:nlist] if nlist else data
            elif kw == 'WGNAMES':
                wgnames = data[:nlist] if nlist else data
            elif kw == 'NUMS':
                nums = [int(x) for x in (data[:nlist] if nlist else data)]
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

    # ----- build column names --------------------------------------------
    sep = nameSeparator if nameSeparator else ':'
    col_names = []
    for i in range(nlist):
        kw = keywords[i]
        wg = wgnames[i]
        num = nums[i]

        # Sentinel value for field-level vectors
        if wg in (':+:+:+:+', '') or wg.startswith(':+'):
            wg = 'FIELD'

        # Build composite name
        if kw in ('TIME', 'YEARS', 'DAY', 'MONTH', 'YEAR'):
            # Time vectors keep bare keyword
            col_names.append(kw)
        elif num > 0 and wg == 'FIELD':
            # Region/block vectors: KEYWORD:NUM
            col_names.append(f'{kw}{sep}{num}')
        elif num > 0:
            # Completion vectors: KEYWORD:WGNAME:NUM
            col_names.append(f'{kw}{sep}{wg}{sep}{num}')
        else:
            # Well/group/field vectors: KEYWORD:WGNAME
            col_names.append(f'{kw}{sep}{wg}')

    units_dict = {}
    for name, u in zip(col_names, units_list):
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
    df = pd.DataFrame(arr, columns=col_names)

    # Promote TIME or YEARS to index if present
    index_units = None
    for time_col in ('TIME', 'YEARS'):
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

    return SimDataFrame(data=df, **sim_kwargs)
