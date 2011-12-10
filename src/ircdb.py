###
# Copyright (c) 2002-2009, Jeremiah Fincher
# Copyright (c) 2009, James Vega
# Copyright (c) 2011, Valentin Lorentz
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

from __future__ import division

import os
import time
import operator

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.unpreserve as unpreserve
from utils.iter import imap, ilen, ifilter

def isCapability(capability):
    return len(capability.split(None, 1)) == 1

def fromChannelCapability(capability):
    """Returns a (channel, capability) tuple from a channel capability."""
    assert isChannelCapability(capability), 'got %s' % capability
    return capability.split(',', 1)

def isChannelCapability(capability):
    """Returns True if capability is a channel capability; False otherwise."""
    if ',' in capability:
        (channel, capability) = capability.split(',', 1)
        return ircutils.isChannel(channel) and isCapability(capability)
    else:
        return False

def makeChannelCapability(channel, capability):
    """Makes a channel capability given a channel and a capability."""
    assert isCapability(capability), 'got %s' % capability
    assert ircutils.isChannel(channel), 'got %s' % channel
    return '%s,%s' % (channel, capability)

def isAntiCapability(capability):
    """Returns True if capability is an anticapability; False otherwise."""
    if isChannelCapability(capability):
        (_, capability) = fromChannelCapability(capability)
    return isCapability(capability) and capability[0] == '-'

def makeAntiCapability(capability):
    """Returns the anticapability of a given capability."""
    assert isCapability(capability), 'got %s' % capability
    assert not isAntiCapability(capability), \
           'makeAntiCapability does not work on anticapabilities.  ' \
           'You probably want invertCapability; got %s.' % capability
    if isChannelCapability(capability):
        (channel, capability) = fromChannelCapability(capability)
        return makeChannelCapability(channel, '-' + capability)
    else:
        return '-' + capability

def unAntiCapability(capability):
    """Takes an anticapability and returns the non-anti form."""
    assert isCapability(capability), 'got %s' % capability
    if not isAntiCapability(capability):
        raise ValueError, '%s is not an anti capability' % capability
    if isChannelCapability(capability):
        (channel, capability) = fromChannelCapability(capability)
        return ','.join((channel, capability[1:]))
    else:
        return capability[1:]

def invertCapability(capability):
    """Make a capability into an anticapability and vice versa."""
    assert isCapability(capability), 'got %s' % capability
    if isAntiCapability(capability):
        return unAntiCapability(capability)
    else:
        return makeAntiCapability(capability)

def canonicalCapability(capability):
    if callable(capability):
        capability = capability()
    assert isCapability(capability), 'got %s' % capability
    return capability.lower()

def unWildcardHostmask(hostmask):
    return hostmask.translate(utils.str.chars, '!@*?')

_invert = invertCapability
class CapabilitySet(set):
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
            return False

    def __repr__(self):
        return '%s([%s])' % (self.__class__.__name__,
                             ', '.join(imap(repr, self)))

