# SimPandas Maintainer Skill

## Purpose
Use this skill when implementing or reviewing changes in this repository so unit metadata behavior stays correct and pandas wrappers remain consistent.

## When To Use
- Adding new `SimDataFrame` or `SimSeries` methods.
- Wrapping pandas methods that currently return bare pandas objects.
- Fixing metadata propagation bugs (`units`, `index_units`, `params_`).
- Updating docs/tests after behavior changes.

## Core Rules
1. If a method returns a DataFrame/Series, return a Sim type.
2. Prefer shared wrappers in `SimBasics` when behavior is common to both types.
3. Use `self._rewrap(...)` when pandas return type may vary.
4. Use `self._class(data=..., **self.params_)` when return shape/type is predictable.
5. Add or update tests in `test/` for every behavior change.
6. Update docs (`README.md`, `USER_MANUAL.md`, `docs/USER_GUIDE.md`, `WHATS_NEW.md`, `CHANGELOG.md`) when public behavior changes.

## Wrapper Decision Guide

### Case A: Shared method, predictable shape
Use in `src/simpandas/basics.py`:

```python
def my_method(self, ...):
    return self._class(data=self.as_pandas().my_method(...), **self.params_)
```

### Case B: Shared method, variable return type
Use `_rewrap`:

```python
def my_method(self, ...):
    return self._rewrap(self.as_pandas().my_method(...))
```

### Case C: Proxy-returning APIs
For APIs like window/groupby/resample that return rich intermediate objects,
add/extend a proxy in `src/simpandas/frame.py` and call it from both classes.
Current proxies:
- `_SimWindowProxy`
- `_SimGroupBy`
- `_SimResampleProxy`

### Case D: In-place methods
If pandas method is in-place (`update`, etc.), preserve Sim object and return
`None` unless API explicitly requires otherwise.

## Filter System Notes
- `SimDataFrame.filter()` and `SimSeries.filter()` rely on
  `simpandas.common.filters.key_to_string(...)`.
- If changing filter parser logic, test both:
  - Index-only conditions (`">1"`)
  - Mixed expressions (`"a > 1 and < 3"`)
- Confirm filtered results remain wrapped Sim objects.

## Recommended Test Commands

```powershell
python -m pytest test/test_missing_wrappers.py -v
python -m pytest test/test_audit_bugs.py -v
python -m pytest test/test_frame.py test/test_series.py test/test_basics.py -v
python -m pytest test/common/ -v
```

## Release-Quality Checklist
- [ ] New or changed wrappers covered by tests.
- [ ] No new bare pandas return values from public Sim methods.
- [ ] Units behavior verified (preserved, intentionally changed, or documented).
- [ ] `WHATS_NEW.md` updated.
- [ ] `CHANGELOG.md` updated.
- [ ] User docs updated for new public methods.

## Project-Specific Pitfalls
- `_units_` is positional and must stay in sync with columns.
- Some pandas internals create objects without full constructor paths; rely on
  existing guard patterns in `SimBasics` and wrappers.
- `compare()` and shape-changing methods may require minimal metadata
  reconstruction when result columns differ from source columns.
