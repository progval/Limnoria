###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008, James Vega
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import gc
import os
import re
import csv
import sys
import math
import time
import random
import fnmatch
import os.path
import threading
import collections

import supybot.log as log
import supybot.dbi as dbi
import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import commands

## i think we don't need any of this with sqlite3
#try:
    ## We need to sweep away all that mx.* crap because our code doesn't account
    ## for PySQLite's arbitrary use of it.  Whoever decided to change sqlite's
    ## behavior based on whether or not that module is installed was a *CRACK*
    ## **FIEND**, plain and simple.
    #mxCrap = {}
    #for (name, module) in sys.modules.items():
        #if name.startswith('mx'):
            #mxCrap[name] = module
            #sys.modules.pop(name)
    ## Now that the mx crap is gone, we can import sqlite.
    #import sqlite3 as sqlite
    ## And now we'll put it back, even though it sucks.
    #sys.modules.update(mxCrap)
    ## Just in case, we'll do this as well.  It doesn't seem to work fine by
    ## itself, though, or else we'd just do this in the first place.
    #sqlite.have_datetime = False
    #Connection = sqlite.Connection
    #class MyConnection(sqlite.Connection):
        #def commit(self, *args, **kwargs):
            #if self.autocommit:
                #return
            #else:
                #Connection.commit(self, *args, **kwargs)

        #def __del__(self):
            #try:
                #Connection.__del__(self)
            #except AttributeError:
                #pass
            #except Exception, e:
                #try:
                    #log.exception('Uncaught exception in __del__:')
                #except:
                    #pass
    #sqlite.Connection = MyConnection
    ##del Connection.__del__
#except ImportError:
    #pass

try:
    import sqlite3
except ImportError:
    from pysqlite2 import dbapi2 as sqlite3 # for python2.4

class NoSuitableDatabase(Exception):
    def __init__(self, suitable):
        self.suitable = suitable
        self.suitable.sort()

    def __str__(self):
        return format('No suitable databases were found.  Suitable databases '
                      'include %L.  If you have one of these databases '
                      'installed, make sure it is listed in the '
                      'supybot.databases configuration variable.',
                      self.suitable)

def DB(filename, types):
    # We don't care if any of the DBs are actually available when
    # documenting, so just fake that we found something suitable
    if world.documenting:
        def junk(*args, **kwargs):
            pass
        return junk
    filename = conf.supybot.directories.data.dirize(filename)
    def MakeDB(*args, **kwargs):
        for type in conf.supybot.databases():
            # Can't do this because Python sucks.  Go ahead, try it!
            # filename = '.'.join([filename, type, 'db'])
            fn = '.'.join([filename, type, 'db'])
            try:
                return types[type](fn, *args, **kwargs)
            except KeyError:
                continue
        raise NoSuitableDatabase, types.keys()
    return MakeDB

def makeChannelFilename(filename, channel=None, dirname=None):
    assert channel is not None, 'Death to those who use None for their channel'
    filename = os.path.basename(filename)
    channelSpecific = conf.supybot.databases.plugins.channelSpecific
    channel = channelSpecific.getChannelLink(channel)
    channel = ircutils.toLower(channel)
    if dirname is None:
        dirname = conf.supybot.directories.data.dirize(channel)
    if not os.path.exists(dirname):
            os.makedirs(dirname)
    return os.path.join(dirname, filename)

def getChannel(channel):
    assert channel is not None, 'Death to those who use None for their channel'
    channelSpecific = conf.supybot.databases.plugins.channelSpecific
    return channelSpecific.getChannelLink(channel)

