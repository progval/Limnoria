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

import plugins

import os
import time

import sqlite

import conf
import ircdb
import utils
import privmsgs
import callbacks

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load News')

example = utils.wrapLines("""
<Strike> !listnews
<strikebot> Strike: News for #sourcereview: (#1) Test; (#3) Expiration test
five-million-and-one; (#5) no expire
<Strike> !readnews 1
<strikebot> Strike: no expiration (Subject: "Test", added by Strike on 10:15
PM, September 03, 2003, expires at 12:00 AM, September 12, 2003)
<Strike> !addnews 5000 Another test news item: Here is the news text, much
longer than the subject should be.  The subject should be short and sweet like
a headline whereas the text can be a lot more detailed.
<strikebot> Strike: The operation succeeded.
<Strike> !listnews
<strikebot> Strike: News for #sourcereview: (#1) Test; (#3) Expiration test
five-million-and-one; (#5) no expire; (#7) Another test news item
<Strike> !readnews 7
<strikebot> Strike: Here is the news text, much longer than the subject should
be. The subject should be short and sweet like a headline whereas the text can
be a lot more detailed. (Subject: "Another test news item", added by Strike on
07:12 PM, September 12, 2003, expires at 08:36 PM, September 12, 2003)
""")

class News(plugins.ChannelDBHandler, callbacks.Privmsg):
    def __init__(self):
        plugins.ChannelDBHandler.__init__(self)
        callbacks.Privmsg.__init__(self)
        self.removeOld = False

    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(filename)
        db = sqlite.connect(filename)
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

    def add(self, irc, msg, args, channel):
        """[<channel>] <expires> <subject>: <text>

        Adds a given news item of <text> to a channel with the given <subject>.
        If <expires> isn't 0, that news item will expire <expires> seconds from
        now.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        # Parse out the args
        i = None
        for i, arg in enumerate(args):
            if arg.endswith(':'):
                i += 1
                break
        if not i:
            raise callbacks.ArgumentError
        added_at = int(time.time())
        expire_interval = int(args[0])
        expires = expire_interval and (added_at + expire_interval)
        subject = ' '.join(args[1:i])
        text = ' '.join(args[i:])
        # Set the other stuff needed for the insert.
        if ircdb.users.hasUser(msg.prefix):
            name = ircdb.users.getUser(msg.prefix).name
        else:
            name = msg.nick

        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("INSERT INTO news VALUES (NULL, %s, %s, %s, %s, %s)",
                       subject[:-1], text, added_at, expires, name)
        db.commit()
        irc.reply(msg, conf.replySuccess)
    add = privmsgs.checkChannelCapability(add, 'news')

    def _readnews(self, irc, msg, args):
        """[<channel>] <number>

        Display the text for news item with id <number> from <channel>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT news.item, news.subject, news.added_at,
                          news.expires_at, news.added_by FROM news
                          WHERE news.id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'No news item matches that id.')
        else:
            item, subject, added_at, expires_at, added_by = cursor.fetchone()
            if int(expires_at) == 0:
                s = '%s (Subject: "%s", added by %s on %s)' % \
                    (item, subject, added_by,
                     time.strftime(conf.humanTimestampFormat,
                                   time.localtime(int(added_at))))
            else:
                s = '%s (Subject: "%s", added by %s on %s, expires at %s)' % \
                    (item, subject, added_by,
                     time.strftime(conf.humanTimestampFormat,
                                   time.localtime(int(added_at))),
                     time.strftime(conf.humanTimestampFormat,
                                   time.localtime(int(expires_at))))
            irc.reply(msg, s)

    def news(self, irc, msg, args):
        """[<channel>] [<number>]

        Display the news items for <channel> in the format of '(#id) subject'.
        If <number> is given, retrieve only that news item; otherwise retrieve
        all news items.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        number = privmsgs.getArgs(args, needed=0, optional=1)
        if number:
            self._readnews(irc, msg, [channel, number])
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT news.id, news.subject FROM news
                          WHERE news.expires_at > %s
                          OR news.expires_at=0""", int(time.time()))
        if cursor.rowcount == 0:
            irc.reply(msg, 'No news for %s' % channel)
        else:
            items = ['(#%s) %s' % (id, s) for (id, s) in cursor.fetchall()]
            s = 'News for %s: %s' % (channel, '; '.join(items))
            irc.reply(msg, s)

    def remove(self, irc, msg, args, channel):
        """[<channel>] <number>

        Removes the news item with id <number> from <channel>.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        id = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM news WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'No news item matches that id.')
        else:
            cursor.execute("""DELETE FROM news WHERE news.id = %s""", id)
            db.commit()
            irc.reply(msg, conf.replySuccess)
    remove = privmsgs.checkChannelCapability(remove, 'news')
            
    def change(self, irc, msg, args, channel):
        """[<channel>] <number> <regexp>

        Changes the news item with id <number> from <channel> according to the
        regular expression <regexp>.  <regexp> should be of the form
        s/text/replacement/flags.  <channel> is only necessary if the message
        isn't sent on the channel itself.
        """
        (id, regexp) = privmsgs.getArgs(args, needed=2)
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error(msg, str(e))
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT subject, item FROM news WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'No news item matches that id.')
            return
        (subject, item) = cursor.fetchone()
        s = '%s: %s' % (subject, item)
        s = replacer(s)
        (newSubject, newItem) = s.split(': ')
        cursor.execute("""UPDATE news SET subject=%s, item=%s WHERE id=%s""",
                       newSubject, newItem, id)
        irc.reply(msg, conf.replySuccess)
    change = privmsgs.checkChannelCapability(change, 'news')

    def old(self, irc, msg, args):
        """[<channel>] [<number>]

        Returns the old news item for <channel> with id <number>.  If no number
        is given, returns all the old news items in reverse order.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args, needed=0, optional=1)
        db = self.getDb(channel)
        cursor = db.cursor()
        if id:
            try:
                id = int(id)
            except ValueError:
                irc.error(msg, '%r isn\'t a valid id.' % id)
                return
            cursor.execute("""SELECT subject, item FROM news WHERE id=%s""",id)
            if cursor.rowcount == 0:
                irc.error(msg, 'No news item matches that id.')
            else:
                (subject, item) = cursor.fetchone()
                irc.reply(msg, '%s: %s' % (cursor, item))
        else:
            cursor.execute("""SELECT id, subject FROM news
                              WHERE expires_at <> 0 AND expires_at < %s
                              ORDER BY id DESC""", int(time.time()))
            if cursor.rowcount == 0:
                irc.error(msg, 'I have no news for that channel.')
                return
            subjects = ['#%s: %s' % (id, s) for (id, s) in cursor.fetchall()]
            irc.reply(msg, utils.commaAndify(subjects))
            


                    
Class = News

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
