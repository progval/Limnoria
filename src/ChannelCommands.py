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
Basic channel management commands.
"""

import time

import conf
import ircdb
import ircmsgs
import schedule
import ircutils
import privmsgs
import callbacks

class ChannelCommands(callbacks.Privmsg):
    def op(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will give you ops.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            irc.queueMsg(ircmsgs.op(channel, msg.nick))
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def halfop(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.halfop
        capability, this will give you halfops.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'halfop')
        if ircdb.checkCapability(msg.prefix, capability):
            irc.queueMsg(ircmsgs.halfop(channel, msg.nick))
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def voice(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.voice capability,
        this will give you voice.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'voice')
        if ircdb.checkCapability(msg.prefix, capability):
            irc.queueMsg(ircmsgs.halfop(channel, msg.nick))
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def cycle(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will cause the bot to "cycle", or PART and then JOIN the channel.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            irc.queueMsg(ircmsgs.part(channel))
            irc.queueMsg(ircmsgs.join(channel))
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def kban(self, irc, msg, args):
        """[<channel>] <nick> [<number of seconds to ban>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will kickban <nick> for as many seconds as you specify, or else
        (if you specify 0 seconds or don't specify a number of seconds) it
        will ban the person indefinitely.
        """
        channel = privmsgs.getChannel(msg, args)
        (bannedNick, length) = privmsgs.getArgs(args, optional=1)
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

    def lobotomize(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will "lobotomize" the bot, making it silent and unanswering to
        all requests made in the channel.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            ircdb.channels.getChannel(channel).lobotomized = True
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def unlobotomize(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will unlobotomize the bot, making it respond to requests made in
        the channel again.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            ircdb.channels.getChannel(channel).lobotomized = False
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def permban(self, irc, msg, args):
        """[<channel>] <nick|hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will effect a permanent (persistent) ban on the given <hostmask>
        (or the current hostmask associated with <nick>.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        arg = privmsgs.getArgs(args)
        if ircutils.isNick(arg):
            banmask = ircutils.banmask(irc.state.nickToHostmask(arg))
        else:
            banmask = arg
        if ircdb.checkCapability(msg.prefix, capability):
            c = ircdb.channels.getChannel(channel)
            c.addBan(banmask)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def unpermban(self, irc, msg, args):
        """[<channel>] <hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will remove the permanent ban on <hostmask>.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        banmask = privmsgs.getArgs(args)
        if ircdb.checkCapability(msg.prefix, capability):
            c = ircdb.channels.getChannel(channel)
            c.removeBan(banmask)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def chanignore(self, irc, msg, args):
        """[<channel>] <nick|hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will set a permanent (persistent) ignore on <hostmask> or the
        hostmask currently associated with <nick>.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        arg = privmsgs.getArgs(args)
        if ircutils.isNick(arg):
            banmask = ircutils.banmask(irc.state.nickToHostmask(arg))
        else:
            banmask = arg
        if ircdb.checkCapability(msg.prefix, capability):
            c = ircdb.channels.getChannel(channel)
            c.addIgnore(banmask)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def unchanignore(self, irc, msg, args):
        """[<channel>] <hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will remove the permanent ignore on <hostmask> in the channel.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'op')
        banmask = privmsgs.getArgs(args)
        if ircdb.checkCapability(msg.prefix, capability):
            c = ircdb.channels.getChannel(channel)
            c.removeIgnore(banmask)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def addchancapability(self, irc, msg, args):
        """[<channel>] <name|hostmask> <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will give the user currently identified as <name> (or the user
        to whom <hostmask> maps) the capability <capability> in the channel.
        """
        channel = privmsgs.getChannel(msg, args)
        (name, capability) = privmsgs.getArgs(args, 2)
        neededcapability = ircdb.makeChannelCapability(channel, 'op')
        capability = ircdb.makeChannelCapability(channel, capability)
        if ircdb.checkCapability(msg.prefix, neededcapability):
            try:
                u = ircdb.users.getUser(name)
                u.addCapability(capability)
                ircdb.users.setUser(name, u)
                irc.reply(msg, conf.replySuccess)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
        else:
            irc.error(msg, conf.replyNoCapability % neededcapability)

    def removechancapability(self, irc, msg, args):
        """[<channel>] <name|hostmask> <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will take from the user currently identified as <name> (or the
        user to whom <hostmask> maps) the capability <capability> in the
        channel.
        """
        channel = privmsgs.getChannel(msg, args)
        (name, capability) = privmsgs.getArgs(args, 2)
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
        channel = privmsgs.getChannel(msg, args)
        v = privmsgs.getArgs(args)
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
        channel = privmsgs.getChannel(msg, args)
        neededcapability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, neededcapability):
            (capability, value) = privmsgs.getArgs(args, 2)
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
            else:
                s = 'Value of the capability must be True or False'
                irc.error(msg, s)
        else:
            irc.error(msg, conf.replyNoCapability % neededcapability)

    def unsetchancapability(self, irc, msg, args):
        """[<chanel>] <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will unset the channel capability <capability> so each user's
        specific capability or the channel default capability will take
        precedence.
        """
        channel = privmsgs.getChannel(msg, args)
        neededcapability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, neededcapability):
            capability = privmsgs.getArgs(args)
            c = ircdb.channels.getChannel(channel)
            c.removeCapability(capability)
            ircdb.channels.setChannel(channel, c)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % neededcapability)


Class = ChannelCommands

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
