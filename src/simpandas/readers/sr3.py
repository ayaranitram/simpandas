# -*- coding: utf-8 -*-
"""
CMG SR3 reader (IMEX, GEM, STARS binary results files, HDF5-based).

Reads the ``TimeSeries/*`` groups (WELLS, GROUPS, SECTORS, LAYERS and
SPECIAL HISTORY) of a ``.sr3`` file and returns a ``SimDataFrame`` with
labelled columns and units resolved from the file's own unit tables.

Spatial/grid properties (``SpatialProperties/*``) and static tables
(``Tables/*``, e.g. relative permeability) are out of scope for this reader;
it focuses on the time-series data, the CMG equivalent of Eclipse's
SMSPEC/UNSMRY summary files (see ``simpandas.readers.summary``).

Requires the optional ``h5py`` package (only imported when ``read_sr3`` is
actually called).
"""

__version__ = '0.1.0'
__release__ = 20260828

import logging
import re

import numpy as np
import pandas as pd

from simpandas.frame import SimDataFrame
from simpandas.common.lazy_unyts import unit_product as _unit_product, unit_division as _unit_division, unit_inverse as _unit_inverse

__all__ = ['read_sr3']

log = logging.getLogger(__name__)

# Categories read by default, in a deterministic merge order.
_DEFAULT_CATEGORIES = ('WELLS', 'GROUPS', 'SECTORS', 'LAYERS', 'SPECIAL HISTORY')

# TimeSeries/LAYERS origins look like 'WELLNAME{i,j,k}'
_LAYER_ORIGIN_RE = re.compile(r'^(?P<well>.*)\{(?P<i>-?\d+),(?P<j>-?\d+),(?P<k>-?\d+)\}$')

# Component-indexed variable names look like 'OILCMOLSC(1)'; the
# NameRecordTable stores these using a '$C' placeholder, e.g. 'OILCMOLSC$C'.
_COMPONENT_VAR_RE = re.compile(r'^(?P<base>.+)\(\d+\)$')


def _require_h5py():
    try:
        import h5py
    except ImportError as exc:  # pragma: no cover - exercised only without h5py installed
        raise ImportError(
            "read_sr3() requires the optional 'h5py' package. "
            "Install it with: pip install h5py"
        ) from exc
    return h5py


def _decode(arr):
    """Decode an array of bytes-strings (or pass through already-str arrays)."""
    out = []
    for v in arr:
        if isinstance(v, bytes):
            out.append(v.decode('ascii', errors='replace').strip())
        else:
            out.append(str(v).strip())
    return out


def _build_units_table(h5file):
    """Return {index: output_unit_string} from General/UnitsTable."""
    table = h5file['General/UnitsTable'][:]
    units_by_index = {}
    for row in table:
        idx = int(row['Index'])
        output_unit = row['Output Unit']
        if isinstance(output_unit, bytes):
            output_unit = output_unit.decode('ascii', errors='replace')
        units_by_index[idx] = output_unit.strip()
    return units_by_index


def _parse_dimensionality(code):
    """Parse a NameRecordTable 'Dimensionality' code like '11|-13|'.

    Returns a list of (index, sign) tuples; sign is +1 or -1 (exponent sign).
    """
    tokens = [t for t in code.split('|') if t.strip()]
    parsed = []
    for t in tokens:
        t = t.strip()
        try:
            n = int(t)
        except ValueError:
            continue
        parsed.append((abs(n), -1 if n < 0 else 1))
    return parsed


def _build_keyword_units(h5file):
    """Return {keyword: unit_string_or_None} resolved from the sr3 unit tables."""
    units_by_index = _build_units_table(h5file)
    name_records = h5file['General/NameRecordTable'][:]

    keyword_units = {}
    for row in name_records:
        keyword = row['Keyword']
        keyword = keyword.decode('ascii', errors='replace').strip() if isinstance(keyword, bytes) else str(keyword).strip()
        dim_code = row['Dimensionality']
        dim_code = dim_code.decode('ascii', errors='replace').strip() if isinstance(dim_code, bytes) else str(dim_code).strip()

        if not dim_code:
            keyword_units[keyword] = None
            continue

        unit = None
        for idx, sign in _parse_dimensionality(dim_code):
            factor = units_by_index.get(idx)
            if not factor:
                continue
            if unit is None:
                unit = factor if sign > 0 else _unit_inverse(factor)
            elif sign > 0:
                unit = _unit_product(unit, factor)
            else:
                unit = _unit_division(unit, factor)
        keyword_units[keyword] = unit

    return keyword_units