antiOwner = makeAntiCapability('owner')
class UserCapabilitySet(CapabilitySet):
    """A subclass of CapabilitySet to handle the owner capability correctly."""
    def __init__(self, *args, **kwargs):
        self.__parent = super(UserCapabilitySet, self)
        self.__parent.__init__(*args, **kwargs)

    def __contains__(self, capability, ignoreOwner=False):
        capability = ircutils.toLower(capability)
        if not ignoreOwner and capability == 'owner' or capability == antiOwner:
            return True
        elif not ignoreOwner and self.__parent.__contains__('owner'):
            return True
        else:
            return self.__parent.__contains__(capability)

    def check(self, capability, ignoreOwner=False):
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
        elif not ignoreOwner and self.__parent.__contains__('owner'):
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
        self.id = None
        self.auth = [] # The (time, hostmask) list of auth crap.
        self.name = name # The name of the user.
        self.ignore = ignore # A boolean deciding if the person is ignored.
        self.secure = secure # A boolean describing if hostmasks *must* match.
        self.hashed = hashed # True if the password is hashed on disk.
        self.password = password # password (plaintext? hashed?)
        self.capabilities = UserCapabilitySet()
        for capability in capabilities:
            self.capabilities.add(capability)
        if hostmasks is None:
            self.hostmasks = ircutils.IrcSet() # hostmasks used for recognition
        else:
            self.hostmasks = hostmasks

    def __repr__(self):
        return format('%s(id=%s, ignore=%s, password="", name=%q, hashed=%r, '
                      'capabilities=%r, hostmasks=[], secure=%r)\n',
                      self.__class__.__name__, self.id, self.ignore,
                      self.name, self.hashed, self.capabilities, self.secure)

    def __hash__(self):
        return hash(self.id)

    def addCapability(self, capability):
        """Gives the user the given capability."""
        self.capabilities.add(capability)

    def removeCapability(self, capability):
        """Takes from the user the given capability."""
        self.capabilities.remove(capability)

    def _checkCapability(self, capability, ignoreOwner=False):
        """Checks the user for a given capability."""
        if self.ignore:
            if isAntiCapability(capability):
                return True
            else:
                return False
        else:
            return self.capabilities.check(capability, ignoreOwner)

    def setPassword(self, password, hashed=False):
        """Sets the user's password."""
        if hashed or self.hashed:
            self.hashed = True
            self.password = utils.saltHash(password)
        else:
            self.password = password

    def checkPassword(self, password):
        """Checks the user's password."""
        if password is None:
            return False
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
        if useAuth:
            timeout = conf.supybot.databases.users.timeoutIdentification()
            removals = []
            try:
                for (when, authmask) in self.auth:
                    if timeout and when+timeout < time.time():
                        removals.append((when, authmask))
                    elif hostmask == authmask:
                        return True
            finally:
                while removals:
                    self.auth.remove(removals.pop())
        for pat in self.hostmasks:
            if ircutils.hostmaskPatternEqual(pat, hostmask):
                return pat
        return False

    def addHostmask(self, hostmask):
        """Adds a hostmask to the user's hostmasks."""
        assert ircutils.isUserHostmask(hostmask), 'got %s' % hostmask
        if len(unWildcardHostmask(hostmask)) < 8:
            raise ValueError, \
                  'Hostmask must contain at least 8 non-wildcard characters.'
        self.hostmasks.add(hostmask)

    def removeHostmask(self, hostmask):
        """Removes a hostmask from the user's hostmasks."""
        self.hostmasks.remove(hostmask)

    def addAuth(self, hostmask):
        """Sets a user's authenticated hostmask.  This times out in 1 hour."""
        if self.checkHostmask(hostmask, useAuth=False) or not self.secure:
            self.auth.append((time.time(), hostmask))
        else:
            raise ValueError, 'secure flag set, unmatched hostmask'

    def clearAuth(self):
        """Unsets a user's authenticated hostmask."""
        for (when, hostmask) in self.auth:
            users.invalidateCache(hostmask=hostmask)
        self.auth = []

    def preserve(self, fd, indent=''):
        def write(s):
            fd.write(indent)
            fd.write(s)
            fd.write(os.linesep)
        write('name %s' % self.name)
        write('ignore %s' % self.ignore)
        write('secure %s' % self.secure)
        write('hashed %s' % self.hashed)
        write('password %s' % self.password)
        for capability in self.capabilities:
            write('capability %s' % capability)
        for hostmask in self.hostmasks:
            write('hostmask %s' % hostmask)
        fd.write(os.linesep)


