# Changelog

All notable changes to the simpandas project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.90.5] - 2026-04-21

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

---

## [0.90.0] - 2026-04-20

### Added
- All writer methods (`to_csv`, `to_json`, `to_hdf5`, `to_summary`,
  `to_parquet`, `to_prodml`, `to_witsml`, `to_resqml`) consolidated into the
  shared `SimBasics` mixin — available on **both** `SimDataFrame` and
  `SimSeries` without duplication.
- `write_summary()` / `to_summary()` now accept a `dimens` parameter
  (`[nx, ny, nz]`) for correct round-trip of B-prefix block vectors.
- `read_summary()` now stores `dimens` and `startdat` in `sdf.meta` so the
  writer can recover them automatically without the caller re-specifying them.
- `readers/parquet.py` with `read_parquet()` and `writers/parquet.py` with
  `write_parquet()` — Parquet I/O with units stored as custom schema metadata
  (requires `pyarrow`).
- `to_parquet()` method on `SimDataFrame` and `SimSeries`.
- `readers/prodml.py` with `read_prodml()` — reads PRODML v1/v2 XML
  (production volumes, time series, well tests) with namespace auto-detection.
- `writers/prodml.py` with `write_prodml()` — writes PRODML v2 XML in
  timeseries or volumes style.
- `to_prodml()` method on `SimDataFrame` and `SimSeries`.
- `readers/witsml.py` with `read_witsml()` — reads WITSML v1.4.1.1/v2 XML
  (log curves, trajectories, mudlogs).
- `writers/witsml.py` with `write_witsml()` — writes WITSML v1.4.1.1 log XML.
- `to_witsml()` method on `SimDataFrame` and `SimSeries`.
- `readers/resqml.py` with `read_resqml()` — reads RESQML v2 EPC packages
  (ZIP + HDF5) for continuous/discrete property time series.
- `writers/resqml.py` with `write_resqml()` — writes RESQML EPC packages with
  HDF5 data and XML metadata.
- `to_resqml()` method on `SimDataFrame` and `SimSeries`.
- `read_parquet`, `read_prodml`, `read_witsml`, `read_resqml` exported from
  the top-level package.
- `writers/csv.py` with `write_csv()` — writes CSV with an embedded units row
  compatible with `read_csv(path, units=0)`.
- `writers/json.py` with `write_json()` — writes JSON with a
  `{data, units, index_units}` envelope compatible with `read_json()`.
- `write_csv` and `write_json` exported from the top-level package.
- `SimDataFrame.to_csv()` and `SimSeries.to_csv()` delegate to `write_csv`
  and produce units-aware output by default.
- `SimDataFrame.to_json()` and `SimSeries.to_json()` delegate to `write_json`
  and include `index_units` in the JSON envelope.
- `readers/h5.py` with `read_hdf5()` and `writers/h5.py` with `write_hdf5()`
  for HDF5 I/O with units metadata (requires `h5py`).
- `to_hdf5()` method on `SimDataFrame` and `SimSeries`.
- `readers/summary.py` with `read_summary()` for reading Eclipse binary
  summary (`.SMSPEC` + `.UNSMRY`) files.
- `writers/summary.py` with `write_summary()` for writing Eclipse binary
  summary files.
- `to_summary()` method on `SimDataFrame` and `SimSeries`.
- `read_hdf5` and `read_summary` exported from the top-level package.
- `readers/vdb.py` with `read_vdb()` for reading VIP / Nexus `.vdb` plot data
  (NT32 binary format).  Supports well and region tables, auto-detects case
  hierarchy, and extracts units from VARDESC blocks.
- `read_vdb` exported from the top-level package.
- Wrappers in `SimBasics` for: `ffill`, `bfill`, `pct_change`, `asfreq`,
  `combine_first`, `isin`, `compare`, `swaplevel`, `update`, `align`.
