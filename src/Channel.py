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

__revision__ = "$Id$"

import fix

import time
from itertools import imap

import conf
import ircdb
import utils
import ircmsgs
import schedule
import ircutils
import privmsgs
import callbacks

class Channel(callbacks.Privmsg):
    def op(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel.op capability, this will give you ops.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.queueMsg(ircmsgs.op(channel, msg.nick))
        else:
            irc.error(msg, 'How can I op you?  I\'m not opped!')
    op = privmsgs.checkChannelCapability(op, 'op')

    def halfop(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel.halfop capability, this will give you halfops.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.queueMsg(ircmsgs.halfop(channel, msg.nick))
        else:
            irc.error(msg, 'How can I halfop you?  I\'m not opped!')
    halfop = privmsgs.checkChannelCapability(halfop, 'halfop')

    def voice(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel.voice capability, this will give you voice.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.queueMsg(ircmsgs.voice(channel, msg.nick))
        else:
            irc.error(msg, 'How can I voice you?  I\'m not opped!')
    voice = privmsgs.checkChannelCapability(voice, 'voice')
    
    def cycle(self, irc, msg, args, channel):
        """[<channel>] [<key>]

        If you have the #channel.op capability, this will cause the bot to
        "cycle", or PART and then JOIN the channel. If <key> is given, join
        the channel using that key. <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        key = privmsgs.getArgs(args, required=0, optional=1)
        if not key:
            key = None
        irc.queueMsg(ircmsgs.part(channel))
        irc.queueMsg(ircmsgs.join(channel, key))
    cycle = privmsgs.checkChannelCapability(cycle, 'op')

    def kban(self, irc, msg, args):
        """[<channel>] <nick> [<number of seconds to ban>]

        If you have the #channel.op capability, this will kickban <nick> for
        as many seconds as you specify, or else (if you specify 0 seconds or
        don't specify a number of seconds) it will ban the person indefinitely.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (bannedNick, length) = privmsgs.getArgs(args, optional=1)
        if bannedNick == irc.nick:
            irc.error(msg, 'I cowardly refuse to kickban myself.')
            return
        length = int(length or 0)
        try:
            bannedHostmask = irc.state.nickToHostmask(bannedNick)
        except KeyError:
            irc.error(msg, 'I haven\'t seen %s.' % bannedNick)
            return
        capability = ircdb.makeChannelCapability(channel, 'op')
        banmask = ircutils.banmask(bannedHostmask)
        if ircutils.hostmaskPatternEqual(banmask, irc.prefix):
            banmask = bannedHostmask
        if bannedNick == msg.nick or \
           (ircdb.checkCapability(msg.prefix, capability) \
           and not ircdb.checkCapability(bannedHostmask, capability)):
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

    def unban(self, irc, msg, args, channel):
        """[<channel>] <hostmask>

        Unbans <hostmask> on <channel>.  Especially useful for unbanning
        yourself when you get unexpectedly (or accidentally) banned from
        the channel.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        hostmask = privmsgs.getArgs(args)
        if irc.nick in irc.state.channels[channel].ops:
            irc.queueMsg(ircmsgs.unban(channel, hostmask))
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'How can I unban someone?  I\'m not opped.')
    unban = privmsgs.checkChannelCapability(unban, 'op')

    def lobotomize(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel.op capability, this will "lobotomize" the
        bot, making it silent and unanswering to all requests made in the
        channel. <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        ircdb.channels.getChannel(channel).lobotomized = True
        irc.reply(msg, conf.replySuccess)
    lobotomize = privmsgs.checkChannelCapability(lobotomize, 'op')

    def unlobotomize(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel.op capability, this will unlobotomize the bot,
        making it respond to requests made in the channel again.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        ircdb.channels.getChannel(channel).lobotomized = False
        irc.reply(msg, conf.replySuccess)
    unlobotomize = privmsgs.checkChannelCapability(unlobotomize, 'op')

    def permban(self, irc, msg, args, channel):
        """[<channel>] <nick|hostmask>

        If you have the #channel.op capability, this will effect a permanent
        (persistent) ban on the given <hostmask> (or the current hostmask
        associated with <nick>.  <channel> is only necessary if the message
        isn't sent in the channel itself.
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

        If you have the #channel.op capability, this will remove the permanent
        ban on <hostmask>.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        banmask = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.removeBan(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    unpermban = privmsgs.checkChannelCapability(unpermban, 'op')

    def ignore(self, irc, msg, args, channel):
        """[<channel>] <nick|hostmask>

        If you have the #channel.op capability, this will set a permanent
        (persistent) ignore on <hostmask> or the hostmask currently associated
        with <nick>. <channel> is only necessary if the message isn't sent in
        the channel itself.
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
    ignore = privmsgs.checkChannelCapability(ignore, 'op')

    def unignore(self, irc, msg, args, channel):
        """[<channel>] <hostmask>

        If you have the #channel.op capability, this will remove the permanent
        ignore on <hostmask> in the channel. <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        banmask = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.removeIgnore(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    unignore = privmsgs.checkChannelCapability(unignore, 'op')

    def ignores(self, irc, msg, args, channel):
        """[<channel>]

        Lists the hostmasks that the bot is ignoring on the given channel.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channelarg = privmsgs.getArgs(args, required=0, optional=1)
        channel = channelarg or channel
        c = ircdb.channels.getChannel(channel)
        if len(c.ignores) == 0:
            irc.reply(msg, 'I\'m not currently ignoring any hostmasks '
                           'in %r' % channel)
            return
        irc.reply(msg, utils.commaAndify(imap(repr, c.ignores)))
    ignores = privmsgs.checkChannelCapability(ignores, 'op')


    def addcapability(self, irc, msg, args, channel):
        """[<channel>] <name|hostmask> <capability>

        If you have the #channel.op capability, this will give the user
        currently identified as <name> (or the user to whom <hostmask> maps)
        the capability <capability> in the channel. <channel> is only necessary
        if the message isn't sent in the channel itself.
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
    addcapability = privmsgs.checkChannelCapability(addcapability,'op')

    def removecapability(self, irc, msg, args, channel):
        """[<channel>] <name|hostmask> <capability>

        If you have the #channel.op capability, this will take from the user
        currently identified as <name> (or the user to whom <hostmask> maps)
        the capability <capability> in the channel. <channel> is only necessary
        if the message isn't sent in the channel itself.
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
    removecapability = privmsgs.checkChannelCapability(removecapability, 'op')

    def setdefaultcapability(self, irc, msg, args, channel):
        """[<channel>] <default response to unknown capabilities> <True|False>

        If you have the #channel.op capability, this will set the default
        response to non-power-related (that is, not {op, halfop, voice}
        capabilities to be the value you give. <channel> is only necessary if
        the message isn't sent in the channel itself.
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
    setdefaultcapability = \
        privmsgs.checkChannelCapability(setdefaultcapability, 'op')

    def setcapability(self, irc, msg, args, channel):
        """[<channel>] <capability>

        If you have the #channel.op capability, this will add the channel
        capability <capability> for all users in the channel. <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        capability = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.addCapability(capability)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    setcapability = privmsgs.checkChannelCapability(setcapability, 'op')

    def unsetcapability(self, irc, msg, args, channel):
        """[<chanel>] <capability>

        If you have the #channel.op capability, this will unset the channel
        capability <capability> so each user's specific capability or the
        channel default capability will take precedence. <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        capability = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.removeCapability(capability)
        ircdb.channels.setChannel(channel, c)
        irc.reply(msg, conf.replySuccess)
    unsetcapability = privmsgs.checkChannelCapability(unsetcapability, 'op')

    def capabilities(self, irc, msg, args):
        """[<channel>]

        Returns the capabilities present on the <channel>. <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        c = ircdb.channels.getChannel(channel)
        irc.reply(msg, ', '.join(c.capabilities))

    def lobotomies(self, irc, msg, args):
        """takes no arguments

        Returns the channels in which this bot is lobotomized.
        """
        L = []
        for (channel, c) in ircdb.channels.iteritems():
            if c.lobotomized:
                L.append(channel)
        if L:
            s = 'I\'m currently lobotomized in %s.' % utils.commaAndify(L)
            irc.reply(msg, s)
        else:
            irc.reply(msg, 'I\'m not currently lobotomized in any channels.')
                        

Class = Channel

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
