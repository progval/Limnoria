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
import sys
import imp

import conf
import debug
import world
import ircdb
import ircmsgs
import drivers
import ircutils
import callbacks

def getChannel(msg, args):
    """Returns the channel the msg came over or the channel given in args.

    If the channel was given in args, args is modified (the channel is
    removed).
    """
    if args and ircutils.isChannel(args[0]):
        return args.pop(0)
    elif ircutils.isChannel(msg.args[0]):
        return msg.args[0]
    else:
        raise callbacks.Error, 'Command must be sent in a channel or ' \
                               'include a channel in its arguments.'

def getArgs(args, needed=1, optional=0):
    """Take the needed arguments from args.

    Always returns a list of size needed + optional, filling it with however
    many empty strings is necessary to fill the tuple to the right size.

    If there aren't enough args even to satisfy needed, raise an error and
    let the caller handle sending the help message.
    """
    if len(args) < needed:
        raise callbacks.ArgumentError
    if len(args) < needed + optional:
        ret = list(args) + ([''] * (needed + optional - len(args)))
    elif len(args) >= needed + optional:
        ret = list(args[:needed + optional - 1])
        ret.append(' '.join(args[needed + optional - 1:]))
    if len(ret) == 1:
        return ret[0]
    else:
        return ret

def getKeywordArgs(irc, msg, d=None):
    if d is None:
        d = {}
    args = []
    tokenizer = callbacks.Tokenizer('=')
    s = callbacks.addressed(irc.nick, msg)
    tokens = tokenizer.tokenize(s) + [None, None]
    counter = 0
    for (left, middle, right) in window(tokens, 3):
        if counter:
            counter -= 1
            continue
        elif middle == '=':
            d[callbacks.canonicalName(left)] = right
            counter = 2
        else:
            args.append(left)
    del args[0] # The command name itself.
    return (args, d)
            
def checkCapability(f, capability):
    def newf(self, irc, msg, args):
        if ircdb.checkCapability(msg.prefix, capability):
            f(self, irc, msg, args)
        else:
            irc.error(msg, conf.replyNoCapability % capability)
    newf.__doc__ = f.__doc__
    return newf

class CapabilityCheckingPrivmsg(callbacks.Privmsg):
    capability = '' # To satisfy PyChecker
    def callCommand(self, f, irc, msg, args):
        if ircdb.checkCapability(msg.prefix, self.capability):
            callbacks.Privmsg.callCommand(self, f, irc, msg, args)
        else:
            irc.error(msg, conf.replyNoCapability % self.capability)


