# -*- coding: utf-8 -*-
"""
WITSML reader for SimPandas.

Reads Energistics WITSML XML files (v1.4.1.1 / v2.0 / v2.1) and
extracts tabular data into ``SimDataFrame`` objects.  Supports:

* **Log data** (``<log>`` / ``<Log>``) — depth- or time-indexed curves
  with per-curve units.
* **Trajectory data** (``<trajectory>`` / ``<Trajectory>``) — directional
  survey stations.
* **MudLog data** (``<mudLog>`` / ``<MudLog>``) — geological/gas-show
  records.

Uses only ``xml.etree.ElementTree`` — no external dependencies.
"""

__version__ = '0.1.0'
__release__ = 20260418

import logging
import re
from collections import OrderedDict
from xml.etree import ElementTree

import numpy as np
import pandas as pd

from simpandas.frame import SimDataFrame

__all__ = ['read_witsml']

log = logging.getLogger(__name__)

# Namespace patterns
_NS_WITSML_V2 = 'http://www.energistics.org/energyml/data/witsmlv2'
_NS_WITSML_V14 = 'http://www.witsml.org/schemas/1series'
_NS_WITSML_V131 = 'http://www.witsml.org/schemas/131'

# ---------------------------------------------------------------------------
# Helpers (shared with prodml reader pattern)
# ---------------------------------------------------------------------------

def _detect_ns(root):
    m = re.match(r'\{(.+?)\}', root.tag)
    return m.group(1) if m else ''


def _ns_tag(ns, local):
    return f'{{{ns}}}{local}' if ns else local


def _findall(elem, ns, path):
    results = elem.findall(_ns_tag(ns, path))
    if not results:
        results = elem.findall(path)
    return results


def _find(elem, ns, path):
    result = elem.find(_ns_tag(ns, path))
    if result is None:
        result = elem.find(path)
    return result


def _text(elem, ns, path, default=''):
    child = _find(elem, ns, path)
    if child is not None and child.text:
        return child.text.strip()
    return default


# ---------------------------------------------------------------------------
# Log data parsing (v1.4 & v2)
# ---------------------------------------------------------------------------

