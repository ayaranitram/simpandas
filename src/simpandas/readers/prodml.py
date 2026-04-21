# -*- coding: utf-8 -*-
"""
PRODML reader for SimPandas.

Reads Energistics PRODML XML files and extracts tabular production data
into ``SimDataFrame`` objects.  Supports:

* **Production volume reports** (``productVolume`` / ``productionVolume``)
* **Time series** (``timeSeries``)
* **Well test** results (``wellTest``)

The reader auto-detects the PRODML version (1.x / 2.x) by inspecting
the root element's namespace.  It uses only the standard-library
``xml.etree.ElementTree`` parser — no external dependencies.
"""

__version__ = '0.1.0'
__release__ = 20260418

import logging
import os
import re
from collections import OrderedDict
from xml.etree import ElementTree

import numpy as np
import pandas as pd

from simpandas.frame import SimDataFrame

__all__ = ['read_prodml']

log = logging.getLogger(__name__)

# Common PRODML namespaces (the reader also auto-detects from the root tag)
_NS_PRODML_V2 = 'http://www.energistics.org/energyml/data/prodmlv2'
_NS_PRODML_V1 = 'http://www.prodml.org/schemas/1series'
_NS_EML = 'http://www.energistics.org/energyml/data/commonv2'

# ---------------------------------------------------------------------------
# Namespace helpers
# ---------------------------------------------------------------------------

def _detect_ns(root):
    """Return the namespace URI from the root element's tag."""
    m = re.match(r'\{(.+?)\}', root.tag)
    return m.group(1) if m else ''


def _ns_tag(ns, local):
    """Build a fully qualified tag ``{ns}local``."""
    if ns:
        return f'{{{ns}}}{local}'
    return local


def _findall(elem, ns, path):
    """Find all children matching *path* with or without namespace."""
    results = elem.findall(_ns_tag(ns, path))
    if not results:
        # Try without namespace (some files omit it)
        results = elem.findall(path)
    return results


def _find(elem, ns, path):
    """Find first child matching *path* with or without namespace."""
    result = elem.find(_ns_tag(ns, path))
    if result is None:
        result = elem.find(path)
    return result


def _text(elem, ns, path, default=''):
    """Get text content of a child element."""
    child = _find(elem, ns, path)
    if child is not None and child.text:
        return child.text.strip()
    return default


def _attr(elem, key, default=''):
    """Get attribute value, trying both 'key' and namespace-qualified forms."""
    return elem.get(key, default)

# ---------------------------------------------------------------------------
# Production volume parsing
# ---------------------------------------------------------------------------

def _extract_period_quantities(period, ns):
    """Extract quantity values from a Period element, return (row_dict, units_dict)."""
    row = {}
    units = {}
    for qty_tag in ('Volume', 'volume',
                    'VolumeStd', 'volumeStd',
                    'Rate', 'rate',
                    'Mass', 'mass',
                    'Density', 'density',
                    'Pressure', 'pressure',
                    'Temperature', 'temperature'):
        for qe in _findall(period, ns, qty_tag):
            val_text = qe.text
            uom = qe.get('uom', '')
            product = qe.get('product', '')
            if val_text is not None:
                try:
                    val = float(val_text.strip())
                except ValueError:
                    continue
                col = qty_tag.lower()
                if product:
                    col = f'{col}_{product}'
                row[col] = val
                if uom:
                    units[col] = uom
    return row, units


def _period_dates(period, ns):
    """Extract start/end dates from a Period element (attrs or children)."""
    start = (_attr(period, 'start', '') or
             _text(period, ns, 'DateStart') or
             _text(period, ns, 'dTimStart') or
             _text(period, ns, 'startDate') or '')
    end = (_attr(period, 'end', '') or
           _text(period, ns, 'DateEnd') or
           _text(period, ns, 'dTimEnd') or
           _text(period, ns, 'endDate') or '')
    return start, end


