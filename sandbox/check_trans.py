#!/usr/bin/env python

import os
import sys
import glob
import operator
import subprocess

from supybot.i18n import parse
import supybot.ansi as ansi

def main():
    directory = sys.argv[1]
    if directory == '--core':
        checkCore()
    else:
        for plugin in os.listdir(directory):
            if plugin[0] not in 'AZERTYUIOPQSDFGHJKLMWXCVBN':
                continue
            if plugin in ('Ctcp', 'Owner'):
                continue
            checkPlugin(os.path.join(directory, plugin))

def changedir(f):
    def newf(new_path):
        old_path = os.getcwd()
        os.chdir(new_path)
        try:
            return f('.')
        finally:
            os.chdir(old_path)
    return newf

def checkCore():
    _checkCore(os.path.join(os.path.dirname(__file__), '..'))

@changedir
def _checkCore(corePath):
    subprocess.Popen(['pygettext', '-p', 'locales', 'plugins/__init__.py'] + glob.glob('src/*.py') + glob.glob('src/*/*.py')).wait()
    localePath = os.path.join(corePath, 'locales')
    pot = open(os.path.join(localePath, 'messages.pot'))
    for translation in os.listdir(localePath):
        if not translation.endswith('.po'):
            continue
        pot.seek(0)
        potPath = os.path.join(os.getcwd(), 'locales', translation)
        po = open(potPath)
        if checkTranslation(pot, po):
            print('OK:      ' + potPath)
        else:
            print(ansi.RED + 'ERROR:   ' + potPath + ansi.RESET)


@changedir
def checkPlugin(pluginPath):
    subprocess.Popen('pygettext -D config.py plugin.py', shell=True).wait()
    pot = open(os.path.join(pluginPath, 'messages.pot'))
    localePath = os.path.join(pluginPath, 'locales')
    for translation in os.listdir(localePath):
        if not translation.endswith('.po'):
            continue
        pot.seek(0)
        potPath = os.path.join(os.getcwd(), 'locales', translation)
        po = open(potPath)
        if checkTranslation(pot, po):
            print('OK:      ' + potPath)
        else:
            print(ansi.RED + 'ERROR:   ' + potPath + ansi.RESET)

def checkTranslation(pot, po):
    checking = False
    pot = set(map(operator.itemgetter(0), parse(pot)))
    po = set(map(operator.itemgetter(0), parse(po)))
    diff = [x for x in pot if x not in po]
    return not bool(diff)

if __name__ == '__main__':
    main()
