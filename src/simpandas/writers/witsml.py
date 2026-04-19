# -*- coding: utf-8 -*-
"""
WITSML writer for SimPandas.

Writes a ``SimDataFrame`` as a WITSML v1.4.1.1 ``<log>`` XML document.
The output contains one ``<logCurveInfo>`` per column (with units) and
the data rows in the standard comma-separated ``<data>`` format inside
``<logData>``.

Uses only ``xml.etree.ElementTree`` — no external dependencies.
"""

__version__ = '0.1.0'
__release__ = 20260418

import logging
from xml.etree import ElementTree
from xml.dom import minidom

import pandas as pd

__all__ = ['write_witsml']

log = logging.getLogger(__name__)

_NS_WITSML = 'http://www.witsml.org/schemas/1series'
_NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'


def _prettify(elem):
    rough = ElementTree.tostring(elem, encoding='unicode', xml_declaration=True)
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent='  ', encoding=None)


def write_witsml(sdf, filepath, well_name='', wellbore_name='',
                 log_name='SimPandas Export'):
    """
    Write a ``SimDataFrame`` to a WITSML v1.4.1.1 log XML file.

    The index column becomes the first curve (typically depth or time)
    and each DataFrame column becomes a subsequent curve.  Units from the
    ``SimDataFrame.units`` dict are written into ``<logCurveInfo>``
    elements.

    Parameters
    ----------
    sdf : SimDataFrame or SimSeries
        Data to write.
    filepath : str or path-like
        Destination XML file path.
    well_name : str
        Well name for the ``<nameWell>`` element.
    wellbore_name : str
        Wellbore name for ``<nameWellbore>``.
    log_name : str
        Log name for the ``<name>`` element.

    Returns
    -------
    None
    """
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

    units = {}
    if hasattr(sdf, 'units') and sdf.units:
        if isinstance(sdf.units, dict):
            units = {str(k): str(v) for k, v in sdf.units.items()}
        else:
            units = {str(c): str(u)
                     for c, u in zip(df.columns, sdf.units)}

    index_units = ''
    if hasattr(sdf, 'index_units'):
        iu = sdf.index_units
        if isinstance(iu, dict):
            index_units = str(next(iter(iu.values()), ''))
        elif iu:
            index_units = str(iu)

    idx_name = df.index.name or 'INDEX'

    # All curve names: index + columns
    all_curves = [idx_name] + list(df.columns)

    # Root: <logs xmlns="...">
    root = ElementTree.Element('logs')
    root.set('xmlns', _NS_WITSML)
    root.set('xmlns:xsi', _NS_XSI)
    root.set('version', '1.4.1.1')

    log_elem = ElementTree.SubElement(root, 'log')
    log_elem.set('uidWell', '')
    log_elem.set('uidWellbore', '')
    log_elem.set('uid', '')

    ElementTree.SubElement(log_elem, 'nameWell').text = well_name
    ElementTree.SubElement(log_elem, 'nameWellbore').text = wellbore_name
    ElementTree.SubElement(log_elem, 'name').text = log_name

    # Determine index type
    if df.index.dtype.kind in ('f', 'i'):
        ElementTree.SubElement(log_elem, 'indexType').text = 'measured depth'
    else:
        ElementTree.SubElement(log_elem, 'indexType').text = 'date time'

    # <logCurveInfo> for each curve
    for i, curve in enumerate(all_curves):
        ci = ElementTree.SubElement(log_elem, 'logCurveInfo')
        ci.set('uid', str(i))
        ElementTree.SubElement(ci, 'mnemonic').text = str(curve)
        if i == 0:
            uom = index_units
        else:
            uom = units.get(str(curve), '')
        if uom:
            ElementTree.SubElement(ci, 'unit').text = uom
        ElementTree.SubElement(ci, 'curveDescription').text = str(curve)

    # <logData>
    ld = ElementTree.SubElement(log_elem, 'logData')

    # <mnemonicList>
    ElementTree.SubElement(ld, 'mnemonicList').text = ','.join(
        str(c) for c in all_curves)

    # <unitList>
    unit_parts = [index_units]
    for c in df.columns:
        unit_parts.append(units.get(str(c), ''))
    ElementTree.SubElement(ld, 'unitList').text = ','.join(unit_parts)

    # <data> rows
    for idx_val, row in df.iterrows():
        vals = [str(idx_val)] + [str(v) for v in row.values]
        ElementTree.SubElement(ld, 'data').text = ','.join(vals)

    xml_str = _prettify(root)
    with open(str(filepath), 'w', encoding='utf-8') as f:
        f.write(xml_str)

    log.info('write_witsml: wrote %d rows × %d curves to %s',
             len(df), len(all_curves), filepath)
