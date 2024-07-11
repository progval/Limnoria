###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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

import re
import time

from . import config

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Services')

class State:
    def __init__(self):
        self.channels = []
        self.sentGhost = None
        self.identified = False
        self.waitingJoins = []

class Services(callbacks.Plugin):
    """This plugin handles dealing with Services on networks that provide them.
    Basically, you should use the "password" command to tell the bot a nick to
    identify with and what password to use to identify with that nick.  You can
    use the password command multiple times if your bot has multiple nicks
    registered.  Also, be sure to configure the NickServ and ChanServ
    configuration variables to match the NickServ and ChanServ nicks on your
    network.  Other commands such as identify, op, etc. should not be
    necessary if the bot is properly configured."""

    # 10 minutes ought to be more than enough for the server to reply.
    # Holds the (irc, nick) of the caller so we can notify them when the
    # command either succeeds or fails.
    _register = utils.structures.ExpiringDict(600)

    def __init__(self, irc):
        self.__parent = super(Services, self)
        self.__parent.__init__(irc)
        network = irc.network if irc else None
        for nick in self.registryValue('nicks', network=network):
            config.registerNick(nick)
        self.reset()

    def reset(self):
        self.state = {}

    def _getState(self, irc):
        return self.state.setdefault(irc.network, State())

    def disabled(self, irc):
        disabled = self.registryValue('disabledNetworks')
        if irc.network in disabled or \
           irc.state.supported.get('NETWORK', '') in disabled:
            return True
        return False

    def outFilter(self, irc, msg):
        state = self._getState(irc)
        if msg.command == 'JOIN' and not self.disabled(irc):
            if not state.identified:
                if self.registryValue('noJoinsUntilIdentified', network=irc.network):
                    self.log.info('Holding JOIN to %s @ %s until identified.',
                                  msg.channel, irc.network)
                    state.waitingJoins.append(msg)
                    return None
        return msg

    def _getNick(self, network):
        network_nick = conf.supybot.networks.get(network).nick()
        if network_nick == '':
            return conf.supybot.nick()
        else:
            return network_nick

    def _getNickServPassword(self, nick, network):
        # This should later be nick-specific.
        assert nick in self.registryValue('nicks', network=network)
        return self.registryValue('NickServ.password.%s' % nick, network=network)

    def _setNickServPassword(self, nick, password, network):
        # This also should be nick-specific.
        assert nick in self.registryValue('nicks', network=network)
        self.setRegistryValue('NickServ.password.%s' % nick, password, network=network)

    def _doIdentify(self, irc, nick=None):
        if self.disabled(irc):
            return
        if nick is None:
            nick = self._getNick(irc.network)
        if nick not in self.registryValue('nicks', network=irc.network):
            return
        nickserv = self.registryValue('NickServ', network=irc.network)
        password = self._getNickServPassword(nick, irc.network)
        if not nickserv:
            self.log.warning('Tried to identify without a NickServ set.')
            return
        if not password:
            self.log.warning('Tried to identify without a password set.')
            return
        assert ircutils.strEqual(irc.nick, nick), \
               'Identifying with not normal nick.'
        self.log.info('Sending identify (current nick: %s)', irc.nick)
        identify = 'IDENTIFY %s' % password
        # It's important that this next statement is irc.sendMsg, not
        # irc.queueMsg.  We want this message to get through before any
        # JOIN messages also being sent on 376.
        irc.sendMsg(ircmsgs.privmsg(nickserv, identify))

    def _doGhost(self, irc, nick=None):
        if self.disabled(irc):
            return
        state = self._getState(irc)
        if nick is None:
            nick = self._getNick(irc.network)
        if nick not in self.registryValue('nicks', network=irc.network):
            return
        nickserv = self.registryValue('NickServ', network=irc.network)
        password = self._getNickServPassword(nick, irc.network)
        ghostDelay = self.registryValue('ghostDelay', network=irc.network)
        if not ghostDelay:
            return
        if not nickserv:
            self.log.warning('Tried to ghost without a NickServ set.')
            return
        if not password:
            self.log.warning('Tried to ghost without a password set.')
            return
        if state.sentGhost and time.time() < (state.sentGhost + ghostDelay):
            self.log.warning('Refusing to send GHOST more than once every '
                             '%s seconds.' % ghostDelay)
        else:
            self.log.info('Sending ghost (current nick: %s; ghosting: %s)',
                          irc.nick, nick)
            ghostCommand = self.registryValue('ghostCommand', network=irc.network)
            ghost = '%s %s %s' % (ghostCommand, nick, password)
            # Ditto about the sendMsg (see _doIdentify).
            irc.sendMsg(ircmsgs.privmsg(nickserv, ghost))
            state.sentGhost = time.time()

    def __call__(self, irc, msg):
        self.__parent.__call__(irc, msg)
        if self.disabled(irc):
            return
        state = self._getState(irc)
        nick = self._getNick(irc.network)
        if nick not in self.registryValue('nicks', network=irc.network):
            return
        nickserv = self.registryValue('NickServ', network=irc.network)
        try:
            password = self._getNickServPassword(nick, irc.network)
        except Exception:
            self.log.exception('Could not get NickServ password for %s', nick)
            return
        ghostDelay = self.registryValue('ghostDelay', network=irc.network)
        if not ghostDelay:
            return
        if nick and nickserv and password and \
           not ircutils.strEqual(nick, irc.nick):
            if irc.afterConnect and (state.sentGhost is None or
               (state.sentGhost + ghostDelay) < time.time()):
                if nick in irc.state.nicksToHostmasks:
                    self._doGhost(irc)
                else:
                    irc.sendMsg(ircmsgs.nick(nick)) # 433 is handled elsewhere.

    def do001(self, irc, msg):
        # New connection, make sure sentGhost is None.
        state = self._getState(irc)
        state.sentGhost = None

    def do376(self, irc, msg):
        if self.disabled(irc):
            return
        nick = self._getNick(irc.network)
        if nick not in self.registryValue('nicks', network=irc.network):
            return
        nickserv = self.registryValue('NickServ', network=irc.network)
        if not nickserv:
            self.log.warning('NickServ is unset, cannot identify.')
            return
        password = self._getNickServPassword(nick, irc.network)
        if not password:
            self.log.warning('Password for %s is unset, cannot identify.',nick)
            return
        if not nick:
            self.log.warning('Cannot identify without a nick being set.  '
                             'Set supybot.plugins.Services.nick.')
            return
        if ircutils.strEqual(irc.nick, nick):
            self._doIdentify(irc)
        else:
            self._doGhost(irc)
    do422 = do377 = do376

    def do433(self, irc, msg):
        if self.disabled(irc):
            return
        nick = self._getNick(irc.network)
        if nick not in self.registryValue('nicks', network=irc.network):
            return
        if nick and irc.afterConnect:
            password = self._getNickServPassword(nick, irc.network)
            if not password:
                return
            self._doGhost(irc)

    def do515(self, irc, msg):
        # Can't join this channel, it's +r (we must be identified).
        state = self._getState(irc)
        state.channels.append(msg.args[1])

    def doNick(self, irc, msg):
        nick = self._getNick(irc.network)
        if ircutils.strEqual(msg.args[0], irc.nick) and \
           ircutils.strEqual(irc.nick, nick):
            self._doIdentify(irc)
        elif ircutils.strEqual(msg.nick, nick):
            irc.sendMsg(ircmsgs.nick(nick))

    def _ghosted(self, irc, s):
        nick = self._getNick(irc.network)
        lowered = s.lower()
        return bool('killed' in lowered and (nick in s or 'ghost' in lowered))

    def doNotice(self, irc, msg):
        if irc.afterConnect:
            nickserv = self.registryValue('NickServ', network=irc.network)
            chanserv = self.registryValue('ChanServ', network=irc.network)
            if nickserv and ircutils.strEqual(msg.nick, nickserv):
                self.doNickservNotice(irc, msg)
            elif chanserv and ircutils.strEqual(msg.nick, chanserv):
                self.doChanservNotice(irc, msg)

    _chanRe = re.compile('\x02(#.*?)\x02')
    def doChanservNotice(self, irc, msg):
        if self.disabled(irc):
            return
        s = msg.args[1].lower()
        channel = None
        m = self._chanRe.search(s)
        networkGroup = conf.supybot.networks.get(irc.network)
        on = 'on %s' % irc.network
        if m is not None:
            channel = m.group(1)
        if 'all bans' in s or 'unbanned from' in s or \
                ('unbanned %s' % irc.nick.lower()) in \
                ircutils.stripFormatting(s):
            # All bans removed (old freenode?)
            # You have been unbanned from (oftc, anope)
            # "Unbanned \x02someuser\x02 from \x02#channel\x02 (\x02N\x02
            # ban(s) removed)" (atheme 7.x)
            irc.sendMsg(networkGroup.channels.join(channel))
        elif 'isn\'t registered' in s:
            self.log.warning('Received "%s isn\'t registered" from ChanServ %s',
                             channel, on)
        elif 'this channel has been registered' in s:
            self.log.debug('Got "Registered channel" from ChanServ %s.', on)
        elif 'already opped' in s:
            # This shouldn't happen, Services.op should refuse to run if
            # we already have ops.
            self.log.debug('Got "Already opped" from ChanServ %s.', on)
        elif 'access level' in s and 'is required' in s:
            self.log.warning('Got "Access level required" from ChanServ %s.',
                             on)
        elif 'inviting' in s:
            self.log.debug('Got "Inviting to channel" from ChanServ %s.', on)
        elif s.startswith('['):
            chanTypes = irc.state.supported['CHANTYPES']
            if re.match(r'^\[[%s]' % re.escape(chanTypes), s):
                self.log.debug('Got entrymsg from ChanServ %s.', on)
        elif irc.isChannel(msg.args[0]):
            # Atheme uses channel-wide notices for alerting channel access
            # changes if the FANTASY or VERBOSE setting is on; we can suppress
            # these 'unexpected notice' warnings since they're not really
            # important.
            pass
        else:
            self.log.warning('Got unexpected notice from ChanServ %s: %r.',
                             on, msg)

    def doNickservNotice(self, irc, msg):
        if self.disabled(irc):
            return
        state = self._getState(irc)
        nick = self._getNick(irc.network)
        s = ircutils.stripFormatting(msg.args[1].lower())
        on = 'on %s' % irc.network
        networkGroup = conf.supybot.networks.get(irc.network)
        if 'incorrect' in s or 'denied' in s:
            log = 'Received "Password Incorrect" from NickServ %s.  ' \
                  'Resetting password to empty.' % on
            self.log.warning(log)
            state.sentGhost = time.time()
            self._setNickServPassword(nick, '', irc.network)
        elif self._ghosted(irc, s):
            self.log.info('Received "GHOST succeeded" from NickServ %s.', on)
            state.sentGhost = None
            state.identified = False
            irc.queueMsg(ircmsgs.nick(nick))
        elif 'is not registered' in s:
            self.log.info('Received "Nick not registered" from NickServ %s.',
                          on)
        elif 'currently' in s and 'isn\'t' in s or 'is not' in s:
            # The nick isn't online, let's change our nick to it.
            state.sentGhost = None
            irc.queueMsg(ircmsgs.nick(nick))
        elif ('owned by someone else' in s) or \
             ('nickname is registered and protected' in s) or \
             ('nick belongs to another user' in s):
            # freenode, arstechnica, chatjunkies
            # oftc, zirc.org
            # sorcery
            self.log.info('Received "Registered nick" from NickServ %s.', on)
        elif '/msg' in s and 'id' in s and 'password' in s:
            # Usage info for identify command; ignore.
            self.log.debug('Got usage info for identify command %s.', on)
        elif ('please choose a different nick' in s): # oftc, part 3
            # This is a catch-all for redundant messages from nickserv.
            pass
        elif ('now recognized' in s) or \
             ('already identified' in s) or \
             ('already logged in' in s) or \
             ('successfully identified' in s) or \
             ('password accepted' in s) or \
             ('now identified' in s):
            # freenode, oftc, arstechnica, zirc, ....
            # sorcery
            self.log.info('Received "Password accepted" from NickServ %s.', on)
            state.identified = True
            for channel in irc.state.channels.keys():
                self.checkPrivileges(irc, channel)
            for channel in state.channels:
                irc.queueMsg(networkGroup.channels.join(channel))
            waitingJoins = state.waitingJoins
            state.waitingJoins = []
            for join in waitingJoins:
                irc.sendMsg(join)
        elif 'not yet authenticated' in s:
            # zirc.org has this, it requires an auth code.
            email = s.split()[-1]
            self.log.warning('Received "Nick not yet authenticated" from '
                             'NickServ %s.  Check email at %s and send the '
                             'auth command to NickServ.', on, email)
        else:
            self.log.info('Received notice from NickServ %s: %q.', on,
                          ircutils.stripFormatting(msg.args[1]))

    def do903(self, irc, msg):  # RPL_SASLSUCCESS
        if self.disabled(irc):
            return
        state = self._getState(irc)
        state.identified = True
        for channel in irc.state.channels.keys():
            self.checkPrivileges(irc, channel)
        if irc.state.fsm in [irclib.IrcStateFsm.States.CONNECTED,
                             irclib.IrcStateFsm.States.CONNECTED_SASL]:
            for channel in state.channels:
                irc.queueMsg(networkGroup.channels.join(channel))
            waitingJoins = state.waitingJoins
            state.waitingJoins = []
            for join in waitingJoins:
                irc.sendMsg(join)

    do907 = do903  # ERR_SASLALREADY, just to be sure we didn't miss it

    def do901(self, irc, msg):  # RPL_LOGGEDOUT
        if self.disabled(irc):
            return
        state = self._getState(irc)
        state.identified = False

    def checkPrivileges(self, irc, channel):
        if self.disabled(irc):
            return
        chanserv = self.registryValue('ChanServ', network=irc.network)
        on = 'on %s' % irc.network
        if chanserv and self.registryValue('ChanServ.op', channel, irc.network):
            if irc.nick not in irc.state.channels[channel].ops:
                self.log.info('Requesting op from %s in %s %s.',
                              chanserv, channel, on)
                irc.sendMsg(ircmsgs.privmsg(chanserv, 'op %s' % channel))
        if chanserv and self.registryValue('ChanServ.halfop', channel, irc.network):
            if irc.nick not in irc.state.channels[channel].halfops:
                self.log.info('Requesting halfop from %s in %s %s.',
                              chanserv, channel, on)
                irc.sendMsg(ircmsgs.privmsg(chanserv, 'halfop %s' % channel))
        if chanserv and self.registryValue('ChanServ.voice', channel, irc.network):
            if irc.nick not in irc.state.channels[channel].voices:
                self.log.info('Requesting voice from %s in %s %s.',
                              chanserv, channel, on)
                irc.sendMsg(ircmsgs.privmsg(chanserv, 'voice %s' % channel))

    def doMode(self, irc, msg):
        if self.disabled(irc):
            return
        chanserv = self.registryValue('ChanServ', network=irc.network)
        on = 'on %s' % irc.network
        if ircutils.strEqual(msg.nick, chanserv):
            channel = msg.args[0]
            if len(msg.args) == 3:
                if ircutils.strEqual(msg.args[2], irc.nick):
                    mode = msg.args[1]
                    info = self.log.info
                    if mode == '+o':
                        info('Received op from ChanServ in %s %s.',
                             channel, on)
                    elif mode == '+h':
                        info('Received halfop from ChanServ in %s %s.',
                             channel, on)
                    elif mode == '+v':
                        info('Received voice from ChanServ in %s %s.',
                             channel, on)

    def do366(self, irc, msg): # End of /NAMES list; finished joining a channel
        state = self._getState(irc)
        if state.identified:
            channel = msg.args[1] # nick is msg.args[0].
            self.checkPrivileges(irc, channel)

    def callCommand(self, command, irc, msg, *args, **kwargs):
        if self.disabled(irc):
            irc.error('Services plugin is disabled on this network',
                      Raise=True)
        self.__parent.callCommand(command, irc, msg, *args, **kwargs)

    def _chanservCommand(self, irc, channel, command, log=False):
        chanserv = self.registryValue('ChanServ', network=irc.network)
        if chanserv:
            msg = ircmsgs.privmsg(chanserv,
                                  ' '.join([command, channel]))
            irc.sendMsg(msg)
        else:
            if log:
                self.log.warning('Unable to send %s command to ChanServ, '
                                 'you must set '
                                 'supybot.plugins.Services.ChanServ before '
                                 'I can send commands to ChanServ.', command)
            else:
                irc.error(_('You must set supybot.plugins.Services.ChanServ '
                          'before I\'m able to send the %s command.') % command,
                          Raise=True)

    @internationalizeDocstring
    def op(self, irc, msg, args, channel):
        """[<channel>]

        Attempts to get opped by ChanServ in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.error(format(_('I\'m already opped in %s.'), channel))
        else:
            self._chanservCommand(irc, channel, 'op')
    op = wrap(op, [('checkChannelCapability', 'op'), 'inChannel'])

    @internationalizeDocstring
    def voice(self, irc, msg, args, channel):
        """[<channel>]

        Attempts to get voiced by ChanServ in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        if irc.nick in irc.state.channels[channel].voices:
            irc.error(format(_('I\'m already voiced in %s.'), channel))
        else:
            self._chanservCommand(irc, channel, 'voice')
    voice = wrap(voice, [('checkChannelCapability', 'op'), 'inChannel'])

    def do474(self, irc, msg):
        if self.disabled(irc):
            return
        channel = msg.args[1]
        on = 'on %s' % irc.network
        self.log.info('Banned from %s, attempting ChanServ unban %s.',
                      channel, on)
        self._chanservCommand(irc, channel, 'unban', log=True)
        # Success log in doChanservNotice.

    @internationalizeDocstring
    def unban(self, irc, msg, args, channel):
        """[<channel>]

        Attempts to get unbanned by ChanServ in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself, but chances
        are, if you need this command, you're not sending it in the channel
        itself.
        """
        self._chanservCommand(irc, channel, 'unban')
        irc.replySuccess()
    unban = wrap(unban, [('checkChannelCapability', 'op')])

    def do473(self, irc, msg):
        if self.disabled(irc):
            return
        channel = msg.args[1]
        on = 'on %s' % irc.network
        self.log.info('%s is +i, attempting ChanServ invite %s.', channel, on)
        self._chanservCommand(irc, channel, 'invite', log=True)

    @internationalizeDocstring
    def invite(self, irc, msg, args, channel):
        """[<channel>]

        Attempts to get invited by ChanServ to <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself, but chances
        are, if you need this command, you're not sending it in the channel
        itself.
        """
        self._chanservCommand(irc, channel, 'invite')
        irc.replySuccess()
    invite = wrap(invite, [('checkChannelCapability', 'op'), 'inChannel'])

    def doInvite(self, irc, msg):
        if ircutils.strEqual(
                msg.nick, self.registryValue('ChanServ', network=irc.network)):
            channel = msg.args[1]
            on = 'on %s' % irc.network
            networkGroup = conf.supybot.networks.get(irc.network)
            self.log.info('Joining %s, invited by ChanServ %s.', channel, on)
            irc.queueMsg(networkGroup.channels.join(channel))

    @internationalizeDocstring
    def identify(self, irc, msg, args):
        """takes no arguments

        Identifies with NickServ using the current nick.
        """
        if self.registryValue('NickServ', network=irc.network):
            if irc.nick in self.registryValue('nicks', network=irc.network):
                self._doIdentify(irc, irc.nick)
                irc.replySuccess()
            else:
                irc.error(_('I don\'t have a configured password for '
                          'my current nick.'))
        else:
            irc.error(_('You must set supybot.plugins.Services.NickServ before '
                      'I\'m able to do identify.'))
    identify = wrap(identify, [('checkCapability', 'admin')])

    @internationalizeDocstring
    def ghost(self, irc, msg, args, nick):
        """[<nick>]

        Ghosts the bot's given nick and takes it.  If no nick is given,
        ghosts the bot's configured nick and takes it.
        """
        if self.registryValue('NickServ', network=irc.network):
            if not nick:
                nick = self._getNick(irc.network)
            if ircutils.strEqual(nick, irc.nick):
                irc.error(_('I cowardly refuse to ghost myself.'))
            else:
                self._doGhost(irc, nick=nick)
                irc.replySuccess()
        else:
            irc.error(_('You must set supybot.plugins.Services.NickServ before '
                      'I\'m able to ghost a nick.'))
    ghost = wrap(ghost, [('checkCapability', 'admin'), additional('nick')])

    def nickserv(self, irc, msg, args, text):
        """<text>

        Sends the <text> to NickServ. For example, to register to NickServ
        on Atheme, use: @nickserv REGISTER <password> <email-address>."""
        nickserv = self.registryValue('NickServ', network=irc.network)
        if nickserv:
            irc.replySuccess()
            irc.queueMsg(ircmsgs.privmsg(nickserv, text))
        else:
            irc.error(_('You must set supybot.plugins.Services.NickServ before '
                      'I\'m able to message NickServ'))
    nickserv = wrap(nickserv, ['owner', 'text'])

    def chanserv(self, irc, msg, args, text):
        """<text>

        Sends the <text> to ChanServ. For example, to register a channel
        on Atheme, use: @chanserv REGISTER <#channel>."""
        chanserv = self.registryValue('ChanServ', network=irc.network)
        if chanserv:
            irc.replySuccess()
            irc.queueMsg(ircmsgs.privmsg(chanserv, text))
        else:
            irc.error(_('You must set supybot.plugins.Services.ChanServ before '
                      'I\'m able to message ChanServ'))
    chanserv = wrap(chanserv, ['owner', 'text'])


    @internationalizeDocstring
    def password(self, irc, msg, args, nick, password):
        """<nick> [<password>]

        Sets the NickServ password for <nick> to <password>.  If <password> is
        not given, removes <nick> from the configured nicks.
        """
        if not password:
            try:
                v = self.registryValue('nicks', network=irc.network).copy()
                v.remove(nick)
                self.setRegistryValue('nicks', value=v, network=irc.network)
                irc.replySuccess()
            except KeyError:
                irc.error(_('That nick was not configured with a password.'))
                return
        else:
            v = self.registryValue('nicks', network=irc.network).copy()
            v.add(nick)
            self.setRegistryValue('nicks', value=v, network=irc.network)
            config.registerNick(nick, password)
            irc.replySuccess()
    password = wrap(password, [('checkCapability', 'admin'),
                                'private', 'nick', 'text'])

    @internationalizeDocstring
    def nicks(self, irc, msg, args):
        """takes no arguments

        Returns the nicks that this plugin is configured to identify and ghost
        with.
        """
        L = list(self.registryValue('nicks', network=irc.network))
        if L:
            utils.sortBy(ircutils.toLower, L)
            irc.reply(format('%L', L))
        else:
            irc.reply(_('I\'m not currently configured for any nicks.'))
    nicks = wrap(nicks, [('checkCapability', 'admin')])


    def _checkCanRegister(self, irc, otherIrc):
        if not conf.supybot.protocols.irc.experimentalExtensions():
            irc.error(
                _("Experimental IRC extensions are not enabled for this bot."),
                Raise=True
            )

        if "draft/account-registration" not in otherIrc.state.capabilities_ls:
            irc.error(
                _("This network does not support draft/account-registration."),
                Raise=True
            )

        if "labeled-response" not in otherIrc.state.capabilities_ls:
            irc.error(
                _("This network does not support labeled-response."),
                Raise=True
            )

        if otherIrc.sasl_authenticated:
            irc.error(
                _("This bot is already authenticated on the network."),
                Raise=True
            )

    def register(self, irc, msg, args, otherIrc, password, email):
        """[<network>] <password> [<email>]

        Uses the experimental REGISTER command to create an account for the bot
        on the <network>, using the <password> and the <email> if provided.
        Some networks may require the email.
        You may need to use the 'services verify' command afterward to confirm
        your email address."""
        # Using this early draft specification:
        # https://gist.github.com/edk0/bf3b50fc219fd1bed1aa15d98bfb6495
        self._checkCanRegister(irc, otherIrc)

        cap_values = (otherIrc.state.capabilities_ls["draft/account-registration"] or "").split(",")
        if "email-required" in cap_values and email is None:
            irc.error(
                _("This network requires an email address to register."),
                Raise=True
            )

        label = ircutils.makeLabel()
        self._register[label] = (irc, msg.nick)
        otherIrc.queueMsg(ircmsgs.IrcMsg(
            server_tags={"label": label},
            command="REGISTER",
            args=["*", email or "*", password],
        ))
    register = wrap(register, ["owner", "private", "networkIrc", "something", optional("email")])

    def verify(self, irc, msg, args, otherIrc, account, code):
        """[<network>] <account> <code>

        If the <network> requires a verification code, you need to call this
        command with the code the server gave you to finish the
        registration."""
        self._checkCanRegister(irc, otherIrc)

        label = ircutils.makeLabel()
        self._register[label] = (irc, msg.nick)
        otherIrc.queueMsg(ircmsgs.IrcMsg(
            server_tags={"label": label},
            command="VERIFY",
            args=[account, code]
        ))
    verify = wrap(verify, [
        "owner", "private", "networkIrc", "somethingWithoutSpaces", "something"
    ])

    def _replyToRegister(self, irc, msg, command, reply):
        if not conf.supybot.protocols.irc.experimentalExtensions():
            self.log.warning(
                "Got unexpected '%s' on %s, this should not "
                "happen unless supybot.protocols.irc.experimentalExtensions "
                "is enabled",
                command, irc.network
            )
            return

        label = msg.server_tags.get("label")

        if not label and "batch" in msg.server_tags:
            for batch in irc.state.getParentBatches(msg):
                label = batch.messages[0].server_tags.get("label")
                if label:
                    break

        if not label:
            self.log.error(
                "Got '%s' on %s, but it is missing a label. "
                "This is a bug, please report it.",
                command, irc.network
            )
            return

        if label not in self._register:
            self.log.warning(
                "Got '%s' on %s, but I don't remember using "
                "REGISTER/VERIFY. "
                "This may be caused by high latency from the server.",
                command, irc.network
            )
            return

        (initialIrc, initialNick) = self._register[label]
        initialIrc.reply(reply)

    def doFailRegister(self, irc, msg):
        self._replyToRegister(
            irc, msg, "FAIL %s" % msg.args[0],
            format(
                "Failed to register on %s; the server said: %s (%s)",
                irc.network, msg.args[1], msg.args[-1]
            )
        )
    doFailVerify = doFailRegister

    # This should not be called, but you never know.
    def doWarnRegister(self, irc, msg):
        self._replyToRegister(
            irc, msg, "WARN %s" % msg.args[0],
            format(
                "Registration warning from %s: %s (%s)",
                irc.network, msg.args[1], msg.args[-1]
            )
        )
    doWarnVerify = doWarnRegister

    # This should not be called, but you never know.
    def doNoteRegister(self, irc, msg):
        self._replyToRegister(
            irc, msg, "NOTE %s" % msg.args[0],
            format(
                "Registration note from %s: %s (%s)",
                irc.network, msg.args[1], msg.args[-1]
            )
        )
    doNoteVerify = doNoteRegister

    def doRegister(self, irc, msg):
        (subcommand, account, message) = msg.args
        if subcommand == "SUCCESS":
            self._replyToRegister(
                irc, msg, "REGISTER SUCCESS",
                format(
                    "Registration of account %s on %s succeeded: %s",
                    account, irc.network, message
                )
            )
        elif subcommand == "VERIFICATION_REQUIRED":
            self._replyToRegister(
                irc, msg, "REGISTER VERIFICATION_REQUIRED",
                format(
                    "Registration of %s on %s requires verification to complete: %s",
                    account, irc.network, message
                )
            )
        else:
            self._replyToRegister(
                irc, msg, "REGISTER %s" % subcommand,
                format(
                    "Unknown reply while registering %s on %s: %s %s",
                    account, irc.network, subcommand, message
                )
            )

    def doVerify(self, irc, msg):
        (subcommand, account, message) = msg.args
        if subcommand == "SUCCESS":
            self._replyToRegister(
                irc, msg, "VERIFY SUCCESS",
                format(
                    "Verification of account %s on %s succeeded: %s",
                    account, irc.network, message
                )
            )
        else:
            self._replyToRegister(
                irc, msg, "VERIFY %s" % subcommand,
                format(
                    "Unknown reply while registering %s on %s: %s %s",
                    account, irc.network, subcommand, message
                )
            )

Class = Services

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
