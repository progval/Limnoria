#!/usr/bin/env python


#****************************************************************************
# This file has been modified from its original version. It has been 
# formatted to fit your irc bot. 
# 
# Below is the original copyright. Doug Bell rocks. 
# The hijacker is Keith Jones, and he has no bomb in his shoe.
#
#****************************************************************************

#****************************************************************************
# convertcore.py, provides non-GUI base classes for data
#
# ConvertAll, a units conversion program
# Copyright (C) 2002, Douglas W. Bell
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License, Version 2.  This program is
# distributed in the hope that it will be useful, but WITTHOUT ANY WARRANTY.
#*****************************************************************************

#from option import Option
import re, copy, sys, os.path
import registry
import conf
#from math import *

class UnitGroup:
    "Stores, updates and converts a group of units"
    maxDecPlcs = 12
    def __init__(self, unitData, option):
        self.unitData = unitData
        self.option = option
        self.unitList = []
        self.currentNum = 0
        self.factor = 1.0
        self.reducedList = []
        self.linear = 1

    def update(self, text, cursorPos=None):
        "Decode user entered text into units"
        self.unitList = self.parseGroup(text)
        if cursorPos != None:
            self.updateCurrentUnit(text, cursorPos)
        else:
            self.currentNum = len(self.unitList) - 1

    def updateCurrentUnit(self, text, cursorPos):
        "Set current unit number"
        self.currentNum = len(re.findall('[\*/]', text[:cursorPos]))

    def currentUnit(self):
        "Return current unit if its a full match, o/w None"
        if self.unitList and self.unitList[self.currentNum].equiv:
            return self.unitList[self.currentNum]
        return None

    def currentPartialUnit(self):
        "Return unit with at least a partial match, o/w None"
        if not self.unitList:
            return None
        return self.unitData.findPartialMatch(self.unitList[self.currentNum]\
                                              .name)

    def currentSortPos(self):
        "Return unit near current unit for sorting"
        if not self.unitList:
            return self.unitData[self.unitData.sortedKeys[0]]
        return self.unitData.findSortPos(self.unitList[self.currentNum]\
                                         .name)

    def replaceCurrent(self, unit):
        "Replace the current unit with unit"
        if self.unitList:
            exp = self.unitList[self.currentNum].exp
            self.unitList[self.currentNum] = copy.copy(unit)
            self.unitList[self.currentNum].exp = exp
        else:
            self.unitList.append(copy.copy(unit))

    def completePartial(self):
        "Replace a partial unit with a full one"
        if self.unitList and not self.unitList[self.currentNum].equiv:
            text = self.unitList[self.currentNum].name
            unit = self.unitData.findPartialMatch(text)
            if unit:
                exp = self.unitList[self.currentNum].exp
                self.unitList[self.currentNum] = copy.copy(unit)
                self.unitList[self.currentNum].exp = exp

    def moveToNext(self, upward):
        "Replace unit with adjacent one based on match or sort position"
        unit = self.currentSortPos()
        num = self.unitData.sortedKeys.index(unit.name.\
                                             replace(' ', '')) \
                                             + (upward and -1 or 1)
        if 0 <= num < len(self.unitData.sortedKeys):
            self.replaceCurrent(self.unitData[self.unitData.sortedKeys[num]])

    def addOper(self, mult):
        "Add new operator & blank unit after current, * if mult is true"
        if self.unitList:
            self.completePartial()
            prevExp = self.unitList[self.currentNum].exp
            self.currentNum += 1
            self.unitList.insert(self.currentNum, Unit(''))
            if (not mult and prevExp > 0) or (mult and prevExp < 0):
                self.unitList[self.currentNum].exp = -1

    def changeExp(self, newExp):
        "Change the current unit's exponent"
        if self.unitList:
            self.completePartial()
            if self.unitList[self.currentNum].exp > 0:
                self.unitList[self.currentNum].exp = newExp
            else:
                self.unitList[self.currentNum].exp = -newExp

    def clearUnit(self):
        "Remove units"
        self.unitList = []

    def parseGroup(self, text):
        "Return list of units from text string"
        unitList = []
        parts = [part.strip() for part in re.split('([\*/])', text)]
        numerator = 1
        while parts:
            unit = self.parseUnit(parts.pop(0))
            if not numerator:
                unit.exp = -unit.exp
            if parts and parts.pop(0) == '/':
                numerator = not numerator
            unitList.append(unit)
        return unitList

    def parseUnit(self, text):
        "Return a valid or invalid unit with exponent from a text string"
        parts = text.split('^', 1)
        exp = 1
        if len(parts) > 1:   # has exponent
            try:
                exp = int(parts[1])
            except ValueError:
                if parts[1].lstrip().startswith('-'):
                    exp = -Unit.partialExp  # tmp invalid exp
                else:
                    exp = Unit.partialExp
        unitText = parts[0].strip().replace(' ', '')
        unit = copy.copy(self.unitData.get(unitText, None))
        if not unit and unitText and unitText[-1] == 's' and not \
           self.unitData.findPartialMatch(unitText):   # check for plural
            unit = copy.copy(self.unitData.get(unitText[:-1], None))
        if not unit:
            #unit = Unit(parts[0].strip())   # tmp invalid unit
            raise UnitDataError('%s is not a valid unit.' % (unitText))
        unit.exp = exp
        return unit

    def unitString(self, unitList=None):
        "Return the full string for this group or a given group"
        if unitList == None:
            unitList = self.unitList[:]
        fullText = ''
        if unitList:
            fullText = unitList[0].unitText(0)
            numerator = 1
            for unit in unitList[1:]:
                if (numerator and unit.exp > 0) \
                   or (not numerator and unit.exp < 0):
                    fullText = '%s * %s' % (fullText, unit.unitText(1))
                else:
                    fullText = '%s / %s' % (fullText, unit.unitText(1))
                    numerator = not numerator
        return fullText

    def groupValid(self):
        "Return 1 if all unitself.reducedLists are valid"
        if not self.unitList:
            return 0
        for unit in self.unitList:
            if not unit.unitValid():
                return 0
        return 1

    def reduceGroup(self):
        "Update reduced list of units and factor"
        self.linear = 1
        self.reducedList = []
        self.factor = 1.0
        if not self.groupValid():
            return
        count = 0
        tmpList = self.unitList[:]
        while tmpList:
            count += 1
            if count > 5000:
                raise UnitDataError, 'Circular unit definition'
            unit = tmpList.pop(0)
            if unit.equiv == '!':
                self.reducedList.append(copy.copy(unit))
            elif not unit.equiv:
                raise UnitDataError, 'Invalid conversion for "%s"' % unit.name
            else:
                if unit.fromEqn:
                    self.linear = 0
                newList = self.parseGroup(unit.equiv)
                for newUnit in newList:
                    newUnit.exp *= unit.exp
                tmpList.extend(newList)
                self.factor *= unit.factor**unit.exp
        self.reducedList.sort()
        tmpList = self.reducedList[:]
        self.reducedList = []
        for unit in tmpList:
            if self.reducedList and unit == self.reducedList[-1]:
                self.reducedList[-1].exp += unit.exp
            else:
                self.reducedList.append(unit)
        self.reducedList = [unit for unit in self.reducedList if \
                            unit.name != 'unit' and unit.exp != 0]

    def categoryMatch(self, otherGroup):
        "Return 1 if unit types are equivalent"
        if not self.checkLinear() or not otherGroup.checkLinear():
            return 0
        return self.reducedList == otherGroup.reducedList and \
               [unit.exp for unit in self.reducedList] \
               == [unit.exp for unit in otherGroup.reducedList]

    def checkLinear(self):
        "Return 1 if linear or acceptable non-linear"
        if not self.linear:
            if len(self.unitList) > 1 or self.unitList[0].exp != 1:
                return 0
        return 1

    def compatStr(self):
        "Return string with reduced unit or linear compatability problem"
        if self.checkLinear():
            return self.unitString(self.reducedList)
        return 'Cannot combine non-linear units'

    def convert(self, num, toGroup):
        "Return num of this group converted to toGroup"
        if self.linear:
            num *= self.factor
        else:
            num = self.nonLinearCalc(num, 1) * self.factor
        if toGroup.linear:
            return num / toGroup.factor
        return toGroup.nonLinearCalc(num / toGroup.factor, 0)

    def nonLinearCalc(self, num, isFrom):
        "Return result of non-linear calculation"
        x = num
        try:
            if self.unitList[0].toEqn:      # regular equations
                if isFrom:
                    return float(eval(self.unitList[0].fromEqn))
                return float(eval(self.unitList[0].toEqn))
            data = list(eval(self.unitList[0].fromEqn))  # extrapolation list
            if isFrom:
                data = [(float(group[0]), float(group[1])) for group in data]
            else:
                data = [(float(group[1]), float(group[0])) for group in data]
            data.sort()
            pos = len(data) - 1
            for i in range(len(data)):
                if num <= data[i][0]:
                    pos = i
                    break
            if pos == 0:
                pos = 1
            return (num-data[pos-1][0]) / float(data[pos][0]-data[pos-1][0]) \
                   * (data[pos][1]-data[pos-1][1]) + data[pos-1][1]
        except OverflowError:
            return 1e9999
        except:
            raise UnitDataError, 'Bad equation for %s' % self.unitList[0].name

    def convertStr(self, num, toGroup):
        "Return formatted string of converted number"
        return self.formatNumStr(self.convert(num, toGroup))

    def formatNumStr(self, num):
        "Return num string formatted per options"
        decPlcs = self.option.intData('DecimalPlaces', 0, UnitGroup.maxDecPlcs)
        if self.option.boolData('SciNotation'):
            return ('%%0.%dE' % decPlcs) % num
        if self.option.boolData('FixedDecimals'):
            return ('%%0.%df' % decPlcs) % num
        return ('%%0.%dG' % decPlcs) % num


