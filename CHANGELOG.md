# Changelog

All notable changes to the simpandas project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-04-21

### Added
- `ColumnUnits` class (`simpandas.common.units`): an ordered, duplicate-key-safe
  `Mapping` that stores column units positionally.  `SimDataFrame.units` now
  returns `ColumnUnits` instead of `dict` or `list`.
- `SimDataFrame.deduplicate_columns(inplace=False)`: rename duplicate column
  names to make them unique (`BHP`, `BHP_1`, `BHP_2`, …) with a warning.
  Called automatically by the JSON, PRODML, and WITSML writers.
- `simpandas.common.renamer.deduplicate_column_names(names)`: pure-function
  helper for the above.

### Fixed
- `write_csv` / `to_csv`: unit row now uses `ColumnUnits.to_list()` positionally
  so frames with duplicate column names retain all per-column units.
- `write_hdf5` / `to_hdf5`: same positional fix.
- `write_summary` / `to_summary`: same positional fix.
- `write_json` / `to_json`, `write_prodml` / `to_prodml`, `write_witsml` /
  `to_witsml`: duplicate column names are now deduplicated (with a warning)
  before the dict-based unit metadata is serialised, so no unit is silently lost.

### Changed
- All writer methods (`to_csv`, `to_json`, `to_hdf5`, `to_summary`,
  `to_parquet`, `to_prodml`, `to_witsml`, `to_resqml`) moved from
  `SimDataFrame` / `SimSeries` into the shared `SimBasics` mixin.
  They are now available on **both** `SimDataFrame` and `SimSeries`
  without duplication.

### Fixed
- `read_vdb`: well names were incorrectly returned as `'1.0.0'` (the VDB
  format-version string from the file header).  The `_parse_welist` function
  now uses a proper byte-aligned sentinel scanner (`_extract_8char_names`)
  that filters out header tokens, dot-containing version strings, and
  `#`-prefixed ordinal IDs.
- `read_vdb`: fallback entity names changed from `ENTITY_0` / `ENTITY_1`
  (0-indexed) to `WELL_1` / `WELL_2` (1-indexed, prefix based on table type
  — `WELL_N` for well tables, `REGION_N` for region tables).

## [0.90.0] - 2026-04-20

### Added
- `write_summary()` and `to_summary()` now accept a `dimens`
  parameter (`[nx, ny, nz]`) for correct round-trip of B-prefix block vectors.
- `read_summary()` now stores `dimens` and `startdat` in `sdf.meta` so the
  writer can recover them automatically without the caller re-specifying them.

### Fixed
- `read_summary`: region/aquifer (`R`/`A`-prefix) vectors were silently dropped
  due to incorrect ordering of the sentinel-WGNAME guard — now fixed.
- `read_summary`: block (`B`-prefix) vectors (`BPR:1,2,3`, …) were similarly
  dropped — now fixed.
- `write_summary`: writing a `SimDataFrame` with a `DatetimeIndex` (named
  `DATE`) now works correctly; the writer converts it back to float TIME days
  and derives `startdat` from the first timestamp.
- `write_summary`: `sdf.units` stored as a positional list is now handled
  (previously only dicts were supported).
- `write_summary`: when `dimens=None`, the writer consults `sdf.meta['dimens']`
  before falling back to column-name inference.
- `write_summary`: when `startdat=None`, the writer consults
  `sdf.meta['startdat']` before falling back to `[1, 1, 2000]`.

## [Unreleased] - 2026-06-14

### Added
- Added `readers/parquet.py` with `read_parquet()` and `writers/parquet.py`
  with `write_parquet()` — Parquet I/O with units stored as custom schema
  metadata (requires `pyarrow`).
- Added `to_parquet()` method (available on both `SimDataFrame` and `SimSeries` via `SimBasics`).
- Added `readers/prodml.py` with `read_prodml()` — reads PRODML v1/v2 XML
  (production volumes, time series, well tests) with namespace auto-detection.
- Added `writers/prodml.py` with `write_prodml()` — writes PRODML v2 XML in
  timeseries or volumes style.