class OwnerCommands(CapabilityCheckingPrivmsg):
    capability = 'owner'
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        setattr(self.__class__, 'exec', self._exec)

    def eval(self, irc, msg, args):
        """<string to be evaluated by the Python interpreter>"""
        if conf.allowEval:
            s = getArgs(args)
            try:
                irc.reply(msg, repr(eval(s)))
            except Exception, e:
                irc.reply(msg, debug.exnToString(e))
        else:
            irc.error(msg, conf.replyEvalNotAllowed)

    def _exec(self, irc, msg, args):
        """<code to exec>"""
        if conf.allowEval:
            s = getArgs(args)
            try:
                exec s
                irc.reply(msg, conf.replySuccess)
            except Exception, e:
                irc.reply(msg, debug.exnToString(e))
        else:
            irc.error(msg, conf.replyEvalNotAllowed)

    def setdefaultcapability(self, irc, msg, args):
        """<capability>

        Sets the default capability to be allowed for any command.
        """
        capability = getArgs(args)
        conf.defaultCapabilities[capability] = True
        irc.reply(msg, conf.replySuccess)

    def unsetdefaultcapability(self, irc, msg, args):
        """<capability>

        Unsets the default capability for any command.
        """
        capability = getArgs(args)
        del conf.defaultCapabilities[capability]
        irc.reply(msg, conf.replySuccess)

    def settrace(self, irc, msg, args):
        """takes no arguments

        Starts the function-tracing debug mode; beware that this makes *huge*
        logfiles.
        """
        sys.settrace(debug.tracer)
        irc.reply(msg, conf.replySuccess)

    def unsettrace(self, irc, msg, args):
        """takes no arguments

        Stops the function-tracing debug mode."""
        sys.settrace(None)
        irc.reply(msg, conf.replySuccess)

    def ircquote(self, irc, msg, args):
        """<string to be sent to the server>

        Sends the raw string given to the server.
        """
        s = getArgs(args)
        try:
            m = ircmsgs.IrcMsg(s)
            irc.queueMsg(m)
        except Exception:
            debug.recoverableException()
            irc.error(msg, conf.replyError)

    def quit(self, irc, msg, args):
        """[<int return value>]

        Exits the program with the given return value (the default is 0)
        """
        try:
            i = int(args[0])
        except (ValueError, IndexError):
            i = 0
        for driver in drivers._drivers.itervalues():
            driver.die()
        for irc in world.ircs:
            irc.die()
        debug.exit(i)

    def flush(self, irc, msg, args):
        """takes no arguments

        Runs all the periodic flushers in world.flushers.
        """
        world.flush()
        irc.reply(msg, conf.replySuccess)
            
    def set(self, irc, msg, args):
        """<name> <value>

        Sets the runtime variable <name> to <value>.  Currently used variables
        include "noflush" which, if set to true value, will prevent the
        periodic flushing that normally occurs.
        """
        (name, value) = getArgs(args, optional=1)
        world.tempvars[name] = value
        irc.reply(msg, conf.replySuccess)

    def unset(self, irc, msg, args):
        """<name>

        Unsets the value of variables set via the 'set' command.
        """
        name = getArgs(args)
        try:
            del world.tempvars[name]
            irc.reply(msg, conf.replySuccess)
        except KeyError:
            irc.error(msg, 'That variable wasn\'t set.')

    def load(self, irc, msg, args):
        """<plugin>

        Loads the plugin <plugin> from the plugins/ directory.
        """
        name = getArgs(args)
        if name in [cb.name() for cb in irc.callbacks]:
            irc.error(msg, 'That module is already loaded.')
            return
        try:
            moduleInfo = imp.find_module(name)
        except ImportError:
            irc.error(msg, 'No plugin %s exists.' % name)
            return
        module = imp.load_module(name, *moduleInfo)
        callback = module.Class()
        irc.addCallback(callback)
        irc.reply(msg, conf.replySuccess)

    def superreload(self, irc, msg, args):
        """<module name>

        Reloads a module, hopefully such that all vestiges of the old module
        are gone.
        """
        name = getArgs(args)
        world.superReload(__import__(name))
        irc.reply(msg, conf.replySuccess)
        
    def reload(self, irc, msg, args):
        """<callback name>

        Unloads and subsequently reloads the callback by name; use the 'list'
        command to see a list of the currently loaded callbacks.
        """
        name = getArgs(args)
        callbacks = irc.removeCallback(name)
        if callbacks:
            for callback in callbacks:
                callback.die()
            try:
                moduleInfo = imp.find_module(name)
            except ImportError:
                irc.error(msg, 'No plugin %s exists.' % name)
                return
            module = imp.load_module(name, *moduleInfo)
            callback = module.Class()
            irc.addCallback(callback)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'There was no callback %s.' % name)
        
    def unload(self, irc, msg, args):
        """<callback name>

        Unloads the callback by name; use the 'list' command to see a list
        of the currently loaded callbacks.
        """
        name = getArgs(args)
        callbacks = irc.removeCallback(name)
        if callbacks:
            for callback in callbacks:
                callback.die()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'There was no callback %s' % name)

    def cvsup(self, irc, msg, args):
        """takes no arguments"""
        irc.reply(msg, str(os.system('cvs up')))

    def say(self, irc, msg, args):
        """<channel> <text>"""
        (channel, text) = getArgs(args, needed=2)
        irc.queueMsg(ircmsgs.privmsg(channel, text))


standardPrivmsgModules = [OwnerCommands]

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
