# -*- coding: utf-8 -*-
"""
SimPandas: Unit-aware pandas DataFrames and Series.

This package extends pandas DataFrame and Series with automatic unit tracking
and conversion capabilities. It preserves physical units through arithmetic
operations, I/O, and data transformations.

Main classes:
- SimDataFrame: Unit-aware DataFrame
- SimSeries: Unit-aware Series
- SimIndex: Unit-aware Index

I/O functions:
- read_excel, write_excel: Excel with units
- read_csv, write_csv: CSV with units
- read_json, write_json: JSON with units
- And more for HDF5, Parquet, etc.

Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.90.12'
__release__ = 20260503
__all__ = ['SimSeries', 'SimDataFrame', 'ColumnUnits', 'read_excel', 'read_csv', 'read_json',
           'read_hdf5', 'read_summary', 'read_vdb', 'read_parquet',
           'read_prodml', 'read_witsml', 'read_resqml', 'read_schedule', 'read_auto', 'concat']

from .series import SimSeries
from .frame import SimDataFrame
from .index import SimIndex
from .readers import (read_excel, read_csv, read_json, read_hdf5, read_summary,
                      read_vdb, read_parquet, read_prodml, read_witsml, read_resqml,
                      read_schedule, read_auto)
from .common.merger import concat
from .common.units import ColumnUnits

