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
import re
import sys
import imp
import time
import pprint

import conf
import debug
import world
import ircdb
import ircmsgs
import drivers
import ircutils
import schedule
import callbacks

def getChannel(msg, args):
    """Returns the channel the msg came over or the channel given in args.

    If the channel was given in args, args is modified (the channel is
    removed).
    """
    if ircutils.isChannel(msg.args[0]):
        return msg.args[0]
    else:
        if len(args) > 0:
            return args.pop(0)
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
    if len(args) < needed + optional:
        ret = list(args) + ([''] * (needed + optional - len(args)))
    elif len(args) >= needed + optional:
        ret = list(args[:needed + optional - 1])
        ret.append(' '.join(args[needed + optional - 1:]))
    else:
        raise callbacks.Error
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
            

class CapabilityChecker(callbacks.Privmsg):
    def callCommand(self, f, irc, msg, args):
        if ircdb.checkCapability(msg.prefix, self.capability):
            callbacks.Privmsg.callCommand(self, f, irc, msg, args)
        else:
            irc.error(msg, conf.replyNoCapability % self.capability)


class AdminCommands(CapabilityChecker):
    capability = 'admin'
    def join(self, irc, msg, args):
        """<channel> [<channel> ...]

        Tell the bot to join the whitespace-separated list of channels
        you give it.
        """
        irc.queueMsg(ircmsgs.joins(args))
        for channel in args:
            irc.queueMsg(ircmsgs.who(channel))

    def nick(self, irc, msg, args):
        """<nick>

        Changes the bot's nick to <nick>."""
        nick = getArgs(args)
        irc.queueMsg(ircmsgs.nick(nick))

    def part(self, irc, msg, args):
        """<channel> [<channel> ...]

        Tells the bot to part the whitespace-separated list of channels
        you give it.
        """
        irc.queueMsg(ircmsgs.parts(args, msg.nick))

    def disable(self, irc, msg, args):
        """<command>

        Disables the command <command> for all non-owner users.
        """
        command = getArgs(args)
        if command in ('enable', 'identify'):
            irc.error(msg, 'You can\'t disable %s!' % command)
        else:
            # This has to know that defaultCapabilties gets turned into a
            # dictionary.
            if command in conf.defaultCapabilities:
                conf.defaultCapabilities.remove(command)
            capability = ircdb.makeAntiCapability(command)
            conf.defaultCapabilities.add(capability)
            irc.reply(msg, conf.replySuccess)

    def enable(self, irc, msg, args):
        """<command>

        Re-enables the command <command> for all non-owner users.
        """
        command = getArgs(args)
        anticapability = ircdb.makeAntiCapability(command)
        if anticapability in conf.defaultCapabilities:
            conf.defaultCapabilities.remove(anticapability)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'That command wasn\'t disabled.')

    def addcapability(self, irc, msg, args):
        """<name|hostmask> <capability>

        Gives the user specified by <name> (or the user to whom <hostmask>
        currently maps) the specified capability <capability>
        """
        (name, capability) = getArgs(args, 2)
        # This next check to make sure 'admin's can't hand out 'owner'.
        if ircdb.checkCapability(msg.prefix, capability) or \
           '!' in capability:
            try:
                u = ircdb.users.getUser(name)
                u.addCapability(capability)
                ircdb.users.setUser(name, u)
                irc.reply(msg, conf.replySuccess)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
        else:
            s = 'You can\'t add capabilities you don\'t have.'
            irc.error(msg, s)

    def removecapability(self, irc, msg, args):
        """<name|hostmask> <capability>

        Takes from the user specified by <name> (or the uswer to whom
        <hostmask> currently maps) the specified capability <capability>
        """
        (name, capability) = getArgs(args, 2)
        if ircdb.checkCapability(msg.prefix, capability) or \
           '!' in capability:
            try:
                u = ircdb.users.getUser(name)
                u.addCapability(capability)
                ircdb.users.setUser(name, u)
                irc.reply(msg, conf.replySuccess)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
        else:
            s = 'You can\'t remove capabilities you don\'t have.'
            irc.error(msg, s)

    def setprefixchar(self, irc, msg, args):
        """<prefixchars>

        Sets the prefix chars by which the bot can be addressed.
        """
        s = getArgs(args)
        if s.translate(string.ascii, string.ascii_letters) == '':
            irc.error(msg, 'Prefixes cannot contain letters.')
        else:
            conf.prefixChars = s
            irc.reply(msg, conf.replySuccess)


