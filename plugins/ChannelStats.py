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
Silently listens to every message received on a channel and keeps statistics
concerning joins, parts, and various other commands in addition to tracking
statistics about smileys, actions, characters, and words.
"""

__revision__ = "$Id$"

import plugins

import os
import re
import sets
import time
import getopt
import string
from itertools import imap, ifilter

import log
import conf
import utils
import world
import ircdb
import irclib
import ircmsgs
import plugins
import ircutils
import privmsgs
import registry
import callbacks

class Smileys(registry.Value):
    def set(self, s):
        L = s.split()
        self.setValue(L)

    def setValue(self, v):
        self.s = ' '.join(v)
        self.value = re.compile('|'.join(imap(re.escape, v)))

    def __str__(self):
        return self.s

conf.registerPlugin('ChannelStats')
conf.registerChannelValue(conf.supybot.plugins.ChannelStats, 'selfStats',
    registry.Boolean(True, """Determines whether the bot will keep channel
    statistics on itself, possibly skewing the channel stats (especially in
    cases where the bot is relaying between channels on a network)."""))
conf.registerChannelValue(conf.supybot.plugins.ChannelStats, 'smileys',
    Smileys(':) ;) ;] :-) :-D :D :P :p (= =)'.split(), """Determines what
    words (i.e., pieces of text with no spaces in them) are considered
    'smileys' for the purposes of stats-keeping."""))
conf.registerChannelValue(conf.supybot.plugins.ChannelStats, 'frowns',
    Smileys(':| :-/ :-\\ :\\ :/ :( :-( :\'('.split(), """Determines what words
    (i.e., pieces of text with no spaces in them ) are considered 'frowns' for
    the purposes of stats-keeping."""))

class ChannelStat(irclib.IrcCommandDispatcher):
    def __init__(self, actions=0, chars=0, frowns=0, joins=0, kicks=0, modes=0,
                 msgs=0, parts=0, quits=0, smileys=0, topics=0, words=0):
        self.actions = actions
        self.chars = chars
        self.frowns = frowns
        self.joins = joins
        self.kicks = kicks
        self.modes = modes
        self.msgs = msgs
        self.parts = parts
        self.quits = quits
        self.smileys = smileys
        self.topics = topics
        self.words = words
        self._values = ['actions', 'chars', 'frowns', 'joins', 'kicks','modes',
                       'msgs', 'parts', 'quits', 'smileys', 'topics', 'words']
    def values(self):
        return map(curry(getattr, self), self._values)

    def addMsg(self, msg):
        self.msgs += 1
        method = self.dispatchCommand(msg.command)
        if method is not None:
            method(msg)

    def doPayload(self, channel, payload):
        self.chars += len(payload)
        self.words += len(payload.split())
        fRe = conf.supybot.plugins.ChannelStats.get('frowns').get(channel)()
        sRe =conf.supybot.plugins.ChannelStats.get('smileys').get(channel)()
        self.frowns += len(fRe.findall(payload))
        self.smileys += len(sRe.findall(payload))

    def doPrivmsg(self, msg):
        self.doPayload(*msg.args)
        if ircmsgs.isAction(msg):
            self.actions += 1

    def doTopic(self, msg):
        self.doPayload(*msg.args)
        self.topics += 1

    def doKick(self, msg):
        self.kicks += 1

    def doPart(self, msg):
        if len(msg.args) == 2:
            self.doPayload(*msg.args)
        self.parts += 1

    def doMode(self, msg):
        self.modes += 1


class UserStat(ChannelStat):
    def __init__(self, id, kicked=0, *args):
        ChannelStat.__init__(self, *args)
        self.id = id
        self.kicked = kicked
        self._values.insert(0, 'kicked')

    def doKick(self, msg):
        self.doPayload(msg.args[0], msg.args[2])
        self.kicks += 1

class StatsDB(plugins.ChannelUserDB):
    def __init__(self, *args, **kwargs):
        self.channelStats = ircutils.IrcDict()
        plugins.ChannelUserDB.__init__(self, *args, **kwargs)
    
    def serialize(self, v):
        return v.values()

    def deserialize(self, channel, id, L):
        L = map(int, L)
        if id == 'channelStats':
            return ChannelStat(L)
        else:
            return UserStat(L)

    def addMsg(self, msg, id=None):
        channel = msg.args[0]
        if ircutils.isChannel(channel):
            if channel not in self.channelStats:
                self.channelStats[channel] = ChannelStat()
            self.channelStats[channel].addMsg(msg)
            try:
                if id is None:
                    id = ircdb.users.getUserId(msg.prefix)
            except KeyError:
                return
            if channel not in self.channels:
                self.channels[channel] = {}
            if id not in self.channels[channel]:
                self.channels[channel][id] = UserStat(id)
            self.channels[channel][id].addMsg(msg)

    def getChannelStats(self, channel):
        return self[channel, -1]
        
    def getUserStats(self, channel, id):
        return self[channel, id]

class ChannelStats(callbacks.Privmsg):
    noIgnore = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.lastmsg = None
        self.laststate = None
        self.outFiltering = False
        self.db = StatsDB(os.path.join(conf.supybot.directories.data(),
                                       'ChannelStats.db'))
        world.flushers.append(self.db.flush)

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        else:
            self.log.debug('Odd, no flush in flushers: %r', world.flushers)
        self.db.close()
        callbacks.Privmsg.die(self)

    def __call__(self, irc, msg):
        try:
            if self.lastmsg:
                self.laststate.addMsg(irc, self.lastmsg)
            else:
                self.laststate = irc.state.copy()
        finally:
            self.lastmsg = msg
        self.db.addMsg(msg)
        super(ChannelStats, self).__call__(irc, msg)
        
    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if ircutils.isChannel(msg.args[0]):
                if self.registryValue('selfStats', msg.args[0]):
                    try:
                        self.outFiltering = True
                        self.db.addMsg(msg, 0)
                    finally:
                        self.outFiltering = False
        return msg

    def doQuit(self, irc, msg):
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            id = None
        for (channel, c) in self.laststate.channels.iteritems():
            if msg.nick in c.users:
                if channel not in self.db.channelStats:
                    self.db.channelStats[channel] = ChannelStat()
                self.db.channelStats[channel].quits += 1
                if id is not None:
                    if channel not in self.db.channels:
                        self.db.channels[channel] = {}
                    if id not in self.db.channels[channel]:
                        self.db.channels[channel][id] = UserStat(id)
                    self.db.channels[channel][id].quits += 1

    def doKick(self, irc, msg):
        (channel, nick, _) = msg.args
        hostmask = irc.state.nickToHostmask(nick)
        try:
            id = ircdb.users.getUserId(hostmask)
        except KeyError:
            return
        if channel not in self.db.channels:
            self.db.channels[channel] = {}
        if id not in self.db.channels[channel]:
            self.db.channels[channel][id] = UserStat(id)
        self.db.channels[channel][id].kicked += 1

    def stats(self, irc, msg, args):
        """[<channel>] [<name>]

        Returns the statistics for <name> on <channel>.  <channel> is only
        necessary if the message isn't sent on the channel itself.  If <name>
        isn't given, it defaults to the user sending the command.
        """
        channel = privmsgs.getChannel(msg, args)
        name = privmsgs.getArgs(args, required=0, optional=1)
        if name == irc.nick:
            id = 0
        elif not name:
            try:
                id = ircdb.users.getUserId(msg.prefix)
                name = ircdb.users.getUser(id).name
            except KeyError:
                irc.error('I couldn\'t find you in my user database.')
                return
        elif not ircdb.users.hasUser(name):
            try:
                hostmask = irc.state.nickToHostmask(name)
                id = ircdb.users.getUserId(hostmask)
            except KeyError:
                irc.errorNoUser()
                return
        else:
            id = ircdb.users.getUserId(name)
        try:
            stats = self.db.getUserStats(channel, id)
            s = '%s has sent %s; a total of %s, %s, ' \
                '%s, and %s; %s of those messages %s' \
                '%s has joined %s, parted %s, quit %s, kicked someone %s, ' \
                'been kicked %s, changed the topic %s, ' \
                'and changed the mode %s.' % \
                (name, utils.nItems('message', stats.msgs),
                 utils.nItems('character', stats.chars),
                 utils.nItems('word', stats.words),
                 utils.nItems('smiley', stats.smileys),
                 utils.nItems('frown', stats.frowns),
                 stats.actions, stats.actions == 1 and 'was an ACTION.  '
                                                     or 'were ACTIONs.  ',
                 name,
                 utils.nItems('time', stats.joins),
                 utils.nItems('time', stats.parts),
                 utils.nItems('time', stats.quits),
                 utils.nItems('time', stats.kicks),
                 utils.nItems('time', stats.kicked),
                 utils.nItems('time', stats.topics),
                 utils.nItems('time', stats.modes))
            irc.reply(s)
        except KeyError:
            irc.error('I have no stats for that %s in %s' % (name, channel))

    def channelstats(self, irc, msg, args):
        """[<channel>]

        Returns the statistics for <channel>.  <channel> is only necessary if
        the message isn't sent on the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        try:
            stats = self.db.getChannelStats(channel)
            s = 'On %s there have been %s messages, containing %s ' \
                'characters, %s, %s, and %s; ' \
                '%s of those messages %s.  There have been ' \
                '%s, %s, %s, %s, %s, and %s.' % \
                (channel, stats.msgs, stats.chars,
                 utils.nItems('word', stats.words),
                 utils.nItems('smiley', stats.smileys),
                 utils.nItems('frown', stats.frowns),
                 stats.actions, stats.actions == 1 and 'was an ACTION'
                                                     or 'were ACTIONs',
                 utils.nItems('join', stats.joins),
                 utils.nItems('part', stats.parts),
                 utils.nItems('quit', stats.quits),
                 utils.nItems('kick', stats.kicks),
                 utils.nItems('change', stats.modes, between='mode'),
                 utils.nItems('change', stats.topics, between='topic'))
            irc.reply(s)
        except KeyError:
            irc.error('I\'ve never been on %s.' % channel)

                           
Class = ChannelStats

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
