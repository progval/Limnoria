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

from fix import *

import os
import time
import atexit
import string

import conf
import world
import ircutils

def fromChannelCapability(capability):
    return capability.split('.', 1)

def isChannelCapability(capability):
    if '.' in capability:
        (channel, capability) = fromChannelCapability(capability)
        return ircutils.isChannel(channel)
    else:
        return False

def makeChannelCapability(channel, capability):
    return '%s.%s' % (channel, capability)

def isAntiCapability(capability):
    if isChannelCapability(capability):
        (_, capability) = fromChannelCapability(capability)
    return capability[0] == '!'

def makeAntiCapability(capability):
    if '.' in capability:
        (channel, capability) = fromChannelCapability(capability)
        return '%s.!%s' % (channel, capability)
    else:
        return '!' + capability

_normal = string.maketrans('\r\n', '  ')
def normalize(s):
    return s.translate(_normal)


class IrcUser(object):
    """This class holds the capabilities and authentications for a user.
    """
    def __init__(self, ignore=False, password='', auth=None,
                 capabilities=None, hostmasks=None):
        self.auth = auth # The (time, hostmask) a user authenticated under.
        self.ignore = ignore # A boolean deciding if the person is ignored.
        self.password = password # password (plaintext? hashed?)
        self.capabilities = set()
        if capabilities is not None:
            for capability in capabilities:
                self.capabilities.add(capability)
        if hostmasks is None:
            self.hostmasks = [] # A list of hostmasks used for recognition
        else:
            self.hostmasks = hostmasks

    def __repr__(self):
        return '%s(ignore=%s, auth=%r, password=%r, '\
               'capabilities=%r, hostmasks=%r)\n' %\
               (self.__class__.__name__, self.ignore, self.auth,
                self.password, self.capabilities, self.hostmasks)

    def addCapability(self, capability):
        self.capabilities.add(capability)

    def removeCapability(self, capability):
        if capability in self.capabilities:
            self.capabilities.remove(capability)

    def checkCapability(self, capability):
        if self.ignore:
            if isAntiCapability(capability):
                return True
            else:
                return False
        elif capability in self.capabilities:
            return True
        else:
            return False

    def setPassword(self, password):
        self.password = password

    def checkPassword(self, password):
        return (self.password == password)

    def checkHostmask(self, hostmask):
        if self.auth and (hostmask == self.auth[1]):
            return True
        for pat in self.hostmasks:
            if ircutils.hostmaskPatternEqual(pat, hostmask):
                return True
        return False

    def addHostmask(self, hostmask):
        self.hostmasks.append(hostmask)

    def removeHostmask(self, hostmask):
        self.hostmasks = [s for s in self.hostmasks if s != hostmask]

    def hasHostmask(self, hostmask):
        return hostmask in self.hostmasks

    def setAuth(self, hostmask):
        self.auth = (time.time(), hostmask)

    def unsetAuth(self):
        self.auth = None

    def checkAuth(self, hostmask):
        if self.auth is not None:
            (timeSet, prefix) = self.auth
            if time.time() - timeSet < 3600:
                if hostmask == prefix:
                    return True
                else:
                    return False
            else:
                self.unsetAuth()
                return False
        else:
            return False