class IrcChannel(object):
    """This class holds the capabilities, bans, and ignores of a channel."""
    defaultOff = ('op', 'halfop', 'voice', 'protected')
    def __init__(self, bans=None, silences=None, exceptions=None, ignores=None,
                 capabilities=None, lobotomized=False, defaultAllow=True):
        self.defaultAllow = defaultAllow
        self.expiredBans = []
        self.bans = bans or {}
        self.ignores = ignores or {}
        self.silences = silences or []
        self.exceptions = exceptions or []
        self.capabilities = capabilities or CapabilitySet()
        for capability in self.defaultOff:
            if capability not in self.capabilities:
                self.capabilities.add(makeAntiCapability(capability))
        self.lobotomized = lobotomized

    def __repr__(self):
        return '%s(bans=%r, ignores=%r, capabilities=%r, ' \
               'lobotomized=%r, defaultAllow=%s, ' \
               'silences=%r, exceptions=%r)\n' % \
               (self.__class__.__name__, self.bans, self.ignores,
                self.capabilities, self.lobotomized,
                self.defaultAllow, self.silences, self.exceptions)

    def addBan(self, hostmask, expiration=0):
        """Adds a ban to the channel banlist."""
        assert ircutils.isUserHostmask(hostmask), 'got %s' % hostmask
        self.bans[hostmask] = int(expiration)

    def removeBan(self, hostmask):
        """Removes a ban from the channel banlist."""
        assert ircutils.isUserHostmask(hostmask), 'got %s' % hostmask
        return self.bans.pop(hostmask)

    def checkBan(self, hostmask):
        """Checks whether a given hostmask is banned by the channel banlist."""
        assert ircutils.isUserHostmask(hostmask), 'got %s' % hostmask
        now = time.time()
        for (pattern, expiration) in self.bans.items():
            if now < expiration or not expiration:
                if ircutils.hostmaskPatternEqual(pattern, hostmask):
                    return True
            else:
                self.expiredBans.append((pattern, expiration))
                del self.bans[pattern]
        return False

    def addIgnore(self, hostmask, expiration=0):
        """Adds an ignore to the channel ignore list."""
        assert ircutils.isUserHostmask(hostmask), 'got %s' % hostmask
        self.ignores[hostmask] = int(expiration)

    def removeIgnore(self, hostmask):
        """Removes an ignore from the channel ignore list."""
        assert ircutils.isUserHostmask(hostmask), 'got %s' % hostmask
        return self.ignores.pop(hostmask)

    def addCapability(self, capability):
        """Adds a capability to the channel's default capabilities."""
        assert isCapability(capability), 'got %s' % capability
        self.capabilities.add(capability)

    def removeCapability(self, capability):
        """Removes a capability from the channel's default capabilities."""
        assert isCapability(capability), 'got %s' % capability
        self.capabilities.remove(capability)

    def setDefaultCapability(self, b):
        """Sets the default capability in the channel."""
        self.defaultAllow = b

    def _checkCapability(self, capability):
        """Checks whether a certain capability is allowed by the channel."""
        assert isCapability(capability), 'got %s' % capability
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
        if world.testing:
            return False
        assert ircutils.isUserHostmask(hostmask), 'got %s' % hostmask
        if self.checkBan(hostmask):
            return True
        now = time.time()
        for (pattern, expiration) in self.ignores.items():
            if now < expiration or not expiration:
                if ircutils.hostmaskPatternEqual(pattern, hostmask):
                    return True
            else:
                del self.ignores[pattern]
                # Later we may wish to keep expiredIgnores, but not now.
        return False

    def preserve(self, fd, indent=''):
        def write(s):
            fd.write(indent)
            fd.write(s)
            fd.write(os.linesep)
        write('lobotomized %s' % self.lobotomized)
        write('defaultAllow %s' % self.defaultAllow)
        for capability in self.capabilities:
            write('capability ' + capability)
        bans = self.bans.items()
        utils.sortBy(operator.itemgetter(1), bans)
        for (ban, expiration) in bans:
            write('ban %s %d' % (ban, expiration))
        ignores = self.ignores.items()
        utils.sortBy(operator.itemgetter(1), ignores)
        for (ignore, expiration) in ignores:
            write('ignore %s %d' % (ignore, expiration))
        fd.write(os.linesep)


class Creator(object):
    def badCommand(self, command, rest, lineno):
        raise ValueError, 'Invalid command on line %s: %s' % (lineno, command)

