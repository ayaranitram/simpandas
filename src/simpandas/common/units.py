#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec  7 21:48:37 2019

@author: Martín Carlos Araya <martinaraya@gmail.com>

THIS MODULE IS DEPRECATED, WILL BE SUBSTITUTED BY unyts package
"""

__version__ = '0.5.7'
__release__ = 20220919

import numpy
# import pandas

class WrongUnits(Exception):
    def __init__(self, message='unit not listed in library, unit must be a string'):
        print('ERROR: Wrong Units, ' + message)


class WrongValue(Exception):
    def __init__(self, message='value unit must be a float or integer'):
        print('ERROR: Wrong Value, ' + message)

#class basicmeta(type):
#    def __repr__(cls):
#        return 'temperature'

#class basics(object, metaclass=basicmeta) :

class unit(object) :

    # support variables for internal use:
    previous=[(None, None)]
    RecursionLimit = 5
    fvf = None
    Memory = {} # (fromUnit, toUnit) : ( conversion factor, conversion path )


    # Sistema Internacional
    SI = {
        'Y' : (lambda X: X*1.0E+24,lambda X: X*1.0E+48,lambda X: X*1.0E+72) , # yotta
        'Z' : (lambda X: X*1.0E+21,lambda X: X*1.0E+42,lambda X: X*1.0E+63) , # zetta
        'E' : (lambda X: X*1.0E+18,lambda X: X*1.0E+36,lambda X: X*1.0E+54) , # exa
        'P' : (lambda X: X*1.0E+15,lambda X: X*1.0E+30,lambda X: X*1.0E+46) , # peta
        'T' : (lambda X: X*1.0E+12,lambda X: X*1.0E+24,lambda X: X*1.0E+36) , # tera
        'G' : (lambda X: X*1.0E+09,lambda X: X*1.0E+18,lambda X: X*1.0E+27) , # giga
        'M' : (lambda X: X*1.0E+06,lambda X: X*1.0E+12,lambda X: X*1.0E+18) , # mega
        'K' : (lambda X: X*1.0E+03,)*3 , # with uppercase K is commonly used to express x1000
        'k' : (lambda X: X*1.0E+03,lambda X: X*1.0E+06,lambda X: X*1.0E+09) , # kilo
        'h' : (lambda X: X*1.0E+02,lambda X: X*1.0E+04,lambda X: X*1.0E+06) , # hecto
        'd' : (lambda X: X*1.0E-01,lambda X: X*1.0E-02,lambda X: X*1.0E-03) , # deci
        'c' : (lambda X: X*1.0E-02,lambda X: X*1.0E-04,lambda X: X*1.0E-06) , # centi
        'm' : (lambda X: X*1.0E-03,lambda X: X*1.0E-06,lambda X: X*1.0E-09) , # mili
        'µ' : (lambda X: X*1.0E-06,lambda X: X*1.0E-12,lambda X: X*1.0E-18) , # micro
        'u' : (lambda X: X*1.0E-06,lambda X: X*1.0E-12,lambda X: X*1.0E-18) , # micro
        'n' : (lambda X: X*1.0E-09,lambda X: X*1.0E-18,lambda X: X*1.0E-27) , # nano
        'p' : (lambda X: X*1.0E-12,lambda X: X*1.0E-24,lambda X: X*1.0E-36) , # pico
        'f' : (lambda X: X*1.0E-15,lambda X: X*1.0E-30,lambda X: X*1.0E-45) , # femto
        'a' : (lambda X: X*1.0E-18,lambda X: X*1.0E-36,lambda X: X*1.0E-54) , # atto
        'z' : (lambda X: X*1.0E-21,lambda X: X*1.0E-42,lambda X: X*1.0E-63) , # zepto
        'y' : (lambda X: X*1.0E-24,lambda X: X*1.0E-48,lambda X: X*1.0E-72) , # yocto
        }
    SI_order = (('lenght', 'pressure', 'weight', 'mass', 'time', 'dataBIT', ), ('area', ), ('rate', 'volume', ), ('dataBYTE', ))
    DATA = {
        'Y' : (lambda X: X*1.0E+24, lambda X: X*2**80), # yotta
        'Z' : (lambda X: X*1.0E+21, lambda X: X*2**70), # zetta
        'E' : (lambda X: X*1.0E+18, lambda X: X*2**60), # exa
        'P' : (lambda X: X*1.0E+15, lambda X: X*2**50), # peta
        'T' : (lambda X: X*1.0E+12, lambda X: X*2**40), # tera
        'G' : (lambda X: X*1.0E+09, lambda X: X*2**30), # giga
        'M' : (lambda X: X*1.0E+06, lambda X: X*2**20), # mega
        'K' : (lambda X: X*1.0E+03, lambda X: X*2**10), # kilo with uppercase K because it is very common
        'k' : (lambda X: X*1.0E+03, lambda X: X*2**10), # kilo
        }
    DATA_order = (('dataBIT', ), ('dataBYTE', ))


    # Oil & Gas Field Unit System
    OGF = { 'M' : (None, None, lambda X: X*1.0E+03),
            'MM' : (None, None, lambda X: X*1.0E+06),
            'B' : (None, None, lambda X: X*1.0E+09),
            'T' : (None, None, lambda X: X*1.0E+12),
        }
    OGF_order = (tuple(), tuple, ('volume', 'rate', ))

    dictionary = {}
    dictionary['time'] = []
    dictionary['time_NAMES_UPPER_PLURALwS_REVERSE'] = {
                  'nanosecond' : ('ns', ),
                  'millisecond' : ('ms', ),
                  'second' : ('s', 'sec'),
                  'minute' : ('min', ),
                  'hour' : ('h', 'hr'),
                  'day' : ('d', 'día', 'días', 'DíA'),
                  'week' : ('w', 'we'),
                  'month' : ('mo', ),
                  'year' : ('y', ),
                  'lustrum' : tuple(),
                  'decade' : tuple(),
                  'century' : ('centuries', ),
                  }
    dictionary['time_SI'] = ('s', )

    dictionary['temperature'] = ['C', 'K', 'F', 'R']
    dictionary['temperature_NAMES'] = {'Celsius' : ('Centigrades', 'C', 'DEG C', 'DEGREES C'),
                         'Fahrenheit' : ('F', 'DEG F', 'DEGREES F'),
                         'Rankine' : ('R', 'DEG R', 'DEGREES R'),
                         'Kelvin' : ('K', 'DEG K', 'DEGREES K') }

    dictionary['lenght'] = []
    dictionary['lenght_NAMES_UPPER_REVERSE'] = {'meter': ('m', 'meter')}
    dictionary['length_SI'] = ('m', 'l')  # litre is volumen but the conversion of SI prefixes is linear
    dictionary['lenght_UK_NAMES_UPPER_REVERSE'] = {'thou' : ('th', ),
                 'inch' : ('in', '"'),
                 'foot' : ('feet', 'ft', "'"),
                 'yard' : ('yd', ),
                 'chain' : ('ch', ),
                 'rod' : ('rd', ),
                 'furlong' : ('fur', ),
                 'mile' : ('mi', ),
                 'league' : ('lea', ),
                 'nautical mile' : ('nmi', )}

    dictionary['area'] = []
    dictionary['area_NAMES_UPPER_REVERSE'] = {'square meter' : ('sq m', 'm2', 'sqmeter', 'm*m', 'm3/m')}
    dictionary['area_SI'] = ('m2', )
    dictionary['area_UK_NAMES_UPPER_REVERSE'] = { 'square mile' : ('sq mi', 'mi2', 'sqmile', 'mi*mi'),
                             'acre' : tuple(),
                             'square rod' : ('sq rd', 'sqrd', 'rd2', 'rd*rd'),
                             'square yard' : ('sq yd', 'sqyd', 'yd2', 'yd*yd'),
                             'square foot' : ('sq ft', 'sqft', 'ft2', 'ft*ft', 'ft3/ft'),
                             'square inch' : ('sq in', 'sqin', 'in2', 'in*in', 'in3/in')
                             }

    dictionary['volume'] = []
    dictionary['volume_SI_UPPER_REVERSE'] = ('m3', 'sm3', 'stm3', 'rm3')  # 'l' # litre is volumen but the conversion of SI prefixes is linear
    dictionary['volume_UK_NAMES_UPPER_REVERSE_PLURALwS'] = { 'fuild ounce' : ('fl oz', 'oz', 'ounce'),
                                           'gill' : ('gi', ),
                                           'pint' : ('pt', ),
                                           'quart' : ('qt', ),
                                           'gallonUK' : ('gal', 'galUK', 'UKgal', 'UKgallon', 'gallon'),
                                           'gallonUS' : ('gal', 'galUS', 'USgal', 'USgallon', 'gallon'),
        }
    dictionary['volume_NAMES_UPPER_REVERSE_PLURALwS_SPACES'] = { 'litre' : ('l', 'liter', ),
                                        'mililitre' : ('ml', 'mililiter', 'cubic centimeter'),
                                        'centilitre' : ('cl', 'centiliter'),
                                        'decilitre' : ('dl', 'deciliter'),
                                        'cubic meter' : ('CM', 'm3'),
                                        'standard cubic meter' : ('scm', 'sm3', 'stm3', 'm3'),
                                        'cubic centimeter' : ( 'cc', 'cm3'),
                                        'reservoir cubic meter' : ('rm3', ),
                                        'cubic foot' : ('cubic feet', 'ft3', 'cf'),
                                        'standard cubic foot' : ('scf', 'cf'),
                                        'cubic inch' : ('in3', 'cubic inches'),
                                        'barrel' : ('bbl', 'stb', 'bbls'),
                                        'reservoir barrel' : ('rb', ),
                                        'standard barrel' : ('stb', 'stbo', 'stbw', 'stbl', 'oil barrel'),
                                        }
    dictionary['volume_UPPER_REVERSE'] =  ('kstm3', 'Mstm3')
    dictionary['volume_PLURALwS'] = ('liter', 'mililiter', 'centiliter', 'deciliter', 'barrel', 'oil barrel', 'gals', 'UKgallons', 'USgallons', 'oil gallon')
    dictionary['volume_OGF'] = ('scf', 'cf', 'ft3', 'stb', 'bbl', 'rb', 'stbo', 'stbw', 'stbl')
    # dictionary['volume_oilgas_NAMES'] = ('scf', 'cf', 'ft3', 'stb', 'bbl', 'rb', 'stbo', 'stbw', 'stbl')
    dictionary['volume_oilgas_UPPER'] =  ( 'sm3', 'm3', 'rm3', 'ksm3', 'Msm3', 'Gsm3',
                                          'scf', 'cf', 'ft3', 'Mscf', 'MMscf', 'Bscf', 'Tscf', 'Mcf', 'MMcf', 'Bcf', 'Tcf',
                                          'stb', 'bbl', 'rb', 'Mstb', 'MMstb', 'Bstb', 'Tstb', 'Mbbl', 'MMbbl', 'Mrb', 'MMrb')

    dictionary['volume_producto_NAMES'] = {'m3':('m2*m', ),
                                           'cm3':('cm2*cm', ),
                                           'ft3':('ft2*ft', ),
                                           'in3':('in2*in', )}

    dictionary['pressure'] = []
    dictionary['pressure_NAMES_UPPER_REVERSE_SPACES'] = {
                                                  'absolute psi' : ('psia', 'lb/in2', 'absolute pound/square inch', 'psi absolute'),
                                                  'absolute bar' : ('bara', 'barsa', 'abs bar', 'bar absolute'),
                                                  'atmosphere' : ('atm','atma' ),
                                                  'Pascal' : ('Pa', ),
                                                  'kPa' : ('KPa', 'kilopascal'),
                                                  'hPa' : ('hectopascal', ),
                                                  'Torr' : ('millimeters of mercury', ),
                                                  'millimeters of mercury' : ('mmHg', ),
                                                  }
    dictionary['pressure_NAMES_UPPER_SPACES'] = {'psi gauge' : ('psi', 'pound/square inch', 'psig', 'gauge psi'),
                                                 'bar gauge' : ('bar', 'barg', 'gauge bar', 'bars'),
                                                  }
    dictionary['pressure_SI'] = ('Pa', 'bara', 'bar')


    dictionary['weight'] = []
    dictionary['weight_NAMES_UPPER_REVERSE_SPACES_PLURALwS'] = { 'gram' : ('g', ),
                                                      'kilogram' : ('kg', 'kgm', 'Kgm', ),
                                                      'milligrams' : ('mg', ),
                                                      'metric ton' : ('Tonne', ),
                                                      'g-mol' : ('g-moles', ),
                                                      'Kg-mol' : ('Kg-moles', ),
        }
    dictionary['weight_UK_NAMES_UPPER_REVERSE_SPACES_PLURALwS'] = {
        'grain' : ('gr', ),
        'pennyweight' : ('pwt', 'dwt'),
        'dram' : ('dr', 'dramch'),
        'ounce' : ('oz', ),
        'pound' : ('lb', '#', 'libra'),
        'stone' : ('st', ),
        'quarter' : ('qr', 'qrt'),
        # 'hundredweight' : ('cwt', ),
        'short hundredweight' : ('US hundredweight', 'UScwt'),
        'long hundredweight' : ('UK hundredweight', 'UKcwt', 'cwt'),
        # 'ton' : ('t', ),
        'short ton' : ('USton', ),
        'long ton' : ('t', 'UKton', 'ton'),
        }
    dictionary['weight_SI'] = ('g', 'g-mol')

    dictionary['mass'] = ['kilogram mass']


    dictionary['density'] = []
    dictionary['density_oilgas'] = {}
    dictionary['density_NAMES_UPPER'] = {
        'API' : ('DEGREES', ),
        'SgO':('gas-gravity', 'gas-specific-gravity'),
        'SgW':('water-gravity', ),
        'SgG':('oil-gravity', ),
        }
    dictionary['density_NAMES_UPPER_REVERSE'] = {
        'g/cm3':('g/cc', ),
        'kg/m3':('Kg/m3', ),
        'lb/ft3':tuple(),
        'psi/ft':tuple(),
        'kJ/rm3':('KJ/rm3', ),
        'lb/stb':tuple(),
        'psia/ft':('psi/ft', ),
        'bara/m':('bar/m', ),
        }



    dictionary['compressibility'] = []
    dictionary['compressibility_UPPER_NAMES'] = {'1/psi':('1/psia', 'µsip', 'usip', '1/psig'),
                                                 'µsip':('usip', ),
                                                '1/bar':('1/bara', '1/barg')}

    # volumeRatio = []
    # volumeRatio_UPPER_INV = ['rb/stb', 'rb/scf', 'ft3/scf', 'scf/stb', 'Mscf/stb', 'MMscf/stb',
    #                'rm/sm3', 'sm3/rm', 'sm3/stm3', 'stm3/Ksm3', 'Ksm3/Msm3', 'Msm3/Gsm3',
    #                'sm3/stb', 'sm3/scf']

    # volumeRatio_UPPER_FRACTION = ['stb/stb', 'stm3/stm3', 'sm3/sm3', 'm3/m3', 'Ksm3/Ksm3', 'Msm3/Msm3', 'Gsm3/Gsm3']

    # energy = []
    # energy_UPPER = ('kJ')

    dictionary['rate'] = []
    dictionary['rate_NAMES_UPPER_SPACES_REVERSE'] = {'standard barrel per day' : ('stb/day', ),
                                                     'standard cubic foot per day' : ('scf/day', 'cf/day', 'scfd'),
                                                     'standard cubic meter per day' : ('sm3/day', ),
                                                     'barrel per day' : ('bbl/day'),
                                                     'cubic meter per day' : ('m3/day', ),
                                                     'cubic foot per day' : ('ft3/day', ),
                                                     'reservoir barrel per day' : ('rb/day', ),
                                                     'reservoir cubic meter per day' : ('rm3/day', ),
                                                     }
    dictionary['rate_NAMES_UPPER_SPACES_REVERSE'] = { 'stb/day' : ('stbd', ),
                                                      'scf/day' : ('scfd', 'cf/day', ),
                                                     'sm3/day' : ('sm3d', 'stm3d', 'stm3/day'),
                                                     'bbl/day' : ('bbld', ),
                                                     'm3/day' : ('m3/d', ),
                                                     'ft3/day' : ('cf/day', ),
                                                     }
    # dictionary['rate_UPPER_DAY_REVERSE'] = ('sm3/day', 'rm3/day', 'kg-mol/day', )
    # dictionary['rate_OilGas_UPPER_DAY_REVERSE'] =  ( 'sm3/day', 'm3/day', 'rm3/day', 'ksm3/day', 'Msm3/day', 'Gsm3/day',
    #                                       'scf/day', 'cf/day', 'ft3/day', 'Mscf/day', 'MMscf/day', 'Bscf/day', 'Tscf/day', 'Mcf/day', 'MMcf/day', 'Bcf/day', 'Tcf/day',
    #                                       'stb/day', 'bbl/day', 'rb/day', 'Mstb/day', 'MMstb/day', 'Bstb/day', 'Tstb/day', 'Mbbl/day', 'MMbbl/day', 'Mrb(day', 'MMrb/day')
    # dictionary['rate_SI'] = ('m3/day', 'sm3/day', 'stm3/day')
    # dictionary['rate_OGF'] = ('scf/day', 'cf/day', 'ft3/day', 'stb/day', 'bbl/day', 'rb/day', 'stbo/day', 'stbw/day', 'stbl/day')
    # dictionary['rate_FROMvolume'] = dictionary['rate_SI']

    dictionary['dataBYTE'] = []
    dictionary['dataBYTE_UPPER_PLURALwS_DATA_NAME_REVERSE'] = {'B':('Byte', 'byte')}
    dictionary['dataBIT'] = []
    dictionary['dataBIT_UPPER_PLURALwS_DATA'] = ('bit', )

    dictionary['viscosity'] = []
    dictionary['viscosity_UPPER_NAMES_REVERSE'] = {'centipoise':('cP', ),
                                           'Poise':('dyne*s/cm2', 'g/cm/s'),
                                           'Pa*s':('N*s/m2', 'kg/m/s')
                                           }

    dictionary['permeability'] = []
    dictionary['permeability_UPPER_REVERSE'] = ('mD', 'Darcy', )

    dictionary['force'] = []
    dictionary['force_NAMES_SPACES_RECURSIVE_UPPER_REVERSE'] = {'Newton':('N', 'newton', 'kg*m/s2'),
                                 'kilogram force':('kgf', 'kilopondio', 'kilogram'),
                                 'kilopondio':('kp', ),
                                 'Dyne' : ('dyne', 'dyn', 'g*cm/s2')}

    dictionary['productivityIndex'] = []
    dictionary['productivityIndex_UPPER_NAMES_REVERSE'] = {'stb/day/psi':('STB/DAY/', 'stbd/psi', 'stbd/psia', 'stb/day/psia', 'stb/day-psi', 'stb/day-psia', 'stb/d/psi'),
                                                           'sm3/day/bar':('SM3/DAY/', 'sm3d/bar', 'sm3d/bara', 'sm3/day/bara', 'sm3/day-bar', 'sm3/day-bara', 'sm3/d/b'),
                                                           'sm3/day/KPa':('sm3d/KPa', 'sm3d/KPa', 'sm3/day-KPa', 'sm3/d/KPa')}

    dictionary['pressureGradient'] = []
    dictionary['pressureGradient'] = ( 'psi/ft', 'psia/ft', 'psig/ft', 'psi/m', 'bar/m', 'bars/m', 'barsa/m', 'bara/m', 'barg/m' )

    dictionary['acceleration'] = ('m/s2', )

    dictionary['other'] = []
    dictionary['other_UPPER_NAMES'] = {'sec/day':('sec/d', ),
                                       's2':('s*s', )}

    dictionary['dimensionless'] = []
    dictionary['dimensionless_fractions_UPPER_NAMES'] = { 'fraction' : ('ratio', 'dimensionless', 'unitless', 'None', '')}
    dictionary['dimensionless_percentage_NAMES_REVERSE'] = {'percentage' : ('%'), }

    dictionary['date'] = []

    dictionary['date_UPPER_PLURALwS'] = ['date']

    dictionary['customUnits'] = []

    def __init__(self, name) :
        if type(name) == str :
            self.name = name
        else:
            self.name = ''
    def getName(self):
        return self.name
    def __str__(self):
        return self.name
    def isUnit(Unit) :
        if type(Unit) == str :
            Unit = Unit.strip()
        for each in list(unit.dictionary.keys()) :
            if '_' not in each :
                isU = Unit in list(unit.dictionary[each])
                if isU :
                    # print(" '" + Unit + "' is unit")
                    return True

        if '/' in Unit or '*' in Unit:
            # print(" splitting '" + Unit + "'")
            UnitSplit = []
            for each in Unit.split('/') :
                UnitSplit += each.split('*')
            ret = [False]*len(UnitSplit)
            for each in list(unit.dictionary.keys()) :
                if '_' not in each :
                    for subU in range(len(UnitSplit)) :
                        if UnitSplit[subU] in list(unit.dictionary[each]) :
                            ret[subU] = True
            # print(" split of '" + Unit + "' " + str(ret))
            for each in ret :
                if not each :
                    return False
        # print(" finally '" + Unit + "' is unit")
        return True

# def UnitSplitter(Unit):
#     """
#     split the unit by / and *
#     return the split unit and True or False if the subunit is found in the
#     """
#     UnitSplit = []
#     for each in Unit.split('/') :
#         UnitSplit += each.split('*')
#     ret = [False]*len(UnitSplit)
#     for each in list(unit.dictionary.keys()) :
#         if '_' not in each :
#             for subU in range(len(UnitSplit)) :
#                 if UnitSplit[subU] in list(unit.dictionary[each]) :
#                     ret[subU] = True
#     return UnitSplit, ret

