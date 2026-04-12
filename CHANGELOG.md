# Changelog

All notable changes to the simpandas project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
