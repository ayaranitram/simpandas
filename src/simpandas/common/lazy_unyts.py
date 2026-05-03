# -*- coding: utf-8 -*-
"""
Lazy loader for unyts package.

This module exposes a drop-in API for symbols used by simpandas while
avoiding eager import of unyts during simpandas import.
"""

__version__ = '0.1.0'
__release__ = 20260503

from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def _load_unyts():
    import unyts
    from unyts.converter import convertible, convert_for_SimPandas
    from unyts.operations import unit_power, unit_addition, unit_product, unit_division, unit_inverse, unit_base, unit_base_power
    from unyts.dictionaries import unitless_names
    from unyts.helpers.common_classes import number
    from unyts import units as _units, Unit as _Unit, is_Unit as _is_Unit

    return {
        'unyts': unyts,
        'convertible': convertible,
        'convert_for_SimPandas': convert_for_SimPandas,
        'unit_power': unit_power,
        'unit_addition': unit_addition,
        'unit_product': unit_product,
        'unit_division': unit_division,
        'unit_inverse': unit_inverse,
        'unit_base': unit_base,
        'unit_base_power': unit_base_power,
        'unitless_names': unitless_names,
        'number': number,
        'units': _units,
        'Unit': _Unit,
        'is_Unit': _is_Unit,
    }


class _LazyFunc:
    def __init__(self, key):
        self.__key = key

    def __call__(self, *args, **kwargs):
        return _load_unyts()[self.__key](*args, **kwargs)

    def __getattr__(self, item):
        return getattr(_load_unyts()[self.__key], item)


class _LazyCollection:
    def __init__(self, key):
        self.__key = key

    def _value(self):
        return _load_unyts()[self.__key]

    def __contains__(self, item):
        return item in self._value()

    def __iter__(self):
        return iter(self._value())

    def __len__(self):
        return len(self._value())

    def __getitem__(self, item):
        return self._value()[item]

    def __repr__(self):
        return repr(self._value())


class _LazyUnitMeta(type):
    def __instancecheck__(self, instance):
        return isinstance(instance, _load_unyts()['Unit'])

    def __getattr__(self, item):
        return getattr(_load_unyts()['Unit'], item)


class Unit(metaclass=_LazyUnitMeta):
    def __new__(cls, *args, **kwargs):
        return _load_unyts()['Unit'](*args, **kwargs)

    def __repr__(self):
        return repr(_load_unyts()['Unit'])


def is_Unit(value):
    return _load_unyts()['is_Unit'](value)


def units(*args, **kwargs):
    return _load_unyts()['units'](*args, **kwargs)


def convertible(*args, **kwargs):
    """Check unit convertibility with a safe warmup retry for first-run graphs."""
    unyts = _load_unyts()
    unyts_convertible = unyts['convertible']
    unyts_convert_for_sp = unyts.get('convert_for_SimPandas')

    try:
        result = bool(unyts_convertible(*args, **kwargs))
    except Exception as exc:
        logger.debug("lazy_unyts.convertible initial check failed: %s", exc, exc_info=True)
        result = False

    if result:
        return True

    # Edge case: first call can return False while unit network is still warming up.
    # Attempt a single conversion path to force cache warming, then re-evaluate convertibility.
    if len(args) < 2 or unyts_convert_for_sp is None:
        return False

    from_unit = args[0]
    to_unit = args[1]

    try:
        unyts_convert_for_sp(1, from_unit, to_unit)
    except Exception as exc:
        logger.debug("lazy_unyts.convertible warmup conversion failed: %s", exc, exc_info=True)

    try:
        return bool(unyts_convertible(*args, **kwargs))
    except Exception as exc:
        logger.debug("lazy_unyts.convertible retry check failed: %s", exc, exc_info=True)
        return False


def convert_for_SimPandas(*args, **kwargs):
    return _load_unyts()['convert_for_SimPandas'](*args, **kwargs)


def unit_power(*args, **kwargs):
    return _load_unyts()['unit_power'](*args, **kwargs)


def unit_addition(*args, **kwargs):
    return _load_unyts()['unit_addition'](*args, **kwargs)


def unit_product(*args, **kwargs):
    return _load_unyts()['unit_product'](*args, **kwargs)


def unit_division(*args, **kwargs):
    return _load_unyts()['unit_division'](*args, **kwargs)


def unit_inverse(*args, **kwargs):
    return _load_unyts()['unit_inverse'](*args, **kwargs)


def unit_base(*args, **kwargs):
    return _load_unyts()['unit_base'](*args, **kwargs)


def unit_base_power(*args, **kwargs):
    return _load_unyts()['unit_base_power'](*args, **kwargs)


unitless_names = _LazyCollection('unitless_names')
number = _LazyCollection('number')
