# SimPandas — Bug Reports & Fix Suggestions

Findings from integrating SimPandas 0.90.7 into the **DCA Workstation**
project. All issues were observed on Python 3.12.10, Windows 11 host,
under unit-test runs.

The packaging itself is solid — readers, writers, unit propagation,
`.to(...)` conversion all work. The two issues below are mid-priority
robustness concerns, not blockers.

---

## Issue 1 — `SimDataFrame.__setitem__` raises `KeyError` on column re-assignment when the column wasn't pre-registered in the units dict

**Severity:** medium-high (it breaks a very common pandas idiom).

**Where:** `simpandas/frame.py:836`

```python
if after == before:
    self.new_units(key, u_dict[key])     # <-- KeyError when u_dict[key] is missing
elif after > before:
    for c in range(before, after):
        ...
```

### Symptom

A user-facing call that mutates an existing column raises a *misleading*
`KeyError` whose root cause is internal bookkeeping, not the user's input:

```python
import pandas as pd
import numpy as np
import simpandas as sp

# Build a SimDataFrame with curves whose unit metadata wasn't pre-loaded
sdf = sp.read_excel("...")             # or any reader where the dict
                                        #   doesn't carry every column
# A normal pandas operation that should "just work":
sdf["GR"] = sdf["GR"].mask(sdf["GR"] == -999.25, np.nan)
# →  KeyError: 'GR'
```

The user sees a `KeyError` for a column that *exists* in the frame, which
is confusing.

### Reproduction (verified on 0.90.7)

This was reproduced inside the DCA Workstation while wrapping
`log2frame.read(...)` — the returned `SimDataFrame` has columns whose
mnemonic units are tracked in a separate Series (not the per-column
`u_dict`), and any column-level reassignment trips the bug.

Concretely it bit us when scrubbing LAS NULL placeholders:

```python
out = log_obj.data.copy()       # SimDataFrame
for col in out.columns:
    out[col] = out[col].mask(out[col].isin({-999.25}), np.nan)   # KeyError on first column
```

### Root cause

After delegating to the parent `__setitem__`:

```python
super().__setitem__(key, value)
```

…the post-write branch:

```python
if after == before:
    self.new_units(key, u_dict[key])
```

assumes `u_dict` is populated for every existing column. But in many
constructor paths `u_dict` is built from the *incoming* value (e.g.
`u_dict = {str(key): value.units}` in line 781), so it contains only the
*new* column's unit, not the pre-existing column's unit. When `key`
already existed in `self.columns`, the lookup `u_dict[key]` raises.

A second issue: the `elif after > before:` branch already uses
`u_dict.get`-style guarding (`if self.columns[c] in u_dict`), but the
`if after == before:` branch doesn't.

### Suggested fix

Add the same guarding pattern that the new-column branch already uses:

```python
if after == before:
    # The pre-existing column isn't necessarily in u_dict (it depends
    # on which constructor path built it). Fall back to the existing
    # unit on `self` if the incoming u_dict didn't carry one, then to
    # 'unitless' as a last resort.
    if key in u_dict:
        self.new_units(key, u_dict[key])
    else:
        existing = self.get_units().get(key, 'unitless') \
                   if hasattr(self, 'get_units') else 'unitless'
        self.new_units(key, existing)
elif after > before:
    for c in range(before, after):
        if self.columns[c] in self.columns[before:after] and self.columns[c] in u_dict:
            self.new_units(self.columns[c], u_dict[self.columns[c]])
        else:
            self.new_units(self.columns[c], 'unitless')
```

This preserves the existing column's unit when re-assignment happens
without the user needing to supply one explicitly — and never raises.

### Defensive test for the SimPandas test suite

```python
def test_setitem_existing_column_preserves_unit():
    sdf = SimDataFrame(
        {"GR": [50.0, 60.0, 70.0], "RHOB": [2.5, 2.4, 2.3]},
        units={"GR": "gAPI", "RHOB": "g/cc"},
    )
    sdf["GR"] = sdf["GR"].mask(sdf["GR"] == 60.0, 0.0)   # must not raise
    assert sdf.get_units()["GR"] == "gAPI"
```

### Workaround we used in the meantime

Cast to a plain `pandas.DataFrame` before mutation, then re-attach
units on the way out:

