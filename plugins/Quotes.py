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
Maintains a Quotes database for each channel.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import re
import time
import getopt
import os.path

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this '\
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

class QuoteRecord(object):
    __metaclass__ = dbi.Record
    __fields__ = [
        'at',
        'by',
        'text'
        ]
    def __str__(self):
        format = conf.supybot.humanTimestampFormat()
        return 'Quote %r added by %s at %s.' % \
               (self.text, self.by,
                time.strftime(format, time.localtime(float(self.at))))

class SqliteQuotesDB(object):
    def _getDb(self, channel):
        filename = plugins.makeChannelFilename('Quotes.db', channel)
        if os.path.exists(filename):
            return sqlite.connect(db=filename, mode=0755,
                                  converters={'bool': bool})
        #else:
        db = sqlite.connect(db=filename, mode=0755, coverters={'bool': bool})
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE quotes (
                          id INTEGER PRIMARY KEY,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          quote TEXT
                          );""")
        db.commit()
        return db

    def add(self, channel, by, quote):
        db = self._getDb(channel)
        cursor = db.cursor()
        at = int(time.time())
        cursor.execute("""INSERT INTO quotes VALUES (NULL, %s, %s, %s)""",
                       by, at, quote)
        cursor.execute("""SELECT id FROM quotes
                          WHERE added_by=%s AND added_at=%s AND quote=%s""",
                          by, at, quote)
        db.commit()
        return int(cursor.fetchone()[0])

    def size(self, channel):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM quotes""")
        return int(cursor.fetchone()[0])

    def random(self, channel):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, added_by, added_at, quote FROM quotes
                          ORDER BY random() LIMIT 1""")
        (id, by, at, text) = cursor.fetchone()
        return QuoteRecord(id, by=by, at=int(at), text=text)

    def search(self, channel, **kwargs):
        criteria = []
        formats = []
        predicateName = ''
        db = self._getDb(channel)
        for v in kwargs['id']:
            criteria.append('id=%s' % v)
        for v in kwargs['with']:
            criteria.append('quote LIKE %s')
            formats.append('%%%s%%' % v)
        for v in kwargs['by']:
            criteria.append('added_by=%s')
            formats.append(arg)
        for p in kwargs['predicate']:
            predicateName += 'p'
            db.create_function(predicateName, 1, p)
            criteria.append('%s(quote)' % predicateName)
        for s in kwargs['args']:
            try:
                i = int(s)
                criteria.append('id=%s' % i)
            except ValueError:
                s = '%%%s%%' % s
                criteria.append('quote LIKE %s')
                formats.append(s)
        sql = """SELECT id, added_by, added_at, quote FROM quotes
                 WHERE %s""" % ' AND '.join(criteria)
        cursor = db.cursor()
        cursor.execute(sql, *formats)
        if cursor.rowcount == 0:
            return None
        elif cursor.rowcount == 1:
            (id, by, at, text) = cursor.fetchone()
            return QuoteRecord(id, by=by, at=int(at), text=text)
        else:
            quotes = []
            for (id, by, at, text) in cursor.fetchall():
                quotes.append(QuoteRecord(id, by=by, at=int(at), text=text))
            return quotes

    def get(self, channel, id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT added_by, added_at, quote FROM quotes
                          WHERE id=%s""", id)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError, id
        (by, at, text) = cursor.fetchone()
        return QuoteRecord(id, by=by, at=int(at), text=text)

    def remove(self, channel, id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""DELETE FROM quotes WHERE id=%s""", id)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError, id
        db.commit()

def QuotesDB():
    return SqliteQuotesDB()

class Quotes(callbacks.Privmsg):
    def __init__(self):
        self.db = QuotesDB()
        callbacks.Privmsg.__init__(self)

    def add(self, irc, msg, args):
        """[<channel>] <quote>

        Adds <quote> to the quotes database for <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        quote = privmsgs.getArgs(args)
        id = self.db.add(channel, msg.nick, quote)
        irc.replySuccess('(Quote #%s added)' % id)

    def stats(self, irc, msg, args):
        """[<channel>]

        Returns the numbers of quotes in the quote database for <channel>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        size = self.db.size(channel)
        s = 'There %s %s in my database.' % \
            (utils.be(size), utils.nItems('quote', size))
        irc.reply(s)

    def _replyQuote(self, irc, quote):
        if isinstance(quote, QuoteRecord):
            irc.reply('#%s: %s' % (quote.id, quote.text))
        elif len(quote) > 10:
            irc.reply('More than 10 quotes matched your criteria.  '
                      'Please narrow your query.')
        else:
            quotes = ['#%s: "%s"' % (q.id, utils.ellipsisify(q.text, 30))
                      for q in quote]
            irc.reply(utils.commaAndify(quotes))

    def search(self, irc, msg, args):
        """[<channel>] --{id,regexp,from,with}=<value> ]

        Returns quote(s) matching the given criteria.  --from is who added the
        quote; --id is the id number of the quote; --regexp is a regular
        expression to search for.
        """
        channel = privmsgs.getChannel(msg, args)
        (optlist, rest) = getopt.getopt(args, '', ['id=', 'regexp=',
                                                   'from=', 'with='])
        if not optlist and not rest:
            raise callbacks.ArgumentError
        kwargs = {'args': rest, 'id': [], 'with': [], 'by': [], 'predicate': []}
        for (option, arg) in optlist:
            option = option.lstrip('-')
            if option == 'id':
                try:
                    arg = int(arg)
                    kwargs[option].append(arg)
                except ValueError:
                    irc.error('--id value must be an integer.')
                    return
            elif option == 'with':
                kwargs[option].append(arg)
            elif option == 'from':
                kwargs['by'].append(arg)
            elif option == 'regexp':
                try:
                    r = utils.perlReToPythonRe(arg)
                except ValueError:
                    try:
                        r = re.compile(arg, re.I)
                    except re.error, e:
                        irc.error(str(e))
                        return
                def p(s):
                    return int(bool(r.search(s)))
                kwargs['predicate'].append(p)
        quote = self.db.search(channel, **kwargs)
        if quote is None:
            irc.reply('No quotes matched that criteria.')
        else:
            self._replyQuote(irc, quote)
        ### FIXME: we need to remove those predicates from the database.

    def random(self, irc, msg, args):
        """[<channel>]

        Returns a random quote from <channel>.  <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        quote = self.db.random(channel)
        if quote:
            self._replyQuote(irc, quote)
        else:
            self.error('I have no quotes for this channel.')

    def info(self, irc, msg, args):
        """[<channel>] <id>

        Returns the metadata about the quote <id> in the quotes
        database for <channel>.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error('Invalid id: %r' % id)
            return
        try:
            quote = self.db.get(channel, id)
            irc.reply(str(quote))
        except dbi.NoRecordError, e:
            irc.error('There isn\'t a quote with that id.')

    def remove(self, irc, msg, args):
        """[<channel>] <id>

        Removes quote <id> from the quotes database for <channel>.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error('That\'s not a valid id: %r' % id)
        try:
            self.db.remove(channel, id)
            irc.replySuccess()
        except KeyError:
            irc.error('There was no such quote.')


Class = Quotes
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
