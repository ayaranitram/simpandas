# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.5'
__release__ = 20220924
__all__ = ['SimSeries', 'SimDataFrame']

from .classes.series import SimSeries
from .classes.frame import SimDataFrame
from .readers import read_excel