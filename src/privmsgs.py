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

    Always return a list of size needed + optional, filling it with however
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
            
            
            
    
###
# Privmsg Callbacks.
###
class ChannelCommands(callbacks.Privmsg):
    def op(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will give you ops.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            irc.queueMsg(ircmsgs.op(channel, msg.nick))
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def halfop(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.halfop
        capability, this will give you halfops.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'halfop')
        if ircdb.checkCapability(msg.prefix, capability):
            irc.queueMsg(ircmsgs.halfop(channel, msg.nick))
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def voice(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.voice capability,
        this will give you voice.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'voice')
        if ircdb.checkCapability(msg.prefix, capability):
            irc.queueMsg(ircmsgs.halfop(channel, msg.nick))
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def cycle(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will cause the bot to "cycle", or PART and then JOIN the channel.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            irc.queueMsg(ircmsgs.part(channel))
            irc.queueMsg(ircmsgs.join(channel))
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def kban(self, irc, msg, args):
        """[<channel>] <nick> [<number of seconds to ban>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will kickban <nick> for as many seconds as you specify, or else
        (if you specify 0 seconds or don't specify a number of seconds) it
        will ban the person indefinitely.
        """
        channel = getChannel(msg, args)
        (bannedNick, length) = getArgs(args, optional=1)
        length = int(length or 0)
        bannedHostmask = irc.state.nickToHostmask(bannedNick)
        capability = ircdb.makeChannelCapability(channel, 'op')
        banmask = ircutils.banmask(bannedHostmask)
        if ircdb.checkCapability(msg.prefix, capability)\
           and not ircdb.checkCapability(bannedHostmask, capability):
            irc.queueMsg(ircmsgs.ban(channel, banmask))
            irc.queueMsg(ircmsgs.kick(channel, bannedNick, msg.nick))
            if length > 0:
                def f():
                    irc.queueMsg(ircmsgs.unban(channel, banmask))
                schedule.addEvent(f, time.time() + length)
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def lobotomize(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will "lobotomize" the bot, making it silent and unanswering to
        all requests made in the channel.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            ircdb.channels.getChannel(channel).lobotomized = True
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def unlobotomize(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will unlobotomize the bot, making it respond to requests made in
        the channel again.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            ircdb.channels.getChannel(channel).lobotomized = False
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def permban(self, irc, msg, args):
        """[<channel>] <nick|hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will effect a permanent (persistent) ban on the given <hostmask>
        (or the current hostmask associated with <nick>.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        arg = getArgs(args)
        if ircutils.isNick(arg):
            banmask = ircutils.banmask(irc.state.nickToHostmask(arg))
        else:
            banmask = arg
        if ircdb.checkCapability(msg.prefix, capability):
            c = ircdb.channels.getChannel(channel)
            c.addBan(banmask)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def unpermban(self, irc, msg, args):
        """[<channel>] <hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will remove the permanent ban on <hostmask>.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        banmask = getArgs(args)
        if ircdb.checkCapability(msg.prefix, capability):
            c = ircdb.channels.getChannel(channel)
            c.removeBan(banmask)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def chanignore(self, irc, msg, args):
        """[<channel>] <nick|hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will set a permanent (persistent) ignore on <hostmask> or the
        hostmask currently associated with <nick>.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        arg = getArgs(args)
        if ircutils.isNick(arg):
            banmask = ircutils.banmask(irc.state.nickToHostmask(arg))
        else:
            banmask = arg
        if ircdb.checkCapability(msg.prefix, capability):
            c = ircdb.channels.getChannel(channel)
            c.addIgnore(banmask)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def unchanignore(self, irc, msg, args):
        """[<channel>] <hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will remove the permanent ignore on <hostmask> in the channel.
        """
        channel = getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        banmask = getArgs(args)
        if ircdb.checkCapability(msg.prefix, capability):
            c = ircdb.channels.getChannel(channel)
            c.removeIgnore(banmask)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            return

    def addchancapability(self, irc, msg, args):
        """[<channel>] <name|hostmask> <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will give the user currently identified as <name> (or the user
        to whom <hostmask> maps) the capability <capability> in the channel.
        """
        channel = getChannel(msg, args)
        (name, capability) = getArgs(args, 2)
        neededcapability = ircdb.makeChannelCapability(channel, 'op')
        capability = ircdb.makeChannelCapability(channel, capability)
        if ircdb.checkCapability(msg.prefix, neededcapability):
            try:
                u = ircdb.users.getUser(name)
                u.addCapability(capability)
                ircdb.users.setUser(name, u)
                irc.reply(msg, conf.replySuccess)
                return
            except KeyError:
                irc.error(msg, conf.replyNoUser)
                return
        else:
            irc.error(msg, conf.replyNoCapability % neededcapability)
            return

    def removechancapability(self, irc, msg, args):
        """[<channel>] <name|hostmask> <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will take from the user currently identified as <name> (or the
        user to whom <hostmask> maps) the capability <capability> in the
        channel.
        """
        channel = getChannel(msg, args)
        (name, capability) = getArgs(args, 2)
        neededcapability = ircdb.makeChannelCapability(channel, 'op')
        capability = ircdb.makeChannelCapability(channel, capability)
        if ircdb.checkCapability(msg.prefix, neededcapability):
            try:
                u = ircdb.users.getUser(name)
                u.removeCapability(capability)
                ircdb.users.setUser(name, u)
                irc.reply(msg, conf.replySuccess)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
        else:
            irc.error(msg, conf.replyNoCapability % neededcapability)

    def setdefaultchancapability(self, irc, msg, args):
        """[<channel>] <default response to unknown capabilities> <True|False>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will set the default response to non-power-related (that is,
        not {op, halfop, voice} capabilities to be the value you give.
        """
        channel = getChannel(msg, args)
        v = getArgs(args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            c = ircdb.channels.getChannel(channel)
            if v == 'True' or v == 'False':
                if v == 'True':
                    c.setDefaultCapability(True)
                elif v == 'False':
                    c.setDefaultCapability(False)
                ircdb.channels.setChannel(channel, c)
                irc.reply(msg, conf.replySuccess)
            else:
                s = 'The default value must be either True or False.'
                irc.error(msg, s)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def setchancapability(self, irc, msg, args):
        """[<channel>] <capability> <True|False>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will set the channel capability <capability> for all users in the
        channel.
        """
        channel = getChannel(msg, args)
        neededcapability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, neededcapability):
            (capability, value) = getArgs(args, 2)
            value = value.capitalize()
            if value == 'True' or value == 'False':
                if value == 'True':
                    value = True
                elif value == 'False':
                    value = False
                c = ircdb.channels.getChannel(channel)
                c.addCapability(capability, value)
                ircdb.channels.setChannel(channel, c)
                irc.reply(msg, conf.replySuccess)
                return
            else:
                s = 'Value of the capability must be True or False'
                irc.error(msg, s)
                return
        else:
            irc.error(msg, conf.replyNoCapability % neededcapability)
            return

    def unsetchancapability(self, irc, msg, args):
        """[<chanel>] <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will unset the channel capability <capability> so each user's
        specific capability or the channel default capability will take
        precedence.
        """
        channel = getChannel(msg, args)
        neededcapability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, neededcapability):
            capability = getArgs(args)
            c = ircdb.channels.getChannel(channel)
            c.removeCapability(capability)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % neededcapability)
            return


class AdminCommands(callbacks.Privmsg):
    def join(self, irc, msg, args):
        """<channel> [<channel> ...]

        Tell the bot to join the whitespace-separated list of channels
        you give it.
        """
        if ircdb.checkCapability(msg.prefix, 'admin'):
            irc.queueMsg(ircmsgs.joins(args))
            for channel in args:
                irc.queueMsg(ircmsgs.who(channel))
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return

    def nick(self, irc, msg, args):
        """<nick>

        Changes the bot's nick to <nick>."""
        nick = getArgs(args)
        if ircdb.checkCapability(msg.prefix, 'admin'):
            irc.queueMsg(ircmsgs.nick(nick))
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return

    def part(self, irc, msg, args):
        """<channel> [<channel> ...]

        Tells the bot to part the whitespace-separated list of channels
        you give it.
        """
        if ircdb.checkCapability(msg.prefix, 'admin'):
            irc.queueMsg(ircmsgs.parts(args, msg.nick))
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return

    def disable(self, irc, msg, args):
        """<command>

        Disables the command <command> for all non-owner users.
        """
        command = getArgs(args)
        if ircdb.checkCapability(msg.prefix, 'admin'):
            if command in ('enable', 'identify', 'auth'):
                irc.error(msg, 'You can\'t disable %s!' % command)
            else:
                # This has to know that defaultCapabilties gets turned into a
                # dictionary.
                capability = ircdb.makeAntiCapability(command)
                conf.defaultCapabilities[capability] = True
                irc.reply(msg, conf.replySuccess)
                return
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return

    def enable(self, irc, msg, args):
        """<command>

        Re-enables the command <command> for all non-owner users.
        """
        command = getArgs(args)
        anticapability = ircdb.makeAntiCapability(command)
        if ircdb.checkCapability(msg.prefix, 'admin'):
            if anticapability in conf.defaultCapabilities:
                del conf.defaultCapabilities[anticapability]
                irc.reply(msg, conf.replySuccess)
                return
            else:
                irc.error(msg, 'That command wasn\'t disabled.')
                return
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return

    def addcapability(self, irc, msg, args):
        """<name|hostmask> <capability>

        Gives the user specified by <name> (or the user to whom <hostmask>
        currently maps) the specified capability <capability>
        """
        (name, capability) = getArgs(args, 2)
        if ircdb.checkCapability(msg.prefix, 'admin'):
            # This next check to make sure 'admin's can't hand out 'owner'.
            if ircdb.checkCapability(msg.prefix, capability) or \
               '!' in capability:
                try:
                    u = ircdb.users.getUser(name)
                    u.addCapability(capability)
                    ircdb.users.setUser(name, u)
                    irc.reply(msg, conf.replySuccess)
                    return
                except KeyError:
                    irc.error(msg, conf.replyNoUser)
                    return
            else:
               s = 'You can\'t add capabilities you don\'t have.'
               irc.error(msg, s)
               return
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return

    def removecapability(self, irc, msg, args):
        """<name|hostmask> <capability>

        Takes from the user specified by <name> (or the uswer to whom
        <hostmask> currently maps) the specified capability <capability>
        """
        (name, capability) = getArgs(args, 2)
        if ircdb.checkCapability(msg.prefix, 'admin'):
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
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')

    def setprefixchar(self, irc, msg, args):
        """<prefixchars>

        Sets the prefix chars by which the bot can be addressed.
        """
        s = getArgs(args)
        if ircdb.checkCapability(msg.prefix, 'admin'):
            if s.translate(string.ascii, string.ascii_letters) == '':
                irc.error(msg, 'Prefixes cannot contain letters.')
            else:
                conf.prefixChars = s
                irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')


class OwnerCommands(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        setattr(self.__class__, 'eval', self._eval)
        #setattr(self.__class__, 'import', self._import)
        setattr(self.__class__, 'exec', self._exec)

    def _eval(self, irc, msg, args):
        """<string to be evaluated by the Python interpreter>"""
        if ircdb.checkCapability(msg.prefix, 'owner'):
            if conf.allowEval:
                s = getArgs(args)
                try:
                    irc.reply(msg, repr(eval(s)))
                except Exception, e:
                    irc.reply(msg, debug.exnToString(e))
            else:
                irc.error(msg, conf.replyEvalNotAllowed)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')

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
        if ircdb.checkCapability(msg.prefix, 'owner'):
            if conf.allowEval:
                s = getArgs(args)
                try:
                    exec s
                    irc.reply(msg, conf.replySuccess)
                except Exception, e:
                    irc.reply(msg, debug.exnToString(e))
            else:
                irc.error(msg, conf.replyEvalNotAllowed)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')

    def setdefaultcapability(self, irc, msg, args):
        """<capability>

        Sets the default capability to be allowed for any command.
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            capability = getArgs(args)
            conf.defaultCapabilities[capability] = True
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')

    def unsetdefaultcapability(self, irc, msg, args):
        """<capability>

        Unsets the default capability for any command.
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            capability = getArgs(args)
            del conf.defaultCapabilities[capability]
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')

    def settrace(self, irc, msg, args):
        """takes no arguments

        Starts the function-tracing debug mode; beware that this makes *huge*
        logfiles.
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            sys.settrace(debug.tracer)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')

    def unsettrace(self, irc, msg, args):
        """takes no arguments

        Stops the function-tracing debug mode."""
        if ircdb.checkCapability(msg.prefix, 'owner'):
            sys.settrace(None)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')

    def ircquote(self, irc, msg, args):
        """<string to be sent to the server>

        Sends the raw string given to the server.
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            s = getArgs(args)
            try:
                m = ircmsgs.IrcMsg(s)
                irc.queueMsg(m)
            except Exception:
                debug.recoverableException()
                irc.error(msg, conf.replyError)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')

    def quit(self, irc, msg, args):
        """[<int return value>]

        Exits the program with the given return value (the default is 0)
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            try:
                i = int(args[0])
            except (ValueError, IndexError):
                i = 0
            for driver in drivers._drivers.itervalues():
                driver.die()
            for irc in world.ircs:
                irc.die()
            debug.exit(i)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')

    def flush(self, irc, msg, args):
        """takes no arguments

        Runs all the periodic flushers in world.flushers.
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            world.flush()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')
            
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
                            return
            else:
                try:
                    module = sys.modules[module]
                except KeyError:
                    irc.error(msg, 'Module %s not found.' % module)
                    return
                world.superReload(module)
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')
            return
    '''

    def set(self, irc, msg, args):
        """<name> <value>

        Sets the runtime variable <name> to <value>.  Currently used variables
        include "noflush" which, if set to true value, will prevent the
        periodic flushing that normally occurs.
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            (name, value) = getArgs(args, optional=1)
            world.tempvars[name] = value
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')
            return

    def unset(self, irc, msg, args):
        """<name>

        Unsets the value of variables set via the 'set' command.
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            name = getArgs(args)
            try:
                del world.tempvars[name]
            except KeyError:
                irc.error(msg, 'That variable wasn\'t set.')
                return
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')
            return

    def load(self, irc, msg, args):
        """<plugin>

        Loads the plugin <plugin> from the plugins/ directory.
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            plugin = getArgs(args)
            try:
                moduleInfo = imp.find_module(plugin)
            except ImportError:
                irc.error(msg, 'Sorry, no plugin %s exists.' % plugin)
                return
            try:
                module = imp.load_module(plugin, *moduleInfo)
                callback = module.Class()
                irc.addCallback(callback)
                irc.reply(msg, conf.replySuccess)
                return
            except Exception, e:
                debug.recoverableException()
                irc.error(msg, debug.exnToString(e))
                return
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')
            return

    def unload(self, irc, msg, args):
        """<callback name>

        Unloads the callback by name; use the 'list' command to see a list
        of the currently loaded callbacks.
        """
        if ircdb.checkCapability(msg.prefix, 'owner'):
            name = getArgs(args)
            numCallbacks = len(irc.callbacks)
            callbacks = irc.removeCallback(name)
            for callback in callbacks:
                callback.die()
            if len(irc.callbacks) < numCallbacks:
                irc.reply(msg, conf.replySuccess)
            else:
                irc.error(msg, 'There was no callback %s' % name)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')


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
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        irc.reply(msg, repr(user.hostmasks))

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
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        irc.reply(msg, '[%s]' % ', '.join(user.capabilities))

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
            return
        else:
            irc.error(msg, conf.replyIncorrectAuth)
            return

    def unidentify(self, irc, msg, args):
        """takes no arguments

        Un-identifies the user.
        """
        try:
            u = ircdb.users.getUser(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        u.unsetAuth()
        ircdb.users.setUser(name, u)
        irc.reply(msg, conf.replySuccess)

    def whoami(self, irc, msg, args):
        """takes no arguments.

        Returns the name of the user calling the command.
        """
        try:
            name = ircdb.users.getUserName(msg.prefix)
            irc.reply(msg, name)
        except KeyError:
            irc.error(msg, 'I can\'t find you in my database')


class MiscCommands(callbacks.Privmsg):
    def list(self, irc, msg, args):
        """[<module name>]

        Lists the commands available in the given module.  If no module is
        given, lists the public modules available.
        """
        name = getArgs(args, needed=0, optional=1)
        name = name.lower()
        if not name:
            names = [cb.__class__.__name__
                     for cb in irc.callbacks
                     if hasattr(cb, 'public') and cb.public]
            irc.reply(msg, ', '.join(names))
        else:
            for cb in irc.callbacks:
                cls = cb.__class__
                if cls.__name__.lower().startswith(name) and \
                       not issubclass(cls, callbacks.PrivmsgRegexp) and \
                       issubclass(cls, callbacks.Privmsg):
                    commands = [x for x in cls.__dict__
                                if cb.isCommand(x) and \
                                hasattr(getattr(cb, x), '__doc__')]
                    irc.reply(msg, ', '.join(commands))
                    return
            irc.error(msg, 'There is no module named %s, ' \
                                 'or that module has no commands.' % name)

    def help(self, irc, msg, args):
        """<command>

        Gives the help for a specific command.  To find commands,
        use the 'list' command to go see the commands offered by a module.
        The 'list' command by itself will show you what modules have commands.
        """
        command = getArgs(args, needed=0, optional=1)
        if not command:
            command = 'help'
        command = callbacks.canonicalName(command)
        cb = irc.findCallback(command)
        if cb:
            method = getattr(cb, command)
            if hasattr(method, '__doc__'):
                doclines = method.__doc__.splitlines()
                help = doclines.pop(0)
                if doclines:
                    s = '%s %s (for more help use the morehelp command)'
                else:
                    s = '%s %s'
                irc.reply(msg, s % (command, help))
            else:
                irc.reply(msg, 'That command exists, but has no help.')
        else:
            for cb in irc.callbacks:
                if cb.name() == command:
                    if hasattr(cb, '__doc__'):
                        doclines = cb.__doc__.splitlines()
                        help = ' '.join(map(str.strip, doclines))
                        irc.reply(msg, help)
                    else:
                        irc.error(msg, 'That callback has no help.')
            else:
                irc.error(msg, 'There is no such command')

    def morehelp(self, irc, msg, args):
        """<command>

        This command gives more help than is provided by the simple argument
        list given by the command 'help'.
        """
        command = callbacks.canonicalName(getArgs(args))
        cb = irc.findCallback(command)
        if cb:
            method = getattr(cb, command)
            if hasattr(method, '__doc__'):
                doclines = method.__doc__.splitlines()
                simplehelp = doclines.pop(0)
                if doclines:
                    doclines = filter(None, doclines)
                    doclines = map(str.strip, doclines)
                    help = ' '.join(doclines)
                    irc.reply(msg, help)
                else:
                    irc.reply(msg, 'That command has no more help.  '\
                                   'The original help is this: %s %s' % \
                                   (command, simplehelp))
            else:
                irc.error(msg, 'That command has no help at all.')
        

    def bug(self, irc, msg, args):
        """takes no arguments

        Log a recent bug.  A revent (long) history of the messages received
        will be logged, so don't abuse this command or you'll have an upset
        admin to deal with.
        """
        debug.debugMsg(pprint.pformat(irc.state.history), 'normal')
        irc.reply(msg, conf.replySuccess)

    def version(self, irc, msg, args):
        """takes no arguments

        Returns the version of the current bot.
        """
        irc.reply(msg, world.version)

    def logfilesize(self, irc, msg, args):
        """takes no arguments

        Returns the size of the various logfiles in use.
        """
        result = []
        for file in os.listdir(conf.logDir):
            if file.endswith('.log'):
                stats = os.stat(os.path.join(conf.logDir, file))
                result.append((file, str(stats.st_size)))
        irc.reply(msg, ', '.join(map(': '.join, result)))

standardPrivmsgModules = (OwnerCommands,
                          AdminCommands,
                          ChannelCommands,
                          UserCommands,
                          MiscCommands)
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