def _build_master_dates(h5file):
    """Return a dict {master_index: pandas.Timestamp} and a parallel days array.

    General/MasterTimeTable rows are (Index, Offset in days, Date), where
    Date is encoded as YYYYMMDD[.fraction_of_day].
    """
    mt = h5file['General/MasterTimeTable'][:]
    indices = mt['Index'].astype(int)
    days = mt['Offset in days'].astype(float)
    date_raw = mt['Date'].astype(float)

    whole = np.floor(date_raw)
    frac = date_raw - whole
    whole_int = whole.astype(np.int64)
    year = whole_int // 10000
    month = (whole_int // 100) % 100
    day = whole_int % 100
    seconds = np.round(frac * 86400).astype(np.int64)

    dates = pd.to_datetime(
        {'year': year, 'month': month, 'day': day},
        errors='coerce',
    ) + pd.to_timedelta(seconds, unit='s')

    date_by_index = dict(zip(indices.tolist(), dates))
    days_by_index = dict(zip(indices.tolist(), days.tolist()))
    return date_by_index, days_by_index


def _resolve_unit(var, keyword_units):
    """Look up the unit for *var*, falling back to the '$C' component form."""
    if var in keyword_units:
        return keyword_units[var]
    m = _COMPONENT_VAR_RE.match(var)
    if m:
        return keyword_units.get(m.group('base') + '$C')
    return None


def _read_category(h5file, category, keyword_units, date_by_index, sep):
    """Read one TimeSeries/<category> group into a (DataFrame, units_dict) pair."""
    group_path = f'TimeSeries/{category}'
    if group_path not in h5file:
        return None

    group = h5file[group_path]
    required = ('Origins', 'Variables', 'Data', 'Timesteps')
    if not all(name in group for name in required):
        log.warning("Skipping incomplete TimeSeries/%s group (missing datasets).", category)
        return None

    origins = _decode(group['Origins'][:])
    variables = _decode(group['Variables'][:])
    data = group['Data'][:]
    timesteps = group['Timesteps'][:]

    dates = [date_by_index.get(int(t)) for t in timesteps]

    columns = []
    units_dict = {}
    series_list = []
    for o_idx, origin in enumerate(origins):
        if not origin:
            continue

        if category == 'LAYERS':
            m = _LAYER_ORIGIN_RE.match(origin)
            if m:
                origin_label = f"{m.group('well')}{sep}{m.group('i')},{m.group('j')},{m.group('k')}"
            else:
                origin_label = origin
        else:
            origin_label = origin

        for v_idx, var in enumerate(variables):
            colname = f'{var}{sep}{origin_label}'
            columns.append(colname)
            series_list.append(data[:, v_idx, o_idx])
            unit = _resolve_unit(var, keyword_units)
            if unit:
                units_dict[colname] = unit

    if not columns:
        return None

    arr = np.column_stack(series_list)
    df = pd.DataFrame(arr, index=pd.DatetimeIndex(dates, name='DATE'), columns=columns)
    return df, units_dict


def read_sr3(path,
             categories=None,
             merge=True,
             nameSeparator=':',
             intersectionCharacter=None,
             autoAppend=False,
             operatePerName=False,
             verbose=False):
    """
    Read a CMG SR3 file (IMEX, GEM, STARS) into SimDataFrame(s).

    Parameters
    ----------
    path : str or path-like
        Path to the ``.sr3`` file.
    categories : iterable of str or None
        Which ``TimeSeries`` categories to read. One or more of
        ``'WELLS'``, ``'GROUPS'``, ``'SECTORS'``, ``'LAYERS'``,
        ``'SPECIAL HISTORY'``. ``None`` (default) reads every category
        present in the file.
    merge : bool, default True
        If ``True``, return a single ``SimDataFrame`` with all requested
        categories outer-joined on the DATE index (columns are named
        ``KEYWORD:ORIGIN``, e.g. ``OILRATSC:PROD``).
        If ``False``, return a ``dict`` of ``{category: SimDataFrame}``.
    nameSeparator, intersectionCharacter, autoAppend, operatePerName, verbose
        Forwarded to the ``SimDataFrame`` constructor.

    Returns
    -------
    SimDataFrame or dict[str, SimDataFrame]

    Notes
    -----
    Units are resolved from the file's own ``General/UnitsTable`` and
    ``General/NameRecordTable`` (dimensionality formulas such as
    ``'11|-13|'`` meaning "Well Liquid Volume / Well Rate Time" -> ``bbl/day``),
    so the returned units reflect whatever output unit system (FIELD/SI/etc.)
    the simulation was run with.

    Grid/spatial properties (``SpatialProperties/*``) are not read by this
    function; it only covers the time-series (SUMMARY-equivalent) data.
    """
    h5py = _require_h5py()

    sep = nameSeparator if nameSeparator else ':'
    requested = [c.upper() for c in categories] if categories else list(_DEFAULT_CATEGORIES)

    with h5py.File(str(path), 'r') as h5file:
        keyword_units = _build_keyword_units(h5file)
        date_by_index, _days_by_index = _build_master_dates(h5file)

        results = {}
        for category in requested:
            out = _read_category(h5file, category, keyword_units, date_by_index, sep)
            if out is not None:
                results[category] = out

    if not results:
        raise ValueError(f"No requested TimeSeries categories found in '{path}'.")

    def _to_sdf(df, units_dict):
        return SimDataFrame(
            data=df,
            units=units_dict,
            index_units='date',
            name_separator=sep,
            intersection_character=intersectionCharacter,
            auto_append=autoAppend,
            operate_per_name=operatePerName,
            verbose=verbose,
            source_path=str(path),
        )

    if not merge:
        return {category: _to_sdf(df, units_dict) for category, (df, units_dict) in results.items()}

    merged_df = None
    merged_units = {}
    for category in requested:
        if category not in results:
            continue
        df, units_dict = results[category]
        merged_units.update(units_dict)
        if merged_df is None:
            merged_df = df.sort_index()
        else:
            overlap = set(merged_df.columns) & set(df.columns)
            if overlap:
                log.warning(
                    "Duplicate column name(s) across TimeSeries categories, keeping first occurrence: %s",
                    sorted(overlap),
                )
                df = df.drop(columns=list(overlap))
            merged_df = merged_df.join(df.sort_index(), how='outer')

    merged_df = merged_df.sort_index()
    return _to_sdf(merged_df, merged_units)
