# -*- coding: utf-8 -*-
"""
Created on Wed May 13 00:46:05 2020

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.4.1'
__release__ = 20220523
__all__ = ['melt', 'pivot']

import pandas
import numpy
from simpandas.frame import SimDataFrame
from simpandas.series import SimSeries
from simpandas.common.helpers import main_key as _main_key, item_key as _item_key


def melt(df, hue='--auto', label='--auto', SimObject=None, full_output=False, **kwargs):
    """
        common procedure to melt and rename the dataframe
        """
    if type(df) in [SimSeries, SimDataFrame]:
        SimDF = True
        unitsdict = df.get_units().copy()
        units = lambda col: unitsdict[col] if col in unitsdict else None
        df = df.df
    else:
        SimDF = False

    for key in ['hue', 'label', 'SimObject', 'FullOutput']:
        kwargs.pop(key, None)
    if 'var_name' in kwargs:
        var_name = kwargs['var_name']
    else:
        var_name = 'SDFvariable'
    if 'value_name' in kwargs:
        value_name = kwargs['value_name']
    else:
        value_name = 'value'

    df = df.melt(var_name=var_name, value_name=value_name, ignore_index=False)
    df['attribute'] = _main_key(list(df[var_name]), False)
    df['item'] = _item_key(list(df[var_name]), False)

    if hue == 'main':
        hue = 'attribute'
    if label == 'main':
        label = 'attribute'

    itemLabel = 'item'
    values = value_name  # 'value' before

    if len(set([i[0] for i in _main_key(list(df[var_name]))])) == 1:
        itemLabel = list(set(_main_key(list(df[var_name]))))[0][0].upper()
        if itemLabel == 'W':
            itemLabel = 'well'
        elif itemLabel == 'R':
            itemLabel = 'region'
        elif itemLabel == 'G':
            itemLabel = 'group'
        else:
            itemLabel = 'item'

    if hasattr(SimObject, 'get_plotUnits'):
        unitsLabel = ' [' + SimObject.get_plotUnits(_main_key(list(df[var_name]))[0]) + ']'
    else:
        unitsLabel = ''

    if hue == '--auto' and label == '--auto':
        if len(_main_key(list(df[var_name]))) == 1 and len(_item_key(list(df[var_name]))) == 1:
            hue = None
            label = itemLabel
            newLabel = _main_key(list(df[var_name]))[0] + unitsLabel
            df = df.rename(columns={value_name: newLabel})  # value_name was 'value' before
            values = newLabel
        elif len(_main_key(list(df[var_name]))) == 1 and len(_item_key(list(df[var_name]))) > 1:
            hue = None
            label = itemLabel
            newLabel = _main_key(list(df[var_name]))[0] + unitsLabel
            df = df.rename(columns={value_name: newLabel})  # value_name was 'value' before
            values = newLabel
        elif len(_main_key(list(df[var_name]))) > 1 and len(_item_key(list(df[var_name]))) == 1:
            hue = itemLabel  # None
            label = 'attribute'
            # values = _itemKey( list(df[var_name]) )[0]
            # df = df.rename(columns={'value':values})
        elif len(_main_key(list(df[var_name]))) > len(_item_key(list(df[var_name]))):
            hue = itemLabel  # 'item'
            label = 'attribute'
        elif len(_main_key(list(df[var_name]))) < len(_item_key(list(df[var_name]))):
            hue = 'attribute'
            label = itemLabel  # 'item'
        else:
            hue = 'attribute'
            label = itemLabel  # 'item'

    else:
        if hue == '--auto':
            if len(_main_key(list(df[var_name]))) == 1 and len(_item_key(list(df[var_name]))) == 1:
                hue = None
                # newLabel = _mainKey( list(df[var_name]) )[0] + ' [' + self.get_plotUnits(_mainKey( list(df[var_name]) )[0]) + ']'
                # df = df.rename(columns={'value':newLabel})
                # values = newLabel
            elif len(_main_key(list(df[var_name]))) == 1 and len(_item_key(list(df[var_name]))) > 1:
                hue = None
                # newLabel = _mainKey( list(df[var_name]) )[0] + ' [' + self.get_plotUnits(_mainKey( list(df[var_name]) )[0]) + ']'
                # df = df.rename(columns={'value':newLabel})
                # values = newLabel
            elif len(_main_key(list(df[var_name]))) > 1 and len(_item_key(list(df[var_name]))) == 1:
                hue = None
            elif len(_main_key(list(df[var_name]))) > len(_item_key(list(df[var_name]))):
                hue = itemLabel if label != itemLabel else 'attribute'
            elif len(_main_key(list(df[var_name]))) < len(_item_key(list(df[var_name]))):
                hue = 'attribute' if label != 'attribute' else itemLabel
            else:
                hue = 'attribute' if label != 'attribute' else itemLabel
        else:
            if hue == 'item':
                hue = itemLabel
            elif hue == 'main':
                hue = 'attribute'

        if label == '--auto':
            if len(_main_key(list(df[var_name]))) == 1 and len(_item_key(list(df[var_name]))) == 1:
                label = None
                # newLabel = _mainKey( list(df[var_name]) )[0] + ' [' + self.get_plotUnits(_mainKey( list(df[var_name]) )[0]) + ']'
                # df = df.rename(columns={'value':newLabel})
                # values = newLabel
            elif len(_main_key(list(df[var_name]))) == 1 and len(_item_key(list(df[var_name]))) > 1:
                label = itemLabel
                # newLabel = _mainKey( list(df[var_name]) )[0] + ' [' + self.get_plotUnits(_mainKey( list(df[var_name]) )[0]) + ']'
                # df = df.rename(columns={'value':newLabel})
                # values = newLabel
            elif len(_main_key(list(df[var_name]))) > 1 and len(_item_key(list(df[var_name]))) == 1:
                label = 'attribute' if hue != 'attribute' else itemLabel
            elif len(_main_key(list(df[var_name]))) > len(_item_key(list(df[var_name]))):
                label = 'attribute' if hue != 'attribute' else itemLabel
            elif len(_main_key(list(df[var_name]))) < len(_item_key(list(df[var_name]))):
                label = itemLabel if hue != itemLabel else 'attribute'
            else:
                label = itemLabel if hue != itemLabel else 'attribute'
        else:
            if label == 'item':
                label = itemLabel
            elif label == 'main':
                label = 'attribute'

    # generate values for units columns
    if SimDF:
        unitsCol = [units(df[var_name].iloc[i]) for i in range(len(df))]

    if var_name == 'SDFvariable':
        df = df.drop(columns=var_name)
    df = df.rename(columns={'item': itemLabel})

    if full_output:
        return hue, label, itemLabel, values, df
    elif SimDF:
        df['units'] = unitsCol
        return df
    else:
        return df


def pivot(df, item=None, index=None, values=None, nameSeparator=':'):
    """
    Procedure to convert a long table to wide table (pivot) integrating the data from
    the item column into the column names.

    Parameters
    ----------
    df : DataFrame
        DESCRIPTION.
    item : str, optional
        The column name that contains the item (i.e. wells) names.
        If not will try to guess from the object columns in the dataframe
    index : str, optional
        The column to be used as index in the pivoted table.
        If None will use the first datetime column or column labeled 'time'.
    values : str or list of str, optional
        The columns to be pivoted.
        The default is all the columns but index and item columns.
    nameSeparator : str, optional
        The string to be used separator in the new concatenated column names.
        New column names will be:
            original_column_name:item_name
        The default is ':'.

    Raises
    ------
    TypeError
        If not able to guess item or index columns.

    Returns
    -------
    newdf : DataFrame
        The pivoted DataFrame.

    """
    resetIndex = False
    if index is None:
        resetIndex = True
        for col in df:
            if 'date' in str(df[col].dtype):
                index = col
                break
    if index is None:
        for col in df:
            if str(col).upper().strip() == 'TIME' and ('int' in str(df[col].dtype) or 'float' in str(df[col].dtype)):
                index = col
                break
    if index is None:
        raise TypeError("Not able to find a column to be used as index, please provide 'index' parameter.")
    else:
        print(" >>> Identified column '" + str(index) + "' as index to pivot. <<<")
        newindex = pandas.Index(numpy.sort(df[index].squeeze().unique()))
    if item is None:
        candidate = None
        for col in df:
            if 'object' == str(df[col].dtype):
                if candidate is None:
                    candidate = (col, len(df[col].squeeze().unique()))
                elif len(df[col].squeeze().unique()) < candidate[1]:
                    candidate = (col, len(df[col].squeeze().unique()))
        if candidate is not None:
            item = candidate[0]
            print(" >>> Identified column '" + str(item) + "' as item to pivot. <<<")
        else:
            raise TypeError("Not able to find a column to be used as item, please provide 'item' parameter.")

    names = {col[0] if type(col) is tuple else col: col for col in df.columns}
    if item not in names:
        names[item] = item
    if index not in names:
        names[index] = index
    if values is None:
        values = [cols for cols in df.columns if cols != names[item]] if index is None else [cols for cols in df.columns
                                                                                             if cols != names[
                                                                                                 item] and cols !=
                                                                                             names[index]]
    elif isinstance(values, str):
        values = [values]

    newdf = pandas.DataFrame(index=newindex)
    for ite in df[item].squeeze().unique():
        for col in values:
            newdf[(str(col[0]) + ':' + str(ite),) + col[1:] if type(col) is tuple else str(col) + ':' + str(ite)] = \
                df[df[names[item]] == ite].set_index(names[index])[col]

    if resetIndex:
        newdf = newdf.reset_index()
    return newdf
