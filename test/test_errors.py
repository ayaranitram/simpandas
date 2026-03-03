# -*- coding: utf-8 -*-
"""
Tests for custom exception classes in simpandas.errors

Created on March 3, 2026
@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import pytest
from simpandas.errors import (
    OverwrittingError,
    UndefinedDateFormatError,
    MissingDependenceError,
    InvalidKeyError,
    CorruptedFileError
)


class TestCustomExceptions:
    """Test custom exception classes"""
    
    def test_overwriting_error(self):
        """Test OverwrittingError can be raised and caught"""
        with pytest.raises(OverwrittingError) as excinfo:
            raise OverwrittingError("Cannot overwrite existing data")
        assert "Cannot overwrite existing data" in str(excinfo.value)
    
    def test_undefined_date_format_error(self):
        """Test UndefinedDateFormatError can be raised and caught"""
        with pytest.raises(UndefinedDateFormatError) as excinfo:
            raise UndefinedDateFormatError("Date format not recognized")
        assert "Date format not recognized" in str(excinfo.value)
    
    def test_missing_dependence_error(self):
        """Test MissingDependenceError can be raised and caught"""
        with pytest.raises(MissingDependenceError) as excinfo:
            raise MissingDependenceError("Required package not found")
        assert "Required package not found" in str(excinfo.value)
    
    def test_invalid_key_error(self):
        """Test InvalidKeyError can be raised and caught"""
        with pytest.raises(InvalidKeyError) as excinfo:
            raise InvalidKeyError("Key 'invalid_key' not found in DataFrame")
        assert "invalid_key" in str(excinfo.value)
    
    def test_corrupted_file_error(self):
        """Test CorruptedFileError can be raised and caught"""
        with pytest.raises(CorruptedFileError) as excinfo:
            raise CorruptedFileError("File appears to be corrupted")
        assert "corrupted" in str(excinfo.value).lower()
    
    def test_all_exceptions_are_exceptions(self):
        """Test that all custom exceptions inherit from Exception"""
        assert issubclass(OverwrittingError, Exception)
        assert issubclass(UndefinedDateFormatError, Exception)
        assert issubclass(MissingDependenceError, Exception)
        assert issubclass(InvalidKeyError, Exception)
        assert issubclass(CorruptedFileError, Exception)
    
    def test_exceptions_without_message(self):
        """Test that exceptions can be raised without a message"""
        with pytest.raises(OverwrittingError):
            raise OverwrittingError()
        
        with pytest.raises(UndefinedDateFormatError):
            raise UndefinedDateFormatError()
        
        with pytest.raises(MissingDependenceError):
            raise MissingDependenceError()
        
        with pytest.raises(InvalidKeyError):
            raise InvalidKeyError()
        
        with pytest.raises(CorruptedFileError):
            raise CorruptedFileError()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
