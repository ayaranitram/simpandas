# -*- coding: utf-8 -*-
"""
CMG SR3 writer (IMEX, GEM, STARS binary results files, HDF5-based).

Writes a ``SimDataFrame`` as the ``General/*`` tables and ``TimeSeries/*``
groups of a ``.sr3`` file.  The layout mirrors a GEM 2022.10 results file;
grid properties (``SpatialProperties``) and static tables are not written.

Files produced here are read back with ``simpandas.read_sr3``.
"""

__version__ = '0.93.0'
__release__ = 20261014

__all__ = ['write_sr3']

import logging
import math
import re
import uuid
from collections import Counter

import numpy as np
import pandas as pd

from simpandas.common.lazy_unyts import convertible as _convertible, convert_for_SimPandas as _converter
from simpandas.readers.sr3 import _unit_from_dimensionality, _COMPONENT_VAR_RE, _DEFAULT_CATEGORIES
from simpandas.writers import _sr3_catalog as _cat

log = logging.getLogger(__name__)

_LAYER_IJK_RE = re.compile(r'^-?\d+,-?\d+,-?\d+$')
_COMPONENT_NUM_RE = re.compile(r'\((\d+)\)$')
_NO_PARENT = 4294967295
_MAX_VARIABLE_LEN = 14
_MAX_KEYWORD_LEN = 23
_MAX_ORIGIN_LEN = 100

# Compound dtypes copied from a real SR3 file (explicit offsets/itemsize as written by CMG).
_DT_UNITS = np.dtype([('Index', 'u1'), ('Dimensionality', 'S28'), ('Internal Unit', 'S20'), ('Output Unit', 'S20')])
_DT_UNIT_CONV = np.dtype({'names': ['Dimensionality', 'Unit Name', 'Gain', 'Offset'],
                          'formats': ['i1', 'S10', '<f8', '<f8'], 'offsets': [0, 1, 16, 24], 'itemsize': 32})
_DT_COMPONENT = np.dtype({'names': ['Name'], 'formats': ['S20'], 'offsets': [4], 'itemsize': 24})
_DT_HISTORY = np.dtype({'names': ['Timestep', 'Category', 'Context', 'Action'],
                        'formats': ['<u4', '<i4', 'S50', '<i4'], 'offsets': [0, 4, 12, 8], 'itemsize': 64})
_DT_MASTER_TIME = np.dtype({'names': ['Index', 'Offset in days', 'Date'],
                            'formats': ['<u4', '<f8', '<f8'], 'offsets': [0, 8, 16], 'itemsize': 24})
_DT_NAME_RECORD = np.dtype({
    'names': ['Keyword', 'Name', 'Long Name', 'Dimensionality', 'Propagates', 'Formula Number',
              'Formula Parameters', 'Start Hue', 'End Hue', 'Zero Por', 'Type', 'Packing', 'Size'],
    'formats': ['S23', 'S79', 'S96', 'S18', 'S4', '<u4', 'S152', 'u1', 'u1', 'u1', 'S4', 'S4', 'S9'],
    'offsets': [193, 0, 79, 175, 233, 240, 244, 396, 397, 398, 216, 220, 224], 'itemsize': 400})
_DT_WELL = np.dtype({'names': ['Timestep', 'Number', 'Name', 'Parent', 'Fraction'],
                     'formats': ['<u4', '<u4', 'S101', 'S101', '<f8'],
                     'offsets': [216, 0, 4, 105, 208], 'itemsize': 224})
_DT_GROUP = np.dtype({'names': ['Timestep', 'Number', 'Name', 'Parent', 'Type', 'Type Number'],
                      'formats': ['<u4', '<u4', 'S101', 'S101', '<i4', '<u4'],
                      'offsets': [216, 0, 4, 105, 208, 212], 'itemsize': 220})
_DT_LAYER = np.dtype({
    'names': ['Timestep', 'Number', 'Name', 'Parent', 'Connect To', 'Type', 'X Entry', 'Y Entry', 'Z Entry',
              'X Exit', 'Y Exit', 'Z Exit', 'Perf Length', 'CSIndex'],
    'formats': ['<u4', '<u4', 'S101', 'S101', '<u4', '<i4', '<f8', '<f8', '<f8', '<f8', '<f8', '<f8', '<f8', '<u4'],
    'offsets': [272, 0, 4, 105, 208, 212, 216, 224, 232, 240, 248, 256, 264, 276], 'itemsize': 288})


def _b(text):
    return str(text).encode('ascii', errors='replace')


