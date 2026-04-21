# -*- coding: utf-8 -*-
"""
Created on Wed Aug  3 20:24:36 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.1.5'
__release__ = 20260418

from simpandas.readers.xlsx import read_excel
from simpandas.readers.csv import read_csv
from simpandas.readers.json import read_json
from simpandas.readers.h5 import read_hdf5
from simpandas.readers.summary import read_summary
from simpandas.readers.vdb import read_vdb
from simpandas.readers.parquet import read_parquet
from simpandas.readers.prodml import read_prodml
from simpandas.readers.witsml import read_witsml
from simpandas.readers.resqml import read_resqml