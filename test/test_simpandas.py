# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 22:34:40 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas import SimDataFrame, SimSeries

data = {'A': [1,2,3,4,5],
        'B': [1.0, 2.0, 3.0, 4.0, 5.0],
        'C': [100, 200, 300, 400, 500],
        'D': [3, 6, 12, 24, 36]}
units = {'A': 'ml',
         'B': 'cc',
         'C': 'cm',
         'D': 'in'}

sdf = SimDataFrame(data, units)

sdf['C3'] = (sdf['C']**3).to('m3')
ss = SimSeries