class OwnerCommands(CapabilityChecker):
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

    '''
    def _import(self, irc, msg, args):
        """<module to import>"""
        if ircdb.checkCapability(msg.prefix, 'owner'):
            if conf.allowEval:
                s = getArgs(args)
                try:
                    exec ('global %s' % s)
                    exec ('import %s' % s)
                    irc.reply(msg, conf.replySuccess)
                except Exception, e:
                    irc.reply(msg, debug.exnToString(e))
            else:
                irc.error(msg, conf.replyEvalNotAllowed)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')
    '''

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
            
    '''
    def reload(self, irc, msg, args):
        "<module>"
        if ircdb.checkCapability(msg.prefix, 'owner'):
            module = getArgs(args)
            if module == 'all':
                for name, module in sys.modules.iteritems():
                    if name != '__main__':
                        try:
                            world.superReload(module)
                        except Exception, e:
                            m = '%s: %s' % (name, debug.exnToString(e))
                            irc.reply(msg, m)
            else:
                try:
                    module = sys.modules[module]
                except KeyError:
                    irc.error(msg, 'Module %s not found.' % module)
                    return
                world.superReload(module)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')
    '''

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
        plugin = getArgs(args)
        try:
            moduleInfo = imp.find_module(plugin)
        except ImportError:
            irc.error(msg, 'Sorry, no plugin %s exists.' % plugin)
            return
        module = imp.load_module(plugin, *moduleInfo)
        callback = module.Class()
        irc.addCallback(callback)
        irc.reply(msg, conf.replySuccess)

    def unload(self, irc, msg, args):
        """<callback name>

        Unloads the callback by name; use the 'list' command to see a list
        of the currently loaded callbacks.
        """
        name = getArgs(args)
        numCallbacks = len(irc.callbacks)
        callbacks = irc.removeCallback(name)
        for callback in callbacks:
            callback.die()
        if len(irc.callbacks) < numCallbacks:
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'There was no callback %s' % name)