class IrcChannel(object):
    """This class holds the capabilities, bans, and ignores of a channel.
    """
    defaultOff = ['op', 'halfop', 'voice', 'protected']
    def __init__(self, bans=None, ignores=None, capabilities=None,
                 lobotomized=False, defaultAllow=True):
        self.defaultAllow = defaultAllow
        if bans is None:
            self.bans = []
        else:
            self.bans = bans
        if ignores is None:
            self.ignores = []
        else:
            self.ignores = ignores
        if capabilities is None:
            self.capabilities = {}
        else:
            self.capabilities = capabilities

        for capability in self.defaultOff:
            if capability not in self.capabilities:
                self.capabilities[capability] = False
        self.lobotomized = lobotomized

    def __repr__(self):
        return '%s(bans=%r, ignores=%r, capabilities=%r, '\
               'lobotomized=%r, defaultAllow=%s)\n' %\
               (self.__class__.__name__, self.bans, self.ignores,
                self.capabilities, self.lobotomized,
                self.defaultAllow)

    def addBan(self, hostmask):
        self.bans.append(hostmask)

    def removeBan(self, hostmask):
        self.bans = [s for s in self.bans if s != hostmask]

    def checkBan(self, hostmask):
        for pat in self.bans:
            if ircutils.hostmaskPatternEqual(pat, hostmask):
                return True
        return False

    def addIgnore(self, hostmask):
        self.ignores.append(hostmask)

    def removeIgnore(self, hostmask):
        self.ignores = [s for s in self.ignores if s != hostmask]

    def addCapability(self, capability, value):
        self.capabilities[capability] = value

    def removeCapability(self, capability):
        del self.capabilities[capability]

    def setDefaultCapability(self, v):
        self.defaultAllow = v

    def checkCapability(self, capability):
        if capability in self.capabilities:
            return self.capabilities[capability]
        elif isAntiCapability(capability):
            return not self.defaultAllow
        else:
            return self.defaultAllow

    def checkIgnored(self, hostmask):
        if self.lobotomized:
            return True
        for mask in self.bans:
            if ircutils.hostmaskPatternEqual(mask, hostmask):
                return True
        for mask in self.ignores:
            if ircutils.hostmaskPatternEqual(mask, hostmask):
                return True
        return False


class UsersDictionary(object):
    def __init__(self, filename):
        self.filename = filename
        fd = file(filename, 'r')
        s = fd.read()
        fd.close()
        self.dict = eval(normalize(s))
        self.cache = {} # hostmasks to nicks.
        self.revcache = {} # nicks to hostmasks.

    def resetCache(self, s):
        if s in self.cache:
            # it's a hostmask.
            name = self.cache[s]
            del self.cache[s]
        else:
            # it's already a name.
            name = s
        # name should always be in self.revcache, this should never KeyError.
        if name in self.revcache:
            for hostmask in self.revcache[name]:
                del self.cache[hostmask]
            del self.revcache[name]

    def setCache(self, hostmask, name):
        self.cache[hostmask] = name
        self.revcache.setdefault(name, []).append(hostmask)

    def getUser(self, s):
        if ircutils.isUserHostmask(s):
            name = self.getUserName(s)
        else:
            name = s
        return self.dict[name]

    def setUser(self, s, u):
        # First, invalidate the cache for this user.
        self.resetCache(s)
        if ircutils.isUserHostmask(s):
            name = self.getUserName(s)
        else:
            name = s
        self.dict[name] = u

    def hasUser(self, s):
        return (s in self.dict)

    def delUser(self, s):
        if ircutils.isUserHostmask(s):
            name = self.getUserName(s)
        else:
            name = s
        self.resetCache(name)
        del self.dict[name]

    def getUserName(self, s):
        assert ircutils.isUserHostmask(s), 'string must be a hostmask'
        if s in self.cache:
            return self.cache[s]
        else:
            for (name, user) in self.dict.iteritems():
                if user.checkHostmask(s):
                    self.cache[s] = name
                    self.revcache.setdefault(name,[]).append(s)
                    return name
            raise KeyError, s

    def flush(self):
        fd = file(self.filename, 'w')
        fd.write(repr(self.dict))
        fd.close()

    def reload(self):
        self.__init__(self.filename)

class ChannelsDictionary(object):
    def __init__(self, filename):
        self.filename = filename
        fd = file(filename, 'r')
        s = fd.read()
        fd.close()
        self.dict = eval(normalize(s))

    def getChannel(self, channel):
        channel = channel.lower()
        if channel in self.dict:
            return self.dict[channel]
        else:
            c = IrcChannel()
            self.dict[channel] = c
            return c

    def setChannel(self, channel, ircChannel):
        channel = channel.lower()
        self.dict[channel] = ircChannel

    def flush(self):
        fd = file(self.filename, 'w')
        fd.write(repr(self.dict))
        fd.close()

    def reload(self):
        self.__init__(self.filename)


###
# Later, I might add some special handling for botnet.
###
if not os.path.exists(conf.userfile):
    fd = open(conf.userfile, 'w')
    fd.write('{}')
    fd.close()
users = UsersDictionary(conf.userfile)