class IrcUserCreator(Creator):
    u = None
    def __init__(self, users):
        if self.u is None:
            IrcUserCreator.u = IrcUser()
        self.users = users

    def user(self, rest, lineno):
        if self.u.id is not None:
            raise ValueError, 'Unexpected user command on line %s.' % lineno
        self.u.id = int(rest)

    def _checkId(self):
        if self.u.id is None:
            raise ValueError, 'Unexpected user description without user.'

    def name(self, rest, lineno):
        self._checkId()
        self.u.name = rest

    def ignore(self, rest, lineno):
        self._checkId()
        self.u.ignore = bool(eval(rest))

    def secure(self, rest, lineno):
        self._checkId()
        self.u.secure = bool(eval(rest))

    def hashed(self, rest, lineno):
        self._checkId()
        self.u.hashed = bool(eval(rest))

    def password(self, rest, lineno):
        self._checkId()
        self.u.password = rest

    def hostmask(self, rest, lineno):
        self._checkId()
        self.u.hostmasks.add(rest)

    def capability(self, rest, lineno):
        self._checkId()
        self.u.capabilities.add(rest)

    def finish(self):
        if self.u.name:
            try:
                self.users.setUser(self.u)
            except DuplicateHostmask:
                log.error('Hostmasks for %s collided with another user\'s.  '
                          'Resetting hostmasks for %s.', self.u.name)
                # Some might argue that this is arbitrary, and perhaps it is.
                # But we've got to do *something*, so we'll show some deference
                # to our lower-numbered users.
                self.u.hostmasks.clear()
                self.users.setUser(self.u)
            IrcUserCreator.u = None

class IrcChannelCreator(Creator):
    name = None
    def __init__(self, channels):
        self.c = IrcChannel()
        self.channels = channels
        self.hadChannel = bool(self.name)

    def channel(self, rest, lineno):
        if self.name is not None:
            raise ValueError, 'Unexpected channel command on line %s' % lineno
        IrcChannelCreator.name = rest

    def _checkId(self):
        if self.name is None:
            raise ValueError, 'Unexpected channel description without channel.'

    def lobotomized(self, rest, lineno):
        self._checkId()
        self.c.lobotomized = bool(eval(rest))

    def defaultallow(self, rest, lineno):
        self._checkId()
        self.c.defaultAllow = bool(eval(rest))

    def capability(self, rest, lineno):
        self._checkId()
        self.c.capabilities.add(rest)

    def ban(self, rest, lineno):
        self._checkId()
        (pattern, expiration) = rest.split()
        self.c.bans[pattern] = int(float(expiration))

    def ignore(self, rest, lineno):
        self._checkId()
        (pattern, expiration) = rest.split()
        self.c.ignores[pattern] = int(float(expiration))

    def finish(self):
        if self.hadChannel:
            self.channels.setChannel(self.name, self.c)
            IrcChannelCreator.name = None


class DuplicateHostmask(ValueError):
    pass