def set_fvf(FVF) :
    if type(FVF) is str :
        try :
            FVF = float(FVF)
        except:
            print('received FVF value is not a number: ' + str(FVF))
    if type(FVF) is int or type(FVF) is float :
        unit.fvf = FVF

def get_fvf() :
    if unit.fvf is None :
        print('Please enter formation volume factor (FVF) in reservoir_volume/standard_volume:')
        while unit.fvf is None :
            unit.fvf = input(' FVF (rV/stV) = ')
            if not valid_fvf(unit.fvf) :
                unit.fvf = None
            else:
                unit.fvf = valid_fvf(unit.fvf)

    return unit.fvf

def valid_fvf(FVF) :
    if type(FVF) is str :
        try :
            FVF = float(FVF)
        except:
            return False
    if type(FVF) is int or type(FVF) is float :
        if FVF <= 0 :
            return False
        else:
            return FVF
    return False

class conversion(object):
    def __init__(self, src, dest, conv, reverse=False):
        """Assumes src and dest are nodes"""
        self.src = src
        self.dest = dest
        self.conv = conv
        self.rev = reverse
    def getSource(self):
        return self.src
    def getDestination(self):
        return self.dest
    def convert(self, value):
        return self.conv(value)
    def reverse(self, value):
        return value/self.conv(1)
    def getConvert(self):
        if self.rev and type(self.conv) != None :
            return lambda X: X/self.conv(1)
        else:
            return self.conv
    def __str__(self):
        return self.src.getName() + '->' + self.dest.getName()