def _write_table(parent, name, dtype, rows, title, extra_attrs=None):
    arr = np.array(rows, dtype=dtype) if rows else np.zeros(0, dtype=dtype)
    ds = parent.create_dataset(name, data=arr, chunks=(500,), maxshape=(None,),
                               compression='gzip', compression_opts=1)
    ds.attrs['CLASS'] = np.bytes_(b'TABLE')
    for i, field in enumerate(dtype.names):
        ds.attrs['FIELD_%d_NAME' % i] = np.bytes_(_b(field))
    ds.attrs['TITLE'] = np.bytes_(_b(title))
    ds.attrs['VERSION'] = np.bytes_(b'3.0')
    for key, value in (extra_attrs or {}).items():
        ds.attrs[key] = np.bytes_(_b(value))
    return ds


def _encode_date(ts):
    """CMG date encoding: YYYYMMDD plus the fraction of the day."""
    seconds = ts.hour * 3600 + ts.minute * 60 + ts.second + ts.microsecond / 1e6
    return ts.year * 10000 + ts.month * 100 + ts.day + seconds / 86400.0


def _column_units(sdf, columns):
    """Return {column: unit_string} from the SimDataFrame units, whatever their container."""
    try:
        raw = sdf.units
    except Exception:
        return {}
    if isinstance(raw, dict):
        pairs = raw.items()
    elif hasattr(raw, 'to_list'):
        pairs = zip(columns, raw.to_list())
    elif isinstance(raw, (list, tuple)):
        pairs = zip(columns, raw)
    elif isinstance(raw, str) and len(columns) == 1:
        pairs = [(columns[0], raw)]
    else:
        return {}
    return {c: str(u).strip() for c, u in pairs if u not in (None, '') and str(u).strip()}


def _split_column(col, sep):
    """Split 'VAR:ORIGIN' (or 'VAR:WELL:i,j,k') into (variable, origin, is_layer)."""
    parts = str(col).split(sep)
    var = parts[0]
    if len(parts) == 1:
        return var, 'SPVALS', False
    if len(parts) >= 3 and _LAYER_IJK_RE.match(parts[-1]):
        well = sep.join(parts[1:-1])
        return var, '%s{%s}' % (well, parts[-1]), True
    return var, sep.join(parts[1:]), False


def _catalog_key(var):
    m = _COMPONENT_VAR_RE.match(var)
    return m.group('base') + '$C' if m else var


def _classify_origin(origin, keys, forced):
    if origin in forced:
        return forced[origin]
    votes = Counter()
    for key in keys:
        seen = _cat.CATEGORIES.get(key)
        if seen and len(seen) == 1:
            votes[seen[0]] += 1
    if votes:
        return max(_DEFAULT_CATEGORIES, key=lambda c: votes.get(c, 0))
    return 'SPECIAL HISTORY' if origin == 'SPVALS' else 'WELLS'


class _UnitBook:
    """UnitsTable / UnitConversionTable contents plus unit -> dimensionality lookups."""

    def __init__(self, output_units):
        self.rows = [list(r) for r in _cat.UNITS_FIELD]
        self.conversions = [tuple(r) for r in _cat.UNIT_CONVERSION]
        for key, unit in (output_units or {}).items():
            row = self._find_row(key)
            if row is None:
                raise ValueError("Unknown dimensionality '%s' in output_units." % (key,))
            row[3] = str(unit)
            self._ensure_conversion(row, str(unit))

    def _find_row(self, key):
        for row in self.rows:
            if row[0] == key or str(row[1]).lower() == str(key).lower():
                return row
        return None

    def _ensure_conversion(self, row, unit):
        if any(c[0] == row[0] and c[1] == unit for c in self.conversions):
            return
        try:
            offset = float(_converter(0.0, unit, row[2]))
            gain = float(_converter(1.0, unit, row[2])) - offset
        except Exception:
            log.warning("Cannot derive conversion factors for unit '%s'; CMG may not recognise it.", unit)
            return
        self.conversions.append((row[0], unit, gain, offset))

    @property
    def by_index(self):
        return {r[0]: r[3] for r in self.rows}

    def _match(self, unit):
        for idx, _dim, _internal, output in self.rows:
            if output == unit:
                return idx
        return None

    def code_for_unit(self, unit):
        """Return (dimensionality_code, target_unit) for a unit string, adding a custom dimension if needed."""
        idx = self._match(unit)
        if idx is not None:
            return '%d|' % idx, unit
        if '/' in unit:
            num, den = unit.split('/', 1)
            i_num, i_den = self._match(num), self._match(den)
            if i_num is not None and i_den is not None:
                return '%d|-%d|' % (i_num, i_den), unit
        new_idx = max(r[0] for r in self.rows) + 1
        self.rows.append([new_idx, 'Custom: %s' % unit, unit, unit])
        self.conversions.append((new_idx, unit, 1.0, 0.0))
        log.warning("Unit '%s' has no CMG dimensionality; written as custom dimension %d.", unit, new_idx)
        return '%d|' % new_idx, unit


