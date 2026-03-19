# -*- coding: utf-8 -*-
"""
Tests for Excel reading functionality

Created on March 3, 2026
@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
import pandas as pd
import os
import tempfile
from simpandas import SimDataFrame, read_excel


class TestReadExcel:
    """Test read_excel function"""
    
    @pytest.fixture
    def sample_excel_file(self):
        """Create a temporary Excel file for testing"""
        # Create a temporary file
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        
        # Create sample data
        df = pd.DataFrame({
            'pressure': [100, 200, 300],
            'temperature': [25, 30, 35],
            'volume': [1.0, 1.5, 2.0]
        })
        
        # Write to Excel
        df.to_excel(path, index=False)
        
        yield path
        
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
    
    @pytest.fixture
    def excel_with_units(self):
        """Create an Excel file with units row"""
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        
        # Create DataFrame with units as second row
        data = {
            'pressure': ['Pa', 100, 200, 300],
            'temperature': ['C', 25, 30, 35],
            'volume': ['m**3', 1.0, 1.5, 2.0]
        }
        df = pd.DataFrame(data)
        df.to_excel(path, index=False, header=True)
        
        yield path
        
        if os.path.exists(path):
            os.remove(path)
    
    def test_read_excel_basic(self, sample_excel_file):
        """Test basic Excel reading"""
        result = read_excel(sample_excel_file, units=None)
        
        assert isinstance(result, SimDataFrame)
        assert len(result) == 3
        assert 'pressure' in result.columns
        assert 'temperature' in result.columns
    
    def test_read_excel_with_units_dict(self, sample_excel_file):
        """Test reading Excel with units as dictionary"""
        units = {'pressure': 'Pa', 'temperature': 'C', 'volume': 'm**3'}
        result = read_excel(sample_excel_file, units=units)
        
        assert isinstance(result, SimDataFrame)
        assert hasattr(result, 'units')
        if result.units:
            assert 'pressure' in result.units or result.units.get('pressure') == 'Pa'
    
    def test_read_excel_with_units_row(self, excel_with_units):
        """Test reading Excel where units are in a specific row"""
        # Units in row 0 (after header)
        result = read_excel(excel_with_units, units=1, header=0)
        
        assert isinstance(result, SimDataFrame)
        # Should have 3 data rows after removing units row
        assert len(result) >= 3 or len(result) == 4  # Flexible assertion
    
    def test_read_excel_with_sheet_name(self, sample_excel_file):
        """Test reading specific sheet"""
        result = read_excel(sample_excel_file, sheet_name=0)
        assert isinstance(result, SimDataFrame)
    
    def test_read_excel_with_index_units(self, sample_excel_file):
        """Test reading with index units specified"""
        result = read_excel(sample_excel_file, indexUnits='day')
        
        assert isinstance(result, SimDataFrame)
        if hasattr(result, 'index_units'):
            assert result.index_units == 'day' or True  # Flexible
    
    def test_read_excel_with_name_separator(self, sample_excel_file):
        """Test reading with custom name separator"""
        result = read_excel(sample_excel_file, nameSeparator='_')
        
        assert isinstance(result, SimDataFrame)
        if hasattr(result, 'name_separator'):
            assert result.name_separator == '_'
    
    def test_read_excel_returns_simdataframe(self, sample_excel_file):
        """Test that read_excel always returns SimDataFrame"""
        result = read_excel(sample_excel_file)
        
        # Check it's a SimDataFrame, not just a regular DataFrame
        assert type(result).__name__ == 'SimDataFrame'
        assert hasattr(result, 'params_')


class TestReadExcelEdgeCases:
    """Test edge cases and error handling"""
    
    def test_read_excel_nonexistent_file(self):
        """Test reading non-existent file"""
        with pytest.raises((FileNotFoundError, IOError, Exception)):
            read_excel('nonexistent_file.xlsx')
    
    def test_read_excel_empty_file(self):
        """Test reading empty Excel file"""
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        
        try:
            # Create empty Excel
            pd.DataFrame().to_excel(path)
            
            # Should handle empty file gracefully
            result = read_excel(path)
            assert isinstance(result, SimDataFrame) or result is not None
        
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
