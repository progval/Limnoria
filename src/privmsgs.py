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
Includes various accessories for callbacks.Privmsg based callbacks.
"""

__revision__ = "$Id$"

import supybot.fix as fix

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

def getChannel(msg, args=(), raiseError=True):
    """Returns the channel the msg came over or the channel given in args.

    If the channel was given in args, args is modified (the channel is
    removed).
    """
    if args and ircutils.isChannel(args[0]):
        if conf.supybot.reply.requireChannelCommandsToBeSentInChannel():
            if args[0] != msg.args[0]:
                s = 'Channel commands must be sent in the channel to which ' \
                    'they apply; if this is not the behavior you desire, ' \
                    'ask the bot\'s administrator to change the registry ' \
                    'variable ' \
                    'supybot.reply.requireChannelCommandsToBeSentInChannel ' \
                    'to False.'
                raise callbacks.Error, s
        return args.pop(0)
    elif ircutils.isChannel(msg.args[0]):
        return msg.args[0]
    else:
        if raiseError:
            raise callbacks.Error, 'Command must be sent in a channel or ' \
                                   'include a channel in its arguments.'
        else:
            return None

def getArgs(args, required=1, optional=0):
    """Take the required/optional arguments from args.

    Always returns a list of size required + optional, filling it with however
    many empty strings is necessary to fill the tuple to the right size.  If
    there is only one argument, a string containing that argument is returned.

    If there aren't enough args even to satisfy required, raise an error and
    let the caller handle sending the help message.
    """
    assert not isinstance(args, str), 'args should be a list.'
    assert not isinstance(args, ircmsgs.IrcMsg), 'args should be a list.'
    if len(args) < required:
        raise callbacks.ArgumentError
    if len(args) < required + optional:
        ret = list(args) + ([''] * (required + optional - len(args)))
    elif len(args) >= required + optional:
        ret = list(args[:required + optional - 1])
        ret.append(' '.join(args[required + optional - 1:]))
    if len(ret) == 1:
        return ret[0]
    else:
        return ret

def checkCapability(f, capability):
    """Makes sure a user has a certain capability before a command will run."""
    def newf(self, irc, msg, args):
        if ircdb.checkCapability(msg.prefix, capability):
            f(self, irc, msg, args)
        else:
            self.log.warning('%r attempted %s without %s.',
                             msg.prefix, f.func_name, capability)
            irc.errorNoCapability(capability)
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

def checkChannelCapability(f, capability):
    """Makes sure a user has a certain channel capability before running f.

    Do note that you need to add a "channel" argument to your argument list.
    """
    def newf(self, irc, msg, args, *L, **kwargs):
        channel = getChannel(msg, args)
        chancap = ircdb.makeChannelCapability(channel, capability)
        if ircdb.checkCapability(msg.prefix, chancap):
            L += (channel,)
            ff = types.MethodType(f, self, self.__class__)
            ff(irc, msg, args, *L, **kwargs)
        else:
            self.log.warning('%r attempted %s without %s.',
                             msg.prefix, f.func_name, capability)
            irc.errorNoCapability(chancap)
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

def thread(f):
    """Makes sure a command spawns a thread when called."""
    def newf(self, irc, msg, args, *L, **kwargs):
        if threading.currentThread() is not world.mainThread:
            t = callbacks.CommandThread(target=irc._callCommand,
                                        args=(f.func_name, self),
                                        kwargs=kwargs)
            t.start()
        else:
            f(self, irc, msg, args, *L, **kwargs)
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

def channel(f):
    """Gives the command an extra channel arg as if it had called getChannel"""
    def newf(self, irc, msg, args, *L, **kwargs):
        channel = getChannel(msg, args)
        L = (channel,) + L
        ff = types.MethodType(f, self, self.__class__)
        ff(irc, msg, args, *L, **kwargs)
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
    def key(self, channel):
        return channel

    def getTimeout(self):
        return conf.supybot.snarfThrottle()

_snarfed = SnarfQueue()

class SnarfIrc(object):
    def __init__(self, irc, channel, url):
        self.irc = irc
        self.url = url
        self.channel = channel

    def reply(self, *args, **kwargs):
        _snarfed.enqueue(self.channel, self.url)
        self.irc.reply(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self.irc, attr)

def urlSnarfer(f):
    """Protects the snarfer from loops and whatnot."""
    def newf(self, irc, msg, match, *L, **kwargs):
        channel = msg.args[0]
        if not ircutils.isChannel(channel):
            return
        c = ircdb.channels.getChannel(channel)
        if c.lobotomized:
            self.log.info('Refusing to snarf in %s: lobotomized.', channel)
            return
        url = match.group(0)
        if _snarfed.has(channel, url):
            self.log.info('Refusing to snarf %s, already snarfed.', url)
            return
        irc = SnarfIrc(irc, channel, url)
        if threading.currentThread() is not world.mainThread:
            f(self, irc, msg, match, *L, **kwargs)
        else:
            L = list(L)
            t = UrlSnarfThread(target=f,args=[self,irc,msg,match]+L,url=url)
            t.start()
    newf = utils.changeFunctionName(newf, f.func_name, f.__doc__)
    return newf

class CapabilityCheckingPrivmsg(callbacks.Privmsg):
    """A small subclass of callbacks.Privmsg that checks self.capability
    before allowing any command to be called.
    """
    capability = '' # To satisfy PyChecker
    def __init__(self, *args, **kwargs):
        self.__parent = super(CapabilityCheckingPrivmsg, self)
        self.__parent.__init__(*args, **kwargs)
        
    def callCommand(self, name, irc, msg, args, *L, **kwargs):
        if ircdb.checkCapability(msg.prefix, self.capability):
            self.__parent.callCommand(name, irc, msg, args, *L, **kwargs)
        else:
            self.log.warning('%s tried to call %s without %s.',
                             msg.prefix, name, self.capability)
            irc.errorNoCapability(self.capability)


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
