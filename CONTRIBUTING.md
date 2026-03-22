# Contributing to SimPandas

Thank you for your interest in contributing!  This document covers everything
you need to get a development environment running, understand the project
conventions, and submit a high-quality pull request.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Development Setup](#2-development-setup)
3. [Branch Strategy](#3-branch-strategy)
4. [Running Tests](#4-running-tests)
5. [Code Conventions](#5-code-conventions)
6. [Adding a New Feature](#6-adding-a-new-feature)
7. [Submitting a Pull Request](#7-submitting-a-pull-request)
8. [Release Process](#8-release-process)

---

## 1. Prerequisites

- **Python 3.9+** (tested on 3.14)
- **pip** (or an equivalent package manager)
- **git**

Required packages installed automatically by `pip install -e .`:

| Package | Purpose |
|---|---|
| `pandas` | Core data structures |
| `numpy` | Numeric operations |
| `unyts >= 0.5.25` | Physical unit arithmetic |
| `openpyxl` | Excel read/write |
| `xlsxwriter` | Excel write (alternative engine) |
| `matplotlib` | Plotting helpers |
| `seaborn` | Statistical plot helpers |

---

## 2. Development Setup

```powershell
# 1. Clone the repository
git clone <repo-url> simpandas
cd simpandas

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1       # Windows PowerShell
# or: source .venv/bin/activate  # Linux / macOS

# 3. Install in editable mode with all dependencies
pip install -e .

# 4. Verify the install
python -c "import simpandas; print(simpandas.__version__)"
```

---

## 3. Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable releases only |
| `development` | Integration branch — all PRs target this |
| `feature/<short-name>` | Feature branches (personal forks) |
| `bugfix/<short-name>` | Bug-fix branches |

**Always branch off `development`, never off `main`.**

---

## 4. Running Tests

```powershell
# Run the full test suite
python -m pytest test/ -v

# Run just the core reliability tests before submitting
python -m pytest test/test_frame.py test/test_indexer.py test/test_new_features.py -v

# Run a single test file
python -m pytest test/common/test_stringformat.py -v

# Run a single test
python -m pytest test/test_new_features.py::TestGroupBy::test_groupby_sum -v
```

**All tests targeted by your change must pass before opening a PR.**

At the current 0.84.x baseline, the repository test suite is expected to pass
cleanly apart from explicitly skipped tests.

---

## 5. Code Conventions

### General

- Follow the style already present in the file you are editing.
- Keep methods short.  If a method body exceeds ~40 lines, consider extracting helpers.
- Prefer explicit over implicit.  Do not rely on pandas default behaviour when
  unit propagation is involved — always construct the result explicitly with
  `**self.params_`.

### Unit propagation

Every method that returns a new `SimDataFrame` or `SimSeries` **must** pass
`**self.params_` (or the appropriate subset) to the constructor.

```python
# Good
return self._class(data=result, **self.params_)

# Also good — using _rewrap
return self._rewrap(result)

# Bad — loses units, name_separator, verbose, etc.
return SimDataFrame(result)
```

### `_rewrap` vs manual construction

Use `_rewrap(result)` for methods that:
- Return the same column set as the input, **or**
- Change the column set but can tolerate best-effort unit copy (units for
  new columns will be `None`).

Use manual construction when you need precise control over which units are
assigned to which columns in the result.

### Private attributes

Set private attributes with `object.__setattr__` inside `__init__` and
inside `__finalize__`:

```python
object.__setattr__(self, '_my_attr_', value)
```

Using `self._my_attr_ = value` inside a method body is fine, but inside
`__init__` it will be intercepted by pandas and treated as a column.

### Naming

- New methods follow existing naming conventions:
  - snake_case for standard public methods.
  - CamelCase aliases (`toSimDataFrame`, `asPandas`) are accepted only when
    explicitly requested for backward compatibility.
- Attribute names that cross-cut `SimDataFrame` and `SimSeries` should be added
  to `_metadata` so pandas propagates them automatically.

### Logging

- Use `logging.info(...)` for user-facing informational messages.
- Guard with `if self.verbose:` when the message is only useful for debugging.
- Do not use `print()` in library code.

---

## 6. Adding a New Feature

### New shared method (DataFrame + Series)

1. Add the method to `SimBasics` in `basics.py`.
2. Use `_rewrap` or manual construction to return Sim types.
3. Add at least one test in `test/test_new_features.py` verifying:
   - The result type is `SimDataFrame` / `SimSeries`.
   - Units survive the operation.

### New DataFrame-only method

1. Add to `SimDataFrame` in `frame.py`.
2. Place it in the appropriate block (after `ewm()`/`groupby()` overrides,
   before the final `@property` block).
3. Same testing requirements as above.

### New utility function

1. Add to the appropriate module in `simpandas/common/`.
2. Export from `simpandas/common/__init__.py`.
3. Add a unit test in `test/common/test_<module>.py`.

### New I/O format

See the detailed guide in `DEVELOPER_MANUAL.md § 12`.

---

## 7. Submitting a Pull Request

### PR checklist

- [ ] Branch is based on `development`.
- [ ] `python -m pytest test/test_frame.py test/test_indexer.py test/test_new_features.py -v` — all pass.
- [ ] New public methods have a one-line docstring.
- [ ] `_metadata` updated if a new persistent attribute was added.
- [ ] If a new I/O reader was added: exported from `readers/__init__.py` and
      `simpandas/__init__.py`.
- [ ] `WHATS_NEW.md` updated (add a bullet under the appropriate version).
- [ ] Version bump if you are preparing a release (otherwise change to `WHATS_NEW.md` is enough).

### PR description

Briefly describe:
1. **What** was changed.
2. **Why** (link to issue if applicable).
3. **How** to test it manually beyond the automated tests.

---

## 8. Release Process

1. All changes merged to `development` and tests passing.
2. Bump version in `pyproject.toml`, `src/simpandas/__init__.py`, and the
   affected module files (`__version__` and `__release__`).
3. Update `WHATS_NEW.md` with the release date and a summary.
4. Build: `python -m build`
5. Validate: `twine check dist/*`
6. Publish: `twine upload dist/*`
7. Merge `development` → `main` and tag the commit: `git tag vX.Y.Z`
