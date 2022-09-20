# -*- coding: utf-8 -*-
"""
Created on Wed Sep 18 12:33:46 2019

@author: Martín Carlos Araya <martinaraya@gmail.com>
"""

__version__ = '0.15.2'
__release__ = 20220920
__all__ = ['multisplit', 'is_numeric', 'get_number', 'is_date', 'date']

from ..classes.errors import UndefinedDateFormatError

import numpy as np
import pandas as pd
import datetime as dt


def multisplit(string, sep=[' '], remove=[' ']) :
    """
    receives a string and returns a list with string split
    by all the separators in sep.
    the default separator is the blank space ' '.
    use the remove parameter to indicate the separators that
    must not be reported in the output list.
    by default, the blank space is not reported.
    """
    assert type(string) is str

    # check sep is list
    if type(sep) is str :
        sep = [sep]

    # eliminate duplicated separators
    sep = list( set( sep ) )

    # sort sep by lenght
    s = len(sep)
    for i in range(s-1) :
        for j in range(s-i-1) :
            if len(sep[j]) < len(sep[j+1]) :
                sep[j], sep[j+1] = sep[j+1], sep[j]

    # initialize counters
    stringlist = []
    i, x, t = 0, 0, len(string)
    # loop through the entire string
    while i < t :
        found = False # flag for found separator
        # look for each separator
        for se in sep :
            s = len(se)
            if (i+s <= t) and string[i:i+s] == se :
                stringlist += [ string[x:i], se ]
                x = i+s
                i += s
                found = True
                break
        i += 1 if not found else 0
    stringlist += [ string[x:] ]

    # clean the output
    newlist = []
    for part in stringlist :
        if part not in remove + [''] :
            newlist += [ part ]

    return newlist


def is_numeric(string) :
    """
    returns True if the string is a number
    """
    # assert type(string) is str
    try :
        float(string)
        return True
    except :
        return False

def get_number(string) :
    "returns the number, as integer or float, contained in a string"
    if is_numeric(string) :
        try :
            return int(string)
        except :
            return float(string)

def is_date(dateStr, formatIN='', speak=False, returnFormat=False ):
    """
    returns True if the string 'dateStr' is a valid date, otherwise returns False.
    """
    if formatIN != '' :
        try :
            date(dateStr, formatIN=formatIN, speak=speak, returnFormat=returnFormat )
            if returnFormat :
                return date(dateStr, formatIN=formatIN, speak=speak, returnFormat=True )
            return True
        except :
            return False

    else :
        try :
            date(dateStr, formatIN='', speak=speak )
            if returnFormat :
                return date(dateStr, formatIN='', speak=speak, returnFormat=True )
            return True
        except :
            pass

        formats = [ 'DD-MM-YYYY', 'DD-MMM-YYYY', 'YYYY-MM-DD', 'YYYY-MMM-DD', 'MM-DD-YYYY', 'MMM-DD-YYYY', 'YYYY-DD-MM', 'YYYY-DD-MMM', 'YYYYMMDD', 'YYYYMMMDD', 'DD-MM-YY', 'MMM-DD-YY', 'MM-DD-YY'  ]
        separators = ['-', '/', ' ', '\t', '_', ':', ';', ', ', '.', '#', "'"]
        for f in formats :
            for sep in separators :
                fIN = f.replace('-', sep) if sep != '-' else f
                try :
                    date(dateStr, formatIN=fIN, speak=speak )
                    if returnFormat :
                        return fIN
                    return True
                except :
                    pass

        formats = [ 'YYYYMMDD', 'YYYYMMMDD' ]
        for f in formats :
            try :
                date(dateStr, formatIN=fIN, speak=speak )
                if returnFormat :
                    return f
                return True
            except :
                pass
    return False

def splitDMMMY(string) :
    mi, mf = len(string)+1, len(string)+1
    for x in range(len(string)) :
        if not string[x].isdigit() and x < mi:
            mi = x
        if string[x].isdigit() and x < mf and x > mi:
            mf = x
            break
    if mi > 0 and mf > 0 :
        return [string[:mi], string[mi:mf], string[mf:]]

