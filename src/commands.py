#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

"""
Includes wrappers for commands.
"""

__revision__ = "$Id$"

import supybot.fix as fix

import getopt

import time
import types
import threading

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.structures as structures


###
# Non-arg wrappers -- these just change the behavior of a command without
# changing the arguments given to it.
###
def thread(f):
    """Makes sure a command spawns a thread when called."""
    def newf(self, irc, msg, args, *L, **kwargs):
        if threading.currentThread() is world.mainThread:
            t = callbacks.CommandThread(target=irc._callCommand,
                                        args=(f.func_name, self),
                                        kwargs=kwargs)
            t.start()
        else:
            f(self, irc, msg, args, *L, **kwargs)
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

def private(f):
    """Makes sure a command is given in private."""
    def newf(self, irc, msg, args, *L, **kwargs):
        if ircutils.isChannel(msg.args[0]):
            irc.errorRequiresPrivacy()
        else:
            f(self, irc, msg, args, *L, **kwargs)
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

def checkCapability(f, capability):
    """Makes sure a user has a certain capability before a command will run.
    capability can be either a string or a callable object which will be called
    in order to produce a string for ircdb.checkCapability."""
    def newf(self, irc, msg, args):
        cap = capability
        if callable(cap):
            cap = cap()
        if ircdb.checkCapability(msg.prefix, cap):
            f(self, irc, msg, args)
        else:
            self.log.info('%s attempted %s without %s.',
                          msg.prefix, f.func_name, cap)
            irc.errorNoCapability(cap)
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

class UrlSnarfThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        assert 'url' in kwargs
        kwargs['name'] = 'Thread #%s (for snarfing %s)' % \
                         (world.threadsSpawned, kwargs.pop('url'))
        world.threadsSpawned += 1
        threading.Thread.__init__(self, *args, **kwargs)
        self.setDaemon(True)

class SnarfQueue(ircutils.FloodQueue):
    timeout = conf.supybot.snarfThrottle
    def key(self, channel):
        return channel

_snarfed = SnarfQueue()

class SnarfIrc(object):
    def __init__(self, irc, channel, url):
        self.irc = irc
        self.url = url
        self.channel = channel

    def __getattr__(self, attr):
        return getattr(self.irc, attr)

    def reply(self, *args, **kwargs):
        _snarfed.enqueue(self.channel, self.url)
        self.irc.reply(*args, **kwargs)

# This lock is used to serialize the calls to snarfers, so
# earlier snarfers are guaranteed to beat out later snarfers.
_snarfLock = threading.Lock()
def urlSnarfer(f):
    """Protects the snarfer from loops (with other bots) and whatnot."""
    def newf(self, irc, msg, match, *L, **kwargs):
        url = match.group(0)
        channel = msg.args[0]
        if not ircutils.isChannel(channel):
            return
        if ircdb.channels.getChannel(channel).lobotomized:
            self.log.info('Not snarfing in %s: lobotomized.', channel)
            return
        if _snarfed.has(channel, url):
            self.log.info('Throttling snarf of %s in %s.', url, channel)
            return
        irc = SnarfIrc(irc, channel, url)
        def doSnarf():
            _snarfLock.acquire()
            try:
                if msg.repliedTo:
                    self.log.debug('Not snarfing, msg is already repliedTo.')
                    return
                f(self, irc, msg, match, *L, **kwargs)
            finally:
                _snarfLock.release()
        if threading.currentThread() is not world.mainThread:
            doSnarf()
        else:
            L = list(L)
            t = UrlSnarfThread(target=doSnarf, url=url)
            t.start()
    newf = utils.changeFunctionName(newf, f.func_name, f.__doc__)
    return newf

wrappers = ircutils.IrcDict({
    'thread': thread,
    'private': private,
    'urlSnarfer': urlSnarfer,
    'checkCapability': checkCapability,
})


###
# Arg wrappers, wrappers that add arguments to the command.
###
def getInt(irc, msg, args, default=None, type='integer'):
    s = args.pop(0)
    try:
        return int(s)
    except ValueError:
        if default is not None:
            return default
        else:
            irc.errorInvalid(type, s, Raise=True)

def getId(irc, msg, args):
    getInt(irc, msg, args, type='id')

def getExpiry(irc, msg, args, default=None):
    s = args.pop(0)
    try:
        expires = int(float(s))
        expires += int(time.time())
    except ValueError:
        if default is not None:
            return default
        else:
            irc.errorInvalid('number of seconds', s, Raise=True)

def getBoolean(irc, msg, args, default=None):
    s = args.pop(0).strip().lower()
    if s in ('true', 'on', 'enable', 'enabled'):
        return True
    elif s in ('false', 'off', 'disable', 'disabled'):
        return False
    elif default is not None:
        return default
    else:
        irc.error("Value must be either True or False (or On or Off).",
                  Raise=True)

def getChannelDb(irc, msg, args, **kwargs):
    if not conf.supybot.databases.plugins.channelSpecific():
        return None
    else:
        return channel(irc, msg, args, **kwargs)

def validChannel(irc, msg, args):
    s = args.pop(0)
    if ircutils.isChannel(s):
        return s
    else:
        irc.errorInvalid('channel', s, Raise=True)

def getHostmask(irc, msg, args):
    if ircutils.isUserHostmask(args[0]):
        return args.pop(0)
    else:
        try:
            s = args.pop(0)
            return irc.state.nickToHostmask(s)
        except KeyError:
            irc.errorInvalid('nick or hostmask', s, Raise=True)

def getBanmask(irc, msg, args):
    if ircutils.isUserHostmask(args[0]):
        return args.pop(0)
    else:
        try:
            s = args.pop(0)
            return ircutils.banmask(irc.state.nickToHostmask(s))
        except KeyError:
            irc.errorInvalid('nick or hostmask', s, Raise=True)

