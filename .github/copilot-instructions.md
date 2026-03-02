# simpandas Codebase – Copilot Instructions

These notes are meant to get an AI agent up and running quickly. The project is a small
library that wraps **pandas** `DataFrame`/`Series` with unit support (via **unyts**) and
adds a handful of domain‑specific helpers.

---
## 🧠 Big Picture

* **Core types** live under `src/simpandas`:
  * `frame.py` defines `SimDataFrame` (inherits `pandas.DataFrame`).
  * `series.py` defines `SimSeries` (inherits `pandas.Series`).
  * `index.py` defines `SimIndex` (a `MultiIndex` subclass with units).
  * `basics.py` contains a mix‑in `SimBasics` shared by both classes.
  * `indexer.py` overrides `.loc`/`.iloc` to track unit conversions and wrap results.

* All the helpers that aren’t part of pandas itself live in `src/simpandas/common`.
  Modules there (`math`, `renamer`, `slope`, `stringformat`, `daterelated`, etc.)
  are imported liberally; they favour pure‑Python utility functions and are good
  examples when adding new shared logic.

* I/O wrappers are under `src/simpandas/readers` and `src/simpandas/writters`.
  They all follow the same pattern of calling the underlying pandas function and
  then constructing a `SimDataFrame` with the extracted `units` metadata.

* Tests mirror the implementation directories.  The repository contains both
  `test/*.py` and `test/common/*.py`.  Many of the top‑level tests are trivial
  smoke checks; `common` tests exercise the utility functions.

* There are a few `*_copy.py` modules (e.g. `basics_copy.py`) which are
  snapshots/experiments; they are not imported anywhere and can generally be
  ignored when editing logic unless you know you’re working on the “next” version.

* A notebook (`simpandas_demo.ipynb`) contains interactive examples that can be
  run to see typical usage.

---
## ⚙️ Developer Workflows

1. **Install / build**
   ```powershell
   cd d:\git\simpandas
   pip install -e .           # editable install
   python -m build             # if you need a wheel/sdist (requires build package)
   ```

2. **Run tests** – there’s no test runner configured, so use pytest directly:
   ```powershell
   python -m pytest            # runs everything under test/
   python -m pytest test/common/test_stringformat.py  # run a single file
   python test\manual_testing.py   # quick interactive script
   ```
   The CI configuration isn’t present; tests are very lightweight (mostly
   `assert` statements).

3. **Bumping versions**
   * The project version is defined in `pyproject.toml`.
   * Individual modules also declare `__version__` and `__release__`.  When
     changing behaviour update both constants (and keep them in sync with
     the top‑level version for releases).
   * No changelog is tracked, so commit messages usually stand in for history.

4. **Publishing**
   Releases are pushed to PyPI using the usual `twine upload dist/*` after
   building.  The project’s README explains the PyPI package name.

5. **Common edits**
   * Add new methods to `SimDataFrame`/`SimSeries` by mimicking existing ones
     (e.g. `head`, `concat`, arithmetic helpers).  Always return
     `self._class(..., **self.params_)` so metadata flows through operations.
   * If a new feature needs cross‑cutting logic, consider adding it to
     `simpandas/common` and writing a test in `test/common`.
   * When you add an attribute that should survive pandas operations, add it
     to the `_metadata` list near the top of the subclass.
   * Unit conversions rely on `unyts`.  Use `_convertible`, `_converter` and
     operations imported from `unyts.operations`.  See how indexers call them
     for examples of type-checking and fallback behaviour.

---
## 🛠 Project‑Specific Conventions

* **Metadata passing** – every data object has a `params_` property; it
  collects `name`, `units`, `index_units`, `name_separator`, `intersection_character`,
  `verbose`, `auto_append`, `operate_per_name`, `transposed`, `reverse`,
  `meta`, `source_path` and `return_singles`.  Constructors accept these
  values and downstream methods re‑use `params_` when constructing new objects.

* **Unit handling** – functions and operators frequently accept either a
  string, dict, int or tuple `(value, unit)`.  When setting values via
  `.loc`/`.iloc` the custom indexers convert units and may assign new ones if
  the location is empty.  Study `_SimLocIndexer.__setitem__` for the full
  pattern.

* **Naming helpers** – column names are often manipulated using the
  `name_separator` and `intersection_character` parameters (defaults are `:`
  and `&`).  There are helpers in `common/renamer.py` and `stringformat.py`
  used throughout the codebase; use them rather than re‑implementing logic.

* **Logging** – modules call `logging.basicConfig(level=logging.INFO)` at the
  top; methods often use `logging.info` for user‑visible configuration changes.
  Verbosity is controlled by the `verbose` attribute.

* **Excel I/O** – wrappers accept additional arguments such as `units`,
  `indexUnits`, `nameSeparator`, etc.  If `units` is an integer it is treated
  as the row number containing units.  The output is always a `SimDataFrame`.

* **Tests** – there is no uniform style (some tests use `try/except`).  Always
  import the minimal symbols you need (e.g. `from simpandas import SimDataFrame`).
  For new utilities, add tests alongside existing ones in the appropriate
  `test/common` file.

---
## 🔄 Integration & Dependencies

* **unyts** – the only external library with non‑pandas logic.  All unit
  conversion and arithmetic is mediated through its API.  The package is
  pinned to `>=0.5.25` in `pyproject.toml`.
* **pandas / numpy / matplotlib / seaborn** – core data stack, no special
  versions indicated.
* **openpyxl / xlsxwriter** – required for Excel readers/writers.

Note that none of the source files import anything outside of `simpandas` and
standard libraries except the above packages.

---
## 📝 When You’re Unsure

* Look at the implementation of the nearest existing method.  The repo is
  small, and most logic is duplicated between `frame.py` and `series.py`.
* Use the notebook (`simpandas_demo.ipynb`) or `test/manual_testing.py` to try
  code interactively; both build `SimDataFrame`/`SimSeries` directly.
* Treat `*_copy.py` files as historical snapshots; they are not actively used.

---

> _Let me know if any important piece of project-specific knowledge is missing
> or if some section isn’t clear. I can iterate on this document._
