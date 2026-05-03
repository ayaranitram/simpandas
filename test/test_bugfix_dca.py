# -*- coding: utf-8 -*-
"""
Tests for bug fixes reported from the DCA Workstation integration.

Issue 1: SimDataFrame.__setitem__ KeyError on column re-assignment
Issue 2: SimSeries fastpath DeprecationWarning
Issue 3: SimSeries.as_dict() / from_dict() with unyts values
"""

import warnings
import pytest
from simpandas import SimDataFrame, SimSeries


# ---- Issue 1: __setitem__ KeyError on column re-assignment ----

class TestSetitemExistingColumn:
    """SimDataFrame.__setitem__ should not raise KeyError when re-assigning
    an existing column whose unit wasn't pre-registered in the incoming u_dict."""

    def test_assign_pandas_series_preserves_unit(self):
        """Assigning a plain pandas Series to an existing column must preserve its unit."""
        import pandas as pd
        sdf = SimDataFrame(
            {"GR": [50.0, 60.0, 70.0], "RHOB": [2.5, 2.4, 2.3]},
            units={"GR": "gAPI", "RHOB": "g/cc"},
        )
        # This triggers the after == before path with key not in u_dict
        sdf["GR"] = pd.Series([50.0, 0.0, 70.0], index=sdf.index)
        assert sdf.get_units("GR") == "gAPI"

    def test_assign_numpy_array_preserves_unit(self):
        """Assigning a numpy array to an existing column must preserve its unit."""
        import numpy as np
        sdf = SimDataFrame(
            {"PRES": [3000.0, 2500.0, 2000.0]},
            units={"PRES": "psi"},
        )
        sdf["PRES"] = np.array([3000.0, 0.0, 2000.0])
        assert sdf.get_units("PRES") == "psi"

    def test_assign_list_preserves_unit(self):
        """Assigning a plain list to an existing column must preserve its unit."""
        sdf = SimDataFrame(
            {"GR": [50.0, -999.25, 70.0], "DT": [100.0, -999.25, 80.0]},
            units={"GR": "gAPI", "DT": "us/ft"},
        )
        import numpy as np
        # Scrub nulls using plain DataFrame then assign back
        for col in list(sdf.columns):
            vals = sdf[col].values.copy()
            vals[vals == -999.25] = np.nan
            sdf[col] = list(vals)
        assert sdf.get_units("GR") == "gAPI"
        assert sdf.get_units("DT") == "us/ft"

    def test_setitem_with_new_simseries_unit_used(self):
        """When assigning a SimSeries with units, the new unit should be used."""
        sdf = SimDataFrame(
            {"A": [1.0, 2.0]},
            units={"A": "m"},
        )
        new_col = SimSeries([10.0, 20.0], units="ft", name="B")
        sdf["B"] = new_col
        assert sdf.get_units("B") == "ft"


# ---- Issue 2: fastpath DeprecationWarning ----

