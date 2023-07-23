import simpandas as spd

sample_prod = spd.read_excel('./_testing_data/sample_prod.xlsx')
sample_prod.set_index('DATE', inplace=True)

data = spd.SimDataFrame({'A':[1,2,3], 'B':[3,2,1]},
                        units={'A':'m', 'B': 'in'},
                        index=['2023-01-01', '2023-01-05', '2023-01-07'])


