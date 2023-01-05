# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.10'
__release__ = 20230104
__all__ = ['SimSeries', 'SimDataFrame', 'read_excel', 'concat']

from .series import SimSeries
from .frame import SimDataFrame
from .readers import read_excel
from .common.merger import concat