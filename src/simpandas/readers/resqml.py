# -*- coding: utf-8 -*-
"""
RESQML reader with units support for SimPandas.

Reads RESQML v2.0.1 / v2.2 EPC packages (ZIP containers with XML + HDF5).

Currently extracts:
  * Time series data  (``TimeSeries`` objects)
  * Continuous properties  (``ContinuousProperty`` / ``ContinuousPropertySeries``)

Requires ``h5py`` (optional dependency) when properties reference external
HDF5 datasets.
"""

__version__ = '0.1.0'
__release__ = 20260614

import logging
import os
import xml.etree.ElementTree as ET
import zipfile
from collections import OrderedDict

import numpy as np
import pandas as pd

from simpandas.frame import SimDataFrame

__all__ = ['read_resqml']

logging.basicConfig(level=logging.INFO)

# Known RESQML namespaces
_NS_RESQML201 = 'http://www.energistics.org/energyml/data/resqmlv2'
_NS_RESQML22 = 'http://www.energistics.org/energyml/data/resqmlv2/2.2'
_NS_EML20 = 'http://www.energistics.org/energyml/data/commonv2'
_NS_EML23 = 'http://www.energistics.org/energyml/data/commonv2/2.3'
_NS_RELS = 'http://schemas.openxmlformats.org/package/2006/relationships'
_NS_CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
_NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'


def _strip_ns(tag):
    """Remove namespace prefix from an XML tag."""
    if tag.startswith('{'):
        return tag.split('}', 1)[1]
    return tag


def _find_ns(elem, local_name, namespaces):
    """Find first child element matching *local_name* in any known namespace."""
    for ns in namespaces:
        found = elem.find(f'{{{ns}}}{local_name}')
        if found is not None:
            return found
    # fallback: try without namespace
    found = elem.find(local_name)
    return found


def _findall_ns(elem, local_name, namespaces):
    """Find all child elements matching *local_name* in any known namespace."""
    results = []
    for ns in namespaces:
        results.extend(elem.findall(f'{{{ns}}}{local_name}'))
    if not results:
        results = elem.findall(local_name)
    return results


def _text(elem, local_name, namespaces, default=''):
    """Extract text of a child element."""
    child = _find_ns(elem, local_name, namespaces)
    if child is not None and child.text:
        return child.text.strip()
    return default


def _detect_namespaces(root):
    """Detect RESQML and EML namespaces from the root element."""
    resqml_ns = []
    eml_ns = []

    # scan all namespace declarations
    tag = root.tag
    if tag.startswith('{'):
        ns = tag.split('}', 1)[0].strip('{')
        if 'resqml' in ns.lower():
            resqml_ns.append(ns)
        elif 'common' in ns.lower():
            eml_ns.append(ns)

    # always add known ones as fallbacks
    for ns in [_NS_RESQML22, _NS_RESQML201]:
        if ns not in resqml_ns:
            resqml_ns.append(ns)
    for ns in [_NS_EML23, _NS_EML20]:
        if ns not in eml_ns:
            eml_ns.append(ns)

    return resqml_ns + eml_ns


def _parse_epc_parts(epc_path):
    """
    Open an EPC (ZIP) file and return a dict of ``{part_name: ET.Element}``
    for every XML part inside.  Also returns the ZipFile handle (caller
    must close) and the directory containing the EPC file (for resolving
    relative HDF5 paths).
    """
    epc_dir = os.path.dirname(os.path.abspath(epc_path))
    zf = zipfile.ZipFile(epc_path, 'r')
    parts = {}
    for name in zf.namelist():
        if name.endswith('.xml') or name.endswith('.rels'):
            try:
                data = zf.read(name)
                root = ET.fromstring(data)
                parts[name] = root
            except ET.ParseError:
                pass
    return parts, zf, epc_dir


def _collect_objects(parts):
    """
    Walk all parsed XML parts and bucket objects by their stripped root-tag
    name.  Returns ``{local_tag: [(part_name, root_element), ...]}``.
    """
    objects = {}
    for part_name, root in parts.items():
        local = _strip_ns(root.tag)
        objects.setdefault(local, []).append((part_name, root))
    return objects