def date(date, formatIN='', formatOUT='', speak=True, YYbaseIN=1900, returnFormat=False ):
    """
    stringformat.date receives a string containing a date or a list of strings
    containing dates and changes the date format to the format especified by
    the user. By default the out format will be 'DD-MMM-YYYY'.

    The input and output format can be stated with the keywords formatIN
    and formatOUT followed by a string containing the characters 'D', 'M'
    and 'Y' to identify day, month and year and the characters '/', '-', ' ',
    '\t' (tab) or '_' as separators.

    If the keyword formatIN is not entered, the program will try to infer
    the date format from the provided data.

    syntax examples:

    stringformat.date('31/DEC/1984', formatIN='DD/MMM/YYYY', formatOUT='MM-DD-YYYY')

    speak parameter set to True will print a message showing the input and output formats.
    """
    npDateOnly = lambda x : x.split('T')[0]

    MonthString2Number = {'JAN' :  1,
                          'FEB' :  2,
                          'MAR' :  3,
                          'APR' :  4,
                          'MAY' :  5,
                          'JUN' :  6,
                          'JLY' :  7,
                          'JUL' :  7,
                          'AUG' :  8,
                          'SEP' :  9,
                          'OCT' : 10,
                          'NOV' : 11,
                          'DEC' : 12 }
    MonthNumber2String = dict(zip( MonthString2Number.values(), MonthString2Number.keys()  ))

    separator = '' # initialize
    formatIN = formatIN.upper().strip()
    formatOUT = formatOUT.upper().strip()
    # define if input is a list/tuple of dates or a single date
    sample = str(date)
    output = list
    if type(date) is list or type(date) is tuple:
        output = list
        if type(date[0]) is str :
            for i in range(len(date)) :
                date[i] = date[i].strip()
            sample = date[0].strip()
        elif type(date[0]) is np.datetime64 :
            date = np.array(date)
        elif type(date[0]) is np.str_ :
            date = list( map( str, date ) )
            sample = date[0].strip()

    if type(date) is pd.Series :
        date = date.to_numpy()

    if type(date) is np.ndarray :
        output = list
        sample = date[0]
        if 'datetime64' in str(date.dtype) :
            date = list(np.datetime_as_string(date))
            date = list(map( npDateOnly, date ))
            formatIN = 'YYYY-MM-DD'
            separator = '-'

    if type(date) is np.datetime64 :
        formatIN = 'YYYY-MM-DD'
        date = np.datetime_as_string(date)
        date = npDateOnly( date )
        sample = date
        output = str
        separator = '-'

    if type(date) is pd.Timestamp : # pd._libs.tslibs.timestamps.Timestamp
        date = date.date()

    if type(date) is dt.date :
        date = str( date )
        if formatIN == '' :
            formatIN = 'YYYY-MM-DD'

    if type(date) is dt.datetime :
        date = str( date ).split()[0]
        if formatIN == '' :
            formatIN = 'YYYY-MM-DD'

    if type(date) is str :
        sample = date.strip(' "\'')
        date = [ date ]
        output = str

    # look for the separator, empty string if not found
    if separator == '' :
        for sep in ['/', '-', ' ', '\t', '_', ':', ';', ', ', '.', '#', "'"] :
            if sep in sample :
                separator = sep
                break

    # separate the 1st, 2nd and 3rd components of the DATEs in three lists
    if separator != '' :
        # separate the 1st, 2nd and 3rd components of the DATEs in three lists
        datelist = separator.join(date).split(separator)
        datelist = [ datelist[0::3], datelist[1::3], datelist[2::3] ]

    else :
        l = 0
        if max(map(len, date)) == min(map(len, date)) :
            l = max(map(len, date))

        if formatIN != '' :
            x, y = 0, 0
            for i in range(1, len(formatIN)) :
                if formatIN[i] != formatIN[i-1] :
                    if x == 0 :
                        x = i
                    else :
                        y = i
                        break
            datelist = [ [d[:x], d[x:y], d[y:]] for d in date ]
            datelist = [ [ datelist[i][0] for i in range(len(datelist)) ], [ datelist[i][1] for i in range(len(datelist)) ], [ datelist[i][2] for i in range(len(datelist)) ] ]

        elif l == 6 :
            datelist = [ [d[0:2], d[2:4], d[4:6]] for d in date ]
            datelist = [ [ datelist[i][0] for i in range(len(datelist)) ], [ datelist[i][1] for i in range(len(datelist)) ], [ datelist[i][2] for i in range(len(datelist)) ] ]
        elif l == 8 :
            datelist = [ [d[0:2], d[2:4], d[4:8]] for d in date ]
            datelist = [ [ datelist[i][0] for i in range(len(datelist)) ], [ datelist[i][1] for i in range(len(datelist)) ], [ datelist[i][2] for i in range(len(datelist)) ] ]
            if int(max(datelist[0])) <= 31 and int(min(datelist[2])) >= 1900 and int(max(datelist[2])) <= 2050 and int(max(datelist[1]))<=12 :
                pass # DDMMYYYY
            else :
                datelist = [ [d[0:4], d[4:6], d[6:8]] for d in date ]
                datelist = [ [ datelist[i][0] for i in range(len(datelist)) ], [ datelist[i][1] for i in range(len(datelist)) ], [ datelist[i][2] for i in range(len(datelist)) ] ]
                if int(max(datelist[2])) <= 31 and int(min(datelist[0])) >= 1900 and int(max(datelist[0])) <= 2050 and int(max(datelist[1]))<=12 :
                    pass # YYYYMMDD
                else :
                    raise UndefinedDateFormatError('unable to idenfy date format, please provide with keyword formatIN')
        elif l == 9 :
            x, y = 0, 0
            for i in range(9) :
                if not date[0][i].isdigit() and x == 0 :
                    x = i
                elif date[0][i].isdigit() and x > 0 :
                    y = i
                    break
            datelist = [ [d[:x], d[x:y], d[y:]] for d in date ]
            datelist = [ [ datelist[i][0] for i in range(len(datelist)) ], [ datelist[i][1] for i in range(len(datelist)) ], [ datelist[i][2] for i in range(len(datelist)) ] ]
        else :
            raise UndefinedDateFormatError('unable to idenfy date format, please provide with keyword formatIN')


    # if formatIN is not defined try to guess what it is
    if formatIN == '' :
        datestr = [False, False, False]
        datemax = [None, None, None]

        for i in range(3) :
            for j in range(len(date)) :
                try:
                    datelist[i][j] = int(datelist[i][j])
                except :
                    datestr[i] = True
                    break
            if datestr[i] == False :
                datemax[i] = max(datelist[i])

        orderIN = [None, None, None, separator, None, None, None]
        found = ''
        if True in datestr :
            orderIN[5] = 3
            found = found + 'Ms'
        for i in range(3) :
            if datestr[i] == True :
                orderIN[1] = i
                found = found + 'M'
            elif datemax[i] != None and datemax[i] > 999 :
                orderIN[2] = i
                orderIN[6] = 4
                found = found + 'Y'
            elif datemax[i] != None and datemax[i] > 99 :
                orderIN[2] = i
                orderIN[6] = 3
                found = found + 'Y'
            elif datemax[i] != None and datemax[i] > 31 :
                orderIN[2] = i
                orderIN[6] = 2
                found = found + 'Y'
            elif datemax[i] != None and datemax[i] > 12 and datemax[i] < 32 :
                orderIN[0] = i
                orderIN[4] = 2
                found = found + 'D'
            else :
                pass

        if None in orderIN :
            for i in range(3) :
                if datemax[i] != None and datemax[i] <= 12 :
                    if 'D' in found and 'M' not in found:
                        orderIN[1] = i
                        orderIN[5] = 2
                        found = found + 'M'
                    elif 'M' in found and 'D' not in found :
                        orderIN[0] = i
                        orderIN[4] = 2
                        found = found + 'D'

        if 'Ms' in found :
            found = found[2:]

        if 'D' in found and 'M' in found and 'Y' in found :
            formatIN = []
            for i in range(3) :
                if orderIN[i] == 0 :
                    formatIN.append('D'*orderIN[4])
                elif orderIN[i] == 1 :
                    formatIN.append('M'*orderIN[5])
                elif orderIN[i] == 2 :
                    formatIN.append('Y'*orderIN[6])
            formatIN = orderIN[3].join(formatIN)
            if speak :
                print(' the input format is: ' + formatIN)

        else :
            raise UndefinedDateFormatError('unable to idenfy date format, please provide with keyword formatIN')

        if returnFormat :
            return formatIN

    # read input format from formatIN
    else :
        orderIN = [None, None, None, None, None, None, None] # [day, month, year, separator, day_digit, month_digits, year_digits]
        for sep in ['/', '-', ' ', '\t', '_', ':', ';', '#', "'"] :
            if sep in formatIN :
                orderIN[3] = sep
                break
        indexDMY = [ formatIN.upper().index('D'), formatIN.upper().index('M'), formatIN.upper().index('Y') ]
        for i in range(3) :
            if indexDMY[i] == min(indexDMY):
                orderIN[i] = 0
            elif indexDMY[i] == max(indexDMY):
                orderIN[i] = 2
            else :
                orderIN[i] = 1
        orderIN[4] = formatIN.upper().count('D')
        orderIN[5] = formatIN.upper().count('M')
        orderIN[6] = formatIN.upper().count('Y')

        for sep in ['/', '-', ' ', '\t'] :
            if sep in formatIN :
                test = sep
                break


    # set formatOUT by default if not provided
    if formatOUT == '' :
        formatOUT = 'DD-MMM-YYYY'
        orderOUT = [0, 1, 2, '-', 2, 3, 4]
        # if speak and formatIN != formatOUT :
        #     print(' default output format is: DD-MMM-YYYY')

    # read format from formatOUT
    else :
        orderOUT = [None, None, None, '', None, None, None] # [day, month, year, separator, day_digit, month_digits, year_digits]
        for sep in ['/', '-', ' ', '\t', '_', ':', ';', '#', "'"] :
            if sep in formatOUT :
                orderOUT[3] = sep
                break
        if 'D' in formatOUT.upper() :
            indexD = formatOUT.upper().index('D')
        else :
            indexD = 2
        if 'M' in formatOUT.upper() :
            indexM = formatOUT.upper().index('M')
        else :
            indexM = 2
        if 'Y' in formatOUT.upper() :
            indexY = formatOUT.upper().index('Y')
        else :
            indexY = 2
        indexDMY = [ indexD, indexM, indexY ]
        for i in range(3) :
            if indexDMY[i] == min(indexDMY):
                orderOUT[i] = 0
            elif indexDMY[i] == max(indexDMY):
                orderOUT[i] = 2
            else :
                orderOUT[i] = 1
        orderOUT[4] = formatOUT.upper().count('D')
        orderOUT[5] = formatOUT.upper().count('M')
        orderOUT[6] = formatOUT.upper().count('Y')


    dateOUT = [ datelist[orderIN.index(orderOUT[0])], datelist[orderIN.index(orderOUT[1])], datelist[orderIN.index(orderOUT[2])] ]

    if orderOUT[5] == 0 :
        dateM = ''
    elif orderOUT[5] == 5 :
        dateM = orderOUT[1]
        for i in range(len(dateOUT[dateM])) :
            dateOUT[dateM][i] = str(int(dateOUT[dateM][i])).zfill(2) + MonthNumber2String[int(dateOUT[dateM][i])]
    elif orderOUT[5] > 2 and orderIN[5] <= 2 :
        dateM = orderOUT[1]
        for i in range(len(dateOUT[dateM])) :
            dateOUT[dateM][i] = MonthNumber2String[int(dateOUT[dateM][i])]
    elif orderOUT[5] <= 2 and orderIN[5] > 2 :
        dateM = orderOUT[1]
        for i in range(len(dateOUT[dateM])) :
            dateOUT[dateM][i] = MonthString2Number[dateOUT[dateM][i]]

    dateOUTformated = []
    numberformat = [None, None, None] # [year, day, month]
    for i in range(3) :
        numberformat[orderOUT[i]] = orderOUT[i+4]
    for i in range(len(dateOUT[0])) :
        #print(numberformat)
        if numberformat[0] == 0 or numberformat[0] == None:
            dateStr = ''
        elif type(dateOUT[0][i]) == int and numberformat[0] == 2 and dateOUT[0][i] < 10 :
            dateStr = '0' + str(dateOUT[0][i]) + orderOUT[3]
        elif type(dateOUT[0][i]) == int and numberformat[0] == 3 and dateOUT[0][i] < 10 :
            dateStr = '00' + str(dateOUT[0][i]) + orderOUT[3]
        elif type(dateOUT[0][i]) == int and numberformat[0] == 3 and dateOUT[0][i] < 100 :
            dateStr = '0' + str(dateOUT[0][i]) + orderOUT[3]
        elif type(dateOUT[0][i]) == int and numberformat[0] == 4 and dateOUT[0][i] < 10 :
            if YYbaseIN == 0 :
                dateStr = '000' + str(dateOUT[0][i]) + orderOUT[3]
            else :
                dateStr = str(dateOUT[0][i]+YYbaseIN) + orderOUT[3]
        elif type(dateOUT[0][i]) == int and numberformat[0] == 4 and dateOUT[0][i] < 100 :
            if YYbaseIN == 0 :
                dateStr = '00' + str(dateOUT[0][i]) + orderOUT[3]
            else :
                dateStr = str(dateOUT[0][i]+YYbaseIN) + orderOUT[3]
        elif type(dateOUT[0][i]) == int and numberformat[0] == 4 and dateOUT[0][i] < 1000 :
            dateStr = '0' + str(dateOUT[0][i]) + orderOUT[3]
        else :
            dateStr = str(dateOUT[0][i]) + orderOUT[3]

        if numberformat[1] == 0 or numberformat[1] == None :
            dateStr = dateStr + ''
        elif type(dateOUT[1][i]) == int and numberformat[1] == 2 and dateOUT[1][i] < 10 :
            dateStr = dateStr + '0' + str(dateOUT[1][i]) + orderOUT[3]
        elif type(dateOUT[1][i]) == int and numberformat[1] == 3 and dateOUT[1][i] < 10 :
            dateStr = dateStr + '00' + str(dateOUT[1][i]) + orderOUT[3]
        elif type(dateOUT[1][i]) == int and numberformat[1] == 3 and dateOUT[1][i] < 100 :
            dateStr = dateStr + '0' + str(dateOUT[1][i]) + orderOUT[3]
        elif type(dateOUT[1][i]) == int and numberformat[1] == 4 and dateOUT[1][i] < 10 :
            if YYbaseIN == 0 :
                dateStr = dateStr + '000' + str(dateOUT[1][i]) + orderOUT[3]
            else :
                dateStr = dateStr + str(dateOUT[1][i]+YYbaseIN) + orderOUT[3]
        elif type(dateOUT[1][i]) == int and numberformat[1] == 4 and dateOUT[1][i] < 100 :
            if YYbaseIN :
                dateStr = dateStr + '00' + str(dateOUT[1][i]) + orderOUT[3]
            else :
                dateStr = dateStr + str(dateOUT[1][i]+YYbaseIN) + orderOUT[3]
        elif type(dateOUT[1][i]) == int and numberformat[1] == 4 and dateOUT[1][i] < 1000 :
            dateStr = dateStr + '0' + str(dateOUT[1][i]) + orderOUT[3]
        else :
            dateStr = dateStr + str(dateOUT[1][i]) + orderOUT[3]

        if numberformat[2] == 0 or numberformat[2] == None:
            dateStr = dateStr + ''
        elif type(dateOUT[2][i]) == int and numberformat[2] == 2 and dateOUT[2][i] < 10 :
            dateStr = dateStr + '0' + str(dateOUT[2][i])
        elif type(dateOUT[2][i]) == int and numberformat[2] == 3 and dateOUT[2][i] < 10 :
            dateStr = dateStr + '00' + str(dateOUT[2][i])
        elif type(dateOUT[2][i]) == int and numberformat[2] == 3 and dateOUT[2][i] < 100 :
            dateStr = dateStr + '0' + str(dateOUT[2][i])
        elif type(dateOUT[2][i]) == int and numberformat[2] == 4 and dateOUT[2][i] < 10 :
            if YYbaseIN == 0 :
                dateStr = dateStr + '000' + str(dateOUT[2][i])
            else :
                dateStr = dateStr + str(dateOUT[2][i]+YYbaseIN)
        elif type(dateOUT[2][i]) == int and numberformat[2] == 4 and dateOUT[2][i] < 100 :
            if YYbaseIN == 0 :
                dateStr = dateStr + '00' + str(dateOUT[2][i])
            else :
                dateStr = dateStr + str(dateOUT[2][i]+YYbaseIN)
        elif type(dateOUT[2][i]) == int and numberformat[2] == 4 and dateOUT[2][i] < 1000 :
            dateStr = dateStr + '0' + str(dateOUT[2][i])
        else :
            dateStr = dateStr + str(dateOUT[2][i])

        dateOUTformated.append( dateStr )

    if output is str :
        return dateOUTformated[0]
    else :
        return dateOUTformated