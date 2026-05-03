# -*- coding: utf-8 -*-
"""
VDB (VIP / Nexus) binary reader.

Reads time-series plot data from ``.vdb`` folders produced by the VIP and
Nexus reservoir simulators and returns a ``SimDataFrame`` with labelled
columns and units.

The reader follows a best-effort approach: it extracts well-level and
region-level data from ``plot.bin`` and well names from ``welist.bin``,
logging warnings for sections it cannot parse.  No external dependencies
beyond NumPy and pandas.

Binary format notes
-------------------
* Magic signature: ``NT32`` (4 bytes, little-endian throughout).
* Header area (first ~250 KB) contains 10 VARDESC blocks that define
  variable names, units and descriptions for different data tables.
* Data records follow the pattern::

      count(LE i32) | -1(LE i32) | count(LE i32) | float32[count]

  where ``count = n_vars + 2`` (the first two floats are TIME in days
  and a status FLAG).
* Records are interleaved across wells at each time step.
"""

__version__ = '0.1.1'
__release__ = 20260503

import logging
import os
import re
import struct
from collections import OrderedDict
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pandas as pd

from simpandas.frame import SimDataFrame

__all__ = ['read_vdb']

log = logging.getLogger(__name__)

# VDB internal key -> Eclipse/VIP style key mapping (from vdbObject.py)
VDB2VIP = {
    'QOP': 'OPR', 'QGP': 'GPR', 'QWP': 'WPR',
    'QGI': 'GIR', 'QWI': 'WIR',
    'COP': 'OPT', 'CGP': 'GPT', 'CWP': 'WPT',
    'CGI': 'GIT', 'CWI': 'WIT',
    'BHP': 'BHP', 'THP': 'THP',
    'OIP': 'OIP', 'GIP': 'GIP', 'WIP': 'WIP',
}

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _find_plot_bins(vdb_path):
    """Return all plot.bin paths under *vdb_path* sorted deepest-first."""
    plots = []
    for root, _dirs, files in os.walk(vdb_path):
        for f in files:
            if f.lower() == 'plot.bin':
                fp = os.path.join(root, f)
                depth = fp.count(os.sep)
                size = os.path.getsize(fp)
                plots.append((fp, depth, size))
    plots.sort(key=lambda x: (-x[1], -x[2]))
    return plots


def _resolve_case_path(vdb_path, case=None):
    """Locate the case directory inside a .vdb folder.

    If *case* is given, look for ``<case>/PLOT/plot.bin``.
    Otherwise parse ``main.xml`` for the hierarchy and pick the root
    case that has data, falling back to the deepest non-empty plot.bin.
    """
    vdb_path = str(vdb_path)

    # Direct file reference
    if os.path.isfile(vdb_path) and vdb_path.lower().endswith('.bin'):
        case_dir = os.path.dirname(os.path.dirname(vdb_path))
        return case_dir, vdb_path

    # Specific case requested
    if case is not None:
        case_dir = os.path.join(vdb_path, case)
        pb = os.path.join(case_dir, 'PLOT', 'plot.bin')
        if os.path.isfile(pb):
            return case_dir, pb
        raise FileNotFoundError(
            f"plot.bin not found for case '{case}' at {pb}")

    # Try main.xml for case hierarchy
    main_xml = os.path.join(vdb_path, 'main.xml')
    if os.path.isfile(main_xml):
        try:
            tree = ElementTree.parse(main_xml)
            cases = []
            for elem in tree.iter('CASE'):
                name = elem.get('Name', '')
                parent = elem.get('Parent', '')
                if name:
                    cases.append((name, parent))
            # Find root case (no parent)
            roots = [n for n, p in cases if not p]
            if roots:
                # Try root first, then children in order
                for name, _ in cases:
                    pb = os.path.join(vdb_path, name, 'PLOT', 'plot.bin')
                    if os.path.isfile(pb) and os.path.getsize(pb) > 500:
                        return os.path.join(vdb_path, name), pb
        except Exception:
            pass

    # Fallback: deepest non-empty plot.bin
    plots = _find_plot_bins(vdb_path)
    for fp, _depth, size in plots:
        if size > 500:
            case_dir = os.path.dirname(os.path.dirname(fp))
            return case_dir, fp

    raise FileNotFoundError(
        f"No non-empty plot.bin found under {vdb_path}")