class UnitDataError(Exception):
    pass


class UnitData(dict):
    def __init__(self):
        dict.__init__(self)
        self.sortedKeys = []

    def readData(self):
        "Read all unit data from file"
        types = []
        typeUnits = {}
        try:
            f = file(os.path.join(conf.supybot.directories.data(), \
                                  'units.dat'), 'r')
            lines = f.readlines()
            f.close()
        except IOError:
            raise UnitDataError, 'Can not read "units.dat" file'
        for i in range(len(lines)):     # join continuation lines
            delta = 1
            while lines[i].rstrip().endswith('\\'):
                lines[i] = ''.join([lines[i].rstrip()[:-1], lines[i+delta]])
                lines[i+delta] = ''
                delta += 1
        units = [Unit(line) for line in lines if \
                 line.split('#', 1)[0].strip()]   # remove comment lines
        typeText = ''
        for unit in units:               # find & set headings
            if unit.name.startswith('['):
                typeText = unit.name[1:-1].strip()
                types.append(typeText)
                typeUnits[typeText] = []
            unit.typeName = typeText
        units = [unit for unit in units if unit.equiv]  # keep valid units
        for unit in units:
            self[unit.name.replace(' ', '')] = unit
            typeUnits[unit.typeName].append(unit.name)
        self.sortedKeys = self.keys()
        self.sortedKeys.sort()
        print len(units), 'units loaded'
        if len(self.sortedKeys) < len(units):
            raise UnitDataError, 'Duplicate unit names found'

        return (types, typeUnits)

    def findPartialMatch(self, text):
        "Return first partially matching unit or None"
        text = text.replace(' ', '')
        if not text:
            return None
        for name in self.sortedKeys:
            if name.startswith(text):
                return self[name]
        return None

    def findSortPos(self, text):
        "Return unit whose abbrev comes immediately after text"
        text = text.replace(' ', '')
        for name in self.sortedKeys:
            if text <= name:
                return self[name]
        return self[self.sortedKeys[-1]]