class digraph(object):
    """edges is a dict mapping each node to a list of its children"""
    def __init__(self):
        self.edges = {}
    def addNode(self, node):
        if node in self.edges:
            raise ValueError('Duplicate node')
        else:
            self.edges[node] = []
    def addEdge(self, edge):
        src = edge.getSource()
        dest = edge.getDestination()
        if not (src in self.edges and dest in self.edges):
            raise ValueError('Node not in graph')
        self.edges[src].append(dest)
    def childrenOf(self, node):
        return self.edges[node]
    def hasNode(self, node):
        return node in self.edges
    def getNode(self, name):
        for n in self.edges:
            if n.getName() == name:
                return n
        raise NameError(name)

    def __str__(self):
        result = ''
        for src in self.edges:
            for dest in self.edges[src]:
                result = result + src.getName() + '->'\
                         + dest.getName() + '\n'
        return result[:-1] #omit final newline

class UnitDigraph(object):
    """edges is a dict mapping each node to a list of its children"""
    def __init__(self):
        self.edges = {}
    def addNode(self, node):
        if node in self.edges:
            raise ValueError('Duplicate node')
        else:
            self.edges[node] = [], []
    def addEdge(self, edge, reverse=False):
        src = edge.getSource()
        dest = edge.getDestination()
        conv = edge.getConvert()
        if not (src in self.edges and dest in self.edges):
            raise ValueError('Node not in graph')
        self.edges[src][0].append(dest)
        self.edges[src][1].append(conv)
    def childrenOf(self, node):
        return self.edges[node][0]
    def hasNode(self, node):
        return node in self.edges
    def getNode(self, name):
        for n in self.edges:
            if n.getName() == name:
                return n
        raise NameError(name)
    def convert(self, value, src, dest):
        if type(src) != unit :
            src = self.getNode(src)
        if type(dest) != unit :
            dest = self.getNode(dest)
        return self.edges[src][1][ self.edges[src][0].index(dest) ]( value )
    def conversion(self, src, dest):
        if type(src) != unit :
            src = self.getNode(src)
        if type(dest) != unit :
            dest = self.getNode(dest)
        return self.edges[src][1][ self.edges[src][0].index(dest) ]
    def __str__(self):
        result = ''
        for src in self.edges:
            for dest in self.edges[src]:
                result = result + src.getName() + '->'\
                         + dest.getName() +\
                         str(self.conv) + '\n'
        return result[:-1] #omit final newline

