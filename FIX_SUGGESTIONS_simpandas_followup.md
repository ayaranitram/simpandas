# SimPandas — Follow-up after 0.90.8

Verification of the three issues raised in the original report against
the new `simpandas==0.90.8` release (PyPI) / `development` branch on
GitHub. Two of the three are fully fixed, and one new related issue
surfaced as a result of fixing #1 — reporting it here for your
consideration.

---

## ✅ Issue 1 — `__setitem__` KeyError on column re-assignment

**Status: Fixed.** The patch in `frame.py` lines 835-851 is exactly the
guard I suggested, with an extra nuance I think is **better than my
proposal**:

```python
if after == before:
    incoming_unit = u_dict.get(key)
    if incoming_unit is not None and incoming_unit != 'unitless':
        # The incoming value explicitly carries a unit — use it.
        self.new_units(key, incoming_unit)
    elif key in self.columns:
        # ... preserve the column's existing unit ...
        existing_unit = self.get_units(key)
        if existing_unit is None:
            existing_unit = incoming_unit if incoming_unit is not None else 'unitless'
        self.new_units(key, existing_unit)
    else:
        self.new_units(key, incoming_unit if incoming_unit is not None else 'unitless')
```

The "explicit incoming unit takes precedence over existing" tier-rule
(the first branch) lets users intentionally override a column's unit
via assignment — the simple `u_dict.get(key)` fallback I proposed
would have always preserved the existing unit. Your version is more
flexible and matches user intent better.

**Verification on our side** (`simpandas==0.90.8`):

```python
import simpandas as sp
sdf = sp.SimDataFrame(
    {"GR": [50.0, 60.0, 70.0]}, units={"GR": "gAPI"})
sdf["GR"] = sdf["GR"].mask(sdf["GR"] == 60.0, 0.0)   # 0.90.7: KeyError
                                                       # 0.90.8: now triggers Issue #4 below
```

In isolation the `__setitem__` change alone would let our existing
tests run without the plain-pandas workaround. Unfortunately the
`.mask()` chain hits a different problem — Issue #4.

---

## ✅ Issue 2 — `fastpath` DeprecationWarning

**Status: Fixed.** `series.py:180` no longer passes `fastpath=` to the
parent `__init__`. Verified — no DeprecationWarning is emitted on
SimSeries construction in 0.90.8.

---

## ✅ Issue 3 — `bool(SimSeries)` ambiguity in `or` short-circuit

**Status: Fixed by a much better solution than I suggested.**

I asked for a docstring caution + an optional `as_dict()` helper. You
went considerably further: introduced a brand-new `ColumnUnits` class
(`common/units.py`) that:

* Subclasses `collections.abc.Mapping` — so `len()`, `__bool__`,
  `__iter__`, `__contains__` are all well-defined and fast. The
  conventional `dict(units or {})` idiom now does exactly what users
  expect.
* Supports **duplicate keys** — addresses the multi-occurrence column-
  name case (e.g. two `RHOB` curves from different runs) that the
  bare-Series approach silently mis-handled.
* Has explicit `to_dict()`, `to_list()`, `to_series()` conversions
  with documented duplicate-key semantics.
* Has an `iloc` accessor for positional read/write.

This is the right design. It supersedes the `as_dict()` helper I
suggested and replaces it with a proper container type that the rest
of SimPandas (and downstream consumers like log2frame) can lean on.

---

## 🆕 Issue 4 — `SimSeries.__call__` interferes with pandas' `apply_if_callable`

**Severity: medium.**

This issue was *masked* by the original bug #1: when I worked around
#1 with a plain-pandas cast, I never triggered the path where
SimSeries' `__call__` confuses pandas. With #1 now fixed properly, my
direct attempt to use the SimDataFrame end-to-end hit this new
problem.

### Symptom

A common pandas idiom raises a misleading `KeyError` whose root cause
is again internal:

```python
import simpandas as sp
sdf = sp.SimDataFrame({"GR": [50.0, 60.0, 70.0]}, units={"GR": "gAPI"})
gr = sdf["GR"]                          # SimSeries
masked = gr.mask(gr == 60.0, 0.0)       # ← KeyError
```

### Full traceback (in 0.90.8)

```
SimBasics.mask  (basics.py:297)
   → self._rewrap(self.as_pandas().mask(cond, other, …))
pandas.Series.mask  (pandas/core/generic.py:11131)
   → cond = common.apply_if_callable(cond, self)
pandas.common.apply_if_callable  (pandas/core/common.py:384)
   → maybe_callable(obj, **kwargs)         #  ← treats `cond` as callable
SimSeries.__call__  (series.py:438)
   → return self[key].values               #  cond is the *condition* SimSeries,
                                            #  but it's being called with `self` as `key`
SimSeries.__getitem__  (series.py:488)
   → raise KeyError("the requested Key is not a valid index or name: …")
```

### Root cause

Pandas' helper `apply_if_callable` does roughly:

```python
def apply_if_callable(maybe_callable, obj, **kwargs):
    if callable(maybe_callable):
        return maybe_callable(obj, **kwargs)
    return maybe_callable
```

For a plain `pandas.Series`, `callable(series)` is `False` (no
`__call__`), so the helper returns the series unchanged.