if not os.path.exists(conf.channelfile):
    fd = file(conf.channelfile, 'w')
    fd.write('{}')
    fd.close()
channels = ChannelsDictionary(conf.channelfile)

atexit.register(users.flush)
atexit.register(channels.flush)

world.flushers.append(users.flush)
world.flushers.append(channels.flush)

###
# Useful functions for checking credentials.
###
def checkIgnored(hostmask, recipient='', users=users, channels=channels):
    """checkIgnored(hostmask, recipient='') -> True/False

    Checks if the user is ignored by the recipient of the message.
    """
    for ignore in conf.ignores:
        if ircutils.hostmaskPatternEqual(ignore, hostmask):
            return True
    try:
        user = users.getUser(hostmask)
    except KeyError:
        # If there's no user...
        if ircutils.isChannel(recipient):
            channel = channels.getChannel(recipient)
            return channel.checkIgnored(hostmask)
        else:
            return conf.defaultIgnore
    if user.checkCapability('owner'):
        # Owners shouldn't ever be ignored.
        return False
    elif user.ignore:
        return True
    elif recipient:
        if ircutils.isChannel(recipient):
            channel = channels.getChannel(recipient)
            return channel.checkIgnored(hostmask)
        else:
            return False
    else:
        return False

def checkCapability(hostmask, capability, users=users, channels=channels):
    """checkCapability(hostmask, recipient, capability) -> True/False

    Checks if the user represented by hostmask has capability with recipient.
    """
    ###
    # This is a hard function to write correctly.
    #
    # Basically, we want to return whether or not a user has a certain
    # capability in a given channel.  This should be easy, but the various
    # different cases are all hard to get right.

    if world.startup:
        # Are we in special startup mode?
        if isAntiCapability(capability):
            return False
        else:
            return True
    try:
        u = users.getUser(hostmask)
    except KeyError: # the user isn't in the database.
        # First, check to see if we're asking for a channel capability:
        if isChannelCapability(capability):
            # If it is, we'll check the channel.
            try:
                (channel, capability) = fromChannelCapability(capability)
            except ValueError: # unpack list of wrong size
                return False   # stupid, invalid capability.
            # Now, go fetch the channel and check to see what it thinks about
            # said capability.
            c = channels.getChannel(channel)
            # Channels have their own defaults, so we can just directly return
            # what the channel has to say about the capability.
            return c.checkCapability(capability)
        else: # It's not a channel capability.
            # If it's not a channel, then the only thing we have to go by is
            # conf.defaultCapabilities.
            return (capability in conf.defaultCapabilities)
    # Good, the user exists.
    # First, we check to see if it's an owner -- if it is, it should have all
    # capabilities and should not have any negative capabilities.
    if u.checkCapability('owner'):
        if isAntiCapability(capability):
            return False
        else:
            return True
    # Now, we need to check if it's a channel capability or not.
    if isChannelCapability(capability):
        # First check to see if the user has the capability already; if so,
        # it can be returned without checking the channel.
        try:
            return u.checkCapability(capability)
        except KeyError:
            # User doesn't have the capability.  Check the channel.
            try:
                (channel, capability) = fromChannelCapability(capability)
            except ValueError:
                return False # stupid, invalid capability.
            c = channels.getChannel(channel)
            # And return the channel's opinion.
            return c.checkCapability(capability)
    else: # It's not a channel capability.
        # Just check the user.
        try:
            return u.checkCapability(capability)
        except KeyError:
            return (capability in conf.defaultCapabilities)

def checkCapabilities(hostmask, capabilities, requireAll=False):
    """Checks that a user has capabilities in a list.

    requireAll is the True if *all* capabilities in the list must be had, False
    if *any* of the capabilities in the list must be had.
    """
    for capability in capabilities:
        if requireAll:
            if not checkCapability(hostmask, capability):
                return False
        else:
            if checkCapability(hostmask, capability):
                return True
    if requireAll:
        return True
    else:
        return False

def getUser(irc, s):
    if ircutils.isUserHostmask(s):
        return users.getUserName(s)
    else:
        if users.hasUser(s):
            return s
        else:
            return users.getUserName(irc.state.nickToHostmask(s))

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