def _parse_logs(root, ns):
    """Extract log curves → list of DataFrames + units dicts."""
    frames = []
    all_units = OrderedDict()

    for log_tag in ('log', 'Log'):
        for log_elem in _findall(root, ns, log_tag):
            name_well = (_text(log_elem, ns, 'nameWell') or
                         _text(log_elem, ns, 'WellName') or '')
            log_name = (_text(log_elem, ns, 'name') or
                        _text(log_elem, ns, 'Name') or
                        log_elem.get('uid', '') or
                        log_elem.get('uuid', ''))

            # --- v1.4 style: <logCurveInfo> + <logData> ---
            curve_names = []
            curve_units = OrderedDict()

            for ci_tag in ('logCurveInfo', 'LogCurveInfo',
                           'ChannelSet/Channel', 'Channel'):
                for ci in _findall(log_elem, ns, ci_tag):
                    mnemonic = (_text(ci, ns, 'mnemonic') or
                                _text(ci, ns, 'Mnemonic') or
                                ci.get('mnemonic', '') or
                                ci.get('uid', ''))
                    uom = (_text(ci, ns, 'unit') or
                           _text(ci, ns, 'Uom') or '')
                    if mnemonic:
                        curve_names.append(mnemonic)
                        if uom:
                            curve_units[mnemonic] = uom

            # --- v1.4 <logData> with <data> rows ---
            for ld_tag in ('logData', 'LogData'):
                for ld in _findall(log_elem, ns, ld_tag):
                    # Column header override from <mnemonicList>
                    mn_list_text = _text(ld, ns, 'mnemonicList')
                    if mn_list_text:
                        curve_names = [s.strip()
                                       for s in mn_list_text.split(',')]

                    # Unit list override
                    unit_list_text = _text(ld, ns, 'unitList')
                    if unit_list_text:
                        unit_parts = [s.strip()
                                      for s in unit_list_text.split(',')]
                        for cn, uu in zip(curve_names, unit_parts):
                            if uu and uu.lower() not in ('', 'unitless'):
                                curve_units[cn] = uu

                    data_rows = []
                    for d_tag in ('data', 'Data'):
                        for d_elem in _findall(ld, ns, d_tag):
                            if d_elem.text:
                                vals = d_elem.text.strip().split(',')
                                parsed = []
                                for v in vals:
                                    v = v.strip()
                                    try:
                                        parsed.append(float(v))
                                    except ValueError:
                                        parsed.append(v if v else np.nan)
                                data_rows.append(parsed)

                    if data_rows and curve_names:
                        n_cols = len(curve_names)
                        # Pad/trim rows
                        padded = []
                        for row in data_rows:
                            if len(row) < n_cols:
                                row += [np.nan] * (n_cols - len(row))
                            padded.append(row[:n_cols])

                        df = pd.DataFrame(padded, columns=curve_names)
                        # First column is typically depth/time index
                        idx_col = curve_names[0]
                        try:
                            df[idx_col] = pd.to_numeric(
                                df[idx_col], errors='coerce')
                        except Exception:
                            pass
                        df.set_index(idx_col, inplace=True)
                        frames.append(df)
                        all_units.update(curve_units)

            # --- v2 <ChannelData> rows ---
            for cd_tag in ('ChannelData', 'channelData'):
                for cd in _findall(log_elem, ns, cd_tag):
                    if cd.text:
                        data_rows = []
                        for line in cd.text.strip().split('\n'):
                            line = line.strip()
                            if not line:
                                continue
                            # v2 uses JSON-ish [[idx, [v1, v2, ...]]] or CSV
                            line = line.strip('[]')
                            vals = [v.strip().strip('"')
                                    for v in line.split(',')]
                            parsed = []
                            for v in vals:
                                try:
                                    parsed.append(float(v))
                                except ValueError:
                                    parsed.append(v if v else np.nan)
                            data_rows.append(parsed)

                        if data_rows and curve_names:
                            n_cols = len(curve_names)
                            padded = []
                            for row in data_rows:
                                if len(row) < n_cols:
                                    row += [np.nan] * (n_cols - len(row))
                                padded.append(row[:n_cols])
                            df = pd.DataFrame(padded, columns=curve_names)
                            idx_col = curve_names[0]
                            try:
                                df[idx_col] = pd.to_numeric(
                                    df[idx_col], errors='coerce')
                            except Exception:
                                pass
                            df.set_index(idx_col, inplace=True)
                            frames.append(df)
                            all_units.update(curve_units)

    return frames, all_units


# ---------------------------------------------------------------------------
# Trajectory parsing
# ---------------------------------------------------------------------------

def _parse_trajectories(root, ns):
    """Extract trajectory stations → DataFrame."""
    frames = []
    units_map = OrderedDict()

    for t_tag in ('trajectory', 'Trajectory'):
        for traj in _findall(root, ns, t_tag):
            rows = []
            for st_tag in ('trajectoryStation', 'TrajectoryStation',
                           'station', 'Station'):
                for sta in _findall(traj, ns, st_tag):
                    row = {}
                    for field, tags in [
                        ('MD', ('md', 'Md', 'MD')),
                        ('TVD', ('tvd', 'Tvd', 'TVD')),
                        ('Inclination', ('incl', 'Incl', 'Inclination')),
                        ('Azimuth', ('azi', 'Azi', 'Azimuth')),
                        ('DLS', ('dls', 'Dls', 'DoglegSeverity')),
                        ('NS', ('dispNs', 'Northing')),
                        ('EW', ('dispEw', 'Easting')),
                    ]:
                        for t in tags:
                            elem = _find(sta, ns, t)
                            if elem is not None and elem.text:
                                try:
                                    row[field] = float(elem.text.strip())
                                except ValueError:
                                    row[field] = elem.text.strip()
                                uom = elem.get('uom', '')
                                if uom:
                                    units_map[field] = uom
                                break
                    if row:
                        rows.append(row)

            if rows:
                df = pd.DataFrame(rows)
                if 'MD' in df.columns:
                    try:
                        df['MD'] = pd.to_numeric(df['MD'], errors='coerce')
                    except Exception:
                        pass
                    df.set_index('MD', inplace=True)
                frames.append(df)

    return frames, units_map