def UnitConversions():
    UC = UnitDigraph()

    StandardAirDensity = 1.225 # Kg/m3 or g/cc
    StandadEarthGravity = 9.80665 # m/s2 or 980.665 cm/s2 from



    for unitKind in list(unit.dictionary.keys()):
        # print('1: ' +unitKind)
        if '_' not in unitKind :
            for unitName in unit.dictionary[unitKind] :
                # print('_ 2: ' + unitName)
                UC.addNode(unit(unitName))
        if '_NAMES' in unitKind :
            for unitName in list(unit.dictionary[unitKind].keys()) :
                # print('N  2: ' + unitName, unitKind.split('_')[0])
                UC.addNode(unit(unitName))
                unit.dictionary[unitKind.split('_')[0]].append(unitName)
                for secondName in unit.dictionary[unitKind][unitName] :
                    # print('N   3: ' + unitName)
                    UC.addNode(unit(secondName))
                    UC.addEdge(conversion(UC.getNode(secondName), UC.getNode(unitName), lambda X: X ))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(secondName), lambda X: X ))
                    unit.dictionary[unitKind.split('_')[0]].append(secondName)
        if '_SPACES' in unitKind :
            for unitName in list(unit.dictionary[unitKind].keys()) :
                # print('N  2: ' + unitName, unitKind.split('_')[0])
                if ' ' in unitName :
                    UC.addNode(unit(unitName))
                    UC.addNode(unit(unitName.replace(' ', '-')))
                    unit.dictionary[unitKind.split('_')[0]].append(unitName)
                    unit.dictionary[unitKind.split('_')[0]].append(unitName.replace(' ', '-'))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(unitName.replace(' ', '-')), lambda X: X ))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(unitName.replace(' ', '-')), lambda X: X ))
                    for secondName in unit.dictionary[unitKind][unitName] :
                        # print('N   3: ' + unitName)
                        if ' ' in secondName :
                            UC.addNode(unit(secondName))
                            UC.addNode(unit(secondName.replace(' ', '-')))
                            UC.addEdge(conversion(UC.getNode(secondName.replace(' ', '-')), UC.getNode(secondName), lambda X: X ))
                            UC.addEdge(conversion(UC.getNode(secondName), UC.getNode(secondName.replace(' ', '-')), lambda X: X ))
                            unit.dictionary[unitKind.split('_')[0]].append(secondName)
                            unit.dictionary[unitKind.split('_')[0]].append(secondName.replace(' ', '-'))
                else:
                    for secondName in unit.dictionary[unitKind][unitName] :
                        # print('N   3: ' + unitName)
                        if ' ' in secondName :
                            UC.addNode(unit(secondName))
                            UC.addNode(unit(secondName.replace(' ', '-')))
                            UC.addEdge(conversion(UC.getNode(secondName.replace(' ', '-')), UC.getNode(secondName), lambda X: X ))
                            UC.addEdge(conversion(UC.getNode(secondName), UC.getNode(secondName.replace(' ', '-')), lambda X: X ))
                            unit.dictionary[unitKind.split('_')[0]].append(secondName)
                            unit.dictionary[unitKind.split('_')[0]].append(secondName.replace(' ', '-'))



        if '_SI' in unitKind and unitKind.split('_')[0] in unit.SI_order[0] :
            for unitName in list( unit.dictionary[unitKind] ) :
                # print('S  2: ' + unitName)
                UC.addNode(unit(unitName))
                unit.dictionary[unitKind.split('_')[0]].append(unitName)
                for prefix in list(unit.SI.keys()) :
                    # print('S   3: ' + prefix+unitName+'_'+str(unit.SI[prefix][0]))
                    UC.addNode(unit(prefix+unitName))
                    UC.addEdge(conversion(UC.getNode(prefix+unitName), UC.getNode(unitName), unit.SI[prefix][0] ))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(prefix+unitName), unit.SI[prefix][0], True ))
                    unit.dictionary[unitKind.split('_')[0]].append(prefix+unitName)
        if '_SI' in unitKind and unitKind.split('_')[0]  in unit.SI_order[1] :
            for unitName in list( unit.dictionary[unitKind] ) :
                # print('S  2: ' + unitName)
                UC.addNode(unit(unitName))
                unit.dictionary[unitKind.split('_')[0]].append(unitName)
                for prefix in list(unit.SI.keys()) :
                    # print('S   3: ' + prefix+unitName+'_'+str(unit.SI[prefix][1]))
                    UC.addNode(unit(prefix+unitName))
                    UC.addEdge(conversion(UC.getNode(prefix+unitName), UC.getNode(unitName), unit.SI[prefix][1] ))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(prefix+unitName), unit.SI[prefix][1], True ))
                    unit.dictionary[unitKind.split('_')[0]].append(prefix+unitName)
        if '_SI' in unitKind and unitKind.split('_')[0]  in unit.SI_order[2] :
            for unitName in list( unit.dictionary[unitKind] ) :
                # print('S  2: ' + unitName)
                UC.addNode(unit(unitName))
                unit.dictionary[unitKind.split('_')[0]].append(unitName)
                for prefix in list(unit.SI.keys()) :
                    # print('S   3: ' + prefix+unitName+'_'+str(unit.SI[prefix]))
                    UC.addNode(unit(prefix+unitName))
                    UC.addEdge(conversion(UC.getNode(prefix+unitName), UC.getNode(unitName), unit.SI[prefix][2] ))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(prefix+unitName), unit.SI[prefix][2], True ))
                    unit.dictionary[unitKind.split('_')[0]].append(prefix+unitName)
        if '_DATA' in unitKind and unitKind.split('_')[0]  in unit.DATA_order[0] :
            for unitName in list( unit.dictionary[unitKind] ) :
                # print('S  2: ' + unitName)
                UC.addNode(unit(unitName))
                unit.dictionary[unitKind.split('_')[0]].append(unitName)
                for prefix in list(unit.DATA.keys()) :
                    # print('S   3: ' + prefix+unitName+'_'+str(unit.SI[prefix]))
                    UC.addNode(unit(prefix+unitName))
                    UC.addEdge(conversion(UC.getNode(prefix+unitName), UC.getNode(unitName), unit.DATA[prefix][0] ))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(prefix+unitName), unit.DATA[prefix][0], True ))
                    unit.dictionary[unitKind.split('_')[0]].append(prefix+unitName)
        if '_DATA' in unitKind and unitKind.split('_')[0]  in unit.DATA_order[1] :
            for unitName in list( unit.dictionary[unitKind] ) :
                # print('S  2: ' + unitName)
                UC.addNode(unit(unitName))
                unit.dictionary[unitKind.split('_')[0]].append(unitName)
                for prefix in list(unit.DATA.keys()) :
                    # print('S   3: ' + prefix+unitName+'_'+str(unit.SI[prefix]))
                    UC.addNode(unit(prefix+unitName))
                    UC.addEdge(conversion(UC.getNode(prefix+unitName), UC.getNode(unitName), unit.DATA[prefix][1] ))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(prefix+unitName), unit.DATA[prefix][1], True ))
                    unit.dictionary[unitKind.split('_')[0]].append(prefix+unitName)
        if '_OGF' in unitKind and unitKind.split('_')[0] in unit.OGF_order[2] :
            for unitName in list( unit.dictionary[unitKind] ) :
                # print('O  2: ' + unitName)
                UC.addNode(unit(unitName))
                unit.dictionary[unitKind.split('_')[0]].append(unitName)
                for prefix in list(unit.OGF.keys()) :
                    # print('S   3: ' + prefix+unitName+'_'+str(unit.SI[prefix]))
                    UC.addNode(unit(prefix+unitName))
                    UC.addEdge(conversion(UC.getNode(prefix+unitName), UC.getNode(unitName), unit.OGF[prefix][2] ))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(prefix+unitName), unit.OGF[prefix][2], True ))
                    unit.dictionary[unitKind.split('_')[0]].append(prefix+unitName)
        if '_PLURALwS' in unitKind :
            if type( unit.dictionary[unitKind] ) == dict :
                listNames = list(unit.dictionary[unitKind].keys())
                for unitName in list(unit.dictionary[unitKind].keys()) :
                    # print('U  2: ' + unitName, unitKind.split('_')[0])
                    UC.addNode(unit(unitName))
                    UC.addNode(unit(unitName+'s'))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(unitName+'s'), lambda X: X ))
                    UC.addEdge(conversion(UC.getNode(unitName+'s'), UC.getNode(unitName), lambda X: X ))
                    unit.dictionary[unitKind.split('_')[0]].append(unitName+'s')
                    # for secondName in unit.dictionary[unitKind][unitName] :
                    #     # print('U   3: ' + unitName)
                    #     UC.addNode(unit(secondName))
                    #     UC.addNode(unit(secondName+'s'))
                    #     UC.addEdge(conversion(UC.getNode(secondName), UC.getNode(secondName+'s'), lambda X: X ))
                    #     UC.addEdge(conversion(UC.getNode(secondName+'s'), UC.getNode(secondName), lambda X: X ))
                    #     unit.dictionary[unitKind.split('_')[0]].append(secondName+'s')
            else:
                for unitName in list( unit.dictionary[unitKind] ) :
                    # print('U  2: ' + unitName, unitKind.split('_')[0])
                    UC.addNode(unit(unitName))
                    UC.addNode(unit(unitName+'s'))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(unitName+'s'), lambda X: X ))
                    UC.addEdge(conversion(UC.getNode(unitName+'s'), UC.getNode(unitName), lambda X: X ))
                    unit.dictionary[unitKind.split('_')[0]].append(unitName+'s')
            if '_UPPER' in unitKind :
                if type( unit.dictionary[unitKind] ) == dict :
                    listNames = list(unit.dictionary[unitKind].keys())
                    for unitName in list(unit.dictionary[unitKind].keys()) :
                        # print('U  2: ' + unitName, unitKind.split('_')[0])
                        UC.addNode(unit(unitName))
                        UC.addNode(unit(unitName.upper()+'S'))
                        UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(unitName.upper()+'S'), lambda X: X ))
                        UC.addEdge(conversion(UC.getNode(unitName.upper()+'S'), UC.getNode(unitName), lambda X: X ))
                        unit.dictionary[unitKind.split('_')[0]].append(unitName.upper()+'S')
                        # for secondName in unit.dictionary[unitKind][unitName] :
                        #     # print('U   3: ' + unitName)
                        #     UC.addNode(unit(secondName))
                        #     UC.addNode(unit(secondName.upper()+'S'))
                        #     UC.addEdge(conversion(UC.getNode(secondName), UC.getNode(secondName.upper()+'S'), lambda X: X ))
                        #     UC.addEdge(conversion(UC.getNode(secondName.upper()+'S'), UC.getNode(secondName), lambda X: X ))
                        #     unit.dictionary[unitKind.split('_')[0]].append(secondName.upper()+'S')
                else:
                    for unitName in list( unit.dictionary[unitKind] ) :
                        # print('U  2: ' + unitName, unitKind.split('_')[0])
                        UC.addNode(unit(unitName))
                        UC.addNode(unit(unitName.upper()+'S'))
                        UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(unitName.upper()+'S'), lambda X: X ))
                        UC.addEdge(conversion(UC.getNode(unitName.upper()+'S'), UC.getNode(unitName), lambda X: X ))
                        unit.dictionary[unitKind.split('_')[0]].append(unitName.upper()+'S')
        if '_UPPER' in unitKind :
            if type( unit.dictionary[unitKind] ) == dict :
                listNames = list(unit.dictionary[unitKind].keys())
                for unitName in list(unit.dictionary[unitKind].keys()) :
                    # print('U  2: ' + unitName, unitKind.split('_')[0])
                    UC.addNode(unit(unitName))
                    UC.addNode(unit(unitName.upper()))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(unitName.upper()), lambda X: X ))
                    UC.addEdge(conversion(UC.getNode(unitName.upper()), UC.getNode(unitName), lambda X: X ))
                    unit.dictionary[unitKind.split('_')[0]].append(unitName.upper())
                    for secondName in unit.dictionary[unitKind][unitName] :
                        # print('U   3: ' + unitName)
                        UC.addNode(unit(secondName))
                        UC.addNode(unit(secondName.upper()))
                        UC.addEdge(conversion(UC.getNode(secondName), UC.getNode(secondName.upper()), lambda X: X ))
                        UC.addEdge(conversion(UC.getNode(secondName.upper()), UC.getNode(secondName), lambda X: X ))
                        unit.dictionary[unitKind.split('_')[0]].append(secondName.upper())
            else:
                for unitName in list( unit.dictionary[unitKind] ) :
                    # print('U  2: ' + unitName, unitKind.split('_')[0])
                    UC.addNode(unit(unitName))
                    UC.addNode(unit(unitName.upper()))
                    UC.addEdge(conversion(UC.getNode(unitName), UC.getNode(unitName.upper()), lambda X: X ))
                    UC.addEdge(conversion(UC.getNode(unitName.upper()), UC.getNode(unitName), lambda X: X ))
                    unit.dictionary[unitKind.split('_')[0]].append(unitName.upper())
        if '_INVERSE' in unitKind :
            pass





    # for unitKind in list(unit.dictionary.keys()) :
    #     if '_REVERSE' in unitKind :
    #         for unitNode in

    # productivity index
    UC.addEdge(conversion(UC.getNode('sm3/day/bar'), UC.getNode('stb/day/psi'), lambda pi:  pi*6.289814/14.5038 ))
    UC.addEdge(conversion(UC.getNode('sm3/day/bar'), UC.getNode('sm3/day/KPa'), lambda pi:  pi/100 ))


    # percentage & fraction :
    UC.addEdge(conversion(UC.getNode('fraction'), UC.getNode('percentage'), lambda f: f*100 ))

    # time conversions
    # UC.addEdge(conversion(UC.getNode('second'), UC.getNode('millisecond'), lambda t: t*1000 ))
    UC.addEdge(conversion(UC.getNode('minute'), UC.getNode('second'), lambda t: t*60 ))
    UC.addEdge(conversion(UC.getNode('hour'), UC.getNode('minute'), lambda t: t*60 ))
    UC.addEdge(conversion(UC.getNode('day'), UC.getNode('hour'), lambda t: t*24 ))
    UC.addEdge(conversion(UC.getNode('day'), UC.getNode('month'), lambda t: t/36525/100*12 ))
    UC.addEdge(conversion(UC.getNode('week'), UC.getNode('day'), lambda t: t*7 ))
    UC.addEdge(conversion(UC.getNode('year'), UC.getNode('month'), lambda t: t*12 ))
    UC.addEdge(conversion(UC.getNode('year'), UC.getNode('day'), lambda t: t*36525/100 ))
    UC.addEdge(conversion(UC.getNode('lustrum'), UC.getNode('year'), lambda t: t*5 ))
    UC.addEdge(conversion(UC.getNode('decade'), UC.getNode('year'), lambda t: t*10 ))
    UC.addEdge(conversion(UC.getNode('century'), UC.getNode('year'), lambda t: t*100 ))

    # temperature conversions
    UC.addEdge(conversion(UC.getNode('Celsius'), UC.getNode('Kelvin'), lambda t: t + 273.15 ))
    UC.addEdge(conversion(UC.getNode('Kelvin'), UC.getNode('Celsius'), lambda t: t - 273.15 ))
    UC.addEdge(conversion(UC.getNode('Celsius'), UC.getNode('Fahrenheit'), lambda t: t*9/5 + 32 ))
    UC.addEdge(conversion(UC.getNode('Fahrenheit'), UC.getNode('Celsius'), lambda t: (t-32) * 5/9 ))
    UC.addEdge(conversion(UC.getNode('Fahrenheit'), UC.getNode('Rankine'), lambda t: t+459.67 ))
    UC.addEdge(conversion(UC.getNode('Rankine'), UC.getNode('Fahrenheit'), lambda t: t-459.67 ))
    UC.addEdge(conversion(UC.getNode('Rankine'), UC.getNode('Kelvin'), lambda t: t*9/5 ))
    UC.addEdge(conversion(UC.getNode('Kelvin'), UC.getNode('Rankine'), lambda t: t*5/9 ))


    # lenght conversions
    UC.addEdge(conversion(UC.getNode('yard'), UC.getNode('meter'), lambda d: d*9144/10000 ))
    # UC.addEdge(conversion(UC.getNode('foot'), UC.getNode('meter'), lambda d: d*3048/10000 ))
    UC.addEdge(conversion(UC.getNode('inch'), UC.getNode('thou'), lambda d: d*1000 ))
    UC.addEdge(conversion(UC.getNode('foot'), UC.getNode('inch'), lambda d: d*12))
    UC.addEdge(conversion(UC.getNode('yard'), UC.getNode('foot'), lambda d: d*3))
    UC.addEdge(conversion(UC.getNode('chain'), UC.getNode('yard'), lambda d: d*22))
    UC.addEdge(conversion(UC.getNode('furlong'), UC.getNode('chain'), lambda d: d*10))
    UC.addEdge(conversion(UC.getNode('mile'), UC.getNode('furlong'), lambda d: d*8))
    UC.addEdge(conversion(UC.getNode('league'), UC.getNode('mile'), lambda d: d*3))
    UC.addEdge(conversion(UC.getNode('nautical mile'), UC.getNode('meter'), lambda d: d*1852))
    UC.addEdge(conversion(UC.getNode('rod'), UC.getNode('yard'), lambda d: d*55/10))

    # area conversions
    UC.addEdge(conversion(UC.getNode('square mile'), UC.getNode('acre'), lambda d: d*640 ))
    UC.addEdge(conversion(UC.getNode('acre'), UC.getNode('square yard'), lambda d: d*4840 ))
    UC.addEdge(conversion(UC.getNode('square rod'), UC.getNode('square yard'), lambda d: d*3025/100))
    UC.addEdge(conversion(UC.getNode('square yard'), UC.getNode('square foot'), lambda d: d*9))
    UC.addEdge(conversion(UC.getNode('square foot'), UC.getNode('square inch'), lambda d: d*144))
    UC.addEdge(conversion(UC.getNode('square foot'), UC.getNode('square meter'), lambda d: d*(3048**2)/(10000**2)))
    UC.addEdge(conversion(UC.getNode('Darcy'), UC.getNode('mD'), lambda d: d*1000 ))
    UC.addEdge(conversion(UC.getNode('Darcy'), UC.getNode('µm2'), lambda d: d*0.9869233))
    # UC.addEdge(conversion(UC.getNode('m*m'), UC.getNode('m'), lambda d: d**0.5 ))
    # UC.addEdge(conversion(UC.getNode('m'), UC.getNode('m*m'), lambda d: d**2 ))
    # UC.addEdge(conversion(UC.getNode('rd*rd'), UC.getNode('rd'), lambda d: d**0.5 ))
    # UC.addEdge(conversion(UC.getNode('rd'), UC.getNode('rd*rd'), lambda d: d**2 ))
    # UC.addEdge(conversion(UC.getNode('yd*yd'), UC.getNode('yd'), lambda d: d**0.5 ))
    # UC.addEdge(conversion(UC.getNode('yd'), UC.getNode('yd*yd'), lambda d: d**2 ))
    # UC.addEdge(conversion(UC.getNode('ft*ft'), UC.getNode('ft'), lambda d: d**0.5 ))
    # UC.addEdge(conversion(UC.getNode('ft'), UC.getNode('ft*ft'), lambda d: d**2 ))
    # UC.addEdge(conversion(UC.getNode('in*in'), UC.getNode('in'), lambda d: d**0.5 ))
    # UC.addEdge(conversion(UC.getNode('in'), UC.getNode('in*in'), lambda d: d**2 ))

    # volume conversions
    UC.addEdge(conversion(UC.getNode('gill'), UC.getNode('fuild ounce'), lambda v: v*5))
    UC.addEdge(conversion(UC.getNode('pint'), UC.getNode('gill'), lambda v: v*4))
    UC.addEdge(conversion(UC.getNode('quart'), UC.getNode('pint'), lambda v: v*2))
    UC.addEdge(conversion(UC.getNode('gallonUK'), UC.getNode('quart'), lambda v: v*4))
    UC.addEdge(conversion(UC.getNode('gallonUS'), UC.getNode('cubic inch'), lambda v: v*231))
    UC.addEdge(conversion(UC.getNode('gallonUK'), UC.getNode('liter'), lambda v: v* 4.54609))
    UC.addEdge(conversion(UC.getNode('cubic foot'), UC.getNode('cubic meter'), lambda v: v*(3048**3)/(10000**3)))
    UC.addEdge(conversion(UC.getNode('standard cubic foot'), UC.getNode('standard cubic meter'), lambda v: v*(3048**3)/(10000**3)))
    UC.addEdge(conversion(UC.getNode('standard barrel'), UC.getNode('USgal'), lambda v: v*42))
    UC.addEdge(conversion(UC.getNode('standard cubic meter'), UC.getNode('standard barrel'), lambda v: v*6.289814))
    UC.addEdge(conversion(UC.getNode('standard cubic meter'), UC.getNode('litre'), lambda v: v*1000))
    UC.addEdge(conversion(UC.getNode('standard barrel'), UC.getNode('standard cubic foot'), lambda v: v*5.614584))
    UC.addEdge(conversion(UC.getNode('reservoir cubic meter'), UC.getNode('reservoir barrel'), lambda v: v*6.289814))
    UC.addEdge(conversion(UC.getNode('reservoir cubic meter'), UC.getNode('standard cubic meter'), lambda v: v / get_fvf()))
    # UC.addEdge(conversion(UC.getNode('standard cubic meter'), UC.getNode('standard cubic foot'), lambda v: v/5.614584))
    UC.addEdge(conversion(UC.getNode('KSM3'), UC.getNode('sm3'), lambda v: v*1E3))
    UC.addEdge(conversion(UC.getNode('MSM3'), UC.getNode('sm3'), lambda v: v*1E6))
    UC.addEdge(conversion(UC.getNode('SM3'), UC.getNode('KSM3'), lambda v: v/1000))

    # pressure conversions
    UC.addEdge(conversion(UC.getNode('psi gauge'), UC.getNode('absolute psi'), lambda p: p+14.6959))
    UC.addEdge(conversion(UC.getNode('absolute psi'), UC.getNode('psi gauge'), lambda p: p-14.6959))
    UC.addEdge(conversion(UC.getNode('bar gauge'), UC.getNode('bara'), lambda p: p+1.01325))
    UC.addEdge(conversion(UC.getNode('absolute bar'), UC.getNode('bar gauge'), lambda p: p-1.01325))

    UC.addEdge(conversion(UC.getNode('bara'), UC.getNode('Pascal'), lambda p: p*100000))
    UC.addEdge(conversion(UC.getNode('atmosphere'), UC.getNode('absolute bar'), lambda p: p*1.01325))
    UC.addEdge(conversion(UC.getNode('absolute bar'), UC.getNode('absolute psi'), lambda p: p*14.503773773022))
    UC.addEdge(conversion(UC.getNode('bar gauge'), UC.getNode('psi gauge'), lambda p: p*14.503773773022))
    UC.addEdge(conversion(UC.getNode('atmosphere'), UC.getNode('Pascal'), lambda p: p*101325))
    UC.addEdge(conversion(UC.getNode('atmosphere'), UC.getNode('Torr'), lambda p: p*760))

    # conversion weight
    UC.addEdge(conversion(UC.getNode('grain'), UC.getNode('milligrams'), lambda w: w*64.7989))
    UC.addEdge(conversion(UC.getNode('pennyweight'), UC.getNode('grain'), lambda w: w*24))
    UC.addEdge(conversion(UC.getNode('dram'), UC.getNode('pound'), lambda w: w/256))
    UC.addEdge(conversion(UC.getNode('stone'), UC.getNode('pound'), lambda w: w*14))
    UC.addEdge(conversion(UC.getNode('quarter'), UC.getNode('stone'), lambda w: w*2))
    UC.addEdge(conversion(UC.getNode('ounce'), UC.getNode('dram'), lambda w: w*16))
    UC.addEdge(conversion(UC.getNode('pound'), UC.getNode('ounce'), lambda w: w*16))
    UC.addEdge(conversion(UC.getNode('long hundredweight'), UC.getNode('quarter'), lambda w: w*4))
    UC.addEdge(conversion(UC.getNode('short hundredweight'), UC.getNode('pound'), lambda w: w*100))
    UC.addEdge(conversion(UC.getNode('short ton'), UC.getNode('short hundredweight'), lambda w: w*20))
    UC.addEdge(conversion(UC.getNode('long ton'), UC.getNode('long hundredweight'), lambda w: w*20))
    UC.addEdge(conversion(UC.getNode('metric ton'), UC.getNode('kilogram'), lambda w: w*1000))
    UC.addEdge(conversion(UC.getNode('kilogram'), UC.getNode('gram'), lambda w: w*1000))
    UC.addEdge(conversion(UC.getNode('pound'), UC.getNode('gram'), lambda w: w*453.59237))
    UC.addEdge(conversion(UC.getNode('pound'), UC.getNode('kilogram'), lambda w: w*0.45359237))

    # force conversion
    # UC.addEdge(conversion(UC.getNode('kilogram'), UC.getNode('kilogram force'), lambda f: f* converter(StandadEarthGravity, 'm/s2', 'cm/s2', False) ))
    UC.addEdge(conversion(UC.getNode('kilogram mass'), UC.getNode('kilogram force'), lambda f: f* StandadEarthGravity ))
    UC.addEdge(conversion(UC.getNode('Dyne'), UC.getNode('Newton'), lambda f: f*1E-5 ))
    UC.addEdge(conversion(UC.getNode('Newton'), UC.getNode('Dyne'), lambda f: f*1E5 ))


    # density conversion
    UC.addEdge(conversion(UC.getNode('API'), UC.getNode('SgO'), lambda d: 141.5/(131.5+d) ))
    UC.addEdge(conversion(UC.getNode('SgO'), UC.getNode('API'), lambda d: 141.5/d-131.5 ))
    UC.addEdge(conversion(UC.getNode('SgO'), UC.getNode('g/cc'), lambda d: d ))
    UC.addEdge(conversion(UC.getNode('SgW'), UC.getNode('g/cc'), lambda d: d ))
    UC.addEdge(conversion(UC.getNode('SgG'), UC.getNode('g/cc'), lambda d: d * StandardAirDensity ))
    UC.addEdge(conversion(UC.getNode('psia/ft'), UC.getNode('lb/ft3'), lambda d: d*144 ))
    UC.addEdge(conversion(UC.getNode('g/cm3'), UC.getNode('lb/ft3'), lambda d: d*62.427960576144606 ))
    UC.addEdge(conversion(UC.getNode('lb/ft3'), UC.getNode('lb/stb'), lambda d: d*5.614584 ))

    # viscosity conversions
    UC.addEdge(conversion(UC.getNode('Pa*s'), UC.getNode('Poise'), lambda v: v*10 ))

    # data conversions
    UC.addEdge(conversion(UC.getNode('byte'), UC.getNode('bit'), lambda d: d*8 ))
    UC.addEdge(conversion(UC.getNode('bit'), UC.getNode('byte'), lambda d: d/8 ))

    for unitKind in list(unit.dictionary.keys()):
        if '_REVERSE' in unitKind :
            if type(unit.dictionary[unitKind]) == dict :
                nameList = list(unit.dictionary[unitKind].keys())
            else:
                nameList = list(unit.dictionary[unitKind])
            # print(nameList)
            for unitName in nameList :
                # print('R  2: ' + unitName)
                for otherName in UC.childrenOf( UC.getNode(unitName) ) :
                    # print('R   3: '+unitName, otherName.getName())
                    if UC.getNode(unitName)!=otherName :
                        UC.addEdge(conversion(otherName, UC.getNode(unitName), UC.edges[ UC.getNode(unitName) ][1][ UC.edges[ UC.getNode(unitName) ][0].index(otherName) ], True  ))

    for unitKind in list(unit.dictionary.keys()):
        if '_FROMvolume' in unitKind and unitKind.split('_')[0] in unit.SI_order[2] :
            # if '_SI' in unitKind and unitKind.split('_')[0]  in unit.SI_order[2] :
            for unitName in list( unit.dictionary[unitKind] ) :
                # print('S  2: ' + unitName)
                UC.addNode(unit(unitName))
                unit.dictionary[unitKind.split('_')[0]].append(unitName)
                for otherName in UC.childrenOf( UC.getNode(unitName.split('/')[0] ) ) :
                    if UC.getNode(unitName.split('/')[0])!=otherName :
                        print('R   3: '+unitName, otherName.getName())
                        otherRate = otherName.getName() +'/'+ unitName.split('/')[1]
                        UC.addNode(unit( otherRate ))
                        UC.addEdge(conversion(UC.getNode(unitName), otherRate, UC.edges[ UC.getNode(unitName.split('/')[1]) ][1][ UC.edges[ UC.getNode(unitName.split('/')[1]) ][0].index(otherName) ]  ))
                        UC.addEdge(conversion(otherRate, UC.getNode(unitName), UC.edges[ UC.getNode(unitName.split('/')[1]) ][1][ UC.edges[ UC.getNode(unitName.split('/')[1]) ][0].index(otherName) ], True  ))

    for dic in unit.dictionary :
        if '_' not in dic :
            unit.dictionary[dic] = tuple(unit.dictionary[dic])

    return UC