def _parse_production_volumes(root, ns, name_sep):
    """Extract production volumes → DataFrame rows."""
    rows = []
    units_map = OrderedDict()

    # Collect ProductVolume containers – they may be children of root OR
    # root itself (when root tag *is* ProductVolume).
    containers = []
    root_local = re.sub(r'\{.*?\}', '', root.tag)
    if root_local.lower() in ('productvolume', 'productionvolume'):
        containers.append(root)
    for vol_tag in ('ProductVolume', 'productVolume',
                    'ProductionVolume', 'productionVolume'):
        containers.extend(_findall(root, ns, vol_tag))

    for pvol in containers:
        facility_top = (_text(pvol, ns, 'Installation/Name') or
                        _text(pvol, ns, 'name') or
                        _attr(pvol, 'name', '') or
                        _attr(pvol, 'uid', 'Unknown'))

        # --- path 1: ProductVolume → Product → Period ---
        for prod_tag in ('Product', 'product'):
            for product in _findall(pvol, ns, prod_tag):
                product_name = (_text(product, ns, 'Name') or
                                _text(product, ns, 'name') or
                                _attr(product, 'name', '') or
                                _attr(product, 'uid', ''))
                flow_kind = (_text(product, ns, 'Kind') or
                             _text(product, ns, 'kind') or '')

                for per_tag in ('Period', 'period'):
                    for period in _findall(product, ns, per_tag):
                        start, end = _period_dates(period, ns)
                        row = {'facility': facility_top,
                               'product': product_name,
                               'kind': flow_kind,
                               'start': start, 'end': end}
                        qty_row, qty_units = _extract_period_quantities(period, ns)
                        row.update(qty_row)
                        units_map.update(qty_units)
                        if len(row) > 5:
                            rows.append(row)

        # --- path 2: ProductVolume → Facility → Period ---
        for fac_tag in ('Facility', 'facility', 'Flow', 'flow'):
            for fac in _findall(pvol, ns, fac_tag):
                fac_name = (_text(fac, ns, 'Name') or
                            _text(fac, ns, 'name') or
                            _attr(fac, 'name', '') or
                            _attr(fac, 'uid', '') or
                            facility_top)
                for per_tag in ('Period', 'period'):
                    for period in _findall(fac, ns, per_tag):
                        start, end = _period_dates(period, ns)
                        row = {'facility': fac_name,
                               'start': start, 'end': end}
                        qty_row, qty_units = _extract_period_quantities(period, ns)
                        row.update(qty_row)
                        units_map.update(qty_units)
                        if len(row) > 2 and qty_row:
                            rows.append(row)

        # --- path 3: periods directly under ProductVolume ---
        for per_tag in ('Period', 'period'):
            for period in _findall(pvol, ns, per_tag):
                start, end = _period_dates(period, ns)
                row = {'facility': facility_top,
                       'start': start, 'end': end}
                qty_row, qty_units = _extract_period_quantities(period, ns)
                row.update(qty_row)
                units_map.update(qty_units)
                if len(row) > 2 and qty_row:
                    rows.append(row)

    return rows, units_map


# ---------------------------------------------------------------------------
# Time series parsing
# ---------------------------------------------------------------------------

def _parse_time_series(root, ns, name_sep):
    """Extract time-series data → DataFrame rows."""
    rows = []
    units_map = OrderedDict()

    for ts_tag in ('TimeSeries', 'timeSeries'):
        for ts in _findall(root, ns, ts_tag):
            key = (_text(ts, ns, 'Key') or _text(ts, ns, 'keyword') or
                   _attr(ts, 'uid', '') or 'VALUE')
            uom = (_text(ts, ns, 'Unit') or _text(ts, ns, 'uom') or
                   _attr(ts, 'uom', ''))
            well = (_text(ts, ns, 'WellName') or
                    _text(ts, ns, 'nameWell') or '')
            comment = _text(ts, ns, 'Comment') or ''

            col_name = f'{key}{name_sep}{well}' if well else key
            if uom:
                units_map[col_name] = uom

            for val_tag in ('Value', 'value', 'DataValue', 'dataValue'):
                for ve in _findall(ts, ns, val_tag):
                    dt = (ve.get('dateTime', '') or
                          ve.get('dTim', '') or '')
                    val_text = ve.text
                    if val_text is not None and dt:
                        try:
                            rows.append({
                                'datetime': dt,
                                'column': col_name,
                                'value': float(val_text.strip())
                            })
                        except ValueError:
                            pass

    return rows, units_map


# ---------------------------------------------------------------------------
# Well test parsing
# ---------------------------------------------------------------------------

