#!/usr/bin/env python

import sys

sys.path.insert(0, 'src')
sys.path.insert(0, 'others')

from fix import *

import os

import cdb
import conf
import world
import callbacks

class DBHandler(object):
    """A class to handle database stuff for individual channels transparently.
    """
    suffix = '.db'
    def __init__(self, suffix='.db'):
        self.dbCache = {}
        suffix = self.suffix
        if self.suffix and self.suffix[0] != '.':
            suffix = '.' + suffix
        self.suffix = suffix

    def makeFilename(self, channel):
        prefix = '%s-%s%s' % (channel, self.__class__.__name__, self.suffix)
        return os.path.join(conf.dataDir, prefix)

    def makeDb(self, filename):
        return cdb.shelf(filename)

    def getDb(self, channel):
        try:
            return self.dbCache[channel]
        except KeyError:
            db = self.makeDb(self.makeFilename(channel))
            self.dbCache[channel] = db
            return db

    def die(self):
        for db in self.dbCache.itervalues():
            db.close()
