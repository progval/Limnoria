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

import conf
import utils
import ircdb
import ircmsgs
import plugins
import ircutils
import privmsgs
import registry
import callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

# I should write/copy a generalized proxy at some point.
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

        
class ChannelStats(plugins.ChannelDBHandler, callbacks.Privmsg):
    noIgnore = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        plugins.ChannelDBHandler.__init__(self)
        self.lastmsg = None
        self.laststate = None
        self.outFiltering = False

    def die(self):
        callbacks.Privmsg.die(self)
        plugins.ChannelDBHandler.die(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename)
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE user_stats (
                              id INTEGER PRIMARY KEY,
                              user_id INTEGER UNIQUE ON CONFLICT IGNORE,
                              smileys INTEGER,
                              frowns INTEGER,
                              chars INTEGER,
                              words INTEGER,
                              msgs INTEGER,
                              actions INTEGER,
                              joins INTEGER,
                              parts INTEGER,
                              kicks INTEGER,
                              kicked INTEGER,
                              modes INTEGER,
                              topics INTEGER,
                              quits INTEGER
                              )""")
            cursor.execute("""CREATE TABLE channel_stats (
                              smileys INTEGER,
                              frowns INTEGER,
                              chars INTEGER,
                              words INTEGER,
                              msgs INTEGER,
                              actions INTEGER,
                              joins INTEGER,
                              parts INTEGER,
                              kicks INTEGER,
                              modes INTEGER,
                              topics INTEGER,
                              quits INTEGER
                              )""")
            cursor.execute("""INSERT INTO channel_stats
                              VALUES (0, 0, 0, 0, 0, 0,
                                      0, 0, 0, 0, 0, 0)""")
            db.commit()
        return db

    def __call__(self, irc, msg):
        try:
            if self.lastmsg:
                self.laststate.addMsg(irc, self.lastmsg)
            else:
                self.laststate = irc.state.copy()
        finally:
            self.lastmsg = msg
        super(ChannelStats, self).__call__(irc, msg)
        
    def doPrivmsg(self, irc, msg):
        if not ircutils.isChannel(msg.args[0]):
            return
        else:
            self._updatePrivmsgStats(msg)

    def _updatePrivmsgStats(self, msg):
        (channel, s) = msg.args
        db = self.getDb(channel)
        cursor = db.cursor()
        chars = len(s)
        words = len(s.split())
        isAction = ircmsgs.isAction(msg)
        frowns = len(self.registryValue('frowns', channel).findall(s))
        smileys = len(self.registryValue('smileys', channel).findall(s))
        s = ircmsgs.prettyPrint(msg)
        cursor.execute("""UPDATE channel_stats
                          SET smileys=smileys+%s,
                              frowns=frowns+%s,
                              chars=chars+%s,
                              words=words+%s,
                              msgs=msgs+1,
                              actions=actions+%s""",
                       smileys, frowns, chars, words, int(isAction))
        try:
            if self.outFiltering:
                id = 0
            else:
                id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            return
        cursor.execute("""INSERT INTO user_stats VALUES (
                          NULL, %s, 0, 0, 0, 0, 0, 0,
                          0, 0, 0, 0, 0, 0, 0)""", id)
        cursor.execute("""UPDATE user_stats SET
                          chars=chars+%s,
                          words=words+%s, msgs=msgs+1,
                          actions=actions+%s, smileys=smileys+%s,
                          frowns=frowns+%s
                          WHERE user_id=%s""",
                       chars, words, int(isAction), smileys, frowns, id)
        db.commit()

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if ircutils.isChannel(msg.args[0]):
                if self.registryValue('selfStats', msg.args[0]):
                    try:
                        self.outFiltering = True
                        self._updatePrivmsgStats(msg)
                    finally:
                        self.outFiltering = False
        return msg

    def doPart(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET parts=parts+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats SET parts=parts+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doTopic(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET topics=topics+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats
                              SET topics=topics+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doMode(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET modes=modes+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats
                              SET modes=modes+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doKick(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET kicks=kicks+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats
                              SET kicks=kicks+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        try:
            kicked = msg.args[1]
            id = ircdb.users.getUserId(irc.state.nickToHostmask(kicked))
            cursor.execute("""UPDATE user_stats
                              SET kicked=kicked+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doJoin(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET joins=joins+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats
                              SET joins=joins+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doQuit(self, irc, msg):
        for (channel, c) in self.laststate.channels.iteritems():
            if msg.nick in c.users:
                db = self.getDb(channel)
                cursor = db.cursor()
                cursor.execute("""UPDATE channel_stats SET quits=quits+1""")
                try:
                    id = ircdb.users.getUserId(msg.prefix)
                    cursor.execute("""UPDATE user_stats SET quits=quits+1
                                      WHERE user_id=%s""", id)
                except KeyError:
                    pass
                db.commit()

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
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM user_stats WHERE user_id=%s""", id)
        if cursor.rowcount == 0:
            irc.error('I have no stats for that user.')
            return
        values = cursor.fetchone()
        s = '%s has sent %s; a total of %s, %s, ' \
            '%s, and %s; %s of those messages %s' \
            '%s has joined %s, parted %s, quit %s, kicked someone %s, ' \
            'been kicked %s, changed the topic %s, ' \
            'and changed the mode %s.' % \
            (name, utils.nItems('message', values.msgs),
             utils.nItems('character', values.chars),
             utils.nItems('word', values.words),
             utils.nItems('smiley', values.smileys),
             utils.nItems('frown', values.frowns),
             values.actions, values.actions == 1 and 'was an ACTION.  '
                                                 or 'were ACTIONs.  ',
             name,
             utils.nItems('time', values.joins),
             utils.nItems('time', values.parts),
             utils.nItems('time', values.quits),
             utils.nItems('time', values.kicks),
             utils.nItems('time', values.kicked),
             utils.nItems('time', values.topics),
             utils.nItems('time', values.modes))
        irc.reply(s)

    def channelstats(self, irc, msg, args):
        """[<channel>]

        Returns the statistics for <channel>.  <channel> is only necessary if
        the message isn't sent on the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM channel_stats""")
        values = cursor.fetchone()
        s = 'On %s there have been %s messages, containing %s characters, ' \
            '%s words, %s smileys, and %s frowns; %s of those messages were ' \
            'ACTIONs.  There have been %s joins, %s parts, %s quits, ' \
            '%s kicks, %s mode changes, and %s topic changes.' % \
            (channel, values.msgs, values.chars,
             values.words, values.smileys, values.frowns, values.actions,
             values.joins, values.parts, values.quits,
             values.kicks, values.modes, values.topics)
        irc.reply(s)

                           
Class = ChannelStats

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
