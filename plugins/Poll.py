# -*- coding:utf-8 -*-

###
# Copyright (c) 2002, Stéphan Kochen
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
A module for managing and voting on polls.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.strike

import supybot.plugins as plugins

import os
import time

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class PollError(Exception):
    pass

class OptionRecord(dbi.Record):
    __fields__ = [
        'text',
        'votes'
        ]
    def __str__(self):
        return '#%s: %s' % (self.id, utils.quoted(self.text))

class PollRecord(dbi.Record):
    __fields__ = [
        'by',
        'question',
        'options',
        'status'
        ]
    def __str__(self):
        format = conf.supybot.humanTimestampFormat()
        user = plugins.getUserName(self.by)
        if self.options:
            options = 'Options: %s' % '; '.join(map(str, self.options))
        else:
            options = 'The poll has no options, yet'
        if self.status:
            status = 'open'
        else:
            status = 'closed'
        return 'Poll #%s: %s started by %s. %s.  Poll is %s.' % \
               (self.id, utils.quoted(self.question), user, options, status)

class SqlitePollDB(object):
    def __init__(self, filename):
        self.dbs = ircutils.IrcDict()
        self.filename = filename

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
        filename = plugins.makeChannelFilename(self.filename, channel)
        if filename in self.dbs:
            return self.dbs[filename]
        if os.path.exists(filename):
            self.dbs[filename] = sqlite.connect(filename)
            return self.dbs[filename]
        db = sqlite.connect(filename)
        self.dbs[filename] = db
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE polls (
                          id INTEGER PRIMARY KEY,
                          question TEXT UNIQUE ON CONFLICT IGNORE,
                          started_by INTEGER,
                          open INTEGER)""")
        cursor.execute("""CREATE TABLE options (
                          id INTEGER,
                          poll_id INTEGER,
                          option TEXT,
                          UNIQUE (poll_id, id) ON CONFLICT IGNORE)""")
        cursor.execute("""CREATE TABLE votes (
                          user_id INTEGER,
                          poll_id INTEGER,
                          option_id INTEGER,
                          UNIQUE (user_id, poll_id)
                          ON CONFLICT IGNORE)""")
        db.commit()
        return db

    def get(self, channel, poll_id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT question, started_by, open
                          FROM polls WHERE id=%s""", poll_id)
        if cursor.rowcount:
            (question, by, status) = cursor.fetchone()
        else:
            raise dbi.NoRecordError
        cursor.execute("""SELECT id, option FROM options WHERE poll_id=%s""",
                       poll_id)
        if cursor.rowcount:
            options = [OptionRecord(i, text=o, votes=0)
                       for (i, o) in cursor.fetchall()]
        else:
            options = []
        return PollRecord(poll_id, question=question, status=status, by=by,
                          options=options)

    def open(self, channel, user, question):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO polls VALUES (NULL, %s, %s, 1)""",
                       question, user.id)
        db.commit()
        cursor.execute("""SELECT id FROM polls WHERE question=%s""", question)
        return cursor.fetchone()[0]

    def closePoll(self, channel, id):
        db = self._getDb(channel)
        cursor = db.cursor()
        # Check to make sure that the poll exists
        cursor.execute("""SELECT id FROM polls WHERE id=%s""", id)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        cursor.execute("""UPDATE polls SET open=0 WHERE id=%s""", id)
        db.commit()

    def add(self, channel, user, id, option):
        db = self._getDb(channel)
        cursor = db.cursor()
        # Only the poll starter or an admin can add options
        cursor.execute("""SELECT started_by FROM polls
                          WHERE id=%s""",
                          id)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        if not ((user.id == cursor.fetchone()[0]) or
                (ircdb.checkCapability(user.id, 'admin'))):
            raise PollAddError, \
                    'That poll isn\'t yours and you aren\'t an admin.'
        # and NOBODY can add options once a poll has votes
        cursor.execute("""SELECT COUNT(user_id) FROM votes
                          WHERE poll_id=%s""",
                          id)
        if int(cursor.fetchone()[0]) != 0:
            raise PollAddError, 'Cannot add options to a poll with votes.'
        # Get the next highest id
        cursor.execute("""SELECT MAX(id)+1 FROM options
                          WHERE poll_id=%s""",
                          id)
        option_id = cursor.fetchone()[0] or 1
        cursor.execute("""INSERT INTO options VALUES
                          (%s, %s, %s)""",
                          option_id, id, option)
        db.commit()

    def vote(self, channel, user, id, option):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT open
                          FROM polls WHERE id=%s""",
                          id)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        elif int(cursor.fetchone()[0]) == 0:
            raise PollError, 'That poll is closed.'
        cursor.execute("""SELECT id FROM options
                          WHERE poll_id=%s
                          AND id=%s""",
                          id, option)
        if cursor.rowcount == 0:
            raise PollError, 'There is no such option.'
        cursor.execute("""SELECT option_id FROM votes
                          WHERE user_id=%s AND poll_id=%s""",
                          user.id, id)
        if cursor.rowcount == 0:
            cursor.execute("""INSERT INTO votes VALUES (%s, %s, %s)""",
                           user.id, id, option)
        else:
            cursor.execute("""UPDATE votes SET option_id=%s
                              WHERE user_id=%s AND poll_id=%s""",
                              option, user.id, id)
        db.commit()

    def results(self, channel, poll_id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, question, started_by, open
                          FROM polls WHERE id=%s""",
                          poll_id)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        (id, question, by, status) = cursor.fetchone()
        by = ircdb.users.getUser(by).name
        cursor.execute("""SELECT count(user_id), option_id
                          FROM votes
                          WHERE poll_id=%s
                          GROUP BY option_id
                          UNION
                          SELECT 0, id AS option_id
                          FROM options
                          WHERE poll_id=%s
                          AND id NOT IN (
                                SELECT option_id FROM votes
                                WHERE poll_id=%s)
                          GROUP BY option_id
                          ORDER BY count(user_id) DESC""",
                          poll_id, poll_id, poll_id)
        if cursor.rowcount == 0:
            raise PollError, 'This poll has no votes yet.'
        else:
            options = []
            for count, option_id in cursor.fetchall():
                cursor.execute("""SELECT option FROM options
                                  WHERE id=%s AND poll_id=%s""",
                                  option_id, poll_id)
                option = cursor.fetchone()[0]
                options.append(OptionRecord(option_id, votes=int(count),
                                            text=option))
        return PollRecord(poll_id, question=question, status=status, by=by,
                          options=options)

    def select(self, channel):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, started_by, question
                          FROM polls
                          WHERE open=1""")
        if cursor.rowcount:
            return [PollRecord(id, question=q, by=by, status=1)
                    for (id, by, q) in cursor.fetchall()]
        else:
            raise dbi.NoRecordError

