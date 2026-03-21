# Bug Report: Unit + SimSeries Left-Operand Dispatch Bypasses Conversion

## Summary
When a unyts Unit is the left operand and a SimPandas SimSeries is the right operand, arithmetic does not follow unit-aware conversion behavior.

- Works: SimSeries + Unit
- Fails: Unit + SimSeries

This creates asymmetric behavior and can silently produce wrong values.

## Environment
- Python: 3.14
- OS: Windows
- unyts: local/dev
- simpandas: local/dev

## Minimal Reproduction
```python
import simpandas as spd
import unyts
import pandas as pd

s = pd.Series([1, 2, 3])

f = unyts.units(1.0, 'ft')
i = unyts.units(1.0, 'in')

print(f"f+i={f+i}")
print(f"i+f={i+f}")

# Plain pandas Series (not unit-aware): raw math is expected
print(f"{type(f+s)=} {f+s=}")
print(f"{type(s+f)=} {s+f=}")

# Unit-aware series
ss = spd.SimSeries(s, units='yd')

# Problem path: Unit on LEFT
print(f"{type(f+ss)=} {f+ss=}")

# Working path: SimSeries on LEFT
print(f"{type(ss+f)=} {ss+f=}")
```

## Observed Behavior
- `ss + f` converts correctly and returns a unit-aware result.
- `f + ss` does not convert as expected; values behave like raw numeric math.
- Similar issue appears with `-`, `*`, and `/` when Unit is on the left.

## Expected Behavior
For `Unit <op> SimSeries`, behavior should be equivalent to `SimSeries <op> Unit` semantics (including conversion), or Unyts should return `NotImplemented` so Python dispatches to SimSeries reflected operators (`__radd__`, etc.).

## Why This Appears To Be Unyts-Side Dispatch
SimPandas already implements reflected operators for unit-aware behavior when Unit is on the left:
- `__radd__`
- `__rsub__`
- `__rmul__`
- `__rtruediv__`

Those reflected methods only run if the left operand returns `NotImplemented`.

Current behavior suggests Unyts consumes `Unit + SimSeries` directly instead of deferring.

## Impact
- Asymmetric arithmetic semantics:
  - `ss + unit` correct
  - `unit + ss` incorrect
- Risk of silent numerical errors in unit-aware workflows.

## Suggested Fix Direction
In Unyts Unit binary operator methods (`__add__`, `__sub__`, `__mul__`, `__truediv__`):
1. Detect unsupported foreign unit-aware operands and return `NotImplemented`.
2. Optionally add explicit interop handling for SimPandas types.

## Suggested Regression Tests
- Verify `unit + simseries` matches converted semantics of `simseries + unit` for values and units.
- Add same checks for `-`, `*`, `/`.
- Verify fallback to reflected operator when foreign type is not natively handled.
