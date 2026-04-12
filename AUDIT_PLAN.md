# Simpandas Project Audit Plan

## 1. Overview

This document is the result of a full audit of the simpandas codebase — a pandas `DataFrame`/`Series` wrapper that adds unit awareness via the **unyts** package. The audit covers: confirmed bugs, pandas method coverage analysis, and recommended improvements.

---

## 2. Confirmed Bugs

### 2.1 HIGH Severity

#### BUG-01: COMPLETED — `cumsum()` and `describe()` call non-existent methods  
**File:** `src/simpandas/basics.py` lines 281, 284  
**Problem:** `self.as_Pandas()` and `self.to_Pandas()` — capital `P` — don't exist. The correct methods are `as_pandas()` / `to_pandas()`.  
**Impact:** `AttributeError` at runtime when calling `cumsum()` or `describe()` on any SimDataFrame/SimSeries.  
**Fix:** Change to `self.as_pandas()` and `self.to_pandas()`.

#### BUG-02: COMPLETED — `as_Series()` calls in SimSeries `filter()` and `sort_values()`  
**File:** `src/simpandas/series.py` lines 900, 902, 1374  
**Problem:** Calls `self.as_Series()` (capital S). The method is actually `as_series()`.  
- Lines 900/902: Inside string templates evaluated via `eval()`, so the error only surfaces at filter evaluation time.  
- Line 1374: Direct call in `sort_values(inplace=False)` — will always crash.  
**Fix:** Replace `as_Series()` with `as_series()`.

#### BUG-03: COMPLETED — `errors='errors'` string literal instead of variable in SimSeries `drop()`  
**File:** `src/simpandas/series.py` lines 693, 696  
**Problem:** Both the inplace and non-inplace branches pass `errors='errors'` (a string literal) instead of `errors=errors` (the variable).  
**Impact:** Pandas will receive the invalid string `'errors'` instead of `'raise'` or `'ignore'`, likely causing a `ValueError`.  
**Fix:** Change `errors='errors'` to `errors=errors`.

#### BUG-04: COMPLETED — `type(*args)` unpacking error in indexer `_postprocess()`  
**File:** `src/simpandas/indexer.py` lines 110, 112  
**Problem:** `type(*args)` unpacks the tuple into positional arguments for `type()`. When `args` has more than 1 element, `type()` interprets it as a dynamic class creation call (`type(name, bases, dict)`), not a type check. Similarly, `len(*args)` on unpacked args is incorrect.  
**Fix:** Replace `type(*args)` with `type(args[0])` and `len(*args)` with `len(args[0])`.

#### BUG-05: COMPLETED — `read_excel` crashes when `units` is a list  
**File:** `src/simpandas/readers/xlsx.py` line 96  
**Problem:** `for i in len(units)` — `len()` returns an int, which is not iterable.  
**Fix:** Change to `for i in range(len(units))`.

#### BUG-06: COMPLETED — `append()` uses undefined variable `otherC` in else branch  
**File:** `src/simpandas/frame.py` line 1183  
**Problem:** The `else` branch (when `other` is not SimDataFrame/SimSeries) references `otherC`, which is only defined in the `if` branch. This raises `NameError`.  
**Fix:** Change `otherC` to `other`.

#### BUG-07: COMPLETED — `_arithmethic_operation` sets `fill_value` to a label string  
**File:** `src/simpandas/frame.py` line 843  
**Problem:** `fill_value = valid_operations[operation][1]` when `fill_value is True`. Index `[1]` is the operation label (e.g. `'Addition'`), not the proposed fill value. Index `[2]` has the actual value.  
**Fix:** Change `[1]` to `[2]`.

### 2.2 MEDIUM Severity

#### BUG-08: COMPLETED — `dropna()` inplace branch has swapped parameters  
**File:** `src/simpandas/frame.py` lines 1263–1266  
**Problem:** In the inplace branch:  
- When `thresh is None`: passes `thresh=thresh` (None), omitting `how=how`.  
- When `thresh is not None`: passes `how=how`, omitting `thresh=thresh`.  
The non-inplace branch does this correctly (reversed logic).  
**Fix:** Swap the parameters in the inplace branch to match the non-inplace branch.

