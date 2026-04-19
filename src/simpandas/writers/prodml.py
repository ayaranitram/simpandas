# -*- coding: utf-8 -*-
"""
PRODML writer for SimPandas.

Writes a ``SimDataFrame`` as a PRODML v2 ``TimeSeries`` XML document.
The output is a standalone XML file that conforms to the PRODML v2
time-series schema and can be imported by Energistics-compatible tools.

Uses only the standard-library ``xml.etree.ElementTree`` — no external
dependencies.
"""

__version__ = '0.1.0'
__release__ = 20260418

import logging
from xml.etree import ElementTree
from xml.dom import minidom

import pandas as pd

__all__ = ['write_prodml']

log = logging.getLogger(__name__)

_NS_PRODML = 'http://www.energistics.org/energyml/data/prodmlv2'
_NS_EML = 'http://www.energistics.org/energyml/data/commonv2'
_NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'


def _prettify(elem):
    """Return a pretty-printed XML string."""
    rough = ElementTree.tostring(elem, encoding='unicode', xml_declaration=True)
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent='  ', encoding=None)


def write_prodml(sdf, filepath, style='timeseries', facility='SimPandas'):
    """
    Write a ``SimDataFrame`` to a PRODML v2 XML file.

    Parameters
    ----------
    sdf : SimDataFrame or SimSeries
        The data to write.  The index is used as the time axis.
    filepath : str or path-like
        Destination XML file path.
    style : ``'timeseries'`` or ``'volumes'``
        Output schema style.

        * ``'timeseries'`` (default) – writes one ``<TimeSeries>``
          element per column with ``<Value dateTime="...">`` children.
        * ``'volumes'`` – writes a ``<ProductVolume>`` report with one
          ``<Period>`` per row.
    facility : str
        Facility / installation name written into the XML.

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
            units = sdf.units
        else:
            units = {str(c): str(u)
                     for c, u in zip(df.columns, sdf.units)}

    name_sep = getattr(sdf, 'name_separator', ':') or ':'

    # Build XML tree
    root = ElementTree.Element('ProdmlDataDocument')
    root.set('xmlns', _NS_PRODML)
    root.set('xmlns:eml', _NS_EML)
    root.set('xmlns:xsi', _NS_XSI)

    if style == 'timeseries':
        _write_time_series(root, df, units, name_sep)
    elif style == 'volumes':
        _write_volumes(root, df, units, name_sep, facility)
    else:
        raise ValueError(f"Unknown style: {style!r}. "
                         "Use 'timeseries' or 'volumes'.")

    xml_str = _prettify(root)
    with open(str(filepath), 'w', encoding='utf-8') as f:
        f.write(xml_str)

    log.info('write_prodml: wrote %s style to %s', style, filepath)


def _write_time_series(root, df, units, name_sep):
    """Write <TimeSeries> elements."""
    for col in df.columns:
        ts = ElementTree.SubElement(root, 'TimeSeries')

        # Split column into key:well if separator present
        parts = str(col).split(name_sep, 1)
        key = parts[0]
        well = parts[1] if len(parts) > 1 else ''

        ElementTree.SubElement(ts, 'Key').text = key
        if well:
            ElementTree.SubElement(ts, 'WellName').text = well
        uom = units.get(col, units.get(key, ''))
        if uom:
            ElementTree.SubElement(ts, 'Unit').text = str(uom)

        for idx_val, data_val in df[col].dropna().items():
            ve = ElementTree.SubElement(ts, 'Value')
            # Convert index to ISO datetime string
            if isinstance(idx_val, (pd.Timestamp, pd.DatetimeTZDtype)):
                ve.set('dateTime', str(idx_val.isoformat()))
            else:
                ve.set('dateTime', str(idx_val))
            ve.text = str(data_val)


def _write_volumes(root, df, units, name_sep, facility):
    """Write <ProductVolume> element with periods."""
    pvol = ElementTree.SubElement(root, 'ProductVolume')
    inst = ElementTree.SubElement(pvol, 'Installation')
    ElementTree.SubElement(inst, 'Name').text = facility

    for col in df.columns:
        product = ElementTree.SubElement(pvol, 'Product')
        ElementTree.SubElement(product, 'Name').text = str(col)
        uom = units.get(col, '')

        for idx_val, data_val in df[col].dropna().items():
            period = ElementTree.SubElement(product, 'Period')
            if isinstance(idx_val, (pd.Timestamp, pd.DatetimeTZDtype)):
                ElementTree.SubElement(period, 'DateStart').text = str(
                    idx_val.isoformat())
            else:
                ElementTree.SubElement(period, 'DateStart').text = str(idx_val)
            vol_elem = ElementTree.SubElement(period, 'Volume')
            vol_elem.text = str(data_val)
            if uom:
                vol_elem.set('uom', str(uom))