class UsersDictionary(utils.IterableMap):
    """A simple serialized-to-file User Database."""
    def __init__(self):
        self.noFlush = False
        self.filename = None
        self.users = {}
        self.nextId = 0
        self._nameCache = utils.structures.CacheDict(1000)
        self._hostmaskCache = utils.structures.CacheDict(1000)

    # This is separate because the Creator has to access our instance.
    def open(self, filename):
        self.filename = filename
        reader = unpreserve.Reader(IrcUserCreator, self)
        try:
            self.noFlush = True
            try:
                reader.readFile(filename)
                self.noFlush = False
                self.flush()
            except EnvironmentError, e:
                log.error('Invalid user dictionary file, resetting to empty.')
                log.error('Exact error: %s', utils.exnToString(e))
            except Exception, e:
                log.exception('Exact error:')
        finally:
            self.noFlush = False

    def reload(self):
        """Reloads the database from its file."""
        self.nextId = 0
        self.users.clear()
        self._nameCache.clear()
        self._hostmaskCache.clear()
        if self.filename is not None:
            try:
                self.open(self.filename)
            except EnvironmentError, e:
                log.warning('UsersDictionary.reload failed: %s', e)
        else:
            log.error('UsersDictionary.reload called with no filename.')

    def flush(self):
        """Flushes the database to its file."""
        if not self.noFlush:
            if self.filename is not None:
                L = self.users.items()
                L.sort()
                fd = utils.file.AtomicFile(self.filename)
                for (id, u) in L:
                    fd.write('user %s' % id)
                    fd.write(os.linesep)
                    u.preserve(fd, indent='  ')
                fd.close()
            else:
                log.error('UsersDictionary.flush called with no filename.')
        else:
            log.debug('Not flushing UsersDictionary because of noFlush.')

    def close(self):
        self.flush()
        if self.flush in world.flushers:
            world.flushers.remove(self.flush)
        self.users.clear()

    def iteritems(self):
        return self.users.iteritems()

    def getUserId(self, s):
        """Returns the user ID of a given name or hostmask."""
        if ircutils.isUserHostmask(s):
            try:
                return self._hostmaskCache[s]
            except KeyError:
                ids = {}
                for (id, user) in self.users.iteritems():
                    x = user.checkHostmask(s)
                    if x:
                        ids[id] = x
                if len(ids) == 1:
                    id = ids.keys()[0]
                    self._hostmaskCache[s] = id
                    try:
                        self._hostmaskCache[id].add(s)
                    except KeyError:
                        self._hostmaskCache[id] = set([s])
                    return id
                elif len(ids) == 0:
                    raise KeyError, s
                else:
                    log.error('Multiple matches found in user database.  '
                              'Removing the offending hostmasks.')
                    for (id, hostmask) in ids.iteritems():
                        log.error('Removing %q from user %s.', hostmask, id)
                        self.users[id].removeHostmask(hostmask)
                    raise DuplicateHostmask, 'Ids %r matched.' % ids
        else: # Not a hostmask, must be a name.
            s = s.lower()
            try:
                return self._nameCache[s]
            except KeyError:
                for (id, user) in self.users.items():
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
        u = self.users[id]
        while isinstance(u, int):
            id = u
            u = self.users[id]
        u.id = id
        return u

    def hasUser(self, id):
        """Returns the database has a user given its id, name, or hostmask."""
        try:
            self.getUser(id)
            return True
        except KeyError:
            return False

    def numUsers(self):
        return len(self.users)

    def invalidateCache(self, id=None, hostmask=None, name=None):
        if hostmask is not None:
            if hostmask in self._hostmaskCache:
                id = self._hostmaskCache.pop(hostmask)
                self._hostmaskCache[id].remove(hostmask)
                if not self._hostmaskCache[id]:
                    del self._hostmaskCache[id]
        if name is not None:
            del self._nameCache[self._nameCache[id]]
            del self._nameCache[id]
        if id is not None:
            if id in self._nameCache:
                del self._nameCache[self._nameCache[id]]
                del self._nameCache[id]
            if id in self._hostmaskCache:
                for hostmask in self._hostmaskCache[id]:
                    del self._hostmaskCache[hostmask]
                del self._hostmaskCache[id]

    def setUser(self, user, flush=True):
        """Sets a user (given its id) to the IrcUser given it."""
        self.nextId = max(self.nextId, user.id)
        try:
            if self.getUserId(user.name) != user.id:
                raise DuplicateHostmask, hostmask
        except KeyError:
            pass
        for hostmask in user.hostmasks:
            for (i, u) in self.iteritems():
                if i == user.id:
                    continue
                elif u.checkHostmask(hostmask):
                    # We used to remove the hostmask here, but it's not
                    # appropriate for us both to remove the hostmask and to
                    # raise an exception.  So instead, we'll raise an
                    # exception, but be nice and give the offending hostmask
                    # back at the same time.
                    raise DuplicateHostmask, hostmask
                for otherHostmask in u.hostmasks:
                    if ircutils.hostmaskPatternEqual(hostmask, otherHostmask):
                        raise DuplicateHostmask, hostmask
        self.invalidateCache(user.id)
        self.users[user.id] = user
        if flush:
            self.flush()

    def delUser(self, id):
        """Removes a user from the database."""
        del self.users[id]
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
        user = IrcUser(hashed=True)
        self.nextId += 1
        id = self.nextId
        self.users[id] = user
        self.flush()
        user.id = id
        return user


