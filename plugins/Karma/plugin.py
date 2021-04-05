###
# Copyright (c) 2005, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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

import os
import sys
import csv

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Karma')

import sqlite3

def checkAllowShell(irc):
    if not conf.supybot.commands.allowShell():
        irc.error('This command is not available, because '
            'supybot.commands.allowShell is False.', Raise=True)

class SqliteKarmaDB(object):
    def __init__(self, filename):
        self.dbs = ircutils.IrcDict()
        self.filename = filename

    def close(self):
        for db in self.dbs.values():
            db.close()

    def _getDb(self, channel):
        filename = plugins.makeChannelFilename(self.filename, channel)
        if filename in self.dbs:
            return self.dbs[filename]
        if os.path.exists(filename):
            db = sqlite3.connect(filename, check_same_thread=False)
            if minisix.PY2:
                db.text_factory = str
            self.dbs[filename] = db
            return db
        db = sqlite3.connect(filename, check_same_thread=False)
        if minisix.PY2:
            db.text_factory = str
        self.dbs[filename] = db
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

    def get(self, channel, thing):
        db = self._getDb(channel)
        thing = thing.lower()
        cursor = db.cursor()
        cursor.execute("""SELECT added, subtracted FROM karma
                          WHERE normalized=?""", (thing,))
        results = cursor.fetchall()
        if len(results) == 0:
            return None
        else:
            return list(map(int, results[0]))

    def gets(self, channel, things):
        db = self._getDb(channel)
        cursor = db.cursor()
        normalizedThings = dict(list(zip([s.lower() for s in things], things)))
        criteria = ' OR '.join(['normalized=?'] * len(normalizedThings))
        sql = """SELECT name, added-subtracted FROM karma
                 WHERE %s ORDER BY added-subtracted DESC""" % criteria
        cursor.execute(sql, list(normalizedThings.keys()))
        L = [(name, int(karma)) for (name, karma) in cursor.fetchall()]
        for (name, _) in L:
            del normalizedThings[name.lower()]
        neutrals = list(normalizedThings.values())
        neutrals.sort()
        return (L, neutrals)

    def top(self, channel, limit):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT name, added-subtracted FROM karma
                          ORDER BY added-subtracted DESC LIMIT ?""", (limit,))
        return [(t[0], int(t[1])) for t in cursor.fetchall()]

    def bottom(self, channel, limit):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT name, added-subtracted FROM karma
                          ORDER BY added-subtracted ASC LIMIT ?""", (limit,))
        return [(t[0], int(t[1])) for t in cursor.fetchall()]

    def rank(self, channel, thing):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT added-subtracted FROM karma
                          WHERE name=?""", (thing,))
        results = cursor.fetchall()
        if len(results) == 0:
            return None
        karma = int(results[0][0])
        cursor.execute("""SELECT COUNT(*) FROM karma
                          WHERE added-subtracted > ?""", (karma,))
        rank = int(cursor.fetchone()[0])
        return rank+1

    def size(self, channel):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM karma""")
        return int(cursor.fetchone()[0])

    def increment(self, channel, name):
        db = self._getDb(channel)
        cursor = db.cursor()
        normalized = name.lower()
        cursor.execute("""INSERT INTO karma VALUES (NULL, ?, ?, 0, 0)""",
                       (name, normalized,))
        cursor.execute("""UPDATE karma SET added=added+1
                          WHERE normalized=?""", (normalized,))
        db.commit()

    def decrement(self, channel, name):
        db = self._getDb(channel)
        cursor = db.cursor()
        normalized = name.lower()
        cursor.execute("""INSERT INTO karma VALUES (NULL, ?, ?, 0, 0)""",
                       (name, normalized,))
        cursor.execute("""UPDATE karma SET subtracted=subtracted+1
                          WHERE normalized=?""", (normalized,))
        db.commit()

    def most(self, channel, kind, limit):
        if kind == 'increased':
            orderby = 'added'
        elif kind == 'decreased':
            orderby = 'subtracted'
        elif kind == 'active':
            orderby = 'added+subtracted'
        else:
            raise ValueError('invalid kind')
        sql = """SELECT name, %s FROM karma ORDER BY %s DESC LIMIT %s""" % \
              (orderby, orderby, limit)
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute(sql)
        return [(name, int(i)) for (name, i) in cursor.fetchall()]

    def clear(self, channel, name=None):
        db = self._getDb(channel)
        cursor = db.cursor()
        if name:
            normalized = name.lower()
            cursor.execute("""DELETE FROM karma
                              WHERE normalized=?""", (normalized,))
        else:
            cursor.execute("""DELETE FROM karma""")
        db.commit()

    def dump(self, channel, filename):
        filename = conf.supybot.directories.data.dirize(filename)
        fd = utils.file.AtomicFile(filename)
        out = csv.writer(fd)
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT name, added, subtracted FROM karma""")
        for (name, added, subtracted) in cursor.fetchall():
            out.writerow([name, added, subtracted])
        fd.close()

    def load(self, channel, filename):
        filename = conf.supybot.directories.data.dirize(filename)
        fd = open(filename)
        reader = csv.reader(fd)
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""DELETE FROM karma""")
        for (name, added, subtracted) in reader:
            normalized = name.lower()
            cursor.execute("""INSERT INTO karma
                              VALUES (NULL, ?, ?, ?, ?)""",
                           (name, normalized, added, subtracted,))
        db.commit()
        fd.close()

