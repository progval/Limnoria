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

__revision__ = "$Id$"

import fix

import os
import sets
import time
import string
from itertools import imap, ilen, ifilter

import log
import conf
import utils
import world
import ircutils
from structures import PersistentDictionary

def fromChannelCapability(capability):
    """Returns a (channel, capability) tuple from a channel capability."""
    assert isChannelCapability(capability)
    return capability.split(',', 1)

def isChannelCapability(capability):
    """Returns True if capability is a channel capability; False otherwise."""
    if ',' in capability:
        (channel, capability) = capability.split(',', 1)
        return ircutils.isChannel(channel)
    else:
        return False

def makeChannelCapability(channel, capability):
    """Makes a channel capability given a channel and a capability."""
    return '%s,%s' % (channel, capability)

def isAntiCapability(capability):
    """Returns True if capability is an anticapability; False otherwise."""
    if isChannelCapability(capability):
        (_, capability) = fromChannelCapability(capability)
    return capability and capability[0] == '-'

def makeAntiCapability(capability):
    """Returns the anticapability of a given capability."""
    assert not isAntiCapability(capability), 'makeAntiCapability does not ' \
           'work on anticapabilities; you probably want invertCapability.'
    if isChannelCapability(capability):
        (channel, capability) = fromChannelCapability(capability)
        return makeChannelCapability(channel, '-' + capability)
    else:
        return '-' + capability

def unAntiCapability(capability):
    """Takes an anticapability and returns the non-anti form."""
    if not isAntiCapability(capability):
        raise ValueError, '%s is not an anti capability' % capability
    if isChannelCapability(capability):
        (channel, capability) = fromChannelCapability(capability)
        return ','.join((channel, capability[1:]))
    else:
        return capability[1:]

def invertCapability(capability):
    """Make a capability into an anticapability and vice versa."""
    if isAntiCapability(capability):
        return unAntiCapability(capability)
    else:
        return makeAntiCapability(capability)

_normal = string.maketrans('\r\n', '  ')
def _normalize(s):
    return s.translate(_normal)


_invert = invertCapability
class CapabilitySet(sets.Set):
    """A subclass of set handling basic capability stuff."""
    def __init__(self, capabilities=()):
        self.__parent = super(CapabilitySet, self)
        self.__parent.__init__()
        for capability in capabilities:
            self.add(capability)

    def add(self, capability):
        """Adds a capability to the set."""
        capability = ircutils.toLower(capability)
        inverted = _invert(capability)
        if self.__parent.__contains__(inverted):
            self.__parent.remove(inverted)
        self.__parent.add(capability)

    def remove(self, capability):
        """Removes a capability from the set."""
        capability = ircutils.toLower(capability)
        self.__parent.remove(capability)

    def __contains__(self, capability):
        capability = ircutils.toLower(capability)
        if self.__parent.__contains__(capability):
            return True
        if self.__parent.__contains__(_invert(capability)):
            return True
        else:
            return False

    def check(self, capability):
        """Returns the appropriate boolean for whether a given capability is
        'allowed' given its (or its anticapability's) presence in the set.
        """
        capability = ircutils.toLower(capability)
        if self.__parent.__contains__(capability):
            return True
        elif self.__parent.__contains__(_invert(capability)):
            return False
        else:
            raise KeyError, capability

    def __repr__(self):
        return '%s([%s])' % (self.__class__.__name__,
                             ', '.join(imap(repr, self)))