class ChannelsDictionary(utils.IterableMap):
    def __init__(self):
        self.noFlush = False
        self.filename = None
        self.channels = ircutils.IrcDict()

    def open(self, filename):
        self.noFlush = True
        try:
            self.filename = filename
            reader = unpreserve.Reader(IrcChannelCreator, self)
            try:
                reader.readFile(filename)
                self.noFlush = False
                self.flush()
            except EnvironmentError, e:
                log.error('Invalid channel database, resetting to empty.')
                log.error('Exact error: %s', utils.exnToString(e))
            except Exception, e:
                log.error('Invalid channel database, resetting to empty.')
                log.exception('Exact error:')
        finally:
            self.noFlush = False

    def flush(self):
        """Flushes the channel database to its file."""
        if not self.noFlush:
            if self.filename is not None:
                fd = utils.file.AtomicFile(self.filename)
                for (channel, c) in self.channels.iteritems():
                    fd.write('channel %s' % channel)
                    fd.write(os.linesep)
                    c.preserve(fd, indent='  ')
                fd.close()
            else:
                log.warning('ChannelsDictionary.flush without self.filename.')
        else:
            log.debug('Not flushing ChannelsDictionary because of noFlush.')

    def close(self):
        self.flush()
        if self.flush in world.flushers:
            world.flushers.remove(self.flush)
        self.channels.clear()

    def reload(self):
        """Reloads the channel database from its file."""
        if self.filename is not None:
            self.channels.clear()
            try:
                self.open(self.filename)
            except EnvironmentError, e:
                log.warning('ChannelsDictionary.reload failed: %s', e)
        else:
            log.warning('ChannelsDictionary.reload without self.filename.')

    def getChannel(self, channel):
        """Returns an IrcChannel object for the given channel."""
        channel = channel.lower()
        if channel in self.channels:
            return self.channels[channel]
        else:
            c = IrcChannel()
            self.channels[channel] = c
            return c

    def setChannel(self, channel, ircChannel):
        """Sets a given channel to the IrcChannel object given."""
        channel = channel.lower()
        self.channels[channel] = ircChannel
        self.flush()

    def iteritems(self):
        return self.channels.iteritems()


class IgnoresDB(object):
    def __init__(self):
        self.filename = None
        self.hostmasks = {}

    def open(self, filename):
        self.filename = filename
        fd = file(self.filename)
        for line in utils.file.nonCommentNonEmptyLines(fd):
            try:
                line = line.rstrip('\r\n')
                L = line.split()
                hostmask = L.pop(0)
                if L:
                    expiration = int(float(L.pop(0)))
                else:
                    expiration = 0
                self.add(hostmask, expiration)
            except Exception, e:
                log.error('Invalid line in ignores database: %q', line)
        fd.close()

    def flush(self):
        if self.filename is not None:
            fd = utils.file.AtomicFile(self.filename)
            now = time.time()
            for (hostmask, expiration) in self.hostmasks.items():
                if now < expiration or not expiration:
                    fd.write('%s %s' % (hostmask, expiration))
                    fd.write(os.linesep)
            fd.close()
        else:
            log.warning('IgnoresDB.flush called without self.filename.')

    def close(self):
        if self.flush in world.flushers:
            world.flushers.remove(self.flush)
        self.flush()
        self.hostmasks.clear()

    def reload(self):
        if self.filename is not None:
            oldhostmasks = self.hostmasks.copy()
            self.hostmasks.clear()
            try:
                self.open(self.filename)
            except EnvironmentError, e:
                log.warning('IgnoresDB.reload failed: %s', e)
                # Let's be somewhat transactional.
                self.hostmasks.update(oldhostmasks)
        else:
            log.warning('IgnoresDB.reload called without self.filename.')

    def checkIgnored(self, prefix):
        now = time.time()
        for (hostmask, expiration) in self.hostmasks.items():
            if expiration and now > expiration:
                del self.hostmasks[hostmask]
            else:
                if ircutils.hostmaskPatternEqual(hostmask, prefix):
                    return True
        return False

    def add(self, hostmask, expiration=0):
        assert ircutils.isUserHostmask(hostmask), 'got %s' % hostmask
        self.hostmasks[hostmask] = expiration

    def remove(self, hostmask):
        del self.hostmasks[hostmask]


confDir = conf.supybot.directories.conf()
try:
    userFile = os.path.join(confDir, conf.supybot.databases.users.filename())
    users = UsersDictionary()
    users.open(userFile)
except EnvironmentError, e:
    log.warning('Couldn\'t open user database: %s', e)

