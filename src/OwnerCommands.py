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
Provides commands useful to the owner of the bot; the commands here require
their caller to have the 'owner' capability.  This plugin is loaded by default.
"""

import os
import gc
import imp
import sys
import linecache

import conf
import debug
import utils
import world
import ircmsgs
import drivers
import privmsgs
import callbacks

class OwnerCommands(privmsgs.CapabilityCheckingPrivmsg):
    capability = 'owner'
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        setattr(self.__class__, 'exec', self.__class__._exec)

    def eval(self, irc, msg, args):
        """<expression>

        Evaluates <expression> and returns its value.
        """
        if conf.allowEval:
            s = privmsgs.getArgs(args)
            try:
                irc.reply(msg, repr(eval(s)))
            except SyntaxError, e:
                irc.reply(msg, '%s: %r' % (debug.exnToString(e), s))
            except Exception, e:
                irc.reply(msg, debug.exnToString(e))
        else:
            irc.error(msg, conf.replyEvalNotAllowed)

    def _exec(self, irc, msg, args):
        """<statement>

        Execs <code>.  Returns success if it didn't raise any exceptions.
        """
        if conf.allowEval:
            s = privmsgs.getArgs(args)
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
        capability = privmsgs.getArgs(args)
        conf.defaultCapabilities[capability] = True
        irc.reply(msg, conf.replySuccess)

    def unsetdefaultcapability(self, irc, msg, args):
        """<capability>

        Unsets the default capability for any command.
        """
        capability = privmsgs.getArgs(args)
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
        s = privmsgs.getArgs(args)
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
        for irc in world.ircs[:]:
            irc.die()
        debug.exit(i)

    def flush(self, irc, msg, args):
        """takes no arguments

        Runs all the periodic flushers in world.flushers.
        """
        world.flush()
        irc.reply(msg, conf.replySuccess)

    def upkeep(self, irc, msg, args):
        """takes no arguments

        Runs the standard upkeep stuff (flushes and gc.collects()).
        """
        collected = world.upkeep()
        if gc.garbage:
            if len(gc.garbage) < 10:
                irc.reply(msg, 'Garbage!  %r' % gc.garbage)
            else:
                irc.reply(msg, 'Garbage!  %s items.' % len(gc.garbage))
        else:
            irc.reply(msg, '%s collected' % utils.nItems(collected, 'object'))

    def set(self, irc, msg, args):
        """<name> <value>

        Sets the runtime variable <name> to <value>.  Currently used variables
        include "noflush" which, if set to true value, will prevent the
        periodic flushing that normally occurs.
        """
        (name, value) = privmsgs.getArgs(args, optional=1)
        world.tempvars[name] = value
        irc.reply(msg, conf.replySuccess)

    def unset(self, irc, msg, args):
        """<name>

        Unsets the value of variables set via the 'set' command.
        """
        name = privmsgs.getArgs(args)
        try:
            del world.tempvars[name]
            irc.reply(msg, conf.replySuccess)
        except KeyError:
            irc.error(msg, 'That variable wasn\'t set.')

    def load(self, irc, msg, args):
        """<plugin>

        Loads the plugin <plugin> from the plugins/ directory.
        """
        name = privmsgs.getArgs(args)
        for cb in irc.callbacks:
            if cb.name() == name:
                irc.error(msg, 'That module is already loaded.')
                return
        try:
            moduleInfo = imp.find_module(name)
        except ImportError:
            irc.error(msg, 'No plugin %s exists.' % name)
            return
        module = imp.load_module(name, *moduleInfo)
        linecache.checkcache()
        callback = module.Class()
        if hasattr(callback, 'configure'):
            callback.configure(irc)
        irc.addCallback(callback)
        irc.reply(msg, conf.replySuccess)

    '''
    def superreload(self, irc, msg, args):
        """<module name>

        Reloads a module, hopefully such that all vestiges of the old module
        are gone.
        """
        name = privmsgs.getArgs(args)
        world.superReload(__import__(name))
        irc.reply(msg, conf.replySuccess)
    '''

    def reload(self, irc, msg, args):
        """<plugin>

        Unloads and subsequently reloads the callback by name; use the 'list'
        command to see a list of the currently loaded callbacks.
        """
        name = privmsgs.getArgs(args)
        callbacks = irc.removeCallback(name)

        if callbacks:
            for callback in callbacks:
                callback.die()
                del callback
            gc.collect()
            try:
                moduleInfo = imp.find_module(name)
                module = imp.load_module(name, *moduleInfo)
                linecache.checkcache()
                callback = module.Class()
                if hasattr(callback, 'configure'):
                    callback.configure(irc)
                irc.addCallback(callback)
                irc.reply(msg, conf.replySuccess)
            except ImportError:
                for callback in callbacks:
                    irc.addCallback(callback)
                irc.error(msg, 'No plugin %s exists.' % name)
        else:
            irc.error(msg, 'There was no callback %s.' % name)

    def unload(self, irc, msg, args):
        """<plugin>

        Unloads the callback by name; use the 'list' command to see a list
        of the currently loaded callbacks.
        """
        name = privmsgs.getArgs(args)
        callbacks = irc.removeCallback(name)
        if callbacks:
            for callback in callbacks:
                callback.die()
                del callback
            gc.collect()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'There was no callback %s' % name)

    def cvsup(self, irc, msg, args):
        """takes no arguments

        Returns the return code of 'cvs up'.  Do note that this command blocks
        the entire bot until the cvs up finishes.  If you're using ext
        authentication, you'll want to type the password in on the terminal
        the bot is running on, or he'll just freeze.
        """
        irc.reply(msg, str(os.system('cvs up')))

    def say(self, irc, msg, args):
        """<channel> <text>

        Says <text> in <channel>
        """
        (channel, text) = privmsgs.getArgs(args, needed=2)
        irc.queueMsg(ircmsgs.privmsg(channel, text))


Class = OwnerCommands


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