# ---------------------------------------------------------------------------
# MudLog parsing
# ---------------------------------------------------------------------------

def _parse_mudlogs(root, ns):
    """Extract mudlog geology intervals → DataFrame."""
    frames = []
    units_map = OrderedDict()

    for ml_tag in ('mudLog', 'MudLog'):
        for ml in _findall(root, ns, ml_tag):
            rows = []
            for gi_tag in ('geologyInterval', 'GeologyInterval'):
                for gi in _findall(ml, ns, gi_tag):
                    row = {}
                    for field, tags in [
                        ('mdTop', ('mdTop', 'MdTop')),
                        ('mdBottom', ('mdBottom', 'MdBottom')),
                        ('lithology', ('lithology', 'Lithology',
                                       'lithoType', 'LithoType')),
                        ('description', ('description', 'Description')),
                    ]:
                        for t in tags:
                            elem = _find(gi, ns, t)
                            if elem is not None and elem.text:
                                try:
                                    row[field] = float(elem.text.strip())
                                except ValueError:
                                    row[field] = elem.text.strip()
                                uom = elem.get('uom', '')
                                if uom:
                                    units_map[field] = uom
                                break
                    if row:
                        rows.append(row)

            if rows:
                df = pd.DataFrame(rows)
                if 'mdTop' in df.columns:
                    try:
                        df['mdTop'] = pd.to_numeric(
                            df['mdTop'], errors='coerce')
                    except Exception:
                        pass
                    df.set_index('mdTop', inplace=True)
                frames.append(df)

    return frames, units_map


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_witsml(filepath,
                sections='auto',
                nameSeparator=':',
                intersectionCharacter='&',
                verbose=False):
    """
    Read a WITSML XML file into a ``SimDataFrame``.

    Parameters
    ----------
    filepath : str or path-like
        Path to a ``.xml`` WITSML file.
    sections : str or list[str]
        Which sections to extract:

        * ``'auto'`` (default) – read all recognised sections.
        * ``'logs'`` – log curve data only.
        * ``'trajectories'`` – directional survey stations.
        * ``'mudlogs'`` – geology interval data.
    nameSeparator : str
        Separator for column names in ``SimDataFrame``.
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
        log.info('WITSML namespace: %s', ns)

    if isinstance(sections, str):
        sections = [sections]

    frames = []
    all_units = OrderedDict()
    do_all = 'auto' in sections

    if do_all or 'logs' in sections:
        log_frames, log_units = _parse_logs(root, ns)
        frames.extend(log_frames)
        all_units.update(log_units)
        if verbose:
            log.info('Logs: %d datasets', len(log_frames))

    if do_all or 'trajectories' in sections:
        traj_frames, traj_units = _parse_trajectories(root, ns)
        frames.extend(traj_frames)
        all_units.update(traj_units)
        if verbose:
            log.info('Trajectories: %d datasets', len(traj_frames))

    if do_all or 'mudlogs' in sections:
        mud_frames, mud_units = _parse_mudlogs(root, ns)
        frames.extend(mud_frames)
        all_units.update(mud_units)
        if verbose:
            log.info('MudLogs: %d datasets', len(mud_frames))

    if not frames:
        log.warning('No extractable data found in %s', filepath)
        return SimDataFrame(units={},
                            name_separator=nameSeparator,
                            intersection_character=intersectionCharacter)

    if len(frames) == 1:
        combined = frames[0]
    else:
        combined = pd.concat(frames, axis=0, sort=True)

    index_units = ''
    idx_name = combined.index.name or ''
    if idx_name in all_units:
        index_units = all_units.pop(idx_name)

    return SimDataFrame(data=combined,
                        units=all_units,
                        index_units=index_units,
                        name_separator=nameSeparator,
                        intersection_character=intersectionCharacter)
