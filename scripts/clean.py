#!/usr/bin/env python

import os, sys, os.path, shutil

def removeFiles(arg, dirname, names):
    for name in names:
        if name[-4:] in ('.pyc', 'pyo'):
            os.remove(os.path.join(dirname, name))
        elif name[-1] == '~':
            os.remove(os.path.join(dirname, name))

if __name__ == '__main__':
    for name in os.listdir('logs'):
        filename = os.path.join('logs', name)
        if os.path.isfile(filename):
            os.remove(filename)
    os.path.walk(os.curdir, removeFiles, None)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