def printPath(path):
    """Assumes path is a list of nodes"""
    result = '  '
    if len(path) == 1 :
        result = result + str(path[0]) + ' = ' + str(path[0])
    else:
        for i in range(len(path)):
            if type(path[i]) == str :
                result = result + ' ' +  path[i] + ' '
            else:
                result = result + str(path[i])
                if i != len(path) - 1:
                    result = result + ' 🠦 '
    return result


def BFS(graph, start, end, toPrint = False):
    """Assumes graph is a Digraph; start and end are nodes
        Returns a shortest path from start to end in graph"""
    initPath = [start]
    pathQueue = [initPath]
    visited = []
    while len(pathQueue) != 0:
        #Get and remove oldest element in pathQueue
        tmpPath = pathQueue.pop(0)
        if tmpPath in visited :
            if toPrint:
                print(' <UnitsConv> ' + str(len(pathQueue)) + ' paths in queue. ' + 'Already visited BFS path:\n', printPath(tmpPath))
        else:
            if toPrint:
                print(' <UnitsConv> ' + str(len(pathQueue)) + ' paths in queue. ' + 'Current BFS path:\n', printPath(tmpPath))
            lastNode = tmpPath[-1]
            if lastNode == end:
                return tmpPath
            for nextNode in graph.childrenOf(lastNode):
                if nextNode not in tmpPath:
                    newPath = tmpPath + [nextNode]
                    pathQueue.append(newPath)
            visited.append(tmpPath)
    return None