#### BUG-09: COMPLETED — `SimIndex.set_units()` calls `units.split()` on string units  
**File:** `src/simpandas/index.py` lines 89, 108  
**Problem:** `self.units = units.split()` converts a string like `"m/s"` into a list `["m/s"]`. All downstream code expects `units` to be a string, not a list.  
**Fix:** Change `units.split()` to just `units` (or `units.strip()` if whitespace cleanup is desired).

#### BUG-10: COMPLETED — `corr()` returns plain pandas DataFrame, losing Sim metadata  
**Files:** `src/simpandas/frame.py` line 1098, `src/simpandas/series.py` line 687  
**Problem:** Both `SimDataFrame.corr()` and `SimSeries.corr()` call `self.as_pandas().corr(...)` and return the raw result without wrapping.  
**Impact:** Metadata (units, name_separator, etc.) is silently lost.  
**Fix:** Wrap result with `self._rewrap(...)`.

#### BUG-11: COMPLETED — `drop(inplace=True)` in SimDataFrame — column drop detection broken  
**File:** `src/simpandas/frame.py` lines 1202–1216  
**Problem:** The `dropping_columns` variable checks `(axis == 1) or (labels is not None and axis == 1)` — the second clause is redundant with the first. More importantly, when `columns=` keyword is used but `labels` is None and `axis` defaults to 0, `dropping_columns` evaluates to `False` even though columns ARE being dropped. This means `_units_` won't be synced.  
**Fix:** Simplify to `dropping_columns = (axis == 1) or (columns is not None)`.

### 2.3 LOW Severity

#### BUG-12: COMPLETED — `write_excel` `split_by='last'` has wrong `else` pattern  
**File:** `src/simpandas/writers/xlsx.py`  
**Problem:** In the `split_by == 'last'` branch, the `else` case uses `names[i][0]+'*'` pattern instead of `'*'+names[i][-1]`.  
**Fix:** Use `'*'+names[i][-1]` consistently.

#### BUG-13: COMPLETED — `rename_item` `axis` dict not keyed  
**File:** `src/simpandas/frame.py` ~line 1530  
**Problem:** `axis = {'index': 0, 'columns': 1}` assigns a dict to `axis` without using the string value to look up the int. Should be `axis = {'index': 0, 'columns': 1}[axis]` or `axis = {'index': 0, 'columns': 1}.get(axis, axis)`.

#### BUG-14: COMPLETED — `renameItem` passes `self` as first positional arg  
**File:** `src/simpandas/frame.py` ~line 1440  
**Problem:** `return self.rename_item(self, mapper=...)` passes `self` as the `mapper` argument since `rename_item` is a bound method. Should be `return self.rename_item(mapper=...)`.

---

## 3. Pandas Method Coverage Analysis

### 3.1 Methods That Need Wrapping

Pandas methods that return a new DataFrame/Series and would lose Sim metadata if not wrapped. The following are **missing** from simpandas:

| Method | Priority | Notes |
|--------|----------|-------|
| `resample()` | High | Common time-series operation; needs a proxy like `_SimGroupBy` |
| `pct_change()` | Medium | Returns same shape; units become dimensionless |
| `ffill()` / `bfill()` | Medium | Shorthand for `fillna(method=...)`, should preserve units |
| `asfreq()` | Medium | Frequency conversion for time-series |
| `swaplevel()` | Low | MultiIndex operation |
| `align()` | Low | Returns two aligned objects |
| `compare()` | Low | Comparison between two DataFrames |
| `update()` | Low | In-place update — would need unit checking |
| `combine_first()` | Low | Combines two frames with fill logic |
| `isin()` | Low | Returns boolean — units not relevant, but wrapping keeps type |
| `between()` | Low | Series-only; returns boolean |

