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
import supybot.commands as commands
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

    def mode(self, irc, msg, args, channel, mode):
        """[<channel>] <mode> [<arg> ...]

        Sets the mode in <channel> to <mode>, sending the arguments given.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if self.haveOps(irc, channel, 'change the mode'):
            irc.queueMsg(ircmsgs.mode(channel, mode))
    mode = commands.wrap(mode, [('channel', 'op'), 'something'])

    def limit(self, irc, msg, args, channel, limit):
        """[<channel>] <limit>

        Sets the channel limit to <limit>.  If <limit> is 0, removes the
        channel limit.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        if limit < 0:
            irc.error('%r is not a positive integer.' % limit, Raise=True)
        if limit:
            if self.haveOps(irc, channel, 'set the limit'):
                irc.queueMsg(ircmsgs.mode(channel, ['+l', limit]))
        else:
            if self.haveOps(irc, channel, 'unset the limit'):
                irc.queueMsg(ircmsgs.mode(channel, ['-l']))
    limit = commands.wrap(mode, [('channel', 'op'), 'int'])

    def moderate(self, irc, msg, args, channel):
        """[<channel>]

        Sets +m on <channel>, making it so only ops and voiced users can
        send messages to the channel.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        if self.haveOps(irc, channel, 'moderate the channel'):
            irc.queueMsg(ircmsgs.mode(channel, ['+m']))
    moderate = commands.wrap(moderate, [('channel', 'op')])

    def unmoderate(self, irc, msg, args, channel):
        """[<channel>]

        Sets -m on <channel>, making it so everyone can
        send messages to the channel.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        if self.haveOps(irc, channel, 'unmoderate the channel'):
            irc.queueMsg(ircmsgs.mode(channel, ['-m']))
    unmoderate = commands.wrap(unmoderate, [('channel', 'op')])

    def key(self, irc, msg, args, channel, key):
        """[<channel>] [<key>]

        Sets the keyword in <channel> to <key>.  If <key> is not given, removes
        the keyword requirement to join <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        if key:
            if self.haveOps(irc, channel, 'set the keyword'):
                irc.queueMsg(ircmsgs.mode(channel, ['+k', key]))
        else:
            if self.haveOps(irc, channel, 'unset the keyword'):
                irc.queueMsg(ircmsgs.mode(channel, ['-k']))
    key = commands.wrap(key, [('channel', 'op')], ['something'])

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
    op = commands.wrap(op, [('channel', 'op')])

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
    halfop = commands.wrap(halfop, [('channel', 'halfop')])

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
    voice = commands.wrap(voice, [('channel', 'voice')])

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
    deop = commands.wrap(deop, [('channel', 'op')])

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
    dehalfop = commands.wrap(dehalfop, [('channel', 'halfop')])

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
    devoice = commands.wrap(devoice, [('channel', 'voice')])

    def cycle(self, irc, msg, args, channel, key):
        """[<channel>] [<key>]

        If you have the #channel,op capability, this will cause the bot to
        "cycle", or PART and then JOIN the channel. If <key> is given, join
        the channel using that key. <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        if not key:
            key = None
        irc.queueMsg(ircmsgs.part(channel))
        irc.queueMsg(ircmsgs.join(channel, key))
    cycle = commands.wrap(cycle, [('channel', 'op')], ['something'])

    def kick(self, irc, msg, args, channel, nick, reason):
        """[<channel>] <nick> [<reason>]

        Kicks <nick> from <channel> for <reason>.  If <reason> isn't given,
        uses the nick of the person making the command as the reason.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if self.haveOps(irc, channel, 'kick someone'):
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
    kick = commands.wrap(kick, [('channel', 'op'), 'something'], ['something'])

    def kban(self, irc, msg, args, channel, bannedNick, length, reason, *optlist):
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
        # Check that they're not trying to make us kickban ourself.
        self.log.critical('In kban')
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
                if option == 'nick':
                    bnick = nick
                elif option == 'user':
                    buser = user
                elif option == 'host':
                    bhost = host
                elif option == 'exact':
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
            exact,nick,user,host
    kban = \
        commands.wrap(kban, ['channel', 'something'],
                      [('expiry', 0), 'something'],
                      getopts={'exact': None,
                               'nick': None,
                               'user': None,
                               'host': None})

    def unban(self, irc, msg, args, channel, hostmask):
        """[<channel>] <hostmask>

        Unbans <hostmask> on <channel>.  Especially useful for unbanning
        yourself when you get unexpectedly (or accidentally) banned from
        the channel.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        if self.haveOps(irc, channel, 'unban someone'):
            irc.queueMsg(ircmsgs.unban(channel, hostmask))
    unban = commands.wrap(unban, [('channel', 'op'), 'hostmask'])

    def invite(self, irc, msg, args, channel, nick):
        """[<channel>] <nick>

        If you have the #channel,op capability, this will invite <nick>
        to join <channel>. <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        if self.haveOps(irc, channel, 'invite someone'):
            irc.queueMsg(ircmsgs.invite(nick, channel))
    invite = commands.wrap(invite, [('channel', 'op'), 'something'])

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
    lobotomize = commands.wrap(lobotomize, [('channel', 'op')])

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
    unlobotomize = commands.wrap(unlobotomize, [('channel', 'op')])

    def permban(self, irc, msg, args, channel, banmask, expires):
        """[<channel>] <nick|hostmask> [<expires>]

        If you have the #channel,op capability, this will effect a permanent
        (persistent) ban from interacting with the bot on the given <hostmask>
        (or the current hostmask associated with <nick>.  Other plugins may
        enforce this ban by actually banning users with matching hostmasks when
        they join.  <expires> is an optional argument specifying when (in
        "seconds from now") the ban should expire; if none is given, the ban
        will never automatically expire. <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        c = ircdb.channels.getChannel(channel)
        c.addBan(banmask, expires)
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    permban = \
        commands.wrap(permban, [('channel', 'op'), 'banmask', ('expiry', 0)])

    def unpermban(self, irc, msg, args, channel, banmask):
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
    unpermban = commands.wrap(unpermban, [('channel', 'op'), 'banmask'])

    def permbans(self, irc, msg, args, channel):
        """[<channel>]

        If you have the #channel,op capability, this will show you the
        current bans on #channel.
        """
        # XXX Add the expirations.
        c = ircdb.channels.getChannel(channel)
        if c.bans:
            irc.reply(utils.commaAndify(map(utils.dqrepr, c.bans)))
        else:
            irc.reply('There are currently no permanent bans on %s' % channel)
    permbans = commands.wrap(permbans, [('channel', 'op')])

    def ignore(self, irc, msg, args, channel, banmask, expires):
        """[<channel>] <nick|hostmask> [<expires>]

        If you have the #channel,op capability, this will set a permanent
        (persistent) ignore on <hostmask> or the hostmask currently associated
        with <nick>.  <expires> is an optional argument specifying when (in
        "seconds from now") the ignore will expire; if it isn't given, the
        ignore will never automatically expire.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        c = ircdb.channels.getChannel(channel)
        c.addIgnore(banmask, expires)
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    ignore = \
            commands.wrap(ignore,[('channel', 'op'), 'banmask', ('expiry', 0)])

    def unignore(self, irc, msg, args, channel, banmask):
        """[<channel>] <hostmask>

        If you have the #channel,op capability, this will remove the permanent
        ignore on <hostmask> in the channel. <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        c = ircdb.channels.getChannel(channel)
        c.removeIgnore(banmask)
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    unignore = commands.wrap(unignore, [('channel', 'op'), 'something'])

    def ignores(self, irc, msg, args, channel):
        """[<channel>]

        Lists the hostmasks that the bot is ignoring on the given channel.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        # XXX Add the expirations.
        c = ircdb.channels.getChannel(channel)
        if len(c.ignores) == 0:
            s = 'I\'m not currently ignoring any hostmasks in %r' % channel
            irc.reply(s)
        else:
            L = sorted(c.ignores)
            irc.reply(utils.commaAndify(imap(repr, L)))
    ignores = commands.wrap(ignores, [('channel', 'op')])

    def addcapability(self, irc, msg, args, channel, hostmask, capabilities):
        """[<channel>] <name|hostmask> <capability> [<capability> ...]

        If you have the #channel,op capability, this will give the user
        currently identified as <name> (or the user to whom <hostmask> maps)
        the capability <capability> in the channel. <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        try:
            id = ircdb.users.getUserId(hostmask)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.errorNoUser()
        for c in capabilities.split():
            c = ircdb.makeChannelCapability(channel, c)
            user.addCapability(c)
        ircdb.users.setUser(id, user)
        irc.replySuccess()
    addcapability = \
        commands.wrap(addcapability,
                      [('channel', 'op'), 'hostmask', 'something'])

    def removecapability(self, irc, msg, args, channel, hostmask, capabilities):
        """[<channel>] <name|hostmask> <capability> [<capability> ...]

        If you have the #channel,op capability, this will take from the user
        currently identified as <name> (or the user to whom <hostmask> maps)
        the capability <capability> in the channel. <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        try:
            id = ircdb.users.getUserId(hostmask)
        except KeyError:
            irc.errorNoUser()
            return
        user = ircdb.users.getUser(id)
        fail = []
        for c in capabilities.split():
            cap = ircdb.makeChannelCapability(channel, c)
            try:
                user.removeCapability(cap)
            except KeyError:
                fail.append(c)
        ircdb.users.setUser(id, user)
        if fail:
            irc.error('That user didn\'t have the %s %s.' %
                      (utils.commaAndify(fail),
                       utils.pluralize('capability', len(fail))), Raise=True)
        irc.replySuccess()
    removecapability = \
        commands.wrap(removecapability,
                      [('channel', 'op'), 'hostmask', 'something'])

    def setdefaultcapability(self, irc, msg, args, channel, v):
        """[<channel>] {True|False}

        If you have the #channel,op capability, this will set the default
        response to non-power-related (that is, not {op, halfop, voice}
        capabilities to be the value you give. <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        c = ircdb.channels.getChannel(channel)
        if v:
            c.setDefaultCapability(True)
        else:
            c.setDefaultCapability(False)
        ircdb.channels.setChannel(channel, c)
        irc.replySuccess()
    setdefaultcapability = \
        commands.wrap(setdefaultcapability, [('channel', 'op'), 'boolean'])

    def setcapability(self, irc, msg, args, channel, capabilities):
        """[<channel>] <capability> [<capability> ...]

        If you have the #channel,op capability, this will add the channel
        capability <capability> for all users in the channel. <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        chan = ircdb.channels.getChannel(channel)
        for c in capabilities.split():
            chan.addCapability(c)
        ircdb.channels.setChannel(channel, chan)
        irc.replySuccess()
    setcapability = \
        commands.wrap(setcapability, [('channel', 'op'), 'something'])

    def unsetcapability(self, irc, msg, args, channel, capabilities):
        """[<channel>] <capability> [<capability> ...]

        If you have the #channel,op capability, this will unset the channel
        capability <capability> so each user's specific capability or the
        channel default capability will take precedence. <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        chan = ircdb.channels.getChannel(channel)
        fail = []
        for c in capabilities.split():
            try:
                chan.removeCapability(c)
            except KeyError:
                fail.append(c)
        ircdb.channels.setChannel(channel, chan)
        if fail:
            irc.error('I do not know about the %s %s.' %
                      (utils.commaAndify(fail),
                       utils.pluralize('capability', len(fail))), Raise=True)
        irc.replySuccess()
    unsetcapability = \
        commands.wrap(unsetcapability, [('channel', 'op'), 'something'])

    def capabilities(self, irc, msg, args, channel):
        """[<channel>]

        Returns the capabilities present on the <channel>. <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        c = ircdb.channels.getChannel(channel)
        L = sorted(c.capabilities)
        irc.reply('[%s]' % '; '.join(L))
    capabilities = commands.wrap(capabilities, ['channel'])

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

    def nicks(self, irc, msg, args, channel):
        """[<channel>]

        Returns the nicks in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        L = list(irc.state.channels[channel].users)
        utils.sortBy(str.lower, L)
        irc.reply(utils.commaAndify(L))
    nicks = commands.wrap(nicks, ['channel'])

    def alertOps(self, irc, channel, s, frm=None):
        """Internal message for notifying all the #channel,ops in a channel of
        a given situation."""
        capability = ircdb.makeChannelCapability(channel, 'op')
        s = 'Alert to all %s ops: %s' % (channel, s)
        if frm is not None:
            s += ' (from %s)' % frm
        for nick in irc.state.channels[channel].users:
            hostmask = irc.state.nickToHostmask(nick)
            if ircdb.checkCapability(hostmask, capability):
                irc.reply(s, to=nick, private=True)

    def alert(self, irc, msg, args, channel):
        """[<channel>] <text>

        Sends <text> to all the users in <channel> who have the <channel>,op
        capability.
        """
        text = privmsgs.getArgs(args)
        self.alertOps(irc, channel, text, frm=msg.nick)
    alert = privmsgs.checkChannelCapability(alert, 'op')


Class = Channel

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
