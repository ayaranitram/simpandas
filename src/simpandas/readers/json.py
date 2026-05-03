# -*- coding: utf-8 -*-
"""
JSON reader with units support for SimPandas.
"""

__version__ = '0.1.1'
__release__ = 20260503

from simpandas.frame import SimDataFrame

__all__ = ['read_json']


def read_json(path_or_buf,
              units=None,
              indexUnits=None,
              nameSeparator=None,
              intersectionCharacter=None,
              autoAppend=False,
              operatePerName=False,
              verbose=False,
              *args, **kwargs):
    """
    Read a JSON file into a SimDataFrame, with optional units support.

    Accepts either a standard pandas-style JSON file or a SimPandas JSON
    file produced by ``SimDataFrame.to_json()`` that contains ``data`` and
    ``units`` keys.

    Parameters
    ----------
    path_or_buf : str, path object, or file-like
        Path to the JSON file or JSON string.
    units : dict or None
        Maps column names to unit strings. Overrides units in the file.
    indexUnits : str or None
        Units for the index column.
    nameSeparator : str or None
        Separator for structured column names.
    intersectionCharacter : str or None
        Character used for name intersections.
    autoAppend : bool
        Whether to auto-append on assignment.
    operatePerName : bool
        Whether to operate per structured name.
    verbose : bool
        Whether to print info messages.
    *args, **kwargs
        Additional arguments passed to pandas.read_json.

    Returns
    -------
    SimDataFrame
    """
    import json
    import pandas as pd

    # Try to detect SimPandas JSON format (with data + units keys)
    raw = None
    if isinstance(path_or_buf, str):
        try:
            raw = json.loads(path_or_buf)
        except (json.JSONDecodeError, ValueError):
            try:
                with open(path_or_buf, 'r') as f:
                    raw = json.load(f)
            except Exception:
                raw = None

    if isinstance(raw, dict) and 'data' in raw and 'units' in raw:
        df = pd.DataFrame(raw['data'])
        if units is None:
            units = raw.get('units', None)
        if indexUnits is None:
            indexUnits = raw.get('index_units', None)
    else:
        df = pd.read_json(path_or_buf, *args, **kwargs)

    sim_kwargs = {}
    if units is not None:
        sim_kwargs['units'] = units
    if indexUnits is not None:
        sim_kwargs['index_units'] = indexUnits
    if nameSeparator is not None:
        sim_kwargs['name_separator'] = nameSeparator
    if intersectionCharacter is not None:
        sim_kwargs['intersection_character'] = intersectionCharacter
    sim_kwargs['auto_append'] = autoAppend
    sim_kwargs['operate_per_name'] = operatePerName
    sim_kwargs['verbose'] = verbose

    return SimDataFrame(data=df, **sim_kwargs)
