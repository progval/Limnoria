#!/usr/bin/env python

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

__revision__="$Id$"

import plugins

import os
import sets
import time
import shlex
import string
import random
from itertools import imap
from cStringIO import StringIO

import registry

import conf
import ircdb
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks

import Owner

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

dbfilename = os.path.join(conf.supybot.directories.data(), 'MoobotFactoids')


allchars = string.maketrans('', '')
class OptionList(object):
    validChars = allchars.translate(allchars, '|()')
    def _insideParens(self, lexer):
        ret = []
        while True:
            token = lexer.get_token()
            if not token:
                return '(%s' % ''.join(ret) #)
            elif token == ')':
                if len(ret) > 1:
                    if '|' in ret:
                        L = map(''.join,utils.itersplit(lambda x: x=='|', ret))
                        return random.choice(L)
                    else:
                        return ''.join(ret)
                    return [x for x in ret if x != '|']
                elif len(ret) == 1:
                        return '(%s)' % ret[0]
                else:
                    return '()'
            elif token == '(':
                ret.append(self._insideParens(lexer))
            elif token == '|':
                ret.append(token)
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
            else:
                ret.append(token)
        return ''.join(ret)

def pickOptions(s):
    return OptionList().tokenize(s)

conf.registerPlugin('MoobotFactoids')
conf.registerChannelValue(conf.supybot.plugins.MoobotFactoids,
    'showFactoidIfOnlyOneMatch', registry.Boolean(True, """Determines whether
    or not the factoid value will be shown when a listkeys search returns only
    one factoid key."""))

class MoobotDBHandler(plugins.DBHandler):
    def makeDb(self, filename):
        """create MoobotFactoids database and tables"""
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename, converters={'bool': bool})
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE factoids (
                              key TEXT PRIMARY KEY,
                              created_by INTEGER,
                              created_at TIMESTAMP,
                              modified_by INTEGER,
                              modified_at TIMESTAMP,
                              locked_at TIMESTAMP,
                              locked_by INTEGER,
                              last_requested_by TEXT,
                              last_requested_at TIMESTAMP,
                              fact TEXT,
                              requested_count INTEGER
                              )""")
            db.commit()
        return db

    
class MoobotFactoids(callbacks.PrivmsgCommandAndRegexp):
    priority = 98
    addressedRegexps = ['changeFactoid', 'augmentFactoid',
                        'replaceFactoid', 'addFactoid']
    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.dbHandler = MoobotDBHandler(dbfilename)

    def die(self):
        # Handle DB stuff
        self.dbHandler.die()

    def _parseFactoid(self, irc, msg, fact):
        type = "define"  # Default is to just spit the factoid back as a
                         # definition of what the key is (i.e., "foo is bar")
        newfact = pickOptions(fact)
        if newfact.startswith("<reply>"):
            newfact = newfact[7:]
            type = "reply"
        elif newfact.startswith("<action>"):
            newfact = newfact[8:]
            type = "action"
        elif newfact.startswith("see "):
            newfact = newfact[4:]
            type = "refer"
            # shortcut the substitutions here
            return (type, newfact)
        newfact = newfact.strip()
        newfact = plugins.standardSubstitute(irc, msg, newfact)
        return (type, newfact)

    def updateFactoidRequest(self, key, hostmask):
        """Updates the last_requested_* fields of a factoid row"""
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""UPDATE factoids SET
                          last_requested_by = %s,
                          last_requested_at = %s,
                          requested_count = requested_count +1
                          WHERE key = %s""",
                          hostmask, int(time.time()), key)
        db.commit()

    def randomfactoid(self, irc, msg, args):
        """<takes no arguments>

        Displays a random factoid (along with its key) from the database.
        """
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT fact, key FROM factoids 
                          ORDER BY random() LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error('No factoids in the database.')
            return
        (fact, key) = cursor.fetchone()
        irc.reply("%r is %r" % (key, fact))


    def invalidCommand(self, irc, msg, tokens):
        key = ' '.join(tokens)
        key = key.rstrip('?!')
        if key.startswith('\x01'):
            return
        # Check the factoid db for an appropriate reply
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT fact FROM factoids WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            return False
        else:
            fact = cursor.fetchone()[0]
            # Update the requested count/requested by for this key
            hostmask = msg.prefix
            self.updateFactoidRequest(key, hostmask)
            # Now actually get the factoid and respond accordingly
            (type, text) = self._parseFactoid(irc, msg, fact)
            if type == "action":
                irc.reply(text, action=True)
            elif type == "reply":
                irc.reply(text, prefixName=False)
            elif type == "define":
                irc.reply("%s is %s" % (key, text), prefixName=False)
            elif type == "refer":
                # text here is the new key to refer to 
                msg.args = [s.replace(key, text) for s in msg.args]
                newtokens = [s.replace(key, text) for s in tokens]
                self.invalidCommand(irc, wmsg, newtokens) 
            else:
                irc.error("Spurious type from _parseFactoid.")
            return True

    def addFactoid(self, irc, msg, match):
        r"^(?!\x01)(.+?)\s+(?:is|_is_)\s+(.+)"
        # Check and see if there is a command that matches this that didn't
        # get caught due to nesting
