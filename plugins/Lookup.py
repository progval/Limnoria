#!/usr/bin/env python

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
The Lookup plugin handles looking up various values by their key.
"""

__revision__ = "$Id$"

import plugins

import os
import re
import sys
import sets
import getopt
import string

import conf
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
    onStart.append('load Lookup')
    print 'This module allows you to define commands that do a simple key'
    print 'lookup and return some simple value.  It has a command "add"'
    print 'that takes a command name and a file in conf.dataDir and adds a'
    print 'command with that name that responds with mapping from that file.'
    print 'The file itself should be composed of lines of the form key:value.'
    while yn('Would you like to add a file?') == 'y':
        filename = something('What\'s the filename?')
        try:
            fd = file(os.path.join(conf.dataDir, filename))
        except EnvironmentError, e:
            print 'I couldn\'t open that file: %s' % e
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
            print 'That\'s not a valid file; line #%s is malformed.' % counter
            continue
        command = something('What would you like the command to be?')
        onStart.append('lookup add %s %s' % (command, filename))
    

class LookupDB(plugins.DBHandler):
    def makeDb(self, filename):
        return sqlite.connect(filename)

class Lookup(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.lookupDomains = sets.Set()
        self.dbHandler = LookupDB(name=os.path.join(conf.dataDir, 'Lookup'))
        
    def _shrink(self, s):
        return utils.ellipsisify(s, 50)

    def die(self):
        self.dbHandler.die()

    def remove(self, irc, msg, args):
        """<name>

        Removes the lookup for <name>.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if name not in self.lookupDomains:
            irc.error('That\'s not a valid lookup to remove.')
            return
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        try:
            cursor.execute("""DROP TABLE %s""" % name)
            db.commit()
            delattr(self.__class__, name)
            irc.replySuccess()
        except sqlite.DatabaseError:
            irc.error('No such lookup exists.')
    remove = privmsgs.checkCapability(remove, 'admin')

    _splitRe = re.compile(r'(?<!\\):')
    def add(self, irc, msg, args):
        """<name> <filename>

        Adds a lookup for <name> with the key/value pairs specified in the
        colon-delimited file specified by <filename>.  <filename> is searched
        for in conf.dataDir.  If <name> is not singular, we try to make it
        singular before creating the command.
        """
        (name, filename) = privmsgs.getArgs(args, required=2)
        name = utils.depluralize(name)
        name = callbacks.canonicalName(name)
        if hasattr(self, name):
            s = 'I already have a command in this plugin named %s' % name
            irc.error(s)
            return
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        try:
            cursor.execute("""SELECT * FROM %s LIMIT 1""" % name)
            self.addCommand(name)
            irc.replySuccess()
        except sqlite.DatabaseError:
            # Good, there's no such database.
            try:
                filename = os.path.join(conf.dataDir, filename)
                fd = file(filename)
            except EnvironmentError, e:
                irc.error('Could not open %s: %s' % (filename, e.args[1]))
                return
            try:
                cursor.execute("""SELECT COUNT(*) FROM %s""" % name)
            except sqlite.DatabaseError:
                cursor.execute("CREATE TABLE %s (key TEXT, value TEXT)" % name)
                sql = "INSERT INTO %s VALUES (%%s, %%s)" % name
                for line in utils.nonCommentNonEmptyLines(fd):
                    line = line.rstrip('\r\n')
                    try:
                        (key, value) = self._splitRe.split(line, 1)
                        key = key.replace('\\:', ':')
                    except ValueError:
                        cursor.execute("""DROP TABLE %s""" % name)
                        s = 'Invalid line in %s: %r' % (filename, line)
                        irc.error(s)
                        return
                    cursor.execute(sql, key, value)
                cursor.execute("CREATE INDEX %s_keys ON %s (key)" %(name,name))
                db.commit()
            self.addCommand(name)
            irc.replySuccess('(lookup %s added)' % name)
    add = privmsgs.checkCapability(add, 'admin')

    def addCommand(self, name):
        def f(self, irc, msg, args):
            args.insert(0, name)
            self._lookup(irc, msg, args)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM %s""" % name)
        rows = int(cursor.fetchone()[0])
        docstring = """[<key>]

        If <key> is given, looks up <key> in the %s database.  Otherwise,
        returns a random key: value pair from the database.  There are
        %s in the database.
        """ % (name, utils.nItems(name, rows))
        f = utils.changeFunctionName(f, name, docstring)
        self.lookupDomains.add(name)
        setattr(self.__class__, name, f)

    _sqlTrans = string.maketrans('*?', '%_')
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
        db = self.dbHandler.getDb()
        criteria = []
        formats = []
        predicateName = 'p'
        for (option, arg) in options:
            if option == '--regexp':
                criteria.append('%s(%s)' % (predicateName, column))
                try:
                    r = utils.perlReToPythonRe(arg)
                except ValueError, e:
                    irc.error('%r is not a valid regular expression' %
                              arg)
                    return
                def p(s, r=r):
                    return int(bool(r.search(s)))
                db.create_function(predicateName, 1, p)
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
        cursor = db.cursor()
        sql = """SELECT key, value FROM %s WHERE %s""" % \
              (name, ' AND '.join(criteria))
        #print 'sql: %s' % sql
        cursor.execute(sql, formats)
        if cursor.rowcount == 0:
            irc.reply('No %s matched that query.' % utils.pluralize(name))
        else:
            lookups = ['%s: %s' % (item[0], self._shrink(item[1]))
                       for item in cursor.fetchall()]
            irc.reply(utils.commaAndify(lookups))

    def _lookup(self, irc, msg, args):
        """<name> <key>

        Looks up the value of <key> in the domain <name>.
        """
        (name, key) = privmsgs.getArgs(args, optional=1)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        if key:
            sql = """SELECT value FROM %s WHERE key LIKE %%s""" % name
            try:
                cursor.execute(sql, key)
            except sqlite.DatabaseError, e:
                if 'no such table' in str(e):
                    irc.error('I don\'t have a domain %s' % name)
                else:
                    irc.error(str(e))
                return
            if cursor.rowcount == 0:
                irc.error('I couldn\'t find %s in %s' % (key, name))
            elif cursor.rowcount == 1:
                irc.reply(cursor.fetchone()[0])
            else:
                values = [t[0] for t in cursor.fetchall()]
                irc.reply('%s could be %s' % (key, ', or '.join(values)))
        else:
            sql = """SELECT key, value FROM %s
                     ORDER BY random() LIMIT 1""" % name
            try:
                cursor.execute(sql)
            except sqlite.DatabaseError, e:
                if 'no such table' in str(e):
                    irc.error('I don\'t have a domain %r' % name)
                else:
                    irc.error(str(e))
                return
            (key, value) = cursor.fetchone()
            irc.reply('%s: %s' % (key, value))
            
            
Class = Lookup

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
