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
The Todo plugin allows registered users to keep their own personal list of
tasks to do, with an optional priority for each.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.strike

import glob
import time
import getopt
import string
import os.path

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.callbacks as callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

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


filename = conf.supybot.directories.data.dirize('Todo.db')
class Todo(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        dataDir = conf.supybot.directories.data()
        self.dbHandler = TodoDB(filename)

    def die(self):
        self.dbHandler.die()
        callbacks.Privmsg.die(self)

    def _shrink(self, s):
        return utils.ellipsisify(s, 50)

    def todo(self, irc, msg, args, user, taskid):
        """[<username>|<task id>]

        Retrieves a task for the given task id.  If no task id is given, it
        will return a list of task ids that that user has added to their todo
        list.
        """
        # Figure out what userid and taskid need to be set to (if anything)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        if not taskid:
            cursor.execute("""SELECT id, task FROM todo
                              WHERE userid = %s AND active = 1
                              ORDER BY priority, id""", user.id)
            if cursor.rowcount == 0:
                irc.reply('That user has no todos.')
                return
            L = ['#%s: %s' % (item[0], self._shrink(item[1]))
                 for item in cursor.fetchall()]
            if len(L) == 1:
                s = 'Todo for %s: %s' % (user.name, L[0])
            else:
                s = 'Todos for %s: %s' % (user.name, utils.commaAndify(L))
            irc.reply(s)
        else:
            cursor.execute("""SELECT userid,priority,added_at,task,active
                              FROM todo WHERE id = %s""", taskid)
            if cursor.rowcount == 0:
                irc.errorInvalid('task id', taskid)
                return
            (userid, pri, added_at, task, active) = cursor.fetchone()
            # Construct and return the reply
            user = plugins.getUserName(userid)
            if int(active):
                active = 'Active'
            else:
                active = 'Inactive'
            if pri:
                task += ', priority: %s' % pri
            added_at = time.strftime(conf.supybot.reply.format.time(),
                                     time.localtime(int(added_at)))
            s = "%s todo for %s: %s (Added at %s)" % \
                (active, user, task, added_at)
            irc.reply(s)
    todo = wrap(todo, [first('otherUser', 'user'), additional(('id', 'task'))])

    def add(self, irc, msg, args, user, optlist, text, now):
        """[--priority=<num>] <text>

        Adds <text> as a task in your own personal todo list.  The optional
        priority argument allows you to set a task as a high or low priority.
        Any integer is valid.
        """
        priority = 0
        for (option, arg) in optlist:
            if option == 'priority':
                priority = arg
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""INSERT INTO todo
                          VALUES (NULL, %s, %s, %s, %s, 1)""",
                          priority, now, user.id, text)
        db.commit()
        cursor.execute("""SELECT id FROM todo
                          WHERE added_at=%s AND userid=%s""", now, user.id)
        todoId = cursor.fetchone()[0]
        irc.replySuccess('(Todo #%s added)' % (todoId))
    add = wrap(add, ['user', getopts({'priority': ('int', 'priority')}),
                     'text', 'now'])

    def remove(self, irc, msg, args, user, tasks):
        """<task id> [<task id> ...]

        Removes <task id> from your personal todo list.
        """
        #print 'Tasks: %s' % repr(tasks)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        invalid = []
        for taskid in tasks:
            cursor.execute("""SELECT * FROM todo
                              WHERE id = %s AND userid = %s
                              AND active = 1""", taskid, user.id)
            #print 'Rowcount: %s' % cursor.rowcount
            if cursor.rowcount == 0:
                invalid.append(taskid)
        #print 'Invalid tasks: %s' % repr(invalid)
        if invalid and len(invalid) == 1:
            irc.error('Task %s could not be removed either because '
                      'that id doesn\'t exist, the todo doesn\'t '
                      'belong to you, or it has been removed '
                      'already.' % invalid[0])
        elif invalid:
            irc.error('No tasks were removed because the following '
                      'tasks could not be removed: %s' %
                      utils.commaAndify(invalid))
        else:
            for taskid in tasks:
                cursor.execute("""UPDATE todo SET active = 0 WHERE id = %s""",
                               taskid)
            db.commit()
            irc.replySuccess()
    remove = wrap(remove, ['user', many(('id', 'task'))])

    _sqlTrans = string.maketrans('*?', '%_')
    def search(self, irc, msg, args, user, optlist, globs):
        """[--{regexp}=<value>] [<glob> <glob> ...]

        Searches your todos for tasks matching <glob>.  If --regexp is given,
        its associated value is taken as a regexp and matched against the
        tasks.
        """
        if not optlist and not globs:
            raise callbacks.ArgumentError
        db = self.dbHandler.getDb()
        criteria = ['userid=%s' % user.id, 'active=1']
        formats = []
        predicateName = 'p'
        for (option, arg) in optlist:
            if option == 'regexp':
                criteria.append('%s(task)' % predicateName)
                def p(s, r=arg):
                    return int(bool(r.search(s)))
                db.create_function(predicateName, 1, p)
                predicateName += 'p'
        for glob in globs:
            criteria.append('task LIKE %s')
            formats.append(glob.translate(self._sqlTrans))
        cursor = db.cursor()
        sql = """SELECT id, task FROM todo WHERE %s""" % ' AND '.join(criteria)
        cursor.execute(sql, formats)
        if cursor.rowcount == 0:
            irc.reply('No tasks matched that query.')
        else:
            tasks = ['#%s: %s' % (item[0], self._shrink(item[1]))
                     for item in cursor.fetchall()]
            irc.reply(utils.commaAndify(tasks))
    search = wrap(search,
                  ['user', getopts({'regexp': 'regexpMatcher'}), any('glob')])

    def setpriority(self, irc, msg, args, user, id, priority):
        """<id> <priority>

        Sets the priority of the todo with the given id to the specified value.
        """
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT userid, priority FROM todo
                          WHERE id = %s AND active = 1""", id)
        if cursor.rowcount == 0:
            irc.error('No note with id %s' % id, Raise=True)
        (userid, oldpriority) = cursor.fetchone()
        if userid != user.id:
            irc.error('Todo #%s does not belong to you.' % id, Raise=True)
        # If we make it here, we're okay
        cursor.execute("""UPDATE todo SET priority = %s
                          WHERE id = %s""", priority, id)
        db.commit()
        irc.replySuccess()
    setpriority = wrap(setpriority,
                       ['user', ('id', 'task'), ('int', 'priority')])

    def change(self, irc, msg, args, user, id, replacer):
        """<task id> <regexp>

        Modify the task with the given id using the supplied regexp.
        """
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT task FROM todo
                          WHERE userid = %s AND id = %s
                          AND active = 1""", user.id, id)
        if cursor.rowcount == 0:
            irc.errorInvalid('task id', id)
        newtext = replacer(cursor.fetchone()[0])
        cursor.execute("""UPDATE todo SET task = %s
                          WHERE id = %s""", newtext, id)
        db.commit()
        irc.replySuccess()
    change = wrap(change, ['user', ('id', 'task'), 'regexpReplacer'])

Class = Todo

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