# Header keyword tokens that appear in welist.bin and are NOT well names.
_WELIST_SKIP = frozenset({
    'NT', 'NT32', 'RECUR', 'MASTER', 'DBF', 'VARDESC', 'VARLIST',
    'ITEMS', 'INFO', 'MISC', 'GRIDSTAT', 'LASTMOD', 'MAPREC',
    'PLOT', 'PLOTTS', 'WELIST', 'VARLONG',
})


def _extract_8char_names(data):
    """Scan *data* byte-by-byte for VDB character records and return names.

    VDB character records have the structure::

        type_marker(2 B) | count(LE i32) | -1(LE i32) | count(LE i32) | count bytes

    The 2-byte type marker preceding the count makes the record
    mis-aligned with 4-byte boundaries, so a pure int32 scan misses
    them.  Instead we scan for the ``ff ff ff ff`` sentinel at byte
    level, verify the count fields on both sides match, and then
    decode the data as 8-char space-padded ASCII name entries.
    """
    names = []
    seen = set()
    sentinel = b'\xff\xff\xff\xff'
    pos = 0
    n = len(data)
    while pos < n - 12:
        idx = data.find(sentinel, pos)
        if idx < 4 or idx + 8 > n:
            break
        count_b = struct.unpack_from('<I', data, idx - 4)[0]
        count_a = struct.unpack_from('<I', data, idx + 4)[0]
        if count_b != count_a or count_b < 8 or count_b > 50000 or count_b % 8 != 0:
            pos = idx + 4
            continue
        char_start = idx + 8
        char_end = char_start + count_b
        if char_end > n:
            pos = idx + 4
            continue
        chunk = data[char_start:char_end]
        # Accept only records whose payload is entirely printable ASCII.
        if all(0x20 <= b <= 0x7E for b in chunk):
            try:
                text = chunk.decode('ascii')
            except Exception:
                pos = idx + 4
                continue
            for i in range(0, len(text), 8):
                name = text[i:i + 8].rstrip()
                # Skip blank, header keywords, encoded ordinal IDs (#000001W)
                # and version strings (contain a dot, e.g. "1.0.0").
                if (name
                        and name.upper() not in _WELIST_SKIP
                        and not name.startswith('#')
                        and '.' not in name):
                    if name not in seen:
                        seen.add(name)
                        names.append(name)
        pos = idx + 4
    return names


def _parse_welist(case_dir):
    """Extract well names from ``WELIST/welist.bin``."""
    welist = os.path.join(case_dir, 'WELIST', 'welist.bin')
    if not os.path.isfile(welist):
        return []
    with open(welist, 'rb') as f:
        data = f.read()
    return _extract_8char_names(data)


# ---------------------------------------------------------------------------
# VARDESC / variable description parsing
# ---------------------------------------------------------------------------

