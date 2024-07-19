###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010,2015 James McCoy
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

import time
import functools

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization('Network')

class Network(callbacks.Plugin):
    """Provides network-related commands, such as connecting to multiple networks
    and checking latency to the server."""
    _whois = {}
    _latency = {}
    def _getIrc(self, network):
        irc = world.getIrc(network)
        if irc:
            return irc
        else:
            raise callbacks.Error('I\'m not currently connected to %s.' % network)

    def connect(self, irc, msg, args, opts, network, server, password):
        """[--nossl] <network> [<host[:port]>] [<password>]

        Connects to another network (which will be represented by the name
        provided in <network>) at <host:port>.  If port is not provided, it
        defaults to 6697, the default port for IRC with SSL.  If password is
        provided, it will be sent to the server in a PASS command.  If --nossl is
        provided, an SSL connection will not be attempted, and the port will
        default to 6667.
        """
        if '.' in network:
            irc.error("Network names cannot have a '.' in them. "
            "Remember, this is the network name, not the actual "
            "server you plan to connect to.", Raise=True)
        try:
            otherIrc = self._getIrc(network)
            irc.error(_('I\'m already connected to %s.') % network)
            return # We've gotta return here.  This is ugly code, but I'm not
                   # quite sure what to do about it.
        except callbacks.Error:
            pass
        ssl = True
        for (opt, arg) in opts:
            if opt == 'nossl':
                ssl = False
        if server:
            if ':' in server:
                (server, port) = server.rsplit(':', 1)
                port = int(port)
            elif ssl:
                port = 6697
            else:
                port = 6667
            serverPort = (server, port)
        else:
            try:
                serverPort = conf.supybot.networks.get(network).servers()[0]
            except (registry.NonExistentRegistryEntry, IndexError):
                irc.error(_('A server must be provided if the network is not '
                          'already registered.'))
                return
        Owner = irc.getCallback('Owner')
        newIrc = Owner._connect(network, serverPort=serverPort,
                                password=password, ssl=ssl)
        conf.supybot.networks().add(network)
        assert newIrc.callbacks is irc.callbacks, 'callbacks list is different'
        irc.replySuccess(_('Connection to %s initiated.') % network)
    connect = wrap(connect, ['owner', getopts({'nossl': ''}), 'something',
                             additional('something'),
                             additional('something', '')])

    def disconnect(self, irc, msg, args, otherIrc, quitMsg):
        """<network> [<quit message>]

        Disconnects from the network represented by the network <network>.
        If <quit message> is given, quits the network with the given quit
        message.
        """
        standard_msg = conf.supybot.plugins.Owner.quitMsg()
        if standard_msg:
            standard_msg = ircutils.standardSubstitute(irc, msg, standard_msg)
        quitMsg = quitMsg or standard_msg or msg.nick
        otherIrc.queueMsg(ircmsgs.quit(quitMsg))
        otherIrc.die()
        conf.supybot.networks().discard(otherIrc.network)
        if otherIrc != irc:
            irc.replySuccess(_('Disconnection to %s initiated.') %
                             otherIrc.network)
    disconnect = wrap(disconnect, ['owner', ('networkIrc', True), additional('text')])

    def reconnect(self, irc, msg, args, otherIrc, quitMsg):
        """[<network>] [<quit message>]

        Disconnects and then reconnects to <network>.  If no network is given,
        disconnects and then reconnects to the network the command was given
        on.  If no quit message is given, uses the configured one
        (supybot.plugins.Owner.quitMsg) or the nick of the person giving the
        command.
        """
        standard_msg = conf.supybot.plugins.Owner.quitMsg()
        if standard_msg:
            standard_msg = ircutils.standardSubstitute(irc, msg, standard_msg)
        quitMsg = quitMsg or standard_msg or msg.nick
        otherIrc.queueMsg(ircmsgs.quit(quitMsg))
        if otherIrc != irc:
            # No need to reply if we're reconnecting ourselves.
            irc.replySuccess()
    reconnect = wrap(reconnect, ['owner', 'networkIrc', additional('text')])

    def command(self, irc, msg, args, otherIrc, commandAndArgs):
        """<network> <command> [<arg> ...]

        Gives the bot <command> (with its associated <arg>s) on <network>.
        """
        self.Proxy(otherIrc, msg, commandAndArgs, replyIrc=irc)
    command = wrap(command, ['admin', ('networkIrc', True), many('anything')])

    def cmdall(self, irc, msg, args, commandAndArgs):
        """<command> [<arg> ...]

        Perform <command> (with its associated <arg>s) on all networks.
        """
        ircs = world.ircs
        for ircd in ircs:
            self.Proxy(ircd, msg, commandAndArgs)
    cmdall = wrap(cmdall, ['admin', many('anything')])

    ###
    # whois command-related stuff.
    ###
    def do311(self, irc, msg):
        nick = ircutils.toLower(msg.args[1])
        if (irc, nick) not in self._whois:
            return
        elif msg.command == '319':
            if '319' not in self._whois[(irc, nick)][2]:
                self._whois[(irc, nick)][2][msg.command] = []
            self._whois[(irc, nick)][2][msg.command].append(msg)
        else:
            self._whois[(irc, nick)][2][msg.command] = msg

    # These are all sent by a WHOIS response.
    do301 = do311
    do312 = do311
    do314 = do311
    do317 = do311
    do319 = do311
    do320 = do311

    def do318(self, irc, msg):
        nick = msg.args[1]
        loweredNick = ircutils.toLower(nick)
        if (irc, loweredNick) not in self._whois:
            return
        (replyIrc, replyMsg, d, command) = self._whois[(irc, loweredNick)]
        d['318'] = msg
        s = ircutils.formatWhois(irc, d, caller=replyMsg.nick,
                                 channel=replyMsg.args[0],
                                 command=command)
        replyIrc.reply(s)
        del self._whois[(irc, loweredNick)]
    do369 = do318

    def do402(self, irc, msg):
        nick = msg.args[1]
        loweredNick = ircutils.toLower(nick)
        if (irc, loweredNick) not in self._whois:
            return
        (replyIrc, replyMsg, d, command) = self._whois[(irc, loweredNick)]
        del self._whois[(irc, loweredNick)]
        if command == 'whois':
            template = _('There is no user %s on %s.')
        else:
            template = _('There was no user %s on %s.')
        s = template  % (nick, irc.network)
        replyIrc.reply(s)
    do401 = do402
    do406 = do402

    def whois(self, irc, msg, args, otherIrc, nick):
        """[<network>] <nick>

        Returns the WHOIS response <network> gives for <nick>.  <network> is
        only necessary if the network is different than the network the command
        is sent on.
        """
        # Here we use a remote server whois (double nick) to get idle/signon time.
        otherIrc.queueMsg(ircmsgs.whois(nick, nick))
        nick = ircutils.toLower(nick)
        self._whois[(otherIrc, nick)] = (irc, msg, {}, 'whois')
    whois = wrap(whois, ['networkIrc', 'nick'])

    def whowas(self, irc, msg, args, otherIrc, nick):
        """[<network>] <nick>

        Returns the WHOIS response <network> gives for <nick>.  <network> is
        only necessary if the network is different than the network the command
        is sent on.
        """
        # Here we use a remote server whois (double nick) to get idle/signon time.
        otherIrc.queueMsg(ircmsgs.whowas(nick, nick))
        nick = ircutils.toLower(nick)
        self._whois[(otherIrc, nick)] = (irc, msg, {}, 'whowas')
    whowas = wrap(whowas, ['networkIrc', 'nick'])

    def networks(self, irc, msg, args, opts):
        """[--all]

        Returns the networks to which the bot is currently connected.
        If --all is given, also includes networks known by the bot,
        but not connected to.
        """
        opts = dict(opts)
        L = ['%s: %s' % (ircd.network, ircd.server) for ircd in world.ircs]
        if 'all' in opts:
           for net in conf.supybot.networks._children.keys():
               if net not in [ircd.network for ircd in world.ircs]:
                   L.append('%s: (%s)' % (net, _('disconnected')))
        utils.sortBy(str.lower, L)
        irc.reply(format('%L', L))
    networks = wrap(networks, [getopts({'all': ''})])

    def doPong(self, irc, msg):
        now = time.time()
        if irc in self._latency:
            (replyIrc, when) = self._latency.pop(irc)
            replyIrc.reply(_('%.2f seconds.') % (now-when))

    def latency(self, irc, msg, args, otherIrc):
        """[<network>]

        Returns the current latency to <network>.  <network> is only necessary
        if the message isn't sent on the network to which this command is to
        apply.
        """
        otherIrc.queueMsg(ircmsgs.ping(_('Latency check (from %s).') %
                                       msg.nick))
        self._latency[otherIrc] = (irc, time.time())
        irc.noReply()
    latency = wrap(latency, ['networkIrc'])

    def driver(self, irc, msg, args, otherIrc):
        """[<network>]

        Returns the current network driver for <network>.  <network> is only
        necessary if the message isn't sent on the network to which this
        command is to apply.
        """
        irc.reply(otherIrc.driver.__class__.__module__[8:])
    driver = wrap(driver, ['networkIrc'])

    def uptime(self, irc, msg, args, otherIrc):
        """[<network>]

        Returns the time duration since the connection was established.
        """
        network = otherIrc.network
        now = time.time()
        started = otherIrc.startedAt
        irc.reply(_("I've been connected to %s for %s.") %
                            (network, utils.timeElapsed(now - started)))
    uptime = wrap(uptime, ['networkIrc'])

    def capabilities(self, irc, msg, args, otherIrc):
        """[<network>]

        Returns the list of IRCv3 capabilities available on the network.
        """
        irc.reply(format("%L", sorted(otherIrc.state.capabilities_ls)))
    capabilities = wrap(capabilities, ['networkIrc'])

    def authenticate(self, irc, msg, args):
        """takes no arguments

        Manually initiate SASL authentication.
        """
        if 'sasl' in irc.state.capabilities_ack:
            irc.startSasl(msg)
            irc.replySuccess()
        else:
            irc.error(_('SASL not supported'))
    authenticate = wrap(authenticate)

Class = Network

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
