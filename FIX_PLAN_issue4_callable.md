# Fix Plan — Issue #4: `SimSeries.__call__` interferes with `apply_if_callable`

**Date:** 2026-04-27  
**Source:** [FIX_SUGGESTIONS_simpandas_followup.md](FIX_SUGGESTIONS_simpandas_followup.md)  
**Severity:** Medium  
**Target version:** 0.90.9

---

## Problem

`SimSeries` defines `__call__` (line 431 in `series.py`) as a convenience accessor:

```python
def __call__(self, key=None):
    if key is None:
        return self.values
    else:
        return self[key].values
```

This makes `callable(simseries)` return `True`. Pandas internally uses `apply_if_callable(maybe_callable, obj)` in many methods (`.mask()`, `.where()`, `.assign()`, `.pipe()`, etc.). When a `SimSeries` is passed as the `cond` argument, pandas treats it as a function and invokes `cond(self)` — which routes to `SimSeries.__call__(key=<data_series>)` → `__getitem__` → `KeyError`.

**Affected methods:** Any method that passes through `pandas.core.common.apply_if_callable`:
- `mask(cond, other)`
- `where(cond, other)`
- `assign(**kwargs)` (when values are callables)
- `pipe(func)` (indirectly)

---

## Evaluation

The reporter recommends combining fixes **(a)** + **(b)**. I agree — this provides both a targeted fix for known wrappers and a global safety net for unwrapped pandas methods.

| Fix | Scope | Risk | Lines |
|-----|-------|------|-------|
| **(a)** Strip SimSeries args in `mask`/`where` wrappers | Targeted — only wrapped methods | Minimal | ~8 |
| **(b)** Make `__call__` Series/DataFrame-aware | Global — protects unwrapped methods too | Low | ~5 |
| **(c)** Drop `__call__` entirely | Cleanest but breaks backward compat | Medium | N/A |

**Decision: Implement (a) + (b).**

---

## Implementation Plan

### Step 1a — Harden `SimSeries.__call__` (fix b)

**File:** `src/simpandas/series.py`, lines 431–438

When `__call__` receives a pandas Series or DataFrame as `key`, it's being invoked by `apply_if_callable`. In that case, return `self` unchanged (act as a non-callable passthrough).

```python
def __call__(self, key=None):
    """
    Returns the series values, a NumPy array or number without units.

    Special-case: if ``key`` is itself a Series or DataFrame, this
    method is being called by pandas' ``apply_if_callable`` inside
    ``.mask()`` / ``.where()`` / ``.assign()`` etc.  Return ``self``
    so pandas treats this SimSeries as a non-callable value.
    """
    if key is None:
        return self.values
    import pandas as pd
    if isinstance(key, (pd.Series, pd.DataFrame)):
        return self
    return self[key].values
```

### Step 1b — Harden `SimDataFrame.__call__` (same pattern)

**File:** `src/simpandas/frame.py`, lines 540–546

**Confirmed via live testing:** `SimDataFrame` also defines `__call__`, so
`callable(simdataframe)` is `True`. `sdf.mask(sdf > 2)` crashes with
`ValueError: The truth value of a DataFrame is ambiguous` because
`apply_if_callable` invokes `cond(self)` → `SimDataFrame.__call__(key=<data_df>)`
→ `__getitem__` → `bool(key)` on a multi-element DataFrame.

Apply the same guard:

```python
def __call__(self, key=None):
    import pandas as pd
    if isinstance(key, (pd.Series, pd.DataFrame)):
        return self
    if key is None:
        key = self.columns
    result = self.__getitem__(key)
    if isinstance(result, SimSeries):
        result = result.__call__()
    return result
```

**Rationale:** This is the global safety net. Any current or future pandas internals that call `apply_if_callable` will get the correct behavior without requiring wrapper-level fixes.

### Step 2 — Sanitize args in `mask` and `where` wrappers (fix a)

**File:** `src/simpandas/basics.py`, lines 291–297

Convert `cond` and `other` to plain pandas before delegating. This is the belt-and-suspenders defense at the wrapper boundary.

