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

from baseplugin import *

import string
import random
import os.path
import urllib2

import sqlite

import debug
import privmsgs
import callbacks

dbFile = os.path.join(conf.dataDir, 'Debian.db')

def getIndex():
    return urllib2.urlopen('ftp://ftp.us.debian.org' \
                         '/debian/dists/unstable/main/binary-i386/Packages.gz')

def makeDb(dbfilename, indexfd, replace=False):
    if os.path.exists(filename):
        if replace:
            os.remove(filename)
        else:
            indexfd.close()
            return sqlite.connect(dbfilename)
    db = sqlite.connect(filename)
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE packages (
                      id INTEGER PRIMARY KEY,
                      package TEXT,
                      priority TEXT,
                      section TEXT,
                      installed_size INTEGER,
                      maintainer TEXT,
                      architecture TEXT,
                      source TEXT,
                      version TEXT,
                      depends TEXT,
                      filename TEXT,
                      size INTEGER,
                      md5sum TEXT,
                      short_description TEXT,
                      long_description TEXT
                      )""")
    lines = []
    for line in indexfd:
        if line == '\n':
            # Last line of record.
            s = ''.join(lines)
            m = email.message_from_string(s)
            descrlines = map(str.strip, m['description'].splitlines())
            shortdescr = descrlines.pop(0)
            longdescr = ' '.join(descrlines)
            cursor.execute("""INSERT INTO packages VALUES (
                              NULL,   %s, %s, %s, %s, %s, %s,
                              %s, %s, %s, %s, %s, %s, %s, %s
                              )""", m['package'], m['priority'], m['section'],
                         m['installed-size'],m['maintainer'],m['architecture'],
                         m['source'],m['version'],m['depends'],m['filename'],
                         m['size'], m['md5sum'], shortdescr, longdescr)
            lines = []
        else:
            lines.append(line)
    indexfd.close()
    db.commit()
    return db


class Debian(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = makeDb(dbFile, getIndex())

    def numdebs(self, irc, msg, args):
        "takes no arguments"
        cursor = self.db.cursor()
        cursor.execute("""SELECT COUNT(id) FROM packages""")
        number = cursor.fetchone()[0]
        irc.reply(msg, 'There are %s ports in my database.' % number)


Class = Debian

if __name__ == '__main__':
    makeDb(dbFile, getIndex(), replace=True)
