###
# Copyright (c) 2002-2004, Jeremiah Fincher
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
The Lookup plugin handles looking up various values by their key.
"""

import supybot

__revision__ = "$Id$"
__contributors__ = {
    supybot.authors.skorobeus: ['--nokey parameter', 'database abstraction'],
    }

import supybot.plugins as plugins

import os
import re
import sys
import sets
import getopt
import string

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Lookup', True)
    lookups = conf.supybot.plugins.Lookup.lookups
    output("""This module allows you to define commands that do a simple key
              lookup and return some simple value.  It has a command "add"
              that takes a command name and a file from the data dir and adds a
              command with that name that responds with the mapping from that
              file. The file itself should be composed of lines
              of the form key:value.""")
    while yn('Would you like to add a file?'):
        filename = something('What\'s the filename?')
        try:
            fd = file(filename)
        except EnvironmentError, e:
            output('I couldn\'t open that file: %s' % e)
            continue
        counter = 1
        try:
            for line in fd:
                line = line.rstrip('\r\n')
                if not line or line.startswith('#'):
                    continue
                (key, value) = line.split(':', 1)
                counter += 1
        except ValueError:
            output('That\'s not a valid file; '
                   'line #%s is malformed.' % counter)
            continue
        command = something('What would you like the command to be?')
        conf.registerGlobalValue(lookups,command, registry.String(filename,''))
        nokeyVal = yn('Would you like the key to be shown for random \
                        responses?')
        conf.registerGlobalValue(lookups.get(command), 'nokey',
                                    registry.Boolean(nokeyVal, ''))

conf.registerPlugin('Lookup')
conf.registerGroup(conf.supybot.plugins.Lookup, 'lookups')

class SqliteLookupDB(object):
    def __init__(self, filename):
        try:
            import sqlite
        except ImportError:
            raise callbacks.Error, 'You need to have PySQLite installed to '\
                                   'use this plugin.  Download it at '\
                                   '<http://pysqlite.sf.net/>'
        self.filename = filename
        try:
            self.db = sqlite.connect(self.filename)
        except sqlite.DatabaseError, e:
            raise dbi.InvalidDBError, str(e)

    def close(self):
        self.db.close()

    def getRecordCount(self, tableName):
        cursor = self.db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM %s""" % tableName)
        rows = int(cursor.fetchone()[0])
        if rows == 0:
            raise dbi.NoRecordError
        return rows

    def checkLookup(self, name):
        cursor = self.db.cursor()
        sql = "SELECT name FROM sqlite_master \
                WHERE type='table' \
                AND name='%s'" % name
        cursor.execute(sql)
        if cursor.rowcount == 0:
            return False
        else:
            return True

    def addLookup(self, name, fd, splitRe):
        cursor = self.db.cursor()
        cursor.execute("CREATE TABLE %s (key TEXT, value TEXT)" % name)
        sql = "INSERT INTO %s VALUES (%%s, %%s)" % name
        for line in utils.nonCommentNonEmptyLines(fd):
            line = line.rstrip('\r\n')
            try:
                (key, value) = splitRe.split(line, 1)
                key = key.replace('\\:', ':')
            except ValueError:
                cursor.execute("""DROP TABLE %s""" % name)
                s = 'Invalid line in %s: %s' % (filename, utils.quoted(line))
                raise callbacks.Error, s
            cursor.execute(sql, key, value)
        cursor.execute("CREATE INDEX %s_keys ON %s (key)" % (name, name))
        self.db.commit()

    def dropLookup(self, name):
        cursor = self.db.cursor()
        if self.checkLookup(name):
            cursor.execute("""DROP TABLE %s""" % name)
            self.db.commit()
        else:
            raise dbi.NoRecordError

    def getResults(self, name, key):
        cursor = self.db.cursor()
        sql = """SELECT value FROM %s WHERE key LIKE %%s""" % name
        cursor.execute(sql, key)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        else:
            return cursor.fetchall()

    def getRandomResult(self, name, key):
        cursor = self.db.cursor()
        sql = """SELECT key, value FROM %s
                 ORDER BY random() LIMIT 1""" % name
        cursor.execute(sql)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        else:
            return cursor.fetchone()

    _sqlTrans = string.maketrans('*?', '%_')
    def searchResults(self, name, options, globs, column):
        cursor = self.db.cursor()
        criteria = []
        formats = []
        predicateName = 'p'
        for (option, arg) in options:
            if option == '--regexp':
                criteria.append('%s(%s)' % (predicateName, column))
                try:
                    r = utils.perlReToPythonRe(arg)
                except ValueError, e:
                    irc.errorInvalid('regular expression' % arg)
                    return
                def p(s, r=r):
                    return int(bool(r.search(s)))
                self.db.create_function(predicateName, 1, p)
                predicateName += 'p'
        for glob in globs.split():
            if '?' not in glob and '*' not in glob:
                glob = '*%s*' % glob
            criteria.append('%s LIKE %%s' % column)
            formats.append(glob.translate(self._sqlTrans))
        if not criteria:
            raise callbacks.ArgumentError
        #print 'criteria: %s' % repr(criteria)
        #print 'formats: %s' % repr(formats)
        sql = """SELECT key, value FROM %s WHERE %s""" % \
              (name, ' AND '.join(criteria))
        #print 'sql: %s' % sql
        cursor.execute(sql, formats)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        else:
            return cursor.fetchall()

LookupDB = plugins.DB('Lookup', {'sqlite': SqliteLookupDB,})