- Added `to_prodml()` method (available on both `SimDataFrame` and `SimSeries` via `SimBasics`).
- Added `readers/witsml.py` with `read_witsml()` — reads WITSML v1.4.1.1/v2
  XML (log curves, trajectories, mudlogs).
- Added `writers/witsml.py` with `write_witsml()` — writes WITSML v1.4.1.1
  log XML.
- Added `to_witsml()` method (available on both `SimDataFrame` and `SimSeries` via `SimBasics`).
- Added `readers/resqml.py` with `read_resqml()` — reads RESQML v2 EPC
  packages (ZIP + HDF5) for continuous/discrete property time series.
- Added `writers/resqml.py` with `write_resqml()` — writes RESQML EPC
  packages with HDF5 data and XML metadata.
- Added `to_resqml()` method (available on both `SimDataFrame` and `SimSeries` via `SimBasics`).
- `read_parquet`, `read_prodml`, `read_witsml`, `read_resqml` exported from
  top-level package.
- Added tests: `test/readers/test_parquet.py`, `test/readers/test_prodml.py`,
  `test/readers/test_witsml.py`, `test/readers/test_resqml.py`.

## [Unreleased] - 2026-04-18

### Added
- Added `writers/csv.py` with `write_csv()` — writes CSV with an embedded
  units row compatible with `read_csv(path, units=0)`.
- Added `writers/json.py` with `write_json()` — writes JSON with a
  `{data, units, index_units}` envelope compatible with `read_json()`.
- `write_csv` and `write_json` are now exported from the top-level package.
- `SimDataFrame.to_csv()` and `SimSeries.to_csv()` now delegate to
  `write_csv` and produce units-aware output by default.
- `SimDataFrame.to_json()` and `SimSeries.to_json()` now delegate to
  `write_json` and include `index_units` in the JSON envelope.
- Added `readers/h5.py` with `read_hdf5()` and `writers/h5.py` with
  `write_hdf5()` for HDF5 I/O with units metadata (requires `h5py`).
- Added `to_hdf5()` method (available on both `SimDataFrame` and `SimSeries` via `SimBasics`).
- Added `readers/summary.py` with `read_summary()` for reading Eclipse binary
  summary (.SMSPEC + .UNSMRY) files.
- Added `writers/summary.py` with `write_summary()` for writing Eclipse binary
  summary files.
- Added `to_summary()` method (available on both `SimDataFrame` and `SimSeries` via `SimBasics`).
- `read_hdf5` and `read_summary` exported from top-level package.
- Added `readers/vdb.py` with `read_vdb()` for reading VIP / Nexus `.vdb`
  plot data (NT32 binary format). Supports well and region tables, auto-
  detects case hierarchy, extracts units from VARDESC blocks.
- `read_vdb` exported from top-level package.
- Added VDB reader tests in `test/readers/test_vdb.py` (21 tests: 13
  synthetic + 8 with real sample data).
- Added round-trip tests in `test/writers/test_csv_json.py`,
  `test/readers/test_h5.py`, and `test/readers/test_summary.py`.

### Fixed
- `read_csv`: when `units` is an integer and `index_col` is also given,
  the reader now correctly extracts the index column's units as
  `index_units` instead of losing them.
- `read_json`: the reader now extracts `index_units` from the SimPandas
  JSON envelope.

## [Unreleased] - 2026-04-12

### Added
- Added wrappers in `src/simpandas/basics.py` for:
  - `ffill`, `bfill`, `pct_change`, `asfreq`
  - `combine_first`, `isin`, `compare`, `swaplevel`
  - `update`, `align`
- Added `_SimResampleProxy` in `src/simpandas/frame.py`.
- Added `resample()` wrappers to `SimDataFrame` and `SimSeries`.
- Added `between(...)` wrapper in `src/simpandas/series.py`.
- Added wrapper regression tests in `test/test_missing_wrappers.py`.

### Fixed
- Fixed `common.filters.key_to_string(...)` integration so filter parsing no
  longer fails with undefined operation variables.
- Fixed SimDataFrame and SimSeries filter flows to consistently return wrapped
  Sim objects and handle index-condition parsing more robustly.

### Documentation
- Updated user and developer documentation to include the expanded wrapper
  coverage and resample proxy architecture.

## [0.84.0] - 2026-03-03

