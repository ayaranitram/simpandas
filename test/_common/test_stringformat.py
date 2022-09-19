# -*- coding: utf-8 -*-
"""
Created on Mon Sep 19 22:08:26 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

from simpandas._common.stringformat import multisplit, isnumeric, getnumber, isDate, splitDMMMY, date
from simpandas._classes.errors import UndefinedDateFormatError

def test_multisplit():
    assert multisplit('a b cd') == ['a', 'b', 'cd']
    assert multisplit('a+b*cd', sep=['+','*']) == ['a', '+', 'b', '*', 'cd']
    assert multisplit('a+b*cd', sep=['+','*'], remove=['+', '*']) == ['a', 'b', 'cd']
    assert multisplit('a+b+-cd', sep=['+','+-']) == ['a', '+', 'b', '+-', 'cd']

def test_isnumeric():
    assert isnumeric(1) is True
    assert isnumeric('-1') is True
    assert isnumeric('3.5') is True
    assert isnumeric('7E2') is True
    assert isnumeric('-7.3E-2') is True
    assert isnumeric('A') is False

def test_isDate():
    assert isDate('01-07-2015') is True
    assert isDate('28-07-2015') is True
    assert isDate('07-28-2015') is True
    assert isDate('2015-07-28') is True
    assert isDate('2015-28-07') is True
    assert isDate('20150728') is True
    assert isDate('01-07-2015', returnFormat=True) == 'DD-MM-YYYY'
    assert isDate('28-07-2015', returnFormat=True) == 'DD-MM-YYYY'
    assert isDate('07-28-2015', returnFormat=True) == 'MM-DD-YYYY'
    assert isDate('2015-07-28', returnFormat=True) == 'YYYY-MM-DD'
    # assert isDate('2015-28-07', returnFormat=True) == 'YYYY-DD-MM'
    assert isDate('20150728', returnFormat=True) == 'YYYYMMDD'
    assert isDate('01-JUL-2015', returnFormat=True) == 'DD-MMM-YYYY'
    assert isDate('28-JUL-2015', returnFormat=True) == 'DD-MMM-YYYY'
    assert isDate('JUL-28-2015', returnFormat=True) == 'MMM-DD-YYYY'
    assert isDate('2015-JUL-28', returnFormat=True) == 'YYYY-MMM-DD'
    # assert isDate('2015-28-JUL', returnFormat=True) == 'YYYY-DD-MM'
    assert isDate('01 JUL 2015', returnFormat=True) == 'DD MMM YYYY'
    assert isDate('01/JUL/2015', returnFormat=True) == 'DD/MMM/YYYY'

def test_splitDMMMY():
    assert splitDMMMY('28JUL2022') == ['28', 'JUL', '2022']

def test_date():
    assert date('2022-09-19') == '19-SEP-2022'
    try:
        assert date('2022-05-09')
    except UndefinedDateFormatError:
        pass
    assert date('2022-05-09', formatIN='YYYY-MM-DD') == '09-MAY-2022'
    assert date(['2022-01-01', '2022-01-05', '2022-01-10', '2022-01-15']) == ['01-JAN-2022', '05-JAN-2022', '10-JAN-2022', '15-JAN-2022']