### 3.2 Methods Correctly Covered (Already Wrapped)

These methods are implemented and properly return Sim types with metadata propagation:

- **Data access:** `__getitem__`, `__setitem__`, `loc`, `iloc`
- **Reshaping:** `join`, `merge`, `stack`, `unstack`, `pivot`, `pivot_table`, `melt`, `transpose`
- **Aggregation:** `count`, `min`, `max`, `mean`, `median`, `mode`, `std`, `var`, `sum`, `prod`, `quantile`, `rms`
- **Manipulation:** `head`, `tail`, `copy`, `drop`, `dropna`, `drop_duplicates`, `rename`, `reindex`, `sort_values`, `sort_index`, `insert`, `append`, `concat`
- **Apply/Transform:** `apply`, `transform`, `pipe`, `map`, `where`, `mask`
- **Cumulative:** `cumsum`, `cummax`, `cummin`, `cumprod`
- **Stats:** `describe`, `skew`, `kurtosis`, `sem`, `idxmin`, `idxmax`, `rank`
- **Other:** `clip`, `abs`, `round`, `sample`, `nlargest`, `nsmallest`, `value_counts`, `nunique`, `explode`, `astype`, `fillna`, `interpolate`, `replace`, `shift`, `diff`, `squeeze`, `reset_index`
- **Window:** `rolling`, `expanding`, `ewm` (via `_SimWindowProxy`)
- **GroupBy:** `groupby` (via `_SimGroupBy`)
- **I/O:** `to_csv`, `to_json`, `to_excel`

### 3.3 Methods That Don't Need Wrapping

These methods return the same subclass type automatically through pandas' `_constructor` mechanism, or return non-DataFrame results:

- `isna()` / `notna()` — returns boolean frame, correctly delegates
- `any()` / `all()` — reduction to scalar/Series
- `to_numpy()` / `values` — returns ndarray
- `items()` / `keys()` — iteration
- `dtypes` / `shape` / `ndim` / `size` / `empty` — properties

---

## 4. Test Coverage Gaps

### 4.1 Critical (Test These First)

These are methods with confirmed bugs that have **no tests** to catch regressions:

| Method | File |
|--------|------|
| `cumsum()` | `basics.py` — BUG-01 |
| `describe()` | `basics.py` — BUG-01 |
| `filter()` (SimSeries) | `series.py` — BUG-02 |
| `sort_values()` (SimSeries, non-inplace) | `series.py` — BUG-02 |
| `drop()` (SimSeries) | `series.py` — BUG-03 |
| `dropna(inplace=True)` | `frame.py` — BUG-08 |
| `append()` (non-Sim other) | `frame.py` — BUG-06 |
| `_arithmethic_operation(fill_value=True)` | `frame.py` — BUG-07 |

### 4.2 Important (Should Have Tests)

| Category | Methods/Features |
|----------|-----------------|
| Window operations | `rolling().mean()`, `expanding().sum()`, `ewm().mean()` — verify metadata flows through proxy |
| GroupBy | `groupby().agg()`, `groupby().transform()` — verify units propagation |  
| I/O round-trip | `to_csv` → `read_csv`, `to_json` → `read_json`, `to_excel` → `read_excel` — verify units survive |
| Dunder operators | `+`, `-`, `*`, `/`, `//`, `%`, `**` — verify units algebra |
| `convert()` | Single unit, dict of units, list of units — verify conversion |
| `set_index(inplace=True)` | Already has a test from recent fix — keep and expand |
| `insert()` | Verify unit tracking at the correct position |

### 4.3 Nice-to-Have

- Alias methods (`to_Pandas`, `toPandas`, `asPandas`, etc.) — a single parametrized test
- Numbered precision comparisons (`eq0`..`eq6`, `ge0`..`ge6`, etc.)
- Property shortcuts (`s`, `df`, `ss`, `sdf`)

---

## 5. Recommended Improvements

### 5.1 Architecture