# XXX This shouldn't be a mixin.  This should be contained by classes that
#     want such behavior.  But at this point, it wouldn't gain much for us
#     to refactor it.
# XXX We need to get rid of this, it's ugly and opposed to
#     database-independence.
class ChannelDBHandler(object):
    """A class to handle database stuff for individual channels transparently.
    """
    suffix = '.db'
    def __init__(self, suffix='.db'):
        self.dbCache = ircutils.IrcDict()
        suffix = self.suffix
        if self.suffix and self.suffix[0] != '.':
            suffix = '.' + suffix
        self.suffix = suffix

    def makeFilename(self, channel):
        """Override this to specialize the filenames of your databases."""
        channel = ircutils.toLower(channel)
        className = self.__class__.__name__
        return makeChannelFilename(className + self.suffix, channel)

    def makeDb(self, filename):
        """Override this to create your databases."""
        raise NotImplementedError

    def getDb(self, channel):
        """Use this to get a database for a specific channel."""
        currentThread = threading.currentThread()
        if channel not in self.dbCache and currentThread == world.mainThread:
            self.dbCache[channel] = self.makeDb(self.makeFilename(channel))
        if currentThread != world.mainThread:
            db = self.makeDb(self.makeFilename(channel))
        else:
            db = self.dbCache[channel]
        db.isolation_level = None
        return db

    def die(self):
        for db in self.dbCache.itervalues():
            try:
                db.commit()
            except AttributeError: # In case it's not an SQLite database.
                pass
            try:
                db.close()
            except AttributeError: # In case it doesn't have a close method.
                pass
            del db
        gc.collect()


class DbiChannelDB(object):
    """This just handles some of the general stuff for Channel DBI databases.
    Check out ChannelIdDatabasePlugin for an example of how to use this."""
    def __init__(self, filename):
        self.filename = filename
        self.dbs = ircutils.IrcDict()

    def _getDb(self, channel):
        filename = makeChannelFilename(self.filename, channel)
        try:
            db = self.dbs[channel]
        except KeyError:
            db = self.DB(filename)
            self.dbs[channel] = db
        return db

    def close(self):
        for db in self.dbs.itervalues():
            db.close()

    def flush(self):
        for db in self.dbs.itervalues():
            db.flush()

    def __getattr__(self, attr):
        def _getDbAndDispatcher(channel, *args, **kwargs):
            db = self._getDb(channel)
            return getattr(db, attr)(*args, **kwargs)
        return _getDbAndDispatcher


class ChannelUserDictionary(collections.MutableMapping):
    IdDict = dict
    def __init__(self):
        self.channels = ircutils.IrcDict()

    def __getitem__(self, (channel, id)):
        return self.channels[channel][id]

    def __setitem__(self, (channel, id), v):
        if channel not in self.channels:
            self.channels[channel] = self.IdDict()
        self.channels[channel][id] = v

    def __delitem__(self, (channel, id)):
        del self.channels[channel][id]

    def __iter__(self):
        for channel, ids in self.channels.items():
            for id_, value in ids.items():
                yield (channel, id_)
        raise StopIteration()

    def __len__(self):
        return sum([len(x) for x in self.channels])

    def iteritems(self):
        for (channel, ids) in self.channels.iteritems():
            for (id, v) in ids.iteritems():
                yield ((channel, id), v)

    def keys(self):
        L = []
        for (k, _) in self.iteritems():
            L.append(k)
        return L


# XXX The interface to this needs to be made *much* more like the dbi.DB
#     interface.  This is just too odd and not extensible; any extension
#     would very much feel like an extension, rather than part of the db
#     itself.
class ChannelUserDB(ChannelUserDictionary):
    def __init__(self, filename):
        ChannelUserDictionary.__init__(self)
        self.filename = filename
        try:
            fd = open(self.filename)
        except EnvironmentError, e:
            log.warning('Couldn\'t open %s: %s.', self.filename, e)
            return
        reader = csv.reader(fd)
        try:
            lineno = 0
            for t in reader:
                lineno += 1
                try:
                    channel = t.pop(0)
                    id = t.pop(0)
                    try:
                        id = int(id)
                    except ValueError:
                        # We'll skip over this so, say, nicks can be kept here.
                        pass
                    v = self.deserialize(channel, id, t)
                    self[channel, id] = v
                except Exception, e:
                    log.warning('Invalid line #%s in %s.',
                                lineno, self.__class__.__name__)
                    log.debug('Exception: %s', utils.exnToString(e))
        except Exception, e: # This catches exceptions from csv.reader.
            log.warning('Invalid line #%s in %s.',
                        lineno, self.__class__.__name__)
            log.debug('Exception: %s', utils.exnToString(e))

    def flush(self):
        fd = utils.file.AtomicFile(self.filename, makeBackupIfSmaller=False)
        writer = csv.writer(fd)
        items = self.items()
        if not items:
            log.debug('%s: Refusing to write blank file.',
                      self.__class__.__name__)
            fd.rollback()
            return
        try:
            items.sort()
        except TypeError:
            # FIXME: Implement an algorithm that can order dictionnaries
            # with both strings and integers as keys.
            pass
        for ((channel, id), v) in items:
            L = self.serialize(v)
            L.insert(0, id)
            L.insert(0, channel)
            writer.writerow(L)
        fd.close()

    def close(self):
        self.flush()
        self.clear()

    def deserialize(self, channel, id, L):
        """Should take a list of strings and return an object to be accessed
        via self.get(channel, id)."""
        raise NotImplementedError

    def serialize(self, x):
        """Should take an object (as returned by self.get(channel, id)) and
        return a list (of any type serializable to csv)."""
        raise NotImplementedError