class Unit:
    "Reads and stores a single unit conversion"
    partialExp = 1000
    def __init__(self, dataStr):
        dataList = dataStr.split('#')
        unitList = dataList.pop(0).split('=', 1)
        self.name = unitList.pop(0).strip()
        self.equiv = ''
        self.factor = 1.0
        self.fromEqn = ''   # used only for non-linear units
        self.toEqn = ''     # used only for non-linear units
        if unitList:
            self.equiv = unitList[0].strip()
            if self.equiv[0] == '[':   # used only for non-linear units
                try:
                    self.equiv, self.fromEqn = re.match('\[(.*?)\](.*)', \
                                                        self.equiv).groups()
                    if ';' in self.fromEqn:
                        self.fromEqn, self.toEqn = self.fromEqn.split(';', 1)
                        self.toEqn = self.toEqn.strip()
                    self.fromEqn = self.fromEqn.strip()
                except AttributeError:
                    raise UnitDataError, 'Bad equation for "%s"' % self.name
            else:                # split factor and equiv unit for linear
                parts = self.equiv.split(None, 1)
                if len(parts) > 1 and re.search('[^\d\.eE\+\-\*/]', parts[0]) \
                   == None:       # only allowed digits and operators
                    try:
                        self.factor = float(eval(parts[0]))
                        self.equiv = parts[1]
                    except:
                        pass
        self.comments = [comm.strip() for comm in dataList]
        self.comments.extend([''] * (2 - len(self.comments)))
        self.exp = 1
        self.viewLink = [None, None]
        self.typeName = ''

    def description(self):
        "Return name and 1st comment (usu. full name) if applicable"
        if self.comments[0]:
            return '%s  (%s)' % (self.name, self.comments[0])
        return self.name

    def unitValid(self):
        "Return 1 if unit and exponent are valid"
        if self.equiv and -Unit.partialExp < self.exp < Unit.partialExp:
            return 1
        return 0

    def unitText(self, absExp=0):
        "Return text for unit name with exponent or absolute value of exp"
        exp = self.exp
        if absExp:
            exp = abs(self.exp)
        if exp == 1:
            return self.name
        if -Unit.partialExp < exp < Unit.partialExp:
            return '%s^%d' % (self.name, exp)
        if exp > 1:
            return '%s^' % self.name
        else:
            return '%s^-' % self.name

    def __cmp__(self, other):
        return cmp(self.name, other.name)

############################################################################
# Wrapper functionality
#
############################################################################ 


# Parse the data file, and set everything up for conversion
data = UnitData()
(types, unitsByType) = data.readData()

# At the moment, we're not handling options
option = None

# set up the objects for unit conversion
fromUnit = UnitGroup(data, option)
toUnit = UnitGroup(data, option)

def convert(num, unit1, unit2):
    """ Convert from one unit to another

    num is the factor for the first unit. Raises UnitDataError for 
    various errors.
    """

    global fromUnit
    global toUnit
    global types
    global unitsByType
    
    fromUnit.update(unit1)
    toUnit.update(unit2)

    fromUnit.reduceGroup()
    toUnit.reduceGroup()
    
    # Match up unit categories
    if not fromUnit.categoryMatch(toUnit):
        raise UnitDataError('unit categories did not match')
            
    return fromUnit.convert(num, toUnit)
                


def units(type):
    """ Return comma separated string list of units of given type, or 
        a list of types if the argument is not valid.
    """

    global types
    global unitsByType

    if type in types:
        return '%s units: %s' % (type, ', '.join(unitsByType[type]))
    else:
        return 'valid types: ' + ', '.join(types)


