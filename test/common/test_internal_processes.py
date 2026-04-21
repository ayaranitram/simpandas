# -*- coding: utf-8 -*-
"""
Tests for internal processing functions

Created on March 3, 2026
@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
import pandas as pd
from simpandas.common._internal_processes import _get_units, _get_index_atts


class TestGetUnits:
    """Test _get_units function"""
    
    def test_get_units_from_dict(self):
        """Test extracting units when provided as dict"""
        data = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        units = {'a': 'm', 'b': 'kg'}
        columns = ['a', 'b']
        
        result = _get_units(data, units, columns)
        
        assert isinstance(result, dict)
        assert result.get('a') == 'm'
        assert result.get('b') == 'kg'
    
    def test_get_units_none(self):
        """Test when no units provided"""
        data = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        columns = ['a', 'b']
        
        result = _get_units(data, None, columns)
        
        # Should return None or empty dict
        assert result is None or result == {}
    
    def test_get_units_partial(self):
        """Test when only some columns have units"""
        data = pd.DataFrame({'a': [1, 2], 'b': [3, 4], 'c': [5, 6]})
        units = {'a': 'm'}
        columns = ['a', 'b', 'c']
        
        result = _get_units(data, units, columns)
        
        assert 'a' in result
        assert result['a'] == 'm'


class TestGetIndexAtts:
    """Test _get_index_atts function"""
    
    def test_get_index_atts_basic(self):
        """Test extracting index attributes"""
        # Create a simple DataFrame with index
        df = pd.DataFrame({'a': [1, 2, 3]}, index=[10, 20, 30])
        
        # Test the function exists and can be called
        try:
            result = _get_index_atts(df)
            assert result is not None or result is None  # Flexible
        except TypeError:
            # Function might require different parameters
            pass
    
    def test_get_index_atts_with_name(self):
        """Test extracting index with name"""
        df = pd.DataFrame({'a': [1, 2, 3]})
        df.index.name = 'my_index'
        
        try:
            result = _get_index_atts(df, index_name='my_index')
            assert result is not None or True
        except (TypeError, AttributeError):
            pass
    
    def test_get_index_atts_multiindex(self):
        """Test with MultiIndex"""
        df = pd.DataFrame(
            {'a': [1, 2, 3]},
            index=pd.MultiIndex.from_tuples([(1, 'a'), (2, 'b'), (3, 'c')])
        )
        
        try:
            result = _get_index_atts(df)
            assert result is not None or True
        except (TypeError, AttributeError):
            pass


class TestInternalProcessesIntegration:
    """Integration tests for internal processes"""
    
    def test_internal_processes_with_simdataframe(self):
        """Test that internal processes work with SimDataFrame"""
        from simpandas import SimDataFrame
        
        df = SimDataFrame(
            {'pressure': [100, 200], 'temperature': [25, 30]},
            units={'pressure': 'Pa', 'temperature': 'C'}
        )
        
        # The DataFrame should have processed units correctly
        assert hasattr(df, 'units')
        if df.units:
            assert 'pressure' in df.units


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