antiOwner = makeAntiCapability('owner')
class UserCapabilitySet(CapabilitySet):
    """A subclass of CapabilitySet to handle the owner capability correctly."""
    def __init__(self, *args, **kwargs):
        self.__parent = super(UserCapabilitySet, self)
        self.__parent.__init__(*args, **kwargs)
        
    def __contains__(self, capability):
        capability = ircutils.toLower(capability)
        if capability == 'owner' or capability == antiOwner:
            return True
        elif self.__parent.__contains__('owner'):
            return True
        else:
            return self.__parent.__contains__(capability)

    def check(self, capability):
        """Returns the appropriate boolean for whether a given capability is
        'allowed' given its (or its anticapability's) presence in the set.
        Differs from CapabilitySet in that it handles the 'owner' capability
        appropriately.
        """
        capability = ircutils.toLower(capability)
        if capability == 'owner' or capability == antiOwner:
            if self.__parent.__contains__('owner'):
                return not isAntiCapability(capability)
            else:
                return isAntiCapability(capability)
        elif self.__parent.__contains__('owner'):
            if isAntiCapability(capability):
                return False
            else:
                return True
        else:
            return self.__parent.check(capability)

    def add(self, capability):
        """Adds a capability to the set.  Just make sure it's not -owner."""
        capability = ircutils.toLower(capability)
        assert capability != '-owner', '"-owner" disallowed.'
        self.__parent.add(capability)

class IrcUser(object):
    """This class holds the capabilities and authentications for a user."""
    def __init__(self, ignore=False, password='', name='',
                 capabilities=(), hostmasks=None, secure=False, hashed=False):
        self.auth = None # The (time, hostmask) a user authenticated under
        self.name = name # The name of the user.
        self.ignore = ignore # A boolean deciding if the person is ignored.
        self.secure = secure # A boolean describing if hostmasks *must* match.
        self.hashed = hashed # True if the password is hashed on disk.
        self.password = password # password (plaintext? hashed?)
        self.capabilities = UserCapabilitySet()
        for capability in capabilities:
            self.capabilities.add(capability)
        if hostmasks is None:
            self.hostmasks = [] # A list of hostmasks used for recognition
        else:
            self.hostmasks = hostmasks

    def __repr__(self):
        return '%s(ignore=%s, password=%r, name=%r, hashed=%r, ' \
               'capabilities=%r, hostmasks=%r, secure=%r)\n' % \
               (self.__class__.__name__,
                self.ignore, self.password, self.name, self.hashed,
                self.capabilities, self.hostmasks, self.secure)

    def addCapability(self, capability):
        """Gives the user the given capability."""
        self.capabilities.add(capability)

    def removeCapability(self, capability):
        """Takes from the user the given capability."""
        self.capabilities.remove(capability)

    def checkCapability(self, capability):
        """Checks the user for a given capability."""
        if self.ignore:
            if isAntiCapability(capability):
                return True
            else:
                return False
        else:
            return self.capabilities.check(capability)

    def setPassword(self, password, hashed=False):
        """Sets the user's password."""
        if hashed or self.hashed:
            self.hashed = True
            self.password = utils.saltHash(password)
        else:
            self.password = password

    def checkPassword(self, password):
        """Checks the user's password."""
        if self.hashed:
            (salt, _) = self.password.split('|')
            return (self.password == utils.saltHash(password, salt=salt))
        else:
            return (self.password == password)

    def checkHostmask(self, hostmask, useAuth=True):
        """Checks a given hostmask against the user's hostmasks or current
        authentication.  If useAuth is False, only checks against the user's
        hostmasks.
        """
        if useAuth and self.auth and (hostmask == self.auth[1]):
            return True
        for pat in self.hostmasks:
            if ircutils.hostmaskPatternEqual(pat, hostmask):
                return True
        return False

    def addHostmask(self, hostmask):
        """Adds a hostmask to the user's hostmasks."""
        self.hostmasks.append(hostmask)

    def removeHostmask(self, hostmask):
        """Removes a hostmask from the user's hostmasks."""
        self.hostmasks = [s for s in self.hostmasks if s != hostmask]

    def setAuth(self, hostmask):
        """Sets a user's authenticated hostmask.  This times out in 1 hour."""
        if self.checkHostmask(hostmask, useAuth=False) or not self.secure:
            self.auth = (time.time(), hostmask)
        else:
            raise ValueError, 'secure flag set, unmatched hostmask'

    def unsetAuth(self):
        """Unsets a use's authenticated hostmask."""
        self.auth = None