def write_sr3(sdf, path, simulator='GEM', simulator_version='2022.10', titles=None, case_id="'CASE 1'",
              categories=None, components=None, output_units=None, dimens=None, start_date=None):
    """
    Write a SimDataFrame (or SimSeries) to a CMG ``.sr3`` file.

    Columns must be named ``KEYWORD:ORIGIN`` (e.g. ``OILRATSC:PROD``); layer columns
    ``KEYWORD:WELL:i,j,k`` go to ``TimeSeries/LAYERS`` and columns without an origin
    are stored under the ``SPVALS`` origin of ``SPECIAL HISTORY``.

    Parameters
    ----------
    sdf : SimDataFrame or SimSeries
        Data to write.  The index must be a ``DatetimeIndex`` (or numeric days
        when *start_date* is given).
    path : str or path-like
        Destination ``.sr3`` file.  Overwritten if it exists.
    simulator, simulator_version : str
        Written to the root attributes of the file.
    titles : sequence of str, optional
        Up to three case titles.
    case_id : str
        ``Case ID`` root attribute.
    categories : dict, optional
        ``{origin: category}`` overrides, with category one of ``WELLS``,
        ``GROUPS``, ``SECTORS``, ``SPECIAL HISTORY``.  By default the category
        is inferred from the CMG keywords found for each origin, falling back to
        ``WELLS``; ``sdf.meta['sr3']['origin_category']`` (set by ``read_sr3``) is used first.
    components : sequence of str, optional
        Component names for ``KEYWORD(n)`` columns (``ComponentTable``).
    output_units : dict, optional
        Override the output unit of a CMG dimensionality, e.g. ``{'Pressure': 'kPa'}``.
        Data are converted to the output units of the file (FIELD by default).
    dimens : sequence of 3 ints, optional
        Grid size ``[nx, ny, nz]`` used to compute the layer cell index.
    start_date : str or datetime-like, optional
        Date of day 0 when the index is numeric days.

    Returns
    -------
    None
    """
    import h5py

    if hasattr(sdf, 'as_dataframe'):
        df = sdf.as_dataframe()
    elif hasattr(sdf, 'as_pandas'):
        result = sdf.as_pandas()
        df = result.to_frame() if isinstance(result, pd.Series) else result
    else:
        df = pd.DataFrame(sdf)
    df = df.copy()

    sep = getattr(sdf, 'name_separator', ':') or ':'
    meta = getattr(sdf, 'meta', None)
    sr3_meta = meta.get('sr3', {}) if isinstance(meta, dict) else {}

    # ---- time axis -------------------------------------------------------
    if isinstance(df.index, pd.DatetimeIndex):
        dates = df.index
    elif start_date is not None:
        dates = pd.Timestamp(start_date) + pd.to_timedelta(np.asarray(df.index, dtype=float), unit='D')
    else:
        raise ValueError("The index must be a DatetimeIndex, or numeric days together with 'start_date'.")
    keep = ~pd.isna(dates)
    df, dates = df.loc[keep], pd.DatetimeIndex(dates[keep])
    order = np.argsort(dates.values, kind='stable')
    df, dates = df.iloc[order], dates[order]
    dup = dates.duplicated(keep='last')
    if dup.any():
        log.warning("Dropping %d duplicated timestamps (keeping the last).", int(dup.sum()))
        df, dates = df.loc[~dup], dates[~dup]
    if len(df) == 0:
        raise ValueError("Nothing to write: the data has no valid timestamps.")

    # ---- numeric columns -------------------------------------------------
    units = _column_units(sdf, list(df.columns))
    values = {}
    for col in df.columns:
        try:
            values[col] = pd.to_numeric(df[col], errors='raise').to_numpy(dtype=float)
        except (TypeError, ValueError):
            log.warning("Skipping non-numeric column '%s'.", col)
    if not values:
        raise ValueError("Nothing to write: no numeric columns.")

    # ---- columns -> (variable, origin, category) -------------------------
    parsed = {}
    seen_pairs = set()
    for col in values:
        var, origin, is_layer = _split_column(col, sep)
        if (var, origin) in seen_pairs:
            log.warning("Duplicate variable/origin '%s' for column '%s'; skipped.", (var, origin), col)
            continue
        seen_pairs.add((var, origin))
        if len(var) > _MAX_VARIABLE_LEN:
            log.warning("Variable name '%s' is longer than %d characters.", var, _MAX_VARIABLE_LEN)
        if len(origin) > _MAX_ORIGIN_LEN:
            raise ValueError("Origin name '%s' is longer than %d characters." % (origin, _MAX_ORIGIN_LEN))
        parsed[col] = (var, origin, is_layer)

    forced = dict(sr3_meta.get('origin_category', {}))
    forced.update({str(k): str(v).upper() for k, v in (categories or {}).items()})
    for cat in forced.values():
        if cat not in _DEFAULT_CATEGORIES or cat == 'LAYERS':
            raise ValueError("Invalid category '%s'; use one of WELLS, GROUPS, SECTORS, SPECIAL HISTORY." % cat)

    keys_by_origin = {}
    for var, origin, is_layer in parsed.values():
        if not is_layer:
            keys_by_origin.setdefault(origin, []).append(_catalog_key(var))
    origin_cat = {o: _classify_origin(o, k, forced) for o, k in keys_by_origin.items()}

    by_category = {c: [] for c in _DEFAULT_CATEGORIES}
    for col, (var, origin, is_layer) in parsed.items():
        by_category['LAYERS' if is_layer else origin_cat[origin]].append((col, var, origin))

    # ---- units / dimensionality per keyword ------------------------------
    book = _UnitBook(output_units)
    cols_by_key = {}
    for col, (var, _o, _l) in parsed.items():
        cols_by_key.setdefault(_catalog_key(var), []).append(col)

    dim_code = {}
    for key, cols in cols_by_key.items():
        rec = _cat.KEYWORDS.get(key)
        if rec is not None:
            code = rec[2]
            target = _unit_from_dimensionality(code, book.by_index) if code else None
        else:
            src = next((units[c] for c in cols if c in units), None)
            code, target = book.code_for_unit(src) if src else ('', None)
        dim_code[key] = code
        if not target:
            continue
        for c in cols:
            src = units.get(c)
            if not src or src == target:
                continue
            if _convertible(src, target):
                values[c] = np.asarray(_converter(values[c], src, target), dtype=float)
            else:
                log.warning("Column '%s' [%s] is not convertible to %s [%s]; written unconverted.",
                            c, src, key, target)

    # ---- file ------------------------------------------------------------
    n_time = len(dates)
    start = dates[0]
    offsets = (dates - start).total_seconds().to_numpy() / 86400.0
    history = []

    if dimens is not None:
        nx, ny = int(dimens[0]), int(dimens[1])
    else:
        ijk = [tuple(int(n) for n in o.rsplit('{', 1)[1].rstrip('}').split(','))
               for _c, _v, o in by_category['LAYERS']]
        nx = max([t[0] for t in ijk] or [1])
        ny = max([t[1] for t in ijk] or [1])

    with h5py.File(str(path), 'w') as f:
        attrs = {'Case ID': case_id, 'File': '1', 'SR3 Version': '1.0.8', 'Simulator Name': simulator,
                 'Simulator Version': simulator_version, 'Title 1': "'SimPandas export'", 'Title 2': "''",
                 'Title 3': "''", 'id': str(uuid.uuid4())}
        for k in ('SR3 Version', 'File', 'Title 1', 'Title 2', 'Title 3'):
            if k in sr3_meta.get('attrs', {}):
                attrs[k] = sr3_meta['attrs'][k]
        for i, t in enumerate(titles or [], start=1):
            if i <= 3:
                attrs['Title %d' % i] = "'%s'" % t
        for k, v in attrs.items():
            f.attrs[k] = np.bytes_(_b(v))

        general = f.create_group('General')
        f.create_group('SpatialProperties')
        f.create_group('Tables')
        series = f.create_group('TimeSeries')

        for cat in _DEFAULT_CATEGORIES:
            members = by_category[cat]
            if not members:
                continue
            origins, variables = [], []
            for _c, var, origin in members:
                if origin not in origins:
                    origins.append(origin)
                if var not in variables:
                    variables.append(var)
            o_idx = {o: i for i, o in enumerate(origins)}
            v_idx = {v: i for i, v in enumerate(variables)}

            has_data = np.zeros(n_time, dtype=bool)
            for col, _v, _o in members:
                has_data |= ~np.isnan(values[col])
            steps = np.flatnonzero(has_data)
            if len(steps) == 0:
                steps = np.array([0])

            data = np.full((len(steps), len(variables), len(origins)), np.nan)
            for col, var, origin in members:
                data[:, v_idx[var], o_idx[origin]] = values[col][steps]

            grp = series.create_group(cat)
            grp.create_dataset('Data', data=data, chunks=(1, len(variables), len(origins)),
                               compression='gzip', compression_opts=1)
            grp.create_dataset('Origins', data=np.array([_b(o) for o in origins], dtype='S%d' % _MAX_ORIGIN_LEN),
                               chunks=(len(origins),), compression='gzip', compression_opts=1)
            grp.create_dataset('Timesteps', data=steps.astype('<u4'), chunks=(1000,), maxshape=(None,))
            width = max(len(v) for v in variables)
            grp.create_dataset('Variables', data=np.array([_b(v) for v in variables], dtype='S%d' % width),
                               chunks=(max(1, int(math.ceil(len(variables) / 10.0))),),
                               compression='gzip', compression_opts=1)

            if cat == 'WELLS':
                well_rows = [(0, i + 1, _b(o), b'', 1.0) for i, o in enumerate(origins)]
                _write_table(grp, 'WellTable', _DT_WELL, well_rows, 'WellTable')
            elif cat == 'GROUPS':
                group_rows = [(0, i + 1, _b(o), b'', 0, i + 1) for i, o in enumerate(origins)]
                _write_table(grp, 'GroupTable', _DT_GROUP, group_rows, 'GroupTable')
            elif cat == 'LAYERS':
                layer_rows = []
                last_number = {}
                for i, o in enumerate(origins):
                    well, cell = o.rsplit('{', 1)
                    ci, cj, ck = (int(n) for n in cell.rstrip('}').split(','))
                    number = i + 1
                    layer_rows.append((0, number, _b('%d,%d,%d' % (ci, cj, ck)), _b(well),
                                       last_number.get(well, _NO_PARENT), 0,
                                       np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
                                       ci + (cj - 1) * nx + (ck - 1) * nx * ny))
                    last_number[well] = number
                _write_table(grp, 'LayerTable', _DT_LAYER, layer_rows, 'LayerTable')

            history.append((0, 0, _b(cat), 1))
            history.extend((int(s), 0, _b(cat), 0) for s in steps)

        # General tables -----------------------------------------------------
        master = [(i, float(offsets[i]), _encode_date(dates[i])) for i in range(n_time)]
        _write_table(general, 'MasterTimeTable', _DT_MASTER_TIME, master, 'MasterTimeTable')
        _write_table(general, 'HistoryTable', _DT_HISTORY, sorted(history, key=lambda r: r[0]), 'HistoryTable')
        _write_table(general, 'UnitsTable', _DT_UNITS,
                     [(r[0], _b(r[1]), _b(r[2]), _b(r[3])) for r in book.rows], 'UnitsTable')
        _write_table(general, 'UnitConversionTable', _DT_UNIT_CONV,
                     [(c[0], _b(c[1]), c[2], c[3]) for c in book.conversions], 'Unit Conversion Records')

        name_rows = []
        for key in sorted(dim_code):
            if len(key) > _MAX_KEYWORD_LEN:
                log.warning("Keyword '%s' is longer than %d characters.", key, _MAX_KEYWORD_LEN)
            rec = _cat.KEYWORDS.get(key)
            if rec is None:
                rec = (key, key, dim_code[key], '', 0, '', 0, 0, 0, 'r', ' ', '1')
            name_rows.append((_b(key), _b(rec[0]), _b(rec[1]), _b(rec[2]), _b(rec[3]), rec[4], _b(rec[5]),
                              rec[6], rec[7], rec[8], _b(rec[9]), _b(rec[10]), _b(rec[11])))
        _write_table(general, 'NameRecordTable', _DT_NAME_RECORD, name_rows, 'Name Records')

        n_comp = 0
        for var, _o, _l in parsed.values():
            m = _COMPONENT_NUM_RE.search(var)
            if m:
                n_comp = max(n_comp, int(m.group(1)))
        names = list(components or sr3_meta.get('components', []))
        if n_comp:
            names = (names + ['COMP%d' % i for i in range(len(names) + 1, n_comp + 1)])[:max(n_comp, len(names))]
            _write_table(general, 'ComponentTable', _DT_COMPONENT, [(_b(n),) for n in names], 'ComponentTable',
                         {'DIMENSIONS': '%d  %d  %d  %d' % ((len(names),) * 4)})