def _parse_vardesc_blocks(data, max_header=500000):
    """Parse all VARDESC blocks from the header area of plot.bin.

    Returns a list of dicts, each with keys 'var_names', 'units', 'descs',
    'record_count' (= n_vars + 2).
    """
    header = data[:min(len(data), max_header)]
    vardesc_pos = [m.start() for m in re.finditer(rb'VARDESC', header)]
    tables = []

    for vi, vpos in enumerate(vardesc_pos):
        # Each VARDESC is followed by: VARLIST ITEMS <8-byte names> ...
        # Then later in the file, a description section with units.
        if vi < len(vardesc_pos) - 1:
            block_end = vardesc_pos[vi + 1]
        else:
            # For the last VARDESC, scan further for descriptions
            block_end = min(vpos + 200000, len(data))

        block = data[vpos:block_end]

        # Extract variable descriptions: KEY(1-8 uppercase) followed by (UNITS)
        # Use a relaxed pattern that doesn't depend on trailing description text,
        # since binary bytes can appear immediately after the description.
        desc_pattern = rb'([A-Z][A-Z0-9_]{0,7})\s{0,7}\(([^)]{1,30})\)'
        var_names = []
        units_dict = OrderedDict()
        descs_dict = OrderedDict()

        skip_keys = {'VARLIST', 'ITEMS', 'VARDESC', 'DIMENS', 'UNIT', 'N'}
        for m in re.finditer(desc_pattern, block):
            key = m.group(1).decode('ascii', errors='replace').strip()
            unit = m.group(2).decode('ascii', errors='replace').strip()
            if key and key not in skip_keys:
                if key not in units_dict:
                    var_names.append(key)
                units_dict[key] = unit
                # Try to extract description text after the unit
                desc_start = m.end()
                desc_chunk = block[desc_start:desc_start + 60]
                try:
                    desc_text = desc_chunk.split(b'\x00')[0].decode(
                        'ascii', errors='replace').strip()
                    descs_dict[key] = desc_text
                except Exception:
                    descs_dict[key] = ''

        record_count = len(var_names) + 2  # TIME + FLAG prefix
        tables.append({
            'index': vi,
            'offset': vpos,
            'var_names': var_names,
            'units': units_dict,
            'descs': descs_dict,
            'record_count': record_count,
        })

    return tables


def _parse_header_date(data):
    """Try to extract the simulation start date from the header."""
    # Date is stored as 6 LE int32s near offset ~340: day, month, year (×2)
    for offset in range(300, min(len(data), 2000), 4):
        try:
            vals = struct.unpack_from('<6i', data, offset)
            d1, m1, y1, d2, m2, y2 = vals
            if (1 <= d1 <= 31 and 1 <= m1 <= 12 and 1900 <= y1 <= 2100
                    and d1 == d2 and m1 == m2 and y1 == y2):
                return y1, m1, d1
        except struct.error:
            break
    return None


# ---------------------------------------------------------------------------
# Data record extraction
# ---------------------------------------------------------------------------

