# SimPandas — User Manual

**Version 0.90.5 | Python ≥ 3.7 | pandas 1.3 – 2.x**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Core Concepts](#3-core-concepts)
4. [SimDataFrame](#4-simdataframe)
   - 4.1 [Creating a SimDataFrame](#41-creating-a-simdataframe)
   - 4.2 [Units](#42-units)
   - 4.3 [Indexing and Selection](#43-indexing-and-selection)
   - 4.4 [Arithmetic and Unit Arithmetic](#44-arithmetic-and-unit-arithmetic)
   - 4.5 [Aggregation](#45-aggregation)
   - 4.6 [Transformation Methods](#46-transformation-methods)
   - 4.7 [Sorting and Ranking](#47-sorting-and-ranking)
   - 4.8 [Reshaping](#48-reshaping)
   - 4.9 [GroupBy](#49-groupby)
   - 4.10 [Window Operations](#410-window-operations)
   - 4.11 [Comparison and Filtering](#411-comparison-and-filtering)
   - 4.12 [Time-Series Utilities](#412-time-series-utilities)
   - 4.13 [Normalisation Helpers](#413-normalisation-helpers)
   - 4.14 [Copying, Casting, and Cleaning](#414-copying-casting-and-cleaning)
   - 4.15 [Iteration](#415-iteration)
   - 4.16 [Visualisation](#416-visualisation)
5. [SimSeries](#5-simseries)
   - 5.1 [Creating a SimSeries](#51-creating-a-simseries)
   - 5.2 [Units on a Series](#52-units-on-a-series)
   - 5.3 [Arithmetic](#53-arithmetic)
   - 5.4 [Window Operations](#54-window-operations)
   - 5.5 [Conversion Methods](#55-conversion-methods)
   - 5.6 [Time-Series Aggregations](#56-time-series-aggregations)
6. [SimIndex](#6-simindex)
7. [I/O Reference](#7-io-reference)
   - 7.1 [Excel](#71-excel)
   - 7.2 [CSV](#72-csv)
   - 7.3 [JSON](#73-json)
   - 7.4 [HDF5](#74-hdf5)
   - 7.5 [Eclipse Binary Summary (.SMSPEC / .UNSMRY)](#75-eclipse-binary-summary-smspec--unsmry)
   - 7.6 [VDB Plot Data (.vdb)](#76-vdb-plot-data-vdb)
   - 7.7 [Apache Parquet](#77-apache-parquet)
   - 7.8 [PRODML XML](#78-prodml-xml)
   - 7.9 [WITSML XML](#79-witsml-xml)
   - 7.10 [RESQML EPC](#710-resqml-epc)
8. [Column-Name Conventions](#8-column-name-conventions)
   - 8.1 [Name Separator](#81-name-separator)
   - 8.2 [Intersection Character](#82-intersection-character)
   - 8.3 [Helper Functions](#83-helper-functions)
9. [Unit Conversion Reference](#9-unit-conversion-reference)
10. [Full Method Reference](#10-full-method-reference)
11. [Frequently Asked Questions](#11-frequently-asked-questions)
12. [Practical Recipes](#12-practical-recipes)
13. [Troubleshooting](#13-troubleshooting)
14. [Public API Catalog](#14-public-api-catalog)

---

## 1. Introduction

SimPandas is a Python library that extends **pandas** `DataFrame` and `Series`
with _unit tracking_.  Each column (or a Series as a whole) has a physical unit
string attached.  Units are preserved through arithmetic, aggregation, window
operations, I/O, and most pandas transformations — so you never accidentally add
metres to kilograms or lose track of what "column A" means after a `groupby`.

The library is particularly suited to reservoir-engineering and scientific
workflows that produce tables of quantities (pressures, flow rates, depths,
temperatures, …) where unit correctness is critical.

SimPandas builds on:

| Dependency | Role |
|---|---|
| `pandas` | Core data structures and algorithms |
| `numpy` | Array maths |
| `unyts` | Unit definitions, conversion, and arithmetic |
| `matplotlib` / `seaborn` | Plotting helpers |
| `openpyxl` / `xlsxwriter` | Excel I/O |

---

## 2. Installation

```bash
pip install simpandas          # latest stable
pip install --upgrade simpandas
```

Editable (development) install from source:

```bash
git clone https://github.com/ayaranitram/simpandas.git
cd simpandas
pip install -e .
```

---

## 3. Core Concepts

### Units
Units are plain strings such as `'m'`, `'psi'`, `'m3/day'`, `'degC'`.
They are stored per-column on a `SimDataFrame` and as a single string on a
`SimSeries`.  String values that are not recognised by `unyts` are stored
but ignored during arithmetic — arithmetic still works; unit tracking just
does not apply.

### Metadata propagation (`params_`)
Every `SimDataFrame` / `SimSeries` carries a `params_` dictionary that collects
all metadata keys.  Whenever a new object is constructed from an operation
the constructor is called with `**self.params_` so that _name_, _units_,
_index units_, _separators_, _flags_, … are carried through automatically.

### The `_rewrap` pattern
Any pandas operation that returns a plain `pd.DataFrame` or `pd.Series` is
immediately converted back to a Sim type via the internal `_rewrap()` helper.
You should never encounter a bare pandas type as the result of a SimPandas
method call.

### `SimBasics` mixin
Both `SimDataFrame` and `SimSeries` inherit from `SimBasics`.  Methods defined
there apply to both types.  Type-specific methods live in `SimDataFrame` and
`SimSeries` respectively.

---

## 4. SimDataFrame

### 4.1 Creating a SimDataFrame

```python
from simpandas import SimDataFrame

# From a dict — most common
df = SimDataFrame(
    {'pressure': [100, 200, 300],
     'depth':    [1000, 2000, 3000],
     'zone':     ['A', 'A', 'B']},
    units={'pressure': 'psi', 'depth': 'ft', 'zone': None}
)

# From an existing pandas DataFrame
import pandas as pd
pdf = pd.DataFrame({'x': [1, 2, 3]})
df = SimDataFrame(pdf, units='m')         # all columns get 'm'
df = SimDataFrame(pdf, units={'x': 'm'})  # per-column

# From a CSV / Excel file (see Section 7 for full I/O)
from simpandas import read_csv, read_excel
df = read_csv('data.csv', units=0)        # row 0 is the units row
df = read_excel('data.xlsx', units=1)     # row 1 is the units row
```

**Constructor keywords**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | dict / DataFrame / … | — | Input data (same as pandas) |
| `index` | array-like / Index | — | Row labels |
| `columns` | array-like | — | Column labels |
| `units` | str / dict / None | `None` | Column units |
| `dtype` | dtype | `None` | Force a dtype |
| `name` | str | `None` | Object name |
| `index_name` | str | `None` | Name for the index axis |
| `index_units` | str | `None` | Units for the index values |
| `name_separator` | str | `':'` | Separator in structured column names |
| `intersection_character` | str | `'&'` | Character for name intersections |
| `auto_append` | bool | `False` | Auto-append rows on `.loc` assignment |
| `operate_per_name` | bool | `False` | Apply operations per name component |
| `verbose` | bool | `False` | Log informational messages |
| `meta` | any | `None` | Arbitrary metadata payload |
| `source_path` | str | `None` | Path the data was loaded from |
| `return_singles` | bool | `None` | Return scalars for single-element results |

---

### 4.2 Units

```python
# Read units — returns a ColumnUnits object (ordered, positional)
df.units              # ColumnUnits({'pressure': 'psi', 'depth': 'ft'})
df.units['pressure']  # 'psi'
df.units.to_dict()    # plain dict (last value wins for duplicate column names)
df.units.to_list()    # positional list — safe even for duplicate column names
df.get_units()        # same as .units
df.get_units('depth') # unit for a single column
df.get_units_string('pressure')  # unit string for a column (never None)

# Set units
df.units = {'pressure': 'psi', 'depth': 'm'}
df.set_units({'pressure': 'bar'})  # partial update is fine

# Inspect index units
df.index_units
df.get_index_units()

# Convert a column to different units (returns a new object)
df_metric = df.to('bar')         # convert all convertible columns
df_metric = df.convert('bar')    # equivalent

# Handle duplicate column names
df.columns = ['BHP', 'BHP', 'GRAT']   # two identical names
clean = df.deduplicate_columns()        # BHP, BHP_1, GRAT
df.deduplicate_columns(inplace=True)   # modifies df in place
```

Units participate in arithmetic automatically:

```python
rate = SimDataFrame({'q': [100, 200]}, units='STB/day')
time = SimDataFrame({'t': [30, 60]}, units='day')
volume = rate * time  # units → 'STB'
```

---

### 4.3 Indexing and Selection

SimPandas overrides `.loc` and `.iloc` with custom indexers that perform
unit conversion and metadata propagation.

```python
# Standard label-based selection
row = df.loc[0]           # → SimSeries
subset = df.loc[0:2, 'pressure']  # → SimSeries

# Setting with a value+unit tuple
df.loc[0, 'depth'] = (500, 'm')   # converts to the column's unit automatically

# Position-based
df.iloc[0, 1]             # scalar wrapped as a unyts Unit object

# Column selection (same as pandas)
df['pressure']            # → SimSeries
df[['pressure', 'depth']] # → SimDataFrame

# Boolean filter
df[df['pressure'] > 150]  # → SimDataFrame
```

---

### 4.4 Arithmetic and Unit Arithmetic

All standard Python arithmetic operators are supported and propagate units:

```python
df + other   # add
df - other   # subtract
df * other   # multiply  (units multiply)
df / other   # divide    (units divide)
df ** n      # power     (units raised to power n)
```

Named arithmetic methods:

| Method | Operator | Notes |
|--------|----------|-------|
| `add(other, ...)` | `+` | Unit addition |
| `sub(other, ...)` | `-` | Unit subtraction |
| `mul(other, ...)` | `*` | Unit multiplication |
| `truediv(other, ...)` | `/` | Unit division |
| `floordiv(other, ...)` | `//` | Floor division |
| `mod(other, ...)` | `%` | Modulo |
| `pow(other, ...)` | `**` | Power |

`other` may be a scalar, a plain `pd.Series`/`pd.DataFrame`, or another Sim
object.  When `other` is a Sim object with convertible units, conversion is
applied automatically before the operation.

Unary helpers:

```python
df.neg()   # element-wise negation (-df)
df.inv()   # element-wise inversion (1/df), units inverted
df.abs()   # element-wise |df|
df.int()   # cast to int
```

---

### 4.5 Aggregation

All aggregation methods return a `SimSeries` (axis=0) or scalar, preserving
the appropriate unit.

```python
df.sum()           # sum per column
df.mean()          # mean per column
df.min()           # minimum per column
df.max()           # maximum per column
df.std()           # standard deviation
df.var()           # variance
df.median()        # median
df.prod()          # product
df.quantile(0.75)  # 75th percentile
df.count()         # non-null count
df.rms()           # root-mean-square

# Named variants (axis=0 is the default for SimPandas)
df.mean0()   df.sum0()   df.std0()   df.min0()   df.max0()
df.avg()     df.average() df.avg0()  df.count0()  df.rms0()

# Statistical moment
df.skew()          # skewness
df.kurtosis()      # kurtosis  (alias: df.kurt())
df.sem(ddof=1)     # standard error of the mean

# Describe
df.describe()      # → SimDataFrame  summary statistics

# Index of extremes
df.idxmin()        # index label of minimum
df.idxmax()        # index label of maximum
```

---

### 4.6 Transformation Methods

Functions that produce a result of the same shape — units are copied from the
source column.

```python
# Apply an arbitrary function column-by-column (axis=0) or row-by-row (axis=1)
df.apply(np.sqrt)
df.apply(lambda s: s - s.mean(), axis=0)

# Same-shape transform (like apply but must return same-shape result)
df.transform('log')
df.transform(lambda x: (x - x.mean()) / x.std())

# Chainable pipe  (function receives the whole DataFrame)
df.pipe(lambda d: d * 2).pipe(lambda d: d + 1)

# Element-wise function
df.map(lambda x: round(x, 2))

# Cumulative
df.cumsum()
df.cummax()
df.cummin()
df.cumprod()

# Diff
df.diff(periods=1)   # first discrete difference

# Shift / lag
df.shift(periods=1)
```

---

### 4.7 Sorting and Ranking

```python
df.sort_values('pressure', ascending=False)
df.sort_index()
df.sort_index(ascending=False)

df.rank()               # rank within each column
df.rank(pct=True)       # percentile rank

df.nlargest(5, columns='pressure')   # top 5 rows by 'pressure'
df.nsmallest(3, columns='depth')     # bottom 3 rows by 'depth'
```

---

### 4.8 Reshaping

```python
# Stack / unstack
stacked = df.stack()         # → SimSeries (columns become inner index level)
df2 = stacked.unstack()      # reverse

# Pivot (long → wide)
df.pivot(index='date', columns='zone', values='pressure')

# Pivot table (aggregated)
df.pivot_table(values='pressure', index='zone', aggfunc='mean')

# Melt (wide → long)
df.melt(id_vars=['zone'], value_vars=['pressure', 'depth'],
        var_name='parameter', value_name='value')

# Explode list-like cells
df_lists = SimDataFrame({'tags': [['a', 'b'], ['c']]})
df_lists.explode('tags')

# Merge
df1.merge(df2, on='id', how='inner')

# Join (index-based)
df1.join(df2, how='left')

# String-based filter/query
df.query('pressure > 200 and zone == "A"')

# Expression evaluation
df.eval('ratio = pressure / depth')    # adds a 'ratio' column
```

---

### 4.9 GroupBy

```python
gb = df.groupby('zone')

gb.sum()
gb.mean()
gb.median()
gb.std()
gb.var()
gb.min()
gb.max()
gb.count()
gb.first()
gb.last()

# Aggregate with a function or dict
gb.agg('sum')
gb.agg({'pressure': 'mean', 'depth': 'max'})

# Apply a function that receives each group as a DataFrame
gb.apply(lambda g: g.nlargest(1, columns='pressure'))

# Transform (same-index result)
df['pressure_norm'] = gb['pressure'].transform(lambda x: (x - x.mean()) / x.std())

# Filter (keep groups satisfying a predicate)
gb.filter(lambda g: len(g) >= 2)

# Iterate
for group_key, group_df in gb:
    print(group_key, type(group_df))   # group_df is SimDataFrame

# Column sub-selection
gb['pressure'].mean()   # → SimSeries
```

---

### 4.10 Window Operations

All three window types return a proxy object; call aggregation methods on the
proxy.

```python
# Rolling (fixed window)
df.rolling(window=5).mean()
df.rolling('7D').sum()         # time-based window

# Expanding (grows from the start)
df.expanding(min_periods=3).std()

# Exponentially Weighted (EWM)
df.ewm(span=10).mean()
df.ewm(alpha=0.3).var()
df.ewm(halflife=5).std()
```

All aggregation methods available on the pandas window objects work and return
Sim types:

```
mean  sum  std  var  min  max  median  count  corr  cov  apply  ...
```

---

### 4.11 Comparison and Filtering

```python
# Boolean masks
df == other   # element-wise equal
df != other
df >  other
df >= other
df <  other
df <= other

# Conditional replacement
df.where(df > 0)           # keep values > 0, NaN elsewhere
df.where(df > 0, other=-1) # replace failing values with -1
df.mask(df < 0)            # NaN where < 0
df.mask(df < 0, other=0)   # replace with 0

# Clip to bounds
df.clip(lower=0, upper=100)

# Drop NaN
df.dropna()
df.dropna(axis=1)

# Fill NaN
df.fillna(0)
df.fillna(method='ffill')
df.ffill()
df.bfill()

# Element-wise membership (boolean SimDataFrame)
df.isin([0, 1, 2])

# Compare / merge-style helpers
df.compare(other_df)
df.combine_first(other_df)

# Pairwise alignment
left, right = df.align(other_df, join='outer')

# Interpolate
df.interpolate(method='linear')

# Sample
df.sample(n=10)
df.sample(frac=0.1, random_state=42)

# Remove duplicates
df.drop_duplicates()
df.drop_duplicates(subset=['zone'])

# Unique counts
df.nunique()          # → SimSeries  count per column
df['zone'].value_counts()  # → SimSeries  frequency count
```

---

### 4.12 Time-Series Utilities

When the index contains dates, SimPandas provides resampling / aggregation
helpers:

```python
# Native pandas wrappers with Sim metadata
df.resample('D').mean()   # resample by day
df.asfreq('H')            # reindex to hourly frequency

# SimPandas convenience helpers
df.daily(agg='mean')    # daily mean
df.monthly(agg='sum')   # monthly sum
df.yearly(agg='last')   # one value per year

# date math helpers (also available as module-level functions)
from simpandas.common.daterelated import days_in_year, days_in_month
```

Linear interpolation to an arbitrary date / index vector:

```python
df.interpolate(method='slinear', axis='index')
```

---

### 4.13 Normalisation Helpers

```python
df.znorm()        # z-score normalisation per column
df.znorm0()       # same, axis=0 explicit
df.minmaxnorm()   # min-max scale to [0, 1]
df.jitter(std=0.10)  # add Gaussian jitter (useful for visualisation)
```

---

### 4.14 Copying, Casting, and Cleaning

```python
df.copy()                    # deep copy
df.copy(deep=False)          # shallow copy

df.astype(float)             # cast all columns
df.astype({'pressure': float, 'depth': int})

df.round(decimals=2)
df.abs()
df.int()    # shortcut for astype(int)

df.replace(to_replace=np.nan, value=0)
```

Converting between types:

```python
df.to_dataframe()      # plain pandas DataFrame
df.as_dataframe()      # same (no copy)
df.to_simseries()      # only valid when df has exactly one column
```

---

### 4.15 Iteration

```python
# Iterate rows as (index, SimSeries) pairs
for idx, row in df.iterrows():
    print(idx, row.units)

# Iterate rows as namedtuples
for row in df.itertuples():
    print(row)

# Concatenate multiple DataFrames
from simpandas import concat
combined = concat([df1, df2], axis=0)
combined = concat([df1, df2], axis=1)

# Concatenate using the instance method
df1.concat(df2)           # appended as rows
df1.concat([df2, df3])    # multiple objects
```

---

### 4.16 Visualisation

SimDataFrame inherits all pandas / matplotlib plotting functionality.
Units are included in auto-generated axis labels when `verbose=True`.

```python
df.plot()
df['pressure'].plot(kind='hist')
df.plot.scatter('depth', 'pressure')
```

---

## 5. SimSeries

### 5.1 Creating a SimSeries

```python
from simpandas import SimSeries

s = SimSeries([100, 200, 300], units='psi', name='pressure')
s = SimSeries({'a': 1, 'b': 2}, units='m')

# From a pandas Series
import pandas as pd
ps = pd.Series([1.0, 2.0, 3.0])
s = SimSeries(ps, units='kg')
```

### 5.2 Units on a Series

```python
s.units           # unit string (or dict for multi-column history)
s.get_units()     # always returns the unit string
s.set_units('bar')
s.to('bar')       # convert and return new SimSeries
s.convert('bar')  # equivalent
```

### 5.3 Arithmetic

All operators available on `SimDataFrame` work on `SimSeries` as well:

```python
s + other   s - other   s * other   s / other
s.add(other)  s.sub(other)  s.mul(other)  s.truediv(other)
```

Comparison methods return boolean `SimSeries`:

```python
s.eq(other)   # ==
s.ne(other)   # !=
s.gt(other)   # >
s.ge(other)   # >=
s.lt(other)   # <
s.le(other)   # <=
```

### 5.4 Window Operations

```python
s.rolling(5).mean()
s.expanding(3).sum()
s.ewm(span=10).mean()
s.resample('D').mean()
```

### 5.5 Conversion Methods

```python
s.to_series()          # plain pandas Series
s.as_series()          # same (no copy)
s.to_simdataframe()    # wrap in a one-column SimDataFrame
s.to_frame()           # alias
```

### 5.6 Time-Series Aggregations

When the index is datetime-like:

```python
s.daily(agg='mean')
s.monthly(agg='sum')
s.yearly(agg='mean')
s.reindex(new_index)
```

Statistical methods are inherited from `SimBasics`:

```python
s.mean()  s.std()  s.min()  s.max()  s.sum()  s.prod()
s.quantile(0.5)  s.cumsum()  s.diff()  s.shift()
s.pct_change()   s.between(100, 300)
s.asfreq('D')

s.unique()        # NumPy array of unique values
s.value_counts()  # frequency count
s.nunique()       # count of distinct values
```

Slope utilities:

```python
s.slope()              # linear slope over the whole series
s.slope(window=5)      # rolling slope
```

---

## 6. SimIndex

`SimIndex` is a `pd.MultiIndex` subclass that carries a `units` attribute.
It is used internally when the index should have a physical unit (e.g. depths
in metres).

```python
from simpandas.index import SimIndex

idx = SimIndex([(0, 100), (0, 200)], units='m')
df = SimDataFrame({'pressure': [10, 20]}, index=idx, index_units='m')

# Convert the index
df.index_to('ft')  # returns a new df with converted index
df.to('ft')        # converts columns; use index_to for indices
```

---

## 7. I/O Reference

### 7.1 Excel

```python
from simpandas import read_excel
from simpandas.writers.xlsx import write_excel

# Read
df = read_excel('welldata.xlsx')                   # first data row is units
df = read_excel('welldata.xlsx', units=1)          # row 1 is units
df = read_excel('welldata.xlsx', sheet_name='Q1')

# Write
write_excel(df, 'output.xlsx')                     # units row written automatically
write_excel(df, 'output.xlsx', sheet_name='Data', units=True)

# Split into one sheet per column-name prefix
write_excel(df, 'output.xlsx', split_by='left')    # left side of `:` separator
write_excel(df, 'output.xlsx', split_by='right')
write_excel(df, 'output.xlsx', split_by=2)         # first 2 characters
```

`read_excel` parameter highlights:

| Parameter | Default | Description |
|---|---|---|
| `units` | `1` | Row number (0-based) containing units, or `None` |
| `indexUnits` | `None` | Units for the index column |
| `nameSeparator` | `None` | Column-name separator |
| `intersectionCharacter` | `'∩'` | Intersection character |
| `autoAppend` | `False` | Auto-append behaviour |
| `transposed` | `False` | Whether the data is stored in transposed form |

### 7.2 CSV

```python
from simpandas import read_csv

# Units embedded as first data row
df = read_csv('data.csv', units=0)

# Units supplied as a dict
df = read_csv('data.csv', units={'depth': 'm', 'pressure': 'psi'})

# No units
df = read_csv('data.csv')

# All standard pandas.read_csv kwargs are forwarded
df = read_csv('data.csv', index_col=0, parse_dates=['date'], units=0)
```

Writing:

```python
df.to_csv('output.csv')          # standard pandas CSV
```

When units are present and a filename is given, a units row is injected after
the header before the data rows, making the file round-tippable via
`read_csv(..., units=0)`.

### 7.3 JSON

```python
from simpandas import read_json

# SimPandas JSON format (units embedded)
df.to_json('output.json')     # writes {"data": {...}, "units": {...}}
df2 = read_json('output.json')  # units restored automatically

# Plain pandas JSON
df = read_json('plain.json', units={'x': 'm'})

# String round-trip
json_str = df.to_json()        # returns JSON string when no path given
df2 = read_json(json_str)
```

### 7.4 HDF5

```python
from simpandas import read_hdf5
from simpandas.writers.h5 import write_hdf5

# Write (stores data, units, and index_units with gzip compression)
df.to_hdf5('output.h5')

# Read (units restored automatically)
df2 = read_hdf5('output.h5')
```

Requires `h5py` (`pip install h5py`).

### 7.5 Eclipse Binary Summary (.SMSPEC / .UNSMRY)

`read_summary` reads the pair of binary files produced by Eclipse, OPM Flow,
and other reservoir simulators.  Column names follow the
`KEYWORD:WGNAME` convention used across the simulator output files:

| Vector type | Example column name | Description |
|---|---|---|
| Field | `FOPR` | Field Oil Production Rate |
| Well | `WBHP:PROD1` | Well Bottom-Hole Pressure |
| Group | `GOPR:PLATFORM-A` | Group Oil Production Rate |
| Region | `RPR:3` | Region Pressure (region 3) |
| Completion | `COPR:PROD1:2` | Completion Oil Prod Rate |
| Block | `BPR:5,6,7` | Block Pressure at i=5,j=6,k=7 |

The reader computes a `DATE` column from `STARTDAT + TIME` and promotes it
to the index, yielding a `DatetimeIndex`.

Grid dimensions (`nx`, `ny`, `nz`) and the simulation start date are
automatically stored in `sdf.meta` for transparent write-back.

```python
from simpandas import read_summary
from simpandas.writers.summary import write_summary

# Read
sdf = read_summary('CASE.SMSPEC')
print(sdf.index.name)   # 'DATE'
print(sdf.meta)         # {'dimens': [50, 60, 20], 'startdat': [1, 1, 2020]}

# Access vectors
print(sdf[['FOPR', 'WBHP:PROD1']].head())

# Write back — dimens and startdat are taken from sdf.meta automatically
sdf.to_summary('OUTPUT.SMSPEC')

# Equivalent explicit call (needed if sdf was not produced by read_summary)
write_summary(sdf, 'OUTPUT.SMSPEC',
              startdat=[1, 1, 2020],
              dimens=[50, 60, 20])
```

`read_summary` parameter highlights:

| Parameter | Default | Description |
|---|---|---|
| `smspec_path` | required | Path to `.SMSPEC` file |
| `unsmry_path` | `None` | Explicit path to `.UNSMRY` (auto-discovered when `None`) |
| `nameSeparator` | `':'` | Separator for `KEYWORD:WGNAME` column names |

`write_summary` / `to_summary` parameter highlights:

| Parameter | Default | Description |
|---|---|---|
| `smspec_path` | required | Destination `.SMSPEC` path |
| `unsmry_path` | `None` | Derived from `smspec_path` when `None` |
| `startdat` | from `meta` or `[1,1,1900]` | Simulation start date `[day, month, year]` (Eclipse default: 1 JAN 1900) |
| `dimens` | from `meta` or inferred | Grid dimensions `[nx, ny, nz]` |

---

### 7.6 VDB Plot Data (.vdb)

`read_vdb` reads the NT32 binary plot-data files produced by VIP and Nexus
reservoir simulators.

```python
from simpandas import read_vdb

sdf = read_vdb('RUN.vdb')
# Column names follow VDB variable-description conventions
# Units are extracted from the variable descriptors
```

Requires no additional dependencies beyond the standard library.

### 7.7 Apache Parquet

```python
from simpandas import read_parquet
from simpandas.writers.parquet import write_parquet

# Write (units stored as Parquet metadata)
df.to_parquet('output.parquet')

# Read (units restored automatically)
df2 = read_parquet('output.parquet')
```

Requires `pyarrow` (`pip install pyarrow`).

### 7.8 PRODML XML

`read_prodml` reads PRODML v1/v2 XML files containing production volumes,
time series, and well-test data.

```python
from simpandas import read_prodml
from simpandas.writers.prodml import write_prodml

sdf = read_prodml('production.xml')

# Write (automatically deduplicates column names before serialisation)
write_prodml(sdf, 'output.xml')
# or the instance method
sdf.to_prodml('output.xml')
```

### 7.9 WITSML XML

`read_witsml` reads WITSML v1.4.1.1/v2 XML files: log curves, trajectories,
and mudlogs.

```python
from simpandas import read_witsml
from simpandas.writers.witsml import write_witsml

sdf = read_witsml('welllog.xml')

# Write (automatically deduplicates column names before serialisation)
write_witsml(sdf, 'output.xml')
# or the instance method
sdf.to_witsml('output.xml')
```

### 7.10 RESQML EPC

`read_resqml` reads RESQML v2 EPC packages containing continuous/discrete
property time series.

```python
from simpandas import read_resqml
from simpandas.writers.resqml import write_resqml

sdf = read_resqml('model.epc')

write_resqml(sdf, 'output.epc')
# or
sdf.to_resqml('output.epc')
```

Requires `h5py` (`pip install h5py`).

---

## 8. Column-Name Conventions

SimPandas is designed to work with Eclipse-style reservoir-simulator column
names such as `WOPR:WELL-A` (keyword `:` well name) or `FGPR&FOPR:FIELD`
(intersection of two mnemonics).

### 8.1 Name Separator

The `name_separator` (default `':'`) splits column names into a _left_
(mnemonic) and _right_ (entity) component.

```python
df = SimDataFrame(
    {'WOPR:WELL-A': [100, 200], 'WBHP:WELL-A': [3000, 2900]},
    units={'WOPR:WELL-A': 'STB/day', 'WBHP:WELL-A': 'psi'}
)

df.set_name_separator(':')
df.get_name_separator()     # ':'

# Access structured-name helpers
df.wells            # list of unique right-hand parts that start with 'W'
df.groups           # right-hand parts starting with 'G'
df.regions          # right-hand parts starting with 'R'
df.attributes       # left-hand parts (mnemonics)
df.properties       # left-hand parts (alias)
```

Renaming helpers (in `simpandas.common.renamer`):

```python
from simpandas.common.renamer import left, right, common_rename

right(df)      # {col: right_part_only}
left(df)       # {col: left_part_only}
common_rename(df)  # infer a consistent rename mapping
```

### 8.2 Intersection Character

When two column name components are combined (e.g. after `.add()` on objects
with different left-parts):

```
FOPR&FWPR:FIELD
```

The character between the two mnemonics is the `intersection_character`
(default `'&'`).

### 8.3 Helper Functions

```python
df.rename_left(mapping)    # rename the left-hand part of each column
df.rename_right(mapping)   # rename the right-hand part
```

Deduplication helper (in `simpandas.common.renamer`):

```python
from simpandas.common.renamer import deduplicate_column_names

# Returns a new list with duplicates suffixed _1, _2 …
new_names = deduplicate_column_names(['BHP', 'GOR', 'BHP', 'BHP'])
# ['BHP', 'GOR', 'BHP_1', 'BHP_2']
```

The instance method `SimDataFrame.deduplicate_columns(inplace=False)` calls
this helper and logs a `WARNING` for each renamed column.  Writers that use
dict-based serialisation (JSON, PRODML, WITSML) invoke it automatically before
writing.

---

## 9. Unit Conversion Reference

Unit conversion is provided by the `unyts` library.  SimPandas calls it
transparently; you rarely need to interact with it directly.

```python
# Test whether conversion is possible
from unyts.converter import convertible
convertible('psi', 'bar')    # True
convertible('m', 'kg')       # False

# Convert a whole DataFrame
df.to('bar')            # converts all columns that have units convertible to bar
df.to({'depth': 'm', 'pressure': 'psi'})  # per-column target units

# Convert the index
df.index_to('m')

# Get the current unit string for a column
df.get_units_string('pressure')   # 'psi'
```

Arithmetic unit propagation rules:

| Operation | Result unit |
|---|---|
| `A + B` | same unit (conversion applied if needed) |
| `A - B` | same unit |
| `A * B` | `unit_A * unit_B` |
| `A / B` | `unit_A / unit_B` |
| `A ** n` | `unit_A^n` |
| `1 / A` | `1/unit_A` |

---

## 10. Full Method Reference

This section is a condensed signature list.  Descriptions are in the sections
above.

### SimBasics (shared by SimDataFrame and SimSeries)

#### Properties
```
units            get_units()        get_units_string(key)
set_units(u)     index_units        get_index_units()
set_index_units(u)
labels           params_
name_separator   intersection_character
verbose          meta               source_path
```

#### Indexing
```
.loc[...]        .iloc[...]
```

#### Element / column manipulation
```
copy(deep=True)
abs()            int()              inv()            neg()
round(decimals)  clip(lower, upper)
astype(dtype)    map(func)
where(cond)      mask(cond)
```

#### Arithmetic
```
add(other)       sub(other)         mul(other)
truediv(other)   floordiv(other)    div(other)
mod(other)       pow(other)
```

#### Aggregation
```
sum()     mean()    median()   min()    max()
std()     var()     prod()     count()  quantile(q)
rms()     skew()    kurtosis() kurt()   sem(ddof)
idxmin()  idxmax()
cumsum()  cummax()  cummin()   cumprod()
diff(periods)     shift(periods)
```

#### Stats aliases (axis=0 explicit)
```
avg0()  mean0()  median0()  mode0()  count0()
min0()  max0()   std0()     var0()   sum0()
prod0() quantile0() rms0()  log(base) log0(base)
ln()    log10()  log2()
```

#### Transformation
```
apply(func, axis, ...)    transform(func, axis, ...)
pipe(func, ...)           compare(other, ...)
isin(values)              combine_first(other)
align(other, ...)
```

#### Sorting / ranking
```
sort_values(...)   sort_index(...)
rank(...)          nlargest(n)      nsmallest(n)
```

#### Cleaning
```
drop_duplicates(...)   dropna(...)    fillna(...)     replace(...)
ffill(...)             bfill(...)     interpolate(...)
sample(...)            update(other, ...)
```

#### Descriptive
```
describe()       head(n)          tail(n)
value_counts()   nunique()
```

#### Mathematical
```
znorm()   znorm0()   minmaxnorm()   minmaxnorm0()
jitter(std)
```

#### Concat / join
```
concat(objs, axis, ...)
```

#### Time-series
```
resample(rule, ...)   asfreq(freq, ...)   pct_change(...)
daily(agg)            monthly(agg)        yearly(agg)
```

#### I/O writers (SimBasics — available on both SimDataFrame and SimSeries)
```
to_csv(path, units=True, ...)     to_json(path, ...)
to_hdf5(path, ...)                to_summary(smspec_path, ...)
to_parquet(path, ...)             to_prodml(path, ...)
to_witsml(path, ...)              to_resqml(path)
to_excel(path, ...)               # requires xlsxwriter / openpyxl
```

#### Conversion (SimDataFrame)
```
to_pandas()     as_pandas()
to_dataframe()  as_dataframe()
to_simseries()  as_simseries()
```

#### Conversion (SimSeries)
```
to_pandas()     as_pandas()
to_series()     as_series()
to_simseries()  as_simseries()
to_simdataframe()  as_simdataframe()
to_dataframe()  to_frame()
```

### SimDataFrame-specific

```
rolling(window, ...)    expanding(min_periods, ...)    ewm(span, ...)
resample(rule, ...)     groupby(by, ...)
join(other, how, ...)   merge(right, on, ...)
stack(...)              unstack(...)
pivot(...)              pivot_table(...)    melt(...)
explode(column, ...)
query(expr, ...)        eval(expr, ...)
iterrows()              itertuples()
deduplicate_columns(inplace=False)
```

### SimSeries-specific

```
rolling(window, ...)    expanding(min_periods, ...)   ewm(span, ...)
resample(rule, ...)     groupby(by, ...)
unique()
between(left, right, inclusive)
slope(x, y, window)
corr(other)             reindex(index)
rename(...)             set_index(name)
```

---

## 11. Frequently Asked Questions

**Q: A method returned a plain `pandas.DataFrame` instead of a `SimDataFrame`.
What happened?**

A: This usually means one of these happened:
1. You called a pandas method that is still not wrapped in SimPandas.
2. You used a direct pandas object (`.as_pandas()`) mid-pipeline.
3. A new pandas release changed return behavior for a wrapped method.

Check `WHATS_NEW.md` / `CHANGELOG.md` for current wrapper coverage.
Call `.as_dataframe()` on the result and wrap it:

```python
result = SimDataFrame(df.some_pandas_method(), **df.params_)
```

Please open an issue so the method can be added.

---

**Q: I get a warning about `fastpath` being deprecated.**

A: This is a pandas ≥ 2.0 deprecation in `pd.Series.__init__`.  It will be
removed in a future SimPandas release.  The warning is harmless.

---

**Q: Units are showing as `None` after a groupby.**

A: Pass only the numeric columns to `groupby()`.  Non-numeric columns that are
used as group keys are dropped by pandas after aggregation; their units are
therefore not present in the result.

---

**Q: How do I add a new column with its unit?**

```python
df.loc[:, 'new_col'] = (values, 'kg')   # sets values and unit atomically
# or
df['new_col'] = values
df.set_units({'new_col': 'kg'})
```

---

**Q: Can I use SimPandas with dask or polars?**

A: Not at this time.  SimPandas inherits directly from pandas and relies on
pandas internals.

---

**Q: How do I write a schedule (production data) to a file?**

```python
from simpandas.writers.schedule import write_schedule
write_schedule(df, 'schedule.inc', ...)
```

---

**Q: My `sort_values()` dropped units.**

A: Upgrade to v0.84.0+ where `sort_values` is overridden to use `_rewrap`.

---

## 12. Practical Recipes

### 12.1 Align Two Datasets and Merge

```python
from simpandas.common.merger import merge

merged = merge(sdf_a, sdf_b, how='outer', left_index=True, right_index=True)
```

### 12.2 Reshape Wide to Long

```python
from simpandas.common.shape import melt

long_df = melt(sdf)
```

### 12.3 Normalise a Numeric Vector

```python
from simpandas.common.math import znorm

z = znorm([1.0, 2.0, 3.0, 4.0])
```

### 12.4 Handle Duplicate Column Names

```python
# Explicit deduplication before dict-based I/O
clean = df.deduplicate_columns()       # returns a copy
df.deduplicate_columns(inplace=True)   # modifies in-place

# JSON, PRODML, and WITSML writers call this automatically
df.to_json('output.json')   # duplicate columns renamed silently + logged
```

### 12.5 Working with ColumnUnits

```python
# ColumnUnits is the type returned by .units
cu = sdf.units                  # ColumnUnits({'rate': 'bbl/d', 'pressure': 'psi'})
cu.to_dict()                    # {'rate': 'bbl/d', 'pressure': 'psi'}
cu.to_list()                    # ['bbl/d', 'psi']  — positionally safe

# Pass units as ColumnUnits to constructor
sdf2 = SimDataFrame(data, units=cu)
```

---

## 13. Troubleshooting

**Units mismatch in arithmetic**

Ensure both operands use convertible units (`unyts` conversion support
required).  Check with:

```python
from unyts.converter import convertible
convertible('psi', 'bar')   # True
convertible('m', 'kg')      # False — not convertible
```

**Missing metadata after external pandas operations**

Prefer SimPandas wrappers (`to_simdataframe`, `to_simseries`) after raw
pandas operations.  Built-in wrappers already exist for `resample`,
`pct_change`, `align`, `compare`, and `combine_first`.  For uncovered methods:

```python
result = SimDataFrame(df.some_pandas_method(), **df.params_)
```

**Excel units not detected**

Pass the correct `units` row index and verify the sheet layout:

```python
sdf = read_excel('data.xlsx', units=1)   # row 1 (0-based) contains units
```

**Duplicate column names lose unit fidelity in JSON / PRODML / WITSML**

These writers serialise units as a `{column_name: unit}` dict, so duplicate
keys overwrite each other.  Call `deduplicate_columns()` before writing, or
rely on the automatic deduplication built into those writers (they log a
`WARNING` for each renamed column).

**`read_parquet` / `read_resqml` / `to_hdf5` fails with `ModuleNotFoundError`**

Install the required backend:

```
pip install pyarrow   # for Parquet
pip install h5py      # for HDF5 and RESQML
```

---

## 14. Public API Catalog

### Top-level package (`simpandas`)

| Symbol | Kind | Description |
|---|---|---|
| `SimDataFrame` | class | Unit-aware pandas DataFrame subclass |
| `SimSeries` | class | Unit-aware pandas Series subclass |
| `SimIndex` | class | MultiIndex subclass with units (from `simpandas.index`) |
| `ColumnUnits` | class | Ordered unit mapping (from `simpandas.common.units`) |
| `read_excel` | function | Read Excel with unit extraction |
| `read_csv` | function | Read CSV with unit extraction |
| `read_json` | function | Read SimPandas JSON envelope |
| `read_hdf5` | function | Read HDF5 with unit metadata |
| `read_summary` | function | Read Eclipse binary summary |
| `read_vdb` | function | Read VIP/Nexus VDB plot data |
| `read_parquet` | function | Read Parquet with unit metadata |
| `read_prodml` | function | Read PRODML XML |
| `read_witsml` | function | Read WITSML XML |
| `read_resqml` | function | Read RESQML EPC package |
| `concat` | function | Concatenate Sim objects preserving unit metadata |

### Writers (`simpandas.writers`)

| Module | Function | Description |
|---|---|---|
| `xlsx` | `write_excel` | Write SimDataFrame to Excel |
| `csv` | `write_csv` | Write to CSV with units row |
| `json` | `write_json` | Write to JSON envelope |
| `h5` | `write_hdf5` | Write to HDF5 with units |
| `summary` | `write_summary` | Write Eclipse binary summary |
| `parquet` | `write_parquet` | Write to Parquet with units metadata |
| `prodml` | `write_prodml` | Write to PRODML XML |
| `witsml` | `write_witsml` | Write to WITSML XML |
| `resqml` | `write_resqml` | Write to RESQML EPC |
| `schedule` | `write_schedule` | Write production-schedule files |

### Common utilities (`simpandas.common`)

| Module | Key functions |
|---|---|
| `merger` | `concat`, `merge`, `merge_index`, `merge_units`, `merge_SimParameters` |
| `shape` | `melt`, `pivot` |
| `renamer` | `right`, `left`, `rename_right`, `rename_left`, `common_rename`, `deduplicate_column_names` |
| `stringformat` | `multisplit`, `is_numeric`, `get_number`, `is_date`, `splitDMMMY`, `date` |
| `daterelated` | `check_day`, `check_month`, `days_in_year`, `days_in_month`, `real_year` |
| `math` | `jitter`, `znorm`, `minmaxnorm` |
| `filters` | `zeros`, `key_to_string` |
| `helpers` | `clean_axis`, `string_new_name`, `type_of_frame`, `main_key`, `item_key`, `hashable`, `make_units_dict` |
| `slope` | `slope` |
| `units` | `ColumnUnits` |
