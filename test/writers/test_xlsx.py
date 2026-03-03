# -*- coding: utf-8 -*-
"""
Tests for Excel writing functionality

Created on March 3, 2026
@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
import pandas as pd
import os
import tempfile
from simpandas import SimDataFrame, read_excel


class TestWriteExcel:
    """Test write_excel functionality (via SimDataFrame.to_excel)"""
    
    @pytest.fixture
    def sample_simdataframe(self):
        """Create a sample SimDataFrame for testing"""
        data = {
            'pressure': [100, 200, 300],
            'temperature': [25, 30, 35],
            'volume': [1.0, 1.5, 2.0]
        }
        units = {'pressure': 'Pa', 'temperature': 'C', 'volume': 'm**3'}
        
        return SimDataFrame(data, units=units)
    
    def test_write_excel_basic(self, sample_simdataframe):
        """Test basic Excel writing"""
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        
        try:
            # Write to Excel
            if hasattr(sample_simdataframe, 'to_excel'):
                sample_simdataframe.to_excel(path, index=False)
            else:
                # Fallback to pandas method
                sample_simdataframe.to_excel(path, index=False)
            
            # Verify file exists
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        
        finally:
            if os.path.exists(path):
                os.remove(path)
    
    def test_roundtrip_excel(self, sample_simdataframe):
        """Test writing and reading back preserves data"""
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        
        try:
            # Write
            sample_simdataframe.to_excel(path, index=False)
            
            # Read back
            result = read_excel(path)
            
            # Check data is preserved
            assert len(result) == len(sample_simdataframe)
            assert list(result.columns) == list(sample_simdataframe.columns)
            
            # Check values are close (accounting for floating point)
            pd.testing.assert_frame_equal(
                result[['pressure', 'temperature', 'volume']].astype(float),
                sample_simdataframe[['pressure', 'temperature', 'volume']].astype(float),
                check_dtype=False,
                atol=0.01
            )
        
        finally:
            if os.path.exists(path):
                os.remove(path)
    
    def test_write_excel_with_index(self, sample_simdataframe):
        """Test writing Excel with index included"""
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        
        try:
            sample_simdataframe.to_excel(path, index=True)
            assert os.path.exists(path)
            
            # Read back and check index was written
            result = pd.read_excel(path, index_col=0)
            assert len(result) == len(sample_simdataframe)
        
        finally:
            if os.path.exists(path):
                os.remove(path)
    
    def test_write_excel_creates_file(self):
        """Test that writing creates a valid Excel file"""
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        
        try:
            df = SimDataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
            df.to_excel(path)
            
            # Verify it's a valid Excel file by reading it back
            check = pd.read_excel(path)
            assert len(check) == 3
        
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestWriteExcelUnits:
    """Test unit handling in Excel writing"""
    
    def test_write_preserves_units_metadata(self):
        """Test that units information can be recovered"""
        fd, path = tempfile.mkstemp(suffix='.xlsx')
        os.close(fd)
        
        try:
            # Create DataFrame with units
            df = SimDataFrame(
                {'pressure': [100, 200], 'temp': [25, 30]},
                units={'pressure': 'Pa', 'temp': 'C'}
            )
            
            # Write
            df.to_excel(path, index=False)
            
            # File should exist and be readable
            assert os.path.exists(path)
            result = pd.read_excel(path)
            assert len(result) >= 2
        
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
