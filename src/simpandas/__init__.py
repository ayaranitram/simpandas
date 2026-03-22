# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.84.0'
__release__ = 20260303
__all__ = ['SimSeries', 'SimDataFrame', 'read_excel', 'read_csv', 'read_json', 'concat']

# On Python 3.14, recent Unyts versions enable parallel dictionary/network
# build by default. In practice this can consume excessive RAM on some setups.
# Keep a safe default unless the user explicitly overrides it.
import os
os.environ.setdefault('UNYTS_PARALLEL_3_14', '0')

from .series import SimSeries
from .frame import SimDataFrame
from .index import SimIndex
from .readers import read_excel, read_csv, read_json
from .common.merger import concat