def _read_hdf5_dataset(epc_dir, zf, hdf_ref, namespaces):
    """
    Resolve an HDF5 external reference and return a numpy array.

    *hdf_ref* is an XML element with children:
      - ``URI`` or ``PathInHdfFile`` – the dataset path inside the HDF5 file
      - ``HdfProxy`` or ``Title`` – used to locate the external file

    The HDF5 file is looked up first inside the EPC archive, then on disk
    relative to the EPC directory.
    """
    try:
        import h5py
    except ImportError:
        raise ImportError(
            "h5py is required to read property data from RESQML files. "
            "Install it with:  pip install h5py"
        )

    path_in_hdf = None
    hdf_filename = None

    for child in hdf_ref:
        local = _strip_ns(child.tag)
        if local in ('PathInHdfFile', 'PathInExternalFile'):
            path_in_hdf = child.text.strip() if child.text else None
        elif local in ('URI', 'uri'):
            path_in_hdf = child.text.strip() if child.text else None

    # try to find the HDF5 filename from the proxy reference or Title
    title_el = _find_ns(hdf_ref, 'Title', namespaces)
    if title_el is not None and title_el.text:
        hdf_filename = title_el.text.strip()

    if path_in_hdf is None:
        return None

    # Look for HDF5 files: first in EPC zip, then on disk
    h5_candidates = [n for n in zf.namelist() if n.endswith('.h5') or n.endswith('.hdf5')]
    if h5_candidates:
        # extract to temp and read
        import tempfile
        tmp = tempfile.mkdtemp()
        extracted = zf.extract(h5_candidates[0], tmp)
        try:
            with h5py.File(extracted, 'r') as hf:
                if path_in_hdf in hf:
                    return np.array(hf[path_in_hdf])
        finally:
            try:
                os.remove(extracted)
                os.rmdir(tmp)
            except OSError:
                pass

    # try on-disk HDF5 files
    if hdf_filename:
        disk_path = os.path.join(epc_dir, hdf_filename)
        if os.path.isfile(disk_path):
            with h5py.File(disk_path, 'r') as hf:
                if path_in_hdf in hf:
                    return np.array(hf[path_in_hdf])

    # search for any .h5 file alongside the EPC
    for fname in os.listdir(epc_dir):
        if fname.endswith('.h5') or fname.endswith('.hdf5'):
            disk_path = os.path.join(epc_dir, fname)
            with h5py.File(disk_path, 'r') as hf:
                if path_in_hdf in hf:
                    return np.array(hf[path_in_hdf])

    logging.warning("Could not resolve HDF5 dataset: %s", path_in_hdf)
    return None


def _parse_time_series(objects, namespaces):
    """
    Extract TimeSeries objects → dict of {uuid: [datetime, ...]}.
    """
    result = {}
    for tag_name in ('TimeSeries', 'obj_TimeSeries'):
        for _part, root in objects.get(tag_name, []):
            ns_all = _detect_namespaces(root) + namespaces
            uuid = root.attrib.get('uuid', '')
            # collect time entries
            times = []
            for child in root:
                local = _strip_ns(child.tag)
                if local in ('Time', 'Timestamp', 'TimeIndex'):
                    ts_el = _find_ns(child, 'DateTime', ns_all)
                    if ts_el is None:
                        ts_el = _find_ns(child, 'Timestamp', ns_all)
                    if ts_el is not None and ts_el.text:
                        times.append(pd.Timestamp(ts_el.text.strip()))
                    elif child.text and child.text.strip():
                        try:
                            times.append(pd.Timestamp(child.text.strip()))
                        except (ValueError, TypeError):
                            pass
            if times:
                result[uuid] = sorted(times)
    return result


def _parse_properties(objects, epc_dir, zf, namespaces, time_series_map):
    """
    Extract ContinuousProperty / DiscreteProperty objects.
    Returns a list of dicts: {name, uuid, uom, values, times}.
    """
    props = []
    for tag_name in ('ContinuousProperty', 'obj_ContinuousProperty',
                     'ContinuousPropertySeries',
                     'DiscreteProperty', 'obj_DiscreteProperty',
                     'DiscretePropertySeries'):
        for _part, root in objects.get(tag_name, []):
            ns_all = _detect_namespaces(root) + namespaces
            uuid = root.attrib.get('uuid', '')
            # property name / citation title
            citation = _find_ns(root, 'Citation', ns_all)
            name = ''
            if citation is not None:
                name = _text(citation, 'Title', ns_all, default=uuid)
            if not name:
                name = uuid

            # unit of measure
            uom = root.attrib.get('uom', '')
            if not uom:
                uom_el = _find_ns(root, 'UOM', ns_all)
                if uom_el is None:
                    uom_el = _find_ns(root, 'Uom', ns_all)
                if uom_el is not None and uom_el.text:
                    uom = uom_el.text.strip()

            # values from inline or HDF5 reference
            values = None
            for child in root:
                local = _strip_ns(child.tag)
                if local in ('PatchOfValues', 'ValuesForPatch',
                             'Values', 'PatchOfPoints'):
                    # look for HDF5 external reference
                    hdf_proxy = _find_ns(child, 'Values', ns_all)
                    if hdf_proxy is None:
                        hdf_proxy = child
                    hdf_ref = _find_ns(hdf_proxy, 'ExternalFileProxy', ns_all)
                    if hdf_ref is None:
                        hdf_ref = _find_ns(hdf_proxy, 'HdfProxy', ns_all)
                    if hdf_ref is None:
                        # check for PathInHdfFile directly
                        path_el = _find_ns(hdf_proxy, 'PathInHdfFile', ns_all)
                        if path_el is None:
                            path_el = _find_ns(hdf_proxy, 'PathInExternalFile', ns_all)
                        if path_el is not None:
                            hdf_ref = hdf_proxy

                    if hdf_ref is not None:
                        values = _read_hdf5_dataset(epc_dir, zf, hdf_ref, ns_all)

                    # inline double values
                    if values is None:
                        dv = _find_ns(child, 'DoubleHdf5Array', ns_all)
                        if dv is None:
                            dv = _find_ns(child, 'DoubleValues', ns_all)
                        if dv is not None and dv.text:
                            try:
                                values = np.array([float(x) for x in dv.text.strip().split()])
                            except ValueError:
                                pass

                    # inline integer values
                    if values is None:
                        iv = _find_ns(child, 'IntegerHdf5Array', ns_all)
                        if iv is None:
                            iv = _find_ns(child, 'IntValues', ns_all)
                        if iv is not None and iv.text:
                            try:
                                values = np.array([int(x) for x in iv.text.strip().split()])
                            except ValueError:
                                pass

            # link to time series
            ts_uuid = ''
            ts_el = _find_ns(root, 'TimeIndex', ns_all)
            if ts_el is None:
                ts_el = _find_ns(root, 'TimeSeries', ns_all)
            if ts_el is not None:
                uuid_el = _find_ns(ts_el, 'UUID', ns_all)
                if uuid_el is None:
                    uuid_el = _find_ns(ts_el, 'uuid', ns_all)
                if uuid_el is not None and uuid_el.text:
                    ts_uuid = uuid_el.text.strip()
                # or ContentType reference
                if not ts_uuid:
                    ts_uuid = ts_el.attrib.get('uuid', '')

            times = time_series_map.get(ts_uuid, None)

            if values is not None:
                props.append({
                    'name': name,
                    'uuid': uuid,
                    'uom': uom,
                    'values': values,
                    'times': times,
                })
    return props


