# -*- coding: utf-8 -*-
"""
ColumnUnits — an ordered, duplicate-key-safe mapping of column names to units.

This class replaces the ``dict``/``list`` duality that was previously returned
by ``.units`` and ``get_units()``.  It behaves like a ``dict`` when keys are
unique and retains key information even when duplicate column names exist.

Usage::

    cu = ColumnUnits(['PRES', 'TEMP', 'PRES'], ['MPa', 'degC', 'psia'])
    cu['PRES']          # 'MPa'  (first match, dict-like)
    cu.get_all('PRES')  # ['MPa', 'psia']  (all matches)
    cu.iloc[2]          # 'psia'  (positional)
    list(cu)            # ['PRES', 'TEMP', 'PRES']  (key iteration)

"""

__version__ = '0.1.0'
__release__ = 20260421

import collections.abc
from typing import Any, Iterator, List, Optional, Union

__all__ = ['ColumnUnits']


class _IlocAccessor:
    """Positional accessor returned by :attr:`ColumnUnits.iloc`."""

    __slots__ = ('_owner',)

    def __init__(self, owner: 'ColumnUnits') -> None:
        self._owner = owner

    def __getitem__(self, index: int) -> Any:
        """Return the unit value at position *index*."""
        return self._owner._values[index]

    def __setitem__(self, index: int, value: Any) -> None:
        """Set the unit value at position *index*."""
        self._owner._values[index] = value

    def __repr__(self) -> str:  # pragma: no cover
        return f'_IlocAccessor({self._owner!r})'


class ColumnUnits(collections.abc.Mapping):
    """An ordered mapping of column names to unit strings that supports
    duplicate keys.

    Parameters
    ----------
    names : list-like of str
        Column (or row-index) names.  May contain duplicates.
    values : list-like, optional
        Unit string (or ``None``) for each name.  Must be the same length as
        *names*.  Defaults to a list of ``None`` values.

    Notes
    -----
    * Iteration (``for key in cu``) yields **names** (with duplicates), just
      like iterating over a ``dict`` yields keys.
    * ``cu[key]`` returns the unit for the **first** occurrence, preserving
      the ``dict``-like contract expected by most callers.
    * Use :meth:`get_all` to retrieve units for *all* occurrences of a key.
    * :attr:`iloc` gives positional read/write access.
    """

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, d: dict) -> 'ColumnUnits':
        """Build a :class:`ColumnUnits` from a plain ``{name: unit}`` dict."""
        return cls(list(d.keys()), list(d.values()))

    @classmethod
    def from_lists(cls, names: list, values: list) -> 'ColumnUnits':
        """Build a :class:`ColumnUnits` from two parallel lists."""
        return cls(names, values)

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def __init__(
        self,
        names: Optional[List[str]] = None,
        values: Optional[List[Any]] = None,
    ) -> None:
        if names is None:
            names = []
        self._names: List[str] = list(names)
        if values is None:
            self._values: List[Any] = [None] * len(self._names)
        else:
            self._values = list(values)
        if len(self._names) != len(self._values):
            raise ValueError(
                f"names ({len(self._names)}) and values ({len(self._values)}) "
                "must have the same length."
            )

    # ------------------------------------------------------------------
    # collections.abc.Mapping interface
    # ------------------------------------------------------------------

    def __getitem__(self, key: str) -> Any:
        """Return the unit for the *first* column with the given name."""
        for name, value in zip(self._names, self._values):
            if name == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        """Iterate over names (with duplicates, in insertion order)."""
        return iter(self._names)

    def __len__(self) -> int:
        return len(self._names)

    def __contains__(self, key: object) -> bool:  # type: ignore[override]
        return key in self._names

    # ------------------------------------------------------------------
    # Extra helpers
    # ------------------------------------------------------------------

    def get_all(self, key: str) -> List[Any]:
        """Return *all* unit values for columns named *key*."""
        return [v for n, v in zip(self._names, self._values) if n == key]

    @property
    def iloc(self) -> _IlocAccessor:
        """Positional accessor.  ``cu.iloc[i]`` returns/sets the i-th unit."""
        return _IlocAccessor(self)

    @property
    def names(self) -> List[str]:
        """The column name list (read-only view)."""
        return list(self._names)

    @property
    def values_list(self) -> List[Any]:
        """The unit-value list in positional order (read-only view)."""
        return list(self._values)

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to a plain ``dict``.

        When duplicate names exist the **last** value wins (matching Python's
        built-in ``dict()`` semantics for duplicate keys).
        """
        return dict(zip(self._names, self._values))

    def to_list(self) -> list:
        """Return the unit values as a positional list."""
        return list(self._values)

    def to_series(self):
        """Return a :class:`pandas.Series` with names as index and units as values."""
        import pandas as pd
        return pd.Series(data=self._values, index=self._names, name='units')

    # ------------------------------------------------------------------
    # Equality / repr
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ColumnUnits):
            return self._names == other._names and self._values == other._values
        if isinstance(other, dict):
            return self.to_dict() == other
        return NotImplemented

    def __repr__(self) -> str:
        pairs = ', '.join(
            f'{n!r}: {v!r}' for n, v in zip(self._names, self._values)
        )
        return f'ColumnUnits({{{pairs}}})'

    def __str__(self) -> str:
        return repr(self)

    # ------------------------------------------------------------------
    # Mutation helpers (used internally by SimDataFrame/SimSeries)
    # ------------------------------------------------------------------

    def _extend(self, n: int) -> None:
        """Append *n* ``None`` units (called when columns are added)."""
        self._values.extend([None] * n)
        # Caller is responsible for updating names via _set_names.

    def _sync(self, names: List[str]) -> None:
        """Resize and re-align to a new column name list *in-place*.

        * Extends with ``None`` if *names* is longer.
        * Truncates if *names* is shorter.
        """
        current = len(self._names)
        target = len(names)
        if target > current:
            self._values.extend([None] * (target - current))
        elif target < current:
            self._values = self._values[:target]
        self._names = list(names)
