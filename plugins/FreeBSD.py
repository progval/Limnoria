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
Provides FreeBSD ports searching and other FreeBSD-specific services.
"""

import plugins

import time
import string
import getopt
import os.path
import urllib2

import sqlite

import conf
import debug
import ircutils
import privmsgs
import callbacks

indexFile = 'INDEX'
indexUrl = 'ftp://ftp.freebsd.org/pub/FreeBSD/ports/i386/packages-stable/INDEX'
dbFile = os.path.join(conf.dataDir, 'FreeBSD.db')

def getIndex():
    """Returns a file-like object that is the Ports index."""
    if os.path.exists(indexFile):
        return file(indexFile, 'r')
    else:
        return urllib2.urlopen(indexUrl)

def makeDb(dbfilename, indexfd, replace=False):
    if os.path.exists(dbfilename):
        if replace:
            os.remove(dbfilename)
        else:
            indexfd.close()
            return sqlite.connect(dbfilename)
    db = sqlite.connect(dbfilename)
    cursor = db.cursor()
    cursor.execute("""PRAGMA cache_size=20000""")
    cursor.execute("""CREATE TABLE ports (
                      id INTEGER PRIMARY KEY,
                      name TEXT UNIQUE ON CONFLICT IGNORE,
                      path TEXT,
                      info TEXT,
                      maintainer TEXT,
                      website TEXT
                      )""")
    cursor.execute("""CREATE TABLE categories (
                      id INTEGER PRIMARY KEY,
                      name TEXT UNIQUE ON CONFLICT IGNORE
                      )""")
    cursor.execute("""CREATE TABLE in_category (
                      port_id INTEGER,
                      category_id INTEGER,
                      UNIQUE (port_id, category_id) ON CONFLICT IGNORE
                      )""")
    cursor.execute("""CREATE TABLE depends (
                      port_id INTEGER,
                      depends_id INTEGER,
                      UNIQUE (port_id, depends_id) ON CONFLICT IGNORE
                      )""")
    lines = map(lambda s: s.rstrip().split('|'), indexfd)
    for fields in lines:
        # First, add all the entries to the ports table.
        name = fields[0]
        path = fields[1]
        info = fields[3]
        maintainer = fields[5]
        category = fields[6]
        website = fields[9]
        cursor.execute("""INSERT INTO ports
                          VALUES (NULL, %s, %s, %s, %s, %s)""",
                       name, path, info, maintainer, website)
        for category in category.split():
            cursor.execute("INSERT INTO categories VALUES (NULL, %s)",category)
            cursor.execute("""INSERT INTO in_category
                              SELECT ports.id, categories.id
                              FROM ports, categories
                              WHERE ports.name=%s AND categories.name=%s""",
                           name, category)
    for fields in lines:
        # Now, add dependencies.
        name = fields[0]
        b_deps = fields[7]
        r_deps = fields[8]
        for dep in b_deps.split():
            cursor.execute("""SELECT id FROM ports WHERE name=%s""", name)
            port_id = cursor.fetchone()[0]
            cursor.execute("""SELECT id FROM ports WHERE name=%s""", dep)
            depends_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO depends VALUES (%s, %s)",
                           port_id, depends_id)
##         for dep in r_deps.split():
##             cursor.execute("""SELECT id FROM ports WHERE name=%s""", name)
##             port_id = cursor.fetchone()[0]
##             cursor.execute("""SELECT id FROM ports WHERE name=%s""", dep)
##             depends_id = cursor.fetchone()[0]
##             cursor.execute("INSERT INTO depends VALUES (%s, %s)",
##                            port_id, depends_id)
    indexfd.close()
    cursor.execute("CREATE INDEX in_category_port_id ON in_category (port_id)")
    cursor.execute("CREATE INDEX depends_port_id ON depends (port_id)")
    cursor.execute("CREATE INDEX depends_depends_id ON depends (depends_id)")
    db.commit()
    return db


class FreeBSD(callbacks.Privmsg):
    """
    Module for FreeBSD-specific stuff.  Currently contains only the commands
    for searching the Ports database.
    """
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = makeDb(dbFile, getIndex())
        self.lastUpdated = time.time()

    _globtrans = string.maketrans('?*', '_%')
    def searchports(self, irc, msg, args):
        """[--name=<glob>] [--category=<glob>] [--depends=<glob>] """ \
        """[--info=<glob>] [--maintainer=<glob>] [--website=<glob>]

        Returns the names of ports matching the constraints given.  Each
        constraint can be specified as an unambiguous prefix of the constraint
        name -- i.e., --n works for --name.  Arguments not preceded by switches
        are interpreted as having been preceded by the --name switch.
        """
        (optlist, rest) = getopt.getopt(args, '', ['name=', 'category=',
                                                   'depends=', 'info=',
                                                   'maintainer=', 'website='])
        for s in rest:
            optlist.append(('--name', s))
        cursor = self.db.cursor()
        tables = ['ports']
        constraints = []
        arguments = []
        dependsConstraints = []
        dependsArguments = []
        for (option, argument) in optlist:
            if len(argument.translate(string.ascii, '*%_?')) < 2:
                irc.error(msg, 'You must provide 2 non-wildcard characters.')
            option = option[2:]
            argument = argument.translate(self._globtrans)
            if option in ('name', 'info', 'maintainer', 'website'):
                constraints.append('ports.%s LIKE %%s' % option)
                arguments.append(argument)
            elif option == 'category':
                if 'categories' not in tables:
                    tables.insert(0, 'categories')
                    tables.insert(0, 'in_category')
                constraints.append('categories.name LIKE %s')
                arguments.append(argument)
                constraints.append('in_category.category_id=categories.id')
                constraints.append('in_category.port_id=ports.id')
            elif option == 'depends':
                if 'depends' not in tables:
                    tables.append('depends')
                    dependsConstraints.append('ports.id=depends.port_id')
                    dependsConstraints.append("""depends.depends_id IN
                                                 (SELECT ports.id FROM ports
                                                 WHERE ports.name LIKE %s)""")
                else:
                    for (i, s) in enumerate(dependsConstraints):
                        if s.startswith('depends.depends_id IN'):
                            s = s.replace('%s)', '%s OR ports.name LIKE %s)')
                            dependsConstraints[i] = s
                dependsArguments.append(argument)
        sql = """SELECT ports.name FROM %s WHERE %s""" % \
              (', '.join(tables), ' AND '.join(constraints+dependsConstraints))
        debug.printf(sql)
        cursor.execute(sql, *(arguments+dependsArguments))
        if cursor.rowcount == 0:
            irc.reply(msg, 'No ports matched those constraints.')
            return
        names = [t[0] for t in cursor.fetchall()]
        shrunkenNames = names[:]
        ircutils.shrinkList(shrunkenNames)
        if len(names) != len(shrunkenNames):
            irc.reply(msg, '%s ports matched those constraints.  ' \
                           'Please narrow your search.' % cursor.rowcount)
        else:
            irc.reply(msg, ', '.join(names))


    def numports(self, irc, msg, args):
        """takes no arguments

        Returns the total number of ports in the database.
        """
        cursor = self.db.cursor()
        cursor.execute("""SELECT COUNT(id) FROM ports""")
        number = cursor.fetchone()[0]
        irc.reply(msg, 'There are %s ports in my database.' % number)

    def randomport(self, irc, msg, args):
        """takes no arguments

        Returns a random port from the database.
        """
        cursor = self.db.cursor()
        cursor.execute("""SELECT name, info, website, maintainer FROM ports
                          ORDER BY random()
                          LIMIT 1""")
        (name, info, website, maintainer) = cursor.fetchone()
        s = '%s: %s (maintained by %s; more info at %s)' %\
            (name, info, website, maintainer)
        irc.reply(msg, s)

    def portinfo(self, irc, msg, args):
        """<port name>

        Gives the information from the database on a given port.
        """
        name = privmsgs.getArgs(args)
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, info, maintainer, website FROM ports
                          WHERE name=%s""", name)
        if cursor.rowcount == 0:
            irc.reply(msg, 'No port matched the %r.' % name)
            return
        (id, info, maintainer, website) = cursor.fetchone()
        cursor.execute("""SELECT categories.name FROM categories, in_category
                          WHERE in_category.port_id=%s
                          AND categories.id=in_category.category_id""", id)
        categories = map(lambda t: t[0], cursor.fetchall())
        irc.reply(msg, '%s; Categories: %s; Maintainer: %s; Website: %s' %
                     (info, ', '.join(categories), maintainer, website))


Class = FreeBSD


if __name__ == '__main__':
    makeDb(dbFile, getIndex(), replace=True)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
