# import packages
import matplotlib
matplotlib.use('Agg')  # non-interactive backend — no pop-up windows
import simpandas as spd
from matplotlib import pyplot as plt

# read data
data0 = r'test\_testing_data\SAMPLE_PROD.SMSPEC'
df0 = spd.read_auto(data0)
data1 = r'test\_testing_data\SAMPLE_PROD.SMSPEC'
df1 = spd.read_auto(data1)

# plot WOPR for the first well using Pandas
w = df1.wells[0]
ax = df1['WOPR:'+w].as_pandas().plot(title=w)
df0['WOPR:'+w].as_pandas().plot(ax=ax)
assert ax is not None
plt.close('all')

# plot WOPR for the second well using SimPandas
w = df1.wells[1]
ax = df1['WOPR:'+w].plot(title=w)
df0['WOPR:'+w].plot(ax=ax)
assert ax is not None
plt.close('all')

# plot WOPR for the third well using SimPandas (label= parameter)
w = df1.wells[-1]
ax = df1['WOPR:'+w].plot(title=w, label='DF1')
df0['WOPR:'+w].plot(ax=ax, label='DF0')
assert ax is not None
plt.close('all')