- `_SimResampleProxy` and `resample()` wrappers on `SimDataFrame` and
  `SimSeries`.
- `SimSeries.between(...)` wrapper.
- Tests: `test/readers/test_vdb.py` (21 tests), `test/readers/test_parquet.py`,
  `test/readers/test_prodml.py`, `test/readers/test_witsml.py`,
  `test/readers/test_resqml.py`, `test/writers/test_csv_json.py`,
  `test/readers/test_h5.py`, `test/readers/test_summary.py`,
  `test/test_missing_wrappers.py`.

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
- `read_vdb`: well names were incorrectly returned as `'1.0.0'` (the VDB
  format-version string from the file header).  The `_parse_welist` function
  now uses a proper byte-aligned sentinel scanner (`_extract_8char_names`)
  that filters out header tokens, dot-containing version strings, and
  `#`-prefixed ordinal IDs.
- `read_vdb`: fallback entity names changed from `ENTITY_0` / `ENTITY_1`
  (0-indexed) to `WELL_1` / `WELL_2` (1-indexed, prefix based on table type:
  `WELL_N` for well tables, `REGION_N` for region tables).
- `read_csv`: when `units` is an integer and `index_col` is also given, the
  reader now correctly extracts the index column's units as `index_units`.
- `read_json`: the reader now extracts `index_units` from the SimPandas JSON
  envelope.
- `common.filters.key_to_string(...)` integration: filter parsing no longer
  fails with undefined operation variables.
- `SimDataFrame` and `SimSeries` filter flows now consistently return wrapped
  Sim objects and handle index-condition parsing more robustly.

---

## [0.84.0] - 2026-03-03

### Breaking Changes
- **Renamed folder:** `simpandas.writters` → `simpandas.writers` to fix spelling error.
  Backward compatibility maintained via deprecation shim at `writters.py`.
  Users should update imports to `from simpandas.writers import ...`.

### Added
- **Pandas 2.x compatibility layer** (`src/simpandas/common/compat.py`)
  - `concat_compat()` replaces deprecated `.append()`; supports pandas 1.x and 2.x.
  - `PANDAS_GE_20` flag for version detection.
  - `packaging` dependency for version parsing.
- **Comprehensive test suite** (~100 new tests):
  `test/test_errors.py`, `test/test_index.py`, `test/test_basics.py`,
  `test/readers/test_xlsx.py`, `test/writers/test_xlsx.py`,
  `test/writers/test_schedule.py`, `test/common/test_internal_processes.py`.
- **Backward compatibility shim** (`src/simpandas/writters.py`) — re-exports
  all functions from the new `writers` module.

### Changed
- All module `__version__` values updated to `0.84.0`.
- Replaced 8 deprecated `.append()` calls with `concat_compat()` (5 in
  `basics.py`, 3 in `writers/schedule.py`).

### Fixed
- Syntax error in `basics.py` (smart quote encoding).
- Typo: `__release` → `__release__` in `errors.py`.
- Typo: `.lowrt()` → `.lower()` in `readers/xlsx.py`.
- Missing import `clean_axis` in `common/filters.py`.
- `zeros()` called with missing `axis` argument in `common/filters.py`.
- Eager `unyts` import replaced with lazy-loading via `common/lazy_unyts.py`.
- Removed invalid `"datetime"` stdlib entry from `dependencies`.
- Added pandas version constraint `>=1.3.0,<3.0.0`; added `packaging`.

---

## [0.83.22] - 2022-11-16

### Previous Release
- Last stable release before major quality improvements.
- Various bug fixes and feature additions (see git history).

---

## Version Numbering

This project uses semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR:** Breaking API changes
- **MINOR:** New features, backward compatible
- **PATCH:** Bug fixes, backward compatible

---

## Links

- **PyPI:** https://pypi.org/project/simpandas/
- **Repository:** https://github.com/ayaranitram/simpandas
- **Issues:** https://github.com/ayaranitram/simpandas/issues
