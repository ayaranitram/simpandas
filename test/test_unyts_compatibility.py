# -*- coding: utf-8 -*-
"""
Integration tests for unyts.Unit <-> SimSeries arithmetic interoperability.

Converted from the repository-root script ``test_unyts_compatibility.py``.
Both operand orders are tested:
  * ``SimSeries + Unit``  (SimSeries.__add__ drives the conversion)
  * ``Unit + SimSeries``  (SimSeries.__radd__ is invoked via unyts delegation)
"""

import pytest

try:
    import unyts
    import pandas as pd
    from simpandas import SimSeries
    HAS_UNYTS = True
except ImportError:
    HAS_UNYTS = False

pytestmark = pytest.mark.skipif(not HAS_UNYTS, reason="unyts not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ft():
    return unyts.units(1.0, 'ft')


def _yd_series():
    return SimSeries(pd.Series([1.0, 2.0, 3.0]), units='yd')


# ---------------------------------------------------------------------------
# unyts <-> unyts (sanity)
# ---------------------------------------------------------------------------

def test_unyts_plus_unyts():
    f = _ft()
    i = unyts.units(1.0, 'in')
    result = f + i
    # 1 ft + 1 in = 1.0833... ft; unyts Unit objects expose their numeric value via .value
    assert pytest.approx(result.value, rel=1e-4) == 1.0 + 1.0 / 12.0


# ---------------------------------------------------------------------------
# unyts <-> plain pd.Series  (no unit-aware conversion expected)
# ---------------------------------------------------------------------------

def test_unyts_plus_plain_series_returns_series():
    f = _ft()
    s = pd.Series([1.0, 2.0, 3.0])
    result = f + s
    # result is a unyts Length (broadcast), not a SimSeries
    assert len(result) == 3


def test_plain_series_plus_unyts_returns_series():
    f = _ft()
    s = pd.Series([1.0, 2.0, 3.0])
    result = s + f
    assert len(result) == 3


# ---------------------------------------------------------------------------
# SimSeries + Unit  (left-hand SimSeries)
# ---------------------------------------------------------------------------

def test_simseries_plus_unit_values():
    """ss + f should add 1 ft (= 1/3 yd) to each element and keep yd units."""
    ss = _yd_series()
    f = _ft()
    result = ss + f
    assert isinstance(result, SimSeries)
    # 1 ft = 1/3 yd
    expected = [1.0 + 1.0 / 3.0, 2.0 + 1.0 / 3.0, 3.0 + 1.0 / 3.0]
    assert pytest.approx(list(result.values), rel=1e-4) == expected


def test_simseries_plus_unit_preserves_units():
    """The result of ss + f should carry the SimSeries' original units."""
    ss = _yd_series()
    result = ss + _ft()
    assert result.units == 'yd'


def test_simseries_plus_unit_returns_simseries():
    result = _yd_series() + _ft()
    assert isinstance(result, SimSeries)


# ---------------------------------------------------------------------------
# Unit + SimSeries  (left-hand Unit, reflected operator on SimSeries)
#
# Previously this path failed because unyts did not detect SimSeries as a
# units-aware object and did not delegate to SimSeries.__radd__.  That bug
# was fixed in unyts; both operand orders now produce a correct result.
# ---------------------------------------------------------------------------

def test_unit_plus_simseries_returns_simseries():
    """f + ss must delegate to SimSeries.__radd__ and return a SimSeries."""
    result = _ft() + _yd_series()
    assert isinstance(result, SimSeries)


def test_unit_plus_simseries_values():
    """f + ss: SimSeries is converted to ft, then 1 ft is added.
    [1 yd, 2 yd, 3 yd] = [3 ft, 6 ft, 9 ft]; plus 1 ft = [4, 7, 10] ft."""
    result = _ft() + _yd_series()
    assert pytest.approx(list(result.values), rel=1e-4) == [4.0, 7.0, 10.0]


def test_unit_plus_simseries_units():
    """Result units should be the left-operand (ft) when Unit is on the left."""
    result = _ft() + _yd_series()
    assert result.units == 'ft'
