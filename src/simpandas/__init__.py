# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.2'
__release__ = 20220919
__all__ = ['SimSeries', 'SimDataFrame', 'read_excel']

from ._classes.series import SimSeries
from ._classes.frame import SimDataFrame
from ._readers import read_excel