try:
    channelFile = os.path.join(confDir,
                               conf.supybot.databases.channels.filename())
    channels = ChannelsDictionary()
    channels.open(channelFile)
except EnvironmentError, e:
    log.warning('Couldn\'t open channel database: %s', e)

try:
    ignoreFile = os.path.join(confDir,
                              conf.supybot.databases.ignores.filename())
    ignores = IgnoresDB()
    ignores.open(ignoreFile)
except EnvironmentError, e:
    log.warning('Couldn\'t open ignore database: %s', e)


world.flushers.append(users.flush)
world.flushers.append(ignores.flush)
world.flushers.append(channels.flush)


###
# Useful functions for checking credentials.
###
def checkIgnored(hostmask, recipient='', users=users, channels=channels):
    """checkIgnored(hostmask, recipient='') -> True/False

    Checks if the user is ignored by the recipient of the message.
    """
    if ignores.checkIgnored(hostmask):
        log.debug('Ignoring %s due to ignore database.', hostmask)
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
    if user._checkCapability('owner'):
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
                return c._checkCapability(capability)
            else:
                return _x(capability, c.defaultAllow)
        except KeyError:
            pass
    defaultCapabilities = conf.supybot.capabilities()
    if capability in defaultCapabilities:
        return defaultCapabilities.check(capability)
    else:
        return _x(capability, conf.supybot.capabilities.default())

def checkCapability(hostmask, capability, users=users, channels=channels,
                    ignoreOwner=False):
    """Checks that the user specified by name/hostmask has the capability given.
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
        return u._checkCapability(capability, ignoreOwner)
    else:
        if isChannelCapability(capability):
            (channel, capability) = fromChannelCapability(capability)
            try:
                chanop = makeChannelCapability(channel, 'op')
                if u._checkCapability(chanop):
                    return _x(capability, True)
            except KeyError:
                pass
            c = channels.getChannel(channel)
            if capability in c.capabilities:
                return c._checkCapability(capability)
            else:
                return _x(capability, c.defaultAllow)
        defaultCapabilities = conf.supybot.capabilities()
        if capability in defaultCapabilities:
            return defaultCapabilities.check(capability)
        else:
            return _x(capability, conf.supybot.capabilities.default())


def checkCapabilities(hostmask, capabilities, requireAll=False):
    """Checks that a user has capabilities in a list.

    requireAll is True if *all* capabilities in the list must be had, False if
    *any* of the capabilities in the list must be had.
    """
    for capability in capabilities:
        if requireAll:
            if not checkCapability(hostmask, capability):
                return False
        else:
            if checkCapability(hostmask, capability):
                return True
    return requireAll

###
# supybot.capabilities
###

class DefaultCapabilities(registry.SpaceSeparatedListOfStrings):
    List = CapabilitySet
    # We use a keyword argument trick here to prevent eval'ing of code that
    # changes allowDefaultOwner from affecting this.  It's not perfect, but
    # it's still an improvement, raising the bar for potential crackers.
    def setValue(self, v, allowDefaultOwner=conf.allowDefaultOwner):
        registry.SpaceSeparatedListOfStrings.setValue(self, v)
        if '-owner' not in self.value and not allowDefaultOwner:
            print '*** You must run supybot with the --allow-default-owner'
            print '*** option in order to allow a default capability of owner.'
            print '*** Don\'t do that, it\'s dumb.'
            self.value.add('-owner')

conf.registerGlobalValue(conf.supybot, 'capabilities',
    DefaultCapabilities(['-owner', '-admin', '-trusted'], """These are the
    capabilities that are given to everyone by default.  If they are normal
    capabilities, then the user will have to have the appropriate
    anti-capability if you want to override these capabilities; if they are
    anti-capabilities, then the user will have to have the actual capability
    to override these capabilities.  See docs/CAPABILITIES if you don't
    understand why these default to what they do."""))

conf.registerGlobalValue(conf.supybot.capabilities, 'default',
    registry.Boolean(True, """Determines whether the bot by default will allow
    users to have a capability.  If this is disabled, a user must explicitly
    have the capability for whatever command he wishes to run."""))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