class TestFastpathDeprecation:
    """SimSeries construction should not emit a DeprecationWarning
    about the 'fastpath' keyword."""

    def test_no_deprecation_on_construct(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            _ = SimSeries([1.0, 2.0, 3.0], units="psi")

    def test_no_deprecation_on_copy(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            ss = SimSeries([1.0, 2.0], units="bar")
            _ = ss.copy()

    def test_fastpath_param_still_accepted(self):
        """The fastpath parameter should still be accepted (for backward compat)
        even though it's silently ignored."""
        ss = SimSeries([1.0, 2.0], units="psi", fastpath=True)
        assert len(ss) == 2


# ---- Issue 3: as_dict() / from_dict() with unyts values ----

class TestAsDict:
    """SimSeries.as_dict() should return unyts-valued dicts by default."""

    def test_as_dict_returns_unyts_instances(self):
        from unyts import is_Unit
        ss = SimSeries([100, 200], index=[0.0, 1.0], units='psi', name='BHP')
        d = ss.as_dict()
        assert len(d) == 2
        assert is_Unit(d[0.0])
        assert d[0.0].value == 100
        assert d[0.0].units == 'psi'
        assert is_Unit(d[1.0])
        assert d[1.0].value == 200

    def test_as_dict_data_only(self):
        """data_only=True should return plain values without unyts."""
        ss = SimSeries([10, 20], index=['a', 'b'], units='m')
        d = ss.as_dict(data_only=True)
        assert d == {'a': 10, 'b': 20}

    def test_as_dict_empty(self):
        ss = SimSeries([], dtype=object)
        assert ss.as_dict() == {}

    def test_as_dict_unitless(self):
        """Unitless series should return plain values even with data_only=False."""
        ss = SimSeries([1, 2, 3], units='unitless')
        d = ss.as_dict()
        assert d == {0: 1, 1: 2, 2: 3}


class TestFromDict:
    """SimSeries.from_dict() should reconstruct from unyts-valued dicts."""

    def test_roundtrip(self):
        """Full round-trip: SimSeries -> as_dict() -> from_dict() -> SimSeries."""
        ss = SimSeries([100, 200, 300], index=[0.0, 1.0, 2.0],
                       units='psi', name='BHP')
        d = ss.as_dict()
        reconstructed = SimSeries.from_dict(d, name='BHP')
        assert (reconstructed == ss).all()
        assert reconstructed.units == 'psi'
        assert reconstructed.name == 'BHP'

    def test_from_dict_plain_values(self):
        """from_dict should also accept plain (non-unyts) values."""
        d = {0.0: 100, 1.0: 200}
        ss = SimSeries.from_dict(d, name='test')
        assert ss.name == 'test'
        # When no unyts instances are found, units is None or empty (no explicit unit)
        assert ss.units is None or ss.units == {} or ss.units == 'unitless'
        assert len(ss) == 2

    def test_from_dict_empty(self):
        ss = SimSeries.from_dict({})
        assert ss.empty

    def test_from_dict_with_unyts(self):
        """Directly construct from externally-created unyts instances."""
        from unyts import units
        d = {0.0: units(100, 'psi'), 1.0: units(200, 'psi')}
        ss = SimSeries.from_dict(d, name='BHP')
        assert ss.units == 'psi'
        assert ss.iloc[0] == 100
        assert ss.iloc[1] == 200

    def test_from_dict_with_index_metadata(self):
        """Index metadata should be passed through to the reconstructed series."""
        from unyts import units
        d = {0.0: units(100, 'psi'), 1.0: units(200, 'psi')}
        ss = SimSeries.from_dict(d, name='BHP', index_name='time', index_units='day')
        assert ss.index.name == 'time'


# ---- Issue 4: SimSeries.__call__ vs apply_if_callable ----

class TestApplyIfCallable:
    """Issue #4: SimSeries.__call__ must not interfere with pandas
    apply_if_callable used inside .mask(), .where(), etc."""

    def test_simseries_mask_with_series_cond(self):
        sdf = SimDataFrame({"GR": [50., 60., 70.]}, units={"GR": "gAPI"})
        gr = sdf["GR"]
        masked = gr.mask(gr == 60.0, 0.0)
        assert masked.tolist() == [50., 0., 70.]
        assert masked.units == "gAPI"

    def test_simseries_where_with_series_cond(self):
        sdf = SimDataFrame({"GR": [50., 60., 70.]}, units={"GR": "gAPI"})
        gr = sdf["GR"]
        kept = gr.where(gr > 55, 0.0)
        assert kept.tolist() == [0., 60., 70.]

    def test_simdataframe_setitem_via_mask(self):
        """The full end-to-end pattern from the original report."""
        sdf = SimDataFrame({"GR": [50., 60., 70.]}, units={"GR": "gAPI"})
        sdf["GR"] = sdf["GR"].mask(sdf["GR"] == 60., 0.)
        assert sdf.get_units("GR") == "gAPI"
        assert sdf["GR"].tolist() == [50., 0., 70.]

    def test_simseries_call_with_key_still_works(self):
        """Backward compat: series(key) must still work."""
        ss = SimSeries([10, 20, 30], index=['a', 'b', 'c'], units='m')
        assert ss('b') == 20       # existing __call__ behavior
        assert list(ss()) == [10, 20, 30]  # ss() returns values

    def test_simseries_call_with_series_arg_returns_self(self):
        """When __call__ receives a Series (apply_if_callable pattern),
        it must return self unchanged."""
        import pandas as pd
        ss = SimSeries([1, 2, 3], units='m')
        result = ss(pd.Series([10, 20, 30]))
        assert result is ss

    def test_simdataframe_mask_preserves_unit(self):
        """mask() on a SimDataFrame itself (not just SimSeries)."""
        sdf = SimDataFrame(
            {"GR": [50., 60., 70.], "RHOB": [2.5, 2.4, 2.3]},
            units={"GR": "gAPI", "RHOB": "g/cc"})
        masked = sdf.mask(sdf > 60)   # NaN where > 60
        assert masked.get_units("GR") == "gAPI"
        assert masked.get_units("RHOB") == "g/cc"