UnCo = UnitConversions()

def convertUnit(value, fromUnit, toUnit, PrintConversionPath=True ) :

    if type(PrintConversionPath) != bool :
        if type(PrintConversionPath) == int or type(PrintConversionPath) == float :
            if PrintConversionPath > 1 :
                PrintConversionPath = False
            else:
                PrintConversionPath = bool( PrintConversionPath )
        else:
            PrintConversionPath = True

    conv = converter( value, fromUnit, toUnit, PrintConversionPath )#[0]
    if type(conv) is not None :
        return conv
    else:
        if PrintConversionPath :
            print( " No conversion found from '" + fromUnit + "' to '" + toUnit + "' .\n ... returning the received value for '" + str(fromUnit) + "'." )
        if type(value) == float and int(value) == value :
            value = int(value)
        return value




def converter(value, fromUnit, toUnit, PrintConversionPath=True, AllowRecursion=unit.RecursionLimit, Start=True) :
    """
    returns the received value (string, float or numpy array) and transform it
    from the units 'fromUnit' to the units 'tuUnits
    """
    if value is None:
        return None
    if fromUnit is None or toUnit is None:
        return value

    if type(fromUnit) is str and type(toUnit) is str and fromUnit.lower().strip() == toUnit.lower().strip():
        return value

    if Start==True :
        unit.previous=[]

    # strip off the parentesis, the string o
    if type(fromUnit) == str and fromUnit not in ('"', "'") :
        fromUnit = fromUnit.strip("( ')").strip('"')
    if type(toUnit) == str and toUnit not in ('"', "'") :
        toUnit = toUnit.strip("( ')").strip('"')

    if fromUnit.lower().strip(' ()') in unit.dictionary['dimensionless'] or toUnit.lower().strip(' ()') in unit.dictionary['dimensionless'] :
        return value

    # if PrintConversionPath :
    #     print( "\n converting from '" + str(fromUnit) + "' to '" + str(toUnit) + "'")

    # if converting from or to any dimensionless units,
    # the other unit has to have the same in numerator and denominator
    for pair in ((fromUnit, toUnit), (toUnit, fromUnit)) :
        if pair[0].lower().strip(' ()') in unit.dictionary['dimensionless'] :
            if pair[1].lower().strip(' ()') not in unit.dictionary['dimensionless'] :
                if '/' in pair[1] :
                    if pair[1].split('/')[0] == pair[1].split('/')[1] :
                        return value
                    else:
                        unit.previous=(fromUnit, toUnit)
                        if ( pair[1].split('/')[0], pair[1].split('/')[1] ) in unit.Memory :
                            conv = unit.Memory[ ( pair[1].split('/')[0], pair[1].split('/')[1] ) ]
                        else:
                            conv = converter( 1, pair[1].split('/')[0], pair[1].split('/')[1], AllowRecursion, Start=False )
                            unit.Memory[ ( pair[1].split('/')[0], pair[1].split('/')[1] ) ] = conv
                        if type(conv) != None:
                            return value / conv

    if (fromUnit, toUnit) in unit.previous :
        AllowRecursion = 0
    unit.previous.append((fromUnit, toUnit))
    # try to found conversion path for the input parameters un the defined graph:
    try :
        conversionPath = BFS(UnCo, UnCo.getNode(fromUnit), UnCo.getNode(toUnit) )
    except : # if the units doesn't exists the BFS function returns error
        conversionPath = None

    # if direct conversion fail, try to divide the unit to it fundamental units
    if conversionPath is None and AllowRecursion > 0 :
        # print( 'doing something... /')
        operator = ''
        if fromUnit == toUnit or ( fromUnit in unit.dictionary['date'] and toUnit in unit.dictionary['date'] ) :
            partA = fromUnit
            partB = toUnit
            operator = ' = '
        # print(fromUnit, toUnit )
        if conversionPath is None and ( '/' in fromUnit or '/' in toUnit ) :
            AllowRecursion -= 1
            if '/' in fromUnit and '/' in toUnit :
                operator = ' / '
                if ( fromUnit.split('/')[0], toUnit.split('/')[0] ) in unit.Memory :
                    partA = value * unit.Memory[ ( fromUnit.split('/')[0], toUnit.split('/')[0] ) ] # numerator
                else:
                    partA = converter(  1, fromUnit.split('/')[0], toUnit.split('/')[0], PrintConversionPath, AllowRecursion, Start=False ) # numerator
                    unit.Memory[ ( fromUnit.split('/')[0], toUnit.split('/')[0] ) ] = partA

                    if partA is None:
                        partA = value
                        print('no conversion found from',fromUnit,'to',toUnit)
                    else:
                        partA = value * unit.Memory[ ( fromUnit.split('/')[0], toUnit.split('/')[0] ) ]
                if ( fromUnit.split('/')[1], toUnit.split('/')[1] ) in unit.Memory :
                    partB = unit.Memory[ ( fromUnit.split('/')[1], toUnit.split('/')[1] ) ]
                else:
                    partB = converter(    1, fromUnit.split('/')[1], toUnit.split('/')[1], PrintConversionPath, AllowRecursion, Start=False ) # denominator
                    unit.Memory[ ( fromUnit.split('/')[1], toUnit.split('/')[1] ) ]  = partB
                if type(partA) is None or type(partB) is None :
                    # if PrintConversionPath :
                    # print( "no conversion found from " + fromUnit + " to " + toUnit + " ." )
                    # conversionPath = None
                    for middleFrom in UnCo.childrenOf(UnCo.getNode(fromUnit)) : #+ UnCo.childrenOf(UnCo.getNode(fromUnit.split('/')[0])) + UnCo.childrenOf(UnCo.getNode(fromUnit.split('/')[1])) :
                        #for middleTo in UnCo.childrenOf(UnCo.getNode(toUnit)) : # + UnCo.childrenOf(UnCo.getNode(toUnit.split('/')[0])) + UnCo.childrenOf(UnCo.getNode(toUnit.split('/')[1])) :
                        middle = converter( converter( value, fromUnit, str(middleFrom), PrintConversionPath, Start=False ), str(middleFrom), toUnit, PrintConversionPath, AllowRecursion, Start=False )
                        if type(middle) is not None :
                            return middle
                        middle = converter( converter( value, fromUnit, str(middleFrom), PrintConversionPath, Start=False ), str(middleFrom), toUnit.split('/')[0], PrintConversionPath, AllowRecursion, Start=False )
                        if type(middle) is not None :
                            return middle
                        middle = converter( converter( value, fromUnit, str(middleFrom), PrintConversionPath, Start=False ), str(middleFrom), toUnit.split('/')[1], PrintConversionPath, AllowRecursion, Start=False )
                        if type(middle) is not None :
                            return 1/middle
                    for middleTo in UnCo.childrenOf(UnCo.getNode(toUnit)) :
                        middle = converter( value, fromUnit, str(middleTo), PrintConversionPath, AllowRecursion, Start=False )
                        if type(middle) is not None :
                            return converter( middle, str(middleTo), toUnit, PrintConversionPath, AllowRecursion, Start=False )

                    # return value
                else:
                    # if returnPath :
                    #     return ( partA, operator, partB)
                    # else:
                    return partA / partB
            elif '/' in fromUnit :
                # print('if / in fromUnit')
                for middleUnit in UnCo.childrenOf(UnCo.getNode(toUnit)) :
                    # print('from ' + fromUnit + ' to ' + str(middleUnit))
                    middle = converter(value, fromUnit, str(middleUnit), PrintConversionPath, AllowRecursion, Start=False )
                    if type(middle) is not None :
                        return converter(middle, str(middleUnit), toUnit, PrintConversionPath, AllowRecursion, Start=False )

            else: # elif '/' in toUnit :
                # print('if / in toUnit ')
                for middleUnit in UnCo.childrenOf(UnCo.getNode(fromUnit)) :
                    # print('from ' + fromUnit + ' to ' + str(middleUnit))
                    middle = converter( converter( value, fromUnit, str(middleUnit), PrintConversionPath ), str(middleUnit), toUnit, PrintConversionPath, AllowRecursion, Start=False )
                    if type(middle) is not None :
                        return middle
            return None


    # if direct conversion fail, try to multiply the unit to it fundamental units
    if conversionPath is None and AllowRecursion > 0 :
        # print( 'doing something... *')
        operator = ''
        if fromUnit == toUnit or ( fromUnit in unit.dictionary['date'] and toUnit in unit.dictionary['date'] ) :
            partA = fromUnit
            partB = toUnit
            operator = ' = '

        if conversionPath is None and ( '*' in fromUnit or '*' in toUnit ) :
            AllowRecursion -= 1
            if '*' in fromUnit and '*' in toUnit :
                operator = ' * '
                partA = converter(value, fromUnit.split('*')[0], toUnit.split('*')[0], PrintConversionPath, AllowRecursion, Start=False ) # 1st factor
                partB = converter(    1, fromUnit.split('*')[1], toUnit.split('*')[1], PrintConversionPath, AllowRecursion, Start=False ) # 2nd factor
                if type(partA) is None or type(partB) is None :
                    # if PrintConversionPath :
                    # print( "no conversion found from " + fromUnit + " to " + toUnit + " ." )
                    # conversionPath = None
                    for middleFrom in UnCo.childrenOf(UnCo.getNode(fromUnit)) : #+ UnCo.childrenOf(UnCo.getNode(fromUnit.split('/')[0])) + UnCo.childrenOf(UnCo.getNode(fromUnit.split('/')[1])) :
                        #for middleTo in UnCo.childrenOf(UnCo.getNode(toUnit)) : # + UnCo.childrenOf(UnCo.getNode(toUnit.split('/')[0])) + UnCo.childrenOf(UnCo.getNode(toUnit.split('/')[1])) :
                        middle = converter( converter( value, fromUnit, str(middleFrom), PrintConversionPath, AllowRecursion, Start=False ), str(middleFrom), toUnit, PrintConversionPath, AllowRecursion, Start=False )
                        if type(middle) is not None :
                            return middle
                        middle = converter( converter( value, fromUnit, str(middleFrom), PrintConversionPath, AllowRecursion, Start=False ), str(middleFrom), toUnit.split('/')[0], PrintConversionPath, AllowRecursion, Start=False )
                        if type(middle) is not None :
                            return middle
                        middle = converter( converter( value, fromUnit, str(middleFrom), PrintConversionPath, AllowRecursion, Start=False ), str(middleFrom), toUnit.split('/')[1], PrintConversionPath, AllowRecursion, Start=False )
                        if type(middle) is not None :
                            return 1/middle
                    for middleTo in UnCo.childrenOf(UnCo.getNode(toUnit)) :
                        middle = converter( value, fromUnit, str(middleTo), PrintConversionPath, AllowRecursion, Start=False )
                        if type(middle) is not None :
                            return converter( middle, str(middleTo), toUnit, PrintConversionPath, AllowRecursion, Start=False )

                    # return value
                else:
                    # if returnPath :
                    #     return ( partA, operator, partB)
                    # else:
                    return partA * partB
            elif '*' in fromUnit :
                # print('if * in fromUnit')
                for middleUnit in UnCo.childrenOf(UnCo.getNode(toUnit)) :
                    # print('from ' + fromUnit + ' to ' + str(middleUnit))
                    middle = converter(value, fromUnit, str(middleUnit), PrintConversionPath, AllowRecursion, Start=False )
                    if type(middle) is not None :
                        return converter(middle, str(middleUnit), toUnit, PrintConversionPath, AllowRecursion, Start=False )

            else: # elif '*' in toUnit :
                # print('if * in toUnit ')
                for middleUnit in UnCo.childrenOf(UnCo.getNode(fromUnit)) :
                    # print('from ' + fromUnit + ' to ' + str(middleUnit))
                    middle = converter( converter( value, fromUnit, str(middleUnit), PrintConversionPath, AllowRecursion, Start=False ), str(middleUnit), toUnit, PrintConversionPath, AllowRecursion, Start=False )
                    if type(middle) is not None :
                        return middle
            return None


    if conversionPath is None :
        # if PrintConversionPath :
        # print( "no conversion found from " + fromUnit + " to " + toUnit + " ." )
        return None

    # if returnPath :
    #     return conversionPath

    if type(value) in [list, tuple] :
        value = numpy.array(value)
    if PrintConversionPath is True and conversionPath is not None:
        # print( "\n converting from '" + str(fromUnit) + "' to '" + str(toUnit) + "'")
        print( "\n converting from '" + str(fromUnit) + "' to '" + str(toUnit) + "'\n  " + printPath(conversionPath) )
    for conversion in range(len(conversionPath)-1) :
        value = UnCo.convert(value, conversionPath[conversion], conversionPath[conversion+1])
    # if type(value) == float and int(value) == value :
    #     value = int(value)

    return value


