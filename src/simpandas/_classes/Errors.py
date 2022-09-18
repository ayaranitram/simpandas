"""
Created on Wed May 13 15:14:35 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.0.2'
__release = 20220919
__all__ = []


class OverwrittingError(Exception):
    pass


class UndefinedDateFormatError(Exception):
    pass


# PrototypeError class to recognize the class from cwrap
try :
    from cwrap import PrototypeError
except ModuleNotFoundError :
    print("\n WARNING: missing 'cwrap' module, will not be able to load eclipse style simulation outputs.\n         Please intall it using pip command:\n           pip install cwrap\n\n       or upgrade:\n\n          pip install cwrap --upgrade\n        or intall libecl using pip command:\n           pip install libecl\n\n       or upgrade:\n\n          pip install libecl --upgrade" )


class MissingDependenceError(Exception):
    pass


class InvalidKeyError(Exception):
    pass

class CorruptedFileError(Exception):
    pass