class IrcChannel(object):
    """This class holds the capabilities, bans, and ignores of a channel.
    """
    defaultOff = ('op', 'halfop', 'voice', 'protected')
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
            self.capabilities = CapabilitySet()
        else:
            self.capabilities = capabilities
        for capability in self.defaultOff:
            if capability not in self.capabilities:
                self.capabilities.add(makeAntiCapability(capability))
        self.lobotomized = lobotomized

    def __repr__(self):
        return '%s(bans=%r, ignores=%r, capabilities=%r, ' \
               'lobotomized=%r, defaultAllow=%s)\n' % \
               (self.__class__.__name__, self.bans, self.ignores,
                self.capabilities, self.lobotomized,
                self.defaultAllow)

    def addBan(self, hostmask):
        """Adds a ban to the channel banlist."""
        self.bans.append(hostmask)

    def removeBan(self, hostmask):
        """Removes a ban from the channel banlist."""
        self.bans = [s for s in self.bans if s != hostmask]

    def checkBan(self, hostmask):
        """Checks whether a given hostmask is banned by the channel banlist."""
        for pat in self.bans:
            if ircutils.hostmaskPatternEqual(pat, hostmask):
                return True
        return False

    def addIgnore(self, hostmask):
        """Adds an ignore to the channel ignore list."""
        self.ignores.append(hostmask)

    def removeIgnore(self, hostmask):
        """Removes an ignore from the channel ignore list."""
        self.ignores = [s for s in self.ignores if s != hostmask]

    def addCapability(self, capability):
        """Adds a capability to the channel's default capabilities."""
        self.capabilities.add(capability)

    def removeCapability(self, capability):
        """Removes a capability from the channel's default capabilities."""
        self.capabilities.remove(capability)

    def setDefaultCapability(self, b):
        """Sets the default capability in the channel."""
        self.defaultAllow = b

    def checkCapability(self, capability):
        """Checks whether a certain capability is allowed by the channel."""
        if capability in self.capabilities:
            return self.capabilities.check(capability)
        else:
            if isAntiCapability(capability):
                return not self.defaultAllow
            else:
                return self.defaultAllow

    def checkIgnored(self, hostmask):
        """Checks whether a given hostmask is to be ignored by the channel."""
        if self.lobotomized:
            return True
        for mask in self.bans:
            if ircutils.hostmaskPatternEqual(mask, hostmask):
                return True
        for mask in self.ignores:
            if ircutils.hostmaskPatternEqual(mask, hostmask):
                return True
        return False

