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
import types

import sqlite

import conf
import utils
import privmsgs
import callbacks


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
    

def getDb():
    return sqlite.connect(os.path.join(conf.dataDir, 'Lookup.db'))

class Lookup(callbacks.Privmsg):
    def die(self):
        db = getDb()
        db.commit()
        db.close()
        del db

    def remove(self, irc, msg, args):
        """<name>

        Removes the lookup for <name>.
        """
        name = privmsgs.getArgs(args)
        db = getDb()
        cursor = db.cursor()
        try:
            cursor.execute("""DROP TABLE %s""" % name)
            db.commit()
            delattr(self.__class__, name)
            irc.reply(msg, conf.replySuccess)
        except sqlite.DatabaseError:
            irc.error(msg, 'No such lookup exists.')

    _splitRe = re.compile(r'(?<!\\):')
    def add(self, irc, msg, args):
        """<name> <filename>

        Adds a lookup for <name> with the key/value pairs specified in the
        colon-delimited file specified by <filename>.  <filename> is searched
        for in conf.dataDir.  Use 'lookup <name> <key>' to get the value of
        the key in the file.
        """
        (name, filename) = privmsgs.getArgs(args, required=2)
        db = getDb()
        cursor = db.cursor()
        try:
            cursor.execute("""SELECT * FROM %s LIMIT 1""" % name)
            self.addCommand(name)
            irc.reply(msg, conf.replySuccess)
        except sqlite.DatabaseError:
            # Good, there's no such database.
            try:
                filename = os.path.join(conf.dataDir, filename)
                fd = file(filename)
            except EnvironmentError, e:
                irc.error('Could not open %s: %s' % (filename, e))
                return
            cursor.execute("""CREATE TABLE %s (key TEXT, value TEXT)""" % name)
            sql = """INSERT INTO %s VALUES (%%s, %%s)""" % name
            for line in fd:
                line = line.rstrip('\r\n')
                if not line or line.startswith('#'):
                    continue
                try:
                    (key, value) = self._splitRe.split(line, 1)
                    key = key.replace('\\:', ':')
                except ValueError:
                    irc.error(msg, 'Invalid line in %s: %r' % (filename, line))
                    return
                cursor.execute(sql, key, value)
            cursor.execute("CREATE INDEX %s_keys ON %s (key)" % (name, name))
            db.commit()
            self.addCommand(name)
            cb = irc.getCallback('Alias')
            irc.reply(msg, conf.replySuccess)

    def addCommand(self, name):
        def f(self, irc, msg, args):
            args.insert(0, name)
            self._lookup(irc, msg, args)
        f = types.FunctionType(f.func_code, f.func_globals,
                               f.func_name, closure=f.func_closure)
        setattr(self.__class__, name, f)

    def _lookup(self, irc, msg, args):
        """<name> <key>

        Looks up the value of <key> in the domain <name>.
        """
        (name, key) = privmsgs.getArgs(args, optional=1)
        db = getDb()
        cursor = db.cursor()
        if key:
            sql = """SELECT value FROM %s WHERE key LIKE %%s""" % name
            try:
                cursor.execute(sql, key)
            except sqlite.DatabaseError, e:
                if 'no such table' in str(e):
                    irc.error(msg, 'I don\'t have a domain %s' % name)
                else:
                    irc.error(msg, str(e))
                return
            if cursor.rowcount == 0:
                irc.error(msg, 'I couldn\'t find %s in %s' % (key, name))
            elif cursor.rowcount == 1:
                irc.reply(msg, cursor.fetchone()[0])
            else:
                values = [t[0] for t in cursor.fetchall()]
                irc.reply(msg, '%s could be %s' % (key, ', or '.join(values)))
        else:
            sql = """SELECT key, value FROM %s
                     ORDER BY random() LIMIT 1""" % name
            try:
                cursor.execute(sql)
            except sqlite.DatabaseError, e:
                if 'no such table' in str(e):
                    irc.error(msg, 'I don\'t have a domain %r' % name)
                else:
                    irc.error(msg, str(e))
                return
            (key, value) = cursor.fetchone()
            irc.reply(msg, '%s: %s' % (key, value))
            
            
Class = Lookup

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
