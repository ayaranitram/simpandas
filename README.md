# `simpandas`
A couple of Pandas DataFrame and Series subclasses, extended to work with units and to deal with column names following the style of eclipse simulator outputs.

This package is under development and is regularly updated. Back-compatibility is intended to be maintained when possible.

**Version:** 0.93.0 | **Python:** ≥3.7 (≥3.8 recommended) | **Pandas:** 1.3.0 - 3.x

## What Contains This Package
It is powered by other packages, like <a href="https://numpy.org/">**NumPy**</a>, <a href="https://seaborn.pydata.org/">**seaborn**</a> and <a href="https://github.com/ayaranitram/unyts">**unyts**</a> and further own methods, to be able to deal with tables of quantities and facilitate common manipulations of time-dependent data.

### Key Features
- **Unit-aware DataFrames and Series:** Automatic unit tracking and conversion using unyts
- **Pandas 1.3-3.x compatible:** Compatibility wrappers avoid pandas 2.x/3.x deprecation paths while retaining support for pandas 1.3+
- **Enhanced I/O:** Read/write Excel, CSV, and JSON files with unit metadata preservation
- **Expanded pandas wrapper coverage:** `ffill`, `bfill`, `pct_change`, `asfreq`, `combine_first`, `isin`, `compare`, `swaplevel`, `align`, `update`, `resample`, and `between` now return Sim types where applicable
- **Time-series utilities:** Built-in methods for daily, monthly, yearly aggregations
- **Eclipse-style simulator support:** Handle column naming conventions from reservoir simulators
- **Eclipse/OPM summary round-trip:** Read/write `.SMSPEC` + `.UNSMRY` files with `to_summary` / `read_summary` and optional `OPM` or `ECLIPSE` naming style
- **Schedule import:** Read `WCONHIST`, `WCONINJH`, `WCONPROD` and `WCONINJE` Eclipse schedule records with inferred FIELD or METRIC units; each row carries the date set by `START`/`DATES`/`TIME`/`TSTEP`
- **CMG SR3 support:** Read/write CMG `.sr3` files (IMEX, GEM, STARS) with `read_sr3` / `write_sr3` (requires `h5py`)

## Installation

To install from <a href="https://pypi.org/search/?q=simpandas">pypi.org</a>:  
```bash
pip install simpandas
```

To upgrade to the latest version:
```bash
pip install --upgrade simpandas
```

## Requirements
- **pandas** ≥1.3.0, <4.0.0
- **numpy**
- **matplotlib**
- **seaborn**
- **unyts** ≥1.0.0
- **schedule_reader** ≥0.7.15 (for Eclipse schedule imports; use the latest version for the strict Eclipse date parsing)
- **h5py** (optional, for CMG SR3 files)
- **openpyxl** (for Excel support)
- **xlsxwriter** (for Excel writing)
- **packaging** (for version detection)

## Quick Start

```python
from simpandas import SimDataFrame, SimSeries, read_csv, read_json

# Create a DataFrame with units
df = SimDataFrame(
    {'velocity': [1, 2, 3], 'temperature': [25, 30, 35]},
    units={'velocity': 'm/s', 'temperature': 'degC'}
)

# Units are preserved through operations
result = df * 2
print(df.get_units())  # Access unit information

# Read CSV/JSON with units
df = read_csv('data.csv', units=0)  # units in row 0 after the header
df = read_json('data.json')         # restores units from SimPandas JSON
```

## Compatibility Notes

### Pandas Compatibility
Version 0.93.0 supports pandas 1.3.0 through the 3.x series. Compatibility wrappers avoid deprecated pandas `copy` arguments where pandas Copy-on-Write supersedes them. `GroupBy.apply()` excludes grouping columns on pandas 2.2+ to match pandas' forward behavior, while retaining the legacy call signature on older supported versions.

### Selection Semantics
With Eclipse-style column names, a string can select a semantic column group. For example, `sdf['WOPR']` selects columns such as `WOPR:WELL-1` and `WOPR:WELL-2` in their original column order. Exact column names always take precedence; strings that do not resolve to a column or name pattern can resolve to date-like index labels.

### Python Version
- **Minimum:** Python 3.7
- **Recommended:** Python 3.8 or higher

### Breaking Changes in v0.84.0
The `writters` module has been renamed to `writers` (correcting spelling). For backward compatibility:

```python
# Deprecated (still works with warning):
from simpandas.writters import write_excel

# New (recommended):
from simpandas.writers import write_excel
```

### Maintenance Updates (September 2026)
- Added wrappers for missing pandas methods in `SimBasics` to preserve metadata through more operations.
- Added `_SimResampleProxy` and `resample()` support on both `SimDataFrame` and `SimSeries`.
- Fixed filter parsing infrastructure by wiring `common.filters.key_to_string(...)` correctly from `SimSeries.filter()` and `SimDataFrame.filter()`.
- Added `as_dict()` and `from_dict()` for `SimSeries` with `unyts` instance support.
- Fixed `KeyError` in `__setitem__` when re-assigning columns and preserved existing units.
- Added regression coverage in `test/test_bugfix_dca.py`.
- Resolved ambiguous string selection between name-pattern columns and datetime indexes without pandas indexing warnings.
- Added pandas 3.x compatibility for `replace`, `set_index`, `concat`, `rename`, `align`, `astype`, and `GroupBy.apply()`.
- Updated schedule-reader string normalization for pandas 3.x dtype-selection behavior.

### Release 0.93.0 (October 2026)
- Added `read_sr3` / `write_sr3` for CMG SR3 files, tested with two real examples from [sr3_reader](https://github.com/nikolai-andrianov/sr3_reader) (MIT).
- Fixed `read_schedule`: dates are repeated for every record until the next `DATES`/`TIME`/`TSTEP`, parsed as `DD MMM YYYY [HH:MM:SS.SSSS]`, and rows are returned sorted by date. `WCONPROD` and `WCONINJE` are now read too.

## Documentation

For detailed documentation, examples, and API reference, see:
- **USER_MANUAL.md** - Comprehensive user manual for classes, functions, and modules
- **docs/USER_GUIDE.md** - Shorter quick-start guide
- **DEVELOPER_MANUAL.md** - Internal architecture and contributor-focused technical notes
- **CONTRIBUTING.md** - Contribution workflow and release checklist
- **CHANGELOG.md** - Version history and migration guides
- **WHATS_NEW.md** - Highlights for the current release
- **simpandas_demo.ipynb** - Interactive examples and tutorials
- **test/** - Comprehensive test suite with usage examples


### API At A Glance

```python
from simpandas import (
    SimDataFrame, SimSeries, SimIndex, ColumnUnits, concat,
    read_excel, read_csv, read_json, read_hdf5, read_parquet,
    read_summary, read_sr3, read_schedule, read_vdb,
)
from simpandas.index import SimIndex

from simpandas.writers.xlsx import write_excel
from simpandas.writers.schedule import write_schedule
from simpandas.writers.summary import write_summary
```

## Contributing

Contributions are welcome! Please ensure:
1. Code passes all tests: `pytest test/`
2. Follow existing code style
3. Add tests for new features
4. Update documentation as needed

## Testing

Run the test suite:
```bash
cd simpandas
pytest test/ -v
```

## License

See LICENSE file for details.

## Author

Martín Carlos Araya <martinaraya@gmail.com>

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.
