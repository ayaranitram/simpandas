# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 18:24:20 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas.common.daterelated import daysInYear, daysInMonth, realYear
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

def test_daysInMonth():
    for m, d in {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}.items():
        assert daysInMonth(m) == d
        assert daysInMonth(m, 2023) == d
        assert daysInMonth(m, 2024) == d if m != 2 else 29
        assert daysInMonth(dt.date(2023, m, 1)) == d
        assert daysInMonth(dt.date(2024, m, 1)) == d if m != 2 else 29
        assert daysInMonth(to_datetime('2023-' + str(m).zfill(2) + '-01')) == d
        assert daysInMonth(to_datetime('2024-' + str(m).zfill(2) + '-01')) == d if m != 2 else 29
    assert daysInMonth('JAN') == 31
    assert daysInMonth('FEB') == 28
    assert daysInMonth('MAR') == 31
    assert daysInMonth('APR') == 30
    assert daysInMonth('MAY') == 31
    assert daysInMonth('JUN') == 30
    assert daysInMonth('JUL') == 31
    assert daysInMonth('AUG') == 31
    assert daysInMonth('SEP') == 30
    assert daysInMonth('OCT') == 31
    assert daysInMonth('NOV') == 30
    assert daysInMonth('DEC') == 31

def test_realYear():
    assert realYear(dt.date(2022, 1, 1)) == 2022.0
    assert realYear(dt.date(2022, 12, 31)) == 2022 + 364/365
    assert realYear(dt.date(2024, 3, 15)) == 2024.0 + (31+29+15-1)/366
    assert realYear(dt.date(2023, 3, 1)) == 2023.0 + (31+28)/365