# -*- coding: utf-8 -*-
"""
Created on Sun Feb 12 00:59:53 2023

@author: martin
"""

import simpandas as spd

sample_prod = spd.read_excel('D:/git/simpandas/test/_testing_data/sample_prod.xlsx')
sample_prod.set_index('DATE', inplace=True)

sample_prod['WOPR:P1']
sample_prod[['WOPR:P1']]
sample_prod[['WOPR:P1', 'WOPR:P2']]
sample_prod['WOPR:P1', 'WOPR:P2']
sample_prod['WOPR']
sample_prod['P1']
sample_prod['WWPR:P1':'WOPR:P2']
sample_prod['W?PR*2']
sample_prod['2100-04-09']
sample_prod.loc['2100-12-24', 'P1']
sample_prod['2100-04', 'P1']
sample_prod['2100-04']
sample_prod['2100']




sample_prod['2100-04']
sample_prod['P1']
sample_prod.loc['2100-12-24', 'P1']


sample_prod['P1'].loc['2100-04']
sample_prod.loc['2100-04', 'WOPR:P1']

sample_prod.loc[:,'WOPR:P1']

sample_prod.loc[:,'P1']
sample_prod.loc['2100-04']
sample_prod.loc['2100-04':'2100-06']
sample_prod.loc['2100-04','WOPR:P1']
sample_prod.loc['2100-04','P1']
sample_prod.loc['2100-04-09']
sample_prod['WOPR:P1']

sample_prod.loc[:,:]

sample_prod.iloc[3]
sample_prod.iloc[0:3]



sample_prod.iloc[6,0]