def _parse_well_tests(root, ns, name_sep):
    """Extract well-test results → DataFrame rows."""
    rows = []
    units_map = OrderedDict()

    for wt_tag in ('WellTest', 'wellTest'):
        for wt in _findall(root, ns, wt_tag):
            well = (_text(wt, ns, 'WellName') or
                    _text(wt, ns, 'nameWell') or
                    _attr(wt, 'uidWell', ''))
            test_date = (_text(wt, ns, 'TestDate') or
                         _text(wt, ns, 'dTimTest') or
                         _text(wt, ns, 'testDate') or '')

            row = {'well': well, 'test_date': test_date}

            # Production test results
            for res_tag in ('ProductionTestResults',
                            'productionTestResults',
                            'TestResult', 'testResult'):
                for res in _findall(wt, ns, res_tag):
                    for child in res:
                        tag = re.sub(r'\{.*?\}', '', child.tag)
                        if child.text is not None:
                            try:
                                val = float(child.text.strip())
                                uom = child.get('uom', '')
                                row[tag] = val
                                if uom:
                                    units_map[tag] = uom
                            except ValueError:
                                row[tag] = child.text.strip()

            if len(row) > 2:
                rows.append(row)

    return rows, units_map


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_prodml(filepath,
                sections='auto',
                nameSeparator=':',
                intersectionCharacter='&',
                verbose=False):
    """
    Read a PRODML XML file into a ``SimDataFrame``.

    Parameters
    ----------
    filepath : str or path-like
        Path to a ``.xml`` PRODML file.
    sections : str or list[str]
        Which data sections to extract:

        * ``'auto'`` (default) – detect and read all available sections.
        * ``'volumes'`` – production volume reports only.
        * ``'timeseries'`` – time-series data only.
        * ``'welltests'`` – well-test results only.
    nameSeparator : str
        Separator between key and well/entity in column names.
    intersectionCharacter : str
        Intersection character for ``SimDataFrame``.
    verbose : bool
        Log progress messages.

    Returns
    -------
    SimDataFrame
    """
    filepath = str(filepath)
    tree = ElementTree.parse(filepath)
    root = tree.getroot()
    ns = _detect_ns(root)

    if verbose:
        log.info('PRODML namespace: %s', ns)
        log.info('Root tag: %s', root.tag)

    if isinstance(sections, str):
        sections = [sections]

    frames = []
    all_units = OrderedDict()

    do_all = 'auto' in sections

    # --- Production volumes ---
    if do_all or 'volumes' in sections:
        vol_rows, vol_units = _parse_production_volumes(root, ns, nameSeparator)
        if vol_rows:
            df = pd.DataFrame(vol_rows)
            # Try to use start date as index
            if 'start' in df.columns:
                try:
                    df['start'] = pd.to_datetime(df['start'])
                    df.set_index('start', inplace=True)
                    df.index.name = 'DATE'
                except Exception:
                    pass
            frames.append(df)
            all_units.update(vol_units)
            if verbose:
                log.info('Production volumes: %d rows', len(df))

    # --- Time series ---
    if do_all or 'timeseries' in sections:
        ts_rows, ts_units = _parse_time_series(root, ns, nameSeparator)
        if ts_rows:
            ts_df = pd.DataFrame(ts_rows)
            # Pivot: rows=datetime, columns=col_name, values=value
            try:
                ts_df['datetime'] = pd.to_datetime(ts_df['datetime'])
                pivoted = ts_df.pivot_table(
                    index='datetime', columns='column',
                    values='value', aggfunc='first')
                pivoted.index.name = 'DATE'
                frames.append(pivoted)
            except Exception:
                frames.append(ts_df)
            all_units.update(ts_units)
            if verbose:
                log.info('Time series: %d values', len(ts_rows))

    # --- Well tests ---
    if do_all or 'welltests' in sections:
        wt_rows, wt_units = _parse_well_tests(root, ns, nameSeparator)
        if wt_rows:
            df = pd.DataFrame(wt_rows)
            if 'test_date' in df.columns:
                try:
                    df['test_date'] = pd.to_datetime(df['test_date'])
                    df.set_index('test_date', inplace=True)
                    df.index.name = 'DATE'
                except Exception:
                    pass
            frames.append(df)
            all_units.update(wt_units)
            if verbose:
                log.info('Well tests: %d rows', len(df))

    # --- Combine ---
    if not frames:
        log.warning('No extractable data found in %s', filepath)
        return SimDataFrame(units={},
                            name_separator=nameSeparator,
                            intersection_character=intersectionCharacter)

    if len(frames) == 1:
        combined = frames[0]
    else:
        combined = pd.concat(frames, axis=0, sort=True)

    return SimDataFrame(data=combined,
                        units=all_units,
                        name_separator=nameSeparator,
                        intersection_character=intersectionCharacter)
