"""
Created on Wed May 13 15:14:35 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.0.3'
__release__ = 20221116
__all__ = []


class OverwrittingError(Exception):
    pass


class UndefinedDateFormatError(Exception):
    pass


class MissingDependenceError(Exception):
    pass


class InvalidKeyError(Exception):
    pass


class CorruptedFileError(Exception):
    pass