def getUserName(id):
    if isinstance(id, int):
        try:
            return ircdb.users.getUser(id).name
        except KeyError:
            return 'a user that is no longer registered'
    else:
        return id

class ChannelIdDatabasePlugin(callbacks.Plugin):
    class DB(DbiChannelDB):
        class DB(dbi.DB):
            class Record(dbi.Record):
                __fields__ = [
                    'at',
                    'by',
                    'text'
                    ]
            def add(self, at, by, text, **kwargs):
                record = self.Record(at=at, by=by, text=text, **kwargs)
                return super(self.__class__, self).add(record)

    def __init__(self, irc):
        self.__parent = super(ChannelIdDatabasePlugin, self)
        self.__parent.__init__(irc)
        self.db = DB(self.name(), {'flat': self.DB})()

    def die(self):
        self.db.close()
        self.__parent.die()

    def getCommandHelp(self, name, simpleSyntax=None):
        help = self.__parent.getCommandHelp(name, simpleSyntax)
        help = help.replace('$Types', format('%p', self.name()))
        help = help.replace('$Type', self.name())
        help = help.replace('$types', format('%p', self.name().lower()))
        help = help.replace('$type', self.name().lower())
        return help

    def noSuchRecord(self, irc, channel, id):
        irc.error('There is no %s with id #%s in my database for %s.' %
                  (self.name(), id, channel))

    def checkChangeAllowed(self, irc, msg, channel, user, record):
        if user.id == record.by:
            return True
        cap = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, cap):
            return True
        irc.errorNoCapability(cap)

    def addValidator(self, irc, text):
        """This should irc.error or raise an exception if text is invalid."""
        pass

    def add(self, irc, msg, args, user, channel, text):
        """[<channel>] <text>

        Adds <text> to the $type database for <channel>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        at = time.time()
        self.addValidator(irc, text)
        if text is not None:
            id = self.db.add(channel, at, user.id, text)
            irc.replySuccess('%s #%s added.' % (self.name(), id))
    add = wrap(add, ['user', 'channeldb', 'text'])

    def remove(self, irc, msg, args, user, channel, id):
        """[<channel>] <id>

        Removes the $type with id <id> from the $type database for <channel>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        try:
            record = self.db.get(channel, id)
            self.checkChangeAllowed(irc, msg, channel, user, record)
            self.db.remove(channel, id)
            irc.replySuccess()
        except KeyError:
            self.noSuchRecord(irc, channel, id)
    remove = wrap(remove, ['user', 'channeldb', 'id'])

    def searchSerializeRecord(self, record):
        text = utils.str.ellipsisify(record.text, 50)
        return format('#%s: %q', record.id, text)

    def search(self, irc, msg, args, channel, optlist, glob):
        """[<channel>] [--{regexp,by} <value>] [<glob>]

        Searches for $types matching the criteria given.
        """
        predicates = []
        def p(record):
            for predicate in predicates:
                if not predicate(record):
                    return False
            return True

        for (opt, arg) in optlist:
            if opt == 'by':
                predicates.append(lambda r, arg=arg: r.by == arg.id)
            elif opt == 'regexp':
                predicates.append(lambda x: commands.regexp_wrapper(x.text, reobj=arg, 
                        timeout=0.1, plugin_name = self.name(), fcn_name='search'))
                #predicates.append(lambda r, arg=arg: arg.search(r.text))
        if glob:
            def globP(r, glob=glob.lower()):
                return fnmatch.fnmatch(r.text.lower(), glob)
            predicates.append(globP)
        L = []
        for record in self.db.select(channel, p):
            L.append(self.searchSerializeRecord(record))
        if L:
            L.sort()
            irc.reply(format('%s found: %L', len(L), L))
        else:
            what = self.name().lower()
            irc.reply(format('No matching %p were found.', what))
    search = wrap(search, ['channeldb',
                           getopts({'by': 'otherUser',
                                    'regexp': 'regexpMatcher'}),
                           additional(rest('glob'))])

    def showRecord(self, record):
        name = getUserName(record.by)
        return format('%s #%s: %q (added by %s at %t)',
                      self.name(), record.id, record.text, name, record.at)

    def get(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Gets the $type with id <id> from the $type database for <channel>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        try:
            record = self.db.get(channel, id)
            irc.reply(self.showRecord(record))
        except KeyError:
            self.noSuchRecord(irc, channel, id)
    get = wrap(get, ['channeldb', 'id'])

    def change(self, irc, msg, args, user, channel, id, replacer):
        """[<channel>] <id> <regexp>

        Changes the $type with id <id> according to the regular expression
        <regexp>.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        try:
            record = self.db.get(channel, id)
            self.checkChangeAllowed(irc, msg, channel, user, record)
            record.text = replacer(record.text)
            self.db.set(channel, id, record)
            irc.replySuccess()
        except KeyError:
            self.noSuchRecord(irc, channel, id)
    change = wrap(change, ['user', 'channeldb', 'id', 'regexpReplacer'])

    def stats(self, irc, msg, args, channel):
        """[<channel>]

        Returns the number of $types in the database for <channel>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        n = self.db.size(channel)
        whats = self.name().lower()
        irc.reply(format('There %b %n in my database.', n, (n, whats)))
    stats = wrap(stats, ['channeldb'])


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
    under.  It'll be in conf.supybot.directories.data, of course.

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
            if self.periodicFiles[filename][-1] is None:
                fullname = os.path.join(conf.supybot.directories.data(),
                                        filename)
                if os.path.exists(fullname):
                    self.lastDownloaded[filename] = os.stat(fullname).st_ctime
                else:
                    self.lastDownloaded[filename] = 0
            else:
                self.lastDownloaded[filename] = 0
            self.currentlyDownloading = set()
            self.downloadedCounter[filename] = 0
            self.getFile(filename)

    def _downloadFile(self, filename, url, f):
        self.currentlyDownloading.add(filename)
        try:
            try:
                infd = utils.web.getUrlFd(url)
            except IOError, e:
                self.log.warning('Error downloading %s: %s', url, e)
                return
            except utils.web.Error, e:
                self.log.warning('Error downloading %s: %s', url, e)
                return
            confDir = conf.supybot.directories.data()
            newFilename = os.path.join(confDir, utils.file.mktemp())
            outfd = open(newFilename, 'wb')
            start = time.time()
            s = infd.read(4096)
            while s:
                outfd.write(s)
                s = infd.read(4096)
            infd.close()
            outfd.close()
            self.log.info('Downloaded %s in %s seconds',
                          filename, time.time()-start)
            self.downloadedCounter[filename] += 1
            self.lastDownloaded[filename] = time.time()
            if f is None:
                toFilename = os.path.join(confDir, filename)
                if os.name == 'nt':
                    # Windows, grrr...
                    if os.path.exists(toFilename):
                        os.remove(toFilename)
                os.rename(newFilename, toFilename)
            else:
                start = time.time()
                f(newFilename)
                total = time.time() - start
                self.log.info('Function ran on %s in %s seconds',
                              filename, total)
        finally:
            self.currentlyDownloading.remove(filename)

    def getFile(self, filename):
        if world.documenting:
            return
        (url, timeLimit, f) = self.periodicFiles[filename]
        if time.time() - self.lastDownloaded[filename] > timeLimit and \
           filename not in self.currentlyDownloading:
            self.log.info('Beginning download of %s', url)
            args = (filename, url, f)
            name = '%s #%s' % (filename, self.downloadedCounter[filename])
            t = threading.Thread(target=self._downloadFile, name=name,
                                 args=(filename, url, f))
            t.setDaemon(True)
            t.start()
            world.threadsSpawned += 1




# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
