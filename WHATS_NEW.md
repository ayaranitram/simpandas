# What's New in SimPandas

## Version 0.84.0 — March 2026

This release is the largest feature update since the library's initial release.
It fills a substantial gap between SimPandas and plain pandas by wrapping all
commonly-used pandas operations so that unit metadata is never silently dropped.

---

### New Top-Level I/O Functions

#### `read_csv(filepath, units=..., ...)`
Read a CSV file directly into a `SimDataFrame`.

- `units=<int>` — treat that row (0-based after the header) as a units row.
- `units=<dict>` — supply a `{column: unit}` mapping explicitly.
- All standard `pandas.read_csv` keyword arguments are forwarded.

```python
from simpandas import read_csv

# units embedded as the first data row
df = read_csv('measurements.csv', units=0)

# units supplied externally
df = read_csv('measurements.csv', units={'pressure': 'psi', 'depth': 'm'})
```

#### `read_json(path_or_buf, units=..., ...)`
Read a JSON file into a `SimDataFrame`.

- Detects SimPandas JSON format automatically (files that contain `"data"` and
  `"units"` keys written by `SimDataFrame.to_json()`).
- Falls back to standard `pandas.read_json` for plain JSON files.

```python
from simpandas import read_json

df = read_json('output.json')          # SimPandas-format: units restored
df = read_json('plain.json', units={'x': 'm'})  # plain pandas JSON
```

---

### New Instance Methods — `SimDataFrame` and `SimSeries`

All methods below return `SimDataFrame` / `SimSeries` objects with full unit
and metadata propagation. They are drop-in replacements for the identically
named pandas methods.

#### Functional / Transform
| Method | Description |
|--------|-------------|
| `apply(func, axis=0, ...)` | Apply a function along an axis |
| `transform(func, axis=0, ...)` | Apply a function producing a same-shape result |
| `pipe(func, ...)` | Chainable function application |
| `map(func, na_action=None)` | Element-wise function application |

#### Conditional Selection
| Method | Description |
|--------|-------------|
| `where(cond, other=None, ...)` | Keep values where `cond` is True |
| `mask(cond, other=None, ...)` | Replace values where `cond` is True |

#### Cumulative
| Method | Description |
|--------|-------------|
| `cummax(axis=0, skipna=True)` | Cumulative maximum |
| `cummin(axis=0, skipna=True)` | Cumulative minimum |
| `cumprod(axis=0, skipna=True)` | Cumulative product |

#### Statistics
| Method | Description |
|--------|-------------|
| `skew(axis=0, ...)` | Unbiased skewness |
| `kurtosis(axis=0, ...)` / `kurt(...)` | Unbiased kurtosis |
| `sem(axis=0, ddof=1, ...)` | Standard error of the mean |
| `idxmin(axis=0, ...)` | Index label at minimum value |
| `idxmax(axis=0, ...)` | Index label at maximum value |

#### Sorting & Ranking
| Method | Description |
|--------|-------------|
| `sort_values(*args, **kwargs)` | Sort by values |
| `sort_index(*args, **kwargs)` | Sort by index |
| `rank(axis=0, method='average', ...)` | Numerical ranking |
| `nlargest(n, columns=None, ...)` | Top-n rows by value |
| `nsmallest(n, columns=None, ...)` | Bottom-n rows by value |

#### Cleaning & Shaping
| Method | Description |
|--------|-------------|
| `sample(*args, **kwargs)` | Random row/column sample |
| `clip(lower, upper, ...)` | Trim values to bounds |
| `abs()` | Element-wise absolute value |
| `round(decimals=0)` | Round to decimal places |
| `drop_duplicates(*args, **kwargs)` | Remove duplicate rows |
| `astype(dtype, ...)` | Cast to dtype |
| `explode(column=None, ...)` | Expand list-like cells to rows |
| `value_counts(*args, **kwargs)` | Frequency count |
| `nunique(axis=0, dropna=True)` | Count of unique values |

