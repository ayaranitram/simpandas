# -*- coding: utf-8 -*-
"""
Tests for WITSML reader/writer.
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from simpandas import SimDataFrame


@pytest.fixture
def log_xml_v14():
    """Minimal WITSML v1.4.1.1 log document."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<logs xmlns="http://www.witsml.org/schemas/1series">
  <log uidWell="W-001" uidWellbore="WB-001" uid="LOG-001">
    <name>GR Log</name>
    <indexType>measured depth</indexType>
    <logCurveInfo uid="lci-1">
      <mnemonic>DEPT</mnemonic>
      <unit>m</unit>
      <curveDescription>Measured Depth</curveDescription>
    </logCurveInfo>
    <logCurveInfo uid="lci-2">
      <mnemonic>GR</mnemonic>
      <unit>gAPI</unit>
      <curveDescription>Gamma Ray</curveDescription>
    </logCurveInfo>
    <logCurveInfo uid="lci-3">
      <mnemonic>RHOB</mnemonic>
      <unit>g/cm3</unit>
      <curveDescription>Bulk Density</curveDescription>
    </logCurveInfo>
    <logData>
      <mnemonicList>DEPT,GR,RHOB</mnemonicList>
      <unitList>m,gAPI,g/cm3</unitList>
      <data>1000.0,45.2,2.35</data>
      <data>1001.0,50.1,2.40</data>
      <data>1002.0,48.8,2.38</data>
    </logData>
  </log>
</logs>
"""


@pytest.fixture
def trajectory_xml():
    """Minimal WITSML v1.4.1.1 trajectory document."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<trajectorys xmlns="http://www.witsml.org/schemas/1series">
  <trajectory uidWell="W-001" uidWellbore="WB-001" uid="TRJ-001">
    <name>Main Trajectory</name>
    <trajectoryStation uid="ts-1">
      <md uom="m">1000.0</md>
      <tvd uom="m">998.5</tvd>
      <incl uom="dega">2.5</incl>
      <azi uom="dega">135.0</azi>
    </trajectoryStation>
    <trajectoryStation uid="ts-2">
      <md uom="m">1100.0</md>
      <tvd uom="m">1090.2</tvd>
      <incl uom="dega">5.0</incl>
      <azi uom="dega">138.0</azi>
    </trajectoryStation>
  </trajectory>
</trajectorys>
"""


@pytest.fixture
def witsml_path():
    fd, path = tempfile.mkstemp(suffix='.xml')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestWitsmlReader:

    def test_read_log(self, log_xml_v14, witsml_path):
        from simpandas.readers.witsml import read_witsml
        with open(witsml_path, 'w', encoding='utf-8') as f:
            f.write(log_xml_v14)

        result = read_witsml(witsml_path)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 3
        assert 'GR' in result.columns
        assert 'RHOB' in result.columns

    def test_read_log_units(self, log_xml_v14, witsml_path):
        from simpandas.readers.witsml import read_witsml
        with open(witsml_path, 'w', encoding='utf-8') as f:
            f.write(log_xml_v14)

        result = read_witsml(witsml_path)
        u = result.units
        if isinstance(u, dict):
            assert u.get('GR') == 'gAPI'
            assert u.get('RHOB') == 'g/cm3'

    def test_read_trajectory(self, trajectory_xml, witsml_path):
        from simpandas.readers.witsml import read_witsml
        with open(witsml_path, 'w', encoding='utf-8') as f:
            f.write(trajectory_xml)

        result = read_witsml(witsml_path)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2

    def test_file_not_found(self):
        from simpandas.readers.witsml import read_witsml
        with pytest.raises(FileNotFoundError):
            read_witsml('/nonexistent/witsml.xml')


class TestWitsmlWriter:

    def test_write_log(self, witsml_path):
        from simpandas.writers.witsml import write_witsml

        df = pd.DataFrame({
            'GR': [45.2, 50.1, 48.8],
            'RHOB': [2.35, 2.40, 2.38],
        }, index=[1000.0, 1001.0, 1002.0])
        sdf = SimDataFrame(
            data=df,
            units={'GR': 'gAPI', 'RHOB': 'g/cm3'},
            index_units='m',
        )

        write_witsml(sdf, witsml_path, well_name='TestWell', wellbore_name='WB-1')
        assert os.path.isfile(witsml_path)

        # verify valid XML
        import xml.etree.ElementTree as ET
        tree = ET.parse(witsml_path)
        root = tree.getroot()
        assert root is not None

    def test_to_witsml_method(self, witsml_path):
        df = pd.DataFrame({'GR': [10, 20]}, index=[100.0, 200.0])
        sdf = SimDataFrame(data=df, units={'GR': 'gAPI'}, index_units='m')
        sdf.to_witsml(witsml_path)
        assert os.path.isfile(witsml_path)


class TestWitsmlRoundTrip:

    def test_log_round_trip(self, witsml_path):
        from simpandas.writers.witsml import write_witsml
        from simpandas.readers.witsml import read_witsml

        df = pd.DataFrame({
            'GR': [45.2, 50.1],
            'RHOB': [2.35, 2.40],
        }, index=[1000.0, 1001.0])
        sdf = SimDataFrame(
            data=df,
            units={'GR': 'gAPI', 'RHOB': 'g/cm3'},
            index_units='m',
        )

        write_witsml(sdf, witsml_path)
        result = read_witsml(witsml_path)
        assert isinstance(result, SimDataFrame)
        assert len(result) == 2
        assert 'GR' in result.columns
        np.testing.assert_array_almost_equal(
            result['GR'].values.astype(float), [45.2, 50.1], decimal=1
        )