#        cb = callbacks.findCallbackForCommand(irc, msg)
#        if cb:
#            irc.reply(irc.getHelp(cb[0].config))
#            return
        # First, check and see if the entire message matches a factoid key
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        key = match.group().rstrip('?! ')
        cursor.execute("""SELECT * FROM factoids WHERE key LIKE %s""", key)
        if cursor.rowcount != 0:
            self.invalidCommand(irc, msg, callbacks.tokenize(match.group()))
            return
        # Okay, we are REALLY adding stuff
        # Must be registered!
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        key, fact = match.groups()
        # These are okay, unless there's an _is_ in there, in which case
        # we split on the leftmost one.
        if '_is_' in match.group():
            key, fact = imap(str.strip, match.group().split('_is_', 1))
        # Strip the key of punctuation and spaces
        key = key.rstrip('?! ')
        # Check and make sure it's not in the DB already
        cursor.execute("""SELECT * FROM factoids WHERE key LIKE %s""", key)
        if cursor.rowcount != 0:
            irc.error('Factoid %r already exists.' % key)
            return
        # Otherwise, 
        cursor.execute("""INSERT INTO factoids VALUES
                          (%s, %s, %s, NULL, NULL, NULL, NULL, NULL, NULL,
                           %s, 0)""",
                           key, id, int(time.time()), fact)
        db.commit()
        irc.replySuccess()

    def changeFactoid(self, irc, msg, match):
        r"(.+)\s+=~\s+(.+)"
        # Must be registered!
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        key, regexp = match.groups()
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        # Check and make sure it's in the DB 
        cursor.execute("""SELECT locked_at, fact FROM factoids
                          WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            irc.error("Factoid %r not found." % key)
            return
        # No dice if it's locked, no matter who it is
        (locked_at, fact) = cursor.fetchone()
        if locked_at is not None:
            irc.error("Factoid %r is locked." % key)
            return
        # It's fair game if we get to here
        try:
            r = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error("Invalid regexp: %r" % regexp)
            return
        new_fact = r(fact) 
        cursor.execute("""UPDATE factoids   
                          SET fact = %s, modified_by = %s,   
                          modified_at = %s WHERE key = %s""",
                          new_fact, id, int(time.time()), key)
        db.commit()
        irc.replySuccess()

    def augmentFactoid(self, irc, msg, match):
        r"(.+?) is also (.+)"
        # Must be registered!
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        key, new_text = match.groups()
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        # Check and make sure it's in the DB 
        cursor.execute("""SELECT locked_at, fact FROM factoids
                          WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            irc.error("Factoid %r not found." % key)
            return
        # No dice if it's locked, no matter who it is
        (locked_at, fact) = cursor.fetchone()
        if locked_at is not None:
            irc.error("Factoid %r is locked." % key)
            return
        # It's fair game if we get to here
        new_fact = "%s, or %s" % (fact, new_text)
        cursor.execute("""UPDATE factoids
                          SET fact = %s, modified_by = %s,
                          modified_at = %s WHERE key = %s""",
                          new_fact, id, int(time.time()), key)
        db.commit()
        irc.replySuccess()

    def replaceFactoid(self, irc, msg, match):
        r"^no,?\s+(.+?)\s+is\s+(.+)"
        # Must be registered!
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        key, new_fact = match.groups()
        # These are okay, unless there's an _is_ in there, in which case
        # we split on the leftmost one.
        if '_is_' in match.group():
            key, new_fact = imap(str.strip, match.group().split('_is_', 1))
            key = key.split(' ', 1)[1]  # Take out everything to first space
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        # Check and make sure it's in the DB 
        cursor.execute("""SELECT locked_at, fact FROM factoids
                          WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            irc.error("Factoid %r not found." % key)
            return
        # No dice if it's locked, no matter who it is
        (locked_at, _) = cursor.fetchone()
        if locked_at is not None:
            irc.error("Factoid %r is locked." % key)
            return
        # It's fair game if we get to here
        cursor.execute("""UPDATE factoids
                          SET fact = %s, created_by = %s,
                          created_at = %s, modified_by = NULL,
                          modified_at = NULL, requested_count = 0,
                          last_requested_by = NULL, last_requested_at = NULL,
                          locked_at = NULL
                          WHERE key = %s""",
                          new_fact, id, int(time.time()), key)
        db.commit()
        irc.replySuccess()

    def literal(self, irc, msg, args):
        """<factoid key>

        Returns the literal factoid for the given factoid key.  No parsing of
        the factoid value is done as it is with normal retrieval.
        """
        key = privmsgs.getArgs(args, required=1)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT fact FROM factoids WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            irc.error("No such factoid: %r" % key)
            return
        else:
            fact = cursor.fetchone()[0]
            irc.reply(fact)

    def factinfo(self, irc, msg, args):
        """<factoid key>

        Returns the various bits of info on the factoid for the given key.
        """
        key = privmsgs.getArgs(args, required=1)
        # Start building the response string
        s = key + ": "
        # Next, get all the info and build the response piece by piece
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT created_by, created_at, modified_by,
                          modified_at, last_requested_by, last_requested_at,
                          requested_count, locked_by, locked_at FROM
                          factoids WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            irc.error("No such factoid: %r" % key)
            return
        (created_by, created_at, modified_by, modified_at, last_requested_by,
         last_requested_at, requested_count, locked_by,
         locked_at) = cursor.fetchone()
        # First, creation info.
        # Map the integer created_by to the username
        creat_by = ircdb.users.getUser(created_by).name
        creat_at = time.strftime(conf.supybot.humanTimestampFormat(),
                                 time.localtime(int(created_at)))
        s += "Created by %s on %s." % (creat_by, creat_at)
        # Next, modification info, if any.
        if modified_by is not None:
            mod_by = ircdb.users.getUser(modified_by).name
            mod_at = time.strftime(conf.supybot.humanTimestampFormat(),
                                   time.localtime(int(modified_at)))
            s += " Last modified by %s on %s." % (mod_by, mod_at)
        # Next, last requested info, if any
        if last_requested_by is not None:
            last_by = last_requested_by  # not an int user id
            last_at = time.strftime(conf.supybot.humanTimestampFormat(),
                                    time.localtime(int(last_requested_at)))
            req_count = requested_count
            times_str = utils.nItems('time', requested_count)
            s += " Last requested by %s on %s, requested %s." % \
                 (last_by, last_at, times_str)
        # Last, locked info
        if locked_at is not None:
            lock_at = time.strftime(conf.supybot.humanTimestampFormat(),
                                     time.localtime(int(locked_at)))
            lock_by = ircdb.users.getUser(locked_by).name
            s += " Locked by %s on %s." % (lock_by, lock_at)
        irc.reply(s)

    def _lock(self, irc, msg, args, lock=True):
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        key = privmsgs.getArgs(args, required=1)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT created_by, locked_by FROM factoids
                          WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            irc.error("No such factoid: %r" % key)
            return
        (created_by, locked_by) = cursor.fetchone()
        # Don't perform redundant operations
        if lock:
           if locked_by is not None:
               irc.error("Factoid %r is already locked." % key)
               return
        else:
           if locked_by is None:
               irc.error("Factoid %r is not locked." % key)
               return
        # Can only lock/unlock own factoids unless you're an admin
        if not (ircdb.checkCapability(id, 'admin') or created_by == id):
            s = "unlock"
            if lock:
               s = "lock"
            irc.error("Cannot %s someone else's factoid unless you "
                           "are an admin." % s)
            return
        # Okay, we're done, ready to lock/unlock
        if lock:
           locked_at = int(time.time())
        else:
           locked_at = None
           id = None
        cursor.execute("""UPDATE factoids SET locked_at = %s, locked_by = %s
                          WHERE key = %s""", locked_at, id, key)
        db.commit()
        irc.replySuccess()

    def lock(self, irc, msg, args):
        """<factoid key>

        Locks the factoid with the given factoid key.  Requires that the user
        be registered and have created the factoid originally.
        """
        self._lock(irc, msg, args, True)

    def unlock(self, irc, msg, args):
        """<factoid key>

        Unlocks the factoid with the given factoid key.  Requires that the
        user be registered and have locked the factoid.
        """
        self._lock(irc, msg, args, False)

    _mostCount = 10
    class MostException(Exception):
        pass
    def most(self, irc, msg, args):
        """<popular|authored|recent>

        Lists the most <popular|authored|recent> factoids.  <popular> lists the
        most frequently requested factoids.  <authored> lists the author with
        the most factoids.  <recent> lists the most recently created factoids.
        """
        arg = privmsgs.getArgs(args)
        arg = arg.capitalize()
        method = getattr(self, '_most%s' % arg, None)
        if method is None:
            raise callbacks.ArgumentError
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM factoids""")
        if int(cursor.fetchone()[0]) == 0:
            irc.error('I don\'t have any factoids in my database!')
        else:
            try:
                irc.reply(method(cursor, self._mostCount))
            except self.MostException, e:
                irc.error(str(e))

    def _mostAuthored(self, cursor, limit):
        cursor.execute("""SELECT created_by, count(key) FROM factoids
                          GROUP BY created_by
                          ORDER BY count(key) DESC LIMIT %s""", limit)
        L = ['%s (%s)' % (ircdb.users.getUser(t[0]).name, int(t[1]))
             for t in cursor.fetchall()]
        return 'Most prolific %s: %s' % \
               (utils.pluralize('author', len(L)), utils.commaAndify(L))

    def _mostRecent(self, cursor, limit):
        cursor.execute("""SELECT key FROM factoids
                          ORDER by created_at DESC LIMIT %s""", limit)
        L = [repr(t[0]) for t in cursor.fetchall()]
        return '%s: %s' % \
               (utils.nItems('factoid', len(L), between='latest'),
                utils.commaAndify(L))

    def _mostPopular(self, cursor, limit):
        cursor.execute("""SELECT key, requested_count FROM factoids
                          WHERE requested_count > 0
                          ORDER BY requested_count DESC LIMIT %s""", limit)
        if cursor.rowcount == 0:
            raise self.MostException, 'No factoids have been requested.'
        L = ['%r (%s)' % (t[0], t[1]) for t in cursor.fetchall()]
        return 'Top %s: %s' % \
               (utils.nItems('factoid', len(L), between='requested'),
                utils.commaAndify(L))

    def listauth(self, irc, msg, args):
        """<author name>

        Lists the keys of the factoids with the given author.  Note that if an
        author has an integer name, you'll have to use that author's id to use
        this function (so don't use integer usernames!).
        """
        author = privmsgs.getArgs(args, required=1)
        try:
            id = ircdb.users.getUserId(author)
        except KeyError:
            irc.error("No such user: %r" % author)
            return
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM factoids
                          WHERE created_by = %s
                          ORDER BY key""", id)
        if cursor.rowcount == 0:
            irc.reply("No factoids by %r found." % author)
            return
        keys = [repr(tup[0]) for tup in cursor.fetchall()]
        s = "Author search for %r (%s found): %s" % \
            (author, len(keys), utils.commaAndify(keys))
        irc.reply(s)

    def listkeys(self, irc, msg, args):
        """<text>

        Lists the keys of the factoids whose key contains the provided text.
        """
        search = privmsgs.getArgs(args, required=1)
        glob = '%' + search + '%'
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM factoids
                          WHERE key LIKE %s
                          ORDER BY key""",
                          glob)
        if cursor.rowcount == 0:
            irc.reply("No keys matching %r found." % search)
        elif cursor.rowcount == 1 and \
        self.registryValue('showFactoidIfOnlyOneMatch', msg.args[0]):
            key = cursor.fetchone()[0]
            self.invalidCommand(irc, msg, [key])
        else:
            keys = [repr(tup[0]) for tup in cursor.fetchall()]
            s = "Key search for %r (%s found): %s" % \
                (search, len(keys), utils.commaAndify(keys))
            irc.reply(s)

    def listvalues(self, irc, msg, args):
        """<text>

        Lists the keys of the factoids whose value contains the provided text.
        """
        search = privmsgs.getArgs(args, required=1)
        glob = '%' + search + '%'
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM factoids
                          WHERE fact LIKE %s
                          ORDER BY key""",
                          glob)
        if cursor.rowcount == 0:
            irc.reply("No values matching %r found." % search)
            return
        keys = [repr(tup[0]) for tup in cursor.fetchall()]
        s = "Value search for %r (%s found): %s" % \
            (search, len(keys), utils.commaAndify(keys))
        irc.reply(s)

    def delete(self, irc, msg, args):
        """<factoid key>

        Deletes the factoid with the given key.
        """
        # Must be registered to use this
        try:
            ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        key = privmsgs.getArgs(args, required=1)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT key, locked_at FROM factoids
                          WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            irc.error("No such factoid: %r" % key)
            return
        (_, locked_at) = cursor.fetchone() 
        if locked_at is not None:
            irc.error("Factoid is locked, cannot remove.")
            return
        cursor.execute("""DELETE FROM factoids WHERE key = %s""", key)
        db.commit()
        irc.replySuccess()

    def randomfactoid(self, irc, msg, args):
        """<takes no arguments>

        Displays a random factoid (along with its key) from the database.
        """
        cursor = self.db.cursor()
        cursor.execute("""SELECT fact, key FROM factoids 
                          ORDER BY random() LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error(msg, 'No factoids in the database.')
            return
        (fact, key) = cursor.fetchone()
        irc.reply(msg, "Random factoid: %r is %r" % (key, fact))

Class = MoobotFactoids

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
