# -*- coding: utf-8 -*-
"""
Tests for PRODML reader/writer.
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from simpandas import SimDataFrame


@pytest.fixture
def timeseries_xml():
    """Minimal PRODML v2 TimeSeries XML."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<TimeSeries xmlns="http://www.energistics.org/energyml/data/prodmlv2">
  <TimeSeries name="OilRate">
    <Key keyword="product" value="oil"/>
    <Value dateTime="2024-01-01T00:00:00" uom="bbl/d">100.0</Value>
    <Value dateTime="2024-01-02T00:00:00" uom="bbl/d">105.0</Value>
    <Value dateTime="2024-01-03T00:00:00" uom="bbl/d">98.0</Value>
  </TimeSeries>
</TimeSeries>
"""


@pytest.fixture
def volumes_xml():
    """Minimal PRODML v2 ProductVolume XML."""
    return """\
<?xml version="1.0" encoding="UTF-8"?>
<ProductVolume xmlns="http://www.energistics.org/energyml/data/prodmlv2">
  <Facility name="Well-A">
    <Period start="2024-01-01T00:00:00" end="2024-01-31T23:59:59">
      <Volume uom="bbl" product="oil">3100.0</Volume>
      <Volume uom="Mscf" product="gas">450.0</Volume>
    </Period>
    <Period start="2024-02-01T00:00:00" end="2024-02-29T23:59:59">
      <Volume uom="bbl" product="oil">2800.0</Volume>
      <Volume uom="Mscf" product="gas">410.0</Volume>
    </Period>
  </Facility>
</ProductVolume>
"""


@pytest.fixture
def prodml_path():
    fd, path = tempfile.mkstemp(suffix='.xml')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestProdmlReader:

    def test_read_timeseries(self, timeseries_xml, prodml_path):
        from simpandas.readers.prodml import read_prodml
        with open(prodml_path, 'w', encoding='utf-8') as f:
            f.write(timeseries_xml)

        result = read_prodml(prodml_path)
        assert isinstance(result, SimDataFrame)
        assert len(result) >= 1  # at least some data parsed

    def test_read_volumes(self, volumes_xml, prodml_path):
        from simpandas.readers.prodml import read_prodml
        with open(prodml_path, 'w', encoding='utf-8') as f:
            f.write(volumes_xml)

        result = read_prodml(prodml_path)
        assert isinstance(result, SimDataFrame)
        assert len(result) >= 1

    def test_file_not_found(self):
        from simpandas.readers.prodml import read_prodml
        with pytest.raises(FileNotFoundError):
            read_prodml('/nonexistent/prodml.xml')


class TestProdmlWriter:

    def test_write_timeseries_style(self, prodml_path):
        from simpandas.writers.prodml import write_prodml

        df = pd.DataFrame({
            'oil_rate': [100.0, 105.0, 98.0],
            'gas_rate': [450.0, 460.0, 440.0],
        }, index=pd.date_range('2024-01-01', periods=3))
        sdf = SimDataFrame(data=df, units={'oil_rate': 'bbl/d', 'gas_rate': 'Mscf/d'})

        write_prodml(sdf, prodml_path, style='timeseries')
        assert os.path.isfile(prodml_path)

        # verify valid XML
        import xml.etree.ElementTree as ET
        tree = ET.parse(prodml_path)
        root = tree.getroot()
        assert root is not None

    def test_write_volumes_style(self, prodml_path):
        from simpandas.writers.prodml import write_prodml

        df = pd.DataFrame({
            'oil_volume': [3100.0, 2800.0],
            'gas_volume': [450.0, 410.0],
        }, index=pd.date_range('2024-01-01', periods=2, freq='MS'))
        sdf = SimDataFrame(data=df, units={'oil_volume': 'bbl', 'gas_volume': 'Mscf'})

        write_prodml(sdf, prodml_path, style='volumes')
        assert os.path.isfile(prodml_path)

    def test_to_prodml_method(self, prodml_path):
        df = pd.DataFrame({'a': [1, 2]}, index=pd.date_range('2024-01-01', periods=2))
        sdf = SimDataFrame(data=df, units={'a': 'psi'})
        sdf.to_prodml(prodml_path)
        assert os.path.isfile(prodml_path)


class TestProdmlRoundTrip:

    def test_timeseries_round_trip(self, prodml_path):
        """Write then read back a timeseries PRODML file."""
        from simpandas.writers.prodml import write_prodml
        from simpandas.readers.prodml import read_prodml

        df = pd.DataFrame({
            'oil_rate': [100.0, 200.0],
        }, index=pd.date_range('2024-01-01', periods=2))
        sdf = SimDataFrame(data=df, units={'oil_rate': 'bbl/d'})

        write_prodml(sdf, prodml_path, style='timeseries')
        result = read_prodml(prodml_path)
        assert isinstance(result, SimDataFrame)
        assert len(result) >= 1
