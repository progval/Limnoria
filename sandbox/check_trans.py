#!/usr/bin/env python2

import os
import sys

def main():
    directory = sys.argv[1]
    for plugin in os.listdir(directory):
        if plugin[0] not in 'AZERTYUIOPQSDFGHJKLMWXCVBN':
            continue
        checkPlugin(os.path.join(directory, plugin))

def checkPlugin(pluginPath):
    try:
        pot = open(os.path.join(pluginPath, 'messages.pot'))
    except IOError: # Does not exist
        print 'WARNING: %s has no messages.pot' % pluginPath
        return
    localePath = os.path.join(pluginPath, 'locale')
    for translation in os.listdir(localePath):
        if not translation.endswith('.po'):
            continue
        pot.seek(0)
        potPath = os.path.join(localePath, translation)
        po = open(potPath)
        if checkTranslation(pot, po):
            print 'OK:      ' + potPath
        else:
            print 'ERROR:   ' + potPath

def checkTranslation(pot, po):
    checking = False
    for potLine in pot:
        if not checking and potLine.startswith('msgid'):
            checking = True
            while True:
                poLine = po.readline()
                if poLine == '': # EOF
                    return False
                if poLine.startswith('msgid'):
                    if poLine == potLine:
                        break
                    else:
                        return False
            continue
        elif checking and potLine.startswith('msgstr'):
            checking = False

        if checking:
            poLine = po.readline()
            if potLine != poLine:
                return False
    return True

if __name__ == '__main__':
    main()