class Lookup(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.lookupDomains = sets.Set()
        try:
            self.db = LookupDB()
        except Exception:
            self.log.exception('Error loading %s:', self.filename)
            raise # So it doesn't get loaded without its database.
        for (name, value) in registry._cache.iteritems():
            name = name.lower()
            if name.startswith('supybot.plugins.lookup.lookups.'):
                name = name[len('supybot.plugins.lookup.lookups.'):]
                if '.' in name:
                    continue
                self.addRegistryValue(name, value)
        group = conf.supybot.plugins.Lookup.lookups
        for (name, value) in group.getValues(fullNames=False):
            name = name.lower() # Just in case.
            filename = value()
            try:
                if not self.db.checkLookup(name):
                    self.addDatabase(name, filename)
                self.addCommand(name)
            except Exception, e:
                self.log.warning('Couldn\'t add lookup %s: %s', name, e)

    def _shrink(self, s):
        return utils.ellipsisify(s, 50)

    def die(self):
        self.db.close()

    def remove(self, irc, msg, args, name):
        """<name>

        Removes the lookup for <name>.
        """
        if name not in self.lookupDomains:
            irc.error('That\'s not a valid lookup to remove.')
            return
        try:
            self.db.dropLookup(name)
            delattr(self.__class__, name)
            self.delRegistryValues(name)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.error('No such lookup exists.')
    remove = wrap(remove, [('checkCapability', 'admin'), 'commandName'])

    _splitRe = re.compile(r'(?<!\\):')
    def add(self, irc, msg, args, optlist, name, filename):
        """[--nokey] <name> <filename>

        Adds a lookup for <name> with the key/value pairs specified in the
        colon-delimited file specified by <filename>.  <filename> is searched
        for in conf.supybot.directories.data.  If <name> is not singular, we
        try to make it singular before creating the command.  If the --nokey
        option is specified, the new lookup will display only the value when
        queried, and will omit the key from the response.
        """
        nokey = False
        for (option, argument) in optlist:
            if option == 'nokey':
                nokey = True
        name = utils.depluralize(name)
        if hasattr(self, name):
            s = 'I already have a command in this plugin named %s' % name
            irc.error(s)
            return
        if not self.db.checkLookup(name):
            try:
                self.addDatabase(name, filename)
            except EnvironmentError, e:
                irc.error('Could not open %s: %s' % (filename, e.args[1]))
                return
        self.addCommand(name)
        self.addRegistryValue(name, filename, nokey)
        irc.replySuccess('Lookup %s added.' % name)
    add = wrap(add, [('checkCapability', 'admin'), getopts({'nokey':''}),
                     'commandName', 'filename'])

    def addRegistryValue(self, name, filename, nokey = False):
        group = conf.supybot.plugins.Lookup.lookups
        conf.registerGlobalValue(group, name, registry.String(filename, ''))
        #print 'nokey: %s' % nokey
        conf.registerGlobalValue(group.get(name), 'nokey',
                                 registry.Boolean(nokey, ''))

    def delRegistryValues(self, name):
        group = conf.supybot.plugins.Lookup.lookups
        group.unregister(name)

    def addDatabase(self, name, filename):
        filename = conf.supybot.directories.data.dirize(filename)
        fd = file(filename)
        self.db.addLookup(name, fd, self._splitRe)

    def addCommand(self, name):
        def f(self, irc, msg, args):
            args.insert(0, name)
            self._lookup(irc, msg, args)
        rows = self.db.getRecordCount(name)
        docstring = """[<key>]

        If <key> is given, looks up <key> in the %s database.  Otherwise,
        returns a random key: value pair from the database.  There are
        %s in the database.
        """ % (name, utils.nItems(name, rows))
        f = utils.changeFunctionName(f, name, docstring)
        self.lookupDomains.add(name)
        setattr(self.__class__, name, f)

    def search(self, irc, msg, args):
        """[--{regexp}=<value>] [--values] <name> <glob>

        Searches the domain <name> for lookups matching <glob>.  If --regexp
        is given, its associated value is taken as a regexp and matched
        against the lookups.  If --values is given, search the values rather
        than the keys.
        """
        column = 'key'
        while '--values' in args:
            column = 'value'
            args.remove('--values')
        (options, rest) = getopt.getopt(args, '', ['regexp='])
        (name, globs) = privmsgs.getArgs(rest, optional=1)
        if self.db.checkLookup(name):
            try:
                results = self.db.searchResults(name, options, globs, column)
                lookups = ['%s: %s' % (item[0], self._shrink(item[1]))
                           for item in results]
                irc.reply(utils.commaAndify(lookups))
            except dbi.NoRecordError:
                irc.reply('No entries in %s matched that query.' % name)
        else:
            irc.error('I don\'t have a domain %s' % name)

    def _lookup(self, irc, msg, args, name, key):
        """<name> <key>

        Looks up the value of <key> in the domain <name>.
        """
        if self.db.checkLookup(name):
            results = []
            if key:
                try:
                    results = self.db.getResults(name, key)
                except dbi.NoRecordError:
                    irc.error('I couldn\'t find %s in %s.' % (key, name))
                    return
                if len(results) == 1:
                    irc.reply(results[0][0])
                else:
                    values = [t[0] for t in results]
                    irc.reply('%s could be %s' % (key, ', or '.join(values)))
            else:
                (key, value) = self.db.getRandomResult(name, key)
                nokeyRegKey = 'lookups.%s.nokey' % name
                if not self.registryValue(nokeyRegKey):
                    irc.reply('%s: %s' % (key, value))
                else:
                    irc.reply('%s' % value)
        else:
            irc.error('I don\'t have a domain %s' % name)
    _lookup = wrap(_lookup, ['something', additional('text')])

Class = Lookup

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
