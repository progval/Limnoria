#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

import fix

import os
import sys
import sets
import time
import types
import urllib2
import threading

import fix
import cdb
import conf
import debug
import utils
import world
import ircdb
import ircutils
import privmsgs
import callbacks
import re
import random

__all__ = ['ChannelDBHandler', 'PeriodicFileDownloader', 'ToggleDictionary']

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
        """Override this to specialize the filenames of your databases."""
        channel = ircutils.toLower(channel)
        prefix = '%s-%s%s' % (channel, self.__class__.__name__, self.suffix)
        return os.path.join(conf.dataDir, prefix)

    def makeDb(self, filename):
        """Override this to create your databases."""
        return cdb.shelf(filename)

    def getDb(self, channel):
        """Use this to get a database for a specific channel."""
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
            try:
                db.commit()
            except AttributeError: # In case it's not an SQLite database.
                pass
            try:
                db.close()
            except AttributeError: # In case it doesn't have a close method.
                pass
            del db


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
            if self.periodicFiles[filename][-1] is None:
                fullname = os.path.join(conf.dataDir, filename)
                if os.path.exists(fullname):
                    self.lastDownloaded[filename] = os.stat(fullname).st_ctime
                else:
                    self.lastDownloaded[filename] = 0
            else:
                self.lastDownloaded[filename] = 0
            self.currentlyDownloading = sets.Set()
            self.downloadedCounter[filename] = 0
            self.getFile(filename)

    def _downloadFile(self, filename, url, f):
        infd = urllib2.urlopen(url)
        newFilename = os.path.join(conf.dataDir, utils.mktemp())
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
            toFilename = os.path.join(conf.dataDir, filename)
            if os.name == 'nt':
                # Windows, grrr...
                if os.path.exists(toFilename):
                    os.remove(toFilename)
            os.rename(newFilename, toFilename)
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
            t.setDaemon(True)
            t.start()
            world.threadsSpawned += 1
        

class ToggleDictionary(object):
    """I am ToggleDictionary! Hear me roar!
    """
    def __init__(self, toggles):
        if not toggles:
            raise ValueError, 'At least one toggle must be provided.'
        self.channels = ircutils.IrcDict()
        self.defaults = {}
        for (k, v) in toggles.iteritems():
            self.defaults[callbacks.canonicalName(k)] = v

    def _getDict(self, channel):
        #debug.printf('_getDict(%s)' % channel)
        if channel is None:
            return self.defaults
        else:
            assert ircutils.isChannel(channel) or ircutils.isNick(channel)
            if channel not in self.channels:
                self.channels[channel] = self.defaults.copy()
            return self.channels[channel]

    def get(self, key, channel=None):
        key = callbacks.canonicalName(key)
        return self._getDict(channel)[key]

    def toggle(self, key, value=None, channel=None):
        #debug.printf('inside toggle: %s %s %s' % (key, value, channel))
        if channel is not None:
            assert ircutils.isChannel(channel) or ircutils.isNick(channel)
        d = self._getDict(channel)
        key = callbacks.canonicalName(key)
        if value is None:
            d[key] = not d[key] # Raises KeyError, we want this.
        else:
            # I considered this, to save the if statement:
            # d[key] = (d[key] ^ d[key]) or value
            # But didn't, so people can provide non-boolean keys.
            if key in d:
                d[key] = value
            else:
                raise KeyError, key

    def toString(self, channel=None):
        resp = []
        d = self._getDict(channel)
        for (k, v) in d.iteritems():
            if v:
                resp.append('%s: On' % k)
            else:
                resp.append('%s: Off' % k)
        resp.sort()
        return '(%s)' % '; '.join(resp)


class Toggleable(object):
    """A mixin class to provide a 'toggle' command that can be consistent
    across plugins.  To use this class, simply define a 'toggles' attribute
    in your class that is a ToggleDictionary mapping valid attributes to toggle
    to their default values.
    """
    def __init__(self):
        s = """[<channel>] <name> [<value>]

        Toggles the value of <name> in <channel>.  If <value> is given,
        explicitly sets the value of <name> to <value>.  <channel> is only
        necessary if the message isn't sent in the channel itself.  Valid
        names are %s""" % (self._toggleNames())
        code = self.toggle.im_func.func_code
        globals = self.toggle.im_func.func_globals
        closure = self.toggle.im_func.func_closure
        newf = types.FunctionType(code, globals, None, closure=closure)
        newf.__doc__ = s
        self.__class__.toggle = types.MethodType(newf, self, self.__class__)

    def _toggleNames(self):
        names = self.toggles.defaults.keys()
        names.sort()
        return utils.commaAndify(map(repr, names))
        
    def toggle(self, irc, msg, args):
        """[<channel>] <name> [<value>]

        The author of my plugin didn't call Toggleable.__init__.
        """
        #debug.printf('%s.toggle called.' % self.__class__)
        try:
            channel = privmsgs.getChannel(msg, args)
            capability = ircdb.makeChannelCapability(channel, 'op')
        except callbacks.ArgumentError:
            raise
        except callbacks.Error:
            channel = None
            capability = 'admin'
        if not ircdb.checkCapability(msg.prefix, capability):
            irc.error(msg, conf.replyNoCapability % capability)
            return
        (name, value) = privmsgs.getArgs(args, optional=1)
        if not value:
            value = None
        elif value.lower() in ('enable', 'on', 'true'):
            value = True
        elif value.lower() in ('disable', 'off', 'false'):
            value = False
        else:
            irc.error(msg, '%r isn\'t a valid value.' % value)
            return
        try:
            self.toggles.toggle(name, value=value, channel=channel)
            s = '%s  %s' % (conf.replySuccess, self.toggles.toString(channel))
            irc.reply(msg, s)
        except KeyError:
            irc.error(msg, '%r isn\'t a valid name to toggle.  '
                           'Valid names are %s' % (name, self._toggleNames()))

randomnickre = re.compile ("\$randomnick", re.I)
randomdatere = re.compile ("\$randomdate", re.I)
randomintre = re.compile ("\$randomint", re.I)
whore = re.compile ("\$who", re.I)
botnickre = re.compile("\$botnick", re.I)
todayre = re.compile("\$today", re.I)
def standardSubstitute(irc, msg, text):
    """Do the standard set of substitutions on text, and return it"""
    nochannel = False
    try:
        channel = privmsgs.getChannel(msg, None)
    except:
        nochannel = True
    if nochannel:
        text = randomnickre.sub('anyone', text)
    else:
        text = randomnickre.sub(random.choice(irc.state.channels[channel].users._data.keys()),
                text)
    t = pow(2,30)*random.random()+time.time()/4.0 
    text = randomdatere.sub(time.ctime(t), text)
    text = randomintre.sub(str(random.randint(-1000, 1000)), text)
    text = whore.sub(msg.nick, text)
    text = botnickre.sub(irc.nick, text)
    text = todayre.sub(time.ctime(), text)
    return text
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
