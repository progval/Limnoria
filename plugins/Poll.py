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

import plugins

import utils
import ircdb
import ircutils
import privmsgs
import callbacks
import conf
import debug

import os.path
import time
import sqlite


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
                              question TEXT,
                              started_by INTEGER,
                              expires INTEGER)""")
            cursor.execute("""CREATE TABLE options (
                              poll_id INTEGER,
                              option_id INTEGER,
                              option TEXT,
                              votes INTEGER,
                              PRIMARY KEY (poll_id, option_id)
                              ON CONFLICT IGNORE)""")
            cursor.execute("""CREATE TABLE votes (
                              user_id INTEGER,
                              poll_id INTEGER,
                              option_id INTERER)""")
            db.commit()
        return db

    def new(self, irc, msg, args):
        """[<channel>] [<lifespan in seconds>] <question>
        
        Creates a new poll with the given question and optional lifespan.
        Without a lifespan the poll will never expire and accept voting
        until it is closed.
        """
        channel = privmsgs.getChannel(msg, args)
        (lifespan, question) = privmsgs.getArgs(args, optional=1)
        try:
            lifespan = int(lifespan)
        except ValueError:
            if question:
                question = '%s %s' % (lifespan, question)
            else:
                question = lifespan
            lifespan = 0
        if lifespan:
            lifespan += time.time()
        if not question:
            raise callbacks.ArgumentError
        try:
            userId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO polls VALUES
                          (NULL, %%s, %s, %s)""" % (userId, lifespan),
                       question)
        db.commit()
        cursor.execute("""SELECT id FROM polls WHERE question=%s""", question)
        id = cursor.fetchone()[0]
        irc.reply(msg, '%s (poll #%s)' % (conf.replySuccess, id))

    def open(self, irc, msg, args):
        """[<channel>] [<lifespan in seconds>] <id>
        
        Reopens a closed poll with the given <id> and optional lifespan.
        Without a lifespan the poll will never expire and accept voting
        until it is closed.
        """
        channel = privmsgs.getChannel(msg, args)
        (lifespan, id) = privmsgs.getArgs(args, optional=1)
        if not id:
            id = lifespan
            lifespan = 0
        else:
            try:
                lifespan = int(lifespan)
            except ValueError:
                irc.error(msg, 'The <lifespan> argument must be an integer.')
                return
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if lifespan:
            lifespan += time.time()
        
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE polls SET expires=%s WHERE id=%s""" % \
                       (lifespan, id))
        db.commit()
        irc.reply(msg, conf.replySuccess)

    def close(self, irc, msg, args):
        """[<channel>] <id>
        
        Closes the poll with the given <id>; further votes will not be allowed.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return

        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE polls SET expires=%s WHERE id=%s""" % \
                       (int(time.time()), id))
        db.commit()
        irc.reply(msg, conf.replySuccess)

    def add(self, irc, msg, args):
        """[<channel>] <id> <option>
        
        Add an option to poll <id>.
        """
        channel = privmsgs.getChannel(msg, args)
        (id, option) = privmsgs.getArgs(args, required=2)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return

        try:
            userId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return

        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT started_by FROM polls WHERE id=%s""" % id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such poll.')
            return
        elif userId != cursor.fetchone()[0]:
            irc.error(msg, 'That poll isn\'t yours.')
            return

        cursor.execute("""INSERT INTO options VALUES
                          (%s, NULL, %%s, 0)""" % id, option)
        db.commit()
        cursor.execute("""SELECT option_id FROM options
                          WHERE poll_id=%s
                          AND votes=0
                          AND option=%%s""" % id, option)
        irc.reply(msg, '%s (option #%s)' % (conf.replySuccess, cursor.fetchone()[0]))

    def vote(self, irc, msg, args):
        """[<channel>] <poll id> <option id>
        
        Vote <option id> on an active poll with the given <poll id>.
        This command can also be used to override the previous vote.
        """
        channel = privmsgs.getChannel(msg, args)
        (id, option) = privmsgs.getArgs(args, required=2)
        try:
            id = int(id)
            option = int(option)
        except ValueError:
            irc.error(msg, 'The <poll id> and <option id> '
                           'arguments must be an integers.')
            return
        try:
            userId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return

        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT expires
                          FROM polls WHERE id=%s""" % id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such poll.')
            return
        expires = cursor.fetchone()[0]
        if expires and time.time() >= expires:
            irc.error(msg, 'That poll is closed.')
            return

        cursor.execute("""SELECT option_id FROM options
                          WHERE poll_id=%s
                          AND option_id=%s""" % (id, option))
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such option.')
            return

        cursor.execute("""SELECT vote FROM votes WHERE user_id=%s
                          AND poll_id=%s""" % (userId, id))
        if cursor.rowcount == 0:
            cursor.execute("""INSERT INTO votes VALUES (%s, %s, %s)""" % \
                           (userId, id, option))
            db.commit()
            irc.reply(msg, 'You voted option #%s on poll #%s.' % (option, id))
        else:
            oldVote = int(cursor.fetchone()[0])
            if option == oldVote:
                irc.error(msg, 'You already voted option #%s '
                               'on that poll.' % option)
                return
            cursor.execute("""UPDATE options SET votes=votes-1
                              WHERE poll_id=%s AND option_id=%s""" \
                           % (id, oldVote))
            cursor.execute("""UPDATE options SET votes=votes+1
                              WHERE poll_id=%s AND option_id=%s""" \
                           % (id, option))
            cursor.execute("""UPDATE votes SET option_id=%s WHERE user_id=%s
                              AND poll_id=%s""" % (option, userId, id))
            db.commit()
            irc.reply(msg, 'Your vote on poll #%s has been updated to option '
                           '#%s.' % (id, option))

    def results(self, irc, msg, args):
        """[<channel>] <id>
        
        Shows the (current) results for the poll with the given id.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM polls WHERE id=%s""" % id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such poll.')
            return
        (id, question, startedBy, expires) = cursor.fetchone()
        try:
            startedBy = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            startedBy = 'an unknown user'
            return
        reply = 'Results for poll #%s: "%s" by %s' % \
                (ircutils.bold(id), question, ircutils.bold(startedBy))
        cursor.execute("""SELECT option_id, option, votes FROM options
                          WHERE poll_id=%s ORDER BY option_id""" % id)
        totalVotes = 0
        results = []
        if cursor.rowcount == 0:
            reply = '%s - This poll has no options yet.' % reply
        else:
            for (optionId, option, votes) in cursor.fetchall():
                if votes == 0:
                    percent = 0
                else:
                    percent = int(float(votes) / float(totalVotes) * 100.0)
                results.append('%s. %s: %s (%s%%)'\
                               % (ircutils.bold(option_id), option,
                                  ircutils.bold(votes), percent))
            reply = '%s - %s' % (reply, utils.commaAndify(results))
        expires = int(expires)
        if expires:
            if time.time() >= expires:
                reply = '%s - Poll is closed.' % reply
            else:
                expires -= time.time()
                reply = '%s - Poll expires in %s' % (reply,
                        utils.timeElapsed(expires))
        irc.reply(msg, reply)


Class = Poll

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
