import pytest
from simpandas.common.helpers import (clean_axis, string_new_name, type_of_frame,
                                       main_key, item_key, hashable)
from simpandas import SimDataFrame, SimSeries
import pandas as pd

def test_clean_axis():
    assert clean_axis() == 0
    assert clean_axis('cols') == 1
    assert clean_axis('rows&cols') == 2
    assert clean_axis(True) == 1

def test_string_new_name():
    assert string_new_name({'a':1}) == 1
    assert string_new_name({'a':1,'b':2}) == '1∩2'

def test_type_of_frame():
    assert type_of_frame(pd.DataFrame()) is pd.DataFrame
    assert type_of_frame(SimDataFrame({'a':[1]})) is SimDataFrame
    assert type_of_frame(SimSeries([1,2,3])) is SimSeries
    with pytest.raises(TypeError):
        type_of_frame(123)

def test_main_item_key():
    assert main_key('A:B') == 'A'
    assert item_key('A:B') == 'B'
    assert main_key(['A:B','C:D']) == ['A','C']
    assert item_key(['A:B','C:D']) == ['B','D']

def test_hashable():
    assert hashable(1)
    assert not hashable({})
