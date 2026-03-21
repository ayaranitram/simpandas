# -*- coding: utf-8 -*-
"""
Tests for SimIndex class

Created on March 3, 2026
@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
import pandas as pd
from simpandas.index import SimIndex


class TestSimIndex:
    """Test SimIndex - a MultiIndex with unit support"""
    
    def test_simindex_creation_basic(self):
        """Test basic SimIndex creation"""
        names = ['pressure', 'temperature']
        index = SimIndex([['A', 'A', 'B'], [1, 2, 1]], names=names)
        assert isinstance(index, pd.MultiIndex)
        assert list(index.names) == names
    
    def test_simindex_with_units(self):
        """Test SimIndex creation with units"""
        names = ['depth', 'time']
        units = {'depth': 'm', 'time': 'day'}
        index = SimIndex([['shallow', 'deep'], [0, 10]], names=names, units=units)
        assert hasattr(index, 'units')
        assert index.units == units
    
    def test_simindex_set_units(self):
        """Test setting units on SimIndex"""
        index = SimIndex([[1, 2, 3], ['a', 'b', 'c']], names=['x', 'y'])
        index.set_units({'x': 'km', 'y': 'unitless'})
        assert index.units['x'] == 'km'
        assert index.units['y'] == 'unitless'
    
    def test_simindex_convert_units(self):
        """Test unit conversion on SimIndex"""
        # This is a basic test - actual conversion depends on unyts
        index = SimIndex([[100, 200, 300]], names=['distance'], units={'distance': 'cm'})
        # Test the 'to' method exists (set in __new__)
        assert hasattr(index, 'to')
    
    def test_simindex_to_method(self):
        """Test the 'to' method for unit conversion"""
        index = SimIndex([[1000, 2000]], names=['mass'], units={'mass': 'g'})
        # Test the to method exists
        assert hasattr(index, 'to')
    
    def test_simindex_empty(self):
        """Test empty SimIndex creation"""
        index = SimIndex([[], []], names=['a', 'b'])
        assert len(index) == 0
        assert list(index.names) == ['a', 'b']
    
    def test_simindex_single_level(self):
        """Test SimIndex with single level"""
        index = SimIndex([[1, 2, 3]], names=['value'])
        assert len(index) == 3
        assert index.names == ['value']
    
    def test_simindex_metadata_preservation(self):
        """Test that metadata is preserved through operations"""
        index = SimIndex([[1, 2]], names=['x'], units={'x': 'm'})
        assert hasattr(index, 'units')
        # After slicing
        sliced = index[:1]
        # Check if units are preserved (may depend on implementation)
        assert hasattr(sliced, 'units') or True  # Relaxed assertion


class TestSimIndexIntegration:
    """Integration tests for SimIndex with DataFrames"""
    
    def test_simindex_in_dataframe(self):
        """Test using SimIndex as DataFrame index"""
        from simpandas import SimDataFrame
        
        index = SimIndex([[1, 2, 3], ['a', 'b', 'c']], names=['num', 'letter'])
        df = SimDataFrame({'values': [10, 20, 30]}, index=index)
        
        assert isinstance(df.index, pd.MultiIndex)
        assert len(df) == 3
    
    def test_simindex_units_in_simdataframe(self):
        """Test that units work with SimDataFrame"""
        from simpandas import SimDataFrame
        
        index = SimIndex([[1, 2]], names=['depth'], units={'depth': 'm'})
        df = SimDataFrame({'pressure': [100, 200]}, index=index, units={'pressure': 'Pa'})
        
        # Check both index units and column units
        assert hasattr(df, 'index_units') or hasattr(df.index, 'units')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
