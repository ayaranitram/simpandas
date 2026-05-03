"""
Created on Wed May 13 15:14:35 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.0.4'
__release__ = 20260503
__all__ = []


class OverwrittingError(Exception):
    """Raised when an operation would overwrite protected data or metadata."""
    pass


class UndefinedDateFormatError(Exception):
    """Raised when a date string cannot be matched to a supported format."""
    pass


class MissingDependenceError(Exception):
    """Raised when an optional third-party dependency is required but unavailable."""
    pass


class InvalidKeyError(Exception):
    """Raised when a key expression cannot be resolved against the target object."""
    pass


class CorruptedFileError(Exception):
    """Raised when an input file is malformed or structurally inconsistent."""
    pass
