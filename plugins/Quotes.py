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

import plugins

import re
import time
import getopt
import os.path

import sqlite

import conf
import utils
import ircdb
import privmsgs
import callbacks

class Quotes(plugins.ChannelDBHandler, callbacks.Privmsg):
    def __init__(self):
        plugins.ChannelDBHandler.__init__(self)
        callbacks.Privmsg.__init__(self)

    def makeDb(self, filename):
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
        cursor.execute("""CREATE TABLE quotegrabs (
                          id INTEGER PRIMARY KEY,
                          nick TEXT,
                          hostmask TEXT,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          quote TEXT
                          );""")
        db.commit()
        return db

    def add(self, irc, msg, args):
        """[<channel>] <quote>

        Adds <quote> to the quotes database for <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        quote = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        quotetime = int(time.time())
        cursor.execute("""INSERT INTO quotes
                         VALUES(NULL, %s, %s, %s)""",
                       msg.nick, quotetime, quote)
        db.commit()
        sql = """SELECT id FROM quotes
                 WHERE added_by=%s AND added_at=%s AND quote=%s"""
        cursor.execute(sql, msg.nick, quotetime, quote)
        quoteid = cursor.fetchone()[0]
        irc.reply(msg, '%s (Quote #%s added)' % (conf.replySuccess, quoteid))

    def num(self, irc, msg, args):
        """[<channel>]

        Returns the numbers of quotes in the quote database for <channel>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM quotes""")
        maxid = int(cursor.fetchone()[0])
        if maxid is None:
            maxid = 0
        QUOTE = utils.pluralize(maxid, 'quote')
        s = 'There %s %s %s in my database.' % (utils.be(maxid), maxid, QUOTE)
        irc.reply(msg, s)

    def get(self, irc, msg, args):
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
        criteria = []
        formats = []
        predicateName = ''
        db = self.getDb(channel)
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'id':
                try:
                    argument = int(argument)
                    criteria.append('id=%s' % argument)
                except ValueError:
                    irc.error(msg, '--id value must be an integer.')
                    return
            elif option == 'with':
                criteria.append('quote LIKE %s')
                formats.append('%%%s%%' % argument)
            elif option == 'from':
                criteria.append('added_by=%s')
                formats.append(argument)
            elif option == 'regexp':
                try:
                    r = utils.perlReToPythonRe(argument)
                except ValueError:
                    try:
                        r = re.compile(argument, re.I)
                    except re.error, e:
                        irc.error(msg, str(e))
                        return
                def p(s):
                    return int(bool(r.search(s)))
                predicateName += 'p'
                db.create_function(predicateName, 1, p)
                criteria.append('%s(quote)' % predicateName)
        for s in rest:
            try:
                i = int(s)
                criteria.append('id=%s' % i)
            except ValueError:
                s = '%%%s%%' % s
                criteria.append('quote LIKE %s')
                formats.append(s)
        sql = """SELECT id, quote FROM quotes
                 WHERE %s""" % ' AND '.join(criteria)
        #debug.printf(sql)
        cursor = db.cursor()
        cursor.execute(sql, *formats)
        if cursor.rowcount == 0:
            irc.reply(msg, 'No quotes matched that criteria.')
        elif cursor.rowcount == 1:
            (id, quote) = cursor.fetchone()
            irc.reply(msg, '#%s: %s' % (id, quote))
        elif cursor.rowcount > 10:
            irc.reply(msg, 'More than 10 quotes matched your criteria.  '
                           'Please narrow your query.')
        else:
            results = cursor.fetchall()
            idsWithSnippets = []
            for (id, quote) in results:
                s = '#%s: "%s..."' % (id, quote[:30])
                idsWithSnippets.append(s)
            irc.reply(msg, utils.commaAndify(idsWithSnippets))
        ### FIXME: we need to remove those predicates from the database.

    def random(self, irc, msg, args):
        """[<channel>]

        Returns a random quote from <channel>.  <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id FROM quotes
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount != 1:
            irc.error(msg, 'It seems that quote database is empty.')
            return
        (id,) = cursor.fetchone()
        self.get(irc, msg, [channel, '--id', str(id)])

    def info(self, irc, msg, args):
        """[<channel>] <id>

        Returns the metadata about the quote <id> in the quotes
        database for <channel>.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM quotes WHERE id=%s""", id)
        if cursor.rowcount == 1:
            (id, added_by, added_at, quote) = cursor.fetchone()
            timestamp = time.strftime(conf.humanTimestampFormat,
                                      time.localtime(int(added_at)))
            irc.reply(msg, 'Quote %r added by %s at %s.' % \
                           (quote, added_by, timestamp))
        else:
            irc.error(msg, 'There isn\'t a quote with that id.')

    def remove(self, irc, msg, args):
        """[<channel>] <id>

        Removes quote <id> from the quotes database for <channel>.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            cursor.execute("""DELETE FROM quotes WHERE id=%s""", id)
            if cursor.rowcount == 0:
                irc.error(msg, 'There was no such quote.')
            else:
                irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)


Class = Quotes
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
