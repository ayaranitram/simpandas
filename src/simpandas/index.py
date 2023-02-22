# -*- coding: utf-8 -*-
"""
Created on Thu Jan 19 21:48:27 2023

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.0.9'
__release__ = 20230222
__all__ = ['SimIndex']

from abc import ABC
import pandas as pd
from unyts.converter import convertible as _convertible, convert_for_SimPandas as _converter


def convert(values, from_units, to_units):
    """
    returns the index converted to the requested units if possible, if not, returns the original values.
    """
    if _convertible(from_units, to_units):
        return SimIndex(data=_converter(values, from_units, to_units, print_conversion_path=False),
                        units=to_units)
    else:
        return SimIndex(data=values,
                        units=from_units)


class SimIndex(pd.MultiIndex, ABC):
    _metadata = ['units']

    def __new__(cls, *args, **kwargs):
        def to_(units):
            return SimIndex(convert(obj.values, obj.units, units))

        def set_units_(units):
            if hasattr(units, 'unit') and type(units.unit) is str:
                units = units.unit
            elif hasattr(units, 'units') and type(units.units) is str:
                units = units.units
            if type(units) is str:
                obj.units = units.split()
            elif type(units) is dict:
                obj.units = units.copy()

        if 'units' in kwargs:
            units = kwargs['units']
            del kwargs['units']
        else:
            units = None
        obj = pd.Index.__new__(cls, *args, **kwargs)
        if (len(args) > 0 and type(args[0]) is pd.MultiIndex) or (
                len(args) > 0 and len(args[0]) > 0 and hasattr(args[0], '__iter__')
                and sum([type(each) is tuple for each in args[0]]) == len(args[0])):
            obj = pd.MultiIndex.from_tuples(args[0])
        obj.units = units
        obj.to = to_
        obj.set_units = set_units_
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.units = getattr(obj, 'units', None)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        results = super().__array_ufunc__(ufunc, method, *inputs, **kwargs)
        results = SimIndex(results, units=self.units)
        return results

    def __array_wrap__(self, out_arr, context=None):
        return super().__array_wrap__(self, out_arr, context)

    def _constructor(self, *args, **kwargs):
        if 'units' in kwargs:
            del kwargs['units']
        return SimIndex(*args, units=self.units, **kwargs)
