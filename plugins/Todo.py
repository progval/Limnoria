#!/usr/bin/python

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
Add the module docstring here.  This will be used by the setup.py script.
"""

import plugins

import time
import getopt
import os.path

import sqlite

import conf
import ircdb
import utils
import privmsgs
import callbacks

dbfilename = os.path.join(conf.dataDir, 'Todo.db')

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Todo')

example = utils.wrapLines("""
Add an example IRC session using this module here.
""")

class Todo(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.makeDB(dbfilename)

    def makeDB(self, filename):
        """create Todo database and tables"""
        if os.path.exists(filename):
            self.db = sqlite.connect(filename)
            return
        self.db = sqlite.connect(filename, converters={'bool': bool})
        cursor = self.db.cursor()
        cursor.execute("""CREATE TABLE todo (
                          id INTEGER PRIMARY KEY,
                          priority INTEGER,
                          added_at TIMESTAMP,
                          userid INTEGER,
                          task TEXT
                          )""")
        self.db.commit()

    def die(self):
        self.db.commit()
        self.db.close()
        del self.db

    def todo(self, irc, msg, args):
        """[<task id>]

        Retrieves a task for the given task id.  If no task id is given, it
        will return a list of task ids that that user has added to their todo
        list.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return

        taskid = privmsgs.getArgs(args, needed=0, optional=1)
        if taskid:
            try:
                taskid = int(taskid)
            except ValueError, e:
                irc.error(msg, 'Invalid task id: %s' % e)
                return
            cursor = self.db.cursor()
            cursor.execute("""SELECT priority, added_at, task FROM todo
                              WHERE id = %s AND userid = %s""", taskid, id)
            if cursor.rowcount == 0:
                irc.reply(msg, 'None of your tasks match that id.')
            else:
                pri, added_at, task = cursor.fetchone()
                if pri == 0:
                    priority = ""
                else:
                    priority = ", priority: %s" % pri
                added_time = time.strftime(conf.humanTimestampFormat,
                                           time.localtime(int(added_at)))
                s = "%s%s (Added at: %s)" % (task, priority, added_time)
                irc.reply(msg, s)
        else:
            cursor = self.db.cursor()
            cursor.execute("""SELECT id FROM todo WHERE userid = %s""", id)
            if cursor.rowcount == 0:
                irc.reply(msg, 'You have no tasks in your todo list.')
            else:
                ids = []
                for (id,) in cursor.fetchall():
                    ids.append(str(id))
                s = 'Task ids: %s' % ', '.join(ids)
                irc.reply(msg, s)
                return

    def addtodo(self, irc, msg, args):
        """[--priority=<num>] <text>

        Adds <text> as a task in your own personal todo list.  The optional
        priority argument allows you to set a task as a high or low priority.
        Any integer is valid.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        (optlist, rest) = getopt.getopt(args, '', ['priority='])  
        priority = 0 
        for (option, arg) in optlist:
            if option == '--priority':
                try:
                    priority = int(arg)
                except ValueError, e:
                    irc.error(msg, 'Invalid priority: %s' % e)
                    return
        cursor = self.db.cursor()
        cursor.execute("""INSERT INTO todo VALUES (NULL, %s, %s, %s, %s)""",
                       priority, int(time.time()), id, ' '.join(rest))
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def removetodo(self, irc, msg, args):
        """<task id>

        Removes <task id> from your personal todo list.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return

        taskid = privmsgs.getArgs(args, needed=1)
        cursor = self.db.cursor()
        cursor.execute("""SELECT * FROM todo
                          WHERE id = %s AND userid = %s""", taskid, id)
        if cursor.rowcount == 0:
            irc.error(msg, 'None of your tasks match that id.')
            return
        cursor.execute("""DELETE FROM todo WHERE id = %s""", taskid)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

Class = Todo

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