def getUser(irc, msg, args):
    try:
        return ircdb.users.getUser(msg.prefix)
    except KeyError:
        irc.errorNotRegistered(Raise=True)

def getOtherUser(irc, msg, args):
    s = args.pop(0)
    try:
        return ircdb.users.getUser(s)
    except KeyError:
        try:
            hostmask = getHostmask(irc, msg, [s])
            return ircdb.users.getUser(hostmask)
        except (KeyError, IndexError, callbacks.Error):
            irc.errorNoUser(Raise=True)

def _getRe(f):
    def get(irc, msg, args):
        s = args.pop(0)
        def isRe(s):
            try:
                _ = f(s)
                return True
            except ValueError:
                return False
        while not isRe(s):
            s += ' ' + args.pop(0)
        return f(s)
    return get

getMatcher = _getRe(utils.perlReToPythonRe)
getReplacer = _getRe(utils.perlReToReplacer)

def getNick(irc, msg, args):
    s = args.pop(0)
    if ircutils.isNick(s):
        if 'nicklen' in irc.state.supported:
            if len(s) > irc.state.supported['nicklen']:
                irc.errorInvalid('nick', s,
                                 'That nick is too long for this server.',
                                 Raise=True)
        return s
    else:
        irc.errorInvalid('nick', s, Raise=True)

def getChannel(irc, msg, args, cap=None):
    if ircutils.isChannel(args[0]):
        channel = args.pop(0)
    elif ircutils.isChannel(msg.args[0]):
        channel = msg.args[0]
    else:
        raise callbacks.ArgumentError
    if cap is not None:
        if callable(cap):
            cap = cap()
        cap = ircdb.makeChannelCapability(channel, cap)
        if not ircdb.checkCapability(msg.prefix, cap):
            irc.errorNoCapability(cap, Raise=True)
    return channel

def getLowered(irc, msg, args):
    return ircutils.toLower(args.pop(0))

def getSomething(irc, msg, args):
    s = args.pop(0)
    if not s:
        # XXX Better reply?  How?
        irc.error('You must not give the empty string as an argument.',
                  Raise=True)
    return s

def getPlugin(irc, msg, args, requirePresent=False):
    s = args.pop(0)
    cb = irc.getCallback(s)
    if requirePresent and cb is None:
        irc.errorInvalid('plugin', s, Raise=True)
    return cb

argWrappers = ircutils.IrcDict({
    'id': getId,
    'int': getInt,
    'expiry': getExpiry,
    'nick': getNick,
    'channel': getChannel,
    'plugin': getPlugin,
    'boolean': getBoolean,
    'lowered': getLowered,
    'something': getSomething,
    'channelDb': getChannelDb,
    'hostmask': getHostmask,
    'banmask': getBanmask,
    'user': getUser,
    'otherUser': getOtherUser,
    'regexpMatcher': getMatcher,
    'validChannel': validChannel,
    'regexpReplacer': getReplacer,
})

def args(irc,msg,args, required=[], optional=[], getopts=None, noExtra=False):
    starArgs = []
    req = required[:]
    opt = optional[:]
    if getopts is not None:
        getoptL = []
        for (key, value) in getopts.iteritems():
            if value != '': # value can be None, remember.
                key += '='
            getoptL.append(key)
    def getArgWrapper(x):
        if isinstance(x, tuple):
            assert x
            name = x[0]
            args = x[1:]
        else:
            assert isinstance(x, basestring) or x is None
            name = x
            args = ()
        if name is not None:
            return argWrappers[name], args
        else:
            return lambda irc, msg, args: args.pop(0), args
    def getConversion(name):
        (converter, convertArgs) = getArgWrapper(name)
        v = converter(irc, msg, args, *convertArgs)
        return v
    def callConverter(name):
        v = getConversion(name)
        starArgs.append(v)

    # First, we getopt stuff.
    if getopts is not None:
        L = []
        (optlist, args) = getopt.getopt(args, '', getoptL)
        for (opt, arg) in optlist:
            opt = opt[2:] # Strip --
            assert opt in getopts
            if arg is not None:
                assert getopts[opt] != ''
                L.append((opt, getConversion(getopts[opt])))
            else:
                assert getopts[opt] == ''
                L.append((opt, True))
        starArgs.append(L)

    # Second, we get out everything but the last argument.
    try:
        while len(req) + len(opt) > 1:
            if req:
                callConverter(req.pop(0))
            else:
                assert opt
                callConverter(opt.pop(0))
        # Third, if there is a remaining required or optional argument
        # (there's a possibility that there were no required or optional
        # arguments) then we join the remaining args and work convert that.
        if req or opt:
            rest = ' '.join(args)
            args = [rest]
            if required:
                converterName = req.pop(0)
            else:
                converterName = opt.pop(0)
            callConverter(converterName)
    except IndexError:
        if req:
            raise callbacks.ArgumentError
        while opt:
            del opt[-1]
            starArgs.append('')
    if noExtra and args:
        raise callbacks.ArgumentError
    return starArgs

# These are used below, but we need to rename them so their names aren't
# shadowed by our locals.
_args = args
_wrappers = wrappers
def wrap(f, required=[], optional=[],
         wrappers=None, getopts=None, noExtra=False):
    def newf(self, irc, msg, args, **kwargs):
        starArgs = _args(irc, msg, args,
                         getopts=getopts, noExtra=noExtra,
                         required=required, optional=optional)
        f(self, irc, msg, args, *starArgs, **kwargs)

    if wrappers is not None:
        wrappers = map(_wrappers.__getitem__, wrappers)
        for wrapper in wrappers:
            newf = wrapper(newf)
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