KarmaDB = plugins.DB('Karma',
                     {'sqlite3': SqliteKarmaDB})

class Karma(callbacks.Plugin):
    """
    Provides a simple tracker for setting Karma (thing++, thing--).
    If ``config plugins.karma.allowUnaddressedKarma`` is set to ``True``
    (default since 2014.05.07), saying `boats++` will give 1 karma
    to ``boats``, and ``ships--`` will subtract 1 karma from ``ships``.

    However, if you use this in a sentence, like
    ``That deserves a ++. Kevin++``, 1 karma will be added to
    ``That deserves a ++. Kevin``, so you should only add or subtract karma
    in a line that doesn't have anything else in it.
    Alternatively, you can restrict karma tracking to nicks in the current
    channel by setting `config plugins.Karma.onlyNicks` to ``True``.

    If ``config plugins.karma.allowUnaddressedKarma` is set to `False``,
    you must address the bot with nick or prefix to add or subtract karma.
    """
    callBefore = ('Factoids', 'MoobotFactoids', 'Infobot')
    def __init__(self, irc):
        self.__parent = super(Karma, self)
        self.__parent.__init__(irc)
        self.db = KarmaDB()

    def die(self):
        self.__parent.die()
        self.db.close()

    def _normalizeThing(self, thing):
        assert thing
        if thing[0] == '(' and thing[-1] == ')':
            thing = thing[1:-1]
        return thing

    def _respond(self, irc, channel, thing, karma):
        if self.registryValue('response', channel, irc.network):
            irc.reply(_('%(thing)s\'s karma is now %(karma)i') %
                    {'thing': thing, 'karma': karma})
        else:
            irc.noReply()

    def _doKarma(self, irc, msg, channel, thing):
        inc = self.registryValue('incrementChars', channel, irc.network)
        dec = self.registryValue('decrementChars', channel, irc.network)
        onlynicks = self.registryValue('onlyNicks', channel, irc.network)
        karma = ''
        for s in inc:
            if thing.endswith(s):
                thing = thing[:-len(s)]
                # Don't reply if the target isn't a nick
                if onlynicks and thing.lower() not in map(ircutils.toLower,
                        irc.state.channels[channel].users):
                    return
                if ircutils.strEqual(thing, msg.nick) and \
                    not self.registryValue('allowSelfRating',
                                           channel, irc.network):
                        irc.error(_('You\'re not allowed to adjust your own karma.'))
                        return
                self.db.increment(channel, self._normalizeThing(thing))
                karma = self.db.get(channel, self._normalizeThing(thing))
        for s in dec:
            if thing.endswith(s):
                thing = thing[:-len(s)]
                if onlynicks and thing.lower() not in map(ircutils.toLower,
                        irc.state.channels[channel].users):
                    return
                if ircutils.strEqual(thing, msg.nick) and \
                    not self.registryValue('allowSelfRating',
                                           channel, irc.network):
                    irc.error(_('You\'re not allowed to adjust your own karma.'))
                    return
                self.db.decrement(channel, self._normalizeThing(thing))
                karma = self.db.get(channel, self._normalizeThing(thing))
        if karma:
            self._respond(irc, channel, thing, karma[0]-karma[1])

    def invalidCommand(self, irc, msg, tokens):
        if msg.channel and tokens:
            thing = ' '.join(tokens)
            self._doKarma(irc, msg, msg.channel, thing)

    def doPrivmsg(self, irc, msg):
        # We don't handle this if we've been addressed because invalidCommand
        # will handle it for us.  This prevents us from accessing the db twice
        # and therefore crashing.
        if not (msg.addressed or msg.repliedTo):
            if msg.channel and \
               not ircmsgs.isCtcp(msg) and \
               self.registryValue('allowUnaddressedKarma',
                                  msg.channel, irc.network):
                irc = callbacks.SimpleProxy(irc, msg)
                thing = msg.args[1].rstrip()
                self._doKarma(irc, msg, msg.channel, thing)

    @internationalizeDocstring
    def karma(self, irc, msg, args, channel, things):
        """[<channel>] [<thing> ...]

        Returns the karma of <thing>.  If <thing> is not given, returns the top
        N karmas, where N is determined by the config variable
        supybot.plugins.Karma.rankingDisplay.  If one <thing> is given, returns
        the details of its karma; if more than one <thing> is given, returns
        the total karma of each of the things. <channel> is only necessary
        if the message isn't sent on the channel itself.
        """
        if len(things) == 1:
            name = things[0]
            t = self.db.get(channel, name)
            if t is None:
                irc.reply(format(_('%s has neutral karma.'), name))
            else:
                (added, subtracted) = t
                total = added - subtracted
                if self.registryValue('simpleOutput', channel, irc.network):
                    s = format('%s: %i', name, total)
                else:
                    s = format(_('Karma for %q has been increased %n and '
                               'decreased %n for a total karma of %s.'),
                               name, (added, _('time')),
                               (subtracted, _('time')),
                               total)
                irc.reply(s)
        elif len(things) > 1:
            (L, neutrals) = self.db.gets(channel, things)
            if L:
                s = format('%L', [format('%s: %i', *t) for t in L])
                if neutrals:
                    neutral = format('.  %L %h neutral karma',
                                     neutrals, len(neutrals))
                    s += neutral
                irc.reply(s + '.')
            else:
                irc.reply(_('I didn\'t know the karma for any of those '
                            'things.'))
        else: # No name was given.  Return the top/bottom N karmas.
            limit = self.registryValue('rankingDisplay', channel, irc.network)
            highest = [format('%q (%s)', s, t)
                       for (s, t) in self.db.top(channel, limit)]
            lowest = [format('%q (%s)', s, t)
                      for (s, t) in self.db.bottom(channel, limit)]
            if not (highest and lowest):
                irc.error(_('I have no karma for this channel.'))
                return
            rank = self.db.rank(channel, msg.nick)
            if rank is not None:
                total = self.db.size(channel)
                rankS = format(_('  You (%s) are ranked %i out of %i.'),
                               msg.nick, rank, total)
            else:
                rankS = ''
            s = format(_('Highest karma: %L.  Lowest karma: %L.%s'),
                       highest, lowest, rankS)
            irc.reply(s)
    karma = wrap(karma, ['channel', any('something')])

    _mostAbbrev = utils.abbrev(['increased', 'decreased', 'active'])
    @internationalizeDocstring
    def most(self, irc, msg, args, channel, kind):
        """[<channel>] {increased,decreased,active}

        Returns the most increased, the most decreased, or the most active
        (the sum of increased and decreased) karma things.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        L = self.db.most(channel, kind,
                         self.registryValue('mostDisplay',
                                            channel, irc.network))
        if L:
            L = [format('%q: %i', name, i) for (name, i) in L]
            irc.reply(format('%L', L))
        else:
            irc.error(_('I have no karma for this channel.'))
    most = wrap(most, ['channel',
                       ('literal', ['increased', 'decreased', 'active'])])

    @internationalizeDocstring
    def clear(self, irc, msg, args, channel, name):
        """[<channel>] [<name>]

        Resets the karma of <name> to 0. If <name> is not given, resets
        everything.
        """
        self.db.clear(channel, name or None)
        irc.replySuccess()
    clear = wrap(clear, [('checkChannelCapability', 'op'), optional('text')])

    @internationalizeDocstring
    def dump(self, irc, msg, args, channel, filename):
        """[<channel>] <filename>

        Dumps the Karma database for <channel> to <filename> in the bot's
        data directory.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        checkAllowShell(irc)
        self.db.dump(channel, filename)
        irc.replySuccess()
    dump = wrap(dump, [('checkCapability', 'owner'), 'channeldb', 'filename'])

    @internationalizeDocstring
    def load(self, irc, msg, args, channel, filename):
        """[<channel>] <filename>

        Loads the Karma database for <channel> from <filename> in the bot's
        data directory.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        checkAllowShell(irc)
        self.db.load(channel, filename)
        irc.replySuccess()
    load = wrap(load, [('checkCapability', 'owner'), 'channeldb', 'filename'])

Class = Karma

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