```python
out = pd.DataFrame(df.values, index=df.index.copy(), columns=list(df.columns))
# safe to mutate now
```

This works but loses the unit metadata, so we have to re-build the
units dict by hand from the original `log_obj.units` Series. A native
fix on the SimPandas side would let downstream tooling stay
unit-aware throughout.

---

## Issue 2 — Deprecation warning on every `SimSeries` construction

**Severity:** low (warning only; will become a real failure in a
future pandas release).

**Where:** `simpandas/series.py:173`

```python
super().__init__(data=data, index=index, dtype=dtype, name=name, copy=copy, fastpath=fastpath)
```

### Symptom

Every `SimSeries` instantiation emits:

```
DeprecationWarning: The 'fastpath' keyword in pd.Series is deprecated
and will be removed in a future version.
```

In a pytest run with hundreds of SimSeries operations the warning is
emitted repeatedly, polluting the output and (in projects that use
`-W error`) failing the suite.

### Suggested fix

Drop the `fastpath` kwarg unconditionally — it's been an internal,
private pandas optimisation since pandas 1.0 and was never part of the
public API:

```python
super().__init__(
    data=data, index=index, dtype=dtype, name=name, copy=copy,
)
```

If there's a code path inside SimPandas that depends on the truthy
behaviour of `fastpath` (very unlikely — it bypasses validation), gate
it behind a pandas-version sniff:

```python
import pandas as pd
from packaging.version import Version

_PANDAS_HAS_FASTPATH = Version(pd.__version__) < Version("3.0")
kwargs = dict(data=data, index=index, dtype=dtype, name=name, copy=copy)
if _PANDAS_HAS_FASTPATH:
    kwargs["fastpath"] = fastpath
super().__init__(**kwargs)
```

### Defensive test

```python
import warnings
def test_simseries_no_deprecation_on_construct():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        _ = SimSeries([1.0, 2.0, 3.0], units="psi")    # must not raise
```

---

## Issue 3 — `bool(SimSeries)` ambiguity when used in `or` short-circuit

**Severity:** low-medium (it surprises users writing the standard pandas
"falsy guard" idiom).

**Where:** any user code that does

```python
units = log_obj.units or {}        # log_obj.units is a SimSeries
```

### Symptom

A multi-element `SimSeries` (which is what `Log.units` is in the
`log2frame` integration) raises `ValueError` when evaluated as a
boolean, the same as plain pandas does:

```
ValueError: The truth value of a Series is ambiguous.
Use a.empty, a.bool(), a.item(), a.any() or a.all().
```

This is *consistent* with pandas, so it's arguably "by design", but
it's a friction point because:

1. The doc-string for `SimSeries` doesn't note that it inherits this
   behaviour.
2. Users coming from a "dictionary of units" mental model expect
   `units or {}` to mean "use units if non-empty, else empty dict",
   which works for plain dicts.

### Suggested fix (documentation, not code)

Add a one-paragraph note to the `SimSeries` docstring under a
**"Truthiness"** heading:

> Because `SimSeries` inherits from `pandas.Series`, the standard
> "falsy or fallback" idiom (`series or {}`) does not work and raises
> `ValueError` on multi-element series. Use `series.empty`,
> `len(series) == 0`, or an explicit `series if series is not None
> else {}` instead.

A code-level helper would also be welcomed — e.g. a `series.as_dict()`
shortcut that returns `{}` when empty and `dict(series)` otherwise:

```python
def as_dict(self) -> dict:
    """Return ``dict(self)`` when non-empty, else an empty dict.

    Useful for the common idiom ``units = sdf.units.as_dict()`` where
    plain ``dict(sdf.units)`` raises if the underlying Series isn't
    materialised.
    """
    if self.empty:
        return {}
    return dict(self)
```

---

## Summary

| # | Severity | Type | Suggested fix |
|---|---|---|---|
| 1 | Medium-high | Code (KeyError on common idiom) | Guard `u_dict[key]` lookup; fall back to existing unit |
| 2 | Low | Code (DeprecationWarning) | Drop the `fastpath=` kwarg from the Series super-call |
| 3 | Low | Documentation + minor convenience | Document inherited truthiness; consider `series.as_dict()` |

All three fixes are 1-5 lines of code each. None require API
changes — the public surface stays identical for callers who don't
hit the broken path today.

Happy to send pull requests for any of these if it'd help.
