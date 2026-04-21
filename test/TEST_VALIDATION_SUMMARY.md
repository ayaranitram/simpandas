# simpandas Test Suite – Validation Tests

This document summarizes the validation test coverage added to the project.

---
## Test Files Added/Updated

### Core Module Tests

#### `test/test_frame.py`
- `test_basic_creation()` – verify SimDataFrame instantiation with units
- `test_head_tail()` – row selection methods
- `test_arithmetic()` – add operation with units
- `test_concat()` – DataFrame concatenation preserving units
- `test_loc_set_get()` – `.loc` indexer with unit assignment
- `test_iloc_set_get()` – `.iloc` position-based indexer
- `test_series_conversion()` – extracting columns as SimSeries

#### `test/test_series.py`
- `test_basic_creation()` – SimSeries instantiation
- `test_head_tail()` – row selection
- `test_arithmetic()` – add operation between Series
- `test_to_dataframe()` – convert to pandas DataFrame
- `test_to_simdataframe()` – convert to SimDataFrame
- `test_loc_access()` – label-based indexing
- `test_iloc_access()` – position-based indexing

#### `test/test_indexer.py`
- `test_loc_indexer_basic()` – `.loc` getter
- `test_loc_unit_conversion()` – automatic unit conversions via `.loc`
- `test_loc_new_column_units()` – assigning new columns with units
- `test_iloc_basic()` – `.iloc` getter
- `test_iloc_set()` – `.iloc` setter

#### `test/test_simpandas.py`
- `test_units_preservation()` – units dict passed to constructor
- `test_direct_unit_arithmetic()` – power operations with units
- `test_copy_preserves_units()` – `.copy()` maintains metadata
- `test_describe()` – pandas `.describe()` wrapper

### Common Module Tests

#### `test/common/test_math.py`
- `test_jitter_preserves_shape()` – jitter function shape preservation
- `test_znorm()` – z-score normalization (mean 0, std 1)
- `test_minmaxnorm()` – min-max normalization (0 to 1)

#### `test/common/test_slope.py`
- `test_slope_simple()` – slope against index
- `test_slope_with_xy()` – slope with explicit x, y columns
- `test_slope_window()` – rolling window slope

#### `test/common/test_helpers.py`
- `test_clean_axis()` – axis string/int normalization
- `test_string_new_name()` – column name concatenation
- `test_type_of_frame()` – frame type detection
- `test_main_item_key()` – name separator parsing
- `test_hashable()` – hashability check

#### `test/common/test_merger.py`
- `test_concat_basic()` – basic DataFrame concatenation
- `test_concat_type_error()` – input validation
- `test_merge_units_two()` – merging units dicts
- `test_merge_index_simple()` – index merging
- `test_merge_index_invalid_how()` – invalid merge method validation

#### `test/common/test_filters.py`
- `test_zeros_dataframe()` – zeros detection by axis
- `test_zeros_series()` – Series-specific zero detection

#### `test/common/test_shape.py`
- `test_melt_basic()` – long-format conversion
- `test_pivot_basic()` – wide-format conversion

---
## Running Tests

Run all tests:
```powershell
python -m pytest
```

Run tests in a specific file:
```powershell
python -m pytest test/common/test_math.py
```

Run with verbose output:
```powershell
python -m pytest -v
```

---
## Test Coverage Notes

- **Unit preservation** is tested across creation, arithmetic, copy, and indexing.
- **Indexer behavior** covers both `.loc` and `.iloc` get/set with units.
- **Helper functions** are validated for edge cases (type errors, empty inputs).
- **Arithmetic operations** test unit-aware addition, multiplication, and power.
- **Merging/concatenation** validates unit fusion and index alignment.

---
## Future Enhancements

Consider adding tests for:
- Excel I/O (`readers/xlsx.py`)
- Date handling (`common/daterelated.py`)
- String formatting (`common/stringformat.py`)
- More edge cases (NaN handling, empty frames, large data)
- Performance benchmarks for large datasets
