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
Includes commands for connecting, disconnecting, and reconnecting to multiple
networks, as well as several other utility functions related to IRC networks.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import time

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


class Network(callbacks.Privmsg):
    _whois = {}
    _latency = {}
    def _getIrc(self, network):
        network = network.lower()
        for irc in world.ircs:
            if irc.network.lower() == network:
                return irc
        raise callbacks.Error, 'I\'m not currently connected to %s.' % network

    def _getNetwork(self, irc, args):
        try:
            self._getIrc(args[0])
            return args.pop(0)
        except (callbacks.Error, IndexError):
            return irc.network

    def connect(self, irc, msg, args):
        """<network> [<host[:port]>]

        Connects to another network at <host:port>.  If port is not provided, it
        defaults to 6667, the default port for IRC.
        """
        (network, server) = privmsgs.getArgs(args, optional=1)
        try:
            otherIrc = self._getIrc(network)
            irc.error('I\'m already connected to %s.' % network, Raise=True)
        except callbacks.Error:
            pass
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
        newIrc = Owner._connect(network, serverPort=serverPort)
        conf.supybot.networks().add(network)
        assert newIrc.callbacks is irc.callbacks, 'callbacks list is different'
        irc.replySuccess('Connection to %s initiated.' % network)
    connect = privmsgs.checkCapability(connect, 'owner')

    def disconnect(self, irc, msg, args):
        """[<network>] [<quit message>]

        Disconnects from the network represented by the network <network>.
        If <quit message> is given, quits the network with the given quit
        message.  <network> is only necessary if the network is different
        from the network the command is sent on.
        """
        network = self._getNetwork(irc, args)
        quitMsg = privmsgs.getArgs(args, required=0, optional=1)
        if not quitMsg:
            quitMsg = msg.nick
        otherIrc = self._getIrc(network)
        # replySuccess here, rather than lower, in case we're being
        # told to disconnect from the network we received the command on.
        irc.replySuccess()
        otherIrc.queueMsg(ircmsgs.quit(quitMsg))
        otherIrc.die()
        conf.supybot.networks().discard(network)
    disconnect = privmsgs.checkCapability(disconnect, 'owner')

    def reconnect(self, irc, msg, args):
        """[<network>]

        Disconnects and then reconnects to <network>.  If no network is given,
        disconnects and then reconnects to the network the command was given
        on.
        """
        network = self._getNetwork(irc, args)
        badIrc = self._getIrc(network)
        try:
            badIrc.driver.reconnect()
            if badIrc != irc:
                # No need to reply if we're reconnecting ourselves.
                irc.replySuccess()
        except AttributeError: # There's a cleaner way to do this, but I'm lazy.
            irc.error('I couldn\'t reconnect.  You should restart me instead.')
    reconnect = privmsgs.checkCapability(reconnect, 'owner')

    def command(self, irc, msg, args):
        """<network> <command> [<arg> ...]

        Gives the bot <command> (with its associated <arg>s) on <network>.
        """
        if len(args) < 2:
            raise callbacks.ArgumentError
        network = args.pop(0)
        otherIrc = self._getIrc(network)
        Owner = irc.getCallback('Owner')
        Owner.disambiguate(irc, args)
        self.Proxy(otherIrc, msg, args)
    command = privmsgs.checkCapability(command, 'admin')

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
        hostmask = '@'.join(d['311'].args[2:4])
        user = d['311'].args[-1]
        if '319' in d:
            channels = d['319'].args[-1].split()
            ops = []
            voices = []
            normal = []
            halfops = []
            for channel in channels:
                if channel.startswith('@'):
                    ops.append(channel[1:])
                elif channel.startswith('%'):
                    halfops.append(channel[1:])
                elif channel.startswith('+'):
                    voices.append(channel[1:])
                else:
                    normal.append(channel)
            L = []
            if ops:
                L.append('is an op on %s' % utils.commaAndify(ops))
            if halfops:
                L.append('is a halfop on %s' % utils.commaAndify(halfops))
            if voices:
                L.append('is voiced on %s' % utils.commaAndify(voices))
            if normal:
                if L:
                    L.append('is also on %s' % utils.commaAndify(normal))
                else:
                    L.append('is on %s' % utils.commaAndify(normal))
        else:
            L = ['isn\'t on any non-secret channels']
        channels = utils.commaAndify(L)
        if '317' in d:
            idle = utils.timeElapsed(d['317'].args[2])
            signon = time.strftime(conf.supybot.humanTimestampFormat(),
                                   time.localtime(float(d['317'].args[3])))
        else:
            idle = '<unknown>'
            signon = '<unknown>'
        if '312' in d:
            server = d['312'].args[2]
        else:
            server = '<unknown>'
        if '301' in d:
            away = '  %s is away: %s.' % (nick, d['301'].args[2])
        else:
            away = ''
        if '320' in d:
            if d['320'].args[2]:
                identify = ' identified'
            else:
                identify = ''
        else:
            identify = ''
        s = '%s (%s) has been%s on server %s since %s (idle for %s) and ' \
            '%s.%s' % (user, hostmask, identify, server, signon, idle,
                       channels, away)
        replyIrc.reply(s)
        del self._whois[(irc, loweredNick)]

    def do402(self, irc, msg):
        nick = msg.args[1]
        loweredNick = ircutils.toLower(nick)
        if (irc, loweredNick) not in self._whois:
            return
        (replyIrc, replyMsg, d) = self._whois[(irc, loweredNick)]
        del self._whois[(irc, loweredNick)]
        s = 'There is no %s on %s.' % (nick, self._getIrcName(irc))
        replyIrc.reply(s)
    do401 = do402

    def whois(self, irc, msg, args):
        """[<network>] <nick>

        Returns the WHOIS response <network> gives for <nick>.  <network> is
        only necessary if the network is different than the network the command
        is sent on.
        """
        network = self._getNetwork(irc, args)
        nick = privmsgs.getArgs(args)
        if not ircutils.isNick(nick):
            irc.errorInvalid('nick', nick, Raise=True)
        nick = ircutils.toLower(nick)
        otherIrc = self._getIrc(network)
        # The double nick here is necessary because single-nick WHOIS only works
        # if the nick is on the same server (*not* the same network) as the user
        # giving the command.  Yeah, it made me say wtf too.
        otherIrc.queueMsg(ircmsgs.whois(nick, nick))
        self._whois[(otherIrc, nick)] = (irc, msg, {})

    def networks(self, irc, msg, args):
        """takes no arguments

        Returns the networks to which the bot is currently connected.
        """
        L = ['%s: %s' % (ircd.network, ircd.server) for ircd in world.ircs]
        utils.sortBy(str.lower, L)
        irc.reply(utils.commaAndify(L))

    def doPong(self, irc, msg):
        now = time.time()
        if irc in self._latency:
            (replyIrc, when) = self._latency.pop(irc)
            replyIrc.reply('%.2f seconds.' % (now-when))

    def latency(self, irc, msg, args):
        """[<network>]

        Returns the current latency to <network>.  <network> is only necessary
        if the message isn't sent on the network to which this command is to
        apply.
        """
        network = self._getNetwork(irc, args)
        otherIrc = self._getIrc(network)
        otherIrc.queueMsg(ircmsgs.ping('Latency check (from %s).' % msg.nick))
        self._latency[otherIrc] = (irc, time.time())
        
    # XXX join
    # XXX part
        


Class = Network

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