class UserCommands(callbacks.Privmsg):
    def _checkNotChannel(self, irc, msg, password=' '):
        if password and ircutils.isChannel(msg.args[0]):
            irc.error(msg, conf.replyRequiresPrivacy)

    def register(self, irc, msg, args):
        """<name> <password>

        Registers <name> with the given password <password> and the current
        hostmask of the person registering.
        """
        (name, password) = getArgs(args, optional=1)
        self._checkNotChannel(irc, msg, password)
        if ircutils.isChannel(msg.args[0]):
            irc.error(msg, conf.replyRequiresPrivacy)
        if ircdb.users.hasUser(name):
            irc.error(msg, 'That name is already registered.')
        if ircutils.isUserHostmask(name):
            irc.error(msg, 'Hostmasks aren\'t valid usernames.')
        user = ircdb.IrcUser()
        user.setPassword(password)
        user.addHostmask(msg.prefix)
        ircdb.users.setUser(name, user)
        irc.reply(msg, conf.replySuccess)

    def addhostmask(self, irc, msg, args):
        """<name> <hostmask> [<password>]

        Adds the hostmask <hostmask> to the user specified by <name>.  The
        <password> may only be required if the user is not recognized by his
        hostmask.
        """
        (name, hostmask, password) = getArgs(args, 2, 1)
        self._checkNotChannel(irc, msg, password)
        s = hostmask.translate(string.ascii, '!@*?')
        if len(s) < 10:
            s = 'Hostmask must be more than 10 non-wildcard characters.'
            irc.error(msg, s)
        try:
            user = ircdb.users.getUser(name)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
        try:
            name = ircdb.users.getUserName(hostmask)
            s = 'That hostmask is already registered to %s.' % name
            irc.error(msg, s)
        except KeyError:
            pass
        if user.checkHostmask(msg.prefix) or user.checkPassword(password):
            user.addHostmask(hostmask)
            ircdb.users.setUser(name, user)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyIncorrectAuth)

    def delhostmask(self, irc, msg, args):
        """<name> <hostmask> [<password>]

        Deletes the hostmask <hostmask> from the record of the user specified
        by <name>.  The <password> may only be required if the user is not
        recognized by his hostmask.
        """
        (name, hostmask, password) = getArgs(args, 2, 1)
        self._checkNotChannel(irc, msg, password)
        try:
            user = ircdb.users.getUser(name)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
        if user.checkHostmask(msg.prefix) or user.checkPassword(password):
            user.removeHostmask(hostmask)
            ircdb.users.setUser(name, user)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyIncorrectAuth)

    def setpassword(self, irc, msg, args):
        """<name> <old password> <new password>

        Sets the new password for the user specified by <name> to
        <new password>.
        """
        (name, oldpassword, newpassword) = getArgs(args, 3)
        self._checkNotChannel(irc, msg, oldpassword+newpassword)
        try:
            user = ircdb.users.getUser(name)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
        if user.checkPassword(oldpassword):
            user.setPassword(newpassword)
            ircdb.users.setUser(name, user)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyIncorrectAuth)

    def username(self, irc, msg, args):
        """<hostmask|nick>

        Returns the username of the user specified by <hostmask> or <nick> if
        the user is registered.
        """
        hostmask = getArgs(args)
        if not ircutils.isUserHostmask(hostmask):
            try:
                hostmask = irc.state.nickToHostmask(hostmask)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
        try:
            name = ircdb.users.getUserName(hostmask)
            irc.reply(msg, name)
        except KeyError:
            irc.error(msg, conf.replyNoUser)

    def hostmasks(self, irc, msg, args):
        """[<name>]

        Returns the hostmasks of the user specified by <name>; if <name> isn't
        specified, returns the hostmasks of the user calling the command.
        """
        if not args:
            name = msg.prefix
        else:
            name = getArgs(args)
        try:
            user = ircdb.users.getUser(name)
            irc.reply(msg, repr(user.hostmasks))
        except KeyError:
            irc.error(msg, conf.replyNoUser)

    def capabilities(self, irc, msg, args):
        """[<name>]

        Returns the capabilities of the user specified by <name>; if <name>
        isn't specified, returns the hostmasks of the user calling the command.
        """
        if not args:
            try:
                name = ircdb.users.getUserName(msg.prefix)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
                return
        else:
            name = getArgs(args)
        try:
            user = ircdb.users.getUser(name)
            irc.reply(msg, '[%s]' % ', '.join(user.capabilities))
        except KeyError:
            irc.error(msg, conf.replyNoUser)

    def identify(self, irc, msg, args):
        """<name> <password>

        Identifies the user as <name>.
        """
        (name, password) = getArgs(args, 2)
        self._checkNotChannel(irc, msg)
        try:
            u = ircdb.users.getUser(name)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        if u.checkPassword(password):
            u.setAuth(msg.prefix)
            ircdb.users.setUser(name, u)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyIncorrectAuth)

    def unidentify(self, irc, msg, args):
        """takes no arguments

        Un-identifies the user.
        """
        try:
            u = ircdb.users.getUser(msg.prefix)
            name = ircdb.users.getUserName(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        u.unsetAuth()
        ircdb.users.setUser(name, u)
        irc.reply(msg, conf.replySuccess)

    def whoami(self, irc, msg, args):
        """takes no arguments

        Returns the name of the user calling the command.
        """
        try:
            name = ircdb.users.getUserName(msg.prefix)
            irc.reply(msg, name)
        except KeyError:
            irc.error(msg, 'I can\'t find you in my database')


standardPrivmsgModules = (OwnerCommands,
                          AdminCommands,
                          UserCommands,)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