def convertible(fromUnit, toUnit, PrintPath=False) :
    try :
        if converter(1, fromUnit, toUnit, PrintPath) is not None :
            return True
        else:
            return False
    except :
        return False



# def basicsProduct(basics1, basics2):
#     knownBasics = {lenght : {lenght : area,
#                              area : volume},
#                    area : {lenght : volume }
#                    }
#     if basics1 in knownBasics :
#         if basics2 in knownBasics :
#             return knownBasics[basics1][basics2]
#     return basics

# def basicsDiv(basics1, basics2):
#     knownBasics = {area : {lenght : lenght},
#                    volume : {lenght : area,
#                              area : lenght}
#                    }
#     if basics1 in knownBasics :
#         if basics2 in knownBasics :
#             return knownBasics[basics1][basics2]
#     return basics

# def unitProduct2(unit1, unit2):
#     prod = []
#     for u in unit1.split('_').append( unit2.split('_') ) :
#         rept = ''
#         for i in len(u) :
#             try :
#                 rept += str(int(i))
#             except :
#                 pass
    # return unit1 + '*' + unit2

def unitBasePower(unit):
    Ubas, Upow = '', ''
    oth = ''
    for c in unit :
        if c.isdigit() :
            Upow += oth + c
            oth = ''
        elif c in ['-', '+', '.'] :
            oth += c
        else:
            Ubas += oth + c
            oth = ''
    Upow = 1 if Upow == '' else float(Upow) if '.' in Upow else int(Upow)
    return Ubas, Upow

def unitBase(unit):
    return unitBasePower(unit)[0]

def unitPower(unit):
    return unitBasePower(unit)[1]

def unitProduct(unit1, unit2):

    if unit1 is None :
        unit1 = 'dimensionless'
    if unit2 is None :
        unit2 = 'dimensionless'

    if type(unit1) is str and len(unit1.strip(' ()'))==0 :
        unit1 = 'dimensionless'
    if type(unit2) is str and len(unit2.strip(' ()'))==0 :
        unit2 = 'dimensionless'

    if unit2.lower().strip(' ()') in unit.dictionary['dimensionless'] :
        return unit1
    if unit1.lower().strip(' ()') in unit.dictionary['dimensionless'] :
        if unit2.lower().strip(' ()') not in unit.dictionary['dimensionless'] :
            return unit2
        else:
            return unit1

    if unit1 != unit2 and convertible(unit1, unit2) :
        return unitProduct(unit1, unit1)

    U1bas, U1pow, U2bas, U2pow = '', '', '', ''
    oth = ''

    for c in unit1 :
        if c.isdigit() :
            U1pow += oth + c
            oth = ''
        elif c in ['-', '+', '.'] :
            oth += c
        else:
            U1bas += oth + c
            oth = ''
    U1pow = 1 if U1pow == '' else float(U1pow) if '.' in U1pow else int(U1pow)

    for c in unit2 :
        if c.isdigit() :
            U2pow += c
        else:
            U2bas += c
    U2pow = 1 if U2pow == '' else float(U2pow) if '.' in U2pow else int(U2pow)

    if convertible(U1bas, U2bas) :
        Upow = U1pow+U2pow
        if Upow == -1 :
            result = '1/'+U1bas
        elif Upow == 1 :
            result = U1bas
        elif Upow == 0 :
            result = 'dimensionless'
        else:
            for c in ['+', '-', '*', '/', '^'] :
                if c in U1bas :
                    U1bas = '('+U1bas+')'
                    break
            result = U1bas + str(Upow)

    else:
        for c in ['+', '-', '*', '/', '^'] :
            if c in U1bas :
                U1bas = '('+U1bas+')'
                break
        for c in ['+', '-', '*', '/', '^'] :
            if c in U2bas :
                U2bas = '('+U2bas+')'
                break
        result = U1bas + '*' + U2bas

    return result


def unitDivision(unit1, unit2):

    if unit1 is None :
        unit1 = 'dimensionless'
    if unit2 is None :
        unit2 = 'dimensionless'

    if unit1 == unit2:
        return 'dimensionless'

    if type(unit1) is str and len(unit1.strip(' ()'))==0 :
        unit1 = 'dimensionless'
    if type(unit2) is str and len(unit2.strip(' ()'))==0 :
        unit2 = 'dimensionless'

    if unit2.lower().strip(' ()') in unit.dictionary['dimensionless'] :
        return unit1
    if unit1.lower().strip(' ()') in unit.dictionary['dimensionless'] :
        if unit2.lower().strip(' ()') not in unit.dictionary['dimensionless'] :
            return '1/'+unit2
        else:
            return unit1

    # if '/' in unit1 and '/' in unit2:
    #     if len(unit1.split('/')) == 2 and len(unit2.split('/')) == 2:
    #         if unit1.split('/')[1] == unit2.split('/')[1] and unit1.split('/')[0] != unit2.split('/')[0]:
    #             return unit1.split('/')[0] + '/' + unit2.split('/')[0]
    #         if unit1.split('/')[0] == unit0.split('/')[0] and unit1.split('/')[1] != unit2.split('/')[1]:
    #             return unit2.split('/')[1] + '/' + unit1.split('/')[1]

    if unit1 != unit2 and convertible(unit1, unit2):
        return unitDivision(unit1, unit1)

    U1bas, U1pow, U2bas, U2pow = '', '', '', ''
    oth = ''
    for c in unit1 :
        if c.isdigit() :
            U1pow += oth + c
            oth = ''
        elif c in ['-', '+', '.'] :
            oth += c
        else:
            U1bas += oth + c
            oth = ''

    U1pow = 1 if U1pow == '' else float(U1pow) if '.' in U1pow else int(U1pow)
    for c in unit2 :
        if c.isdigit() :
            U2pow += c
        else:
            U2bas += c
    U2pow = 1 if U2pow == '' else float(U2pow) if '.' in U2pow else int(U2pow)

    if convertible(U1bas, U2bas) :
        Upow = U1pow-U2pow
        if Upow == -1 :
            result = '1/'+U1bas
        elif Upow == 1 :
            result = U1bas
        elif Upow == 0 :
            result = 'dimensionless'
        else:
            for c in ['+', '-', '*', '/', '^'] :
                if c in U1bas :
                    U1bas = '('+U1bas+')'
                    break
            result = U1bas + str(Upow)

    else:
        for c in ['+', '-', '*', '/', '^'] :
            if c in U1bas :
                U1bas = '('+U1bas+')'
                break
        for c in ['+', '-', '*', '/', '^'] :
            if c in U2bas :
                U2bas = '('+U2bas+')'
                break
        result = U1bas + '/' + U2bas

    return result


