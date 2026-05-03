# -*- coding: utf-8 -*-
"""
Parquet reader with units support for SimPandas.

Requires ``pyarrow`` **or** ``fastparquet`` (the same engines that
``pandas.read_parquet`` supports).

Units are stored as JSON in the Parquet file-level metadata under the
key ``simpandas:units`` and ``simpandas:index_units``.  Files written
by ``write_parquet`` embed this metadata automatically; plain Parquet
files work too — supply *units* / *indexUnits* manually.
"""

__version__ = '0.1.1'
__release__ = 20260503

import json
import logging

import pandas as pd

from simpandas.frame import SimDataFrame

__all__ = ['read_parquet']

log = logging.getLogger(__name__)


def read_parquet(filepath,
                 columns=None,
                 units=None,
                 indexUnits=None,
                 nameSeparator=None,
                 intersectionCharacter=None,
                 verbose=False,
                 **kwargs):
    """
    Read a Parquet file into a ``SimDataFrame`` with units.

    Parameters
    ----------
    filepath : str or path-like
        Path to a ``.parquet`` file.
    columns : list[str] or None
        Subset of columns to read.  *None* reads all columns.
    units : dict or None
        Override / supply ``{column: unit}`` mapping.  When *None* the
        reader looks for ``simpandas:units`` in the Parquet metadata.
    indexUnits : str or None
        Override / supply index units.  When *None* the reader looks
        for ``simpandas:index_units`` in the Parquet metadata.
    nameSeparator, intersectionCharacter
        Forwarded to ``SimDataFrame``.
    verbose : bool
        Log progress messages.
    **kwargs
        Extra keyword arguments forwarded to ``pandas.read_parquet``.

    Returns
    -------
    SimDataFrame
    """
    df = pd.read_parquet(filepath, columns=columns, **kwargs)

    # --- Extract units from Parquet metadata if not supplied ---
    meta_units = {}
    meta_index_units = None

    try:
        import pyarrow.parquet as pq
        pf = pq.read_metadata(filepath)
        raw_meta = pf.metadata
        if raw_meta:
            if b'simpandas:units' in raw_meta:
                meta_units = json.loads(
                    raw_meta[b'simpandas:units'].decode('utf-8'))
            if b'simpandas:index_units' in raw_meta:
                meta_index_units = raw_meta[
                    b'simpandas:index_units'].decode('utf-8')
    except ImportError:
        # pyarrow not available — try fastparquet
        try:
            import fastparquet
            pf = fastparquet.ParquetFile(str(filepath))
            kv_meta = pf.key_value_metadata or {}
            if 'simpandas:units' in kv_meta:
                meta_units = json.loads(kv_meta['simpandas:units'])
            if 'simpandas:index_units' in kv_meta:
                meta_index_units = kv_meta['simpandas:index_units']
        except (ImportError, Exception):
            pass
    except Exception:
        pass

    if units is None:
        units = meta_units
    if indexUnits is None and meta_index_units:
        indexUnits = meta_index_units

    if verbose:
        log.info('read_parquet: %d rows × %d cols, %d units',
                 len(df), len(df.columns), len(units))

    kw = {}
    if nameSeparator is not None:
        kw['name_separator'] = nameSeparator
    if intersectionCharacter is not None:
        kw['intersection_character'] = intersectionCharacter

    return SimDataFrame(data=df,
                        units=units or {},
                        index_units=indexUnits or '',
                        **kw)
