# Unyts Bug Report: convertible('stb/day', 'sm3/day') transient False

## Summary
`unyts.convertible('stb/day', 'sm3/day')` sometimes returns `False` on initial call after import, then returns `True` after a warm-up conversion (`unyts.convert(1, 'stb/day', 'sm3/day')`).

## Environment
- simpandas development repository
- unyts version: 0.10.1
- Python version: 3.14
- OS: Windows
- Notebook: `simpandas_demo.ipynb`

## Repro steps
1. Fresh kernel/process.
2. `import unyts`
3. `print(unyts.convertible('stb/day', 'sm3/day'))`  # can be False
4. `print(unyts.convert(1, 'stb/day', 'sm3/day'))`  # should convert
5. `print(unyts.convertible('stb/day', 'sm3/day'))`  # then should be True

Optional:
```python
from simpandas.common import lazy_unyts
print(lazy_unyts.convertible('stb/day', 'sm3/day'))
```

## Observed behavior
- First call may be `False`.
- Then `convert` works and returns `0.158987...`.
- Subsequent `convertible` is `True`.

## Analysis
In `unyts/converter.py`:
- `convertible` calls `_converter(1, from_unit, to_unit)`.
- If conversion path not found immediately, it returns `False` for `None` or `Empty`.
- `_get_conversion` may return `Empty` due to graph path exploration timeout or partial cache state.
- Ratio units such as `stb/day`, `sm3/day` require recursive child search; first call can fail if cache not warmed.

`database.py` has async cache logic (`_cache_all_units`, `_wait_for_all_units_cache`) that may leave network in warmup state.

## Suggested fix for Unyts
1. In `convertible`:
   - run normal path first.
   - if false, call warmup conversion (either `convert_for_SimPandas(1, ...)` or `_converter(1, ..., use_cache=False)`).
   - retry `convertible` once and return final value.
2. Make `convertible` robust to transient `Empty` on first install/load.
3. Add regression test for warmup scenario:
   - first call might be false
   - after convert it is true

## Suggested tests
- `test_convertible_stb_sm3_warmup`.
- Confirm `convertible('stb/day','sm3/day')` stable true after warmup path.
- Add checks for mirrored operator in simpandas side if needed.

## Simpandas workaround (already implemented)
- `src/simpandas/common/lazy_unyts.py` has wrapper `convertible`:
  - attempts unyts `convertible`
  - if False, calls `convert_for_SimPandas(1, ...)` and retries.

## Diagnostics commands
```python
from unyts.database import units_network
print(units_network.has_node('stb/day'), units_network.has_node('sm3/day'))
from unyts.converter import _search_network
print(_search_network('stb/day', 'sm3/day'))
print(_search_network('stb', 'sm3'))
print('params', unyts_parameters_.cache_, unyts_parameters_.timeout_, unyts_parameters_.algorithm_)
```

## Root-cause summary
`convertible` currently conflates transient graph warm-up failure with permanent unconvertibility. fix in Unyts core so first warmup path does not produce false-negative result.
