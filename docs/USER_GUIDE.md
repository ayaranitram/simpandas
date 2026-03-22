# Simpandas User Guide

## 1. Overview

`simpandas` extends pandas with first-class unit tracking.

Core ideas:
- `SimDataFrame` and `SimSeries` behave like pandas objects but preserve unit metadata.
- Arithmetic and conversions use `unyts` when units are convertible.
- Metadata (`units`, `index_units`, naming conventions, flags) is carried through most operations.

Top-level API:
- `from simpandas import SimDataFrame, SimSeries, read_excel, read_csv, read_json, concat`

## 2. Installation

```bash
pip install simpandas
```

## 3. Quick Start

```python
from simpandas import SimDataFrame

sdf = SimDataFrame(
    data={"rate": [100, 105, 98], "pressure": [2500, 2480, 2470]},
    units={"rate": "bbl/d", "pressure": "psi"},
)

print(sdf.units)
# {'rate': 'bbl/d', 'pressure': 'psi'}

sdf2 = sdf * 2
print(sdf2.units)  # metadata is preserved
```

## 4. Core Classes

### 4.1 `SimDataFrame`

Unit-aware table based on `pandas.DataFrame`.

Typical constructor:

```python
from simpandas import SimDataFrame

sdf = SimDataFrame(
    data={"A": [1, 2], "B": [3, 4]},
    units={"A": "m", "B": "s"},
    index_units="day",
    name_separator=":",
)
```

Key capabilities:
- Convert/export: `to_pandas`, `as_pandas`, `to_series`, `to_simseries`, `to_dataframe`.
- Units and index units: `get_units`, `set_units`, `get_index_units`, `set_index_units`, `convert`.
- Aggregations: `sum`, `mean`, `median`, `min`, `max`, `std`, `var`, `prod`, `quantile`, `mode`, `count`, `rms`.
- Data wrangling: `drop`, `dropna`, `drop_duplicates`, `sort_values`, `melt`, `rename`, `reindex`, `transpose`.
- Binary operations and comparisons follow pandas semantics while preserving units when possible.

### 4.2 `SimSeries`

Unit-aware vector based on `pandas.Series`.

```python
from simpandas import SimSeries

ss = SimSeries([10, 12, 11], index=[0, 1, 2], name="rate", units="m3/d")
print(ss.get_units())
```

Key capabilities:
- Convert/export: `to_pandas`, `as_pandas`, `to_dataframe`, `to_simdataframe`.
- Units: `get_units`, `set_units`, `convert`, `get_index_units`, `set_index_units`.
- Statistics and math: `sum`, `mean`, `min`, `max`, `std`, `var`, `prod`, `quantile`, `mode`, `rms`.
- Data ops: `drop`, `dropna`, `astype`, `copy`, `sort_values`, `filter`.

### 4.3 `SimIndex`

Index object carrying unit metadata.

```python
from simpandas.index import SimIndex

idx = SimIndex([1, 2, 3], units="day")
idx2 = idx.to("hour")
```

## 5. Top-Level Exposed Functions

### 5.1 `read_excel`

Read Excel files and build a `SimDataFrame` while parsing units.

```python
from simpandas import read_excel

sdf = read_excel("my_data.xlsx", units=0)  # row 0 contains units
```

### 5.2 `read_csv`

Read CSV files and build a `SimDataFrame` while parsing units.

```python
from simpandas import read_csv

sdf = read_csv("my_data.csv", units=0)  # first data row contains units
```

### 5.3 `read_json`

Read JSON files into a `SimDataFrame`.

- SimPandas JSON payloads restore embedded units automatically.
- Plain JSON inputs can receive units explicitly.

```python
from simpandas import read_json

sdf = read_json("my_data.json")
sdf = read_json("plain.json", units={"rate": "bbl/d"})
```

### 5.4 `concat`

Concatenate `SimDataFrame`/`SimSeries` objects preserving metadata as much as possible.

```python
from simpandas import concat

joined = concat([sdf_a, sdf_b], axis=0)
```

## 6. Readers and Writers Modules

### 6.1 `simpandas.readers`
- `read_excel`: Excel reader with unit extraction support.
- `read_csv`: CSV reader with explicit or embedded units support.
- `read_json`: JSON reader with SimPandas payload detection.

### 6.2 `simpandas.writers`
- `write_excel`: Write `SimDataFrame` data and units to Excel.
- `write_schedule`: Write schedule-style outputs.

Example:

```python
from simpandas.writers.xlsx import write_excel

write_excel(sdf, "out.xlsx")
```

## 7. Common Utility Modules (Public)

### 7.1 `simpandas.common.merger`
- `concat(objs, ...)`
- `merge(left, right, ...)`
- `merge_index(left, right, ...)`
- `merge_units(left, right, ...)`
- `merge_SimParameters(left, right)`

Use when combining objects with potentially different columns/units.

### 7.2 `simpandas.common.shape`
- `melt(df, ...)`
- `pivot(df, ...)`

Use for reshaping with simpandas metadata preservation.

