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
The Todo module allows registered users to keep their own personal list of
tasks to do, with an optional priority for each.
"""

__revision__ = "$Id$"

import plugins

import glob
import time
import getopt
import string
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
                          task TEXT,
                          active BOOLEAN
                          )""")
        self.db.commit()

    def die(self):
        self.db.commit()
        self.db.close()
        del self.db

    def todo(self, irc, msg, args):
        """[<username>|<task id>]

        Retrieves a task for the given task id.  If no task id is given, it
        will return a list of task ids that that user has added to their todo
        list.
        """
        arg = privmsgs.getArgs(args, required=0, optional=1)

        userid = None
        taskid = None
        # Figure out what userid and taskid need to be set to (if anything)
        if not arg:
            pass
        else:
            try:
                taskid = int(arg)
            except ValueError:
                try:
                    userid = ircdb.users.getUserId(arg)
                except KeyError:
                    irc.error(msg,
                              '%r is not a valid task id or username' % arg)
                    return
        # Everything needs a cursor, might as well plop it outside
        if not userid and not taskid:
            try:
                id = ircdb.users.getUserId(msg.prefix)
            except KeyError:
                irc.error(msg, conf.replyNotRegistered)
                return
            cursor = self.db.cursor()
            cursor.execute("""SELECT id, task FROM todo
                              WHERE userid = %s AND active = 1
                              ORDER BY priority, id""", id)
            if cursor.rowcount == 0:
                irc.reply(msg, 'You have no tasks in your todo list.')
                return
            s = ['#%s: %s' % (item[0], utils.ellipsisify(item[1], 50)) \
                     for item in cursor.fetchall()]
            irc.reply(msg, utils.commaAndify(s))
        else:
            cursor = self.db.cursor() 
            if userid:
                cursor.execute("""SELECT id, task FROM todo
                                  WHERE userid = %s AND active = 1
                                  ORDER BY priority, id""", userid)
                if cursor.rowcount == 0:
                    irc.reply(msg, 'That user has no todos.')
                    return
                s = ['#%s: %s' % (item[0], utils.ellipsisify(item[1], 50)) \
                        for item in cursor.fetchall()]                    
                reply = "%s for %s: %s" % \
                        (utils.pluralize(len(s), 'Todo'), arg,
                         utils.commaAndify(s))
                irc.reply(msg, reply)
                return
            else:
                cursor.execute("""SELECT userid, priority, added_at, task
                                  FROM todo WHERE id = %s
                                  AND active = 1""", taskid)
                if cursor.rowcount == 0:
                    irc.error(msg, '%r is not a valid task id' % taskid)
                    return
                userid, pri, added_at, task = cursor.fetchone()
                # Construct and return the reply
                username = ircdb.users.getUser(userid).name
                if pri == 0:
                    priority = ""
                else:
                    priority = ", priority: %s" % pri
                added_time = time.strftime(conf.humanTimestampFormat,
                                           time.localtime(int(added_at)))
                s = "Todo for %s: %s%s (Added at %s)" % \
                    (username, task, priority, added_time)
                irc.reply(msg, s)

    def add(self, irc, msg, args):
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
                    irc.error(msg, '%r is an invalid priority' % arg)
                    return
        text = privmsgs.getArgs(rest, required=1)
        cursor = self.db.cursor()
        now = int(time.time())
        cursor.execute("""INSERT INTO todo
                          VALUES (NULL, %s, %s, %s, %s, 1)""",
                          priority, now, id, text)
        self.db.commit()
        cursor.execute("""SELECT id FROM todo 
                          WHERE added_at=%s AND userid=%s""", now, id)
        todoId = cursor.fetchone()[0]
        irc.reply(msg, '%s (Todo #%s added)' % (conf.replySuccess, todoId))

    def remove(self, irc, msg, args):
        """<task id>

        Removes <task id> from your personal todo list.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return

        taskid = privmsgs.getArgs(args, required=1)
        cursor = self.db.cursor()
        cursor.execute("""SELECT * FROM todo
                          WHERE id = %s AND userid = %s
                          AND active = 1""", taskid, id)
        if cursor.rowcount == 0:
            irc.error(msg, 'None of your tasks match that id.')
            return
        cursor.execute("""UPDATE todo SET active = 0 WHERE id = %s""", taskid)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    _sqlTrans = string.maketrans('*?', '%_')
    def search(self, irc, msg, args):
        """[--{regexp,exact}=<value>] [<glob>]

        Searches the keyspace for tasks matching <glob>.  If --regexp is given,
        it associated value is taken as a regexp and matched against the tasks;
        if --exact is given, its associated value is taken as an exact string
        to match against the task.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return

        (optlist, rest) = getopt.getopt(args, '', ['regexp=', 'exact='])
        if not optlist and not rest:
            raise callbacks.ArgumentError
        criteria = ['userid = %s' % id, 'active = 1']
        formats = []
        predicateName = 'p'
        for (option, arg) in optlist:
            if option == '--exact':
                criteria.append('task LIKE %s')
                formats.append('%' + arg + '%')
            elif option == '--regexp':
                criteria.append('%s(task)' % predicateName)
                try:
                    r = utils.perlReToPythonRe(arg)
                except ValueError, e:
                    irc.error(msg, '%r is not a valid regular expression' %
                              arg)
                    return
                def p(s, r=r):
                    return int(bool(r.search(s)))
                self.db.create_function(predicateName, 1, p)
                predicateName += 'p'
        for glob in rest:
            criteria.append('task LIKE %s')
            formats.append(glob.translate(self._sqlTrans))
        cursor = self.db.cursor()
        sql = """SELECT id, task FROM todo WHERE %s""" % ' AND '.join(criteria)
        cursor.execute(sql, formats)
        if cursor.rowcount == 0:
            irc.reply(msg, 'No tasks matched that query.')
        else:
            tasks = ['#%s: %s' % (item[0], utils.ellipsisify(item[1], 50)) \
                     for item in cursor.fetchall()]
            irc.reply(msg, utils.commaAndify(tasks))

    def setpriority(self, irc, msg, args):
        """<id> <priority>

        Sets the priority of the todo with the given id to the specified value.
        """
        try:
            user_id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        (id, priority) = privmsgs.getArgs(args, required=2)
        cursor = self.db.cursor()
        cursor.execute("""SELECT userid, priority FROM todo
                          WHERE id = %s AND active = 1""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'No note with id %s' % id)
            return
        (userid, oldpriority) = cursor.fetchone()
        if userid != user_id:
            irc.error(msg, 'Todo #%s does not belong to you.' % id)
            return
        # If we make it here, we're okay
        cursor.execute("""UPDATE todo SET priority = %s
                          WHERE id = %s""", priority, id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def change(self, irc, msg, args):
        """<task id> <regexp>

        Modify the task with the given id using the supplied regexp.
        """
        try:
            userid = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        taskid, regexp = privmsgs.getArgs(args, required=2)
        # Check the regexp first, it's easier and doesn't require a db query
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError:
            irc.error(msg, '%r is not a valid regexp' % regexp)
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT task FROM todo
                          WHERE userid = %s AND id = %s
                          AND active = 1""", userid, taskid)
        if cursor.rowcount == 0:
            irc.error(msg, '%r is not a valid task id' % taskid)
            return
        newtext = replacer(cursor.fetchone()[0])
        cursor.execute("""UPDATE todo SET task = %s
                          WHERE id = %s""", newtext, taskid)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

Class = Todo

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
