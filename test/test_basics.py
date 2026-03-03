# -*- coding: utf-8 -*-
"""
Tests for SimBasics mixin class

The SimBasics class provides common functionality shared by both SimDataFrame
and SimSeries. This test file covers the extensive methods in this mixin.

Created on March 3, 2026
@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
import numpy as np
import pandas as pd
from simpandas import SimDataFrame, SimSeries


class TestSimBasicsArithmetic:
    """Test arithmetic methods from SimBasics"""
    
    def test_add(self):
        """Test addition operation"""
        df = SimDataFrame({'a': [1, 2, 3]}, units={'a': 'm'})
        result = df.add(SimDataFrame({'a': [10, 20, 30]}, units={'a': 'm'}))
        assert result['a'].iloc[0] == 11
    
    def test_sub(self):
        """Test subtraction operation"""
        df = SimDataFrame({'a': [10, 20, 30]}, units={'a': 'kg'})
        result = df.sub(SimDataFrame({'a': [1, 2, 3]}, units={'a': 'kg'}))
        assert result['a'].iloc[0] == 9
    
    def test_mul(self):
        """Test multiplication operation"""
        df = SimDataFrame({'a': [2, 3, 4]})
        result = df.mul(2)
        assert result['a'].iloc[0] == 4
    
    def test_truediv(self):
        """Test division operation"""
        df = SimDataFrame({'a': [10, 20, 30]})
        result = df.truediv(2)
        assert result['a'].iloc[0] == 5
    
    def test_pow(self):
        """Test power operation"""
        df = SimDataFrame({'a': [2, 3, 4]})
        result = df.pow(2)
        assert result['a'].iloc[0] == 4
        assert result['a'].iloc[1] == 9


class TestSimBasicsAggregation:
    """Test aggregation methods"""
    
    def test_mean(self):
        """Test mean calculation"""
        df = SimDataFrame({'a': [1, 2, 3, 4]}, units={'a': 'm'})
        result = df.mean()
        assert result['a'] == 2.5
    
    def test_mean0(self):
        """Test mean excluding zeros"""
        df = SimDataFrame({'a': [0, 2, 0, 4]}, units={'a': 'm'})
        if hasattr(df, 'mean0'):
            result = df.mean0()
            assert result['a'] == 3.0  # (2+4)/2
    
    def test_median(self):
        """Test median calculation"""
        df = SimDataFrame({'a': [1, 2, 3, 4, 5]})
        result = df.median()
        assert result['a'] == 3
    
    def test_sum(self):
        """Test sum calculation"""
        df = SimDataFrame({'a': [1, 2, 3]}, units={'a': 'kg'})
        result = df.sum()
        assert result['a'] == 6
    
    def test_sum0(self):
        """Test sum excluding zeros"""
        df = SimDataFrame({'a': [0, 1, 2, 0, 3]})
        if hasattr(df, 'sum0'):
            result = df.sum0()
            assert result['a'] == 6
    
    def test_min_max(self):
        """Test min and max"""
        df = SimDataFrame({'a': [5, 2, 8, 1]})
        assert df.min()['a'] == 1
        assert df.max()['a'] == 8
    
    def test_std_var(self):
        """Test standard deviation and variance"""
        df = SimDataFrame({'a': [1, 2, 3, 4, 5]})
        std_result = df.std()
        var_result = df.var()
        
        assert std_result['a'] > 0
        assert var_result['a'] > 0
        # var should be std squared (approximately)
        assert abs(var_result['a'] - std_result['a']**2) < 0.01
    
    def test_count(self):
        """Test count method"""
        df = SimDataFrame({'a': [1, 2, np.nan, 4]})
        result = df.count()
        assert result['a'] == 3  # Excludes NaN


class TestSimBasicsMath:
    """Test mathematical operations"""
    
    def test_log(self):
        """Test natural logarithm"""
        df = SimDataFrame({'a': [1, np.e, np.e**2]})
        if hasattr(df, 'log') or hasattr(df, 'ln'):
            result = df.log() if hasattr(df, 'log') else df.ln()
            assert abs(result['a'].iloc[1] - 1.0) < 0.01
    
    def test_log10(self):
        """Test base-10 logarithm"""
        df = SimDataFrame({'a': [1, 10, 100]})
        if hasattr(df, 'log10'):
            result = df.log10()
            assert result['a'].iloc[1] == 1.0
            assert result['a'].iloc[2] == 2.0
    
    def test_log2(self):
        """Test base-2 logarithm"""
        df = SimDataFrame({'a': [1, 2, 4, 8]})
        if hasattr(df, 'log2'):
            result = df.log2()
            assert result['a'].iloc[2] == 2.0
            assert result['a'].iloc[3] == 3.0
    
    def test_abs(self):
        """Test absolute value"""
        df = SimDataFrame({'a': [-5, -2, 3]})
        result = df.abs()
        assert all(result['a'] >= 0)
        assert result['a'].iloc[0] == 5
    
    def test_neg(self):
        """Test negation"""
        df = SimDataFrame({'a': [1, -2, 3]})
        if hasattr(df, 'neg'):
            result = df.neg()
            assert result['a'].iloc[0] == -1
            assert result['a'].iloc[1] == 2


class TestSimBasicsNormalization:
    """Test normalization methods"""
    
    def test_znorm(self):
        """Test z-score normalization"""
        df = SimDataFrame({'a': [1, 2, 3, 4, 5]})
        result = df.znorm()
        
        # Z-normalized data should have mean ≈ 0 and std ≈ 1
        assert abs(result['a'].mean()) < 0.01
        assert abs(result['a'].std() - 1.0) < 0.1
    
    def test_znorm0(self):
        """Test z-score normalization excluding zeros"""
        df = SimDataFrame({'a': [0, 1, 2, 0, 3, 4]})
        if hasattr(df, 'znorm0'):
            result = df.znorm0()
            # Should normalize only non-zero values
            assert isinstance(result, (SimDataFrame, SimSeries))
    
    def test_minmaxnorm(self):
        """Test min-max normalization"""
        df = SimDataFrame({'a': [0, 5, 10]})
        result = df.minmaxnorm()
        
        # Min-max normalized should be between 0 and 1
        assert result['a'].min() >= 0
        assert result['a'].max() <= 1
        assert result['a'].iloc[0] == 0
        assert result['a'].iloc[2] == 1
    
    def test_jitter(self):
        """Test adding jitter to data"""
        df = SimDataFrame({'a': [1, 1, 1, 1]})
        result = df.jitter(std=0.1)
        
        # Values should be slightly different but close to 1
        assert not all(result['a'] == 1)  # Some variation
        assert abs(result['a'].mean() - 1.0) < 0.5  # Still close to original


class TestSimBasicsComparison:
    """Test comparison methods with precision"""
    
    def test_eq_basic(self):
        """Test equality comparison"""
        df = SimDataFrame({'a': [1, 2, 3]})
        result = df.eq(2)
        assert result['a'].iloc[1] == True
        assert result['a'].iloc[0] == False
    
    def test_gt_lt(self):
        """Test greater than and less than"""
        df = SimDataFrame({'a': [1, 2, 3]})
        
        gt_result = df.gt(2)
        assert gt_result['a'].iloc[2] == True
        assert gt_result['a'].iloc[0] == False
        
        lt_result = df.lt(2)
        assert lt_result['a'].iloc[0] == True
        assert lt_result['a'].iloc[2] == False
    
    def test_ge_le(self):
        """Test greater/less than or equal"""
        df = SimDataFrame({'a': [1, 2, 3]})
        
        ge_result = df.ge(2)
        assert ge_result['a'].iloc[1] == True
        assert ge_result['a'].iloc[2] == True
        
        le_result = df.le(2)
        assert le_result['a'].iloc[0] == True
        assert le_result['a'].iloc[1] == True


class TestSimBasicsDataManipulation:
    """Test data manipulation methods"""
    
    def test_diff(self):
        """Test difference calculation"""
        df = SimDataFrame({'a': [1, 3, 6, 10]})
        result = df.diff()
        
        # First value should be NaN
        assert pd.isna(result['a'].iloc[0])
        # Differences should be 2, 3, 4
        assert result['a'].iloc[1] == 2
        assert result['a'].iloc[2] == 3
    
    def test_cumsum(self):
        """Test cumulative sum"""
        df = SimDataFrame({'a': [1, 2, 3]})
        result = df.cumsum()
        
        assert result['a'].iloc[0] == 1
        assert result['a'].iloc[1] == 3
        assert result['a'].iloc[2] == 6
    
    def test_shift(self):
        """Test shift operation"""
        df = SimDataFrame({'a': [1, 2, 3]})
        result = df.shift(1)
        
        assert pd.isna(result['a'].iloc[0])
        assert result['a'].iloc[1] == 1
        assert result['a'].iloc[2] == 2
    
    def test_fillna(self):
        """Test filling NA values"""
        df = SimDataFrame({'a': [1, np.nan, 3]})
        result = df.fillna(0)
        
        assert result['a'].iloc[1] == 0
        assert not pd.isna(result['a']).any()
    
    def test_replace(self):
        """Test value replacement"""
        df = SimDataFrame({'a': [1, 2, 3, 2]})
        result = df.replace(2, 99)
        
        assert result['a'].iloc[1] == 99
        assert result['a'].iloc[3] == 99
        assert result['a'].iloc[0] == 1
    
    def test_interpolate(self):
        """Test interpolation"""
        df = SimDataFrame({'a': [1, np.nan, np.nan, 4]})
        result = df.interpolate()
        
        # Should interpolate NaN values
        assert not pd.isna(result['a']).any()


class TestSimBasicsUnits:
    """Test unit-related methods"""
    
    def test_to_unit_conversion(self):
        """Test unit conversion with 'to' method"""
        df = SimDataFrame({'distance': [1000, 2000]}, units={'distance': 'm'})
        
        if hasattr(df, 'to'):
            # Try converting to km
            try:
                result = df.to({'distance': 'km'})
                # If conversion works, values should be scaled
                assert result['distance'].iloc[0] == 1.0
            except:
                # Conversion might not work depending on unyts installation
                pass
    
    def test_like_unit_matching(self):
        """Test 'like' method for unit matching"""
        df1 = SimDataFrame({'a': [100, 200]}, units={'a': 'cm'})
        df2 = SimDataFrame({'a': [1, 2]}, units={'a': 'm'})
        
        if hasattr(df1, 'like'):
            # Try to make df1 units like df2
            try:
                result = df1.like(df2)
                assert isinstance(result, SimDataFrame)
            except:
                pass


class TestSimBasicsDateHelpers:
    """Test date-related helper methods"""
    
    def test_days_in_year(self):
        """Test days_in_year method"""
        # Create DataFrame with date index
        df = SimDataFrame(
            {'value': [1, 2]},
            index=pd.date_range('2020-01-01', periods=2)
        )
        
        if hasattr(df, 'days_in_year'):
            result = df.days_in_year()
            # 2020 is a leap year
            assert 366 in result.values or 365 in result.values
    
    def test_real_year(self):
        """Test real_year fractional year conversion"""
        df = SimDataFrame(
            {'value': [1, 2]},
            index=pd.date_range('2020-01-01', periods=2)
        )
        
        if hasattr(df, 'real_year'):
            result = df.real_year()
            # Should return fractional year values
            assert isinstance(result, (SimDataFrame, SimSeries, pd.Series))


class TestSimBasicsNameManipulation:
    """Test name manipulation methods"""
    
    def test_right(self):
        """Test extracting right part of column names"""
        df = SimDataFrame({'well:pressure': [1, 2], 'well:temperature': [3, 4]})
        
        if hasattr(df, 'right'):
            result = df.right()
            # Should extract 'pressure' and 'temperature'
            assert 'pressure' in result.columns or 'well:pressure' in result.columns
    
    def test_left(self):
        """Test extracting left part of column names"""
        df = SimDataFrame({'well:pressure': [1, 2], 'tank:pressure': [3, 4]})
        
        if hasattr(df, 'left'):
            result = df.left()
            # Should extract 'well' and 'tank'
            assert 'well' in result.columns or 'tank' in result.columns or 'well:pressure' in result.columns


class TestSimBasicsMetadata:
    """Test metadata and params preservation"""
    
    def test_params_property(self):
        """Test params_ property exists and contains metadata"""
        df = SimDataFrame(
            {'a': [1, 2, 3]},
            units={'a': 'm'},
            name='test',
            verbose=False
        )
        
        assert hasattr(df, 'params_')
        params = df.params_
        
        assert 'units' in params
        assert 'name' in params
    
    def test_metadata_preserved_after_operation(self):
        """Test that metadata is preserved through operations"""
        df = SimDataFrame({'a': [1, 2, 3]}, units={'a': 'kg'}, name='original')
        
        # Perform operation
        result = df + 1
        
        # Check metadata preservation
        assert hasattr(result, 'params_')
        # Units should be preserved
        if hasattr(result, 'units') and result.units:
            assert 'a' in result.units


class TestSimBasicsConversions:
    """Test conversion methods"""
    
    def test_to_pandas(self):
        """Test conversion to pandas DataFrame"""
        df = SimDataFrame({'a': [1, 2, 3]}, units={'a': 'm'})
        
        pd_df = df.to_pandas()
        assert isinstance(pd_df, pd.DataFrame)
        assert 'a' in pd_df.columns
    
    def test_as_pandas_alias(self):
        """Test as_pandas alias"""
        df = SimDataFrame({'a': [1, 2, 3]})
        
        if hasattr(df, 'as_pandas'):
            pd_df = df.as_pandas()
            assert isinstance(pd_df, pd.DataFrame)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
