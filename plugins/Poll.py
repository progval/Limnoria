#!/usr/bin/python
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

__revision__ = "$Id$"

import plugins

import os
import time

import conf
import utils
import ircdb
import ircutils
import privmsgs
import callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Poll')

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
                              id INTEGER PRIMARY KEY,
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

    def open(self, irc, msg, args):
        """[<channel>] <question>
        
        Creates a new poll with the given question.
        """
        channel = privmsgs.getChannel(msg, args)
        question = privmsgs.getArgs(args)
        # Must be registered to create a poll
        try:
            userId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO polls
                          VALUES (NULL, %s, %s, 1)""",
                          question, userId)
        db.commit()
        cursor.execute("""SELECT id FROM polls WHERE question=%s""", question)
        id = cursor.fetchone()[0]
        irc.reply(msg, '%s (poll #%s)' % (conf.replySuccess, id))

    def close(self, irc, msg, args):
        """[<channel>] <id>
        
        Closes the poll with the given <id>; further votes will not be allowed.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The id must be an integer.')
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        # Check to make sure that the poll exists
        cursor.execute("""SELECT id FROM polls WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'Id #%s is not an existing poll.')
            return
        cursor.execute("""UPDATE polls SET open=0 WHERE id=%s""", id)
        irc.reply(msg, conf.replySuccess)

    def add(self, irc, msg, args):
        """[<channel>] <id> <option text>
        
        Add an option with the given text to the poll with the given id.
        """
        channel = privmsgs.getChannel(msg, args)
        (poll_id, option) = privmsgs.getArgs(args, required=2)
        try:
            poll_id = int(poll_id)
        except ValueError:
            irc.error(msg, 'The id must be an integer.')
            return
        try:
            userId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT started_by FROM polls
                          WHERE id=%s""",
                          poll_id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such poll.')
            return
        if not ((userId == cursor.fetchone()[0]) or
                (ircdb.checkCapability(userId, 'admin'))):
            irc.error(msg, 'That poll isn\'t yours and you aren\'t an admin.')
            return
        cursor.execute("""INSERT INTO options VALUES
                          (NULL, %s, %s)""",
                          poll_id, option)
        irc.reply(msg, conf.replySuccess)

    def vote(self, irc, msg, args):
        """[<channel>] <poll id> <option id>
        
        Vote for the option with the given id on the poll with the given poll
        id.  This command can also be used to override any previous vote.
        """
        channel = privmsgs.getChannel(msg, args)
        (poll_id, option_id) = privmsgs.getArgs(args, required=2)
        try:
            poll_id = int(poll_id)
            option_id = int(option_id)
        except ValueError:
            irc.error(msg, 'The poll id and option id '
                           'arguments must be an integers.')
            return
        try:
            userId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT open
                          FROM polls WHERE id=%s""",
                          poll_id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such poll.')
            return
        elif cursor.fetchone()[0] == 0:
            irc.error(msg, 'That poll is closed.')
            return
        cursor.execute("""SELECT id FROM options
                          WHERE poll_id=%s
                          AND id=%s""",
                          poll_id, option_id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such option.')
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
        irc.reply(msg, conf.replySuccess)

    def results(self, irc, msg, args):
        """[<channel>] <id>
        
        Shows the results for the poll with the given id.
        """
        channel = privmsgs.getChannel(msg, args)
        poll_id = privmsgs.getArgs(args)
        try:
            poll_id = int(poll_id)
        except ValueError:
            irc.error(msg, 'The id argument must be an integer.')
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, question, started_by, open
                          FROM polls WHERE id=%s""",
                          poll_id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such poll.')
            return
        (id, question, startedBy, open) = cursor.fetchone()
        try:
            startedBy = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            startedBy = 'an unknown user'
            return
        reply = 'Results for poll #%s: "%s" by %s' % \
                (id, question, startedBy)
        cursor.execute("""SELECT count(user_id), option_id
                          FROM votes
                          WHERE poll_id=%s 
                          GROUP BY option_id
                          ORDER BY count(user_id) DESC""",
                          poll_id)
        if cursor.rowcount == 0:
            s = 'This poll has no votes yet.'
        else:
            results = []
            for count, option_id in cursor.fetchall():
                cursor.execute("""SELECT option FROM options
                                  WHERE id=%s""", option_id)
                option = cursor.fetchone()[0]
                results.append('%s: %s' % (option, count))
            s = utils.commaAndify(results)
        reply += ' - %s' % s
        irc.reply(msg, reply)
    
    def list(self, irc, msg, args):
        """takes no arguments.

        Lists the currently open polls for the channel and their ids.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, question FROM polls WHERE open=1""")
        if cursor.rowcount == 0:
            irc.reply(msg, 'This channel currently has no open polls.')
            return
        polls = ['#%s: %r' % (id, q) for id, q in cursor.fetchall()]
        irc.reply(msg, utils.commaAndify(polls))

    def options(self, irc, msg, args):
        """<id>

        Lists the options for the poll with the given id.
        """
        channel = privmsgs.getChannel(msg, args)
        poll_id = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, option FROM options
                          WHERE poll_id=%s""",
                          poll_id)
        if cursor.rowcount == 0:
            irc.reply(msg, 'This poll has no options yet '
                           'or no such poll exists.')
            return
        options = ['%s: %r' % (id, o) for id, o in cursor.fetchall()]
        irc.reply(msg, utils.commaAndify(options))


Class = Poll

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