class UsersDB(object):
    """A simple serialized-to-file User Database."""
    def __init__(self, filename):
        self.filename = filename
        if os.path.exists(filename):
            fd = file(filename, 'r')
            s = fd.read()
            fd.close()
            IrcSet = ircutils.IrcSet
            (self.nextId, self.users) = eval(_normalize(s))
        else:
            self.nextId = 1
            self.users = [IrcUser(capabilities=['owner'],
                                  password=utils.mktemp())]
        self._nameCache = {}
        self._hostmaskCache = {}

    def reload(self):
        """Reloads the database from its file."""
        self.__init__(self.filename)

    def flush(self):
        """Flushes the database to its file."""
        fd = file(self.filename, 'w')
        fd.write(repr((self.nextId, self.users)))
        fd.close()

    def getUserId(self, s):
        """Returns the user ID of a given name or hostmask."""
        if ircutils.isUserHostmask(s):
            try:
                return self._hostmaskCache[s]
            except KeyError:
                ids = []
                for (id, user) in enumerate(self.users):
                    if user is None:
                        continue
                    if user.checkHostmask(s):
                        ids.append(id)
                if len(ids) == 1:
                    id = ids[0]
                    self._hostmaskCache[s] = id
                    try:
                        self._hostmaskCache[id].add(s)
                    except KeyError:
                        self._hostmaskCache[id] = sets.Set([s])
                    return id
                elif len(ids) == 0:
                    raise KeyError, s
                else:
                    raise ValueError, 'Ids %r matched.' % ids
        else: # Not a hostmask, must be a name.
            s = s.lower()
            try:
                return self._nameCache[s]
            except KeyError:
                for (id, user) in enumerate(self.users):
                    if user is None:
                        continue
                    if s == user.name.lower():
                        self._nameCache[s] = id
                        self._nameCache[id] = s
                        return id
                else:
                    raise KeyError, s

    def getUser(self, id):
        """Returns a user given its id, name, or hostmask."""
        if not isinstance(id, int):
            # Must be a string.  Get the UserId first.
            id = self.getUserId(id)
        try:
            ret = self.users[id]
            if ret is None:
                raise KeyError, id
            return ret
        except IndexError:
            raise KeyError, id

    def hasUser(self, id):
        """Returns the database has a user given its id, name, or hostmask."""
        try:
            self.getUser(id)
            return True
        except KeyError:
            return False

    def __iter__(self):
        x = ifilter(None, self.users)
        x.next() # Skip the bot user.
        return x
        
    def numUsers(self):
        return ilen(self)

    def setUser(self, id, user):
        """Sets a user (given its id) to the IrcUser given it."""
        assert isinstance(id, int), 'setUser takes an integer userId.'
        if (not 0 <= id < len(self.users)) or self.users[id] is None:
            raise KeyError, id
        try:
            if self.getUserId(user.name) != id:
                s = '%s is already registered to someone else.' % user.name
                raise ValueError, s
        except KeyError:
            pass
        for hostmask in user.hostmasks:
            try:
                if self.getUserId(hostmask) != id:
                    s = '%s is already registered to someone else.'% hostmask
                    raise ValueError, s
            except KeyError:
                continue
        if id in self._nameCache:
            del self._nameCache[self._nameCache[id]]
            del self._nameCache[id]
        if id in self._hostmaskCache:
            for hostmask in self._hostmaskCache[id]:
                del self._hostmaskCache[hostmask]
            del self._hostmaskCache[id]
        self.users[id] = user
        self.flush()

    def delUser(self, id):
        """Removes a user from the database."""
        if not 0 <= id < len(self.users) or self.users[id] is None:
            raise KeyError, id
        self.users[id] = None
        if id in self._nameCache:
            del self._nameCache[self._nameCache[id]]
            del self._nameCache[id]
        if id in self._hostmaskCache:
            for hostmask in self._hostmaskCache[id]:
                del self._hostmaskCache[hostmask]
            del self._hostmaskCache[id]
        self.flush()

    def newUser(self):
        """Allocates a new user in the database and returns it and its id."""
        user = IrcUser()
        id = self.nextId
        self.nextId += 1
        self.users.append(user)
        self.flush()
        return (id, user)
    


class ChannelsDictionary(utils.IterableMap):
    def __init__(self, filename):
        self.filename = filename
        Set = sets.Set
        self.dict = PersistentDictionary(filename, globals(), locals())

    def getChannel(self, channel):
        """Returns an IrcChannel object for the given channel."""
        channel = channel.lower()
        if channel in self.dict:
            return self.dict[channel]
        else:
            c = IrcChannel()
            self.dict[channel] = c
            return c

    def setChannel(self, channel, ircChannel):
        """Sets a given channel to the IrcChannel object given."""
        channel = channel.lower()
        self.dict[channel] = ircChannel
        self.flush()

    def flush(self):
        """Flushes the channel database to its file."""
        self.dict.flush()

    def reload(self):
        """Reloads the channel database from its file."""
        self.__init__(self.filename)

    def iteritems(self):
        return self.dict.iteritems()