```python
def where(self, cond, other=None, *args, **kwargs):
    """Replace values where the condition is False, preserving units."""
    if hasattr(cond, 'as_pandas'):
        cond = cond.as_pandas()
    if hasattr(other, 'as_pandas'):
        other = other.as_pandas()
    return self._rewrap(self.as_pandas().where(cond, other, *args, **kwargs))

def mask(self, cond, other=None, *args, **kwargs):
    """Replace values where the condition is True, preserving units."""
    if hasattr(cond, 'as_pandas'):
        cond = cond.as_pandas()
    if hasattr(other, 'as_pandas'):
        other = other.as_pandas()
    return self._rewrap(self.as_pandas().mask(cond, other, *args, **kwargs))
```

**Rationale:** Even though step 1 fixes the global case, explicitly stripping Sim wrappers at the boundary makes the code self-documenting and prevents any future regression if `__call__` behavior changes.

### Step 3 — Add tests

**File:** `test/test_bugfix_dca.py` (append new class)

```python
class TestApplyIfCallable:
    """Issue #4: SimSeries.__call__ must not interfere with pandas
    apply_if_callable used inside .mask(), .where(), etc."""

    def test_simseries_mask_with_series_cond(self):
        sdf = SimDataFrame({"GR": [50., 60., 70.]}, units={"GR": "gAPI"})
        gr = sdf["GR"]
        masked = gr.mask(gr == 60.0, 0.0)
        assert masked.tolist() == [50., 0., 70.]
        assert masked.units == "gAPI"

    def test_simseries_where_with_series_cond(self):
        sdf = SimDataFrame({"GR": [50., 60., 70.]}, units={"GR": "gAPI"})
        gr = sdf["GR"]
        kept = gr.where(gr > 55, 0.0)
        assert kept.tolist() == [0., 60., 70.]

    def test_simdataframe_setitem_via_mask(self):
        """The full end-to-end pattern from the original report."""
        sdf = SimDataFrame({"GR": [50., 60., 70.]}, units={"GR": "gAPI"})
        sdf["GR"] = sdf["GR"].mask(sdf["GR"] == 60., 0.)
        assert sdf.get_units("GR") == "gAPI"
        assert sdf["GR"].tolist() == [50., 0., 70.]

    def test_simseries_call_with_key_still_works(self):
        """Backward compat: series(key) must still work."""
        ss = SimSeries([10, 20, 30], index=['a', 'b', 'c'], units='m')
        assert ss('b') == 20       # existing __call__ behavior
        assert list(ss()) == [10, 20, 30]  # ss() returns values

    def test_simseries_call_with_series_arg_returns_self(self):
        """When __call__ receives a Series (apply_if_callable pattern),
        it must return self unchanged."""
        import pandas as pd
        ss = SimSeries([1, 2, 3], units='m')
        result = ss(pd.Series([10, 20, 30]))
        assert result is ss

    def test_simdataframe_mask_preserves_unit(self):
        """mask() on a SimDataFrame itself (not just SimSeries)."""
        sdf = SimDataFrame(
            {"GR": [50., 60., 70.], "RHOB": [2.5, 2.4, 2.3]},
            units={"GR": "gAPI", "RHOB": "g/cc"})
        masked = sdf.mask(sdf > 60)   # NaN where > 60
        assert masked.get_units("GR") == "gAPI"
        assert masked.get_units("RHOB") == "g/cc"
```

### Step 4 — Update documentation

- **CHANGELOG.md**: Add entry under `[0.90.9]` for the `__call__` fix.
- **DEVELOPER_MANUAL.md**: Add a note under Common Pitfalls about `__call__` and `apply_if_callable`.

---

## Files Modified

| File | Change |
|------|--------|
| `src/simpandas/series.py` | Harden `__call__` to detect Series/DataFrame args |
| `src/simpandas/frame.py` | Harden `__call__` to detect Series/DataFrame args |
| `src/simpandas/basics.py` | Sanitize `cond`/`other` in `mask()` and `where()` |
| `test/test_bugfix_dca.py` | Add `TestApplyIfCallable` (~8 tests) |
| `CHANGELOG.md` | New entry |
| `DEVELOPER_MANUAL.md` | Pitfall note |

---

## Risk Assessment

- **Backward compatibility:** `__call__` still works for string/int keys (step 1 only intercepts Series/DataFrame). No API break.
- **Edge case:** A user calling `series(another_series)` to index will now get `self` back instead of a `KeyError`. This is arguably better behavior — the old code crashed in this case anyway.
- **Regression risk:** Minimal. The `as_pandas()` stripping in step 2 is a no-op for already-plain types, and `_rewrap` already handles the re-wrapping.
