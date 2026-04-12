import simpandas as spd
from pandas import date_range
s = spd.SimSeries([1,2,3], index=date_range('2100-01-08', periods=3), units='m', index_units='date')
print('name', s.name)
print('get_units', s.get_units())
print('get_units_string(name)', s.get_units_string(s.name))
print('get_units_string()', s.get_units_string())
val = s.loc['2100-01-08']
print('loc, type', type(val), val)
print('has value', hasattr(val,'value'), getattr(val,'value',None), getattr(val,'unit',None))
