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

def getChannel(msg, args, raiseError=True):
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
    def newf(self, irc, msg, args, *L):
        channel = getChannel(msg, args)
        chancap = ircdb.makeChannelCapability(channel, capability)
        if ircdb.checkCapability(msg.prefix, chancap):
            L += (channel,)
            ff = types.MethodType(f, self, self.__class__)
            ff(irc, msg, args, *L)
        else:
            self.log.warning('%r attempted %s without %s.',
                             msg.prefix, f.func_name, capability)
            irc.errorNoCapability(chancap)
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

def _threadedWrapMethod(f):
    """A function to wrap methods that are to be run in a thread, so that the
    callback's threaded attribute is set to True while the thread is running.
    """
    def newf(self, *args, **kwargs):
        originalThreaded = self.threaded
        try:
            self.threaded = True
            return f(self, *args, **kwargs)
        finally:
            self.threaded = originalThreaded
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

def thread(f):
    """Makes sure a command spawns a thread when called."""
    f = _threadedWrapMethod(f)
    def newf(self, irc, msg, args, *L):
        ff = types.MethodType(f, self, self.__class__)
        t = callbacks.CommandThread(target=irc._callCommand,
                                    args=(f.func_name, ff, self))
        t.start()
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

def channel(f):
    """Gives the command an extra channel arg as if it had called getChannel"""
    def newf(self, irc, msg, args, *L):
        channel = getChannel(msg, args)
        L = (channel,) + L
        ff = types.MethodType(f, self, self.__class__)
        ff(irc, msg, args, *L)
    return utils.changeFunctionName(newf, f.func_name, f.__doc__)

_snarfed = structures.smallqueue()
def urlSnarfer(f):
    """Protects the snarfer from loops and whatnot."""
    f = _threadedWrapMethod(f)
    def newf(self, irc, msg, match, *L):
        channel = msg.args[0]
        if ircutils.isChannel(channel):
            c = ircdb.channels.getChannel(channel)
            if c.lobotomized:
                self.log.info('Refusing to snarf in %s: lobotomized.', channel)
                return
        now = time.time()
        cutoff = now - conf.supybot.snarfThrottle()
        while _snarfed and _snarfed[0][2] < cutoff:
            _snarfed.dequeue()
        url = match.group(0)
        for (qUrl, target, when) in _snarfed:
            if url == qUrl and target == channel and not world.testing:
                self.log.info('Not snarfing %s from %r: in queue.',
                              url, msg.prefix)
                return
        else:
            _snarfed.enqueue((url, channel, now))
            if self.threaded:
                f(self, irc, msg, match, *L)
            else:
                L = list(L)
                world.threadsSpawned += 1
                t = threading.Thread(target=f, args=[self,irc,msg,match]+L)
                t.setDaemon(True)
                t.start()
    newf = utils.changeFunctionName(newf, f.func_name, f.__doc__)
    return newf


class CapabilityCheckingPrivmsg(callbacks.Privmsg):
    """A small subclass of callbacks.Privmsg that checks self.capability
    before allowing any command to be called.
    """
    capability = '' # To satisfy PyChecker
    def callCommand(self, f, irc, msg, args):
        if ircdb.checkCapability(msg.prefix, self.capability):
            callbacks.Privmsg.callCommand(self, f, irc, msg, args)
        else:
            self.log.warning('%r tried to call %s without %s.',
                             msg.prefix, f.im_func.func_name, self.capability)
            irc.errorNoCapability(self.capability)


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
