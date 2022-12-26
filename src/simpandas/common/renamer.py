#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 16 18:25:41 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.80.7'
__release__ = 20221116
__all__ = ['left', 'right', 'renameLeft', 'renameRight', 'commonRename']

from pandas import Series

def right(sdf, name_separator=None):
    if not hasattr(sdf, 'nameSeparator') or sdf.name_separator in [None, False, '']:
        if name_separator is None:
            return {sdf.name:sdf.name} if type(sdf) is Series else {col: col for col in sdf.columns}
    if name_separator is None and sdf.name_separator not in [None, False, '']:
        name_separator = sdf.name_separator
    if type(sdf) is Series:
        objs = {sdf.name: str(sdf.name).split(name_separator)[-1] if name_separator in sdf.name else sdf.name}
    else:
        objs = {each: str(each).split(name_separator)[-1] if name_separator in str(each) else each for each in sdf.columns if each is not None}
    return objs


def left(sdf, name_separator=None):
    if not hasattr(sdf, 'nameSeparator') or sdf.name_separator in [None, False, '']:
        if name_separator is None:
            return {sdf.name:sdf.name} if type(sdf) is Series else {col: col for col in sdf.columns}
    if name_separator is None and sdf.name_separator not in [None, False, '']:
        name_separator = sdf.name_separator
    if type(sdf) is Series:
        objs = {sdf.name: str(sdf.name).split(name_separator)[0] if name_separator in sdf.name else sdf.name}
    else:
        objs = {each: str(each).split(name_separator)[0] if name_separator in str(each) else each for each in sdf.columns if each is not None}
    return objs


def renameRight(sdf, name_separator=None):
    if not hasattr(sdf, 'nameSeparator') or sdf.name_separator in [None, False, '']:
        if name_separator is None:
            return sdf
    objs = right(sdf, name_separator=name_separator)
    if type(sdf) is Series:
        return sdf.rename(list(objs.values())[0])
    return sdf.rename(columns=objs, inplace=False)


def renameLeft(sdf, name_separator=None):
    if not hasattr(sdf, 'nameSeparator') or sdf.name_separator in [None, False, '']:
        if name_separator is None:
            return sdf
    objs = left(sdf, name_separator=name_separator)
    if type(sdf) is Series:
        return sdf.rename(list(objs.values())[0])
    return sdf.rename(columns=objs, inplace=False)


def commonRename(sdf1, sdf2, *,
                 left_right=None,
                 intersection_character=None,
                 name_separator1=None,
                 name_separator2=None):

    if intersection_character is None:
        if hasattr(sdf1, 'intersectionCharacter'):
            ic = sdf1.intersection_character
        elif hasattr(sdf2, 'intersectionCharacter'):
            ic = sdf2.intersection_character
        else:
            ic = '&'
    else:
        ic = str(intersection_character)

    if left_right is not None:
        if type(left_right) is not str:
            raise TypeError("`left_right` parameter must be a string 'left' or 'right'")
        left_right = left_right.lower().strip()
        if left_right[0] not in 'lr':
            raise TypeError("`left_right` parameter must be a string 'left' or 'right'")

    ns = None
    if name_separator1 is None:
        if hasattr(sdf1, 'nameSeparator'):
            ns1 = str(sdf1.name_separator)
            ns = ns1
        else:
            pass
    if name_separator2 is None:
        if hasattr(sdf2, 'nameSeparator'):
            ns2 = str(sdf2.name_separator)
            if ns1 is None:
                ns = ns2
        else:
            pass
    if ns is None:
        raise ValueError("`name_separator1` and `name_separator2` must be a string.")

    if left_right == 'l' or (
            left_right is None and
            hasattr(sdf1, 'left') and len(sdf1.left) == 1 and
            hasattr(sdf2, 'left') and len(sdf2.left) == 1):

        sdf1_copy = sdf1.renameRight(inplace=False)
        sdf2_copy = sdf2.renameRight(inplace=False)

        commonNames = {}
        for col in sdf1_copy.columns:
            if col in sdf2_copy.columns:
                commonNames[col] = str(sdf1.left[0]) + ic + str(sdf2.left[0]) + str(SDF1.name_separator) + str(col)
            else:
                commonNames[c] = str(SDF1.left[0]) + str(SDF1.name_separator) + str(c)
        for c in SDF2C.columns:
            if c not in SDF1C.columns:
                commonNames[c] = str(SDF2.left[0]) + str(SDF1.name_separator) + str(c)
        if LR is None and len(commonNames) > 1:
            alternative = self._CommonRename(SDF1, SDF2, LR='R')
            if len(alternative[2]) < len(commonNames):
                return alternative

    elif left_right == 'r' or (LR is None and len(SDF1.right) == 1 and len(SDF2.right) == 1 ):
        SDF2C = SDF2.copy()
        SDF2C.renameLeft(inplace=True)
        SDF1C = SDF1.copy()
        SDF1C.renameLeft(inplace=True)
        commonNames = {}
        for c in SDF1C.columns:
            if c in SDF2C.columns:
                commonNames[c] = str(c) + str(SDF1.name_separator) + str(SDF1.right[0]) + str(cha) + str(SDF2.right[0])
            else:
                commonNames[c] = str(c) + str(SDF1.name_separator) + str(SDF1.right[0])
        for c in SDF2C.columns:
            if c not in SDF1C.columns:
                commonNames[c] = str(c) + str(SDF1.name_separator) + str(SDF2.right[0])
        if LR is None and len(commonNames) > 1:
            alternative = self._CommonRename(SDF1, SDF2, LR='L')
            if len(alternative[2]) < len(commonNames):
                return alternative

    else:
        SDF1C, SDF2C = SDF1, SDF2.copy()
        commonNames = None

    # check if proposed names are not repetitions of original names
    for name in commonNames:
        if self.name_separator is str and len(self.name_separator) > 0 and self.name_separator in commonNames[name]:
            if commonNames[name].split(self.name_separator)[0] == commonNames[name].split(self.name_separator)[1] and commonNames[name].split(self.name_separator)[0] == name:
                commonNames[name] = name

    return SDF1C, SDF2C, commonNames