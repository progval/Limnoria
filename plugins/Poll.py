#!/usr/bin/python
# -*- coding:iso-8859-1 -*-

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

example = utils.wrapLines("""
mooooo
""")

dbFilename = os.path.join(conf.dataDir, 'Poll.db')

def makeDb(dbfilename, replace=False):
    if os.path.exists(dbfilename):
        if replace:
            os.remove(dbfilename)
    db = sqlite.connect(dbfilename)
    cursor = db.cursor()
    try:
        cursor.execute("""SELECT * FROM polls LIMIT 1""")
    except sqlite.DatabaseError:
        cursor.execute("""CREATE TABLE polls (
                          id INTEGER PRIMARY KEY,
                          question TEXT,
                          started_by INTEGER,
                          yes INTEGER,
                          no INTEGER,
                          expires TIMESTAMP)""")
    try:
        cursor.execute("""SELECT * FROM votes LIMIT 1""")
    except sqlite.DatabaseError:
        cursor.execute("""CREATE TABLE votes (
                          user_id INTEGER,
                          poll_id INTEGER,
                          vote BOOLEAN)""")
    db.commit()
    return db

class Poll(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = makeDb(dbFilename)

    def new(self, irc, msg, args):
        """[<lifespan in seconds>] <question>
        
        Creates a new poll with the given question and optional lifespan.
        Without a lifespan the poll will never expire and accept voting
        until it is closed or deleted.
        """
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
        
        cursor = self.db.cursor()
        cursor.execute("""INSERT INTO polls VALUES
                          (NULL, %s, %s, 0, 0, %s)""", question,
                       userId, lifespan)
        self.db.commit()
        cursor.execute("""SELECT id FROM polls WHERE question=%s""", question)
        id = cursor.fetchone()[0]
        irc.reply(msg, '%s (poll #%s)' % (conf.replySuccess, id))

    def open(self, irc, msg, args):
        """[<lifespan in seconds>] <id>
        
        Reopens a closed poll with the given <id> and optional lifespan.
        Without a lifespan the poll will never expire and accept voting
        until it is closed or deleted.
        """
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
        
        cursor = self.db.cursor()
        cursor.execute("""UPDATE polls SET expires=%s WHERE id=%s""",
                       lifespan, id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def close(self, irc, msg, args):
        """<id>
        
        Closes the poll with the given <id>; further votes will not be allowed.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        
        cursor = self.db.cursor()
        cursor.execute("""UPDATE polls SET expires=%s WHERE id=%s""",
                       int(time.time()), id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def delete(self, irc, msg, args):
        """<id>
        
        Deletes the poll with the given <id> from the history (thus also 
        closing it if it's still active).
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        
        cursor = self.db.cursor()
        cursor.execute("""DELETE FROM polls WHERE id=%s""", id)
        cursor.execute("""DELETE FROM votes WHERE poll_id=%s""", id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def vote(self, irc, msg, args):
        """<id> <Yes,No>
        
        Vote yes or no on an active poll with the given id. This command can 
        also be used to override the previous vote.
        """
        (id, vote) = privmsgs.getArgs(args, needed=2)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if vote.capitalize() == 'Yes':
            vote = 1
        elif vote.capitalize() == 'No':
            vote = 0
        else:
            raise callbacks.ArgumentError
        try:
            userId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        
        cursor = self.db.cursor()
        cursor.execute("""SELECT yes, no, expires FROM polls WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such poll.')
            return
        (yVotes, nVotes, expires) = cursor.fetchone()
        expires = float(expires)
        if expires != 0 and time.time() >= expires:
            irc.error(msg, 'That poll is closed.')
            return
        
        cursor.execute("""SELECT vote FROM votes WHERE user_id=%s
                          AND poll_id=%s""", userId, id)
        if cursor.rowcount == 0:
            cursor.execute("""INSERT INTO votes VALUES (%s, %s, %s)""",
                           userId, id, vote)
            if vote:
               yVotes += 1
               sql = """UPDATE polls SET yes=%s WHERE id=%%s""" % yVotes
            else:
               nVotes += 1
               sql = """UPDATE polls SET no=%s WHERE id=%%s""" % nVotes
            cursor.execute(sql, id)
            self.db.commit()
            irc.reply(msg, 'You voted %s on poll #%s.'\
                           % (ircutils.bold(args[1].capitalize()), id))
        else:
            oldVote = cursor.fetchone()[0]
            if vote == int(oldVote):
                irc.error(msg, 'You already voted %s on that poll.'\
                               % ircutils.bold(args[1].capitalize()))
                return
            elif vote:
                yVotes += 1
                nVotes -= 1
            else:
                nVotes += 1
                yVotes -= 1
            cursor.execute("""UPDATE polls SET yes=%s, no=%s WHERE id=%s""",
                           yVotes, nVotes, id)
            cursor.execute("""UPDATE votes SET vote=%s WHERE user_id=%s
                              AND poll_id=%s""", vote, userId, id)
            self.db.commit()
            irc.reply(msg, 'Your vote on poll #%s has been updated to %s.'\
                           % (id, ircutils.bold(args[1].capitalize())))

    def results(self, irc, msg, args):
        """<id>
        
        Shows the (current) results for the poll with the given id.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        
        cursor = self.db.cursor()
        cursor.execute("""SELECT * FROM polls WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such poll.')
            return
        (id, question, startedBy, yVotes, nVotes, expires) = cursor.fetchone()
        tVotes = yVotes + nVotes
        try:
            startedBy = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            startedBy = 'an unknown user'
            return
        reply = 'Results for poll #%s: "%s" by %s' % (id, question, startedBy)
        if tVotes == 0:
            reply = '%s - There have been no votes on this poll yet.' % reply
        else:
            pc = lambda x: int(float(x) / float(tVotes) * 100.0)
            reply = '%s - %s %s (%s%%), %s %s (%s%%), %s %s.'\
                    % (reply, ircutils.bold('Yes:'), yVotes, pc(yVotes),
                       ircutils.bold('No:'), nVotes, pc(nVotes),
                       ircutils.bold('Total votes:'), tVotes)
        expires = float(expires)
        if expires != 0:
            if time.time() >= expires:
                reply = '%s Poll is closed.' % reply
            else:
                reply = '%s Poll expires on %s %s' % (reply,
                        time.asctime(time.localtime(expires)),
                        time.tzname[0])
        irc.reply(msg, reply)


Class = Poll

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
