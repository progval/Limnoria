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
Basic channel management commands.  Many of these commands require their caller
to have the <channel>.op capability.  This plugin is loaded by default.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.fix as fix

import sys
import time
import getopt
from itertools import imap

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.schedule as schedule
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

conf.registerPlugin('Channel')
conf.registerChannelValue(conf.supybot.plugins.Channel, 'alwaysRejoin',
    registry.Boolean(True, """Determines whether the bot will always try to
    rejoin a channel whenever it's kicked from the channel."""))

class Channel(callbacks.Privmsg):
    def haveOps(self, irc, channel, what):
        try:
            if irc.nick in irc.state.channels[channel].ops:
                return True
            else:
                irc.error('How can I %s?  I\'m not opped in %s.' %
                          (what, channel))
                return False
        except KeyError:
            irc.error('I don\'t seem to be in %s.' % channel)

    def doKick(self, irc, msg):
        channel = msg.args[0]
        if msg.args[1] == irc.nick:
            if self.registryValue('alwaysRejoin', channel):
                irc.sendMsg(ircmsgs.join(channel)) # Fix for keys.

    def mode(self, irc, msg, args, channel):
        """[<channel>] <mode> [<arg> ...]

        Sets the mode in <channel> to <mode>, sending the arguments given.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if not args:
            raise callbacks.ArgumentError
        if self.haveOps(irc, channel, 'change the mode'):
            irc.queueMsg(ircmsgs.mode(channel, args))
    mode = privmsgs.checkChannelCapability(mode, 'op')

    def limit(self, irc, msg, args, channel):
        """[<channel>] <limit>

        Sets the channel limit to <limit>.  If <limit> is 0, removes the
        channel limit.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        limit = privmsgs.getArgs(args)
        try:
            limit = int(limit)
            if limit < 0:
                raise ValueError
        except ValueError:
            irc.error('%r is not a positive integer.' % limit)
            return
        if limit:
            if self.haveOps(irc, channel, 'set the limit'):
                irc.queueMsg(ircmsgs.mode(channel, ['+l', limit]))
        else:
            if self.haveOps(irc, channel, 'unset the limit'):
                irc.queueMsg(ircmsgs.mode(channel, ['-l']))
    limit = privmsgs.checkChannelCapability(limit, 'op')

    def moderate(self, irc, msg, args, channel):
        """[<channel>]

        Sets +m on <channel>, making it so only ops and voiced users can
        send messages to the channel.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        if self.haveOps(irc, channel, 'moderate the channel'):
            irc.queueMsg(ircmsgs.mode(channel, ['+m']))
    moderate = privmsgs.checkChannelCapability(moderate, 'op')

    def unmoderate(self, irc, msg, args, channel):
        """[<channel>]

        Sets -m on <channel>, making it so everyone can
        send messages to the channel.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        if self.haveOps(irc, channel, 'unmoderate the channel'):
            irc.queueMsg(ircmsgs.mode(channel, ['-m']))
    unmoderate = privmsgs.checkChannelCapability(unmoderate, 'op')

    def key(self, irc, msg, args, channel):
        """[<channel>] [<key>]

        Sets the keyword in <channel> to <key>.  If <key> is not given, removes
        the keyword requirement to join <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        key = privmsgs.getArgs(args, required=0, optional=1)
        if key:
            if self.haveOps(irc, channel, 'set the keyword'):
                irc.queueMsg(ircmsgs.mode(channel, ['+k', key]))
        else:
            if self.haveOps(irc, channel, 'unset the keyword'):
                irc.queueMsg(ircmsgs.mode(channel, ['-k']))
    key = privmsgs.checkChannelCapability(key, 'op')

    def op(self, irc, msg, args, channel):
        """[<channel>] [<nick> ...]

        If you have the #channel,op capability, this will give all the <nick>s
        you provide ops.  If you don't provide any <nick>s, this will op you.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if not args:
            args = [msg.nick]
        if self.haveOps(irc, channel, 'op you'):
            irc.queueMsg(ircmsgs.ops(channel, args))
    op = privmsgs.checkChannelCapability(op, 'op')

    def halfop(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel,halfop capability, this will give all the
        <nick>s you provide halfops.  If you don't provide any <nick>s, this
        will give you halfops. <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        if not args:
            args = [msg.nick]
        if self.haveOps(irc, channel, 'halfop you'):
            irc.queueMsg(ircmsgs.halfops(channel, args))
    halfop = privmsgs.checkChannelCapability(halfop, 'halfop')

    def voice(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel,voice capability, this will voice all the
        <nick>s you provide.  If you don't provide any <nick>s, this will
        voice you. <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        if not args:
            args = [msg.nick]
        if self.haveOps(irc, channel, 'voice you'):
            irc.queueMsg(ircmsgs.voices(channel, args))
    voice = privmsgs.checkChannelCapability(voice, 'voice')

    def deop(self, irc, msg, args, channel):
        """[<channel>] [<nick> ...]

        If you have the #channel,op capability, this will remove operator
        privileges from all the nicks given.  If no nicks are given, removes
        operator privileges from the person sending the message.
        """
        if not args:
            args.append(msg.nick)
        if irc.nick in args:
            irc.error('I cowardly refuse to deop myself.  If you really want '
                      'me deopped, tell me to op you and then deop me '
                      'yourself.')
        elif self.haveOps(irc, channel, 'deop someone'):
            irc.queueMsg(ircmsgs.deops(channel, args))
    deop = privmsgs.checkChannelCapability(deop, 'op')

    def dehalfop(self, irc, msg, args, channel):
        """[<channel>] [<nick> ...]

        If you have the #channel,op capability, this will remove half-operator
        privileges from all the nicks given.  If no nicks are given, removes
        half-operator privileges from the person sending the message.
        """
        if not args:
            args.append(msg.nick)
        if irc.nick in args:
            irc.error('I cowardly refuse to dehalfop myself.  If you really '
                      'want me dehalfopped, tell me to op you and then '
                      'dehalfop me yourself.')
        elif self.haveOps(irc, channel, 'dehalfop someone'):
            irc.queueMsg(ircmsgs.dehalfops(channel, args))
    dehalfop = privmsgs.checkChannelCapability(dehalfop, 'op')

    def devoice(self, irc, msg, args, channel):
        """[<channel>] [<nick> ...]

        If you have the #channel,op capability, this will remove voice from all
        the nicks given.  If no nicks are given, removes voice from the person
        sending the message.
        """
        if not args:
            args.append(msg.nick)
        if irc.nick in args:
            irc.error('I cowardly refuse to devoice myself.  If you really '
                      'want me devoiced, tell me to op you and then devoice '
                      'me yourself.')
        elif self.haveOps(irc, channel, 'devoice someone'):
            irc.queueMsg(ircmsgs.devoices(channel, args))
    devoice = privmsgs.checkChannelCapability(devoice, 'op')

    def cycle(self, irc, msg, args, channel):
        """[<channel>] [<key>]

        If you have the #channel,op capability, this will cause the bot to
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

    def kick(self, irc, msg, args, channel):
        """[<channel>] <nick> [<reason>]

        Kicks <nick> from <channel> for <reason>.  If <reason> isn't given,
        uses the nick of the person making the command as the reason.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if self.haveOps(irc, channel, 'kick someone'):
            (nick, reason) = privmsgs.getArgs(args, optional=1)
            if nick not in irc.state.channels[channel].users:
                irc.error('%s isn\'t in %s.' % (nick, channel))
                return
            if not reason:
                reason = msg.nick
            kicklen = irc.state.supported.get('kicklen', sys.maxint)
            if len(reason) > kicklen:
                irc.error('The reason you gave is longer than the allowed '
                          'length for a KICK reason on this server.')
                return
            irc.queueMsg(ircmsgs.kick(channel, nick, reason))
    kick = privmsgs.checkChannelCapability(kick, 'op')

    def kban(self, irc, msg, args):
        """[<channel>] [--{exact,nick,user,host}] <nick> [<seconds>] [<reason>]

        If you have the #channel,op capability, this will kickban <nick> for
        as many seconds as you specify, or else (if you specify 0 seconds or
        don't specify a number of seconds) it will ban the person indefinitely.
        --exact bans only the exact hostmask; --nick bans just the nick;
        --user bans just the user, and --host bans just the host.  You can
        combine these options as you choose.  <reason> is a reason to give for
        the kick.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (optlist, rest) = getopt.getopt(args, '', ['exact', 'nick',
                                                   'user', 'host'])
        (bannedNick, length, reason) = privmsgs.getArgs(rest, optional=2)
        # Check that they're not trying to make us kickban ourself.
        if not ircutils.isNick(bannedNick):
            self.log.warning('%r tried to kban a non nick: %r',
                             msg.prefix, bannedNick)
            raise callbacks.ArgumentError
        elif bannedNick == irc.nick:
            self.log.warning('%r tried to make me kban myself.', msg.prefix)
            irc.error('I cowardly refuse to kickban myself.')
            return
        try:
            length = int(length or 0)
            if length < 0:
                irc.error('Ban length must be a non-negative integer.')
                return
        except ValueError:
            if reason:
                reason = ' '.join((length, reason))
                length = 0
            else:
                irc.error('Ban length must be a non-negative integer.')
                return
        if not reason:
            reason = msg.nick
        try:
            bannedHostmask = irc.state.nickToHostmask(bannedNick)
        except KeyError:
            irc.error('I haven\'t seen %s.' % bannedNick)
            return
        capability = ircdb.makeChannelCapability(channel, 'op')
        if optlist:
            (nick, user, host) = ircutils.splitHostmask(bannedHostmask)
            self.log.debug('*** nick: %s' % nick)
            self.log.debug('*** user: %s' % user)
            self.log.debug('*** host: %s' % host)
            bnick = '*'
            buser = '*'
            bhost = '*'
            for (option, _) in optlist:
                if option == '--nick':
                    bnick = nick
                elif option == '--user':
                    buser = user
                elif option == '--host':
                    bhost = host
                elif option == '--exact':
                    (bnick, buser, bhost) = \
                                   ircutils.splitHostmask(bannedHostmask)
            banmask = ircutils.joinHostmask(bnick, buser, bhost)
        else:
            banmask = ircutils.banmask(bannedHostmask)
        # Check (again) that they're not trying to make us kickban ourself.
        if ircutils.hostmaskPatternEqual(banmask, irc.prefix):
            if ircutils.hostmaskPatternEqual(banmask, irc.prefix):
                self.log.warning('%r tried to make me kban myself.',msg.prefix)
                irc.error('I cowardly refuse to ban myself.')
                return
            else:
                banmask = bannedHostmask
        # Now, let's actually get to it.  Check to make sure they have
        # #channel,op and the bannee doesn't have #channel,op; or that the
        # bannee and the banner are both the same person.
        def doBan():
            if bannedNick in irc.state.channels[channel].ops:
                irc.queueMsg(ircmsgs.deop(channel, bannedNick))
            irc.queueMsg(ircmsgs.ban(channel, banmask))
            irc.queueMsg(ircmsgs.kick(channel, bannedNick, reason))
            if length > 0:
                def f():
                    irc.queueMsg(ircmsgs.unban(channel, banmask))
                schedule.addEvent(f, time.time() + length)
        if bannedNick == msg.nick:
            if self.haveOps(irc, channel, 'kick or ban someone'):
                doBan()
        elif ircdb.checkCapability(msg.prefix, capability):
            if ircdb.checkCapability(bannedHostmask, capability):
                self.log.warning('%r tried to ban %r, but both have %s',
                                 msg.prefix, bannedHostmask, capability)
                irc.error('%s has %s too, you can\'t ban him/her/it.' %
                          (bannedNick, capability))
            elif self.haveOps(irc, channel, 'kick or ban someone'):
                doBan()
        else:
            self.log.warning('%r attempted kban without %s',
                             msg.prefix, capability)
            irc.errorNoCapability(capability)

    def unban(self, irc, msg, args, channel):
        """[<channel>] <hostmask>

        Unbans <hostmask> on <channel>.  Especially useful for unbanning
        yourself when you get unexpectedly (or accidentally) banned from
        the channel.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        hostmask = privmsgs.getArgs(args)
        if self.haveOps(irc, channel, 'unban someone'):
            irc.queueMsg(ircmsgs.unban(channel, hostmask))
    unban = privmsgs.checkChannelCapability(unban, 'op')

    def invite(self, irc, msg, args, channel):
        """[<channel>] <nick>

        If you have the #channel,op capability, this will invite <nick>
        to join <channel>. <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        nick = privmsgs.getArgs(args)
        if self.haveOps(irc, channel, 'invite someone'):
            irc.queueMsg(ircmsgs.invite(nick, channel))
    invite = privmsgs.checkChannelCapability(invite, 'op')

    def lobotomize(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel,op capability, this will "lobotomize" the
        bot, making it silent and unanswering to all requests made in the
        channel. <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        c = ircdb.channels.getChannel(channel)
        c.lobotomized = True
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    lobotomize = privmsgs.checkChannelCapability(lobotomize, 'op')

    def unlobotomize(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel,op capability, this will unlobotomize the bot,
        making it respond to requests made in the channel again.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        c = ircdb.channels.getChannel(channel)
        c.lobotomized = False
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    unlobotomize = privmsgs.checkChannelCapability(unlobotomize, 'op')

    def permban(self, irc, msg, args, channel):
        """[<channel>] <nick|hostmask>

        If you have the #channel,op capability, this will effect a permanent
        (persistent) ban from interacting with the bot on the given <hostmask>
        (or the current hostmask associated with <nick>.  <channel> is only
         necessary if the message isn't sent in the channel itself.
        """
        arg = privmsgs.getArgs(args)
        if ircutils.isNick(arg):
            banmask = ircutils.banmask(irc.state.nickToHostmask(arg))
        elif ircutils.isUserHostmask(arg):
            banmask = arg
        else:
            irc.error('That\'s not a valid nick or hostmask.')
            return
        c = ircdb.channels.getChannel(channel)
        c.addBan(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    permban = privmsgs.checkChannelCapability(permban, 'op')

    def unpermban(self, irc, msg, args, channel):
        """[<channel>] <hostmask>

        If you have the #channel,op capability, this will remove the permanent
        ban on <hostmask>.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        banmask = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.removeBan(banmask)
        ircdb.channels.setChannel(channel, c)
        #irc.queueMsg(ircmsgs.unban(channel, banmask))
        irc.replySuccess()
    unpermban = privmsgs.checkChannelCapability(unpermban, 'op')

    def permbans(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel,op capability, this will show you the
        current bans on #channel.
        """
        c = ircdb.channels.getChannel(channel)
        if c.bans:
            irc.reply(utils.commaAndify(map(utils.dqrepr, c.bans)))
        else:
            irc.reply('There are currently no permanent bans on %s' % channel)
    permbans = privmsgs.checkChannelCapability(permbans, 'op')

    def ignore(self, irc, msg, args, channel):
        """[<channel>] <nick|hostmask>

        If you have the #channel,op capability, this will set a permanent
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
            irc.error('That\'s not a valid nick or hostmask.')
            return
        c = ircdb.channels.getChannel(channel)
        c.addIgnore(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    ignore = privmsgs.checkChannelCapability(ignore, 'op')

    def unignore(self, irc, msg, args, channel):
        """[<channel>] <hostmask>

        If you have the #channel,op capability, this will remove the permanent
        ignore on <hostmask> in the channel. <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        banmask = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.removeIgnore(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
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
            s = 'I\'m not currently ignoring any hostmasks in %r' % channel
            irc.reply(s)
        else:
            L = sorted(c.ignores)
            irc.reply(utils.commaAndify(imap(repr, L)))
    ignores = privmsgs.checkChannelCapability(ignores, 'op')

    def addcapability(self, irc, msg, args, channel):
        """[<channel>] <name|hostmask> <capability>

        If you have the #channel,op capability, this will give the user
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
            irc.replySuccess()
        except KeyError:
            irc.errorNoUser()
    addcapability = privmsgs.checkChannelCapability(addcapability,'op')

    def removecapability(self, irc, msg, args, channel):
        """[<channel>] <name|hostmask> <capability>

        If you have the #channel,op capability, this will take from the user
        currently identified as <name> (or the user to whom <hostmask> maps)
        the capability <capability> in the channel. <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        (name, capability) = privmsgs.getArgs(args, 2)
        capability = ircdb.makeChannelCapability(channel, capability)
        try:
            id = ircdb.users.getUserId(name)
        except KeyError:
            irc.errorNoUser()
            return
        user = ircdb.users.getUser(id)
        try:
            user.removeCapability(capability)
        except KeyError:
            irc.error('That user doesn\'t have the %s capability.'%capability)
            return
        ircdb.users.setUser(id, user)
        irc.replySuccess()
    removecapability = privmsgs.checkChannelCapability(removecapability, 'op')

    def setdefaultcapability(self, irc, msg, args, channel):
        """[<channel>] <default response to unknown capabilities> <True|False>

        If you have the #channel,op capability, this will set the default
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
            irc.error(s)
            return
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    setdefaultcapability = \
        privmsgs.checkChannelCapability(setdefaultcapability, 'op')

    def setcapability(self, irc, msg, args, channel):
        """[<channel>] <capability>

        If you have the #channel,op capability, this will add the channel
        capability <capability> for all users in the channel. <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        capability = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        c.addCapability(capability)
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    setcapability = privmsgs.checkChannelCapability(setcapability, 'op')

    def unsetcapability(self, irc, msg, args, channel):
        """[<channel>] <capability>

        If you have the #channel,op capability, this will unset the channel
        capability <capability> so each user's specific capability or the
        channel default capability will take precedence. <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        capability = privmsgs.getArgs(args)
        c = ircdb.channels.getChannel(channel)
        try:
            c.removeCapability(capability)
            ircdb.channels.setChannel(channel, c)
            irc.replySuccess()
        except KeyError:
            irc.error('I do not know about that channel capability.')
    unsetcapability = privmsgs.checkChannelCapability(unsetcapability, 'op')

    def capabilities(self, irc, msg, args):
        """[<channel>]

        Returns the capabilities present on the <channel>. <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        c = ircdb.channels.getChannel(channel)
        L = sorted(c.capabilities)
        irc.reply('[%s]' % '; '.join(L))

    def lobotomies(self, irc, msg, args):
        """takes no arguments

        Returns the channels in which this bot is lobotomized.
        """
        L = []
        for (channel, c) in ircdb.channels.iteritems():
            if c.lobotomized:
                L.append(channel)
        if L:
            L.sort()
            s = 'I\'m currently lobotomized in %s.' % utils.commaAndify(L)
            irc.reply(s)
        else:
            irc.reply('I\'m not currently lobotomized in any channels.')

    def nicks(self, irc, msg, args):
        """[<channel>]

        Returns the nicks in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        L = list(irc.state.channels[channel].users)
        utils.sortBy(str.lower, L)
        irc.reply(utils.commaAndify(L))


Class = Channel

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
