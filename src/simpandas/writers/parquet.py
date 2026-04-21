# -*- coding: utf-8 -*-
"""
Parquet writer with units support for SimPandas.

Units are stored as JSON in the Parquet file-level metadata under the
keys ``simpandas:units`` and ``simpandas:index_units``.  Files produced
by this writer can be read back with ``simpandas.read_parquet()``.

Requires ``pyarrow`` (the default Parquet engine for pandas).
"""

__version__ = '0.1.0'
__release__ = 20260418

import json
import logging

import pandas as pd

__all__ = ['write_parquet']

log = logging.getLogger(__name__)


def write_parquet(sdf, filepath, compression='snappy', **kwargs):
    """
    Write a ``SimDataFrame`` (or ``SimSeries``) to a Parquet file with
    units stored in the file metadata.

    Parameters
    ----------
    sdf : SimDataFrame or SimSeries
        The object to write.
    filepath : str or path-like
        Destination ``.parquet`` file.  Overwrites if it exists.
    compression : str, default ``'snappy'``
        Compression codec (``'snappy'``, ``'gzip'``, ``'brotli'``,
        ``'zstd'``, ``None``).
    **kwargs
        Extra keyword arguments forwarded to ``pyarrow.parquet.write_table``.

    Returns
    -------
    None
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError(
            "The pyarrow package is required for Parquet support. "
            "Install it with:  pip install pyarrow"
        )

    # Normalise to a plain DataFrame
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

    # Gather units metadata
    units = {}
    if hasattr(sdf, 'units') and sdf.units:
        raw = sdf.units
        if isinstance(raw, dict):
            units = {str(k): str(v) for k, v in raw.items() if v is not None}
        elif hasattr(raw, 'names') and hasattr(raw, 'values_list'):  # ColumnUnits
            units = {str(k): str(v) for k, v in zip(raw.names, raw.values_list) if v is not None}
        else:
            units = {str(c): str(u)
                     for c, u in zip(df.columns, raw) if u is not None}

    index_units = ''
    if hasattr(sdf, 'index_units'):
        iu = sdf.index_units
        if isinstance(iu, dict):
            index_units = str(next(iter(iu.values()), ''))
        elif iu:
            index_units = str(iu)

    # Build Arrow table with custom metadata
    table = pa.Table.from_pandas(df)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b'simpandas:units': json.dumps(units).encode('utf-8'),
        b'simpandas:index_units': index_units.encode('utf-8'),
    }
    merged_meta = {**existing_meta, **custom_meta}
    table = table.replace_schema_metadata(merged_meta)

    pq.write_table(table, str(filepath), compression=compression, **kwargs)

    log.info('write_parquet: wrote %d rows × %d cols to %s',
             len(df), len(df.columns), filepath)
