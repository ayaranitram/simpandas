# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 18:24:20 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas.common.daterelated import days_in_year, days_in_month, real_year
from pandas import to_datetime
import datetime as dt
import numpy as np

def test_daysInYear():
    assert days_in_year(2022) == 365
    assert days_in_year(2023) == 365
    assert days_in_year(2024) == 366
    assert np.array_equal(days_in_year([2022, 2023, 2024]), np.array([365, 365, 366]))
    assert days_in_year(to_datetime('2023-12-31')) == 365
    assert days_in_year(to_datetime('2023-05-03')) == 365
    assert days_in_year(to_datetime('2024-12-31')) == 366
    assert days_in_year(to_datetime('2024-05-03')) == 366
    assert np.array_equal(days_in_year(to_datetime(['2023-01-01', '2024-05-03'])), np.array([365, 366]))
    assert days_in_year(dt.date(2023, 5, 3)) == 365
    assert days_in_year(dt.date(2024, 12, 31)) == 366
    assert days_in_year(dt.datetime(2024, 8, 15, 12, 53, 26)) == 366

def test_daysInMonth():
    for m, d in {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}.items():
        assert days_in_month(m) == d
        assert days_in_month(m, 2023) == d
        assert days_in_month(m, 2024) == d if m != 2 else 29
        assert days_in_month(dt.date(2023, m, 1)) == d
        assert days_in_month(dt.date(2024, m, 1)) == d if m != 2 else 29
        assert days_in_month(to_datetime('2023-' + str(m).zfill(2) + '-01')) == d
        assert days_in_month(to_datetime('2024-' + str(m).zfill(2) + '-01')) == d if m != 2 else 29
    assert days_in_month('JAN') == 31
    assert days_in_month('FEB') == 28
    assert days_in_month('MAR') == 31
    assert days_in_month('APR') == 30
    assert days_in_month('MAY') == 31
    assert days_in_month('JUN') == 30
    assert days_in_month('JUL') == 31
    assert days_in_month('AUG') == 31
    assert days_in_month('SEP') == 30
    assert days_in_month('OCT') == 31
    assert days_in_month('NOV') == 30
    assert days_in_month('DEC') == 31

def test_realYear():
    assert real_year(dt.date(2022, 1, 1)) == 2022.0
    assert real_year(dt.date(2022, 12, 31)) == 2022 + 364 / 365
    assert real_year(dt.date(2024, 3, 15)) == 2024.0 + (31 + 29 + 15 - 1) / 366
    assert real_year(dt.date(2023, 3, 1)) == 2023.0 + (31 + 28) / 365