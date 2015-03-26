###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010,2015 James McCoy
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

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks

class Network(callbacks.Plugin):
    _whois = {}
    _latency = {}
    def _getIrc(self, network):
        irc = world.getIrc(network)
        if irc:
            return irc
        else:
            raise callbacks.Error, \
                  'I\'m not currently connected to %s.' % network

    def connect(self, irc, msg, args, opts, network, server, password):
        """[--ssl] <network> [<host[:port]>] [<password>]

        Connects to another network (which will be represented by the name
        provided in <network>) at <host:port>.  If port is not provided, it
        defaults to 6667, the default port for IRC.  If password is
        provided, it will be sent to the server in a PASS command.  If --ssl is
        provided, an SSL connection will be attempted.
        """
        try:
            otherIrc = self._getIrc(network)
            irc.error('I\'m already connected to %s.' % network)
            return # We've gotta return here.  This is ugly code, but I'm not
                   # quite sure what to do about it.
        except callbacks.Error:
            pass
        ssl = False
        for (opt, arg) in opts:
            if opt == 'ssl':
                ssl = True
        if server:
            if ':' in server:
                (server, port) = server.split(':')
                port = int(port)
            else:
                port = 6667
            serverPort = (server, port)
        else:
            try:
                serverPort = conf.supybot.networks.get(network).servers()[0]
            except (registry.NonExistentRegistryEntry, IndexError):
                irc.error('A server must be provided if the network is not '
                          'already registered.')
                return
        Owner = irc.getCallback('Owner')
        newIrc = Owner._connect(network, serverPort=serverPort,
                                password=password, ssl=ssl)
        conf.supybot.networks().add(network)
        assert newIrc.callbacks is irc.callbacks, 'callbacks list is different'
        irc.replySuccess('Connection to %s initiated.' % network)
    connect = wrap(connect, ['owner', getopts({'ssl': ''}), 'something',
                             additional('something'),
                             additional('something', '')])

    def disconnect(self, irc, msg, args, otherIrc, quitMsg):
        """[<network>] [<quit message>]

        Disconnects from the network represented by the network <network>.
        If <quit message> is given, quits the network with the given quit
        message.  <network> is only necessary if the network is different
        from the network the command is sent on.
        """
        quitMsg = quitMsg or conf.supybot.plugins.Owner.quitMsg() or msg.nick
        otherIrc.queueMsg(ircmsgs.quit(quitMsg))
        otherIrc.die()
        conf.supybot.networks().discard(otherIrc.network)
        if otherIrc != irc:
            irc.replySuccess('Disconnection to %s initiated.' %
                             otherIrc.network)
    disconnect = wrap(disconnect, ['owner', 'networkIrc', additional('text')])

    def reconnect(self, irc, msg, args, otherIrc, quitMsg):
        """[<network>] [<quit message>]

        Disconnects and then reconnects to <network>.  If no network is given,
        disconnects and then reconnects to the network the command was given
        on.  If no quit message is given, uses the configured one
        (supybot.plugins.Owner.quitMsg) or the nick of the person giving the
        command.
        """
        quitMsg = quitMsg or conf.supybot.plugins.Owner.quitMsg() or msg.nick
        otherIrc.queueMsg(ircmsgs.quit(quitMsg))
        if otherIrc != irc:
            # No need to reply if we're reconnecting ourselves.
            irc.replySuccess()
    reconnect = wrap(reconnect, ['owner', 'networkIrc', additional('text')])

    def command(self, irc, msg, args, otherIrc, commandAndArgs):
        """<network> <command> [<arg> ...]

        Gives the bot <command> (with its associated <arg>s) on <network>.
        """
        self.Proxy(otherIrc, msg, commandAndArgs)
    command = wrap(command, ['admin', ('networkIrc', True), many('something')])

    ###
    # whois command-related stuff.
    ###
    def do311(self, irc, msg):
        nick = ircutils.toLower(msg.args[1])
        if (irc, nick) not in self._whois:
            return
        else:
            self._whois[(irc, nick)][-1][msg.command] = msg

    # These are all sent by a WHOIS response.
    do301 = do311
    do312 = do311
    do317 = do311
    do319 = do311
    do320 = do311

    def do318(self, irc, msg):
        nick = msg.args[1]
        loweredNick = ircutils.toLower(nick)
        if (irc, loweredNick) not in self._whois:
            return
        (replyIrc, replyMsg, d) = self._whois[(irc, loweredNick)]
        d['318'] = msg
        s = ircutils.formatWhois(irc, d, caller=replyMsg.nick,
                                 channel=replyMsg.args[0])
        replyIrc.reply(s)
        del self._whois[(irc, loweredNick)]

    def do402(self, irc, msg):
        nick = msg.args[1]
        loweredNick = ircutils.toLower(nick)
        if (irc, loweredNick) not in self._whois:
            return
        (replyIrc, replyMsg, d) = self._whois[(irc, loweredNick)]
        del self._whois[(irc, loweredNick)]
        s = 'There is no %s on %s.' % (nick, irc.network)
        replyIrc.reply(s)
    do401 = do402

    def whois(self, irc, msg, args, otherIrc, nick):
        """[<network>] <nick>

        Returns the WHOIS response <network> gives for <nick>.  <network> is
        only necessary if the network is different than the network the command
        is sent on.
        """
        # The double nick here is necessary because single-nick WHOIS only works
        # if the nick is on the same server (*not* the same network) as the user
        # giving the command.  Yeah, it made me say wtf too.
        nick = ircutils.toLower(nick)
        otherIrc.queueMsg(ircmsgs.whois(nick, nick))
        self._whois[(otherIrc, nick)] = (irc, msg, {})
    whois = wrap(whois, ['networkIrc', 'nick'])

    def networks(self, irc, msg, args):
        """takes no arguments

        Returns the networks to which the bot is currently connected.
        """
        L = ['%s: %s' % (ircd.network, ircd.server) for ircd in world.ircs]
        utils.sortBy(str.lower, L)
        irc.reply(format('%L', L))
    networks = wrap(networks)

    def doPong(self, irc, msg):
        now = time.time()
        if irc in self._latency:
            (replyIrc, when) = self._latency.pop(irc)
            replyIrc.reply('%.2f seconds.' % (now-when))

    def latency(self, irc, msg, args, otherIrc):
        """[<network>]

        Returns the current latency to <network>.  <network> is only necessary
        if the message isn't sent on the network to which this command is to
        apply.
        """
        otherIrc.queueMsg(ircmsgs.ping('Latency check (from %s).' % msg.nick))
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


Class = Network

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