def _scan_data_records(data, target_counts, max_records=500000):
    """Scan *data* for data records matching any of *target_counts*.

    Each record is: count(LE i32) | -1(LE i32) | count(LE i32) | float32[count]

    Uses numpy vectorisation for speed on large files.
    Returns dict mapping count -> list of float32 arrays.
    """
    target_set = set(int(c) for c in target_counts)
    results = {c: [] for c in target_set}

    # Map entire file as int32 array
    n_bytes = len(data)
    # Ensure alignment (trim trailing bytes)
    usable = (n_bytes // 4) * 4
    iarr = np.frombuffer(data[:usable], dtype='<i4')
    n = len(iarr)
    if n < 3:
        return results

    # Find all positions where iarr[i+1] == -1 (sentinel)
    sentinel_mask = (iarr[1:n - 1] == -1)
    sentinel_positions = np.nonzero(sentinel_mask)[0] + 1  # offset by 1

    total_found = 0
    for s in sentinel_positions:
        if total_found >= max_records:
            break
        # s is the index of -1 in iarr
        # iarr[s-1] should be count, iarr[s+1] should be count
        i0 = s - 1
        i2 = s + 1
        if i0 < 0 or i2 >= n:
            continue
        v0 = int(iarr[i0])
        v2 = int(iarr[i2])
        if v0 != v2 or v0 not in target_set:
            continue

        count = v0
        data_start = (i2 + 1)  # index in int32 array
        data_end = data_start + count
        if data_end > n:
            continue

        # Read as float32
        floats = np.frombuffer(data[data_start * 4:data_end * 4],
                               dtype='<f4').copy()

        # Sanity: first value should be time in days (positive, reasonable)
        if len(floats) >= 2 and np.isfinite(floats[0]) and floats[0] >= 0:
            results[count].append(floats)
            total_found += 1

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_vdb(path,
             case=None,
             tables='well',
             key_style='vdb',
             nameSeparator=':',
             intersectionCharacter='&',
             verbose=False):
    """
    Read VIP / Nexus ``.vdb`` plot data into a ``SimDataFrame``.

    Parameters
    ----------
    path : str or path-like
        Path to the ``.vdb`` folder, a case directory, or a ``plot.bin``
        file directly.
    case : str or None
        Specific case name inside the ``.vdb`` folder (e.g. ``'HM4r'``).
        If *None*, the reader picks the root case with the largest
        non-empty ``plot.bin``.
    tables : str or list of str
        Which data tables to extract.  Supported values:

        * ``'well'`` – well-level production / injection data (default).
        * ``'region'`` – region / ROOT level data (field totals, pressures
          in place, etc.).
        * ``'all'`` – all tables that have data records.

        You can also pass a list, e.g. ``['well', 'region']``.
    key_style : ``'vdb'`` or ``'eclipse'``
        Column key style.  ``'vdb'`` (default) uses the raw VDB key names
        (``QOP``, ``COP``, …).  ``'eclipse'`` converts to Eclipse/VIP
        equivalents via the VDB2VIP mapping (``OPR``, ``OPT``, …).
    nameSeparator : str
        Separator between key and well/entity name in column headers
        (default ``':'``).
    intersectionCharacter : str
        Intersection character passed to ``SimDataFrame``.
    verbose : bool
        If *True*, log detailed progress messages.

    Returns
    -------
    SimDataFrame
        A ``SimDataFrame`` whose index is ``TIME`` (days) and columns are
        ``KEY<sep>WELLNAME`` (e.g. ``QOP:RKF-01P``).  Units are populated
        from the VARDESC descriptions where available.
    """
    path = str(path)
    case_dir, plot_path = _resolve_case_path(path, case=case)

    if verbose:
        log.info('VDB case directory: %s', case_dir)
        log.info('plot.bin: %s (%s bytes)',
                 plot_path, os.path.getsize(plot_path))

    # --- Read entire plot.bin into memory ---
    with open(plot_path, 'rb') as f:
        raw = f.read()

    if len(raw) < 500:
        log.warning('plot.bin is very small (%d bytes), returning empty '
                     'SimDataFrame', len(raw))
        return SimDataFrame(units={}, name_separator=nameSeparator,
                            intersection_character=intersectionCharacter)

    # --- Parse header ---
    all_tables = _parse_vardesc_blocks(raw)
    if not all_tables:
        log.warning('No VARDESC blocks found in %s', plot_path)
        return SimDataFrame(units={}, name_separator=nameSeparator,
                            intersection_character=intersectionCharacter)

    if verbose:
        log.info('Found %d VARDESC tables', len(all_tables))
        for t in all_tables:
            log.info('  Table #%d: %d vars, record_count=%d',
                     t['index'], len(t['var_names']), t['record_count'])

    # --- Identify which tables to extract ---
    if isinstance(tables, str):
        tables = [tables]

    # Heuristic: well-level table is the one with ~50-60 vars containing
    # both QOP and BHP.  Region table is the one containing OIP/GIP/WIP.
    well_table = None
    region_table = None
    for t in all_tables:
        vn_upper = {v.upper() for v in t['var_names']}
        if 'QOP' in vn_upper and 'BHP' in vn_upper and well_table is None:
            well_table = t
        if 'OIP' in vn_upper and 'GIP' in vn_upper and region_table is None:
            region_table = t

    selected = []
    for name in tables:
        name = name.lower()
        if name == 'well' and well_table is not None:
            selected.append(('well', well_table))
        elif name == 'region' and region_table is not None:
            selected.append(('region', region_table))
        elif name == 'all':
            for t in all_tables:
                if t['var_names']:
                    selected.append((f'table{t["index"]}', t))
            break

    if not selected:
        log.warning('No matching tables found. Available tables: %s',
                     [f'#{t["index"]}: {len(t["var_names"])} vars'
                      for t in all_tables])
        return SimDataFrame(units={}, name_separator=nameSeparator,
                            intersection_character=intersectionCharacter)

    # --- Well names ---
    well_names = _parse_welist(case_dir)
    if verbose:
        log.info('Wells from welist.bin: %d', len(well_names))

    # --- Scan for data records ---
    target_counts = set()
    for _label, tbl in selected:
        target_counts.add(tbl['record_count'])

    if verbose:
        log.info('Scanning for records with counts: %s', target_counts)

    records_by_count = _scan_data_records(raw, target_counts)

    # --- Build DataFrames per table ---
    frames = []
    all_units = {}

    for label, tbl in selected:
        rc = tbl['record_count']
        recs = records_by_count.get(rc, [])
        if not recs:
            log.warning('No data records found for %s table (count=%d)',
                         label, rc)
            continue

        if verbose:
            log.info('Table %s: %d records found', label, len(recs))

        var_names = tbl['var_names']
        n_vars = len(var_names)
        var_units = tbl['units']

        # Apply key style mapping
        if key_style == 'eclipse':
            mapped_names = [VDB2VIP.get(v, v) for v in var_names]
            mapped_units = OrderedDict(
                (VDB2VIP.get(k, k), u) for k, u in var_units.items())
        else:
            mapped_names = list(var_names)
            mapped_units = OrderedDict(var_units)

        # Group records by time to identify wells per timestep
        # Records: [TIME, FLAG, var1, var2, ..., varN]
        time_groups = OrderedDict()
        for rec in recs:
            t = float(rec[0])
            if t not in time_groups:
                time_groups[t] = []
            time_groups[t].append(rec[2:2 + n_vars])  # skip TIME, FLAG

        # Determine entity names
        if label == 'well':
            entity_names = well_names
        elif label == 'region':
            entity_names = ['FIELD']
        else:
            entity_names = None

        # Build column names
        timesteps = sorted(time_groups.keys())

        # Determine number of entities per timestep
        n_per_step = [len(time_groups[t]) for t in timesteps]
        max_entities = max(n_per_step) if n_per_step else 0

        # Choose fallback name prefix based on entity type.
        _pfx = {'well': 'WELL', 'region': 'REGION'}.get(label, 'ENTITY')

        if entity_names and len(entity_names) >= max_entities:
            enames = entity_names[:max_entities]
        else:
            enames = [f'{_pfx}_{i + 1}' for i in range(max_entities)]
            if entity_names:
                for i, en in enumerate(entity_names):
                    if i < len(enames):
                        enames[i] = en

        # Build columns: KEY:ENTITY for each variable × entity
        sep = nameSeparator
        columns = []
        col_units = {}
        for vname, mname in zip(var_names, mapped_names):
            unit = mapped_units.get(mname, '')
            for ename in enames:
                col = f'{mname}{sep}{ename}'
                columns.append(col)
                if unit:
                    col_units[col] = unit

        # Build data matrix: rows = timesteps, cols = vars × entities
        n_rows = len(timesteps)
        n_cols = len(columns)
        matrix = np.full((n_rows, n_cols), np.nan, dtype=np.float32)

        for row_idx, t in enumerate(timesteps):
            entity_recs = time_groups[t]
            for ent_idx, vals in enumerate(entity_recs):
                if ent_idx >= max_entities:
                    break
                for var_idx in range(min(n_vars, len(vals))):
                    col_idx = var_idx * max_entities + ent_idx
                    if col_idx < n_cols:
                        matrix[row_idx, col_idx] = vals[var_idx]

        df = pd.DataFrame(matrix, index=timesteps, columns=columns)
        df.index.name = 'TIME'
        frames.append(df)
        all_units.update(col_units)

    # --- Concatenate tables ---
    if not frames:
        log.warning('No data extracted from %s', plot_path)
        return SimDataFrame(units={}, name_separator=nameSeparator,
                            intersection_character=intersectionCharacter)

    if len(frames) == 1:
        combined = frames[0]
    else:
        combined = pd.concat(frames, axis=1)
        # Align on common TIME index
        combined.sort_index(inplace=True)

    # --- Build SimDataFrame ---
    sdf = SimDataFrame(data=combined,
                       units=all_units,
                       index_units='DAYS',
                       name_separator=nameSeparator,
                       intersection_character=intersectionCharacter)

    if verbose:
        log.info('VDB read complete: %d rows × %d columns',
                 len(sdf), len(sdf.columns))

    return sdf
