# SimPandas — Developer Manual

**Version 0.90.8 | For contributors and maintainers**

---

## Table of Contents

1. [Repository Layout](#1-repository-layout)
2. [Architecture Overview](#2-architecture-overview)
3. [Class Hierarchy](#3-class-hierarchy)
4. [SimBasics — The Shared Mixin](#4-simbasics--the-shared-mixin)
   - 4.1 [Metadata System (`params_`)](#41-metadata-system-params_)
   - 4.2 [Unit Storage (`_units_`)](#42-unit-storage-_units_)
   - 4.3 [The `_rewrap` Pattern](#43-the-_rewrap-pattern)
   - 4.4 [Arithmetic Dispatch (`_arithmethic_operation`)](#44-arithmetic-dispatch-_arithmethic_operation)
5. [SimDataFrame](#5-simdataframe)
   - 5.1 [Constructor and `_metadata`](#51-constructor-and-_metadata)
   - 5.2 [Window Proxies](#52-window-proxies)
   - 5.3 [GroupBy Proxy](#53-groupby-proxy)
6. [SimSeries](#6-simseries)
7. [Custom Indexers](#7-custom-indexers)
8. [SimIndex](#8-simindex)
9. [I/O Layer](#9-io-layer)
   - 9.1 [Excel](#91-excel)
   - 9.2 [CSV](#92-csv)
   - 9.3 [JSON](#93-json)
   - 9.4 [Schedule Writer](#94-schedule-writer)
10. [Common Utilities (`simpandas.common`)](#10-common-utilities-simpandascommon)
11. [Adding a New Method](#11-adding-a-new-method)
12. [Adding a New I/O Format](#12-adding-a-new-io-format)
13. [Testing Strategy](#13-testing-strategy)
14. [Common Pitfalls](#14-common-pitfalls)
15. [Versioning and Release](#15-versioning-and-release)

---

## 1. Repository Layout

```
d:\git\simpandas\
│
├── src/
│   └── simpandas/
│       ├── __init__.py           # Public API exports
│       ├── basics.py             # SimBasics mixin (shared by both types)
│       ├── frame.py              # SimDataFrame + _SimWindowProxy + _SimGroupBy + _SimResampleProxy
│       ├── series.py             # SimSeries
│       ├── indexer.py            # _SimLocIndexer, _iSimLocIndexer
│       ├── index.py              # SimIndex
│       ├── errors.py             # Custom exception types
│       ├── basics_copy.py        # Historical snapshot — NOT imported
│       ├── frame_copy.py         # Historical snapshot — NOT imported
│       │
│       ├── common/               # Utility functions (no pandas subclassing)
│       │   ├── __init__.py
│       │   ├── _internal_processes.py
│       │   ├── daterelated.py
│       │   ├── filters.py
│       │   ├── helpers.py
│       │   ├── math.py
│       │   ├── merger.py         # unit-aware concat()
│       │   ├── renamer.py
│       │   ├── shape.py
│       │   ├── slope.py
│       │   └── stringformat.py
│       │
│       ├── readers/
│       │   ├── __init__.py       # exports read_excel, read_csv, read_json
│       │   ├── xlsx.py
│       │   ├── csv.py
│       │   └── json.py
│       │
│       └── writers/
│           ├── __init__.py
│           ├── xlsx.py
│           └── schedule.py
│
├── test/
│   ├── __init__.py
│   ├── test_frame.py
│   ├── test_indexer.py
│   ├── test_series.py
│   ├── test_simpandas.py
│   ├── test_new_features.py      # Tests for v0.84 additions
│   ├── test.py
│   ├── manual_testing.py
│   ├── TEST_VALIDATION_SUMMARY.md
│   └── common/
│       ├── test_daterelated.py
│       ├── test_filters.py
│       ├── test_helpers.py
│       ├── test_math.py
│       ├── test_merger.py
│       ├── test_renamer.py
│       ├── test_shape.py
│       ├── test_slope.py
│       └── test_stringformat.py
│
├── pyproject.toml
├── README.md
├── WHATS_NEW.md
├── USER_MANUAL.md
├── DEVELOPER_MANUAL.md   ← this file
└── CONTRIBUTING.md
```

`*_copy.py` files are historical snapshots.  They are **not** imported anywhere
and should be ignored when editing logic.

---

## 2. Architecture Overview

```
pandas.DataFrame          pandas.Series
        │                         │
        └──────────┬──────────────┘
                   │
             SimBasics (mixin)          ← basics.py
           /           \
   SimDataFrame        SimSeries        ← frame.py / series.py
        │
   _SimWindowProxy                      ← wraps rolling/expanding/ewm
   _SimResampleProxy                    ← wraps resample
   _SimGroupBy                          ← wraps groupby
   _SimLocIndexer / _iSimLocIndexer     ← wraps .loc / .iloc
```

**Key invariants:**
1. Every method that produces a new data object must return a `SimDataFrame` or
   `SimSeries` — never a bare `pd.DataFrame` / `pd.Series`.
2. The result must carry the same `params_` (units, name_separator, etc.) as
   the source object.
3. Unit arithmetic rules are implemented once in `_arithmethic_operation`
   (in `basics.py`) and are reused by all operators.

---

## 3. Class Hierarchy

### `SimBasics(object, metaclass=SimType)`

The shared mixin (no `__init__`).  All methods that make sense for both
DataFrame and Series live here.  New shared behaviour goes here first.

### `SimDataFrame(SimBasics, DataFrame)`

MRO: `SimDataFrame → SimBasics → object → DataFrame → NDFrame → …`

pandas calls constructors internally during indexing, `copy()`, etc.  That path
bypasses `SimDataFrame.__init__`, which is why `_metadata` exists (pandas copies
those attribute names to new instances automatically).

### `SimSeries(SimBasics, Series)`

Same MRO pattern.  `_constructor` returns `_simseries_constructor_with_fallback`
to gracefully degrade when pandas tries to create a Series without units.

### `_SimWindowProxy`

Not a pandas subclass.  Wraps a plain pandas window object (Rolling, Expanding,
ExponentialMovingWindow) and intercepts any method call to re-wrap the result
into a Sim type.

### `_SimGroupBy`

Same pattern as `_SimWindowProxy`.  Wraps `pd.core.groupby.GroupBy` and
re-wraps aggregation results.

---

## 4. SimBasics — The Shared Mixin

### 4.1 Metadata System (`params_`)

`params_` is a `@property` that builds and returns a fresh dictionary every
call.  It contains every piece of metadata that needs to survive operations:

```python
{
    'name':                  str | None,
    'units':                 dict | str | None,
    'index_name':            str | None,
    'index_units':           str | None,
    'name_separator':        str | None,
    'intersection_character': str,
    'verbose':               bool,
    'auto_append':           bool,
    'operate_per_name':      bool,
    'transposed':            bool,
    'reverse':               bool,
    'meta':                  any,
    'source_path':           str | None,
    'return_singles':        bool | None,
}
```

**Every constructor call that creates a new Sim object passes `**self.params_`.**
This is the canonical pattern:

```python
return self._class(data=result, **self.params_)
# or
return SimDataFrame(data=result, **self.params_)
```

`_class` is a property on both subclasses that returns the class itself
(`SimDataFrame` or `SimSeries`) so the right constructor is always called from
shared code.

### 4.2 Unit Storage (`_units_`)

Units are stored in `_units_` as a **list** parallel to `self.labels` (which is
`self.columns` for DataFrames, `self.index` for transposed objects, and the
series name for Series).

The `units` property translates:
- list → dict `{column: unit}` when all column names are unique (backward compat)
- list → list when duplicate column names exist (positional access)
- string → string passthrough (for SimSeries)

**Defensive guard:** Many pandas internal operations (e.g. during `groupby`,
`apply`, `concat`) create `SimDataFrame`/`SimSeries` instances by calling
`__new__` + `__finalize__` without calling `__init__`.  This leaves
`_units_` uninitialised.  The `units` property opens with:

```python
if not hasattr(self, '_units_'):
    object.__setattr__(self, '_units_', [None] * len(labels))
```

**Always use `object.__setattr__` to set private attributes inside `__init__`**
or guards, because pandas overrides `__setattr__` and can interfere.

### 4.3 The `_rewrap` Pattern

`_rewrap(self, result)` is the recommended way to wrap any pandas output back
into a Sim type.  Its logic:

```
result is pd.DataFrame → SimDataFrame(result, **self.params_)
                          then copy matching column units from self
result is pd.Series    → SimSeries(result, **params_with_unit)
                          unit looked up via self.get_units_string(result.name)
otherwise              → return result unchanged (scalars, arrays, etc.)
```

The unit copy inside the DataFrame branch is a best-effort operation wrapped in
`try/except`.  Unit propagation is approximate for operations that change the
column set (e.g. `pivot_table`).

### 4.4 Arithmetic Dispatch (`_arithmethic_operation`)

All Python operators (`__add__`, `__mul__`, …) and named methods (`add`,
`mul`, …) delegate to `_arithmethic_operation`.  This private method:

1. Checks whether `other` has units.
2. Tries `unyts._convertible` to see if unit conversion is possible.
3. Calls `unyts._converter` if a conversion is needed.
4. Applies the raw pandas operation on the data values.
5. Runs the `unyts` unit-combination functions (`unit_product`, `unit_division`,
   `unit_addition`, `unit_power`, …) to compute the result unit.
6. Constructs and returns the appropriate Sim type.

This method is large and handles many edge cases (scalars, Series, DataFrames,
unyts Unit objects, `_reverse_` flag, `intersection_character`, etc.).  **Do
not call it directly from user code.**

---

## 5. SimDataFrame

### 5.1 Constructor and `_metadata`

`__init__` receives all `params_` keys as named arguments.  The very first
thing it does is set private attributes with `object.__setattr__` to avoid
pandas intercepting them.

`_metadata` is a class-level list of attribute names that pandas copies to
derived objects:

```python
_metadata = ['units', 'verbose', 'index_units_', 'name_separator',
             'intersection_character', 'spdLocator', 'spdiLocator',
             'name', 'meta', 'source_path', '_auto_append_',
             '_operate_per_name_', '_transposed_', '_reverse_',
             '_return_singles_']
```

Attributes not in `_metadata` are **lost** when pandas creates a new instance
through its internal machinery.  If you add a new persistent attribute, add its
name to this list.

### 5.2 Window Proxies

`_SimWindowProxy` in `frame.py`:

```python
class _SimWindowProxy:
    def __init__(self, window_obj, parent):
        self._window_obj = window_obj   # the pandas window object
        self._parent = parent           # the SimDataFrame/SimSeries

    def _wrap_result(self, result): ...   # DataFrame → SimDF, Series → SimS

    def __getattr__(self, name):
        # intercept any method call, call it on the pandas object,
        # then wrap the result
        target = getattr(self._window_obj, name)
        if callable(target):
            def _wrapped(*args, **kwargs):
                return self._wrap_result(target(*args, **kwargs))
            return _wrapped
        return target
```

`rolling()`, `expanding()`, and `ewm()` on `SimDataFrame` and `SimSeries` all
return `_SimWindowProxy(super().<method>(...), self)`.

`resample()` on `SimDataFrame` and `SimSeries` returns `_SimResampleProxy`.
The proxy follows the same interception strategy as `_SimWindowProxy` and wraps
aggregation outputs back into Sim types.

### 5.3 GroupBy Proxy

`_SimGroupBy` in `frame.py` mirrors `_SimWindowProxy` but is more explicit
because GroupBy objects have a richer API (iteration, column selection, etc.):

```python
class _SimGroupBy:
    def __init__(self, groupby_obj, parent): ...
    def _wrap_result(self, result): ...

    # Explicit aggregation methods (sum, mean, std, …) to keep IDE autocompletion
    def sum(self, *args, **kwargs):
        return self._wrap_result(self._groupby_obj.sum(*args, **kwargs))
    ...
    def __iter__(self): ...      # yields (key, SimDataFrame) pairs
    def __getitem__(self, key):  # column selection returns another _SimGroupBy
        return _SimGroupBy(self._groupby_obj[key], self._parent)
    def __getattr__(self, name): ...   # fallback for any other method
```

`groupby()` on `SimDataFrame` and `SimSeries`:

```python
def groupby(self, *args, **kwargs):
    return _SimGroupBy(super().groupby(*args, **kwargs), self)

def resample(self, *args, **kwargs):
    return _SimResampleProxy(super().resample(*args, **kwargs), self)
```

---

## 6. SimSeries

`SimSeries` mirrors `SimDataFrame` but:

- Stores units as a **simple string** (not a list/dict) internally when the
  series has a single unit.
- `_constructor` returns `_simseries_constructor_with_fallback` (a free
  function) so pandas can create Series fallbacks when constructing intermediate
  results.
- Overrides comparison methods (`eq`, `ge`, `gt`, `le`, `lt`, `ne`) as
  named methods that accept a `precision` argument for rounded comparison.
- Has extra conversion helpers: `as_dict()`, `from_dict()`, `to_simdataframe()`, `as_simdataframe()`,
  `daily()`, `monthly()`, `yearly()`, `slope()`.

### `as_dict()` Implementation Detail

`as_dict(data_only=False)` leverages the fact that `unyts` instances are self-contained. It iterates over the series and returns `{index: unyts.Unit(value, unit)}`. This makes the dictionary serializable and reversible without needing a separate units sidecar. `from_dict()` performs the inverse by checking `is_Unit(val)` on each dictionary value to extract both raw data and the canonical unit for the series.

---

## 7. Custom Indexers

`_SimLocIndexer` (`indexer.py`) inherits both from `_SimBaseIndexer` and
pandas `_LocIndexer`:

```
_SimBaseIndexer  ←  _postprocess()
       │
_SimLocIndexer  ←  __getitem__, __setitem__
_iSimLocIndexer ←  __getitem__, __setitem__
```

**`__getitem__`** delegates to `super().__getitem__` (pandas), then calls
`_postprocess()` to re-wrap the result.

**`__setitem__`** supports a `(value, unit)` tuple:

```python
df.loc[idx, col] = (42, 'psi')
```

Logic:
1. If the column already has a unit, convert `value` from the tuple's unit to
   the column's unit using `unyts._converter`.
2. If the column is empty (new column), assign the tuple's unit to that column.
3. Assign the converted scalar value via `super().__setitem__`.

---

## 8. SimIndex

`SimIndex` (in `index.py`) subclasses `pd.MultiIndex` and carries a `units`
attribute.  It is primarily used when an index has physical meaning (e.g. a
depth axis in metres).

Use it by passing a `SimIndex` as the `index` argument to `SimDataFrame`:

```python
idx = SimIndex([(0, 1000), (0, 2000)], units='m')
df = SimDataFrame({'P': [100, 200]}, index=idx)
```

`SimIndex` provides `to_(units)` and `set_units_(units)` helper methods
injected in `__new__`.

---

## 9. I/O Layer

### 9.1 Excel

**Reader** (`readers/xlsx.py` → `read_excel`):

1. Calls `pandas.read_excel` to get a plain DataFrame.
2. Extracts the units row (default row 1) from the data, building a
   `{column: unit_string}` dict.
3. Drops the units row from the DataFrame.
4. Constructs and returns `SimDataFrame(df, units=units_dict, ...)`.

**Writer** (`writers/xlsx.py` → `write_excel`):

1. Optionally splits the DataFrame into multiple sheets based on `split_by`.
2. For each sheet, writes the header, then a units row, then the data using
   pandas `to_excel` / `ExcelWriter`.

### 9.2 CSV

**Reader** (`readers/csv.py` → `read_csv`):

```python
def read_csv(filepath, units=None, indexUnits=None, nameSeparator=None, ...):
    if isinstance(units, int):
        df = pd.read_csv(filepath)
        units_row = df.iloc[units]
        units_dict = {col: str(val).strip() for col, val in units_row.items()
                      if pd.notna(val) and str(val).lower() not in ('nan','none','')}
        df = df.drop(units).reset_index(drop=True)
    else:
        df = pd.read_csv(filepath)
    return SimDataFrame(df, units=units_dict or units, ...)
```

**Writing**: `SimBasics.to_csv()` in `basics.py` (shared by both `SimDataFrame`
and `SimSeries`).  When a path is given and units are present, a units row is
injected after the header using `pandas.DataFrame.to_csv(..., header=False)`
for the data portion.

### 9.3 JSON

**Reader** (`readers/json.py` → `read_json`):

Tries to load the file as JSON directly.  If the loaded object is a dict with
`"data"` and `"units"` keys it is treated as a SimPandas JSON file:

```python
raw = json.load(file)
if isinstance(raw, dict) and 'data' in raw and 'units' in raw:
    df = pd.DataFrame(raw['data'])
    units = raw.get('units', None)
else:
    df = pd.read_json(filepath)
```

**Writer**: `SimBasics.to_json()` in `basics.py` (shared by both `SimDataFrame`
and `SimSeries`).  Produces `{"data": {...}, "units": {...}}`.

### 9.4 Schedule Writer

`writers/schedule.py` → `write_schedule` is a domain-specific writer for
Eclipse-style petroleum simulation schedule files.  It is not part of the
general-purpose I/O layer.

---

## 10. Common Utilities (`simpandas.common`)

| Module | Key exports | Purpose |
|---|---|---|
| `merger.py` | `concat` | Unit-aware `pd.concat` wrapper |
| `renamer.py` | `left`, `right`, `common_rename` | Column-name helpers |
| `stringformat.py` | `multisplit`, `is_date`, `date` | String utilities |
| `daterelated.py` | `days_in_year`, `days_in_month`, `check_day`, `check_month`, `real_year` | Date arithmetic |
| `math.py` | `znorm`, `minmaxnorm`, `jitter` | Numeric helpers |
| `slope.py` | `slope` | Linear regression / rolling slope |
| `helpers.py` | `clean_axis`, `hashable`, `string_new_name` | Generic utilties |
| `filters.py` | `zeros`, `key_to_string` | DataFrame / Series filter parsing helpers |
| `shape.py` | `melt`, `pivot` wrappers | Shape helpers |
| `_internal_processes.py` | `get_units`, `get_index_atts` | Internal unit-extraction logic |

**Rules for `common/`:**
- No direct `import` of `SimDataFrame` or `SimSeries` at module level (would
  create circular imports).  If needed, import inside the function body.
- Pure functions only — no class definitions.

---

## 11. Adding a New Method

### Case A: Method applies to both DataFrame and Series

1. Add it to `SimBasics.py`, using `_rewrap`:

```python
def my_method(self, *args, **kwargs):
    """One-line description."""
    return self._rewrap(self.as_pandas().my_method(*args, **kwargs))
```

2. Add a test in `test/test_new_features.py` (or the appropriate existing test
   file) that checks:
   - The result is a `SimDataFrame` / `SimSeries`.
   - Units are preserved (or intentionally dropped with a comment).

### Case B: Method applies only to DataFrame

Add it to `SimDataFrame` in `frame.py`, typically in the block after
`ewm()` / `groupby()`:

```python
def my_frame_method(self, *args, **kwargs):
    """One-line description."""
    return self._rewrap(self.as_dataframe().my_frame_method(*args, **kwargs))
```

### Case C: Method returns non-Sim output (scalar, numpy array, …)

Do not call `_rewrap`.  Just delegate:

```python
def unique(self):
    return self.as_pandas().unique()   # returns np.ndarray
```

### Case D: Method needs custom unit logic

Override the full implementation and construct the result manually:

```python
def inv(self):
    params_ = self.params_
    params_['units'] = _unit_inverse(self.units)   # unit-lib call
    return self._class(data=1 / self.as_pandas(), **params_)
```

### Case E: Method changes shape (sets of columns change)

`_rewrap` only copies units for columns that exist in both `self` and the
result.  If the column set changes fundamentally, track units explicitly:

```python
def pivot_table(self, *args, **kwargs):
    import pandas as pd
    result = pd.pivot_table(self.as_dataframe(), *args, **kwargs)
    # units on the value columns may be known; set them manually if needed
    wrapped = SimDataFrame(result, **self.params_)
    return wrapped
```

---

## 12. Adding a New I/O Format

1. Create `src/simpandas/readers/<format>.py` with a `read_<format>()` function.
   - Always return a `SimDataFrame`.
   - Accept `units`, `indexUnits`, `nameSeparator`, `intersectionCharacter`,
     `autoAppend`, `operatePerName`, `verbose` to match the existing readers.
2. Export from `src/simpandas/readers/__init__.py`.
3. Export from `src/simpandas/__init__.py` and add to `__all__`.
4. Add `to_<format>()` to `SimDataFrame` (and `SimSeries` if relevant) in
   `frame.py` / `series.py`.
5. Write tests in `test/test_new_features.py` covering round-trip:
   write → read → verify `isinstance(result, SimDataFrame)` and units match.

---

## 13. Testing Strategy

```bash
# Run all tests
python -m pytest test/ -v

# Run specific files
python -m pytest test/test_frame.py test/test_indexer.py test/test_new_features.py -v

# Run a single test class / function
python -m pytest test/test_new_features.py::TestGroupBy -v
python -m pytest test/test_new_features.py::TestGroupBy::test_groupby_sum -v
```

**Test file ownership:**

| File | Covers |
|---|---|
| `test_frame.py` | `SimDataFrame` core (indexing, arithmetic, units, I/O) |
| `test_indexer.py` | `.loc` / `.iloc` unit conversion, tuple assignment |
| `test_series.py` | `SimSeries` core — note: has module-level assertion that may fail |
| `test_new_features.py` | All v0.84+ additions |
| `test/common/test_merger.py` | `concat()` |
| `test/common/test_renamer.py` | Column-name helpers |
| `test/common/test_math.py` | Math utilities |
| `test/common/test_slope.py` | Slope calculation |
| `test/common/test_stringformat.py` | String utilities |

**Writing tests:**

- Import `from simpandas import SimDataFrame, SimSeries`.
- Use `pytest.fixture` for reusable test data.
- Always verify the **type** of the result (`isinstance(result, SimDataFrame)`).
- Verify units are not dropped: `result.get_units()['col'] == 'psi'`.
- Use `tempfile.NamedTemporaryFile` for I/O tests; always clean up with
  `os.unlink(path)` in a `finally` block.

**Known pre-existing failures in `test/common/`:**

Several tests in `test/common/` fail due to numpy API changes (`np.RankWarning`
removed), pre-pandas-2 DataFrame constructors, and a module-level `assert` in
`test_series.py`.  These are unrelated to SimPandas logic and are tracked
separately.

---

## 14. Common Pitfalls

### Pandas `apply_if_callable` interpreting Sim types as functions

**Symptom:** `ValueError: The truth value of a DataFrame is ambiguous` or `KeyError` when calling `.mask()`, `.where()`, `.assign()`, etc., with a SimPandas type as an argument.

**Cause:** Both `SimSeries` and `SimDataFrame` implement `__call__` for convenience extraction. The internal pandas wrapper function `apply_if_callable(cond, self)` checks `callable(cond)` and invokes `cond(self)` if true. This means passing a `SimSeries` as the condition to `.mask()` would result in pandas attempting to execute the SimSeries as a function, treating the target object as the key argument.

**Fix:** `__call__` in both classes contains a specialized guard that checks `if isinstance(key, (pd.Series, pd.DataFrame)): return self`. This intercepts the `apply_if_callable` invocation and returns the object safely, ensuring it is effectively treated as a scalar non-callable value during pandas internals traversal.

### `_units_` not initialised after pandas internal construction

**Symptom:** `AttributeError: '_units_'` or `TypeError` inside the `units`
property.

**Cause:** pandas creates instances via `__new__` + `__finalize__` without
going through `__init__`.  The `_metadata` list ensures the attribute is
copied from `__finalize__`, but when the source object itself is a plain
pandas type the attribute will be absent.

**Fix:** The `units` property already contains a defensive guard.  Ensure any
new property or method that accesses `_units_` directly also has one:

```python
if not hasattr(self, '_units_'):
    object.__setattr__(self, '_units_', [])
```

### Setting pandas-managed attributes with `self.attr = value`

**Symptom:** The attribute is silently ignored or a `ValueError` / `UserWarning`
is raised.

**Cause:** pandas overrides `__setattr__` and treats unknown attribute names as
column names.

**Fix:** Use `object.__setattr__(self, 'attr', value)` inside `__init__` and
inside any method that sets private state.

### Circular import between `basics.py` and `frame.py` / `series.py`

**Symptom:** `ImportError: cannot import name 'SimDataFrame'`.

**Cause:** `basics.py` is imported by `frame.py`.  If `basics.py` imports from
`frame.py` at module level a circular import results.

**Fix:** Use local imports inside method bodies:

```python
def _rewrap(self, result):
    from .frame import SimDataFrame   # local import, not circular
    from .series import SimSeries
    ...
```

### `as_pandas()` vs `to_pandas()`

Both return a plain pandas object.  `as_pandas()` returns a **view** (no copy).
`to_pandas()` may return a copy.  Use `as_pandas()` when you only need to
read the data; use `to_pandas()` (or `.copy()`) when you will modify it.

### `_class` property

`_class` is a property defined on both `SimDataFrame` and `SimSeries` that
returns the class itself.  It exists so shared code in `SimBasics` can
construct a new object of the correct type:

```python
return self._class(data=result, **self.params_)
```

Never hard-code `SimDataFrame(...)` inside `SimBasics` unless you specifically
need a DataFrame regardless of type.

### `KeyError` during column re-assignment (`__setitem__`)

**Symptom**: `KeyError` when performing `sdf['col'] = sdf['col'].mask(...)` or assigning a plain Series back to an existing column.

**Cause**: The `__setitem__` logic traditionally looked up units in an incoming `u_dict`. If the column already existed but the incoming data didn't provide a new unit (plain pandas object), the lookup would fail or overwrite with `'unitless'`.

**Fix**: `SimDataFrame.__setitem__` now includes an `after == before` check. If the column exists and no explicit unit is provided in the assignment, it attempts to **preserve** the existing unit from `self.get_units(key)`. This ensures operations like `.mask`, `.where`, or manual array assignments don't strip metadata.

## 15. Versioning and Release

### Version numbers

The project uses a `MAJOR.MINOR.PATCH` scheme.  The version string appears in:

- `pyproject.toml` → `[project] version`
- `src/simpandas/__init__.py` → `__version__`
- Each major module file → its own `__version__` / `__release__`

Keep these in sync before a release.

`__release__` is an integer date `YYYYMMDD` used for quick version ordering.

### Build and publish

```powershell
# Editable install (dev)
pip install -e .

# Build wheel + sdist
python -m build

# Upload to PyPI
twine upload dist/*
```

### Branch strategy

- `development` — active development branch; all feature work goes here.
- PRs are merged to `development`, then `development` is merged to `main` for
  releases.
- Tests must pass on `development` before merging.

### Pre-release checklist

1. `python -m pytest test/test_frame.py test/test_indexer.py test/test_new_features.py -v` — all pass.
2. Bump `__version__` and `__release__` in `__init__.py` and each changed module.
3. Update `WHATS_NEW.md`.
4. `python -m build` — no errors.
5. `twine check dist/*` — no issues.
6. `twine upload dist/*`.
