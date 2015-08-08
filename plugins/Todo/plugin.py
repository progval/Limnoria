###
# Copyright (c) 2003-2005, Daniel DiPaolo
# Copyright (c) 2010, James McCoy
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

import os
import re
import time
import operator

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import commands
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Todo')

class TodoRecord(dbi.Record):
    __fields__ = [
          ('priority', int),
          'at',
          'task',
          'active',
          ]

dataDir = conf.supybot.directories.data

class FlatTodoDb(object):
    def __init__(self):
        self.directory = dataDir.dirize('Todo')
        if not os.path.exists(self.directory):
            os.mkdir(self.directory)
        self.dbs = {}

    def _getDb(self, uid):
        dbfile = os.path.join(self.directory, str(uid))
        if uid not in self.dbs:
            self.dbs[uid] = dbi.DB(dbfile, Record=TodoRecord)
        return self.dbs[uid]

    def close(self):
        for db in self.dbs.values():
            db.close()

    def get(self, uid, tid):
        db = self._getDb(uid)
        return db.get(tid)

    def getTodos(self, uid):
        db = self._getDb(uid)
        L = [R for R in db.select(lambda r: r.active)]
        if not L:
            raise dbi.NoRecordError
        return L

    def add(self, priority, now, uid, task):
        db = self._getDb(uid)
        return db.add(TodoRecord(priority=priority, at=now,
                                 task=task, active=True))

    def remove(self, uid, tid):
        db = self._getDb(uid)
        t = db.get(tid)
        t.active = False
        db.set(tid, t)

    def select(self, uid, criteria):
        db = self._getDb(uid)
        def match(todo):
            for p in criteria:
                if not p(todo.task):
                    return False
            return True
        todos = db.select(lambda t: match(t))
        if not todos:
            raise dbi.NoRecordError
        return todos

    def setpriority(self, uid, tid, priority):
        db = self._getDb(uid)
        t = db.get(tid)
        t.priority = priority
        db.set(tid, t)

    def change(self, uid, tid, replacer):
        db = self._getDb(uid)
        t = db.get(tid)
        t.task = replacer(t.task)
        db.set(tid, t)

class Todo(callbacks.Plugin):
    """This plugin allows you to create your own personal to-do list on
    the bot."""
    def __init__(self, irc):
        self.__parent = super(Todo, self)
        self.__parent.__init__(irc)
        self.db = FlatTodoDb()

    def die(self):
        self.__parent.die()
        self.db.close()

    def _shrink(self, s):
        return utils.str.ellipsisify(s, 50)

    @internationalizeDocstring
    def todo(self, irc, msg, args, user, taskid):
        """[<username>] [<task id>]

        Retrieves a task for the given task id.  If no task id is given, it
        will return a list of task ids that that user has added to their todo
        list.
        """
        try:
            u = ircdb.users.getUser(msg.prefix)
        except KeyError:
            u = None
        if u != user and not self.registryValue('allowThirdpartyReader'):
            irc.error(_('You are not allowed to see other users todo-list.'))
            return
        # List the active tasks for the given user
        if not taskid:
            try:
                tasks = self.db.getTodos(user.id)
                utils.sortBy(operator.attrgetter('priority'), tasks)
                tasks = [format(_('#%i: %s'), t.id, self._shrink(t.task))
                         for t in tasks]
                Todo = 'Todo'
                if len(tasks) != 1:
                    Todo = 'Todos'
                irc.reply(format(_('%s for %s: %L'),
                                 Todo, user.name, tasks))
            except dbi.NoRecordError:
                if u != user:
                    irc.reply(_('That user has no tasks in their todo list.'))
                else:
                    irc.reply(_('You have no tasks in your todo list.'))
                return
        # Reply with the user's task
        else:
            try:
                t = self.db.get(user.id, taskid)
                if t.active:
                    active = _('Active')
                else:
                    active = _('Inactive')
                if t.priority:
                    t.task += format(_(', priority: %i'), t.priority)
                at = time.strftime(conf.supybot.reply.format.time(),
                                   time.localtime(t.at))
                s = format(_('%s todo for %s: %s (Added at %s)'),
                           active, user.name, t.task, at)
                irc.reply(s)
            except dbi.NoRecordError:
                irc.errorInvalid(_('task id'), taskid)
    todo = wrap(todo, [first('otherUser', 'user'), additional(('id', 'task'))])

    @internationalizeDocstring
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
        todoId = self.db.add(priority, now, user.id, text)
        irc.replySuccess(format(_('(Todo #%i added)'), todoId))
    add = wrap(add, ['user', getopts({'priority': ('int', 'priority')}),
                     'text', 'now'])

    @internationalizeDocstring
    def remove(self, irc, msg, args, user, tasks):
        """<task id> [<task id> ...]

        Removes <task id> from your personal todo list.
        """
        invalid = []
        for taskid in tasks:
            try:
                self.db.get(user.id, taskid)
            except dbi.NoRecordError:
                invalid.append(taskid)
        if invalid and len(invalid) == 1:
            irc.error(format(_('Task %i could not be removed either because '
                             'that id doesn\'t exist or it has been removed '
                             'already.'), invalid[0]))
        elif invalid:
            irc.error(format(_('No tasks were removed because the following '
                             'tasks could not be removed: %L.'), invalid))
        else:
            for taskid in tasks:
                self.db.remove(user.id, taskid)
            irc.replySuccess()
    remove = wrap(remove, ['user', many(('id', 'task'))])

    @internationalizeDocstring
    def search(self, irc, msg, args, user, optlist, globs):
        """[--{regexp} <value>] [<glob> <glob> ...]

        Searches your todos for tasks matching <glob>.  If --regexp is given,
        its associated value is taken as a regexp and matched against the
        tasks.
        """
        if not optlist and not globs:
            raise callbacks.ArgumentError
        criteria = []
        for (option, arg) in optlist:
            if option == 'regexp':
                criteria.append(lambda s:
                                regexp_wrapper(s, reobj=arg, timeout=0.1,
                                               plugin_name=self.name(),
                                               fcn_name='search'))
        for glob in globs:
            glob = utils.python.glob2re(glob)
            criteria.append(re.compile(glob).search)
        try:
            tasks = self.db.select(user.id, criteria)
            L = [format('#%i: %s', t.id, self._shrink(t.task)) for t in tasks]
            irc.reply(format('%L', L))
        except dbi.NoRecordError:
            irc.reply(_('No tasks matched that query.'))
    search = wrap(search,
                  ['user', getopts({'regexp': 'regexpMatcher'}), any('glob')])

    @internationalizeDocstring
    def setpriority(self, irc, msg, args, user, id, priority):
        """<id> <priority>

        Sets the priority of the todo with the given id to the specified value.
        """
        try:
            self.db.setpriority(user.id, id, priority)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.errorInvalid(_('task id'), id)
    setpriority = wrap(setpriority,
                       ['user', ('id', 'task'), ('int', 'priority')])

    @internationalizeDocstring
    def change(self, irc, msg, args, user, id, replacer):
        """<task id> <regexp>

        Modify the task with the given id using the supplied regexp.
        """
        try:
            self.db.change(user.id, id, replacer)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.errorInvalid(_('task id'), id)
    change = wrap(change, ['user', ('id', 'task'), 'regexpReplacer'])


Class = Todo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
