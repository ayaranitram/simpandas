# Unyts Issue Report: First-call false for `convertible('stb/day', 'sm3/day')` in notebook

## Description
In Jupyter notebook `simpandas_demo.ipynb` (cells 79 and 80), after:

```python
import unyts
```

calling:

```python
unyts.convertible('stb/day', 'sm3/day')
```

returns `False`, but after executing conversion:

```python
unyts.convert(1, 'stb/day', 'sm3/day')
```

then:

```python
unyts.convertible('stb/day', 'sm3/day')
```

returns `True`.

This is a transient warmup issue within `unyts.convertible` logic.

## Environment
- Python 3.14
- unyts 0.10.1
- simpandas Dev
- Notebook path: `D:\git\simpandas\simpandas_demo.ipynb`

## Steps to reproduce
1. Open notebook and restart kernel.
2. Execute cells up to and including `import unyts`.
3. Call `unyts.convertible('stb/day', 'sm3/day')` -> expect `True` but observed `False`.
4. Call `unyts.convert(1, 'stb/day', 'sm3/day')` -> returns ~0.158987
5. Call `unyts.convertible('stb/day', 'sm3/day')` -> now returns `True`.

## Root cause analysis
- `convertible` is implemented as:
  - run `_converter(1, from, to)`
  - return `False` if result is `None` or `Empty`
- `_converter` with ratio units can need graph memoization and may yield `Empty`/`None` on first attempt when internal network cache not warmed.
- After `convert`, conversion path is cached (`units_network.memory`), so next `convertible` succeeds.

## Minimal reproducer (out-of-notebook)
```python
import unyts

print(unyts.convertible('stb/day', 'sm3/day'))        # may be False immediately
print(unyts.convert(1, 'stb/day', 'sm3/day'))          # should return ~0.158987
print(unyts.convertible('stb/day', 'sm3/day'))        # should be True after warmup
```

## Suggested upstream fix for unyts
1. In `convertible` (converter.py):
   - If first call returns False, do one warmup conversion path:
     - `(try/except) unyts.convert(1, from_unit, to_unit)` or `_converter(1, ..., use_cache=False)`.
   - Re-run convertible and return new result (or False if now still fails).
2. Add a regression test for this warmup behavior.
3. Consider reducing false/Empty classification for first-call cache-miss cases.

## Potential simpandas temporary fix (already done)
- `src/simpandas/common/lazy_unyts.py` wrapper now does warmup on false convertibility by calling `convert_for_SimPandas` and retrying.

## Additional diagnostic commands
```python
from unyts.database import units_network
from unyts.converter import _search_network

print('network nodes', units_network.has_node('stb/day'), units_network.has_node('sm3/day'))
print(_search_network('stb/day','sm3/day'))
print(_search_network('stb','sm3'))
```

## Notes for unyts team
- This is not simpandas-specific; it's in `convertible` semantics on cold start.
- With fix, notebook users should get consistent `True` behavior immediately.
