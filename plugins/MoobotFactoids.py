#!/usr/bin/python

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
Moobot factoid compatibility module.  Overrides the replyWhenNotCommand
behavior so that when someone addresses the bot with anything other than a
command, it checks the factoid database for a key that matches what was said
and if nothing is found, responds with an entry from the "dunno" database.
"""

import plugins

import os
import sets
import time
import shlex
import string
import random
import sqlite
from cStringIO import StringIO

import conf
import debug
import ircdb
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks

import OwnerCommands

dbfilename = os.path.join(conf.dataDir, 'MoobotFactoids.db')

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load MoobotFactoids')

example = utils.wrapLines("""
Add an example IRC session using this module here.
""")


allchars = string.maketrans('', '')
class OptionList(object):
    validChars = allchars.translate(allchars, '|()')
    def _insideParens(self, lexer):
        ret = []
        while True:
            token = lexer.get_token()
            if not token:
                raise SyntaxError, 'Missing ")"'
            elif token == ')':
                return ret
            elif token == '(':
                ret.append(self._insideParens(lexer))
            elif token == '|':
                continue
            else:
                ret.append(token)

    def tokenize(self, s):
        lexer = shlex.shlex(StringIO(s))
        lexer.commenters = ''
        lexer.quotes = ''
        lexer.whitespace = ''
        lexer.wordchars = self.validChars
        ret = []
        while True:
            token = lexer.get_token()
            if not token:
                break
            elif token == '(':
                ret.append(self._insideParens(lexer))
            elif token == ')':
                raise SyntaxError, 'Spurious ")"'
            else:
                ret.append(token)
        return ret

def tokenize(s):
    return OptionList().tokenize(s)

def pick(L, recursed=False):
    L = L[:]
    for (i, elt) in enumerate(L):
        if isinstance(elt, list):
            L[i] = pick(elt, recursed=True)
    if recursed:
        return random.choice(L)
    else:
        return L

class MoobotFactoids(callbacks.PrivmsgCommandAndRegexp):
    priority = 1000
    addressedRegexps = sets.Set(['addFactoids'])
    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.makeDB(dbfilename)
        # Set up the "reply when not command" behavior
        conf.replyWhenNotCommand = True
        MiscCommands = OwnerCommands.loadPluginModule('MiscCommands')
        # Gotta make sure we restore this when we unload
        self.originalReplyWhenNotCommand = MiscCommands.replyWhenNotCommand
        MiscCommands.replyWhenNotCommand = self._checkFactoids

    def makeDB(self, filename):
        """create MoobotFactoids database and tables"""
        if os.path.exists(filename):
            self.db = sqlite.connect(filename)
            return
        self.db = sqlite.connect(filename, converters={'bool': bool})
        cursor = self.db.cursor()
        cursor.execute("""CREATE TABLE factoids (
                          key TEXT PRIMARY KEY,
                          created_by INTEGER,
                          created_at TIMESTAMP,
                          modified_by INTEGER,
                          modified_at TIMESTAMP,
                          locked_by INTEGER,
                          locked_at TIMESTAMP,
                          last_requested_by TEXT,
                          last_requested_at TIMESTAMP,
                          fact TEXT,
                          requested_count INTEGER
                          )""")
        cursor.execute("""CREATE TABLE dunnos (
                          id INTEGER PRIMARY KEY,
                          added_by INTEGER,
                          added_at TIMESTAMP,
                          dunno TEXT
                          )""")
        self.db.commit()

    def die(self):
        # Handle DB stuff
        self.db.commit()
        self.db.close()
        del self.db
        # Recover from clobbering this command earlier
        MiscCommands = OwnerCommands.loadPluginModule('MiscCommands')
        MiscCommands.replyWhenNotCommand = self.originalReplyWhenNotCommand

    def parseFactoid(self, fact):
        type = "define"  # Default is to just spit the factoid back as a
                         # definition of what the key is (i.e., "foo is bar")
        newfact = ''.join(pick(tokenize(fact)))
        if newfact.startswith("<reply>"):
            newfact = newfact.replace("<reply>", "", 1)
            type = "reply"
        elif newfact.startswith("<action>"):
            newfact = newfact.replace("<action>", "", 1)
            type = "action"
        return (type, newfact)

    def updateFactoidRequest(self, key, hostmask):
        """Updates the last_requested_* fields of a factoid row"""
        cursor = self.db.cursor()
        cursor.execute("""UPDATE factoids SET
                          last_requested_by = %s,
                          last_requested_at = %s,
                          requested_count = requested_count +1
                          WHERE key = %s""",
                          hostmask, int(time.time()), key)
        self.db.commit()

    def _checkFactoids(self, irc, msg, _):
        # Strip the bot name
        key = callbacks.addressed(irc.nick, msg)
        # Check the factoid db for an appropriate reply
        cursor = self.db.cursor()
        cursor.execute("""SELECT fact FROM factoids WHERE key = %s""", key)
        if cursor.rowcount == 0:
            irc.reply(msg, "Would reply with a dunno here")
        else:
            fact = cursor.fetchone()[0]
            # Update the requested count/requested by for this key
            hostmask = msg.prefix
            self.updateFactoidRequest(key, hostmask)
            # Now actually get the factoid and respond accordingly
            (type, text) = self.parseFactoid(fact)
            if type == "action":
                irc.queueMsg(ircmsgs.action(ircutils.replyTo(msg), text))
            elif type == "reply":
                irc.reply(msg, text)
            elif type == "define":
                irc.reply(msg, "%s is %s" % (key, text))
            else:
                irc.error(msg, "Spurious type from parseFactoid.")

    def addFactoids(self, irc, msg, match):
        r"^(.+)\s+(is|are|_is_|_are_)\s+(.+)"
        # Must be registered!
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        key, _, fact = match.groups()
        cursor = self.db.cursor()
        # Check and make sure it's not in the DB already
        cursor.execute("""SELECT * FROM factoids WHERE key = %s""", key)
        if cursor.rowcount != 0:
            irc.error(msg, "Factoid '%s' already exists." % key)
            return
        # Otherwise, 
        cursor.execute("""INSERT INTO factoids VALUES
                          (%s, %s, %s, NULL, NULL, NULL, NULL, NULL, NULL,
                           %s, 0)""",
                           key, id, int(time.time()), fact)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def literal(self, irc, msg, args):
        """<factoid key>

        Returns the literal factoid for the given factoid key.  No parsing of
        the factoid value is done as it is with normal retrieval.
        """
        key = privmsgs.getArgs(args, needed=1)
        cursor = self.db.cursor()
        cursor.execute("""SELECT fact FROM factoids WHERE key = %s""", key)
        if cursor.rowcount == 0:
            irc.error(msg, "No such factoid: %s" % key)
            return
        else:
            fact = cursor.fetchone()[0]
            irc.reply(msg, fact)

    def factinfo(self, irc, msg, args):
        """<factoid key>

        Returns the various bits of info on the factoid for the given key.
        """
        key = privmsgs.getArgs(args, needed=1)
        # Start building the response string
        s = key + ": "
        # Next, get all the info and build the response piece by piece
        cursor = self.db.cursor()
        cursor.execute("""SELECT created_by, created_at, modified_by,
                          modified_at, last_requested_by, last_requested_at,
                          requested_count, locked_by, locked_at FROM
                          factoids WHERE key = %s""", key)
        if cursor.rowcount == 0:
            irc.error(msg, "No such factoid: %s" % key)
            return
        (created_by, created_at, modified_by, modified_at, last_requested_by,
         last_requested_at, requested_count, locked_by, locked_at) = \
         cursor.fetchone()
        # First, creation info.
        # Map the integer created_by to the username
        creat_by = ircdb.users.getUser(created_by).name
        creat_at = time.strftime(conf.humanTimestampFormat,
                                 time.localtime(int(created_at)))
        s += "Created by %s on %s." % (creat_by, creat_at)
        # Next, modification info, if any.
        if modified_by is not None:
            mod_by = ircdb.users.getUser(modified_by).name
            mod_at = time.strftime(conf.humanTimestampFormat,
                                   time.localtime(int(modified_at)))
            s += " Last modified by %s on %s." % (mod_by, mod_at)
        # Next, last requested info, if any
        if last_requested_by is not None:
            last_by = last_requested_by  # not an int user id
            last_at = time.strftime(conf.humanTimestampFormat,
                                    time.localtime(int(last_requested_at)))
            req_count = requested_count
            s += " Last requested by %s on %s, requested %s times." % \
                 (last_by, last_at, req_count)
        # Last, locked info
        if locked_by is not None:
             lock_by = ircdb.users.getUser(locked_by).name
             lock_at = time.strftime(conf.humanTimestampFormat,
                                     time.localtime(int(locked_at)))
             s += " Locked by %s on %s." % (lock_by, lock_at)
        irc.reply(msg, s)

    def lock(self, irc, msg, args):
        """<factoid key>

        Locks the factoid with the given factoid key.  Requires that the user
        be registered and have created the factoid originally.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        key = privmsgs.getArgs(args, needed=1)
        cursor = self.db.cursor() 
        cursor.execute("""SELECT created_by, locked_by FROM factoids
                          WHERE key = %s""", key)
        if cursor.rowcount == 0:
            irc.error(msg, "No such factoid: %s" % key)
            return
        (created_by, locked_by) = cursor.fetchone()
        if locked_by is not None:
            irc.error(msg, "Factoid '%s' is already locked." % key)
            return
        if created_by != id:
            irc.error(msg, "Cannot lock someone else's factoid." % key)
            return
        cursor.execute("""UPDATE factoids SET locked_by = %s, locked_at = %s
                          WHERE key = %s""", id, int(time.time()), key)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

Class = MoobotFactoids

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
