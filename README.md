# `simpandas`
A couple of Pandas DataFrame and Series subclasses, extended to work with units and to deal with column names following the style of eclipse simulator outputs.

This package is under development and is regularly updated. Back-compatibility is intended to be maintained when possible.

**Version:** 0.84.0 | **Python:** ≥3.7 (≥3.8 recommended) | **Pandas:** 1.3.0 - 2.x

## What Contains This Package
It is powered by other packages, like <a href="https://numpy.org/">**NumPy**</a>, <a href="https://seaborn.pydata.org/">**seaborn**</a> and <a href="https://github.com/ayaranitram/unyts">**unyts**</a> and further own methods, to be able to deal with tables of quantities and facilitate common manipulations of time-dependent data.

### Key Features
- **Unit-aware DataFrames and Series:** Automatic unit tracking and conversion using unyts
- **Pandas 2.x compatible:** Works with both pandas 1.x and 2.x
- **Enhanced I/O:** Read/write Excel, CSV, and JSON files with unit metadata preservation
- **Time-series utilities:** Built-in methods for daily, monthly, yearly aggregations
- **Eclipse simulator support:** Handle column naming conventions from reservoir simulators

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
- **pandas** ≥1.3.0, <3.0.0
- **numpy**
- **matplotlib**
- **seaborn**
- **unyts** ≥0.5.25
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

### Pandas 2.x Support
Version 0.84.0+ is fully compatible with pandas 2.x while maintaining backward compatibility with pandas 1.3.0+. The deprecated `.append()` method has been replaced with `pd.concat()` internally.

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
from simpandas import SimDataFrame, SimSeries, read_excel, read_csv, read_json, concat
from simpandas.index import SimIndex

from simpandas.writers.xlsx import write_excel
from simpandas.writers.schedule import write_schedule
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
