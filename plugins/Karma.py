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
Plugin for handling Karma stuff for a channel.
"""

__revision__ = "$Id$"

import os
import sets
from itertools import imap

import supybot.conf as conf
import supybot.utils as utils
import supybot.plugins as plugins
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'


conf.registerPlugin('Karma')
conf.registerChannelValue(conf.supybot.plugins.Karma, 'simpleOutput',
    registry.Boolean(False, """Determines whether the bot will output shorter
    versions of the karma output when requesting a single thing's karma."""))
conf.registerChannelValue(conf.supybot.plugins.Karma, 'response',
    registry.Boolean(False, """Determines whether the bot will reply with a
    success message when something's karma is incrneased or decreased."""))
conf.registerChannelValue(conf.supybot.plugins.Karma, 'rankingDisplay',
    registry.Integer(3, """Determines how many highest/lowest karma things are
    shown when karma is called with no arguments."""))
conf.registerChannelValue(conf.supybot.plugins.Karma, 'mostDisplay',
    registry.Integer(25, """Determines how many karma things are shown when
    the most command is called.'"""))
conf.registerChannelValue(conf.supybot.plugins.Karma, 'allowSelfRating',
    registry.Boolean(False, """Determines whether users can adjust the karma
    of their nick."""))

class Karma(callbacks.PrivmsgCommandAndRegexp, plugins.ChannelDBHandler):
    addressedRegexps = ['increaseKarma', 'decreaseKarma']
    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        plugins.ChannelDBHandler.__init__(self)

    def die(self):
        callbacks.PrivmsgCommandAndRegexp.die(self)
        plugins.ChannelDBHandler.die(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename)
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE karma (
                              id INTEGER PRIMARY KEY,
                              name TEXT,
                              normalized TEXT UNIQUE ON CONFLICT IGNORE,
                              added INTEGER,
                              subtracted INTEGER
                              )""")
            db.commit()
        def p(s1, s2):
            return int(ircutils.nickEqual(s1, s2))
        db.create_function('nickeq', 2, p)
        return db

    def karma(self, irc, msg, args):
        """[<channel>] [<thing> [<thing> ...]]

        Returns the karma of <text>.  If <thing> is not given, returns the top
        three and bottom three karmas.  If one <thing> is given, returns the
        details of its karma; if more than one <thing> is given, returns the
        total karma of each of the the things. <channel> is only necessary if
        the message isn't sent on the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        if len(args) == 1:
            name = args[0]
            normalized = name.lower()
            cursor.execute("""SELECT added, subtracted
                              FROM karma
                              WHERE normalized=%s""", normalized)
            if cursor.rowcount == 0:
                irc.reply('%s has no karma.' % name)
            else:
                (added, subtracted) = imap(int, cursor.fetchone())
                total = added - subtracted
                if self.registryValue('simpleOutput', channel):
                    s = '%s: %s' % (name, total)
                else:
                    s = 'Karma for %r has been increased %s ' \
                        'and decreased %s for a total karma of %s.' % \
                        (name, utils.nItems('time', added),
                         utils.nItems('time', subtracted), total)
                irc.reply(s)
        elif len(args) > 1:
            normalizedArgs = sets.Set(imap(str.lower, args))
            criteria = ' OR '.join(['normalized=%s'] * len(normalizedArgs))
            sql = """SELECT name, added-subtracted
                     FROM karma WHERE %s
                     ORDER BY added-subtracted DESC""" % criteria
            cursor.execute(sql, *normalizedArgs)
            if cursor.rowcount > 0:
                L = []
                for (n, t) in cursor.fetchall():
                    L.append('%s: %s' % (n, t))
                    normalizedArgs.remove(n.lower())
                if normalizedArgs:
                    if len(normalizedArgs) == 1:
                        ss = '%s has no karma' % normalizedArgs.pop()
                    else:
                        LL = list(normalizedArgs)
                        LL.sort()
                        ss = '%s have no karma' % utils.commaAndify(LL)
                    s = '%s.  %s.' % (utils.commaAndify(L), ss)
                else:
                    s = utils.commaAndify(L) + '.'
                irc.reply(s)
            else:
                irc.reply('I didn\'t know the karma for any '
                               'of those things.')
        else: # No name was given.  Return the top/bottom N karmas.
            limit = self.registryValue('rankingDisplay', channel)
            cursor.execute("""SELECT name, added-subtracted
                              FROM karma
                              ORDER BY added-subtracted DESC
                              LIMIT %s""", limit)
            highest=['%r (%s)' % (t[0], int(t[1])) for t in cursor.fetchall()]
            cursor.execute("""SELECT name, added-subtracted
                              FROM karma
                              ORDER BY added-subtracted ASC
                              LIMIT %s""", limit)
            lowest=['%r (%s)' % (t[0], int(t[1])) for t in cursor.fetchall()]
            cursor.execute("""SELECT added-subtracted FROM karma
                              WHERE name=%s""", msg.nick)
            if not (highest and lowest):
                irc.error('I have no karma for this channel.')
                return
            rankS = ''
            if cursor.rowcount != 0:
                personal = int(cursor.fetchone()[0])
                cursor.execute("""SELECT COUNT(*) FROM karma
                                  WHERE added-subtracted > %s""", personal)
                rank = int(cursor.fetchone()[0]) + 1
                cursor.execute("""SELECT COUNT(*) FROM karma""")
                total = int(cursor.fetchone()[0])
                rankS = '  You (%s) are ranked %s out of %s.' % \
                        (msg.nick, rank, total)
            s = 'Highest karma: %s.  Lowest karma: %s.%s' % \
                (utils.commaAndify(highest), utils.commaAndify(lowest), rankS)
            irc.reply(s)

    _mostAbbrev = utils.abbrev(['increased', 'decreased', 'active'])
    def most(self, irc, msg, args):
        """[<channel>] {increased,decreased,active}

        Returns the most increased, the most decreased, or the most active
        (the sum of increased and decreased) karma things.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        kind = privmsgs.getArgs(args)
        try:
            kind = self._mostAbbrev[kind]
            if kind == 'increased':
                orderby = 'added'
            elif kind == 'decreased':
                orderby = 'subtracted'
            elif kind == 'active':
                orderby = 'added+subtracted'
            sql = "SELECT name, %s FROM karma ORDER BY %s DESC LIMIT %s" % \
                  (orderby, orderby,
                   self.registryValue('mostDisplay', channel))
            db = self.getDb(channel)
            cursor = db.cursor()
            cursor.execute(sql)
            L = ['%s: %s' % (name, int(i)) for (name, i) in cursor.fetchall()]
            if L:
                irc.reply(utils.commaAndify(L))
            else:
                irc.error('I have no karma for this channel.')
        except KeyError:
            raise callbacks.ArgumentError

    def increaseKarma(self, irc, msg, match):
        r"^(\S+)\+\+(|\s+)$"
        name = match.group(1)
        normalized = name.lower()
        if not self.registryValue('allowSelfRating', msg.args[0]):
            if normalized == msg.nick.lower():
                return
        db = self.getDb(msg.args[0])
        cursor = db.cursor()
        cursor.execute("""INSERT INTO karma VALUES (NULL, %s, %s, 0, 0)""",
                       name, normalized)
        cursor.execute("""UPDATE karma
                          SET added=added+1
                          WHERE normalized=%s""", normalized)
        if self.registryValue('response', msg.args[0]):
            irc.replySuccess()

    def decreaseKarma(self, irc, msg, match):
        r"^(\S+)--(|\s+)$"
        name = match.group(1)
        normalized = name.lower()
        if not self.registryValue('allowSelfRating', msg.args[0]):
            if normalized == msg.nick.lower():
                return
        db = self.getDb(msg.args[0])
        cursor = db.cursor()
        cursor.execute("""INSERT INTO karma VALUES (NULL, %s, %s, 0, 0)""",
                       name, normalized)
        cursor.execute("""UPDATE karma
                          SET subtracted=subtracted+1
                          WHERE normalized=%s""", normalized)
        if self.registryValue('response', msg.args[0]):
            irc.replySuccess()


Class = Karma

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