For a `SimSeries`, `callable(simseries)` is `True` because SimSeries
defines `__call__` (the `series()` / `series(key)` getter convenience
in `series.py:431-438`). Pandas then *invokes* the SimSeries as a
function with `obj=self` (the data Series), which routes through
`SimSeries.__call__(key=data_series)` → `self[key].values` →
`__getitem__` failure.

So **any** pandas method that runs `apply_if_callable` on a Series
argument mis-handles a SimSeries. Common culprits include
`.mask(cond, other)`, `.where(cond, other)`, `.assign(col=lambda)`,
`.pipe(func)`, and `.apply(func)`.

### Suggested fixes (in increasing order of intrusion)

#### (a) Convert SimSeries args to plain pandas inside the wrapped methods

In `SimBasics.mask` (and `where`, and any other method that takes a
condition Series argument), convert the `cond` to a plain pandas
Series before delegating:

```python
def mask(self, cond, other=None, *args, **kwargs):
    """Replace values where the condition is True, preserving units."""
    if hasattr(cond, "as_pandas"):     # SimSeries → plain Series
        cond = cond.as_pandas()
    if hasattr(other, "as_pandas"):
        other = other.as_pandas()
    return self._rewrap(self.as_pandas().mask(cond, other, *args, **kwargs))
```

Tiny change, affects only the methods you've already wrapped. Doesn't
break anything; the fixed methods stop tripping `apply_if_callable`.

#### (b) Make SimSeries' `__call__` compatible with pandas' `apply_if_callable` semantics

`apply_if_callable(cond, self)` invokes `cond(self)` expecting "apply
this function to self". Currently `SimSeries.__call__` interprets the
arg as a *key* into the series, which is unrelated. One option: detect
when `__call__` is being invoked with another Series/DataFrame as the
sole positional arg (the `apply_if_callable` signature) and return
`self` unchanged in that case:

```python
def __call__(self, key=None):
    """
    Returns the series values, a NumPy array or number without units.

    Special-case: if `key` is itself a Series or DataFrame, this method
    is being called as a pandas-style callable (via `apply_if_callable`
    inside .mask/.where/.assign/etc.). Return `self` so pandas treats
    this SimSeries as a non-callable.
    """
    if key is None:
        return self.values
    import pandas as pd
    if isinstance(key, (pd.Series, pd.DataFrame)):
        return self                 # behave as if not callable
    return self[key].values
```

Slightly more invasive but it fixes the problem globally — any pandas
method that goes through `apply_if_callable` will work with SimSeries.

#### (c) Drop `__call__` entirely

Cleanest from a "least surprise" perspective but breaks API
compatibility for users who relied on `series()` and `series(key)`.
I'd only recommend this if those forms aren't widely used.

### My recommendation

Combine **(a)** + **(b)**: convert SimSeries args defensively at the
wrapper-method boundary (so the existing wrapped methods are
bulletproof) AND make `__call__` Series/DataFrame-aware (so
unwrapped pandas methods don't break either when they call
`apply_if_callable`). The two together are about 15 lines of code and
fix the entire family of problems for any pandas method, present and
future.

### Defensive test

```python
import warnings
import simpandas as sp


def test_simseries_mask_with_series_cond():
    sdf = sp.SimDataFrame({"GR": [50., 60., 70.]}, units={"GR": "gAPI"})
    gr = sdf["GR"]
    masked = gr.mask(gr == 60.0, 0.0)            # must not raise
    assert masked.tolist() == [50., 0., 70.]
    assert masked.units == "gAPI"


def test_simseries_where_with_series_cond():
    sdf = sp.SimDataFrame({"GR": [50., 60., 70.]}, units={"GR": "gAPI"})
    gr = sdf["GR"]
    kept = gr.where(gr > 55, 0.0)
    assert kept.tolist() == [0., 60., 70.]


def test_simdataframe_setitem_via_mask():
    sdf = sp.SimDataFrame({"GR": [50., 60., 70.]}, units={"GR": "gAPI"})
    sdf["GR"] = sdf["GR"].mask(sdf["GR"] == 60., 0.)
    assert sdf.get_units()["GR"] == "gAPI"
    assert sdf["GR"].tolist() == [50., 0., 70.]
```

### Workaround we're using

We've kept our `_scrub_nulls()` helper that casts to plain
`pandas.DataFrame` before mutation, then re-attaches units from
`log_obj.units` separately. It's defensive against both the original
0.90.7 KeyError AND this new `apply_if_callable` interaction. We've
documented why in a code comment — once SimPandas fixes #4 we can
remove the helper and operate directly on the SimDataFrame.

---

## Summary

| # | Status in 0.90.8 | Notes |
|---|---|---|
| 1 | ✅ Fixed | Better than I proposed (incoming-unit-precedence rule) |
| 2 | ✅ Fixed | Clean — `fastpath` removed |
| 3 | ✅ Fixed | Excellent — new `ColumnUnits` Mapping class |
| 4 | 🆕 New | Surfaced after #1 was fixed; suggested fixes (a)+(b) above |

Verification environment: Python 3.12.10, Windows 11, pandas 2.3.3,
SimPandas 0.90.8, log2frame 0.2.1. The DCA Workstation regression
suite (86 tests across log_io, petrophysics, data_io, fluid_model,
fluid panels, EOS panel) passes against 0.90.8 with our existing
plain-pandas workaround in place.

Thanks for the very fast turnaround on the original three. Happy to
PR any of the suggested changes for #4 if it'd help.