PollDB = plugins.DB('Poll', {'sqlite': SqlitePollDB})

class Poll(callbacks.Privmsg):
    def __init__(self):
        self.__parent = super(Poll, self)
        self.__parent.__init__()
        self.db = PollDB()

    def die(self):
        self.__parent.die()
        self.db.close()

    def poll(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Displays the poll question and options for the given poll id.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        try:
            record = self.db.get(channel, id)
        except dbi.NoRecordError:
            irc.error('There is no poll with id %s.' % id, Raise=True)
        irc.reply(record)
    poll = wrap(poll, ['channeldb', 'id'])

    def open(self, irc, msg, args, channel, user, question):
        """[<channel>] <question>

        Creates a new poll with the given question.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        irc.replySuccess('(poll #%s added)' %
                         self.db.open(channel, user, question))
    open = wrap(open, ['channeldb', 'user', 'text'])

    def close(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Closes the poll with the given <id>; further votes will not be allowed.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        try:
            self.db.closePoll(channel, id)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.errorInvalid('poll id')
    close = wrap(close, ['channeldb', ('id', 'poll')])

    def add(self, irc, msg, args, channel, user, id, option):
        """[<channel>] <id> <option text>

        Add an option with the given text to the poll with the given id.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        try:
            self.db.add(channel, user, id, option)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.errorInvalid('poll id')
        except PollError, e:
            irc.error(str(e))
        irc.replySuccess()
    add = wrap(add, ['channeldb', 'user', ('id', 'poll'), 'text'])

    def vote(self, irc, msg, args, channel, user, id, option):
        """[<channel>] <poll id> <option id>

        Vote for the option with the given id on the poll with the given poll
        id.  This command can also be used to override any previous vote.
        <channel> is only necesssary if the message isn't sent in the channel
        itself.
        """
        try:
            self.db.vote(channel, user, id, option)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.errorInvalid('poll id')
        except PollError, e:
            irc.error(str(e))
    vote = wrap(vote, ['channeldb', 'user', ('id', 'poll'), ('id', 'option')])

    def results(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Shows the results for the poll with the given id.  <channel> is only
        necessary if the message is not sent in the channel itself.
        """
        try:
            poll = self.db.results(channel, id)
            reply = 'Results for poll #%s: "%s" by %s' % \
                    (poll.id, poll.question, poll.by)
            options = poll.options
            L = []
            for option in options:
                L.append('%s: %s' % (utils.quoted(option.text), option.votes))
            s = utils.commaAndify(L)
            reply += ' - %s' % s
            irc.reply(reply)
        except dbi.NoRecordError:
            irc.error('There is no such poll.', Raise=True)
        except PollError, e:
            irc.error(str(e))
    results = wrap(results, ['channeldb', ('id', 'poll')])

    def list(self, irc, msg, args, channel):
        """[<channel>]

        Lists the currently open polls for <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        try:
            polls = self.db.select(channel)
            polls = ['#%s: %s' % (p.id, utils.quoted(p.question))
                     for p in polls]
            irc.reply(utils.commaAndify(polls))
        except dbi.NoRecordError:
            irc.reply('This channel currently has no open polls.')
    list = wrap(list, ['channeldb'])

Class = Poll

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
