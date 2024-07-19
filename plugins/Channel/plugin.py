###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009-2012, James McCoy
# Copyright (c) 2010-2021, Valentin Lorentz
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

import sys
import fnmatch
import time

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.schedule as schedule
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Channel')

class Channel(callbacks.Plugin):
    """This plugin provides various commands for channel management, such
    as setting modes and channel-wide bans/ignores/capabilities. This is
    a core Supybot plugin that should not be removed!"""

    def __init__(self, irc):
        self.__parent = super(Channel, self)
        self.__parent.__init__(irc)
        self.invites = {}

    def doKick(self, irc, msg):
        channel = msg.channel
        network = irc.network
        if msg.args[1] == irc.nick:
            if self.registryValue('alwaysRejoin', channel, network):
                delay = self.registryValue('rejoinDelay', channel, network)
                networkGroup = conf.supybot.networks.get(irc.network)
                if delay:
                    def f():
                        irc.sendMsg(networkGroup.channels.join(channel))
                    schedule.addEvent(f, time.time() + delay)
                    self.log.info('Kicked from %s @ %s by %s. '
                                  'Rejoining after %s seconds.',
                                  channel, network, msg.prefix, delay)
                else:
                    self.log.info('Kicked from %s @ %s by %s. Rejoining.',
                                  channel, network, msg.prefix)
                    irc.sendMsg(networkGroup.channels.join(channel))
            else:
                self.log.info('Kicked from %s @ %s by %s. Not auto-rejoining.',
                        channel, network, msg.prefix)

    def _sendMsg(self, irc, msg):
        irc.queueMsg(msg)
        irc.noReply()

    def _sendMsgs(self, irc, nicks, f):
        numModes = irc.state.supported.get('modes', 1)
        if numModes is None:
            # No limit enforced by the server, we're setting one ourselves.
            numModes = 5
        for i in range(0, len(nicks), numModes):
            irc.queueMsg(f(nicks[i:i + numModes]))
        irc.noReply()

    @internationalizeDocstring
    def mode(self, irc, msg, args, channel, modes):
        """[<channel>] <mode> [<arg> ...]

        Sets the mode in <channel> to <mode>, sending the arguments given.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        self._sendMsg(irc, ircmsgs.mode(channel, modes))
    mode = wrap(mode, ['op', ('haveHalfop+', _('change the mode')), many('something')])

    @internationalizeDocstring
    def limit(self, irc, msg, args, channel, limit):
        """[<channel>] [<limit>]

        Sets the channel limit to <limit>.  If <limit> is 0, or isn't given,
        removes the channel limit.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        if limit:
            self._sendMsg(irc, ircmsgs.mode(channel, ['+l', limit]))
        else:
            self._sendMsg(irc, ircmsgs.mode(channel, ['-l']))
    limit = wrap(limit, ['op', ('haveOp', _('change the limit')),
                        additional('nonNegativeInt', 0)])

    @internationalizeDocstring
    def moderate(self, irc, msg, args, channel):
        """[<channel>]

        Sets +m on <channel>, making it so only ops and voiced users can
        send messages to the channel.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        self._sendMsg(irc, ircmsgs.mode(channel, ['+m']))
    moderate = wrap(moderate, ['op', ('haveHalfop+', _('moderate the channel'))])

    @internationalizeDocstring
    def unmoderate(self, irc, msg, args, channel):
        """[<channel>]

        Sets -m on <channel>, making it so everyone can
        send messages to the channel.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        self._sendMsg(irc, ircmsgs.mode(channel, ['-m']))
    unmoderate = wrap(unmoderate, ['op', ('haveHalfop+',
                                   _('unmoderate the channel'))])

    @internationalizeDocstring
    def key(self, irc, msg, args, channel, key):
        """[<channel>] [<key>]

        Sets the keyword in <channel> to <key>.  If <key> is not given, removes
        the keyword requirement to join <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        networkGroup = conf.supybot.networks.get(irc.network)
        networkGroup.channels.key.get(channel).setValue(key)
        if key:
            self._sendMsg(irc, ircmsgs.mode(channel, ['+k', key]))
        else:
            self._sendMsg(irc, ircmsgs.mode(channel, ['-k']))
    key = wrap(key, ['op', ('haveHalfop+', _('change the keyword')),
                     additional('somethingWithoutSpaces', '')])

    @internationalizeDocstring
    def op(self, irc, msg, args, channel, nicks):
        """[<channel>] [<nick> ...]

        If you have the #channel,op capability, this will give all the <nick>s
        you provide ops.  If you don't provide any <nick>s, this will op you.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if not nicks:
            nicks = [msg.nick]
        def f(L):
            return ircmsgs.ops(channel, L)
        self._sendMsgs(irc, nicks, f)
    op = wrap(op, ['op', ('haveOp', _('op someone')), any('nickInChannel')])

    @internationalizeDocstring
    def halfop(self, irc, msg, args, channel, nicks):
        """[<channel>] [<nick> ...]

        If you have the #channel,halfop capability, this will give all the
        <nick>s you provide halfops.  If you don't provide any <nick>s, this
        will give you halfops. <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        if not nicks:
            nicks = [msg.nick]
        def f(L):
            return ircmsgs.halfops(channel, L)
        self._sendMsgs(irc, nicks, f)
    halfop = wrap(halfop, ['halfop', ('haveOp', _('halfop someone')),
                           any('nickInChannel')])

    def _voice(self, irc, msg, args, channel, nicks, fn):
        if nicks:
            if len(nicks) == 1 and msg.nick in nicks:
                capability = 'voice'
            else:
                capability = 'op'
        else:
            nicks = [msg.nick]
            capability = 'voice'
        capability = ircdb.makeChannelCapability(channel, capability)
        if ircdb.checkCapability(msg.prefix, capability):
            def f(L):
                return fn(channel, L)
            self._sendMsgs(irc, nicks, f)
        else:
            irc.errorNoCapability(capability)

    def voice(self, irc, msg, args, channel, nicks):
        """[<channel>] [<nick> ...]

        If you have the #channel,voice capability, this will voice all the
        <nick>s you provide.  If you don't provide any <nick>s, this will
        voice you. <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        self._voice(irc, msg, args, channel, nicks, ircmsgs.voices)
    voice = wrap(voice, ['channel', ('haveHalfop+', _('voice someone')),
                         any('nickInChannel')])

    @internationalizeDocstring
    def deop(self, irc, msg, args, channel, nicks):
        """[<channel>] [<nick> ...]

        If you have the #channel,op capability, this will remove operator
        privileges from all the nicks given.  If no nicks are given, removes
        operator privileges from the person sending the message.
        """
        if irc.nick in nicks:
            irc.error(_('I cowardly refuse to deop myself.  If you really '
                      'want me deopped, tell me to op you and then deop me '
                      'yourself.'), Raise=True)
        if not nicks:
            nicks = [msg.nick]
        def f(L):
            return ircmsgs.deops(channel, L)
        self._sendMsgs(irc, nicks, f)
    deop = wrap(deop, ['op', ('haveOp', _('deop someone')),
                       any('nickInChannel')])

    @internationalizeDocstring
    def dehalfop(self, irc, msg, args, channel, nicks):
        """[<channel>] [<nick> ...]

        If you have the #channel,op capability, this will remove half-operator
        privileges from all the nicks given.  If no nicks are given, removes
        half-operator privileges from the person sending the message.
        """
        if irc.nick in nicks:
            irc.error(_('I cowardly refuse to dehalfop myself.  If you really '
                      'want me dehalfopped, tell me to op you and then '
                      'dehalfop me yourself.'), Raise=True)
        if not nicks:
            nicks = [msg.nick]
        def f(L):
            return ircmsgs.dehalfops(channel, L)
        self._sendMsgs(irc, nicks, f)
    dehalfop = wrap(dehalfop, ['halfop', ('haveOp', _('dehalfop someone')),
                               any('nickInChannel')])

    @internationalizeDocstring
    def devoice(self, irc, msg, args, channel, nicks):
        """[<channel>] [<nick> ...]

        If you have the #channel,op capability, this will remove voice from all
        the nicks given.  If no nicks are given, removes voice from the person
        sending the message.
        """
        self._voice(irc, msg, args, channel, nicks, ircmsgs.devoices)
    devoice = wrap(devoice, ['channel', ('haveOp', 'devoice someone'),
                             any('nickInChannel')])

    @internationalizeDocstring
    def cycle(self, irc, msg, args, channel, reason):
        """[<channel>] [<reason>]

        If you have the #channel,op capability, this will cause the bot to
        "cycle", or PART and then JOIN the channel. <channel> is only necessary
        if the message isn't sent in the channel itself. If <reason> is not
        specified, the default part message specified in
        supybot.plugins.Channel.partMsg will be used. No part message will be
        used if neither a cycle reason nor a default part message is given.
        """
        reason = (reason or self.registryValue("partMsg", channel, irc.network))
        reason = ircutils.standardSubstitute(irc, msg, reason)
        self._sendMsg(irc, ircmsgs.part(channel, reason))
        networkGroup = conf.supybot.networks.get(irc.network)
        self._sendMsg(irc, networkGroup.channels.join(channel))
    cycle = wrap(cycle, ['op', additional('text')])

    @internationalizeDocstring
    def kick(self, irc, msg, args, channel, nicks, reason):
        """[<channel>] <nick>[, <nick>, ...] [<reason>]

        Kicks <nick>(s) from <channel> for <reason>.  If <reason> isn't given,
        uses the nick of the person making the command as the reason.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if utils.iter.any(lambda n: ircutils.strEqual(n, irc.nick), nicks):
            irc.error(_('I cowardly refuse to kick myself.'), Raise=True)
        if not reason:
            reason = msg.nick
        kicklen = irc.state.supported.get('kicklen', sys.maxsize)
        if len(reason) > kicklen:
            irc.error(_('The reason you gave is longer than the allowed '
                      'length for a KICK reason on this server.'),
                      Raise=True)
        for nick in nicks:
            self._sendMsg(irc, ircmsgs.kick(channel, nick, reason))
    kick = wrap(kick, ['op', ('haveHalfop+', _('kick someone')),
                       commalist('nickInChannel'), additional('text')])

    @internationalizeDocstring
    def kban(self, irc, msg, args,
             channel, optlist, bannedNick, expiry, reason):
        """[<channel>] [--{exact,nick,user,host,account}] <nick> [<seconds>] [<reason>]

        If you have the #channel,op capability, this will kickban <nick> for
        as many seconds as you specify, or else (if you specify 0 seconds or
        don't specify a number of seconds) it will ban the person indefinitely.
        --exact bans only the exact hostmask; --nick bans just the nick;
        --user bans just the user, and --host bans just the host
        You can combine the --nick, --user, and --host options as you choose.
        If --account is provided and the user is logged in and the network
        supports account bans, this will ban the user's account instead.
        <channel> is only necessary if the message isn't sent in the channel itself.
        """
        self._ban(irc, msg, args,
                channel, optlist, bannedNick, expiry, reason, True)
    kban = wrap(kban,
                ['op',
                 getopts({'exact':'', 'nick':'', 'user':'', 'host':'',
                          'account': ''}),
                 ('haveHalfop+', _('kick or ban someone')),
                 'nickInChannel',
                 optional('expiry', 0),
                 additional('text')])

    @internationalizeDocstring
    def iban(self, irc, msg, args,
             channel, optlist, bannedNick, expiry):
        """[<channel>] [--{exact,nick,user,host}] <nick> [<seconds>]

        If you have the #channel,op capability, this will ban <nick> for
        as many seconds as you specify, otherwise (if you specify 0 seconds or
        don't specify a number of seconds) it will ban the person indefinitely.
        --exact can be used to specify an exact hostmask.
        You can combine the --nick, --user, and --host options as you choose.
        If --account is provided and the user is logged in and the network
        supports account bans, this will ban the user's account instead.
        <channel> is only necessary if the message isn't sent in the channel itself.
        """
        self._ban(irc, msg, args,
                channel, optlist, bannedNick, expiry, None, False)
    iban = wrap(iban,
                ['op',
                 getopts({'exact':'', 'nick':'', 'user':'', 'host':'',
                          'account': ''}),
                 ('haveHalfop+', _('ban someone')),
                 first('nick', 'hostmask'),
                 optional('expiry', 0)])

    def _ban(self, irc, msg, args,
            channel, optlist, target, expiry, reason, kick):
        # Check that they're not trying to make us kickban ourself.
        if irc.isNick(target):
            bannedNick = target
            try:
                bannedHostmask = irc.state.nickToHostmask(target)
                banmaskstyle = conf.supybot.protocols.irc.banmask
                banmasks = banmaskstyle.makeExtBanmasks(
                    bannedHostmask, [o[0] for o in optlist],
                    channel=channel, network=irc.network)
            except KeyError:
                if not conf.supybot.protocols.irc.strictRfc() and \
                        target.startswith('$'):
                    # Select the last part, or the whole target:
                    bannedNick = target.split(':')[-1]
                    bannedHostmask = target
                    banmasks = [bannedHostmask]
                else:
                    irc.error(format(_('I haven\'t seen %s.'), bannedNick), Raise=True)
        else:
            bannedNick = ircutils.nickFromHostmask(target)
            bannedHostmask = target
            banmasks = [bannedHostmask]
        if not irc.isNick(bannedNick):
            self.log.warning('%q tried to kban a non nick: %q',
                             msg.prefix, bannedNick)
            raise callbacks.ArgumentError
        elif bannedNick == irc.nick:
            if kick:
                self.log.warning('%q tried to make me kban myself.', msg.prefix)
                irc.error(_('I cowardly refuse to kickban myself.'))
            else:
                self.log.warning('%q tried to make me ban myself.', msg.prefix)
                irc.error(_('I cowardly refuse to ban myself.'))
            return
        if not reason:
            reason = msg.nick
        capability = ircdb.makeChannelCapability(channel, 'op')

        # Check (again) that they're not trying to make us kickban ourself.
        self_account_extban = ircutils.accountExtban(irc, irc.nick)
        for banmask in banmasks:
            if ircutils.hostmaskPatternEqual(banmask, irc.prefix):
                if ircutils.hostmaskPatternEqual(bannedHostmask, irc.prefix):
                    self.log.warning('%q tried to make me kban myself.',msg.prefix)
                    irc.error(_('I cowardly refuse to ban myself.'))
                    return
                else:
                    self.log.warning('Using exact hostmask since banmask would '
                                     'ban myself.')
                    banmasks = [bannedHostmask]
            elif self_account_extban is not None \
                    and banmask.lower() == self_account_extban.lower():
                self.log.warning('%q tried to make me kban myself.',msg.prefix)
                irc.error(_('I cowardly refuse to ban myself.'))
                return


        # Now, let's actually get to it.  Check to make sure they have
        # #channel,op and the bannee doesn't have #channel,op; or that the
        # bannee and the banner are both the same person.
        def doBan():
            if irc.state.channels[channel].isOp(bannedNick):
                irc.queueMsg(ircmsgs.deop(channel, bannedNick))
            irc.queueMsg(ircmsgs.bans(channel, banmasks))
            if kick:
                irc.queueMsg(ircmsgs.kick(channel, bannedNick, reason))
            if expiry > 0:
                def f():
                    if channel not in irc.state.channels:
                        return
                    remaining_banmasks = [
                        banmask
                        for banmask in banmasks
                        if banmask in irc.state.channels[channel].bans
                    ]
                    if remaining_banmasks:
                        irc.queueMsg(ircmsgs.unbans(
                            channel, remaining_banmasks))
                schedule.addEvent(f, expiry)
        if bannedNick == msg.nick:
            doBan()
        elif ircdb.checkCapability(msg.prefix, capability):
            if ircdb.checkCapability(bannedHostmask, capability) and \
                    not ircdb.checkCapability(msg.prefix, 'owner'):
                self.log.warning('%s tried to ban %q, but both have %s',
                                 msg.prefix, bannedHostmask, capability)
                irc.error(format(_('%s has %s too, you can\'t ban '
                                 'them.'), bannedNick, capability))
            else:
                doBan()
        else:
            self.log.warning('%q attempted kban without %s',
                             msg.prefix, capability)
            irc.errorNoCapability(capability)

    @internationalizeDocstring
    def unban(self, irc, msg, args, channel, hostmask):
        """[<channel>] [<hostmask|--all>]

        Unbans <hostmask> on <channel>.  If <hostmask> is not given, unbans
        any hostmask currently banned on <channel> that matches your current
        hostmask.  Especially useful for unbanning yourself when you get
        unexpectedly (or accidentally) banned from the channel.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        if hostmask == '--all':
            bans = irc.state.channels[channel].bans
            self._sendMsg(irc, ircmsgs.unbans(channel, bans))
        elif hostmask:
            self._sendMsg(irc, ircmsgs.unban(channel, hostmask))
        else:
            bans = []
            for banmask in irc.state.channels[channel].bans:
                if ircutils.hostmaskPatternEqual(banmask, msg.prefix):
                    bans.append(banmask)
            if bans:
                irc.queueMsg(ircmsgs.unbans(channel, bans))
                irc.replySuccess(format(_('All bans on %s matching %s '
                                        'have been removed.'),
                                        channel, msg.prefix))
            else:
                irc.error(_('No bans matching %s were found on %s.') %
                          (msg.prefix, channel))
    unban = wrap(unban, ['op',
                         ('haveHalfop+', _('unban someone')),
                         additional(
                             first('hostmask',
                                 ('literal', '--all')))])

    @internationalizeDocstring
    def listbans(self, irc, msg, args, channel):
        """[<channel>]

        List all bans on the channel.
        If <channel> is not given, it defaults to the current channel."""
        irc.replies(irc.state.channels[channel].bans or [_('No bans.')])
    listbans = wrap(listbans, ['channel'])

    @internationalizeDocstring
    def invite(self, irc, msg, args, channel, nick):
        """[<channel>] <nick>

        If you have the #channel,op capability, this will invite <nick>
        to join <channel>. <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        nick = nick or msg.nick
        self._sendMsg(irc, ircmsgs.invite(nick, channel))
        self.invites[(irc.getRealIrc(), ircutils.toLower(nick))] = irc
    invite = wrap(invite, ['op', ('haveHalfop+', _('invite someone')),
                           additional('nick')])

    def do341(self, irc, msg):
        (foo, nick, channel) = msg.args
        nick = ircutils.toLower(nick)
        replyIrc = self.invites.pop((irc, nick), None)
        if replyIrc is not None:
            self.log.info('Inviting %s to %s by command of %s.',
                          nick, channel, replyIrc.msg.prefix)
            replyIrc.replySuccess()
        else:
            self.log.info('Inviting %s to %s.', nick, channel)

    def do443(self, irc, msg):
        (foo, nick, channel, foo) = msg.args
        nick = ircutils.toLower(nick)
        replyIrc = self.invites.pop((irc, nick), None)
        if replyIrc is not None:
            replyIrc.error(format(_('%s is already in %s.'), nick, channel))

    def do401(self, irc, msg):
        nick = msg.args[1]
        nick = ircutils.toLower(nick)
        replyIrc = self.invites.pop((irc, nick), None)
        if replyIrc is not None:
            replyIrc.error(format(_('There is no %s on this network.'), nick))

    def do504(self, irc, msg):
        nick = msg.args[1]
        nick = ircutils.toLower(nick)
        replyIrc = self.invites.pop((irc, nick), None)
        if replyIrc is not None:
            replyIrc.error(format('There is no %s on this server.', nick))

    class lobotomy(callbacks.Commands):
        @internationalizeDocstring
        def add(self, irc, msg, args, channel):
            """[<channel>]

            If you have the #channel,op capability, this will "lobotomize" the
            bot, making it silent and unanswering to all requests made in the
            channel. <channel> is only necessary if the message isn't sent in
            the channel itself.
            """
            c = ircdb.channels.getChannel(channel)
            c.lobotomized = True
            ircdb.channels.setChannel(channel, c)
            irc.replySuccess()
        add = wrap(add, ['op'])

        @internationalizeDocstring
        def remove(self, irc, msg, args, channel):
            """[<channel>]

            If you have the #channel,op capability, this will unlobotomize the
            bot, making it respond to requests made in the channel again.
            <channel> is only necessary if the message isn't sent in the channel
            itself.
            """
            c = ircdb.channels.getChannel(channel)
            c.lobotomized = False
            ircdb.channels.setChannel(channel, c)
            irc.replySuccess()
        remove = wrap(remove, ['op'])

        @internationalizeDocstring
        def list(self, irc, msg, args):
            """takes no arguments

            Returns the channels in which this bot is lobotomized.
            """
            L = []
            for (channel, c) in ircdb.channels.items():
                if c.lobotomized:
                    chancap = ircdb.makeChannelCapability(channel, 'op')
                    if ircdb.checkCapability(msg.prefix, 'admin') or \
                       ircdb.checkCapability(msg.prefix, chancap) or \
                       (channel in irc.state.channels and \
                        msg.nick in irc.state.channels[channel].users):
                        L.append(channel)
            if L:
                L.sort()
                s = format(_('I\'m currently lobotomized in %L.'), L)
                irc.reply(s)
            else:
                irc.reply(_('I\'m not currently lobotomized in any channels '
                          'that you\'re in.'))
        list = wrap(list)

    class ban(callbacks.Commands):
        def hostmask(self, irc, msg, args, channel, banmask):
            """[<channel>] <banmask>

            Bans the <banmask> from the <channel>."""
            irc.queueMsg(ircmsgs.ban(channel, banmask))
        hostmask = wrap(hostmask, ['op', ('haveHalfop+', _('ban someone')), 'text'])

        @internationalizeDocstring
        def add(self, irc, msg, args, channel, banmasks, expires):
            """[<channel>] <nick|hostmask> [<expires>]

            If you have the #channel,op capability, this will effect a
            persistent ban from interacting with the bot on the given
            <hostmask> (or the current hostmask associated with <nick>).  Other
            plugins may enforce this ban by actually banning users with
            matching hostmasks when they join.  <expires> is an optional
            argument specifying when (in "seconds from now") the ban should
            expire; if none is given, the ban will never automatically expire.
            <channel> is only necessary if the message isn't sent in the
            channel itself.
            """
            c = ircdb.channels.getChannel(channel)
            if isinstance(banmasks, str):
                banmasks = [banmasks]
            for banmask in banmasks:
                c.addBan(banmask, expires)
            ircdb.channels.setChannel(channel, c)
            irc.replySuccess()
        add = wrap(add, ['op',
                         first('hostmask', 'extbanmasks'),
                         additional('expiry', 0)])

        @internationalizeDocstring
        def remove(self, irc, msg, args, channel, banmask):
            """[<channel>] <hostmask>

            If you have the #channel,op capability, this will remove the
            persistent ban on <hostmask>.  <channel> is only necessary if the
            message isn't sent in the channel itself.
            """
            c = ircdb.channels.getChannel(channel)
            try:
                c.removeBan(banmask)
                ircdb.channels.setChannel(channel, c)
                irc.replySuccess()
            except KeyError:
                irc.error(_('There are no persistent bans for that hostmask.'))
        remove = wrap(remove, ['op', 'hostmask'])

        @internationalizeDocstring
        def list(self, irc, msg, args, channel, mask):
            """[<channel>] [<mask>]

            If you have the #channel,op capability, this will show you the
            current persistent bans on the <channel> that match the given
            mask, if any (returns all of them otherwise).
            Note that you can use * as a wildcard on masks and \\* to match
            actual * in masks
            """
            all_bans = ircdb.channels.getChannel(channel).bans
            if mask:
                mask = mask.replace(r'\*', '[*]')
                filtered_bans = fnmatch.filter(all_bans, mask)
            else:
                filtered_bans = all_bans
            if filtered_bans:
                bans = []
                for ban in filtered_bans:
                    if all_bans[ban]:
                        bans.append(format(_('%q (expires %t)'),
                                           ban, all_bans[ban]))
                    else:
                        bans.append(format(_('%q (never expires)'),
                                           ban, all_bans[ban]))
                irc.reply(format('%L', bans))
            else:
                irc.reply(format(_('There are no persistent bans on %s.'),
                                 channel))
        list = wrap(list, ['op', optional('somethingWithoutSpaces')])

    class ignore(callbacks.Commands):
        @internationalizeDocstring
        def add(self, irc, msg, args, channel, banmask, expires):
            """[<channel>] <nick|hostmask> [<expires>]

            If you have the #channel,op capability, this will set a persistent
            ignore on <hostmask> or the hostmask currently
            associated with <nick>. <expires> is an optional argument
            specifying when (in "seconds from now") the ignore will expire; if
            it isn't given, the ignore will never automatically expire.
            <channel> is only necessary if the message isn't sent in the
            channel itself.
            """
            c = ircdb.channels.getChannel(channel)
            c.addIgnore(banmask, expires)
            ircdb.channels.setChannel(channel, c)
            irc.replySuccess()
        add = wrap(add, ['op', 'banmask', additional('expiry', 0)])

        @internationalizeDocstring
        def remove(self, irc, msg, args, channel, banmask):
            """[<channel>] <nick|hostmask>

            If you have the #channel,op capability, this will remove the
            persistent ignore on <hostmask> in the channel. <channel> is only
            necessary if the message isn't sent in the channel itself.
            """
            c = ircdb.channels.getChannel(channel)
            try:
                c.removeIgnore(banmask)
                ircdb.channels.setChannel(channel, c)
                irc.replySuccess()
            except KeyError:
                irc.error(_('There are no ignores for that hostmask.'))
        remove = wrap(remove, ['op', 'banmask'])

        @internationalizeDocstring
        def list(self, irc, msg, args, channel):
            """[<channel>]

            Lists the hostmasks that the bot is ignoring on the given channel.
            <channel> is only necessary if the message isn't sent in the
            channel itself.
            """
            # XXX Add the expirations.
            c = ircdb.channels.getChannel(channel)
            if len(c.ignores) == 0:
                s = format(_('I\'m not currently ignoring any hostmasks in '
                           '%q'), channel)
                irc.reply(s)
            else:
                L = sorted(c.ignores)
                irc.reply(utils.str.commaAndify(list(map(repr, L))))
        list = wrap(list, ['op'])

    class capability(callbacks.Commands):
        @internationalizeDocstring
        def add(self, irc, msg, args, channel, user, capabilities):
            """[<channel>] <nick|username> <capability> [<capability> ...]

            If you have the #channel,op capability, this will give the
            <username> (or the user to whom <nick> maps)
            the capability <capability> in the channel. <channel> is only
            necessary if the message isn't sent in the channel itself.
            """
            for c in capabilities.split():
                c = ircdb.makeChannelCapability(channel, c)
                user.addCapability(c)
            ircdb.users.setUser(user)
            irc.replySuccess()
        add = wrap(add, ['op', 'otherUser', 'capability'])

        @internationalizeDocstring
        def remove(self, irc, msg, args, channel, user, capabilities):
            """[<channel>] <name|hostmask> <capability> [<capability> ...]

            If you have the #channel,op capability, this will take from the
            user currently identified as <name> (or the user to whom <hostmask>
            maps) the capability <capability> in the channel. <channel> is only
            necessary if the message isn't sent in the channel itself.
            """
            fail = []
            for c in capabilities.split():
                cap = ircdb.makeChannelCapability(channel, c)
                try:
                    user.removeCapability(cap)
                except KeyError:
                    fail.append(c)
            ircdb.users.setUser(user)
            if fail:
                s = 'capability'
                if len(fail) > 1:
                    s = utils.str.pluralize(s)
                irc.error(format(_('That user didn\'t have the %L %s.'), fail,
                          s), Raise=True)
            irc.replySuccess()
        remove = wrap(remove, ['op', 'otherUser', 'capability'])

        # XXX This needs to be fix0red to be like Owner.defaultcapability.  Or
        # something else.  This is a horrible interface.
        @internationalizeDocstring
        def setdefault(self, irc, msg, args, channel, v):
            """[<channel>] {True|False}

            If you have the #channel,op capability, this will set the default
            response to non-power-related (that is, not {op, halfop, voice})
            capabilities to be the value you give. <channel> is only necessary
            if the message isn't sent in the channel itself.
            """
            c = ircdb.channels.getChannel(channel)
            if v:
                c.setDefaultCapability(True)
            else:
                c.setDefaultCapability(False)
            ircdb.channels.setChannel(channel, c)
            irc.replySuccess()
        setdefault = wrap(setdefault, ['op', 'boolean'])

        @internationalizeDocstring
        def set(self, irc, msg, args, channel, capabilities):
            """[<channel>] <capability> [<capability> ...]

            If you have the #channel,op capability, this will add the channel
            capability <capability> for all users in the channel. <channel> is
            only necessary if the message isn't sent in the channel itself.
            """
            chan = ircdb.channels.getChannel(channel)
            for c in capabilities:
                chan.addCapability(c)
            ircdb.channels.setChannel(channel, chan)
            irc.replySuccess()
        set = wrap(set, ['op', many('capability')])

        @internationalizeDocstring
        def unset(self, irc, msg, args, channel, capabilities):
            """[<channel>] <capability> [<capability> ...]

            If you have the #channel,op capability, this will unset the channel
            capability <capability> so each user's specific capability or the
            channel default capability will take precedence. <channel> is only
            necessary if the message isn't sent in the channel itself.
            """
            chan = ircdb.channels.getChannel(channel)
            fail = []
            for c in capabilities:
                try:
                    chan.removeCapability(c)
                except KeyError:
                    fail.append(c)
            ircdb.channels.setChannel(channel, chan)
            if fail:
                s = _('capability')
                if len(fail) > 1:
                    s = utils.str.pluralize(s)
                irc.error(format(_('I do not know about the %L %s.'), fail, s),
                          Raise=True)
            irc.replySuccess()
        unset = wrap(unset, ['op', many('capability')])

        @internationalizeDocstring
        def list(self, irc, msg, args, channel):
            """[<channel>]

            Returns the capabilities present on the <channel>. <channel> is
            only necessary if the message isn't sent in the channel itself.
            """
            c = ircdb.channels.getChannel(channel)
            L = sorted(c.capabilities)
            irc.reply(' '.join(L))
        list = wrap(list, ['channel'])

    @internationalizeDocstring
    def disable(self, irc, msg, args, channel, plugin, command):
        """[<channel>] [<plugin>] [<command>]

        If you have the #channel,op capability, this will disable the <command>
        in <channel>.  If <plugin> is provided, <command> will be disabled only
        for that plugin.  If only <plugin> is provided, all commands in the
        given plugin will be disabled.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        chan = ircdb.channels.getChannel(channel)
        failMsg = ''
        if plugin:
            s = '-%s' % plugin.name()
            if command:
                if plugin.isCommand(command):
                    s = '-%s.%s' % (plugin.name(), command)
                else:
                    failMsg = format(_('The %s plugin does not have a command '
                                     'called %s.'), plugin.name(), command)
        elif command:
            # findCallbackForCommand
            if list(filter(None, irc.findCallbacksForArgs([command]))):
                s = '-%s' % command
            else:
                failMsg = format(_('No plugin or command named %s could be '
                                 'found.'), command)
        else:
            raise callbacks.ArgumentError
        if failMsg:
            irc.error(failMsg)
        else:
            chan.addCapability(s)
            ircdb.channels.setChannel(channel, chan)
            irc.replySuccess()
    disable = wrap(disable, ['op',
                             optional(('plugin', False)),
                             additional('commandName')])

    @internationalizeDocstring
    def enable(self, irc, msg, args, channel, plugin, command):
        """[<channel>] [<plugin>] [<command>]

        If you have the #channel,op capability, this will enable the <command>
        in <channel> if it has been disabled.  If <plugin> is provided,
        <command> will be enabled only for that plugin.  If only <plugin> is
        provided, all commands in the given plugin will be enabled.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        chan = ircdb.channels.getChannel(channel)
        failMsg = ''
        if plugin:
            s = '-%s' % plugin.name()
            if command:
                if plugin.isCommand(command):
                    s = '-%s.%s' % (plugin.name(), command)
                else:
                    failMsg = format(_('The %s plugin does not have a command '
                                     'called %s.'), plugin.name(), command)
        elif command:
            # findCallbackForCommand
            if list(filter(None, irc.findCallbacksForArgs([command]))):
                s = '-%s' % command
            else:
                failMsg = format(_('No plugin or command named %s could be '
                                 'found.'), command)
        else:
            raise callbacks.ArgumentError
        if failMsg:
            irc.error(failMsg)
        else:
            fail = []
            try:
                chan.removeCapability(s)
            except KeyError:
                fail.append(s)
            ircdb.channels.setChannel(channel, chan)
            if fail:
                irc.error(format(_('%s was not disabled.'), s[1:]))
            else:
                irc.replySuccess()
    enable = wrap(enable, ['op',
                           optional(('plugin', False)),
                           additional('commandName')])

    @internationalizeDocstring
    def nicks(self, irc, msg, args, channel, optlist):
        """[<channel>] [--count]

        Returns the nicks in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself. Returns only the number of
        nicks if --count option is provided.
        """
        # Make sure we don't elicit information about private channels to
        # people or channels that shouldn't know. Someone is allowed if
        # any of these are true:
        # * the channel is not secret (mode +s),
        # * the request is sent to the channel itself (FIXME: what about
        #   channels without +n?),
        # * the requester is op,
        # * the request is not sent to a channel (or else everyone in the
        #   channel would see the response) and the requester is in the
        #   channel themselves
        capability = ircdb.makeChannelCapability(channel, 'op')
        if 's' in irc.state.channels[channel].modes and \
            msg.channel != channel and \
            not ircdb.checkCapability(msg.prefix, capability) and \
            (msg.channel or \
             msg.nick not in irc.state.channels[channel].users):
            irc.error(_('You don\'t have access to that information.'),
                    Raise=True)
        L = list(irc.state.channels[channel].users)
        keys = [option for (option, arg) in optlist]
        if 'count' not in keys:
            utils.sortBy(str.lower, L)
            private = self.registryValue("nicksInPrivate", channel, irc.network)
            irc.reply(utils.str.commaAndify(L), private=private)
        else:
            irc.reply(str(len(L)))
    nicks = wrap(nicks, ['inChannel',
                        getopts({'count':''})])

    @internationalizeDocstring
    def alertOps(self, irc, msg, channel, s, frm=None):
        """Internal message for notifying all the #channel,ops in a channel of
        a given situation."""
        capability = ircdb.makeChannelCapability(channel, 'op')
        s = format(_('Alert to all %s ops: %s'), channel, s)
        if frm is not None:
            s += format(_(' (from %s)'), frm)
        for nick in irc.state.channels[channel].users:
            prefix = irc.state.nicksToHostmasks.get(nick)
            if not prefix:
                continue
            if not ircdb.checkCapability(prefix, capability):
                continue
            irc.reply(s, to=nick, private=True)
        irc.replySuccess()

    @internationalizeDocstring
    def alert(self, irc, msg, args, channel, text):
        """[<channel>] <text>

        Sends <text> to all the users in <channel> who have the <channel>,op
        capability.
        """
        self.alertOps(irc, msg, channel, text, frm=msg.nick)
    alert = wrap(alert, ['inChannel', 'text'])

    @internationalizeDocstring
    def part(self, irc, msg, args, channel, reason):
        """[<channel>] [<reason>]

        Tells the bot to part the list of channels you give it.  <channel> is
        only necessary if you want the bot to part a channel other than the
        current channel.  If <reason> is specified, use it as the part
        message.  Otherwise, the default part message specified in
        supybot.plugins.Channel.partMsg will be used. No part message will be
        used if no default is configured.
        """
        channel = channel or msg.channel
        if not channel:
            irc.error(Raise=True)
        capability = ircdb.makeChannelCapability(channel, 'op')
        if not ircdb.checkCapabilities(msg.prefix, [capability, 'admin']):
            irc.errorNoCapability(capability, Raise=True)
        try:
            network = conf.supybot.networks.get(irc.network)
            network.channels().remove(channel)
        except KeyError:
            if channel not in irc.state.channels:
                # Not configured AND not in the channel
                irc.error(_('I\'m not in %s.') % channel, Raise=True)
        else:
            if channel not in irc.state.channels:
                # Configured, but not in the channel
                irc.reply(_('%s removed from configured join list.') % channel)
                return
        reason = (reason or self.registryValue("partMsg", channel, irc.network))
        reason = ircutils.standardSubstitute(irc, msg, reason)
        irc.queueMsg(ircmsgs.part(channel, reason))
        if msg.nick in irc.state.channels[channel].users:
            irc.noReply()
        else:
            irc.replySuccess()
    part = wrap(part, [optional('validChannel'), additional('text')])

Class = Channel

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
