# -*- coding: utf-8 -*-
"""
Created on Sun Oct 11 11:14:32 2020

@author: Martin Carlos Araya
"""

__version__ = '0.80.1'
__release__ = 220811
#__all__ = ['SimSeries', 'SimDataFrame', 'read_excel', 'concat', 'znorm', 'minmaxnorm']

from ._classes.series import SimSeries
from ._classes.frame import SimDataFrame
from ._readers import read_excel