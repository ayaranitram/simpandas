import simpandas as spd
sample_prod0 = spd.read_excel('./test/_testing_data/sample_prod.xlsx')
print(f"{sample_prod0.units=}")
print(f"{sample_prod0.index.units=}")

sample_prod1 = sample_prod0.set_index('DATE')
print(f"{sample_prod1.units=}")
print(f"{sample_prod1.index.units=}")

sample_prod2 = spd.read_excel('./test/_testing_data/sample_prod.xlsx')
sample_prod2.set_index('DATE', inplace=True)
print(f"{sample_prod2.units=}")
print(f"{sample_prod2.index.units=}")

assert sample_prod0.index.units == ''
assert sample_prod1.index.units == 'date'
assert sample_prod2.index.units == 'date'

assert sample_prod1.units == sample_prod2.units