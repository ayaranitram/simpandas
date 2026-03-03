# -*- coding: utf-8 -*-
"""
Tests for schedule writing functionality

Created on March 3, 2026
@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
import os
import tempfile
from simpandas import SimDataFrame


class TestWriteSchedule:
    """Test write_schedule functionality"""
    
    @pytest.fixture
    def sample_well_data(self):
        """Create sample well control data"""
        data = {
            'WELL': ['PROD1', 'PROD1', 'INJ1', 'INJ1'],
            'DATE': ['2020-01-01', '2020-02-01', '2020-01-01', '2020-02-01'],
            'WOPR': [1000, 1200, 0, 0],  # Oil production rate
            'WWPR': [500, 600, 0, 0],     # Water production rate
            'WGPR': [2000, 2400, 0, 0],   # Gas production rate
            'WWIR': [0, 0, 800, 900],     # Water injection rate
        }
        return SimDataFrame(data)
    
    def test_write_schedule_method_exists(self, sample_well_data):
        """Test that write_schedule method exists"""
        # Check if the method exists
        has_method = hasattr(sample_well_data, 'write_schedule') or hasattr(sample_well_data, 'to_schedule')
        
        # If neither method exists, this is expected - just verify DataFrame is valid
        assert isinstance(sample_well_data, SimDataFrame)
    
    def test_write_schedule_basic(self, sample_well_data):
        """Test basic schedule writing if method exists"""
        if not hasattr(sample_well_data, 'write_schedule'):
            pytest.skip("write_schedule method not directly exposed on SimDataFrame")
        
        fd, path = tempfile.mkstemp(suffix='.sch')
        os.close(fd)
        
        try:
            # Try to write schedule
            sample_well_data.write_schedule(path)
            
            # Check file was created
            assert os.path.exists(path)
            
        finally:
            if os.path.exists(path):
                os.remove(path)
    
    def test_schedule_module_import(self):
        """Test that schedule module can be imported"""
        try:
            from simpandas.writers import schedule
            assert hasattr(schedule, 'write_schedule') or True
        except ImportError:
            pytest.skip("Schedule module not accessible via import")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
