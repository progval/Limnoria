#!/usr/bin/env python

###
# Copyright (c) 2003, Daniel DiPaolo
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
A module to allow each channel to have "news" which people will be notified of
when they join the channel.  News items may have expiration dates.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import os
import time

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks


class NewsRecord(object):
    __metaclass__ = dbi.Record
    __fields__ = [
        'subject',
        'text',
        'at',
        'expires',
        'by'
        ]
    def __str__(self):
        format = conf.supybot.humanTimestampFormat()
        try:
            user = ircdb.users.getUser(int(self.by)).name
        except ValueError:
            user = self.by
        except KeyError:
            user = 'a user that is no longer registered'
        if int(self.expires) == 0:
            s = '%s (Subject: "%s", added by %s on %s)' % \
                (self.text, self.subject, self.by,
                 time.strftime(format, time.localtime(int(self.at))))
        else:
            s = '%s (Subject: "%s", added by %s on %s, expires at %s)' % \
                (self.text, self.subject, self.by,
                 time.strftime(format, time.localtime(int(self.at))),
                 time.strftime(format, time.localtime(int(self.expires))))
        return s

class SqliteNewsDB(object):
    def __init__(self):
        self.dbs = ircutils.IrcDict()

    def close(self):
        for db in self.dbs.itervalues():
            db.close()

    def _getDb(self, channel):
        try:
            import sqlite
        except ImportError:
            raise callbacks.Error, 'You need to have PySQLite installed to ' \
                                   'use this plugin.  Download it at ' \
                                   '<http://pysqlite.sf.net/>'
        filename = plugins.makeChannelFilename(channel, 'News.db')
        if filename in self.dbs:
            return self.dbs[filename]
        if os.path.exists(filename):
            self.dbs[filename] = sqlite.connect(filename)
            return self.dbs[filename]
        db = sqlite.connect(filename)
        self.dbs[filename] = db
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE news (
                          id INTEGER PRIMARY KEY,
                          subject TEXT,
                          item TEXT,
                          added_at TIMESTAMP,
                          expires_at TIMESTAMP,
                          added_by TEXT
                          )""")
        db.commit()
        return db

    def add(self, channel, subject, text, added_at, expires, by):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("INSERT INTO news VALUES (NULL, %s, %s, %s, %s, %s)",
                       subject, text, added_at, expires, by)
        db.commit()

    def get(self, channel, id=None, old=False):
        db = self._getDb(channel)
        cursor = db.cursor()
        if id:
            cursor.execute("""SELECT item, subject, added_at,
                                     expires_at, added_by
                              FROM news
                              WHERE id=%s""", id)
            if cursor.rowcount == 0:
                raise dbi.NoRecordError, id
            (text, subject, at, expires, by) = cursor.fetchone()
            return NewsRecord(id, text=text, subject=subject, at=int(at),
                              expires=int(expires), by=by)
        else:
            if old:
                cursor.execute("""SELECT id, subject
                                  FROM news
                                  WHERE expires_at <> 0 AND expires_at < %s
                                  ORDER BY id DESC""", int(time.time()))
            else:
                cursor.execute("""SELECT id, subject
                                  FROM news
                                  WHERE expires_at > %s OR expires_at=0""",
                                  int(time.time()))
            if cursor.rowcount == 0:
                raise dbi.NoRecordError
            else:
                return cursor.fetchall()

    def remove(self, channel, id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""DELETE FROM news WHERE id = %s""", id)
        db.commit()
        if cursor.rowcount == 0:
            raise dbi.NoRecordError, id

    def change(self, channel, id, replacer):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT subject, item FROM news WHERE id=%s""", id)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError, id
        (subject, item) = cursor.fetchone()
        s = '%s: %s' % (subject, item)
        s = replacer(s)
        (newSubject, newItem) = s.split(': ', 1)
        cursor.execute("""UPDATE news SET subject=%s, item=%s WHERE id=%s""",
                       newSubject, newItem, id)

def NewsDB():
    return SqliteNewsDB()

class News(callbacks.Privmsg):
    def __init__(self):
        super(News, self).__init__()
        self.db = NewsDB()
        self.removeOld = False

    def die(self):
        super(News, self).die()
        self.db.close()

    def add(self, irc, msg, args, channel):
        """[<channel>] <expires> <subject>: <text>

        Adds a given news item of <text> to a channel with the given <subject>.
        If <expires> isn't 0, that news item will expire <expires> seconds from
        now.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        (expire_interval, news) = privmsgs.getArgs(args, required=2)
        try:
            expire_interval = int(expire_interval)
            (subject, text) = news.split(': ', 1)
        except ValueError:
            raise callbacks.ArgumentError
        added_at = int(time.time())
        expires = expire_interval and (added_at + expire_interval)
        # Set the other stuff needed for the insert.
        try:
            by = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            by = msg.nick
        self.db.add(channel, subject, text, added_at, expires, by)
        irc.replySuccess()
    add = privmsgs.checkChannelCapability(add, 'news')

    def news(self, irc, msg, args):
        """[<channel>] [<id>]

        Display the news items for <channel> in the format of '(#id) subject'.
        If <id> is given, retrieve only that news item; otherwise retrieve all
        news items.  <channel> is only necessary if the message isn't sent in
        the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args, required=0, optional=1)
        if id:
            try:
                record = self.db.get(channel, int(id))
                irc.reply(str(record))
            except dbi.NoRecordError, id:
                irc.errorInvalid('news item id', id)
        else:
            try:
                records = self.db.get(channel)
                items = ['(#%s) %s' % (id, s) for (id, s) in records]
                s = 'News for %s: %s' % (channel, '; '.join(items))
                irc.reply(s)
            except dbi.NoRecordError:
                irc.reply('No news for %s.' % channel)

    def remove(self, irc, msg, args, channel):
        """[<channel>] <number>

        Removes the news item with id <number> from <channel>.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        id = privmsgs.getArgs(args)
        try:
            self.db.remove(channel, id)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.errorInvalid('news item id', id)
    remove = privmsgs.checkChannelCapability(remove, 'news')

    def change(self, irc, msg, args, channel):
        """[<channel>] <number> <regexp>

        Changes the news item with id <number> from <channel> according to the
        regular expression <regexp>.  <regexp> should be of the form
        s/text/replacement/flags.  <channel> is only necessary if the message
        isn't sent on the channel itself.
        """
        (id, regexp) = privmsgs.getArgs(args, required=2)
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error(str(e))
            return
        try:
            self.db.change(channel, id, replacer)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.errorInvalid('news item id', id)
    change = privmsgs.checkChannelCapability(change, 'news')

    def old(self, irc, msg, args):
        """[<channel>] [<number>]

        Returns the old news item for <channel> with id <number>.  If no number
        is given, returns all the old news items in reverse order.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args, required=0, optional=1)
        if id:
            try:
                record = self.db.get(channel, id, old=True)
                irc.reply(str(record))
            except dbi.NoRecordError, id:
                irc.errorInvalid('news item id', id)
        else:
            try:
                records = self.db.get(channel, old=True)
                items = ['(#%s) %s' % (id, s) for (id, s) in records]
                s = 'Old news for %s: %s' % (channel, '; '.join(items))
                irc.reply(s)
            except dbi.NoRecordError:
                irc.reply('No old news for %s.' % channel)


Class = News

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
