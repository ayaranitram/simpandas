#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 16 18:25:41 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.81.1'
__release__ = 20230115
__all__ = ['left', 'right', 'rename_left', 'rename_right', 'common_rename']

import warnings

def right(series_or_frame, name_separator=None):
    if not hasattr(series_or_frame, 'name_separator') or series_or_frame.name_separator in [None, False, '']:
        if name_separator is None:
            return {col: col for col in series_or_frame.columns} if hasattr(series_or_frame, 'columns') else {series_or_frame.name: series_or_frame.name}
    if name_separator is None and series_or_frame.name_separator not in [None, False, '']:
        name_separator = series_or_frame.name_separator
    if not hasattr(series_or_frame, 'columns'):
        new_names = {series_or_frame.name: str(series_or_frame.name).split(name_separator)[-1]}
    else:
        new_names = {each: str(each).split(name_separator)[-1] for each in series_or_frame.columns if each is not None}
    return new_names


def left(series_or_frame, name_separator=None):
    if not hasattr(series_or_frame, 'name_separator') or series_or_frame.name_separator in [None, False, '']:
        if name_separator is None:
            return {col: col for col in series_or_frame.columns} if hasattr(series_or_frame, 'columns') else {series_or_frame.name: series_or_frame.name}
    if name_separator is None and series_or_frame.name_separator not in [None, False, '']:
        name_separator = series_or_frame.name_separator
    if not hasattr(series_or_frame, 'columns'):
        new_names = {series_or_frame.name: str(series_or_frame.name).split(name_separator)[0]}
    else:
        new_names = {each: str(each).split(name_separator)[0] for each in series_or_frame.columns if each is not None}
    return new_names


def rename_right(series_or_frame, name_separator=None):
    if not hasattr(series_or_frame, 'name_separator') or series_or_frame.name_separator in [None, False, '']:
        if name_separator is None:
            return series_or_frame
    new_names = right(series_or_frame, name_separator=name_separator)
    if not hasattr(series_or_frame, 'columns'):
        return series_or_frame.rename(list(new_names.values())[0])
    return series_or_frame.rename(columns=new_names, inplace=False)


def rename_left(series_or_frame, name_separator=None):
    if not hasattr(series_or_frame, 'nameSeparator') or series_or_frame.name_separator in [None, False, '']:
        if name_separator is None:
            return series_or_frame
    new_names = left(series_or_frame, name_separator=name_separator)
    if not hasattr(series_or_frame, 'columns'):
        return series_or_frame.rename(list(new_names.values())[0])
    return series_or_frame.rename(columns=new_names, inplace=False)


