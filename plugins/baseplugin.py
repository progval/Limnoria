#!/usr/bin/env python

import sys

sys.path.insert(0, 'src')
sys.path.insert(0, 'others')

from fix import *

import os
import sets
import time
import urllib2
import threading

import cdb
import conf
import debug
import world
import ircutils

class ChannelDBHandler(object):
    """A class to handle database stuff for individual channels transparently.
    """
    suffix = '.db'
    threaded = False
    def __init__(self, suffix='.db'):
        self.dbCache = ircutils.IrcDict()
        suffix = self.suffix
        if self.suffix and self.suffix[0] != '.':
            suffix = '.' + suffix
        self.suffix = suffix

    def makeFilename(self, channel):
        channel = ircutils.toLower(channel)
        prefix = '%s-%s%s' % (channel, self.__class__.__name__, self.suffix)
        return os.path.join(conf.dataDir, prefix)

    def makeDb(self, filename):
        return cdb.shelf(filename)

    def getDb(self, channel):
        try:
            if self.threaded:
                return self.makeDb(self.makeFilename(channel))
            else:
                return self.dbCache[channel]
        except KeyError:
            db = self.makeDb(self.makeFilename(channel))
            if not self.threaded:
                self.dbCache[channel] = db
            return db

    def die(self):
        for db in self.dbCache.itervalues():
            db.commit()
            db.close()



class PeriodicFileDownloader(object):
    """A class to periodically download a file/files.

    A class-level dictionary 'periodicFiles' maps names of files to
    three-tuples of
    (url, seconds between downloads, function to run with downloaded file).

    'url' should be in some form that urllib2.urlopen can handle (do note that
    urllib2.urlopen handles file:// links perfectly well.)

    'seconds between downloads' is the number of seconds between downloads,
    obviously.  An important point to remember, however, is that it is only
    engaged when a command is run.  I.e., if you say you want the file
    downloaded every day, but no commands that use it are run in a week, the
    next time such a command is run, it'll be using a week-old file.  If you
    don't want such behavior, you'll have to give an error mess age to the user
    and tell him to call you back in the morning.

    'function to run with downloaded file' is a function that will be passed
    a string *filename* of the downloaded file.  This will be some random
    filename probably generated via some mktemp-type-thing.  You can do what
    you want with this; you may want to build a database, take some stats,
    or simply rename the file.  You can pass None as your function and the
    file with automatically be renamed to match the filename you have it listed
    under.  It'll be in conf.dataDir, of course.

    Aside from that dictionary, simply use self.getFile(filename) in any method
    that makes use of a periodically downloaded file, and you'll be set.
    """
    periodicFiles = None
    def __init__(self):
        if self.periodicFiles is None:
            raise ValueError, 'You must provide files to download'
        self.lastDownloaded = {}
        self.downloadedCounter = {}
        for filename in self.periodicFiles:
            self.lastDownloaded[filename] = 0
            self.currentlyDownloading = sets.Set()
            self.downloadedCounter[filename] = 0
            self.getFile(filename)

    def _downloadFile(self, filename, url, f):
        infd = urllib2.urlopen(url)
        newFilename = mktemp()
        outfd = file(newFilename, 'wb')
        start = time.time()
        s = infd.read(4096)
        while s:
            outfd.write(s)
            s = infd.read(4096)
        infd.close()
        outfd.close()
        msg = 'Downloaded %s in %s seconds' % (filename, time.time() - start)
        debug.msg(msg, 'verbose')
        self.downloadedCounter[filename] += 1
        self.lastDownloaded[filename] = time.time()
        if f is None:
            os.rename(newFilename, os.path.join(conf.dataDir, filename))
        else:
            start = time.time()
            f(newFilename)
            total = time.time() - start
            msg = 'Function ran on %s in %s seconds' % (filename, total)
            debug.msg(msg, 'verbose')
        self.currentlyDownloading.remove(filename)

    def getFile(self, filename):
        (url, timeLimit, f) = self.periodicFiles[filename]
        if time.time() - self.lastDownloaded[filename] > timeLimit and \
           filename not in self.currentlyDownloading:
            debug.msg('Beginning download of %s' % url, 'verbose')
            self.currentlyDownloading.add(filename)
            args = (filename, url, f)
            name = '%s #%s' % (filename, self.downloadedCounter[filename])
            t = threading.Thread(target=self._downloadFile, name=name,
                                 args=(filename, url, f))
            t.start()
            world.threadsSpawned += 1
        

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