### 7.3 `simpandas.common.renamer`
- `right(series_or_frame, ...)`
- `left(series_or_frame, ...)`
- `rename_right(series_or_frame, ...)`
- `rename_left(series_or_frame, ...)`
- `common_rename(series_or_frame_1, series_or_frame_2, ...)`

Helpful with Eclipse-style names like `FIELD:WELL:ATTR`.

### 7.4 `simpandas.common.stringformat`
- `multisplit`, `is_numeric`, `get_number`, `is_date`, `splitDMMMY`, `date`

Use for parsing mixed strings/dates from simulator outputs.

### 7.5 `simpandas.common.daterelated`
- `check_day`, `check_month`, `days_in_year`, `days_in_month`, `real_year`

Date utilities used in temporal transformations.

### 7.6 `simpandas.common.math`
- `jitter`, `znorm`, `minmaxnorm`

Numeric helper functions.

### 7.7 `simpandas.common.filters`
- `zeros`, `key_to_string`

Utilities for boolean filtering and key normalization.

### 7.8 `simpandas.common.helpers`
- `clean_axis`, `string_new_name`, `type_of_frame`, `main_key`, `item_key`, `hashable`, `make_units_dict`

General helpers used across the package and reusable in external workflows.

### 7.9 `simpandas.common.slope`
- `slope(df, x=None, y=None, window=None, slope=True, intercept=False)`

Regression-based slope/intercept extraction utility.

## 8. Units Lifecycle

Common workflow:

1. Provide units at object creation.
2. Perform arithmetic/statistics.
3. Convert units when needed.
4. Export while preserving metadata.

```python
sdf = SimDataFrame({"q": [1, 2, 3]}, units={"q": "m3/d"})
q_hour = sdf.convert("q", "m3/h")
```

Notes:
- If units are not convertible, operations may keep source units or fall back to unitless behavior depending on operation.
- For duplicate column names, simpandas tracks units positionally in internal storage to avoid collisions.

## 9. Indexing and Selection

Selection works like pandas with simpandas-aware wrappers:
- `loc` and `iloc` preserve class/metadata where possible.
- Name-based wildcard filtering is supported in several helper methods.
- Date-aware filtering paths are available for temporal strings.

```python
subset = sdf.loc[sdf.index[:10], ["rate", "pressure"]]
```

## 10. Aggregation and Statistics

All common reductions are available with metadata propagation:
- DataFrame: axis-aware reductions return `SimSeries`/`SimDataFrame` as appropriate.
- Series: scalar-like outputs are wrapped with unit context where applicable.

```python
daily_mean = sdf.mean(axis=0)
series_std = ss.std()
```

## 11. IO Patterns

### Read with units row

```python
sdf = read_excel("history.xlsx", units=0)
```

### Write preserving unit metadata

```python
from simpandas.writers.xlsx import write_excel
write_excel(sdf, "history_out.xlsx")
```

## 12. Practical Recipes

### 12.1 Align two datasets and merge

```python
from simpandas.common.merger import merge

merged = merge(sdf_a, sdf_b, how="outer", left_index=True, right_index=True)
```

### 12.2 Reshape wide to long

```python
from simpandas.common.shape import melt

long_df = melt(sdf)
```

### 12.3 Normalize a numeric vector

```python
from simpandas.common.math import znorm

z = znorm([1.0, 2.0, 3.0, 4.0])
```

## 13. Public API Catalog

Top-level package (`simpandas`):
- Classes: `SimDataFrame`, `SimSeries`
- Functions: `read_excel`, `concat`
- Additional class available from package import path: `SimIndex`

User-facing modules:
- `simpandas.readers.xlsx`: `read_excel`
- `simpandas.writers.xlsx`: `write_excel`
- `simpandas.writers.schedule`: `write_schedule`
- `simpandas.common.merger`: `concat`, `merge`, `merge_index`, `merge_units`, `merge_SimParameters`
- `simpandas.common.shape`: `melt`, `pivot`
- `simpandas.common.renamer`: `right`, `left`, `rename_right`, `rename_left`, `common_rename`
- `simpandas.common.stringformat`: `multisplit`, `is_numeric`, `get_number`, `is_date`, `splitDMMMY`, `date`
- `simpandas.common.daterelated`: `check_day`, `check_month`, `days_in_year`, `days_in_month`, `real_year`
- `simpandas.common.math`: `jitter`, `znorm`, `minmaxnorm`
- `simpandas.common.filters`: `zeros`, `key_to_string`
- `simpandas.common.helpers`: `clean_axis`, `string_new_name`, `type_of_frame`, `main_key`, `item_key`, `hashable`, `make_units_dict`
- `simpandas.common.slope`: `slope`

## 14. Troubleshooting

- Units mismatch in arithmetic:
  - Ensure both operands use convertible units (`unyts` support required).
- Missing metadata after external pandas operations:
  - Prefer simpandas wrappers (`to_simdataframe`, `to_simseries`) after raw pandas ops.
- Excel units not detected:
  - Pass correct `units` row index and verify sheet layout.

## 15. Where to Next

- Explore examples in `simpandas_demo.ipynb`.
- Use `test/` as behavior reference for expected API outcomes.
