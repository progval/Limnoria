###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2010, Valentin Lorentz
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
import time

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.schedule as schedule
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Admin')

class Admin(callbacks.Plugin):
    """This plugin provides access to administrative commands, such as
    adding capabilities, managing ignore lists, and joining channels.
    This is a core Supybot plugin that should not be removed!"""
    def __init__(self, irc):
        self.__parent = super(Admin, self)
        self.__parent.__init__(irc)
        self.joins = {}
        self.pendingNickChanges = {}

    @internationalizeDocstring
    def do437(self, irc, msg):
        """Nick/channel temporarily unavailable."""
        target = msg.args[0]
        t = time.time() + 30
        if irc.isChannel(target):
            # Let's schedule a rejoin.
            networkGroup = conf.supybot.networks.get(irc.network)
            def rejoin():
                irc.queueMsg(networkGroup.channels.join(target))
                # We don't need to schedule something because we'll get another
                # 437 when we try to join later.
            schedule.addEvent(rejoin, t)
            self.log.info('Scheduling a rejoin to %s at %s; '
                          'Channel temporarily unavailable.', target, t)
        else:
            irc = self.pendingNickChanges.get(irc, None)
            if irc is not None:
                def nick():
                    irc.queueMsg(ircmsgs.nick(target))
                schedule.addEvent(nick, t)
                self.log.info('Scheduling a nick change to %s at %s; '
                              'Nick temporarily unavailable.', target, t)
            else:
                self.log.debug('Got 437 without Admin.nick being called.')

    def do471(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc, msg) = self.joins.pop(channel)
            irc.error(_('Cannot join %s, it\'s full.') % channel)
        except KeyError:
            self.log.debug('Got 471 without Admin.join being called.')

    def do473(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc, msg) = self.joins.pop(channel)
            irc.error(_('Cannot join %s, I was not invited.') % channel)
        except KeyError:
            self.log.debug('Got 473 without Admin.join being called.')

    def do474(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc, msg) = self.joins.pop(channel)
            irc.error(_('Cannot join %s, I am banned.') % channel)
        except KeyError:
            self.log.debug('Got 474 without Admin.join being called.')

    def do475(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc, msg) = self.joins.pop(channel)
            irc.error(_('Cannot join %s, my keyword was wrong.') % channel)
        except KeyError:
            self.log.debug('Got 475 without Admin.join being called.')

    def do477(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc,msg) = self.joins.pop(channel)
            irc.error(_('Cannot join %s, I\'m not identified with '
                      'NickServ.') % channel)
        except KeyError:
            self.log.debug('Got 477 without Admin.join being called.')

    def do515(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc, msg) = self.joins.pop(channel)
            irc.error(_('Cannot join %s, I\'m not identified with '
                      'NickServ.') % channel)
        except KeyError:
            self.log.debug('Got 515 without Admin.join being called.')

    def doJoin(self, irc, msg):
        if msg.prefix == irc.prefix:
            try:
                del self.joins[msg.args[0]]
            except KeyError:
                s = 'Joined a channel without Admin.join being called.'
                self.log.debug(s)

    def doInvite(self, irc, msg):
        channel = msg.args[1]
        if channel not in irc.state.channels:
            if conf.supybot.alwaysJoinOnInvite.get(channel)() or \
               ircdb.checkCapability(msg.prefix, 'admin'):
                self.log.info('Invited to %s by %s.', channel, msg.prefix)
                networkGroup = conf.supybot.networks.get(irc.network)
                irc.queueMsg(networkGroup.channels.join(channel))
                conf.supybot.networks.get(irc.network).channels().add(channel)
            else:
                self.log.warning('Invited to %s by %s, but '
                                 'supybot.alwaysJoinOnInvite was False and '
                                 'the user lacked the "admin" capability.',
                                 channel, msg.prefix)

    @internationalizeDocstring
    def join(self, irc, msg, args, channel, key):
        """<channel> [<key>]

        Tell the bot to join the given channel.  If <key> is given, it is used
        when attempting to join the channel.
        """
        if not irc.isChannel(channel):
            irc.errorInvalid(_('channel'), channel, Raise=True)
        networkGroup = conf.supybot.networks.get(irc.network)
        networkGroup.channels().add(channel)
        if key:
            networkGroup.channels.key.get(channel).setValue(key)
        maxchannels = irc.state.supported.get('maxchannels', sys.maxsize)
        if len(irc.state.channels) + 1 > maxchannels:
            irc.error(_('I\'m already too close to maximum number of '
                      'channels for this network.'), Raise=True)
        irc.queueMsg(networkGroup.channels.join(channel))
        irc.noReply()
        self.joins[channel] = (irc, msg)
    join = wrap(join, ['validChannel', additional('something')])

    @internationalizeDocstring
    def channels(self, irc, msg, args):
        """takes no arguments

        Returns the channels the bot is on.
        """
        L = irc.state.channels.keys()
        if L:
            utils.sortBy(ircutils.toLower, L)
            irc.reply(format('%L', L), private=True)
        else:
            irc.reply(_('I\'m not currently in any channels.'))
    channels = wrap(channels)

    def do484(self, irc, msg):
        irc = self.pendingNickChanges.get(irc, None)
        if irc is not None:
            irc.error(_('My connection is restricted, I can\'t change nicks.'))
        else:
            self.log.debug('Got 484 without Admin.nick being called.')

    def do433(self, irc, msg):
        irc = self.pendingNickChanges.get(irc, None)
        if irc is not None:
            irc.error(_('Someone else is already using that nick.'))
        else:
            self.log.debug('Got 433 without Admin.nick being called.')

    def do435(self, irc, msg):
        irc = self.pendingNickChanges.get(irc, None)
        if irc is not None:
            irc.error(_('I can\'t change nick, I\'m currently banned in %s.') %
                      msg.args[2])
        else:
            self.log.debug('Got 435 without Admin.nick being called.')

    def do438(self, irc, msg):
        irc = self.pendingNickChanges.get(irc, None)
        if irc is not None:
            irc.error(format(_('I can\'t change nicks, the server said %q.'),
                      msg.args[2]), private=True)
        else:
            self.log.debug('Got 438 without Admin.nick being called.')

    def doNick(self, irc, msg):
        if msg.nick == irc.nick or msg.args[0] == irc.nick:
            try:
                del self.pendingNickChanges[irc]
            except KeyError:
                self.log.debug('Got NICK without Admin.nick being called.')

    @internationalizeDocstring
    def nick(self, irc, msg, args, nick, network):
        """[<nick>] [<network>]

        Changes the bot's nick to <nick>.  If no nick is given, returns the
        bot's current nick.
        """
        network = network or irc.network
        if nick:
            group = getattr(conf.supybot.networks, network)
            group.nick.setValue(nick)
            irc.queueMsg(ircmsgs.nick(nick))
            self.pendingNickChanges[irc.getRealIrc()] = irc
        else:
            irc.reply(irc.nick)
    nick = wrap(nick, [additional('nick'), additional('something')])

    class capability(callbacks.Commands):

        @internationalizeDocstring
        def add(self, irc, msg, args, user, capability):
            """<name|hostmask> <capability>

            Gives the user specified by <name> (or the user to whom <hostmask>
            currently maps) the specified capability <capability>
            """
            # Ok, the concepts that are important with capabilities:
            #
            ### 1) No user should be able to elevate their privilege to owner.
            ### 2) Admin users are *not* superior to #channel.ops, and don't
            ###    have God-like powers over channels.
            ### 3) We assume that Admin users are two things: non-malicious and
            ###    and greedy for power.  So they'll try to elevate their
            ###    privilege to owner, but they won't try to crash the bot for
            ###    no reason.

            # Thus, the owner capability can't be given in the bot.  Admin
            # users can only give out capabilities they have themselves (which
            # will depend on supybot.capabilities and its child default) but
            # generally means they can't mess with channel capabilities.
            if ircutils.strEqual(capability, 'owner'):
                irc.error(_('The "owner" capability can\'t be added in the '
                          'bot.  Use the supybot-adduser program (or edit the '
                          'users.conf file yourself) to add an owner '
                          'capability.'))
                return
            if ircdb.isAntiCapability(capability) or \
               ircdb.checkCapability(msg.prefix, capability):
                user.addCapability(capability)
                ircdb.users.setUser(user)
                irc.replySuccess()
            else:
                irc.error(_('You can\'t add capabilities you don\'t have.'))
        add = wrap(add, ['otherUser', 'lowered'])

        @internationalizeDocstring
        def remove(self, irc, msg, args, user, capability):
            """<name|hostmask> <capability>

            Takes from the user specified by <name> (or the user to whom
            <hostmask> currently maps) the specified capability <capability>
            """
            if ircdb.checkCapability(msg.prefix, capability) or \
               ircdb.isAntiCapability(capability):
                try:
                    user.removeCapability(capability)
                    ircdb.users.setUser(user)
                    irc.replySuccess()
                except KeyError:
                    irc.error(_('That user doesn\'t have that capability.'))
            else:
                s = _('You can\'t remove capabilities you don\'t have.')
                irc.error(s)
        remove = wrap(remove, ['otherUser','lowered'])

    class ignore(callbacks.Commands):

        @internationalizeDocstring
        def add(self, irc, msg, args, hostmask, expires):
            """<hostmask|nick> [<expires>]

            This will set a persistent ignore on <hostmask> or the hostmask
            currently associated with <nick>. <expires> is an optional argument
            specifying when (in "seconds from now") the ignore will expire; if
            it isn't given, the ignore will never automatically expire.
            """
            ircdb.ignores.add(hostmask, expires)
            irc.replySuccess()
        add = wrap(add, ['hostmask', additional('expiry', 0)])

        @internationalizeDocstring
        def remove(self, irc, msg, args, hostmask):
            """<hostmask|nick>

            This will remove the persistent ignore on <hostmask> or the
            hostmask currently associated with <nick>.
            """
            try:
                ircdb.ignores.remove(hostmask)
                irc.replySuccess()
            except KeyError:
                irc.error(_('%s wasn\'t in the ignores database.') % hostmask)
        remove = wrap(remove, ['hostmask'])

        @internationalizeDocstring
        def list(self, irc, msg, args):
            """takes no arguments

            Lists the hostmasks that the bot is ignoring.
            """
            # XXX Add the expirations.
            if ircdb.ignores.hostmasks:
                irc.reply(format('%L', (list(map(repr,ircdb.ignores.hostmasks)))))
            else:
                irc.reply(_('I\'m not currently globally ignoring anyone.'))
        list = wrap(list)

    def clearq(self, irc, msg, args):
        """takes no arguments

        Clears the current send queue for this network.
        """
        irc.queue.reset()
        irc.replySuccess()
    clearq = wrap(clearq)

    def acmd(self, irc, msg, args, commandAndArgs):
        """<command> [<arg> ...]

        Perform <command> (with associated <arg>s on all channels on current network."""
        for channel in irc.state.channels:
            msg = ircmsgs.IrcMsg(msg=msg, args=(channel,) + msg.args[1:])
            self.Proxy(irc.getRealIrc(), msg, commandAndArgs)
    acmd = wrap(acmd, ['admin', many('something')])




Class = Admin

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
