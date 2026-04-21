# -*- coding: utf-8 -*-
"""
RESQML writer with units support for SimPandas.

Writes a SimDataFrame as a RESQML v2.0.1 EPC package (ZIP container)
with an embedded HDF5 file for the numeric data and XML metadata for
properties and time series.

Requires ``h5py`` (optional dependency).
"""

__version__ = '0.1.0'
__release__ = 20260614

import logging
import os
import uuid as _uuid
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

import numpy as np

__all__ = ['write_resqml']

logging.basicConfig(level=logging.INFO)

_NS_RESQML = 'http://www.energistics.org/energyml/data/resqmlv2'
_NS_EML = 'http://www.energistics.org/energyml/data/commonv2'
_NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'
_NS_CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
_NS_RELS = 'http://schemas.openxmlformats.org/package/2006/relationships'

_RESQML_CT = 'application/x-resqml+xml;version=2.0;type='


def _new_uuid():
    return str(_uuid.uuid4())


def _indent_xml(elem, level=0):
    """Add indentation to an ElementTree element (in-place)."""
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        for i, child in enumerate(elem):
            _indent_xml(child, level + 1)
            if i < len(elem) - 1:
                child.tail = indent + "  "
            else:
                child.tail = indent
    if not elem.tail or not elem.tail.strip():
        elem.tail = indent


def _elem(tag, text=None, attrib=None):
    """Create an XML element with optional text and attributes."""
    e = ET.Element(tag, attrib or {})
    if text is not None:
        e.text = str(text)
    return e


def _sub(parent, tag, text=None, attrib=None):
    """Create a sub-element."""
    e = ET.SubElement(parent, tag, attrib or {})
    if text is not None:
        e.text = str(text)
    return e


def write_resqml(sdf, filepath):
    """
    Write a SimDataFrame to a RESQML EPC package.

    The output contains:

    * An HDF5 file (``data.h5``) with one dataset per column.
    * One ``ContinuousProperty`` XML part per column.
    * A ``TimeSeries`` XML part if the index is datetime-based.
    * A ``[Content_Types].xml`` and ``_rels/.rels`` manifest.

    Parameters
    ----------
    sdf : SimDataFrame
        The data to write.
    filepath : str or path-like
        Output ``.epc`` file path.  The companion HDF5 file will be
        written next to it (same directory, name ``<stem>.h5``).
    """
    try:
        import h5py
    except ImportError:
        raise ImportError(
            "h5py is required to write RESQML files. "
            "Install it with:  pip install h5py"
        )

    import pandas as pd

    filepath = str(filepath)
    stem = os.path.splitext(os.path.basename(filepath))[0]
    epc_dir = os.path.dirname(os.path.abspath(filepath))
    h5_filename = stem + '.h5'
    h5_path = os.path.join(epc_dir, h5_filename)

    df = sdf.as_dataframe() if hasattr(sdf, 'as_dataframe') else sdf
    col_units = {}
    if hasattr(sdf, 'units') and sdf.units is not None:
        u = sdf.units
        if isinstance(u, dict):
            col_units = dict(u)
        elif hasattr(u, 'to_dict'):
            col_units = u.to_dict()

    has_time_index = isinstance(df.index, pd.DatetimeIndex)

    # ---- write HDF5 ----
    h5_group = '/RESQML'
    with h5py.File(h5_path, 'w') as hf:
        grp = hf.create_group('RESQML')
        for col in df.columns:
            vals = df[col].values
            if np.issubdtype(vals.dtype, np.floating) or np.issubdtype(vals.dtype, np.integer):
                grp.create_dataset(str(col), data=vals.astype(np.float64))
            else:
                # store as string
                grp.create_dataset(str(col), data=vals.astype(str))

    # ---- build XML parts ----
    # TimeSeries
    ts_uuid = _new_uuid()
    ts_part = None
    if has_time_index:
        ts_root = ET.Element('TimeSeries', {
            'xmlns': _NS_RESQML,
            'uuid': ts_uuid,
            'schemaVersion': '2.0',
        })
        citation = _sub(ts_root, 'Citation')
        _sub(citation, 'Title', 'SimPandas TimeSeries')
        _sub(citation, 'Originator', 'simpandas')

        for ts in df.index:
            time_el = _sub(ts_root, 'Time')
            _sub(time_el, 'DateTime', pd.Timestamp(ts).isoformat())

        _indent_xml(ts_root)
        ts_part = ('TimeSeries_' + ts_uuid + '.xml',
                   ET.tostring(ts_root, encoding='unicode', xml_declaration=True))

    # ContinuousProperty per column
    prop_parts = []
    for col in df.columns:
        prop_uuid = _new_uuid()
        uom = col_units.get(col, 'Euc')  # Euc = dimensionless in Energistics

        root = ET.Element('ContinuousProperty', {
            'xmlns': _NS_RESQML,
            'uuid': prop_uuid,
            'schemaVersion': '2.0',
        })
        citation = _sub(root, 'Citation')
        _sub(citation, 'Title', str(col))
        _sub(citation, 'Originator', 'simpandas')

        _sub(root, 'UOM', uom)

        # reference time series
        if has_time_index:
            ts_ref = _sub(root, 'TimeIndex')
            _sub(ts_ref, 'Index', '0')
            ts_link = _sub(ts_ref, 'TimeSeries')
            _sub(ts_link, 'UUID', ts_uuid)
            _sub(ts_link, 'Title', 'SimPandas TimeSeries')

        # HDF5 reference
        patch = _sub(root, 'PatchOfValues')
        vals = _sub(patch, 'Values')
        _sub(vals, 'PathInHdfFile', f'{h5_group}/{col}')

        _indent_xml(root)
        part_name = f'ContinuousProperty_{prop_uuid}.xml'
        prop_parts.append((part_name, ET.tostring(root, encoding='unicode',
                                                   xml_declaration=True)))

    # ---- Content_Types ----
    ct_root = ET.Element('Types', {'xmlns': _NS_CT})
    _sub(ct_root, 'Default', attrib={
        'Extension': 'rels',
        'ContentType': 'application/vnd.openxmlformats-package.relationships+xml',
    })
    _sub(ct_root, 'Default', attrib={
        'Extension': 'xml',
        'ContentType': 'application/xml',
    })
    if ts_part:
        _sub(ct_root, 'Override', attrib={
            'PartName': '/' + ts_part[0],
            'ContentType': _RESQML_CT + 'obj_TimeSeries',
        })
    for pname, _ in prop_parts:
        _sub(ct_root, 'Override', attrib={
            'PartName': '/' + pname,
            'ContentType': _RESQML_CT + 'obj_ContinuousProperty',
        })
    _indent_xml(ct_root)
    ct_xml = ET.tostring(ct_root, encoding='unicode', xml_declaration=True)

    # ---- .rels ----
    rels_root = ET.Element('Relationships', {'xmlns': _NS_RELS})
    _sub(rels_root, 'Relationship', attrib={
        'Id': 'rel_h5',
        'Type': 'http://schemas.energistics.org/package/2012/relationships/externalResource',
        'Target': h5_filename,
    })
    _indent_xml(rels_root)
    rels_xml = ET.tostring(rels_root, encoding='unicode', xml_declaration=True)

    # ---- write EPC (ZIP) ----
    with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', ct_xml)
        zf.writestr('_rels/.rels', rels_xml)
        if ts_part:
            zf.writestr(ts_part[0], ts_part[1])
        for pname, pxml in prop_parts:
            zf.writestr(pname, pxml)

    logging.info("Wrote RESQML EPC: %s  (HDF5: %s)", filepath, h5_path)
    return filepath
