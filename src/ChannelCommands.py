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
Basic channel management commands.  Many of these commands require their caller
to have the <channel>.op capability.  This plugin is loaded by default.
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
    def op(self, irc, msg, args, channel):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will give you ops.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.queueMsg(ircmsgs.op(channel, msg.nick))
        else:
            irc.error(msg, 'How can I op you?  I\'m not opped!')
    op = privmsgs.checkChannelCapability(op, 'op')

    def halfop(self, irc, msg, args, channel):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.halfop
        capability, this will give you halfops.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.queueMsg(ircmsgs.halfop(channel, msg.nick))
        else:
            irc.error(msg, 'How can I halfop you?  I\'m not opped!')
    halfop = privmsgs.checkChannelCapability(halfop, 'halfop')

    def voice(self, irc, msg, args, channel):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.voice capability,
        this will give you voice.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.queueMsg(ircmsgs.voice(channel, msg.nick))
        else:
            irc.error(msg, 'How can I voice you?  I\'m not opped!')
    voice = privmsgs.checkChannelCapability(voice, 'voice')
    
    def cycle(self, irc, msg, args, channel):
        """[<channel>] [<key>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will cause the bot to "cycle", or PART and then JOIN the channel.
        If <key> is given, join the channel using that key.
        """
        key = privmsgs.getArgs(args, needed=0, optional=1)
        if not key:
            key = None
        irc.queueMsg(ircmsgs.part(channel))
        irc.queueMsg(ircmsgs.join(channel, key))
    cycle = privmsgs.checkChannelCapability(cycle, 'op')

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
            if irc.nick in irc.state.channels[channel].ops:
                irc.queueMsg(ircmsgs.ban(channel, banmask))
                irc.queueMsg(ircmsgs.kick(channel, bannedNick, msg.nick))
                if length > 0:
                    def f():
                        irc.queueMsg(ircmsgs.unban(channel, banmask))
                    schedule.addEvent(f, time.time() + length)
            else:
                irc.error(msg, 'How can I do that?  I\'m not opped.')
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def lobotomize(self, irc, msg, args, channel):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will "lobotomize" the bot, making it silent and unanswering to
        all requests made in the channel.
        """
        ircdb.channels.getChannel(channel).lobotomized = True
        irc.reply(msg, conf.replySuccess)
    lobotomize = privmsgs.checkChannelCapability(lobotomize, 'op')

    def unlobotomize(self, irc, msg, args, channel):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will unlobotomize the bot, making it respond to requests made in
        the channel again.
        """
        ircdb.channels.getChannel(channel).lobotomized = False
        irc.reply(msg, conf.replySuccess)
    unlobotomize = privmsgs.checkChannelCapability(unlobotomize, 'op')

    def permban(self, irc, msg, args, channel):
        """[<channel>] <nick|hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will effect a permanent (persistent) ban on the given <hostmask>
        (or the current hostmask associated with <nick>.
        """
        arg = privmsgs.getArgs(args)
        if ircutils.isNick(arg):
            banmask = ircutils.banmask(irc.state.nickToHostmask(arg))
        elif ircutils.isUserHostmask(arg):
            banmask = arg
        else:
            irc.error(msg, 'That\'s not a valid nick or hostmask.')
            return
        c = ircdb.channels.getChannel(channel)
        c.addBan(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    permban = privmsgs.checkChannelCapability(permban, 'op')

    def unpermban(self, irc, msg, args, channel):
        """[<channel>] <hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will remove the permanent ban on <hostmask>.
        """
        banmask = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.removeBan(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    unpermban = privmsgs.checkChannelCapability(unpermban, 'op')

    def chanignore(self, irc, msg, args, channel):
        """[<channel>] <nick|hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will set a permanent (persistent) ignore on <hostmask> or the
        hostmask currently associated with <nick>.
        """
        arg = privmsgs.getArgs(args)
        if ircutils.isNick(arg):
            banmask = ircutils.banmask(irc.state.nickToHostmask(arg))
        elif ircutils.isUserHostmask(arg):
            banmask = arg
        else:
            irc.error(msg, 'That\'s not a valid nick or hostmask.')
            return
        c = ircdb.channels.getChannel(channel)
        c.addIgnore(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    chanignore = privmsgs.checkChannelCapability(chanignore, 'op')

    def unchanignore(self, irc, msg, args, channel):
        """[<channel>] <hostmask>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will remove the permanent ignore on <hostmask> in the channel.
        """
        banmask = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.removeIgnore(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    unchanignore = privmsgs.checkChannelCapability(unchanignore, 'op')

    def addchancapability(self, irc, msg, args, channel):
        """[<channel>] <name|hostmask> <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will give the user currently identified as <name> (or the user
        to whom <hostmask> maps) the capability <capability> in the channel.
        """
        (name, capability) = privmsgs.getArgs(args, 2)
        capability = ircdb.makeChannelCapability(channel, capability)
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
            user.addCapability(capability)
            ircdb.users.setUser(id, user)
            irc.reply(msg, conf.replySuccess)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
    addchancapability = privmsgs.checkChannelCapability(addchancapability,'op')

    def removechancapability(self, irc, msg, args, channel):
        """[<channel>] <name|hostmask> <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will take from the user currently identified as <name> (or the
        user to whom <hostmask> maps) the capability <capability> in the
        channel.
        """
        (name, capability) = privmsgs.getArgs(args, 2)
        capability = ircdb.makeChannelCapability(channel, capability)
        try:
            id = ircdb.users.getUser(name)
            user = ircdb.users.getUser(id)
            user.removeCapability(capability)
            ircdb.users.setUser(id, user)
            irc.reply(msg, conf.replySuccess)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
    removechancapability = \
        privmsgs.checkChannelCapability(removechancapability, 'op')

    def setdefaultchancapability(self, irc, msg, args, channel):
        """[<channel>] <default response to unknown capabilities> <True|False>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will set the default response to non-power-related (that is,
        not {op, halfop, voice} capabilities to be the value you give.
        """
        v = privmsgs.getArgs(args)
        v = v.capitalize()
        c = ircdb.channels.getChannel(channel)
        if v == 'True':
            c.setDefaultCapability(True)
        elif v == 'False':
            c.setDefaultCapability(False)
        else:
            s = 'The default value must be either True or False.'
            irc.error(msg, s)
            return
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    setdefaultchancapability = \
        privmsgs.checkChannelCapability(setdefaultchancapability, 'op')

    def setchancapability(self, irc, msg, args, channel):
        """[<channel>] <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will add the channel capability <capability> for all users in the
        channel.
        """
        capability = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.addCapability(capability)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    setchancapability = privmsgs.checkChannelCapability(setchancapability,
                                                        'op')

    def unsetchancapability(self, irc, msg, args, channel):
        """[<chanel>] <capability>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  If you have the #channel.op capability,
        this will unset the channel capability <capability> so each user's
        specific capability or the channel default capability will take
        precedence.
        """
        capability = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.removeCapability(capability)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    unsetchancapability = privmsgs.checkChannelCapability(unsetchancapability,
                                                          'op')

    def chancapabilities(self, irc, msg, args):
        """[<channel>]

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  Returns the capabilities present on the
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        c = ircdb.channels.getChannel(channel)
        irc.reply(msg, ', '.join(c.capabilities))


Class = ChannelCommands

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
