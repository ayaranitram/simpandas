# -*- coding: utf-8 -*-
"""
Created on Thu Jan 19 21:48:27 2023

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.0.11'
__release__ = 20260503
__all__ = ['SimIndex']

from abc import ABC
import weakref
import pandas as pd
from .common.lazy_unyts import convertible as _convertible, convert_for_SimPandas as _converter


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
    """
    A unit-aware MultiIndex for simpandas.

    SimIndex extends pandas.MultiIndex to carry units metadata and provide
    unit conversion capabilities. It supports automatic unit conversion
    through the `to()` method and preserves units through indexing operations.

    Parameters
    ----------
    data : array-like, list of arrays, or list of tuples
        Data to construct the index from. Can be:
        - List of arrays for MultiIndex.from_arrays
        - List of tuples for MultiIndex.from_tuples
        - Other array-like data for regular Index
    units : str, optional
        Units associated with the index values.
    names : list of str, optional
        Names for the index levels.

    Attributes
    ----------
    units : str
        Units of the index values.

    Methods
    -------
    to(units) : SimIndex
        Convert index to specified units.
    set_units(units) : None
        Set units for the index.

    See Also
    --------
    pandas.MultiIndex : Base pandas MultiIndex class.

    Examples
    --------
    >>> import simpandas as sp
    >>> idx = sp.SimIndex([['A', 'A', 'B', 'B'], [1, 2, 1, 2]], units='m')
    >>> idx.units
    'm'
    >>> idx.to('ft')  # Convert to feet
    """
    _metadata = ['units']

    def __new__(cls, *args, **kwargs):
        if 'units' in kwargs:
            units = kwargs.pop('units')
        else:
            units = None

        # Extract names before building, as pd.Index.__new__ doesn't accept it
        names = kwargs.pop('names', None)

        # Build the underlying index object
        if len(args) > 0 and isinstance(args[0], list) and len(args[0]) > 0 and isinstance(args[0][0], (list, tuple)):
            # list of arrays or list of tuples → build MultiIndex
            if isinstance(args[0][0], tuple):
                obj = pd.MultiIndex.from_tuples(args[0], names=names)
            else:
                obj = pd.MultiIndex.from_arrays(args[0], names=names)
        elif len(args) > 0 and isinstance(args[0], list) and len(args[0]) == 0:
            # empty list of arrays: build from arrays with names
            obj = pd.MultiIndex.from_arrays([[] for _ in (names or [None])], names=names)
        elif len(args) > 0 and len(args[0]) > 0 and hasattr(args[0], '__iter__') and sum([type(each) is tuple for each in args[0]]) == len(args[0]):
            obj = pd.MultiIndex.from_tuples(args[0], names=names if names is not None else getattr(args[0], 'names', None))
        else:
            obj = pd.Index.__new__(cls, *args, **kwargs)
            if names is not None:
                try:
                    object.__setattr__(obj, 'names', names)
                except Exception:
                    pass

        obj.units = units

        # Use weakref to avoid a reference cycle: obj → closure → obj.
        # Without weakref, obj.to and obj.set_units closures would capture obj
        # directly, preventing immediate ref-count collection and causing GC churn.
        obj_ref = weakref.ref(obj)

        def to_(units):
            actual = obj_ref()
            if actual is not None:
                return SimIndex(convert(actual.values, actual.units, units))

        def set_units_(units):
            actual = obj_ref()
            if actual is None:
                return
            if hasattr(units, 'unit') and type(units.unit) is str:
                units = units.unit
            elif hasattr(units, 'units') and type(units.units) is str:
                units = units.units
            if type(units) is str:
                actual.units = units.strip()
            elif type(units) is dict:
                actual.units = units.copy()

        obj.to = to_
        obj.set_units = set_units_
        return obj

    def to(self, units):
        """Return a new SimIndex with values converted to the requested units."""
        return SimIndex(convert(self.values, self.units, units))

    def set_units(self, units):
        """Set the units attribute on this SimIndex in-place."""
        if hasattr(units, 'unit') and type(units.unit) is str:
            units = units.unit
        elif hasattr(units, 'units') and type(units.units) is str:
            units = units.units
        if type(units) is str:
            self.units = units.strip()
        elif type(units) is dict:
            self.units = units.copy()

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
