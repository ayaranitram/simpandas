import simpandas as spd
import unyts
import pandas as pd

# create a dummy Seres
s = pd.Series([1,2,3])

# create dummy unyts instance
f = unyts.units(1.0, 'ft')
i = unyts.units(1.0, 'in')
# test addition of unyts instances
print(f"f+i={f+i}")
print(f"i+f={i+f}")


# add unyts + Series
# no conversion is expected, since the Series is not units aware
print(f"{type(f+s)=} {f+s=}")
print(f"{type(s+f)=} {s+f=}")

# create a dummy SimSeries
ss = spd.SimSeries(s, units='yd')

# add unyts + SimSeries
# conversion is expected, since the SimSeries is units aware
print(f"{type(f+ss)=} {f+ss=}")  # fails to convert because unyts doesn't identify ss as a SimSeries
print(f"{type(ss+f)=} {ss+f=}")  # correctly converts units