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

import conf
import ircdb
import utils
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
    onStart.append('load Todo')

class TodoDB(plugins.DBHandler):
    def makeDb(self, filename):
        """create Todo database and tables"""
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename, converters={'bool': bool})
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE todo (
                              id INTEGER PRIMARY KEY,
                              priority INTEGER,
                              added_at TIMESTAMP,
                              userid INTEGER,
                              task TEXT,
                              active BOOLEAN
                              )""")
            db.commit()
        return db

    
class Todo(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.dbHandler = TodoDB(os.path.join(conf.dataDir, 'Todo'))

    def die(self):
        self.dbHandler.die()
        callbacks.Privmsg.die(self)

    def _shrink(self, s):
        return utils.ellipsisify(s, 50)

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
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        if not userid and not taskid:
            try:
                id = ircdb.users.getUserId(msg.prefix)
            except KeyError:
                irc.error(msg, conf.replyNotRegistered)
                return
            cursor.execute("""SELECT id, task FROM todo
                              WHERE userid = %s AND active = 1
                              ORDER BY priority, id""", id)
            if cursor.rowcount == 0:
                irc.reply(msg, 'You have no tasks in your todo list.')
            else:
                L = ['#%s: %s' % (item[0], self._shrink(item[1]))
                     for item in cursor.fetchall()]
                irc.reply(msg, utils.commaAndify(L))
        else:
            if userid:
                cursor.execute("""SELECT id, task FROM todo
                                  WHERE userid = %s AND active = 1
                                  ORDER BY priority, id""", userid)
                if cursor.rowcount == 0:
                    irc.reply(msg, 'That user has no todos.')
                    return
                L = ['#%s: %s' % (item[0], self._shrink(item[1]))
                     for item in cursor.fetchall()]                    
                if len(L) == 1:
                    s = 'Todo for %s: %s' % (arg, L[0])
                else:
                    s = 'Todos for %s: %s' % (arg, utils.commaAndify(L))
                irc.reply(msg, s)
            else:
                cursor.execute("""SELECT userid,priority,added_at,task,active
                                  FROM todo WHERE id = %s""", taskid)
                if cursor.rowcount == 0:
                    irc.error(msg, '%r is not a valid task id' % taskid)
                    return
                (userid, pri, added_at, task, active) = cursor.fetchone()
                # Construct and return the reply
                user = ircdb.users.getUser(userid)
                if user is None:
                    name = 'a removed user'
                else:
                    name = user.name
                if int(active):
                    active = 'Active'
                else:
                    active = 'Inactive'
                if pri:
                    task += ', priority: %s' % pri
                added_at = time.strftime(conf.humanTimestampFormat,
                                         time.localtime(int(added_at)))
                s = "%s todo for %s: %s (Added at %s)" % \
                    (active, name, task, added_at)
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
        text = privmsgs.getArgs(rest)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        now = int(time.time())
        cursor.execute("""INSERT INTO todo
                          VALUES (NULL, %s, %s, %s, %s, 1)""",
                          priority, now, id, text)
        db.commit()
        cursor.execute("""SELECT id FROM todo 
                          WHERE added_at=%s AND userid=%s""", now, id)
        todoId = cursor.fetchone()[0]
        irc.reply(msg, '%s (Todo #%s added)' % (conf.replySuccess, todoId))

    def remove(self, irc, msg, args):
        """<task id> [<task id> ...]

        Removes <task id> from your personal todo list.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        taskids = privmsgs.getArgs(args)
        tasks = taskids.split()
        #print 'Tasks: %s' % repr(tasks)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        invalid = []
        for taskid in tasks:
            cursor.execute("""SELECT * FROM todo
                              WHERE id = %s AND userid = %s
                              AND active = 1""", taskid, id)
            #print 'Rowcount: %s' % cursor.rowcount
            if cursor.rowcount == 0:
                invalid.append(taskid)
        #print 'Invalid tasks: %s' % repr(invalid)
        if invalid:
            irc.error(msg, 'No tasks were removed because the following '\
                           'tasks could not be removed: %s' % \
                           utils.commaAndify(invalid))
        else:
            for taskid in tasks:
                cursor.execute("""UPDATE todo SET active = 0 WHERE id = %s""",
                               taskid)
            db.commit()
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
        db = self.dbHandler.getDb()
        criteria = ['userid=%s' % id, 'active=1']
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
                db.create_function(predicateName, 1, p)
                predicateName += 'p'
        for glob in rest:
            criteria.append('task LIKE %s')
            formats.append(glob.translate(self._sqlTrans))
        cursor = db.cursor()
        sql = """SELECT id, task FROM todo WHERE %s""" % ' AND '.join(criteria)
        cursor.execute(sql, formats)
        if cursor.rowcount == 0:
            irc.reply(msg, 'No tasks matched that query.')
        else:
            tasks = ['#%s: %s' % (item[0], self._shrink(item[1]))
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
        db = self.dbHandler.getDb()
        cursor = db.cursor()
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
        db.commit()
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
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT task FROM todo
                          WHERE userid = %s AND id = %s
                          AND active = 1""", userid, taskid)
        if cursor.rowcount == 0:
            irc.error(msg, '%r is not a valid task id' % taskid)
            return
        newtext = replacer(cursor.fetchone()[0])
        cursor.execute("""UPDATE todo SET task = %s
                          WHERE id = %s""", newtext, taskid)
        db.commit()
        irc.reply(msg, conf.replySuccess)

Class = Todo

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
