# -*- coding: utf-8 -*-
"""
Schedule reader for Eclipse DATA files.
"""

__version__ = '0.1.0'
__release__ = 20260425
__all__ = ['read_schedule']

from simpandas.frame import SimDataFrame


def _read_runspec_units(filepath: str, encoding: str = 'cp1252') -> str:
    """Return the unit system declared in the RUNSPEC section, if any."""
    def _clean(line: str) -> str:
        stripped = line.split('--', 1)[0]
        return stripped.strip()

    with open(filepath, 'r', encoding=encoding) as f:
        lines = [ _clean(line) for line in f ]

    start = None
    end = None
    for idx, line in enumerate(lines):
        if line.upper().startswith('RUNSPEC'):
            start = idx + 1
            break
    if start is None:
        return None

    for idx in range(start, len(lines)):
        if lines[idx].upper().startswith('GRID'):
            end = idx
            break
    if end is None:
        end = len(lines)

    section = lines[start:end]
    tokens = []
    for line in section:
        if not line:
            continue
        tokens.extend([tok.strip("'\"/ ") for tok in line.replace('/', ' ').split()])

    tokens = [tok.upper() for tok in tokens if tok]
    if 'FIELD' in tokens:
        return 'FIELD'
    if 'METRIC' in tokens:
        return 'METRIC'
    return None


def _keyword_units(system: str) -> dict:
    system = system.upper() if system is not None else None
    if system == 'METRIC':
        rate_unit = 'SM3/DAY'
        pressure_unit = 'BARSA'
    else:
        rate_unit = 'STB/DAY'
        pressure_unit = 'PSIA'

    return {
        'OIL rate': rate_unit,
        'WATER rate': rate_unit,
        'GAS rate': 'MSCF/DAY' if system != 'METRIC' else 'SM3/DAY',
        'LIQUID rate': rate_unit,
        'RESERVOIR fluid rate': rate_unit,
        'SURFACE fluid rate': rate_unit,
        'injection rate': rate_unit,
        'wet gas rate': 'MSCF/DAY' if system != 'METRIC' else 'SM3/DAY',
        'NGL rate': rate_unit,
        'BHP': pressure_unit,
        'BHP limit': pressure_unit,
        'THP': pressure_unit,
        'THP limit': pressure_unit,
    }


def _populate_units(data, system):
    if system is None:
        return None

    units_map = _keyword_units(system)
    units = {}
    for col in data.columns:
        if col in units_map:
            units[col] = units_map[col]
        else:
            lower = col.lower()
            if 'rate' in lower or 'fluid' in lower:
                if 'gas' in lower:
                    units[col] = 'MSCF/DAY' if system != 'METRIC' else 'SM3/DAY'
                else:
                    units[col] = 'SM3/DAY' if system == 'METRIC' else 'STB/DAY'
            elif 'bhp' in lower or 'thp' in lower:
                units[col] = 'BARSA' if system == 'METRIC' else 'PSIA'
    return units


def read_schedule(filepath,
                  encoding: str = 'cp1252',
                  units: str = None,
                  verbose: bool = False,
                  *args, **kwargs):
    """Read schedule keywords from an Eclipse .DATA file into a SimDataFrame."""
    import pandas as pd
    try:
        from schedule_reader.data_reader import read_data
        from schedule_reader.wcon import extract_wconhist, extract_wconinjh, extract_wconprod, extract_wconinje
    except ImportError as exc:
        raise ImportError(
            'schedule_reader is required to use read_schedule(). '
            'Install it with `pip install schedule_reader`.') from exc

    system = None
    if units is not None:
        units = str(units).upper()
        if units not in {'FIELD', 'METRIC'}:
            raise ValueError("units must be 'FIELD', 'METRIC', or None")
        system = units
    else:
        try:
            system = _read_runspec_units(filepath, encoding=encoding)
        except FileNotFoundError:
            raise

    schedule_dict = read_data(filepath, encoding=encoding, verbose=verbose, *args, **kwargs)

    tables = []
    for keyword, extractor in [
        ('WCONHIST', extract_wconhist),
        ('WCONINJH', extract_wconinjh),
        ('WCONPROD', extract_wconprod),
        ('WCONINJE', extract_wconinje),
    ]:
        table = extractor(schedule_dict)
        if table is not None and len(table) > 0:
            table = table.copy()
            table['keyword'] = keyword
            tables.append(table)

    if tables:
        data = pd.concat(tables, ignore_index=True, sort=False)
    else:
        data = pd.DataFrame()

    if system is not None and not data.empty:
        units_dict = _populate_units(data, system)
    else:
        units_dict = None

    sim_kwargs = {}
    if units_dict is not None:
        sim_kwargs['units'] = units_dict
    sim_kwargs['verbose'] = verbose

    if 'nameSeparator' in kwargs:
        sim_kwargs['name_separator'] = kwargs.pop('nameSeparator')
    if 'intersectionCharacter' in kwargs:
        sim_kwargs['intersection_character'] = kwargs.pop('intersectionCharacter')
    if 'autoAppend' in kwargs:
        sim_kwargs['auto_append'] = kwargs.pop('autoAppend')
    if 'operatePerName' in kwargs:
        sim_kwargs['operate_per_name'] = kwargs.pop('operatePerName')

    return SimDataFrame(data=data, **sim_kwargs)
