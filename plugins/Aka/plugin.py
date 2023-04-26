###
# Copyright (c) 2013-2021, Valentin Lorentz
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

import re
import os
import sys
import datetime

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.utils.minisix as minisix
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.httpserver as httpserver
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization('Aka')

try:
    import sqlite3
except ImportError:
    sqlite3 = None
try:
    import sqlalchemy
    import sqlalchemy.ext
    import sqlalchemy.ext.declarative
except ImportError:
    sqlalchemy = None

if not (sqlite3 or sqlalchemy):
    raise callbacks.Error('You have to install python-sqlite3 or '
            'python-sqlalchemy in order to load this plugin.')

available_db = {}

class Alias(object):
    __slots__ = ('name', 'alias', 'locked', 'locked_by', 'locked_at')
    def __init__(self, name, alias):
        self.name = name
        self.alias = alias
        self.locked = False
        self.locked_by = None
        self.locked_at = None
    def __repr__(self):
        return "<Alias('%r', '%r')>" % (self.name, self.alias)
if sqlite3:
    class SQLiteAkaDB(object):
        __slots__ = ('engines', 'filename', 'dbs',)
        def __init__(self, filename):
            self.engines = ircutils.IrcDict()
            self.filename = filename.replace('sqlite3', 'sqlalchemy')

        def close(self):
            self.dbs.clear()

        def get_db(self, channel):
            if channel in self.engines:
                engine = self.engines[channel]
            else:
                filename = plugins.makeChannelFilename(self.filename, channel)
                exists = os.path.exists(filename)
                engine = sqlite3.connect(filename, check_same_thread=False)
                if not exists:
                    cursor = engine.cursor()
                    cursor.execute("""CREATE TABLE aliases (
                            id INTEGER NOT NULL,
                            name VARCHAR NOT NULL,
                            alias VARCHAR NOT NULL,
                            locked BOOLEAN NOT NULL,
                            locked_by VARCHAR,
                            locked_at DATETIME,
                            PRIMARY KEY (id),
                            UNIQUE (name))""")
                    engine.commit()
                self.engines[channel] = engine
            assert engine.execute("select 1").fetchone() == (1,)
            return engine


        def has_aka(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            return self.get_db(channel).cursor() \
                    .execute("""SELECT COUNT() as count
                                FROM aliases WHERE name = ?;""", (name,)) \
                    .fetchone()[0]

        def get_aka_list(self, channel):
            cursor = self.get_db(channel).cursor()
            cursor.execute("""SELECT name FROM aliases;""")
            list_ = cursor.fetchall()
            return list_

        def get_alias(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            cursor = self.get_db(channel).cursor()
            cursor.execute("""SELECT alias FROM aliases
                              WHERE name = ?;""", (name,))
            r = cursor.fetchone()
            if r:
                return r[0]
            else:
                return None

        def add_aka(self, channel, name, alias):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if self.has_aka(channel, name):
                raise AkaError(_('This Aka already exists.'))
            if minisix.PY2:
                if isinstance(name, str):
                    name = name.decode('utf8')
                if isinstance(alias, str):
                    alias = alias.decode('utf8')
            db = self.get_db(channel)
            cursor = db.cursor()
            cursor.execute("""INSERT INTO aliases VALUES (
                NULL, ?, ?, 0, NULL, NULL);""", (name, alias))
            db.commit()

        def remove_aka(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            db.cursor().execute('DELETE FROM aliases WHERE name = ?', (name,))
            db.commit()

        def lock_aka(self, channel, name, by):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            cursor = db.cursor().execute("""UPDATE aliases
                    SET locked=1, locked_at=?, locked_by=? WHERE name = ?""",
                    (datetime.datetime.now(), by, name))
            if cursor.rowcount == 0:
                raise AkaError(_('This Aka does not exist.'))
            db.commit()

        def unlock_aka(self, channel, name, by):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            cursor = db.cursor()
            cursor.execute("""UPDATE aliases SET locked=0, locked_at=?
                              WHERE name = ?""", (datetime.datetime.now(), name))
            if cursor.rowcount == 0:
                raise AkaError(_('This Aka does not exist.'))
            db.commit()

        def get_aka_lock(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            cursor = self.get_db(channel).cursor()
            cursor.execute("""SELECT locked, locked_by, locked_at
                              FROM aliases WHERE name = ?;""", (name,))
            r = cursor.fetchone()
            if r:
                return (bool(r[0]), r[1], r[2])
            else:
                raise AkaError(_('This Aka does not exist.'))

        def get_all(self, channel):
            cursor = self.get_db(channel).cursor()
            cursor.execute("""
                SELECT id, name, alias, locked, locked_by, locked_at
                FROM aliases;
            """)
            return cursor.fetchall()

    available_db.update({'sqlite3': SQLiteAkaDB})
elif sqlalchemy:
    Base = sqlalchemy.ext.declarative.declarative_base()
    class SQLAlchemyAlias(Alias, Base):
        __slots__ = ()
        __tablename__ = 'aliases'

        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
        alias = sqlalchemy.Column(sqlalchemy.String, nullable=False)

        locked = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False)
        locked_by = sqlalchemy.Column(sqlalchemy.String, nullable=True)
        locked_at = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)

    # TODO: Add table for usage statistics

    class SqlAlchemyAkaDB(object):
        __slots__ = ('engines', 'filename', 'sqlalchemy', 'dbs')
        def __init__(self, filename):
            self.engines = ircutils.IrcDict()
            self.filename = filename
            self.sqlalchemy = sqlalchemy

        def close(self):
            self.dbs.clear()

        def get_db(self, channel):
            if channel in self.engines:
                engine = self.engines[channel]
            else:
                filename = plugins.makeChannelFilename(self.filename, channel)
                exists = os.path.exists(filename)
                engine = sqlalchemy.create_engine('sqlite:///' + filename)
                if not exists:
                    Base.metadata.create_all(engine)
                self.engines[channel] = engine
            assert engine.execute("select 1").scalar() == 1
            Session = sqlalchemy.orm.sessionmaker()
            Session.configure(bind=engine)
            return Session()


        def has_aka(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            count = self.get_db(channel).query(SQLAlchemyAlias) \
                    .filter(SQLAlchemyAlias.name == name) \
                    .count()
            return bool(count)
        def get_aka_list(self, channel):
            list_ = list(self.get_db(channel).query(SQLAlchemyAlias.name))
            return list_

        def get_alias(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            try:
                return self.get_db(channel).query(SQLAlchemyAlias.alias) \
                        .filter(SQLAlchemyAlias.name == name).one()[0]
            except sqlalchemy.orm.exc.NoResultFound:
                return None

        def add_aka(self, channel, name, alias):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if self.has_aka(channel, name):
                raise AkaError(_('This Aka already exists.'))
            if minisix.PY2:
                if isinstance(name, str):
                    name = name.decode('utf8')
                if isinstance(alias, str):
                    alias = alias.decode('utf8')
            db = self.get_db(channel)
            db.add(SQLAlchemyAlias(name, alias))
            db.commit()

        def remove_aka(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            db.query(SQLAlchemyAlias).filter(SQLAlchemyAlias.name == name).delete()
            db.commit()

        def lock_aka(self, channel, name, by):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            try:
                aka = db.query(SQLAlchemyAlias) \
                        .filter(SQLAlchemyAlias.name == name).one()
            except sqlalchemy.orm.exc.NoResultFound:
                raise AkaError(_('This Aka does not exist.'))
            if aka.locked:
                raise AkaError(_('This Aka is already locked.'))
            aka.locked = True
            aka.locked_by = by
            aka.locked_at = datetime.datetime.now()
            db.commit()

        def unlock_aka(self, channel, name, by):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            try:
                aka = db.query(SQLAlchemyAlias) \
                        .filter(SQLAlchemyAlias.name == name).one()
            except sqlalchemy.orm.exc.NoResultFound:
                raise AkaError(_('This Aka does not exist.'))
            if not aka.locked:
                raise AkaError(_('This Aka is already unlocked.'))
            aka.locked = False
            aka.locked_by = by
            aka.locked_at = datetime.datetime.now()
            db.commit()

        def get_aka_lock(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if minisix.PY2 and isinstance(name, str):
                name = name.decode('utf8')
            try:
                return self.get_db(channel) \
                        .query(SQLAlchemyAlias.locked, SQLAlchemyAlias.locked_by, SQLAlchemyAlias.locked_at)\
                        .filter(SQLAlchemyAlias.name == name).one()
            except sqlalchemy.orm.exc.NoResultFound:
                raise AkaError(_('This Aka does not exist.'))

        def get_all(self, channel):
            akas = self.get_db(channel).query(
                SQLAlchemyAlias.id, SQLAlchemyAlias.name, SQLAlchemyAlias.alias,
                SQLAlchemyAlias.locked, SQLAlchemyAlias.locked_by, SQLAlchemyAlias.locked_at
            ).all()
            return map(
                lambda aka: (aka.name, aka.alias, aka.locked, aka.locked_by, aka.locked_at),
                akas
            )

    available_db.update({'sqlalchemy': SqlAlchemyAkaDB})


def getArgs(args, required=1, optional=0, wildcard=0):
    if len(args) < required:
        raise callbacks.ArgumentError
    if len(args) < required + optional:
        ret = list(args) + ([''] * (required + optional - len(args)))
    elif len(args) >= required + optional:
        if not wildcard:
            ret = list(args[:required + optional - 1])
            ret.append(' '.join(args[required + optional - 1:]))
        else:
            ret = list(args)
    return ret

class AkaError(Exception):
    pass

class RecursiveAlias(AkaError):
    pass

dollarRe = re.compile(r'\$(\d+)')
def findBiggestDollar(alias):
    dollars = dollarRe.findall(alias)
    dollars = list(map(int, dollars))
    dollars.sort()
    if dollars:
        return dollars[-1]
    else:
        return 0

atRe = re.compile(r'@(\d+)')
def findBiggestAt(alias):
    ats = atRe.findall(alias)
    ats = list(map(int, ats))
    ats.sort()
    if ats:
        return ats[-1]
    else:
        return 0

if 'sqlite3' in conf.supybot.databases() and 'sqlite3' in available_db:
    AkaDB = SQLiteAkaDB
elif 'sqlalchemy' in conf.supybot.databases() and 'sqlalchemy' in available_db:
    log.warning('Aka\'s only enabled database engine is SQLAlchemy, which '
            'is deprecated. Please consider adding \'sqlite3\' to '
            'supybot.databases (and/or install sqlite3).')
    AkaDB = SqlAlchemyAkaDB
else:
    raise plugins.NoSuitableDatabase(['sqlite3', 'sqlalchemy'])


class AkaHTTPCallback(httpserver.SupyHTTPServerCallback):
    name = 'Aka web interface'
    base_template = '''\
<!DOCTYPE html>
<html>
  <head>
    <title>Aka</title>
    <link rel="stylesheet" href="/default.css">
  </head>

  <body>
    <h1>Aka</h1>

    %s
  </body>
</html>'''
    index_template = base_template % '''\
    <p>To view the global Akas either click <a href="list/global">here</a> or
    enter 'global' in the form below.</p>

    <form action="" method="post">
        <label for="channel">Channel name:</label>
        <input type="text" placeholder="#channel" name="channel" id="channel">
        <input type="submit" name="submit" value="view">
    </form>'''
    list_template = base_template % '''\
    <table>
      <thead>
        <th>Name</th>
        <th>Alias</th>
        <th>Locked</th>
      </thead>
      %s
    </table>'''

    def doGet(self, handler, path, *args, **kwargs):
        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.write(self.index_template)

        elif path.startswith('/list/'):
            parts = path.split('/')
            channel = parts[2] if len(parts) == 3 else 'global'
            channel = utils.web.urlunquote(channel)

            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            akas = {}
            for aka in self._plugin._db.get_all('global'):
                akas[aka[1]] = aka

            if channel != 'global':
                for aka in self._plugin._db.get_all(channel):
                    akas[aka[1]] = aka

            aka_rows = []
            for (name, aka) in sorted(akas.items()):
                (id, name, alias, locked, locked_by, locked_at) = aka
                locked_column = 'False'
                if locked:
                    locked_column = format(
                        _('By %s at %s'),
                        locked_by,
                        locked_at.split('.')[0],
                    )
                aka_rows.append(
                    format(
                        """
                            <tr>
                                <td style="white-space: nowrap;"><code>%s</code></td>
                                <td><code>%s<code></td>
                                <td style="white-space: nowrap;">%s</td>
                            </tr>
                        """,
                        utils.web.html_escape(name),
                        utils.web.html_escape(alias),
                        utils.web.html_escape(locked_column),
                    )
                )
            self.write(format(self.list_template, ''.join(aka_rows)))

    def doPost(self, handler, path, form, *args, **kwargs):
        if path == '/' and 'channel' in form:
            self.send_response(303)
            self.send_header(
                'Location',
                format('list/%s', utils.web.urlquote(form['channel'].value))
            )
            self.end_headers()
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.write('Missing field \'channel\'.')


class Aka(callbacks.Plugin):
    """
    This plugin allows users to define aliases to commands and combinations
    of commands (via nesting).

    Importing from Alias
    ^^^^^^^^^^^^^^^^^^^^

    Add an aka, Alias, which eases the transitioning to Aka from Alias.

    First we will load Alias and Aka::

        <jamessan> @load Alias
        <bot> jamessan: The operation succeeded.
        <jamessan> @load Aka
        <bot> jamessan: The operation succeeded.

    Then we import the Alias database to Aka in case it exists and unload
    Alias::

        <jamessan> @importaliasdatabase
        <bot> jamessan: The operation succeeded.
        <jamessan> @unload Alias
        <bot> jamessan: The operation succeeded.

    And now we will finally add the Aka ``alias`` itself::

        <jamessan> @aka add "alias" "aka $1 $*"
        <bot> jamessan: The operation succeeded.

    Now you can use Aka as you used Alias before.

    Trout
    ^^^^^

    Add an aka, ``trout``, which expects a word as an argument::

        <jamessan> @aka add trout "reply action slaps $1 with a large trout"
        <bot> jamessan: The operation succeeded.
        <jamessan> @trout me
        * bot slaps me with a large trout

    This ``trout`` aka requires the plugin ``Reply`` to be loaded since it
    provides the ``action`` command.

    Random percentage
    ^^^^^^^^^^^^^^^^^

    Add an aka, ``randpercent``, which returns a random percentage value::

        @aka add randpercent "squish [dice 1d100]%"

    This requires the ``Filter`` and ``Games`` plugins to be loaded.

    Note that nested commands in an alias should be quoted, or they will only
    run once when you create the alias, and not each time the alias is
    called. (In this case, not quoting the nested command would mean that
    ``@randpercent`` always responds with the same value!)
    """

    def __init__(self, irc):
        self.__parent = super(Aka, self)
        self.__parent.__init__(irc)
        # "sqlalchemy" is only for backward compatibility
        filename = conf.supybot.directories.data.dirize('Aka.sqlalchemy.db')
        self._db = AkaDB(filename)
        self._http_running = False
        conf.supybot.plugins.Aka.web.enable.addCallback(self._httpConfCallback)
        if self.registryValue('web.enable'):
            self._startHttp()

    def die(self):
        if self._http_running:
            self._stopHttp()

    def _httpConfCallback(self):
        if self.registryValue('web.enable'):
            if not self._http_running:
                self._startHttp()
        else:
            if self._http_running:
                self._stopHttp()

    def _startHttp(self):
        callback = AkaHTTPCallback()
        callback._plugin = self
        httpserver.hook('aka', callback)
        self._http_running = True

    def _stopHttp(self):
        httpserver.unhook('aka')
        self._http_running = False

    def isCommandMethod(self, name):
        args = name.split(' ')
        if '|' in args:
            return False
        if len(args) > 1 and \
                callbacks.canonicalName(args[0]) != self.canonicalName():
            for cb in dynamic.irc.callbacks: # including this plugin
                if cb.isCommandMethod(' '.join(args[0:-1])):
                    return False
        if minisix.PY2 and isinstance(name, str):
            name = name.decode('utf8')
        channel = dynamic.channel or 'global'
        return self._db.has_aka(channel, name) or \
                self._db.has_aka('global', name) or \
                self.__parent.isCommandMethod(name)
    isCommand = isCommandMethod

    def listCommands(self):
        commands = ['add', 'remove', 'lock', 'unlock', 'importaliasdatabase',
            'show', 'list', 'set', 'search']
        return commands

    def getCommand(self, args, check_other_plugins=True):
        canonicalName = callbacks.canonicalName
        # All the code from here to the 'for' loop is copied from callbacks.py
        assert args == list(map(canonicalName, args))
        first = args[0]
        for cb in self.cbs:
            if first == cb.canonicalName():
                return cb.getCommand(args[1:])
        if first == self.canonicalName() and len(args) > 1:
            ret = self.getCommand(args[1:], False)
            if ret:
                return [first] + ret
        max_length = self.registryValue('maximumWordsInName')
        for i in range(1, min(len(args)+1, max_length)):
            if self.isCommandMethod(callbacks.formatCommand(args[0:i])):
                return args[0:i]
        return []

    def getCommandMethod(self, command):
        if len(command) == 1 or command[0] == self.canonicalName():
            try:
                return self.__parent.getCommandMethod(command)
            except AttributeError:
                pass
        name = callbacks.formatCommand(command)
        channel = dynamic.channel or 'global'
        original = self._db.get_alias(channel, name)
        if not original:
            original = self._db.get_alias('global', name)
        biggestDollar = findBiggestDollar(original)
        biggestAt = findBiggestAt(original)
        wildcard = '$*' in original
        def f(irc, msg, args):
            tokens = callbacks.tokenize(original)
            if biggestDollar or biggestAt:
                args = getArgs(args, required=biggestDollar, optional=biggestAt,
                                wildcard=wildcard)
            remaining_len = conf.supybot.reply.maximumLength()
            for (i, arg) in enumerate(args):
                if remaining_len < len(arg):
                    arg = arg[0:remaining_len]
                    args[i+1:] = []
                    break
                remaining_len -= len(arg)
            def regexpReplace(m):
                idx = int(m.group(1))
                return args[idx-1]
            def replace(tokens, replacer):
                for (i, token) in enumerate(tokens):
                    if isinstance(token, list):
                        replace(token, replacer)
                    else:
                        tokens[i] = replacer(token)
            replace(tokens, lambda s: dollarRe.sub(regexpReplace, s))
            if biggestAt:
                assert not wildcard
                args = args[biggestDollar:]
                replace(tokens, lambda s: atRe.sub(regexpReplace, s))
            if wildcard:
                assert not biggestAt
                # Gotta remove the things that have already been subbed in.
                i = biggestDollar
                args[:] = args[i:]
                def everythingReplace(tokens):
                    skip = 0
                    for (i, token) in enumerate(tokens):
                        if skip:
                            skip -= 1
                            continue
                        if isinstance(token, list):
                            everythingReplace(token)
                        if token == '$*':
                            tokens[i:i+1] = args
                            skip = len(args)-1 # do not make replacements in
                                               # tokens we just added
                        elif '$*' in token:
                            tokens[i] = token.replace('$*', ' '.join(args))
                everythingReplace(tokens)
            maxNesting = conf.supybot.commands.nested.maximum()
            if maxNesting and irc.nested+1 > maxNesting:
                irc.error(_('You\'ve attempted more nesting than is '
                      'currently allowed on this bot.'), Raise=True)
            self.Proxy(irc, msg, tokens, nested=irc.nested+1)
        if biggestDollar and (wildcard or biggestAt):
            flexargs = _(' at least')
        else:
            flexargs = ''
        try:
            lock = self._db.get_aka_lock(channel, name)
        except AkaError:
            lock = self._db.get_aka_lock('global', name)
        (locked, locked_by, locked_at) = lock
        if locked:
            lock = ' ' + _('Locked by %s at %s') % (locked_by, locked_at)
        else:
            lock = ''
        escaped_command = original.replace('\\', '\\\\').replace('"', '\\"')
        if channel == 'global':
            doc = format(_('<a global alias,%s %n>\n\nAlias for %q.%s'),
                        flexargs, (biggestDollar, _('argument')),
                        escaped_command, lock)
        else:
            doc = format(_('<an alias on %s,%s %n>\n\nAlias for %q.%s'),
                        channel, flexargs, (biggestDollar, _('argument')),
                        escaped_command, lock)
        f = utils.python.changeFunctionName(f, name, doc)
        return f

    def _add_aka(self, channel, name, alias):
        if self.__parent.isCommandMethod(name):
            raise AkaError(_('You can\'t overwrite commands in '
                    'this plugin.'))
        if self._db.has_aka(channel, name):
            raise AkaError(_('This Aka already exists.'))
        if len(name.split(' ')) > self.registryValue('maximumWordsInName'):
            raise AkaError(_('This Aka has too many spaces in its name.'))
        biggestDollar = findBiggestDollar(alias)
        biggestAt = findBiggestAt(alias)
        wildcard = '$*' in alias
        if biggestAt and wildcard:
            raise AkaError(_('Can\'t mix $* and optional args (@1, etc.)'))
        self._db.add_aka(channel, name, alias)

    def _remove_aka(self, channel, name, evenIfLocked=False):
        if not evenIfLocked:
            (locked, by, at) = self._db.get_aka_lock(channel, name)
            if locked:
                raise AkaError(_('This Aka is locked.'))
        self._db.remove_aka(channel, name)

    def add(self, irc, msg, args, optlist, name, alias):
        """[--channel <#channel>] <name> <command>

        Defines an alias <name> that executes <command>.  The <command>
        should be in the standard "command argument [nestedcommand argument]"
        arguments to the alias; they'll be filled with the first, second, etc.
        arguments.  $1, $2, etc. can be used for required arguments.  @1, @2,
        etc. can be used for optional arguments.  $* simply means "all
        arguments that have not replaced $1, $2, etc.", ie. it will also
        include optional arguments.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not irc.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        if ' ' not in alias:
            # If it's a single word, they probably want $*.
            alias += ' $*'
        try:
            self._add_aka(channel, name, alias)
            self.log.info('Adding Aka %r for %r (from %s)',
                          name, alias, msg.prefix)
            irc.replySuccess()
        except AkaError as e:
            irc.error(str(e))
    add = wrap(add, [getopts({
                                'channel': 'somethingWithoutSpaces',
                            }), 'something', 'text'])

    def set(self, irc, msg, args, optlist, name, alias):
        """[--channel <#channel>] <name> <command>

        Overwrites an existing alias <name> to execute <command> instead.  The
        <command> should be in the standard "command argument [nestedcommand
        argument]" arguments to the alias; they'll be filled with the first,
        second, etc. arguments.  $1, $2, etc. can be used for required
        arguments.  @1, @2, etc. can be used for optional arguments.  $* simply
        means "all arguments that have not replaced $1, $2, etc.", ie. it will
        also include optional arguments.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not irc.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        try:
            self._remove_aka(channel, name)
        except AkaError as e:
            irc.error(str(e), Raise=True)

        if ' ' not in alias:
            # If it's a single word, they probably want $*.
            alias += ' $*'
        try:
            self._add_aka(channel, name, alias)
            self.log.info('Setting Aka %r to %r (from %s)',
                          name, alias, msg.prefix)
            irc.replySuccess()
        except AkaError as e:
            irc.error(str(e))
    set = wrap(set, [getopts({
                                'channel': 'somethingWithoutSpaces',
                            }), 'something', 'text'])

    def remove(self, irc, msg, args, optlist, name):
        """[--channel <#channel>] <name>

        Removes the given alias, if unlocked.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not irc.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        try:
            self._remove_aka(channel, name)
            self.log.info('Removing Aka %r (from %s)', name, msg.prefix)
            irc.replySuccess()
        except AkaError as e:
            irc.error(str(e))
    remove = wrap(remove, [getopts({
                                'channel': 'somethingWithoutSpaces',
                            }), 'something'])

    def _checkManageCapabilities(self, irc, msg, channel):
        """Check if the user has any of the required capabilities to manage
        the regexp database."""
        if channel != 'global':
            capability = ircdb.makeChannelCapability(channel, 'op')
        else:
            capability = 'admin'
        if not ircdb.checkCapability(msg.prefix, capability):
            irc.errorNoCapability(capability, Raise=True)

    def lock(self, irc, msg, args, optlist, user, name):
        """[--channel <#channel>] <alias>

        Locks an alias so that no one else can change it.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not irc.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        self._checkManageCapabilities(irc, msg, channel)
        try:
            self._db.lock_aka(channel, name, user.name)
        except AkaError as e:
            irc.error(str(e))
        else:
            irc.replySuccess()
    lock = wrap(lock, [getopts({
                                'channel': 'somethingWithoutSpaces',
                            }), 'user', 'something'])

    def unlock(self, irc, msg, args, optlist, user, name):
        """[--channel <#channel>] <alias>

        Unlocks an alias so that people can define new aliases over it.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not irc.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        self._checkManageCapabilities(irc, msg, channel)
        try:
            self._db.unlock_aka(channel, name, user.name)
        except AkaError as e:
            irc.error(str(e))
        else:
            irc.replySuccess()
    unlock = wrap(unlock, [getopts({
                                'channel': 'somethingWithoutSpaces',
                            }), 'user', 'something'])

    def show(self, irc, msg, args, optlist, name):
        """[--channel <#channel>] <alias>

        This command shows the content of an Aka.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not irc.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        command = self._db.get_alias(channel, name)
        if command:
            irc.reply(command)
        else:
            irc.error(_('This Aka does not exist.'))
    show = wrap(show, [getopts({'channel': 'somethingWithoutSpaces'}),
        'text'])

    def importaliasdatabase(self, irc, msg, args):
        """takes no arguments

        Imports the Alias database into Aka's, and clean the former."""
        alias_plugin = irc.getCallback('Alias')
        if alias_plugin is None:
            irc.error(_('Alias plugin is not loaded.'), Raise=True)
        errors = {}
        for (name, (command, locked, func)) in \
                list(alias_plugin.aliases.items()):
            try:
                self._add_aka('global', name, command)
            except AkaError as e:
                errors[name] = e.args[0]
            else:
                alias_plugin.removeAlias(name, evenIfLocked=True)
        if errors:
            irc.error(format(_('Error occured when importing the %n: %L'),
                (len(errors), 'following', 'command'),
                ['%s (%s)' % x for x in errors.items()]))
        else:
            irc.replySuccess()
    importaliasdatabase = wrap(importaliasdatabase, ['owner'])

    def list(self, irc, msg, args, optlist):
        """[--channel <#channel>] [--keys] [--unlocked|--locked]

        Lists all Akas defined for <channel>. If <channel> is not specified,
        lists all global Akas. If --keys is given, lists only the Aka names
        and not their commands."""
        channel = 'global'
        filterlocked = filterunlocked = False
        for (option, arg) in optlist:
            if option == 'channel':
                if not irc.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
            if option == 'locked':
                filterlocked = True
            if option == 'unlocked':
                filterunlocked = True
        aka_list = self._db.get_aka_list(channel)
        if filterlocked and filterunlocked:
            irc.error(_('--locked and --unlocked are incompatible options.'), Raise=True)
        elif filterlocked:
            aka_list = [aka for aka in aka_list if
                        self._db.get_aka_lock(channel, aka)[0]]
        elif filterunlocked:
            aka_list = [aka for aka in aka_list if not
                        self._db.get_aka_lock(channel, aka)[0]]
        if aka_list:
            if 'keys' in dict(optlist):
                # Strange, aka_list is a list of one length tuples
                s = [k[0] for k in aka_list]
                oneToOne = True
            else:
                aka_values = [self._db.get_alias(channel, aka) for aka in
                              aka_list]
                s = ('{0}: "{1}"'.format(ircutils.bold(k), v) for (k, v) in
                    zip(aka_list, aka_values))
                oneToOne = None
            irc.replies(s, oneToOne=oneToOne)
        else:
            irc.error(_("No Akas found."))
    list = wrap(list, [getopts({'channel': 'channel', 'keys': '', 'locked': '',
                                'unlocked': ''})])

    def search(self, irc, msg, args, optlist, query):
        """[--channel <#channel>] <query>

        Searches Akas defined for <channel>. If <channel> is not specified,
        searches all global Akas."""
        query = callbacks.canonicalName(query, preserve_spaces=True)
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not irc.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        aka_list = self._db.get_aka_list(channel)
        aka_list = [callbacks.canonicalName(k[0], preserve_spaces=True)
                    for k in aka_list]
        matching = [aka for aka in aka_list if query in aka]
        if matching:
            irc.replies(matching)
        else:
            irc.error(_("No matching Akas were found."))
    search = wrap(search, [getopts({'channel': 'channel'}), 'text'])

Class = Aka


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