1. **Consolidate unit storage:** The codebase mixes list-based and dict-based `_units_` storage with multiple normalization paths (`_units_as_dict`, `_sync_units`, property getter). A single canonical format (list, parallel to columns) with one accessor would reduce bugs.

2. **Reduce code duplication in aggregation methods:** `min`, `max`, `mean`, `median`, `mode`, `std`, `var`, `count`, `rms`, `quantile` all follow the exact same pattern for `axis=1`. Extract a shared helper like `_aggregate_axis1(func_name, unit_rule)`.

3. **`_rewrap` should be the single wrapping path:** Some methods call `_rewrap`, others manually construct `SimDataFrame(data=..., **self.params_)`. Standardizing on `_rewrap` would centralize unit propagation logic.

### 5.2 Robustness

4. **Replace bare `except:` clauses:** There are numerous bare `except:` throughout `frame.py`, `series.py`, and `basics.py`. These swallow `KeyboardInterrupt`, `SystemExit`, and mask real bugs. Replace with `except Exception:` at minimum, or more specific exception types.

5. **Validate unit operations defensively:** `_unit_addition`, `_unit_product`, etc. can return unexpected types if given `None` or empty strings. Add guards around calls.

6. **`params_` property evaluates `self.get_units()`:** This triggers unit normalization on every metadata copy, which can be expensive for large frames and causes subtle re-entrancy. Consider caching or lazy evaluation.

### 5.3 Compatibility

7. **Deprecation warnings:** `append()` in frame.py uses `pd.concat` internally (good), but the method name mirrors the deprecated `DataFrame.append()`. Consider adding a deprecation notice or renaming to `concat_rows()`.

8. **Pandas 2.x compatibility:** Verify all methods work with pandas 2.x. The `append` method on DataFrame was removed in pandas 2.0 — the internal use of `pd.concat` is correct but external callers may be confused.

9. **`common/merger.py`:** Uses the old `.append()` pattern that was removed in pandas 2.0. Should migrate to `pd.concat()`.

### 5.4 Testing

10. **Add a conftest.py with shared fixtures:** Create reusable `SimDataFrame` and `SimSeries` fixtures with known units for consistent test setup.

11. **Parametrize alias tests:** All the naming variants (`to_Pandas`, `toPandas`, `as_pandas`, etc.) should be tested with a single parametrized test to catch capitalization bugs.

12. **CI configuration:** Add a basic `pytest` configuration in `pyproject.toml` or a GitHub Actions workflow to run tests automatically.

---

## 6. Prioritized Action Plan

### Phase 1: Fix Critical Bugs (BUG-01 through BUG-07)
These are runtime crashes — they should be fixed immediately with corresponding regression tests.

1. Fix `as_Pandas()`/`to_Pandas()` capitalization in `basics.py`
2. Fix `as_Series()` capitalization in `series.py`
3. Fix `errors='errors'` in `series.py` `drop()`
4. Fix `type(*args)` in `indexer.py` `_postprocess()`
5. Fix `for i in len(units)` in `readers/xlsx.py`
6. Fix undefined `otherC` in `frame.py` `append()`
7. Fix `fill_value` index in `frame.py` `_arithmethic_operation()`
8. Write tests for each fix

### Phase 2: Fix Medium Bugs (BUG-08 through BUG-11)
These cause incorrect behavior but don't always crash.

1. Fix `dropna()` inplace parameter swap in `frame.py`
2. Fix `set_units()` `.split()` in `index.py`
3. Wrap `corr()` return values 
4. Fix `drop(inplace=True)` column detection
5. Fix `renameItem` self-passing and `rename_item` axis dict

### Phase 3: Expand Test Coverage
Focus on the methods listed in §4.1 and §4.2.

### Phase 4: Add Missing Pandas Wrappers
Implement `resample()`, `pct_change()`, `ffill()`, `bfill()` (§3.1 High/Medium priority).

### Phase 5: Refactor and Improve
Apply improvements from §5.1–§5.4 as time allows.

---

*Generated from a full codebase audit on 2026-04-12.*