def common_rename(series_or_frame_1, series_or_frame_2, *,
                  left_right=None,
                  intersection_character=None,
                  name_separator_1=None,
                  name_separator_2=None,
                  complex_names=False,
                  return_names_dict_only=False):
    def not_possible():
        # warnings.warn(Warning("No possible to found common name."))
        if sum(types) == 0:  # common naming for both Series or SimSeries
            if series_or_frame_1.name is not None and series_or_frame_2.name is not None:
                new_name = {None: str(series_or_frame_1.name) + intersection_character + str(series_or_frame_2.name)}
            else:
                new_name = series_or_frame_1.name if series_or_frame_1.name is not None else series_or_frame_2.name if series_or_frame_2.name is not None else None
                new_name = {new_name: new_name}
        else:
            new_name = {}
        if return_names_dict_only:
            return new_name
        else:
            return series_or_frame_1, series_or_frame_2, new_name
    
    # identify type of input objects
    if hasattr(series_or_frame_1, 'type'):
        if series_or_frame_1.type == 'SimSeries':
            types = [0]
        else:
            types = [1]
    elif hasattr(series_or_frame_1, 'columns'):
        types = [1]
    else:
        types = [0]
    if hasattr(series_or_frame_2, 'type'):
        if series_or_frame_2.type == 'SimSeries':
            types += [0]
        else:
            types += [1]
    elif hasattr(series_or_frame_2, 'columns'):
        types += [1]
    else:
        types += [0]

    # check input parameters
    if intersection_character is None:
        if hasattr(series_or_frame_1, 'intersection_character'):
            intersection_character = series_or_frame_1.intersection_character
        elif hasattr(series_or_frame_2, 'intersectionCharacter'):
            intersection_character = series_or_frame_2.intersection_character
        else:
            intersection_character = '&'
    else:
        intersection_character = str(intersection_character)

    if left_right is not None:
        if type(left_right) is not str or len(left_right.strip()) == 0:
            raise TypeError("`left_right` parameter must be a string 'left' or 'right', or simply 'l' or 'r'.")
        left_right = left_right.lower().strip()[0]
        if left_right[0] not in 'lr':
            raise ValueError("`left_right` parameter must 'left' or 'right', or simply 'l' or 'r'.")

    common_name_separator = None
    if name_separator_1 is None or len(name_separator_1) == 0:
        if hasattr(series_or_frame_1, 'name_separator'):
            name_separator_1 = str(series_or_frame_1.name_separator)
            common_name_separator = name_separator_1
        else:
            raise ValueError("`name_separator_1` must be a not empty string.")
    else:
        common_name_separator = name_separator_1
    if name_separator_2 is None or len(name_separator_2) == 0:
        if hasattr(series_or_frame_2, 'name_separator'):
            name_separator_2 = str(series_or_frame_2.name_separator)
            if name_separator_1 is None:
                common_name_separator = name_separator_2
        else:
            raise ValueError("`name_separator_2` must be a not empty string.")
    elif name_separator_1 is None:
        common_name_separator = name_separator_2
    if common_name_separator is None:
        raise ValueError("`name_separator_1` and `name_separator_2` must be not empty string.")

    complex_names = bool(complex_names)
    return_names_dict_only = bool(return_names_dict_only)

    if left_right is None and \
            (len(set(left(series_or_frame_1, name_separator_1).values())) > 1 and
            len(set(left(series_or_frame_2, name_separator_2).values())) > 1) and \
            (len(set(right(series_or_frame_1, name_separator_1).values())) > 1 and
            len(set(right(series_or_frame_2, name_separator_2).values())) > 1):
        return not_possible()

    elif left_right == 'l' or (
            left_right is None and
            len(set(left(series_or_frame_1, name_separator_1).values())) == 1 and
            len(set(left(series_or_frame_2, name_separator_2).values())) == 1):

        series_or_frame_1_right = list(set(right(series_or_frame_1, name_separator_1).values()))
        series_or_frame_2_right = list(set(right(series_or_frame_2, name_separator_2).values()))

        series_or_frame_1_left = str(list(left(series_or_frame_1, name_separator_1).values())[0])
        series_or_frame_2_left = str(list(left(series_or_frame_2, name_separator_2).values())[0])

        # common_names = {}
        # for col in series_or_frame_1_right:
        #     if col in series_or_frame_2_right:
        #         common_names[col] = series_or_frame_1_left + intersection_character + series_or_frame_2_left + common_name_separator + str(col)
        #     else:
        #         common_names[col] = series_or_frame_1_left + common_name_separator + str(col)
        # for col in series_or_frame_2_right:
        #     if col not in series_or_frame_1_right:
        #         common_names[col] = series_or_frame_2_left + common_name_separator + str(col)
        common_names = {col: (series_or_frame_1_left + intersection_character + series_or_frame_2_left + common_name_separator + str(col))
                        if col in series_or_frame_2_right else
                        series_or_frame_1_left + common_name_separator + str(col)
                        for col in series_or_frame_1_right}
        common_names.update({col: (series_or_frame_2_left + common_name_separator + str(col)) 
                             for col in series_or_frame_2_right
                             if col not in series_or_frame_1_right})

        if left_right is None and len(common_names) > 1:
            alternative = common_rename(series_or_frame_1,
                                        series_or_frame_2,
                                        left_right='right',
                                        intersection_character=intersection_character,
                                        name_separator_1=name_separator_1,
                                        name_separator_2=name_separator_2,
                                        complex_names=False,
                                        return_names_dict_only=True)
            if len(alternative) < len(common_names):
                return common_rename(series_or_frame_1,
                                     series_or_frame_2,
                                     left_right='right',
                                     intersection_character=intersection_character,
                                     name_separator_1=name_separator_1,
                                     name_separator_2=name_separator_2,
                                     complex_names=complex_names,
                                     return_names_dict_only=return_names_dict_only)
            else:
                renamer = rename_right
        else:
            renamer = rename_right

    elif left_right == 'r' or (
            left_right is None and
            len(set(right(series_or_frame_1, name_separator_1).values())) == 1 and
            len(set(right(series_or_frame_2, name_separator_2).values())) == 1):

        series_or_frame_1_left = list(set(left(series_or_frame_1, name_separator_1).values()))
        series_or_frame_2_left = list(set(left(series_or_frame_2, name_separator_2).values()))

        series_or_frame_1_right = str(list(right(series_or_frame_1, name_separator_1).values())[0])
        series_or_frame_2_right = str(list(right(series_or_frame_2, name_separator_2).values())[0])

        # common_names = {}
        # for col in series_or_frame_1_left:
        #     if col in series_or_frame_2_left:
        #         common_names[col] = str(col) + common_name_separator + series_or_frame_1_right + intersection_character + series_or_frame_2_right
        #     else:
        #         common_names[col] = str(col) + common_name_separator + series_or_frame_1_right
        # for col in series_or_frame_2_left:
        #     if col not in series_or_frame_1_left:
        #         common_names[col] = str(col) + common_name_separator + series_or_frame_2_right
        common_names = {col: (str(col) + common_name_separator + series_or_frame_1_right + intersection_character + series_or_frame_2_right)
                        if col in series_or_frame_2_left else
                        str(col) + common_name_separator + series_or_frame_1_right
                        for col in series_or_frame_1_left}
        common_names.update({col: (str(col) + common_name_separator + series_or_frame_2_right) 
                             for col in series_or_frame_2_left
                             if col not in series_or_frame_1_left})

        if left_right is None and len(common_names) > 1:
            alternative = common_rename(series_or_frame_1,
                                        series_or_frame_2,
                                        left_right='left',
                                        intersection_character=intersection_character,
                                        name_separator_1=name_separator_1,
                                        name_separator_2=name_separator_2,
                                        complex_names=False,
                                        return_names_dict_only=True)
            if len(alternative) < len(common_names):
                return common_rename(series_or_frame_1,
                                     series_or_frame_2,
                                     left_right='left',
                                     intersection_character=intersection_character,
                                     name_separator_1=name_separator_1,
                                     name_separator_2=name_separator_2,
                                     complex_names=complex_names,
                                     return_names_dict_only=return_names_dict_only)
            else:
                renamer = rename_left
        else:
            renamer = rename_left
    else:
        return not_possible()

    # check if proposed names are not repetitions of original names
    # for name in common_names:
    #     if type(common_name_separator) is str and len(common_name_separator) > 0 and common_name_separator in common_names[name]:
    #         if common_names[name].split(common_name_separator)[0] == common_names[name].split(common_name_separator)[1] and common_names[name].split(common_name_separator)[0] == name:
    #             common_names[name] = name
    common_names.update({name: name
                         for name in common_names
                         if type(common_name_separator) is str and len(common_name_separator) > 0 and common_name_separator in common_names[name] and \
                             common_names[name].split(common_name_separator)[0] == common_names[name].split(common_name_separator)[1] and common_names[name].split(common_name_separator)[0] == name
        })

    if return_names_dict_only:
        return common_names
    elif complex_names:
        out1 = renamer(series_or_frame_1)
        if hasattr(series_or_frame_1, 'columns'):
            out1 = out1.rename(columns=common_names)
        else:
            out1 = out1.rename(list(common_names.values())[0])
        out2 = renamer(series_or_frame_2)
        if hasattr(series_or_frame_2, 'columns'):
            out2 = out2.rename(columns=common_names)
        else:
            out2 = out2.rename(list(common_names.values())[0])
    else:
        out1 = renamer(series_or_frame_1, name_separator=name_separator_1)
        out2 = renamer(series_or_frame_2, name_separator=name_separator_2)
    return out1, out2, common_names
