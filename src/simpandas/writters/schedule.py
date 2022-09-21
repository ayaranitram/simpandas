# -*- coding: utf-8 -*-
"""
Created on Wed Sep 21 11:08:06 2022

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.1.1'
__release__ = 20220921
__all__ = ['write_schedule']

from .._Classes.errors import OverwrittingError
import os
# from .._common.stringformat import date as strDate
from pandas import DataFrame

def write_schedule(self, path, units='FIELD', ControlMode=None, ShutStop=None):
    """
    export a eclipse style schedule file.

    Parameters
    ----------
    units : str or dict, optional
        a string 'FIELD', 'METRIC', LAB or PVT-M will convert the data to the corresponding eclipse simulator units system.
        a dictionary should contain desired units for all the columns to be converted. The default is None.
    ControlMode : str or dict, optional
        a string defining the control mode for the simulation:'ORAT','WRAT','GRAT'
        a dictionary with pairs of item:ControlModel for each item (well or group).
    ShutStop : str, optional
        a string 'OPEN, 'SHUT' or 'STOP' indicating what to do with the wells when their rate is zero.


    Returns
    -------
    None.
    """
    if os.path.isfile(path):
        raise OverwrittingError("The output file already exists:\n  '"+str(path)+"'")

    eclipseUnits0 = {'FIELD':{'OPR':'stb/day',  # Oil rate
                             'WPR':'stb/day',  # Water rate
                             'GPR':'Mscf/day',  # Gas rate
                             'LPR':'stb/day',  # Liquid rate
                             # 'RFR':'rb/day',  # Reservoir fluid volume rate
                             'BHP':'psia',  # BHP
                             'THP':'psia',  # THP
                             # 'WGPR': 'Mscf/day',  # Wet gas production rate
                             # 'TMR':'lb-M/day',  # Total molar rate
                             # 'SPR': 'stb/day',  # Steam production rate
                             },
                    'METRIC':{'OPR':'sm3/day',  # Oil rate
                             'WPR':'sm3/day',  # Water rate
                             'GPR':'sm3/day',  # Gas rate
                             'LPR':'sm3/day',  # Liquid rate
                             # 'RFR':'rm3/day',  # Reservoir fluid volume rate
                             'BHP':'barsa',  # BHP
                             'THP':'barsa',  # THP
                             # 'WGPR': 'sm3/day',  # Wet gas production rate
                             # 'TMR':'kg-M/day',  # Total molar rate
                             # 'SPR': 'sm3/day',  # Steam production rate
                             },
                    'LAB':{'OPR':'scc/hr',  # Oil rate
                             'WPR':'scc/hr',  # Water rate
                             'GPR':'scc/hr',  # Gas rate
                             'LPR':'scc/hr',  # Liquid rate
                             # 'RFR':'rcc/hr',  # Reservoir fluid volume rate
                             'BHP':'atma',  # BHP
                             'THP':'atma',  # THP
                             # 'WGPR': 'Mscf/day',  # Wet gas production rate
                             # 'TMR':'lb-M/day',  # Total molar rate
                             # 'SPR': 'stb/day',  # Steam production rate
                             },
                    'PVT-M':{'OPR':'sm3/day',  # Oil rate
                             'WPR':'sm3/day',  # Water rate
                             'GPR':'sm3/day',  # Gas rate
                             'LPR':'sm3/day',  # Liquid rate
                             # 'RFR':'rm3/day',  # Reservoir fluid volume rate
                             'BHP':'atma',  # BHP
                             'THP':'atma',  # THP
                             # 'WGPR': 'Mscf/day',  # Wet gas production rate
                             # 'TMR':'lb-M/day',  # Total molar rate
                             # 'SPR': 'stb/day',  # Steam production rate
                             }}

    # create dictionary for keyword parameters
    if units in eclipseUnits0:
        # eclipseUnits = {}
        # for each in eclipseUnits0[units]:
        #     for X in 'FGW':
        #         for H in ' H':
        #             eclipseUnits[X+each+H.strip()] = eclipseUnits0[units][each]
        # del eclipseUnits0
        # units = eclipseUnits
        units = { X+each+H.strip():eclipseUnits0[units][each] for each in eclipseUnits0[units] for X in 'FGW' for H in ' H' }
        del eclipseUnits0

    data = self.to(units).wellStatus().melt()

    indexName = data.index.name
    itemName = data.columns[2]

    if indexName is not None and itemName is not None and len(indexName)>0 and len(itemName)>0:
        data = data.reset_index().sort_values(by=[indexName,itemName,'attribute'],axis=0,ascending=True).set_index(indexName)
    else:
        data = data.melt().sort_index(axis=0,ascending=True)

    out = {'WCONHIST':DataFrame(index=data[itemName].unique(), columns=range(2,13)),
           'WCONINJH':DataFrame(index=data[itemName].unique(), columns=range(2,13)),
           'WCONPROD':DataFrame(index=data[itemName].unique(), columns=range(2,21)),
           'WCONINJE':DataFrame(index=data[itemName].unique(), columns=range(2,16))}

    if ShutStop is None:
        ShutStop = 'STOP'

    if type(ControlMode) is str:
        ControlMode = { item:ControlMode for item in data[itemName].unique() }

    itemCol = 2
    valueCol = 0
    attCol = 1

    curtime = ''
    lastime = None
    i = 0

    GORcriteria = 10

    outstr = []

    for i in range(len(data)):
        curtime = data.iloc[i].name
        if i == 0:
            lastime = curtime

        if lastime != curtime or i == len(data)-1:
            # prepare keywords to write
            out['WCONHIST']['keyword'] = 'WCONHIST'
            out['WCONINJH']['keyword'] = 'WCONINJH'
            out['WCONPROD']['keyword'] = 'WCONPROD'
            out['WCONINJE']['keyword'] = 'WCONINJE'
            keywords = out['WCONHIST'].append(out['WCONINJH']).append(out['WCONPROD']).append(out['WCONINJE'])
            keywords.dropna(axis=0, how='all',subset=range(2,13),inplace=True)

            prodh = keywords['keyword'] == 'WCONHIST'
            keywords.loc[prodh,2] = [ 'OPEN' if each else ShutStop for each in (keywords.loc[prodh,4:6].sum(axis=1) > 0) ]

            injeh = keywords['keyword'] == 'WCONINJH'
            keywords.loc[injeh,3] = [ 'OPEN' if each else ShutStop for each in (keywords.loc[injeh,4] > 0) ]

            prodf = keywords['keyword'] == 'WCONPROD'
            keywords.loc[prodf,2] = [ 'OPEN' if each else ShutStop for each in (keywords.loc[prodf,4:7].sum(axis=1) > 0) ]

            injef = keywords['keyword'] == 'WCONINJE'
            keywords.loc[injef,3] = [ 'OPEN' if each else ShutStop for each in (keywords.loc[injef,5:6].sum(axis=1) > 0) ]

            if ControlMode is None or item not in ControlMode:
                notnull = keywords.loc[prodh,[4,6,5]].notna()
                checkgor = DataFrame({4: keywords.loc[prodh,4].fillna(0) * GORcriteria > keywords.loc[prodh,6].fillna(0) , 5: (keywords.loc[prodh,5].notna()) & ((keywords.loc[prodh,4].isna()) & (keywords.loc[prodh,6].isna())) , 6: keywords.loc[prodh,4].fillna(0) * GORcriteria <= keywords.loc[prodh,6].fillna(0) })
                keywords.loc[prodh,3] = ((notnull*checkgor).astype(int) *   np.array(['ORAT','GRAT','WRAT']).reshape(1,-1)).sum(axis=1)
            else:
                keywords.loc[:,3] = [ ControlMode[item] for item in keywords.loc[:].index ]

# working on how to select from the several keyword lines for each well which is the correct keyword to write

            keywords['ranking'] = keywords.loc[:,4:20].count(axis=1)

            keywords.reset_index().sort_values(['index','keyword','ranking'],axis=0,ascending=[True,True,False]).groupby('index').first()[['keyword']]


            # write keywords
            for kw in keywords['keyword'].unique():
                outstr.append(kw)
                for i in range(len(keywords[keywords['keyword'] == kw])):
                    line = ' ' + ' '.join(map(str,keywords.reset_index().iloc[0].fillna('1*').drop('keyword').to_list())) + ' /'
                    outstr.append(line)
                outstr.append('/')
                outstr.append('\n')

            # write lastime
            if type(lastime) in (int,float):
                outstr.append('TSTEP')
                outstr.append(' ' + str(lastime) + ' /')
                outstr.append('/')
            else:
                outstr.append('DATES')
                outstr.append(' ' + dt.datetime(lastime).strftime("%d %d %Y %H:%M:%S") + ' /')
                outstr.append('/')
            outstr.append('\n')

            # reset out (keywords) dictionary
            out = {'WCONHIST':DataFrame(index=data[itemName].unique(), columns=range(2,13)),
                   'WCONINJH':DataFrame(index=data[itemName].unique(), columns=range(2,13)),
                   'WCONPROD':DataFrame(index=data[itemName].unique(), columns=range(2,21)),
                   'WCONINJE':DataFrame(index=data[itemName].unique(), columns=range(2,16))}

        # read the input table and put the values in the corresponding parameter of the keywords
        if data.iloc[i,attCol] == 'WSTATUS':  # oil production rate
            out['WCONHIST'].loc[data.iloc[i,itemCol],'Status'] = data.iloc[i,valueCol]
            out['WCONINJH'].loc[data.iloc[i,itemCol],'Status'] = data.iloc[i,valueCol]
            out['WCONPROD'].loc[data.iloc[i,itemCol],'Status'] = data.iloc[i,valueCol]
            out['WCONINJE'].loc[data.iloc[i,itemCol],'Status'] = data.iloc[i,valueCol]

        elif data.iloc[i,attCol] == 'WOPRH':  # oil production rate
            out['WCONHIST'].loc[data.iloc[i,itemCol],4] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WWPRH':  # water production rate
            out['WCONHIST'].loc[data.iloc[i,itemCol],5] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WGPRH':  # gas production rate
            out['WCONHIST'].loc[data.iloc[i,itemCol],6] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WVFPH':  # well VFP table number
            out['WCONHIST'].loc[data.iloc[i,itemCol],7] = data.iloc[i,valueCol]
            out['WCONINJH'].loc[data.iloc[i,itemCol],7] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WALQH':  # Artificial lift quantity
            out['WCONHIST'].loc[data.iloc[i,itemCol],8] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WTHPH':  # tubing head pressure (THP)
            out['WCONHIST'].loc[data.iloc[i,itemCol],9] = data.iloc[i,valueCol]
            out['WCONINJH'].loc[data.iloc[i,itemCol],6] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WBHPH':  # bottom hole pressure (BHP)
            out['WCONHIST'].loc[data.iloc[i,itemCol],10] = data.iloc[i,valueCol]
            out['WCONINJH'].loc[data.iloc[i,itemCol],5] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WWGPRH':  # wet gas production rate
            out['WCONHIST'].loc[data.iloc[i,itemCol],11] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] in ('WNPRH','WNLPRH'):  # NGL rate
            out['WCONHIST'].loc[data.iloc[i,itemCol],12] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WOIRH':
            out['WCONINJH'].loc[data.iloc[i,itemCol],4] = data.iloc[i,valueCol]
            out['WCONINJH'].loc[data.iloc[i,itemCol],2] = 'OIL'
        elif data.iloc[i,attCol] == 'WWIRH':
            out['WCONINJH'].loc[data.iloc[i,itemCol],4] = data.iloc[i,valueCol]
            out['WCONINJH'].loc[data.iloc[i,itemCol],2] = 'WATER'
        elif data.iloc[i,attCol] == 'WGIRH':
            out['WCONINJH'].loc[data.iloc[i,itemCol],4] = data.iloc[i,valueCol]
            out['WCONINJH'].loc[data.iloc[i,itemCol],2] = 'GAS'
        elif data.iloc[i,attCol] == 'WCTRL':
            out['WCONHIST'].loc[data.iloc[i,itemCol],3] = data.iloc[i,valueCol]
            out['WCONINJH'].loc[data.iloc[i,itemCol],12] = data.iloc[i,valueCol]
            out['WCONPROD'].loc[data.iloc[i,itemCol],3] = data.iloc[i,valueCol]
            out['WCONINJE'].loc[data.iloc[i,itemCol],4] = data.iloc[i,valueCol]

        elif data.iloc[i,attCol] == 'WOPR':  # oil production rate
            out['WCONPROD'].loc[data.iloc[i,itemCol],4] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WWPR':  # water production rate
            out['WCONPROD'].loc[data.iloc[i,itemCol],5] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WGPR':  # gas production rate
            out['WCONPROD'].loc[data.iloc[i,itemCol],6] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WLPR':  # liquid production rate
            out['WCONPROD'].loc[data.iloc[i,itemCol],7] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WVFP':  # Reservoir fluid volume rate
            out['WCONPROD'].loc[data.iloc[i,itemCol],8] = data.iloc[i,valueCol]
            # out['WCONINJH'].loc[data.iloc[i,itemCol],7] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WALQ':  # Artificial lift quantity
            out['WCONPROD'].loc[data.iloc[i,itemCol],12] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WVFP':  # well VFP table number
            out['WCONPROD'].loc[data.iloc[i,itemCol],11] = data.iloc[i,valueCol]
            out['WCONINJE'].loc[data.iloc[i,itemCol],9] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WTHP':  # tubing head pressure (THP)
            out['WCONPROD'].loc[data.iloc[i,itemCol],10] = data.iloc[i,valueCol]
            out['WCONINJE'].loc[data.iloc[i,itemCol],8] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WBHP':  # bottom hole pressure (BHP)
            out['WCONPROD'].loc[data.iloc[i,itemCol],9] = data.iloc[i,valueCol]
            out['WCONINJE'].loc[data.iloc[i,itemCol],7] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WWGPR':  # wet gas production rate
            out['WCONPROD'].loc[data.iloc[i,itemCol],13] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] in ('WNPR','WNLPR'):  # NGL rate
            out['WCONPROD'].loc[data.iloc[i,itemCol],20] = data.iloc[i,valueCol]
        # elif data.iloc[i,attCol] == 'WNPR':  # Total molar rate
        #     out['WCONPROD'].loc[data.iloc[i,itemCol],14] = data.iloc[i,valueCol]
        # elif data.iloc[i,attCol] == 'WNPR':  # Steam production rate
        #     out['WCONPROD'].loc[data.iloc[i,itemCol],15] = data.iloc[i,valueCol]
        # elif data.iloc[i,attCol] == 'WNPR':  # Calorific rate
        #     out['WCONPROD'].loc[data.iloc[i,itemCol],18] = data.iloc[i,valueCol]
        # elif data.iloc[i,attCol] == 'WNPR':  # Linearly combined rate
        #     out['WCONPROD'].loc[data.iloc[i,itemCol],19] = data.iloc[i,valueCol]
        elif data.iloc[i,attCol] == 'WOIR':  # Surface flow rate
            out['WCONINJE'].loc[data.iloc[i,itemCol],5] = data.iloc[i,valueCol]
            out['WCONINJE'].loc[data.iloc[i,itemCol],2] = 'OIL'
        elif data.iloc[i,attCol] == 'WWIR':  # Surface flow rate
            out['WCONINJE'].loc[data.iloc[i,itemCol],5] = data.iloc[i,valueCol]
            out['WCONINJE'].loc[data.iloc[i,itemCol],2] = 'WATER'
        elif data.iloc[i,attCol] == 'WGIR':  # Surface flow rate
            out['WCONINJE'].loc[data.iloc[i,itemCol],5] = data.iloc[i,valueCol]
            out['WCONINJE'].loc[data.iloc[i,itemCol],2] = 'GAS'
        # elif data.iloc[i,attCol] == 'WGIR':  # Vaporized oil concentration in the injected gas, or dissolved gas concentration in the injected oil
        #     out['WCONINJE'].loc[data.iloc[i,itemCol],10] = data.iloc[i,valueCol]
        # elif data.iloc[i,attCol] == 'WGIR':  # Thermal: ratio of gas volume to steam volume (C.W.E.) for a STEAM-GAS injector
        #     out['WCONINJE'].loc[data.iloc[i,itemCol],11] = data.iloc[i,valueCol]
        # elif data.iloc[i,attCol] == 'WGIR':  # Surface volume proportion of oil in a multiphase injecto
        #     out['WCONINJE'].loc[data.iloc[i,itemCol],12] = data.iloc[i,valueCol]
        # elif data.iloc[i,attCol] == 'WGIR':  # Surface volume proportion of water in a multiphase injecto
        #     out['WCONINJE'].loc[data.iloc[i,itemCol],13] = data.iloc[i,valueCol]
        # elif data.iloc[i,attCol] == 'WGIR':  # Surface volume proportion of gas in a multiphase injecto
        #     out['WCONINJE'].loc[data.iloc[i,itemCol],14] = data.iloc[i,valueCol]
        # elif data.iloc[i,attCol] == 'WGIR':  # Ratio of oil volume to steam volume (C.W.E.) for a STEAM-OIL injector (for use with steam-solvent injection).
        #     out['WCONINJE'].loc[data.iloc[i,itemCol],15] = data.iloc[i,valueCol]

        lastime = curtime