# -*- coding: utf-8 -*-
"""
Backward compatibility shim for the old 'writters' typo

This module provides backward compatibility for code that imported from
simpandas.writters (old typo). All imports are forwarded to the new
simpandas.writers module.

DEPRECATED: This module is deprecated and will be removed in a future version.
Please update your imports from 'simpandas.writters' to 'simpandas.writers'.

Created on March 3, 2026
@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

import warnings
import sys

# Issue deprecation warning
warnings.warn(
    "Importing from 'simpandas.writters' is deprecated due to a spelling error. "
    "Please update your imports to use 'simpandas.writers' instead. "
    "The 'writters' compatibility module will be removed in version 1.0.0.",
    DeprecationWarning,
    stacklevel=2
)

# Import the actual writers module and re-export everything
from simpandas import writers

# Make this module act as a facade to writers
sys.modules[__name__] = writers