### Breaking Changes
- **Renamed folder:** `simpandas.writters` → `simpandas.writers` to fix spelling error
  - Backward compatibility maintained via deprecation shim at `writters.py`
  - Users should update imports: `from simpandas.writers import ...` (new) instead of `from simpandas.writters import ...` (deprecated)

### Added
- **Pandas 2.x compatibility layer** (`src/simpandas/common/compat.py`)
  - Added `concat_compat()` function to replace deprecated `.append()` method
  - Supports both pandas 1.x (≥1.3.0) and 2.x (<3.0.0)
  - Added `PANDAS_GE_20` flag for version detection
  - Added `packaging` dependency for version parsing
- **Comprehensive test suite** (~100 new tests)
  - `test/test_errors.py`: Tests for custom exception classes
  - `test/test_index.py`: Tests for SimIndex MultiIndex functionality
  - `test/test_basics.py`: Tests for SimBasics mixin methods
  - `test/readers/test_xlsx.py`: Tests for Excel reading functionality
  - `test/writers/test_xlsx.py`: Tests for Excel writing functionality
  - `test/writers/test_schedule.py`: Tests for schedule output
  - `test/common/test_internal_processes.py`: Tests for internal helpers
- **Backward compatibility shim** (`src/simpandas/writters.py`)
  - Re-exports all functions from new `writers` module
  - Prevents breaking changes for existing code

### Fixed
- **Critical bug fixes:**
  - Fixed syntax error in `basics.py` line 2424 (smart quote encoding issues)
  - Fixed typo: `__release` → `__release__` in `errors.py`
  - Fixed typo: `.lowrt()` → `.lower()` in `readers/xlsx.py`
  - Fixed typo: "extentions" → "extensions" in `pyproject.toml`
  - Fixed missing import `clean_axis` in `common/filters.py`
  - Fixed `zeros()` function call with missing `axis` argument in `common/filters.py`
  - Fixed eager `unyts` import on top-level module import in `simpandas`; now lazy-loaded via `src/simpandas/common/lazy_unyts.py` and only imports `unyts` on conversion usage
- **Deprecated pandas methods:**
  - Replaced 8 instances of deprecated `.append()` with `concat_compat()`:
    - 5 replacements in `src/simpandas/basics.py`
    - 3 replacements in `src/simpandas/writers/schedule.py`
  - All code now compatible with pandas ≥2.0.0
- **Dependency corrections:**
  - Removed invalid "datetime" dependency (stdlib module)
  - Added pandas version constraint: `>=1.3.0,<3.0.0`
  - Added `packaging` dependency for version detection

### Changed
- **Version standardization:**
  - Updated all module `__version__` to `0.84.0`
  - Updated all module `__release__` dates
  - Synchronized versions across: `__init__.py`, `frame.py`, `series.py`, `basics.py`
- **Documentation updates:**
  - Updated `.github/copilot-instructions.md` to reference correct folder names
  - Added CHANGELOG.md (this file)
  - Updated README.md with compatibility notes

### Technical Details
- **Version:** 0.83.22 → 0.84.0
- **Python compatibility:** ≥3.7 (recommend ≥3.8)
- **Pandas compatibility:** ≥1.3.0, <3.0.0
- **Dependencies updated:** Added `packaging` for version detection

### Migration Guide

#### Updating imports (non-breaking, but recommended):
```python
# Old (still works, but deprecated):
from simpandas.writters import write_excel

# New (recommended):
from simpandas.writers import write_excel
```

#### No action required for:
- Pandas 2.x users: `.append()` is now handled via `concat_compat()`
- Pandas 1.x users: Code remains fully compatible
- Existing unit operations: No API changes

---

## [0.83.22] - 2022-11-16

### Previous Release
- Last stable release before major quality improvements
- Various bug fixes and feature additions (see git history)

---

## Version Numbering

This project uses semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR:** Breaking API changes
- **MINOR:** New features, backward compatible
- **PATCH:** Bug fixes, backward compatible

---

## Contributing

See the main README.md for contribution guidelines.

---

## Links

- **PyPI:** https://pypi.org/project/simpandas/
- **Repository:** (Add repository link)
- **Issues:** (Add issues link)
