# -*- coding: utf-8 -*-
"""
JSON writer with units support for SimPandas.
"""

__version__ = '0.1.0'
__release__ = 20260418

__all__ = ['write_json']


def write_json(sdf, path_or_buf=None, **kwargs):
    """
    Write a SimDataFrame or SimSeries to JSON with units metadata.

    The output uses a SimPandas-specific envelope::

        {
            "data": { ... },
            "units": { ... },
            "index_units": "..."
        }

    Files produced by this function are automatically detected by
    ``simpandas.read_json``::

        simpandas.read_json(path)

    Parameters
    ----------
    sdf : SimDataFrame or SimSeries
        The object to write.
    path_or_buf : str, path object, or file-like, optional
        File path or object.  If ``None`` the JSON string is returned.
    **kwargs
        Additional keyword arguments forwarded to
        ``pandas.DataFrame.to_json`` / ``pandas.Series.to_json``
        when serialising the *data* portion.

    Returns
    -------
    None or str
        ``None`` when writing to a file; the JSON string otherwise.
    """
    import json
    import pandas as pd

    # Deduplicate column names before serialisation so that the units dict
    # retains a value for every column (dict keys must be unique).
    if hasattr(sdf, 'deduplicate_columns'):
        sdf = sdf.deduplicate_columns()

    # Get a plain pandas object for data serialisation
    if hasattr(sdf, 'as_dataframe'):
        data_obj = sdf.as_dataframe()
    elif hasattr(sdf, 'as_pandas'):
        data_obj = sdf.as_pandas()
    else:
        data_obj = sdf

    # Serialise the data part via pandas
    data_json_str = data_obj.to_json(**kwargs)
    data_payload = json.loads(data_json_str) if isinstance(data_json_str, str) else data_json_str

    # Gather units
    try:
        units = sdf.units
        if not isinstance(units, (dict,)) and not hasattr(units, 'to_dict'):
            if isinstance(units, str) and hasattr(sdf, 'name'):
                units = {sdf.name: units}
            else:
                units = {}
        elif hasattr(units, 'to_dict') and not isinstance(units, dict):
            units = units.to_dict()
    except Exception:
        units = {}

    # Gather index units
    index_units_val = getattr(sdf, 'index_units', None)

    payload = {
        'data': data_payload,
        'units': units,
        'index_units': index_units_val,
    }

    if path_or_buf is not None:
        with open(path_or_buf, 'w') as f:
            json.dump(payload, f)
        return None

    return json.dumps(payload)