###
# Later, I might add some special handling for botnet.
###
confDir = conf.supybot.directories.conf()
users = UsersDB(os.path.join(confDir,
                             conf.supybot.databases.users.filename()))
channels = ChannelsDictionary(os.path.join(confDir,
                              conf.supybot.databases.channels.filename()))

###
# Useful functions for checking credentials.
###
def checkIgnored(hostmask, recipient='', users=users, channels=channels):
    """checkIgnored(hostmask, recipient='') -> True/False

    Checks if the user is ignored by the recipient of the message.
    """
    for ignore in conf.supybot.ignores():
        if ircutils.hostmaskPatternEqual(ignore, hostmask):
            log.debug('Ignoring %s due to conf.supybot.ignores.', hostmask)
            return True
    try:
        id = users.getUserId(hostmask)
        user = users.getUser(id)
    except KeyError:
        # If there's no user...
        if ircutils.isChannel(recipient):
            channel = channels.getChannel(recipient)
            if channel.checkIgnored(hostmask):
                log.debug('Ignoring %s due to the channel ignores.', hostmask)
                return True
            else:
                return False
        else:
            if conf.supybot.defaultIgnore():
                log.debug('Ignoring %s due to conf.supybot.defaultIgnore',
                         hostmask)
                return True
            else:
                return False
    if user.checkCapability('owner'):
        # Owners shouldn't ever be ignored.
        return False
    elif user.ignore:
        log.debug('Ignoring %s due to his IrcUser ignore flag.', hostmask)
        return True
    elif recipient:
        if ircutils.isChannel(recipient):
            channel = channels.getChannel(recipient)
            if channel.checkIgnored(hostmask):
                log.debug('Ignoring %s due to the channel ignores.', hostmask)
                return True
            else:
                return False
        else:
            return False
    else:
        return False

def _x(capability, ret):
    if isAntiCapability(capability):
        return not ret
    else:
        return ret

def _checkCapabilityForUnknownUser(capability, users=users, channels=channels):
    if isChannelCapability(capability):
        (channel, capability) = fromChannelCapability(capability)
        try:
            c = channels.getChannel(channel)
            if capability in c.capabilities:
                return c.checkCapability(capability)
            else:
                return _x(capability, c.defaultAllow)
        except KeyError:
            pass
    if capability in conf.supybot.defaultCapabilities():
        return True
    elif invertCapability(capability) in conf.supybot.defaultCapabilities():
        return False
    else:
        return _x(capability, conf.supybot.defaultAllow())

def checkCapability(hostmask, capability, users=users, channels=channels):
    """Checks that the user specified by name/hostmask has the capabilty given.
    """
    if world.testing:
        return _x(capability, True)
    try:
        u = users.getUser(hostmask)
        if u.secure and not u.checkHostmask(hostmask, useAuth=False):
            raise KeyError
    except KeyError:
        # Raised when no hostmasks match.
        return _checkCapabilityForUnknownUser(capability, users=users,
                                              channels=channels)
    except ValueError, e:
        # Raised when multiple hostmasks match.
        log.warning('%s: %s', hostmask, e)
        return _checkCapabilityForUnknownUser(capability, users=users,
                                              channels=channels)
    if capability in u.capabilities:
        return u.checkCapability(capability)
    else:
        if isChannelCapability(capability):
            (channel, capability) = fromChannelCapability(capability)
            try:
                chanop = makeChannelCapability(channel, 'op')
                if u.checkCapability(chanop):
                    return _x(capability, True)
            except KeyError:
                pass
            c = channels.getChannel(channel)
            if capability in c.capabilities:
                return c.checkCapability(capability)
            else:
                return _x(capability, c.defaultAllow)
        defaultCapabilities = conf.supybot.defaultCapabilities()
        if capability in defaultCapabilities:
            return True
        elif invertCapability(capability) in defaultCapabilities:
            return False
        else:
            return _x(capability, conf.supybot.defaultAllow())


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


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
