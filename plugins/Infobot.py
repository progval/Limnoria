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
Add the module docstring here.  This will be used by the setup.py script.
"""

from baseplugin import *

import os.path

import sqlite

import privmsgs
import callbacks

def makeDb(filename):
    if os.path.exists(filename):
        return sqlite.connect(filename)
    db = sqlite.connect(filename)
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE is (
                      key TEXT,
                      value TEXT
                      )""")
    cursor.execute("""CREATE TABLE are (
                      key TEXT,
                      value TEXT
                      )""")
    cursor.execute("""CREATE TABLE dont_knows (saying TEXT)""")
    for s in ('I don\'t know.', 'No idea.', 'I don\'t have a clue.', 'Dunno.'):
        cursor.execute("""INSERT INTO dont_knows VALUES (%s)""", s)
    cursor.execute("""CREATE TABLE statements (saying TEXT)""")
    for s in ('I heard', 'Rumor has it', 'I think', 'I\'m pretty sure'):
        cursor.execute("""INSERT INTO statements VALUES (%s)""", s)
    cursor.execute("""CREATE TABLE confirms (saying TEXT)""")
    for s in ('Gotcha', 'Ok', '10-4', 'I hear ya', 'Got it'):
        cursor.execute("""INSERT INTO confirms VALUES (%s)""", s)
    cursor.execute("""CREATE INDEX is_key ON is (key)""")
    cursor.execute("""CREATE INDEX are_key ON are (key)""")
    db.commmit()
    return db

class Infobot(callbacks.PrivmsgRegexp):
    def __init__(self):
        self.db = makeDb(os.path.join(conf.dataDir, 'Infobot.db'))
        self.cursor = db.cursor()

    def getRandomSaying(self, table):
        sql = 'SELECT saying FROM %s ORDER BY random() LIMIT 1' % table
        cursor.execute(sql)
        return cursor.fetchone()[0]


Class = Infobot
        
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
