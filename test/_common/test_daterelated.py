# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 18:24:20 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas._common.daterelated import daysInYear, daysInMonth
from pandas import to_datetime
import datetime as dt
import numpy as np

def test_daysInYear():
    assert daysInYear(2022) == 365
    assert daysInYear(2023) == 365
    assert daysInYear(2024) == 366
    assert np.array_equal(daysInYear([2022, 2023, 2024]), np.array([365, 365, 366]))
    assert daysInYear(to_datetime('2023-12-31')) == 365
    assert daysInYear(to_datetime('2023-05-03')) == 365
    assert daysInYear(to_datetime('2024-12-31')) == 366
    assert daysInYear(to_datetime('2024-05-03')) == 366
    assert np.array_equal(daysInYear(to_datetime(['2023-01-01', '2024-05-03'])), np.array([365, 366]))
    assert daysInYear(dt.date(2023, 5, 3)) == 365
    assert daysInYear(dt.date(2024, 12, 31)) == 366
    assert daysInYear(dt.datetime(2024, 8, 15, 12, 53, 26)) == 366