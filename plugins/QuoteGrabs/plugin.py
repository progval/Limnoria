###
# Copyright (c) 2004, Daniel DiPaolo
# Copyright (c) 2008-2010, James McCoy
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
import time
import random

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('QuoteGrabs')

import sqlite3

import traceback

#sqlite3.register_converter('bool', bool)

class QuoteGrabsRecord(dbi.Record):
    __fields__ = [
        'by',
        'text',
        'grabber',
        'at',
        'hostmask',
        ]

    def __str__(self):
        grabber = plugins.getUserName(self.grabber)
        if self.at:
            return format(_('%s (Said by: %s; grabbed by %s at %t)'),
                          self.text, self.hostmask, grabber, self.at)
        else:
            return format('%s', self.text)

class SqliteQuoteGrabsDB(object):
    def __init__(self, filename):
        self.dbs = ircutils.IrcDict()
        self.filename = filename

    def close(self):
        for db in self.dbs.values():
            db.close()

    def _getDb(self, channel):
        filename = plugins.makeChannelFilename(self.filename, channel)
        def p(s1, s2):
            # text_factory seems to only apply as an output adapter,
            # so doesn't apply to created functions; so we use str()
            return ircutils.nickEqual(str(s1), str(s2))
        if filename in self.dbs:
            return self.dbs[filename]
        if os.path.exists(filename):
            db = sqlite3.connect(filename)
            if minisix.PY2:
                db.text_factory = str
            db.create_function('nickeq', 2, p)
            self.dbs[filename] = db
            return db
        db = sqlite3.connect(filename)
        if minisix.PY2:
            db.text_factory = str
        db.create_function('nickeq', 2, p)
        self.dbs[filename] = db
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE quotegrabs (
                          id INTEGER PRIMARY KEY,
                          nick BLOB,
                          hostmask TEXT,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          quote TEXT
                          );""")
        db.commit()
        return db

    def get(self, channel, id, quoteonly = 0):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, nick, quote, hostmask, added_at, added_by
                          FROM quotegrabs WHERE id = ?""", (id,))
        results = cursor.fetchall()
        if len(results) == 0:
            raise dbi.NoRecordError
        (id, by, quote, hostmask, at, grabber) = results[0]
        if quoteonly == 0:
            return QuoteGrabsRecord(id, by=by, text=quote, hostmask=hostmask,
                                    at=int(at), grabber=grabber)
        else:
            return QuoteGrabsRecord(id, text=quote)

    def random(self, channel, nick):
        db = self._getDb(channel)
        cursor = db.cursor()
        if nick:
            cursor.execute("""SELECT quote FROM quotegrabs
                              WHERE nickeq(nick, ?)
                              ORDER BY random() LIMIT 1""",
                              (nick,))
        else:
            cursor.execute("""SELECT quote FROM quotegrabs
                              ORDER BY random() LIMIT 1""")
        results = cursor.fetchall()
        if len(results) == 0:
            raise dbi.NoRecordError
        return results[0][0]

    def list(self, channel, nick):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, quote FROM quotegrabs
                          WHERE nickeq(nick, ?)
                          ORDER BY id DESC""", (nick,))
        results = cursor.fetchall()
        if len(results) == 0:
            raise dbi.NoRecordError
        return [QuoteGrabsRecord(id, text=quote)
                for (id, quote) in results]

    def getQuote(self, channel, nick):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT quote FROM quotegrabs
                          WHERE nickeq(nick, ?)
                          ORDER BY id DESC LIMIT 1""", (nick,))
        results = cursor.fetchall()
        if len(results) == 0:
            raise dbi.NoRecordError
        return results[0][0]

    def select(self, channel, nick):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT added_at FROM quotegrabs
                          WHERE nickeq(nick, ?)
                          ORDER BY id DESC LIMIT 1""", (nick,))
        results = cursor.fetchall()
        if len(results) == 0:
            raise dbi.NoRecordError
        return results[0][0]

    def add(self, channel, msg, by):
        db = self._getDb(channel)
        cursor = db.cursor()
        text = ircmsgs.prettyPrint(msg)
        # Check to see if the latest quotegrab is identical
        cursor.execute("""SELECT quote FROM quotegrabs
                          WHERE nick=?
                          ORDER BY id DESC LIMIT 1""", (msg.nick,))
        results = cursor.fetchall()
        if len(results) != 0:
            if text == results[0][0]:
                return
        cursor.execute("""INSERT INTO quotegrabs
                          VALUES (NULL, ?, ?, ?, ?, ?)""",
                       (msg.nick, msg.prefix, by, int(time.time()), text,))
        db.commit()

    def remove(self, channel, grab=None):
        db = self._getDb(channel)
        cursor = db.cursor()
        if grab is not None:
            # the testing if there actually *is* the to-be-deleted record is
            # strictly unnecessary -- the DELETE operation would "succeed"
            # anyway, but it's silly to just keep saying 'OK' no matter what,
            # so...
            cursor.execute("""SELECT * FROM quotegrabs WHERE id = ?""", (grab,))
            results = cursor.fetchall()
            if len(results) == 0:
                raise dbi.NoRecordError
            cursor.execute("""DELETE FROM quotegrabs WHERE id = ?""", (grab,))
        else:
            cursor.execute("""SELECT * FROM quotegrabs WHERE id = (SELECT MAX(id)
                FROM quotegrabs)""")
            results = cursor.fetchall()
            if len(results) == 0:
                raise dbi.NoRecordError
            cursor.execute("""DELETE FROM quotegrabs WHERE id = (SELECT MAX(id)
                FROM quotegrabs)""")
        db.commit()

    def search(self, channel, text):
        db = self._getDb(channel)
        cursor = db.cursor()
        text = '%' + text + '%'
        cursor.execute("""SELECT id, nick, quote FROM quotegrabs
                          WHERE quote LIKE ?
                          ORDER BY id DESC""", (text,))
        results = cursor.fetchall()
        if len(results) == 0:
            raise dbi.NoRecordError
        return [QuoteGrabsRecord(id, text=quote, by=nick)
                for (id, nick, quote) in results]

QuoteGrabsDB = plugins.DB('QuoteGrabs', {'sqlite3': SqliteQuoteGrabsDB})

class QuoteGrabs(callbacks.Plugin):
    """Stores and displays quotes from channels. Quotes are stored randomly
    and/or on user request."""
    def __init__(self, irc):
        self.__parent = super(QuoteGrabs, self)
        self.__parent.__init__(irc)
        self.db = QuoteGrabsDB()

    def doPrivmsg(self, irc, msg):
        if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
            return
        irc = callbacks.SimpleProxy(irc, msg)
        if msg.channel:
            payload = msg.args[1]
            words = self.registryValue('randomGrabber.minimumWords',
                                       msg.channel, irc.network)
            length = self.registryValue('randomGrabber.minimumCharacters',
                                        msg.channel, irc.network)
            grabTime = \
            self.registryValue('randomGrabber.averageTimeBetweenGrabs',
                               msg.channel, irc.network)
            channel = plugins.getChannel(msg.channel)
            if self.registryValue('randomGrabber', msg.channel, irc.network):
                if len(payload) > length and len(payload.split()) > words:
                    try:
                        last = int(self.db.select(channel, msg.nick))
                    except dbi.NoRecordError:
                        self._grab(channel, irc, msg, irc.prefix)
                        self._sendGrabMsg(irc, msg)
                    else:
                        elapsed = int(time.time()) - last
                        if (random.random() * elapsed) > (grabTime / 2):
                            self._grab(channel, irc, msg, irc.prefix)
                            self._sendGrabMsg(irc, msg)

    def _grab(self, channel, irc, msg, addedBy):
        self.db.add(channel, msg, addedBy)

    def _sendGrabMsg(self, irc, msg):
        s = 'jots down a new quote for %s' % msg.nick
        irc.reply(s, action=True, prefixNick=False)

    @internationalizeDocstring
    def grab(self, irc, msg, args, channel, nick):
        """[<channel>] <nick>

        Grabs a quote from <channel> by <nick> for the quotegrabs table.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        # chan is used to make sure we know where to grab the quote from, as
        # opposed to channel which is used to determine which db to store the
        # quote in
        chan = msg.args[0]
        if chan is None or not irc.isChannel(chan):
            raise callbacks.ArgumentError
        if ircutils.nickEqual(nick, msg.nick):
            irc.error(_('You can\'t quote grab yourself.'), Raise=True)
        if conf.supybot.protocols.irc.experimentalExtensions():
            msgid = msg.server_tags.get('+draft/reply')
        else:
            msgid = None
        for m in reversed(irc.state.history):
            if msgid and m.server_tags.get('msgid') != msgid:
                continue
            if m.command == 'PRIVMSG' and ircutils.nickEqual(m.nick, nick) \
                    and ircutils.strEqual(m.args[0], chan):
                # TODO: strip statusmsg prefix for comparison? Must be careful
                # abouk leaks, though.
                self._grab(channel, irc, m, msg.prefix)
                irc.replySuccess()
                return
        irc.error(_('I couldn\'t find a proper message to grab.'))
    grab = wrap(grab, ['channeldb', 'nick'])

    @internationalizeDocstring
    def ungrab(self, irc, msg, args, channel, grab):
        """[<channel>] <number>

        Removes the grab <number> (the last by default) on <channel>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        try:
            self.db.remove(channel, grab)
            irc.replySuccess()
        except dbi.NoRecordError:
            if grab is None:
                irc.error(_('Nothing to ungrab.'))
            else:
                irc.error(_('Invalid grab number.'))
    ungrab = wrap(ungrab, ['channeldb', optional('id')])

    @internationalizeDocstring
    def quote(self, irc, msg, args, channel, nick):
        """[<channel>] <nick>

        Returns <nick>'s latest quote grab in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        try:
            irc.reply(self.db.getQuote(channel, nick))
        except dbi.NoRecordError:
            irc.error(_('I couldn\'t find a matching quotegrab for %s.') %
                      nick, Raise=True)
    quote = wrap(quote, ['channeldb', 'nick'])

    @internationalizeDocstring
    def list(self, irc, msg, args, channel, nick):
        """[<channel>] <nick>

        Returns a list of shortened quotes that have been grabbed for <nick>
        as well as the id of each quote.  These ids can be used to get the
        full quote.  <channel> is only necessary if the message isn't sent in
        the channel itself.
        """
        try:
            records = self.db.list(channel, nick)
            L = []
            for record in records:
                # strip the nick from the quote
                quote = record.text.replace('<%s> ' % nick, '', 1)
                item = utils.str.ellipsisify('#%s: %s' % (record.id, quote),50)
                L.append(item)
            irc.reply(utils.str.commaAndify(L))
        except dbi.NoRecordError:
            irc.error(_('I couldn\'t find any quotegrabs for %s.') % nick,
                      Raise=True)
    list = wrap(list, ['channeldb', 'nick'])

    @internationalizeDocstring
    def random(self, irc, msg, args, channel, nick):
        """[<channel>] [<nick>]

        Returns a randomly grabbed quote, optionally choosing only from those
        quotes grabbed for <nick>.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        try:
            irc.reply(self.db.random(channel, nick))
        except dbi.NoRecordError:
            if nick:
                irc.error(_('Couldn\'t get a random quote for that nick.'))
            else:
                irc.error(_('Couldn\'t get a random quote.  Are there any '
                          'grabbed quotes in the database?'))
    random = wrap(random, ['channeldb', additional('nick')])

    @internationalizeDocstring
    def say(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Return the quotegrab with the given <id>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        try:
            irc.reply(self.db.get(channel, id, 1))
        except dbi.NoRecordError:
            irc.error(_('No quotegrab for id %s') % utils.str.quoted(id),
                      Raise=True)
    say = wrap(say, ['channeldb', 'id'])

    @internationalizeDocstring
    def get(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Return the quotegrab with the given <id>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        try:
            irc.reply(self.db.get(channel, id))
        except dbi.NoRecordError:
            irc.error(_('No quotegrab for id %s') % utils.str.quoted(id),
                      Raise=True)
    get = wrap(get, ['channeldb', 'id'])

    @internationalizeDocstring
    def search(self, irc, msg, args, channel, text):
        """[<channel>] <text>

        Searches for <text> in a quote.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        try:
            records = self.db.search(channel, text)
            L = []
            for record in records:
                # strip the nick from the quote
                quote = record.text.replace('<%s> ' % record.by, '', 1)
                item = utils.str.ellipsisify('#%s: %s' % (record.id, quote),50)
                L.append(item)
            irc.reply(utils.str.commaAndify(L))
        except dbi.NoRecordError:
            irc.error(_('No quotegrabs matching %s') % utils.str.quoted(text),
                       Raise=True)
    search = wrap(search, ['channeldb', 'text'])

Class = QuoteGrabs

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