def read_resqml(filepath,
                sections='auto',
                units=None,
                indexUnits=None,
                nameSeparator=None,
                intersectionCharacter=None,
                autoAppend=False,
                operatePerName=False,
                verbose=False):
    """
    Read a RESQML EPC package into a SimDataFrame.

    The reader extracts time-indexed property data from ``ContinuousProperty``
    and ``DiscreteProperty`` objects inside the EPC (ZIP) archive.  When an
    associated ``TimeSeries`` object exists, it is used as the DataFrame index.

    Parameters
    ----------
    filepath : str or path-like
        Path to the ``.epc`` file.
    sections : str, default ``'auto'``
        What to extract.  Currently only ``'auto'`` and ``'properties'``
        are supported.
    units : dict or None
        Override column → unit mapping.
    indexUnits : str or None
        Override index units.
    nameSeparator, intersectionCharacter, autoAppend, operatePerName, verbose
        Forwarded to the ``SimDataFrame`` constructor.

    Returns
    -------
    SimDataFrame
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"RESQML file not found: {filepath}")

    parts, zf, epc_dir = _parse_epc_parts(filepath)
    try:
        # determine active namespaces
        all_ns = [_NS_RESQML22, _NS_RESQML201, _NS_EML23, _NS_EML20]
        objects = _collect_objects(parts)

        # parse time series
        ts_map = _parse_time_series(objects, all_ns)

        # parse properties
        props = _parse_properties(objects, epc_dir, zf, all_ns, ts_map)

        if not props:
            logging.warning("No property data found in RESQML file: %s", filepath)
            return SimDataFrame()

        # build DataFrame
        # determine common time axis
        time_index = None
        for p in props:
            if p['times'] is not None and len(p['times']) > 0:
                if time_index is None or len(p['times']) > len(time_index):
                    time_index = p['times']

        data = OrderedDict()
        col_units = {}
        for p in props:
            col_name = p['name']
            # make unique if needed
            counter = 1
            orig_name = col_name
            while col_name in data:
                counter += 1
                col_name = f"{orig_name}_{counter}"
            vals = p['values']
            if time_index is not None:
                # align to time index length
                if len(vals) > len(time_index):
                    vals = vals[:len(time_index)]
                elif len(vals) < len(time_index):
                    padded = np.full(len(time_index), np.nan)
                    padded[:len(vals)] = vals
                    vals = padded
            data[col_name] = vals
            if p['uom']:
                col_units[col_name] = p['uom']

        if time_index is not None:
            index = pd.DatetimeIndex(time_index)
        else:
            # no time axis – use simple integer index
            max_len = max(len(v) for v in data.values()) if data else 0
            index = pd.RangeIndex(max_len)

        df = pd.DataFrame(data, index=index)

        # apply user-supplied units override
        if units is not None:
            if isinstance(units, dict):
                col_units.update(units)
            elif isinstance(units, str):
                col_units = {c: units for c in df.columns}

        idx_units = indexUnits or ''

        return SimDataFrame(
            data=df,
            units=col_units if col_units else None,
            index_units=idx_units or None,
            name_separator=nameSeparator,
            intersection_character=intersectionCharacter,
            auto_append=autoAppend,
            operate_per_name=operatePerName,
            verbose=verbose,
            source_path=str(filepath),
        )
    finally:
        zf.close()
