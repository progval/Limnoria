#!/usr/bin/env python
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

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

class Poll(callbacks.Privmsg, plugins.ChannelDBHandler):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        plugins.ChannelDBHandler.__init__(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename)
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

    def _getUserId(self, prefix):
        try:
            return ircdb.users.getUserId(prefix)
        except KeyError:
            irc.errorNotRegistered(Raise=True)

    def _getUserName(self, id):
        try:
            return ircdb.users.getUser(int(id)).name
        except KeyError:
            return 'an unknown user'

    def _getId(self, irc, idStr):
        try:
            return int(idStr)
        except ValueError:
            irc.error('The id must be a valid integer.', Raise=True)

    def poll(self, irc, msg, args):
        """[<channel>] <id>

        Displays the poll question and options for the given poll id.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        poll_id = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT question, started_by, open
                          FROM polls WHERE id=%s""", poll_id)
        if cursor.rowcount == 0:
            irc.error('There is no poll with id %s.' % poll_id)
            return
        question, started_by, open = cursor.fetchone()
        starter = ircdb.users.getUser(started_by).name
        if open:
            statusstr = 'open'
        else:
            statusstr = 'closed'
        cursor.execute("""SELECT id, option FROM options WHERE poll_id=%s""",
                       poll_id)
        if cursor.rowcount == 0:
            optionstr = 'This poll has no options yet'
        else:
            options = cursor.fetchall()
            optionstr = 'Options: %s' %\
                    ' '.join(['%s: %r' % tuple(t) for t in options])
        pollstr = 'Poll #%s: %r started by %s.  %s.  Poll is %s.' % \
                  (poll_id, question, starter, optionstr, statusstr)
        irc.reply(pollstr)

    def open(self, irc, msg, args):
        """[<channel>] <question>

        Creates a new poll with the given question.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        question = privmsgs.getArgs(args)
        userId = self._getUserId(msg.prefix)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO polls VALUES (NULL, %s, %s, 1)""",
                       question, userId)
        db.commit()
        cursor.execute("""SELECT id FROM polls WHERE question=%s""", question)
        id = cursor.fetchone()[0]
        irc.replySuccess('(poll #%s added)' % id)

    def close(self, irc, msg, args):
        """[<channel>] <id>

        Closes the poll with the given <id>; further votes will not be allowed.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        id = self._getId(irc, id)
        db = self.getDb(channel)
        cursor = db.cursor()
        # Check to make sure that the poll exists
        cursor.execute("""SELECT id FROM polls WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error('Id #%s is not an existing poll.')
            return
        cursor.execute("""UPDATE polls SET open=0 WHERE id=%s""", id)
        irc.replySuccess()

    def add(self, irc, msg, args):
        """[<channel>] <id> <option text>

        Add an option with the given text to the poll with the given id.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (poll_id, option) = privmsgs.getArgs(args, required=2)
        poll_id = self._getId(irc, poll_id)
        userId = self._getUserId(msg.prefix)
        db = self.getDb(channel)
        cursor = db.cursor()
        # Only the poll starter or an admin can add options
        cursor.execute("""SELECT started_by FROM polls
                          WHERE id=%s""",
                          poll_id)
        if cursor.rowcount == 0:
            irc.error('There is no such poll.')
            return
        if not ((userId == cursor.fetchone()[0]) or
                (ircdb.checkCapability(userId, 'admin'))):
            irc.error('That poll isn\'t yours and you aren\'t an admin.')
            return
        # and NOBODY can add options once a poll has votes
        cursor.execute("""SELECT COUNT(user_id) FROM votes
                          WHERE poll_id=%s""",
                          poll_id)
        if int(cursor.fetchone()[0]) != 0:
            irc.error('Cannot add options to a poll with votes.')
            return
        # Get the next highest id
        cursor.execute("""SELECT MAX(id)+1 FROM options
                          WHERE poll_id=%s""",
                          poll_id)
        option_id = cursor.fetchone()[0] or 1
        cursor.execute("""INSERT INTO options VALUES
                          (%s, %s, %s)""",
                          option_id, poll_id, option)
        irc.replySuccess()

    def vote(self, irc, msg, args):
        """[<channel>] <poll id> <option id>

        Vote for the option with the given id on the poll with the given poll
        id.  This command can also be used to override any previous vote.
        <channel> is only necesssary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (poll_id, option_id) = privmsgs.getArgs(args, required=2)
        poll_id = self._getId(irc, poll_id)
        option_id = self._getId(irc, option_id)
        userId = self._getUserId(msg.prefix)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT open
                          FROM polls WHERE id=%s""",
                          poll_id)
        if cursor.rowcount == 0:
            irc.error('There is no such poll.')
            return
        elif int(cursor.fetchone()[0]) == 0:
            irc.error('That poll is closed.')
            return
        cursor.execute("""SELECT id FROM options
                          WHERE poll_id=%s
                          AND id=%s""",
                          poll_id, option_id)
        if cursor.rowcount == 0:
            irc.error('There is no such option.')
            return
        cursor.execute("""SELECT option_id FROM votes
                          WHERE user_id=%s AND poll_id=%s""",
                          userId, poll_id)
        if cursor.rowcount == 0:
            cursor.execute("""INSERT INTO votes VALUES (%s, %s, %s)""",
                           userId, poll_id, option_id)
        else:
            cursor.execute("""UPDATE votes SET option_id=%s
                              WHERE user_id=%s AND poll_id=%s""",
                              option_id, userId, poll_id)
        irc.replySuccess()

    def results(self, irc, msg, args):
        """[<channel>] <id>

        Shows the results for the poll with the given id.  <channel> is only
        necessary if the message is not sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        poll_id = privmsgs.getArgs(args)
        poll_id = self._getId(irc, poll_id)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, question, started_by, open
                          FROM polls WHERE id=%s""",
                          poll_id)
        if cursor.rowcount == 0:
            irc.error('There is no such poll.')
            return
        (id, question, startedBy, open) = cursor.fetchone()
        startedBy = self._getUserName(startedBy)
        reply = 'Results for poll #%s: "%s" by %s' % \
                (id, question, startedBy)
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
            s = 'This poll has no votes yet.'
        else:
            results = []
            for count, option_id in cursor.fetchall():
                cursor.execute("""SELECT option FROM options
                                  WHERE id=%s AND poll_id=%s""",
                                  option_id, poll_id)
                option = cursor.fetchone()[0]
                results.append('%r: %s' % (option, int(count)))
            s = utils.commaAndify(results)
        reply += ' - %s' % s
        irc.reply(reply)

    def list(self, irc, msg, args):
        """[<channel>]

        Lists the currently open polls for <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, question FROM polls WHERE open=1""")
        if cursor.rowcount == 0:
            irc.reply('This channel currently has no open polls.')
        else:
            polls = ['#%s: %r' % tuple(t) for t in cursor.fetchall()]
            irc.reply(utils.commaAndify(polls))

Class = Poll

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