class basics(object) :
    def __init__(self) :
        self.unit = None
        self.value = None
        self.name = None
    def __call__(self):
        return self.value
    def __repr__(self):
        return str(self.value) + '_' + str(self.unit)
    def __str__(self) :
        return str(self.value) + '_' + str(self.unit)
    def convert(self, newunit):
        if type(newunit) != str :
            try :
                newunit = newunit.unit
            except :
                raise WrongUnits
        return self.name( converter(self.value, self.unit, newunit), newunit, False )
    def to(self, newunit):
        return self.convert(newunit)
    def __add__(self, other) :
        if type(other) == type(self) :
            if self.unit != other.unit :
                return self.name(self.value + converter(other.value, other.unit, self.unit), self.unit)
            else:
                return self.name(self.value + other.value, self.unit)
        elif type(other) == int or type(other) == float :
            return self.name(self.value + other, self.unit)
    def __radd__(self, other) :
        return self.__add__(other)

    # def __mul2__(self, other) :
    #     if type(other) == type(self) :
    #         if self.unit != other.unit :
    #             return makeUnit(self.value * converter(other.value, other.unit, self.unit), unitProduct2(self.unit, self.unit) )
    #         else:
    #             return makeUnit(self.value * other.value, unitProduct(self.unit, self.unit) )
    #     elif type(other) == int or type(other) == float or type(other) == numpy.ndarray :
    #         return self.name(self.value * other, self.unit)
    #     else:
    #         return basicsProduct(self.name, other.name)(self.value * other.value, unitProduct(self.unit, other.unit))


    def __mul__(self, other) :
        if self.name == dimensionless :
            try:
                if type(other.name) == type :
                    return other.name(self.value * other.value, other.unit)
            except :
                pass
        if type(other) == type(self):
            if self.unit != other.unit :
                return basicsProduct(self.name, other.name)(self.value * converter(other.value, other.unit, self.unit), unitProduct(self.unit, self.unit))
            else:
                return basicsProduct(self.name, other.name)(self.value * other.value, unitProduct(self.unit, other.unit))
        elif type(other) == int or type(other) == float or type(other) == numpy.ndarray :
            return self.name(self.value * other, self.unit)
        else:
            try:
                if other.name == dimensionless :
                    return self.name(self.value * other.value, self.unit)
                else:
                    return basicsProduct(self.name, other.name)(self.value * other.value, unitProduct(self.unit, other.unit))
            except :
                return basicsProduct(self.name, other.name)(self.value * other.value, unitProduct(self.unit, other.unit))
    def __rmul__(self, other) :
        return self.__mul__(other)
    def __sub__(self, other) :
        return self.__add__(other*-1)
    def __rsub__(self, other) :
        return self.__sub__(other)
    def __truediv__(self, other):
        if type(other) == type(self) :
            if self.unit != other.unit :
                return self.value / converter(other.value, other.unit, self.unit)
            else:
                return self.value / other.value
        elif type(other) == int or type(other) == float :
            return self.__mul__(1/other)
        else:
            pass
    def __rtruediv__(self, other):
        return self.__truediv__(other)
    def __lt__(self, other) :
        if type(self) == type(other) :
            return self.value < other.convert(self.unit).value
        else:
            msg = "'<' not supported between instances of '" +   (str(type(self))[str(type(self)).index("'")+1:len(str(type(self))) - str(type(self))[::-1].index("'")-1]).replace('__main__.', '')   + "' and '" +   (str(type(other))[str(type(other)).index("'")+1:len(str(type(other))) - str(type(other))[::-1].index("'")-1]).replace('__main__.', '')   + "'"
            raise TypeError(msg)
    def __le__(self, other) :
        if type(self) == type(other) :
            return self.value <= other.convert(self.unit).value
        else:
            msg = "'<=' not supported between instances of '" +   (str(type(self))[str(type(self)).index("'")+1:len(str(type(self))) - str(type(self))[::-1].index("'")-1]).replace('__main__.', '')   + "' and '" +   (str(type(other))[str(type(other)).index("'")+1:len(str(type(other))) - str(type(other))[::-1].index("'")-1]).replace('__main__.', '')   + "'"
            raise TypeError(msg)
    def __eq__(self, other) :
        if type(self) == type(other) :
            return self.value == other.convert(self.unit).value
        else:
            msg = "'==' not supported between instances of '" +   (str(type(self))[str(type(self)).index("'")+1:len(str(type(self))) - str(type(self))[::-1].index("'")-1]).replace('__main__.', '')   + "' and '" +   (str(type(other))[str(type(other)).index("'")+1:len(str(type(other))) - str(type(other))[::-1].index("'")-1]).replace('__main__.', '')   + "'"
            raise TypeError(msg)
    def __ne__(self, other) :
        if type(self) == type(other) :
            return self.value != other.convert(self.unit).value
        else:
            msg = "'!=' not supported between instances of '" +   (str(type(self))[str(type(self)).index("'")+1:len(str(type(self))) - str(type(self))[::-1].index("'")-1]).replace('__main__.', '')   + "' and '" +   (str(type(other))[str(type(other)).index("'")+1:len(str(type(other))) - str(type(other))[::-1].index("'")-1]).replace('__main__.', '')   + "'"
            raise TypeError(msg)
    def __ge__(self, other) :
        if type(self) == type(other) :
            return self.value >= other.convert(self.unit).value
        else:
            msg = "'>=' not supported between instances of '" +   (str(type(self))[str(type(self)).index("'")+1:len(str(type(self))) - str(type(self))[::-1].index("'")-1]).replace('__main__.', '')   + "' and '" +   (str(type(other))[str(type(other)).index("'")+1:len(str(type(other))) - str(type(other))[::-1].index("'")-1]).replace('__main__.', '')   + "'"
            raise TypeError(msg)
    def __gt__(self, other) :
        if type(self) == type(other) :
            return self.value > other.convert(self.unit).value
        else:
            msg = "'>' not supported between instances of '" +   (str(type(self))[str(type(self)).index("'")+1:len(str(type(self))) - str(type(self))[::-1].index("'")-1]).replace('__main__.', '')   + "' and '" +   (str(type(other))[str(type(other)).index("'")+1:len(str(type(other))) - str(type(other))[::-1].index("'")-1]).replace('__main__.', '')   + "'"
            raise TypeError(msg)
    def __len__(self) :
        try :
            return len(self.value)
        except :
            return 1
    def __getitem__(self, item) :
        if type(item) == int :
            if item >= len(self) :
                raise IndexError
        else:
            raise ValueError
        return self.value[item]
    def __iter__(self) :
        if type(self.value) == int or type(self.value) == float :
            return numpy.array((self.value, )).__iter__()
        else:
            return self.value.__iter__()
    # def __next__(self) :
    #     pass
    def getUnit(self) :
        return self.unit
    def getValue(self) :
        return self.value
    def checkValue(self, value):
        if type(value) == list or type(value) == list :
            return numpy.array(value)
        elif type(value) == int or type(value) == float :
            return value
        elif type(value) == numpy.ndarray :
            return value
        # elif type(value) == pandas.core.frame.DataFrame :
        #     return value
        else:
            raise WrongValue
    def checkUnit(self, units) :
        if type(units) != str :
            try :
                units = units.unit
            except :
                raise WrongUnits
        if units in self.name.classUnits :
            return units
        else:
            raise WrongUnits

class time(basics):
    classUnits = unit.dictionary['time']
    def __init__(self, value, units) :
        self.name = time
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

class temperature(basics):
    classUnits = unit.dictionary['temperature']
    def __init__(self, value, units) :
        self.name = temperature
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

class pressure(basics):
    classUnits = unit.dictionary['pressure']
    def __init__(self, value, units) :
        self.name = pressure
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

class weight(basics):
    classUnits = unit.dictionary['weight']
    def __init__(self, value, units) :
        self.name = weight
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

class lenght(basics):
    classUnits = unit.dictionary['lenght']
    def __init__(self, value, units) :
        self.name = lenght
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

class area(basics):
    classUnits = unit.dictionary['area']
    def __init__(self, value, units) :
        self.name = area
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

class volume(basics):
    classUnits = unit.dictionary['volume']
    def __init__(self, value, units) :
        self.name = volume
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

class density(basics):
    classUnits = unit.dictionary['density']
    def __init__(self, value, units) :
        self.name = density
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

class compressibility(basics):
    classUnits = unit.dictionary['compressibility']
    def __init__(self, value, units) :
        self.name = compressibility
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

# class volumeRatio(basics):
#     classUnits = unit.dictionary['volumeRatio']
#     def __init__(self, value, units) :
#         self.name = volumeRatio
#         self.value = self.checkValue(value)
#         self.unit = self.checkUnit(units)

class rate(basics):
    classUnits = unit.dictionary['rate']
    def __init__(self, value, units) :
        self.name = rate
        self.value = self.checkValue(value)
        self.unit = self.checkUnit(units)

# class productivityIndex(basics):
#     classUnits = unit.dictionary['productivityIndex']
#     def __init__(self, value, units) :
#         self.name = productivityIndex
#         self.value = self.checkValue(value)
#         self.unit = self.checkUnit(units)

# class pressureGradient(basics):
#     classUnits = unit.dictionary['pressureGradient']
#     def __init__(self, value, units) :
#         self.name = pressureGradient
#         self.value = self.checkValue(value)
#         self.unit = self.checkUnit(units)


class dimensionless(basics):
    classUnits = unit.dictionary['dimensionless']
    def __init__(self, value, units=None) :
        self.name = dimensionless
        self.value = self.checkValue(value)
        if units == None :
            units = 'dimensionless'
        self.unit = self.checkUnit(units)

# class userUnits(basics):
#     classUnits = unit.dictionary['customUnits']
#     def __init__(self, value, units) :
#         self.name = userUnits
#         userUnits.classUnits = tuple(unit.customUnits)
#         self.value = self.checkValue(value)
#         self.unit = self.checkUnit(units)

# def makeUnit(value=None, units=None) :
#     if value != None and units != None :
#         if units in unit.dictionary['temperature'] :
#             return temperature(value, units)
#         elif units in unit.dictionary['lenght'] :
#             return lenght(value, units)
#         elif units in unit.dictionary['area'] :
#             return area(value, units)
#         elif units in unit.dictionary['volume'] :
#             return volume(value, units)
#         elif units in unit.dictionary['pressure'] :
#             return pressure(value, units)
#         elif units in unit.dictionary['weight'] :
#             return weight(value, units)
#         elif units in unit.dictionary['density'] :
#             return density(value, units)
#         elif units in unit.dictionary['compressibility'] :
#             return compressibility(value, units)
#         elif units in unit.dictionary['volumeRatio'] :
#             return volumeRatio(value, units)
#         elif units in unit.dictionary['rate'] :
#             return rate(value, units)
#         else:
#             print('WARNING: unit "' + str(units) + '" not found in library, using customUnits.\n         Unit conversion is not possible.')
#             unit.dictionary['customUnits'].append(units)
#             return userUnits(value, units)
#     elif value != None or units != None :
#         if units == None :
#             raise WrongUnits('missing units, must be a string')
#         else:
#             raise WrongValue('missing value, may be float, integer, list, tuple or numpy.array')
#     else:
#         raise WrongValue