#### DataFrame-Only Reshaping
| Method | Description |
|--------|-------------|
| `join(other, how='left', ...)` | Join another DataFrame |
| `merge(right, ...)` | Merge with another DataFrame |
| `stack(*args, **kwargs)` | Stack column level into index |
| `unstack(*args, **kwargs)` | Pivot index level into columns |
| `pivot(index, columns, values)` | Reshape longform → wide |
| `pivot_table(values, index, ...)` | Spreadsheet-style pivot table |
| `melt(*args, **kwargs)` | Wide → long format |
| `query(expr, ...)` | Filter rows with a boolean expression string |
| `eval(expr, ...)` | Evaluate a column expression string |
| `iterrows()` | Iterate rows as `(index, SimSeries)` pairs |
| `itertuples(...)` | Iterate rows as namedtuples |

#### Series-Only
| Method | Description |
|--------|-------------|
| `unique()` | Return unique values as a NumPy array |

---

### GroupBy Support

`df.groupby(...)` now returns a `_SimGroupBy` proxy.  All aggregation and
transformation results are automatically re-wrapped into `SimDataFrame` or
`SimSeries` with unit propagation.

Supported operations on the group object:

```
sum  mean  median  std  var  min  max  count  first  last
agg  aggregate  apply  transform  filter
__iter__  __len__  __getitem__
```

```python
df = SimDataFrame({'depth': [100, 200, 300], 'pressure': [10, 20, 30],
                   'zone': ['A', 'A', 'B']},
                  units={'depth': 'm', 'pressure': 'bar', 'zone': None})

result = df.groupby('zone').mean()  # → SimDataFrame with units 'm', 'bar'
```

---

### Exponentially-Weighted Window (EWM)

`df.ewm(...)` and `series.ewm(...)` return a `_SimWindowProxy` proxy
identical to the existing rolling/expanding proxies.

```python
df.ewm(span=10).mean()   # → SimDataFrame
series.ewm(alpha=0.3).std()  # → SimSeries
```

---

### Rolling and Expanding on `SimSeries`

Previously only `SimDataFrame` supported `rolling()` / `expanding()`.
Both methods are now overridden on `SimSeries` as well.

```python
series.rolling(5).mean()     # → SimSeries
series.expanding(3).sum()    # → SimSeries
```

---

### New Export Methods

#### `SimDataFrame.to_json(path_or_buf=None, ...)`
Writes a JSON file that embeds units as a top-level `"units"` key alongside
the data.  When `path_or_buf` is `None` the JSON string is returned.

#### `SimSeries.to_json(path_or_buf=None, ...)`
Same behaviour for Series (units stored as a single string).

#### `SimDataFrame.to_csv(path_or_buf=None, ...)`
Delegates to `pandas.DataFrame.to_csv` after stripping Sim-specific metadata.
When a `path_or_buf` is provided **and** units are present, a units row is
written immediately after the header before the data rows.

---

### Internal Changes

- **`SimBasics._rewrap(result)`** — new protected helper.  Wraps any
  `pd.DataFrame` or `pd.Series` returned by a pandas operation back into the
  appropriate Sim type, copying units from `self` where columns match.
  Scalars and other types pass through unchanged.
- **`_SimGroupBy`** proxy class added to `frame.py`.  Mirrors the existing
  `_SimWindowProxy` pattern.
- **`_SimWindowProxy`** now also covers `ewm()`.
- `src/simpandas/readers/csv.py` — new module.
- `src/simpandas/readers/json.py` — new module.
- `src/simpandas/__init__.py` exports updated to include `read_csv`, `read_json`.

---

### Bug Fixes (carried forward from intermediate releases)

- `get_units_string()` — fixed crash when `_units_` is `None`.
- `_SimWindowProxy` — fixed metadata loss after `.rolling()` / `.expanding()`.
- `_SimLocIndexer.__setitem__` / `_iSimLocIndexer.__setitem__` — fixed unit
  conversion during `.loc` / `.iloc` assignment.
- `basics.concat()` / `merger.concat()` — fixed unit dropping when
  concatenating along axis 1.
- Removed stray debug `print()` calls.
- Defensive guards added for `_transposed_`, `_units_`, and `params_` to
  handle instances created by internal pandas machinery without calling
  `__init__`.
