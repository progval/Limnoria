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

import supybot

__revision__="$Id$"
__author__ = supybot.authors.strike

import supybot.plugins as plugins

import os
import sets
import time
import shlex
import string
import random
from itertools import imap
from cStringIO import StringIO

import supybot.registry as registry

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks

import supybot.Owner as Owner

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

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
                        L = map(''.join,
                                utils.itersplit('|'.__eq__, ret,
                                                yieldEmpty=True))
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
conf.registerChannelValue(conf.supybot.plugins.MoobotFactoids,
    'mostCount', registry.Integer(10, """Determines how many items are shown
    when the 'most' command is called."""))

class SqliteMoobotDB(object):
    def _getDb(self, channel):
        filename = plugins.makeChannelFilename(channel, 'MoobotFactoids.db')
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename)
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

    def getFactoid(self, channel, key):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT fact FROM factoids
                          WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            return None
        else:
            return cursor.fetchall()[0]

    def getFactinfo(self, channel, key):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT created_by, created_at,
                                 modified_by, modified_at,
                                 last_requested_by, last_requested_at,
                                 requested_count, locked_by, locked_at
                          FROM factoids
                          WHERE key LIKE %s""", key)
        if cursor.rowcount == 0:
            return None
        else:
            return cursor.fetchone()

    def randomFactoid(self, channel):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT fact, key FROM factoids
                          ORDER BY random() LIMIT 1""")
        if cursor.rowcount == 0:
            return None
        else:
            return cursor.fetchone()

    def addFactoid(self, channel, key, value, creator_id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO factoids VALUES
                          (%s, %s, %s, NULL, NULL, NULL, NULL,
                           NULL, NULL, %s, 0)""",
                           key, creator_id, int(time.time()), value)
        db.commit()

    def updateFactoid(self, channel, key, newvalue, modifier_id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE factoids
                          SET fact=%s, modified_by=%s,
                          modified_at=%s WHERE key LIKE %s""",
                          newvalue, modifier_id, int(time.time()), key)
        db.commit()

    def updateRequest(self, channel, key, hostmask):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE factoids SET
                          last_requested_by = %s,
                          last_requested_at = %s,
                          requested_count = requested_count + 1
                          WHERE key = %s""",
                          hostmask, int(time.time()), key)
        db.commit()

    def removeFactoid(self, channel, key):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""DELETE FROM factoids WHERE key LIKE %s""",
                          key)
        db.commit()

    def locked(self, channel, key):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute ("""SELECT locked_by FROM factoids
                           WHERE key LIKE %s""", key)
        if cursor.fetchone()[0] is None:
            return False
        else:
            return True

    def lock(self, channel, key, locker_id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE factoids
                          SET locked_by=%s, locked_at=%s
                          WHERE key LIKE %s""",
                          locker_id, int(time.time()), key) 
        db.commit()

    def unlock(self, channel, key):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE factoids
                          SET locked_by=%s, locked_at=%s
                          WHERE key LIKE %s""", None, None, key)
        db.commit()

    def mostAuthored(self, channel, limit):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT created_by, count(key) FROM factoids
                          GROUP BY created_by
                          ORDER BY count(key) DESC LIMIT %s""", limit)
        return cursor.fetchall() 

    def mostRecent(self, channel, limit):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM factoids
                          ORDER BY created_at DESC LIMIT %s""", limit)
        return cursor.fetchall()

    def mostPopular(self, channel, limit):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT key, requested_count FROM factoids
                          WHERE requested_count > 0
                          ORDER BY requested_count DESC LIMIT %s""", limit)
        if cursor.rowcount == 0:
            return None
        else:
            return cursor.fetchall()

    def getKeysByAuthor(self, channel, author_id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM factoids WHERE created_by=%s
                          ORDER BY key""", author_id)
        if cursor.rowcount == 0:
            return None
        else:
            return cursor.fetchall()

    def getKeysByGlob(self, channel, glob):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM factoids WHERE key LIKE %s
                          ORDER BY key""", glob)
        if cursor.rowcount == 0:
            return None
        else:
            return cursor.fetchall()

    def getKeysByValueGlob(self, channel, glob):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM factoids WHERE fact LIKE %s
                          ORDER BY key""", glob)
        if cursor.rowcount == 0:
            return None
        else:
            return cursor.fetchall()

def MoobotDB():
    return SqliteMoobotDB()

class MoobotFactoids(callbacks.PrivmsgCommandAndRegexp):
    priority = 98
    addressedRegexps = ['changeFactoid', 'augmentFactoid',
                        'replaceFactoid', 'addFactoid']
    def __init__(self):
        self.db = MoobotDB()
        callbacks.PrivmsgCommandAndRegexp.__init__(self)

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
        newfact = newfact.strip()
        newfact = plugins.standardSubstitute(irc, msg, newfact)
        return (type, newfact)

    def randomfactoid(self, irc, msg, args):
        """takes no arguments

        Displays a random factoid (along with its key) from the database.
        """
        channel = privmsgs.getChannel(msg, args)
        tup = self.db.randomFactoid(channel)
        if tup is None:
            irc.error('No factoids in the database.')
        else:
            irc.reply('"%s" is "%s"' % tup)

    def invalidCommand(self, irc, msg, tokens):
        key = ' '.join(tokens)
        key = key.rstrip('?!')
        channel = privmsgs.getChannel(msg, list(msg.args))
        # ignore ACTIONs
        if key.startswith('\x01'):
            return
        # Check the factoid db for an appropriate reply
        fact = self.db.getFactoid(channel, key)
        if not fact:
            return False
        else:
            # getFactoid returns "all results", so we need to extract the
            # first one
            fact = fact[0]
            # Update the requested count/requested by for this key
            hostmask = msg.prefix
            self.db.updateRequest(channel, key, hostmask)
            # Now actually get the factoid and respond accordingly
            (type, text) = self._parseFactoid(irc, msg, fact)
            if type == "action":
                irc.reply(text, action=True)
            elif type == "reply":
                irc.reply(text, prefixName=False)
            elif type == "define":
                irc.reply("%s is %s" % (key, text), prefixName=False)
            else:
                irc.error("Spurious type from _parseFactoid.")
            return True

    # XXX It looks like all these could be converted to use invalidCommand
    # instead, which would then also allow nested commands.  Strike may want
    # to consider that implementation method.
    def addFactoid(self, irc, msg, match):
        r"^(?!\x01)(.+?)\s+(?:is|_is_)\s+(.+)"
        # First, check and see if the entire message matches a factoid key
        channel = privmsgs.getChannel(msg, list(msg.args))
        key = match.group().rstrip('?! ')
        fact = self.db.getFactoid(channel, key)
        # If it exists, call invalidCommand to display it
        if fact:
            self.invalidCommand(irc, msg, callbacks.tokenize(match.group()))
            return
        # Okay, we are REALLY adding stuff
        # Must be registered!
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        key, newfact = match.groups()
        # These are okay, unless there's an _is_ in there, in which case
        # we split on the leftmost one.
        if '_is_' in match.group():
            key, newfact = imap(str.strip, match.group().split('_is_', 1))
        # Strip the key of punctuation and spaces
        key = key.rstrip('?! ')
        # Check and make sure it's not in the DB already
        fact = self.db.getFactoid(channel, key)
        if fact:
            irc.error('Factoid "%s" already exists.' % key)
            return
        # Otherwise,
        self.db.addFactoid(channel, key, newfact, id)
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
        channel = privmsgs.getChannel(msg, list(msg.args))
        # Check and make sure it's in the DB
        fact = self.db.getFactoid(channel, key)
        if not fact:
            irc.error('Factoid "%s" not found.' % key)
            return
        # No dice if it's locked, no matter who it is
        locked = self.db.locked(channel, key)
        if locked:
            irc.error('Factoid "%s" is locked.' % key)
            return
        # It's fair game if we get to here
        try:
            r = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error('Invalid regexp: "%s"' % regexp)
            return
        fact = fact[0]
        new_fact = r(fact)
        self.db.updateFactoid(channel, key, new_fact, id)
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
        channel = privmsgs.getChannel(msg, list(msg.args))
        fact = self.db.getFactoid(channel, key)
        # Check and make sure it's in the DB
        if not fact:
            irc.error('Factoid "%s" not found.' % key)
            return
        # No dice if it's locked, no matter who it is
        locked = self.db.locked(channel, key)
        if locked:
            irc.error('Factoid "%s" is locked.' % key)
            return
        # It's fair game if we get to here
        fact = fact[0]
        new_fact = "%s, or %s" % (fact, new_text)
        self.db.updateFactoid(channel, key, new_fact, id)
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
        # Check and make sure it's in the DB
        channel = privmsgs.getChannel(msg, list(msg.args))
        fact = self.db.getFactoid(channel, key)
        if not fact:
            irc.error('Factoid "%s" not found.' % key)
            return
        # No dice if it's locked, no matter who it is
        locked = self.db.locked(channel, key)
        if locked:
            irc.error('Factoid "%s" is locked.' % key)
            return
        # It's fair game if we get to here
        self.db.removeFactoid(channel, key)
        self.db.addFactoid(channel, key, new_fact, id)
        irc.replySuccess()

    def literal(self, irc, msg, args):
        """<factoid key>

        Returns the literal factoid for the given factoid key.  No parsing of
        the factoid value is done as it is with normal retrieval.
        """
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args, required=1)
        fact = self.db.getFactoid(channel, key)
        if not fact:
            irc.error('No such factoid: "%s"' % key)
        else:
            fact = fact[0]
            irc.reply(fact)

    def factinfo(self, irc, msg, args):
        """<factoid key>

        Returns the various bits of info on the factoid for the given key.
        """
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args, required=1)
        # Start building the response string
        s = key + ": "
        # Next, get all the info and build the response piece by piece
        info = self.db.getFactinfo(channel, key)
        if not info:
            irc.error('No such factoid: "%s"' % key)
            return
        (created_by, created_at, modified_by, modified_at, last_requested_by,
         last_requested_at, requested_count, locked_by, locked_at) = info
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

    def _lock(self, irc, msg, args, locking=True):
        self.log.debug('in _lock')
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        self.log.debug('id: %s' % id)
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args, required=1)
        info = self.db.getFactinfo(channel, key)
        if not info:
            irc.error('No such factoid: "%s"' % key)
            return
        (created_by, _, _, _, _, _, _, locked_by, _) = info
        # Don't perform redundant operations
        if locking and locked_by is not None:
               irc.error('Factoid "%s" is already locked.' % key)
               return
        if not locking and locked_by is None:
               irc.error('Factoid "%s" is not locked.' % key)
               return
        # Can only lock/unlock own factoids unless you're an admin
        self.log.debug('admin?: %s' % ircdb.checkCapability(id, 'admin'))
        self.log.debug('created_by: %s' % created_by)
        if not (ircdb.checkCapability(id, 'admin') or created_by == id):
            if locking:
                s = "lock"
            else:
                s = "unlock"
            irc.error("Cannot %s someone else's factoid unless you "
                           "are an admin." % s)
            return
        # Okay, we're done, ready to lock/unlock
        if locking:
           self.db.lock(channel, key, id)
        else:
           self.db.unlock(channel, key)
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

    class MostException(Exception):
        pass

    def most(self, irc, msg, args):
        """<popular|authored|recent>

        Lists the most <popular|authored|recent> factoids.  <popular> lists the
        most frequently requested factoids.  <authored> lists the author with
        the most factoids.  <recent> lists the most recently created factoids.
        """
        channel = privmsgs.getChannel(msg, args)
        arg = privmsgs.getArgs(args)
        arg = arg.capitalize()
        method = getattr(self, '_most%s' % arg, None)
        if method is None:
            raise callbacks.ArgumentError
        limit = self.registryValue('mostCount', channel)
        irc.reply(method(channel, limit))

    def _mostAuthored(self, channel, limit):
        results = self.db.mostAuthored(channel, limit)
        L = ['%s (%s)' % (ircdb.users.getUser(t[0]).name, int(t[1]))
             for t in results]
        return 'Most prolific %s: %s' % \
               (utils.pluralize('author', len(L)), utils.commaAndify(L))

    def _mostRecent(self, channel, limit):
        results = self.db.mostRecent(channel, limit)
        L = ['"%s"' % t[0] for t in results]
        return '%s: %s' % \
               (utils.nItems('factoid', len(L), between='latest'),
                utils.commaAndify(L))

    def _mostPopular(self, channel, limit):
        results = self.db.mostPopular(channel, limit)
        if not results:
            raise self.MostException, 'No factoids have been requested.'
        L = ['"%s" (%s)' % (t[0], t[1]) for t in results]
        return 'Top %s: %s' % \
               (utils.nItems('factoid', len(L), between='requested'),
                utils.commaAndify(L))

    def listauth(self, irc, msg, args):
        """<author name>

        Lists the keys of the factoids with the given author.  Note that if an
        author has an integer name, you'll have to use that author's id to use
        this function (so don't use integer usernames!).
        """
        channel = privmsgs.getChannel(msg, args)
        author = privmsgs.getArgs(args, required=1)
        try:
            id = ircdb.users.getUserId(author)
        except KeyError:
            irc.error("No such user: %r" % author)
            return
        results = self.db.getKeysByAuthor(channel, id)
        if not results:
            irc.reply('No factoids by "%s" found.' % author)
            return
        keys = ['"%s"' % tup[0] for tup in results]
        s = 'Author search for "%s" (%s found): %s' % \
            (author, len(keys), utils.commaAndify(keys))
        irc.reply(s)

    def listkeys(self, irc, msg, args):
        """<text>

        Lists the keys of the factoids whose key contains the provided text.
        """
        channel = privmsgs.getChannel(msg, args)
        search = privmsgs.getArgs(args, required=1)
        # Don't error if we aren't in a channel, private messages are okay
        channel = privmsgs.getChannel(msg, args, raiseError=False)
        glob = '%' + search + '%'
        results = self.db.getKeysByGlob(channel, glob)
        if not results:
            irc.reply('No keys matching "%s" found.' % search)
        elif len(results) == 1 and \
        self.registryValue('showFactoidIfOnlyOneMatch', channel):
            key = results[0][0]
            self.invalidCommand(irc, msg, [key])
        else:
            keys = ['"%s"' % tup[0] for tup in results]
            s = 'Key search for "%s" (%s found): %s' % \
                (search, len(keys), utils.commaAndify(keys))
            irc.reply(s)

    def listvalues(self, irc, msg, args):
        """<text>

        Lists the keys of the factoids whose value contains the provided text.
        """
        channel = privmsgs.getChannel(msg, args)
        search = privmsgs.getArgs(args, required=1)
        glob = '%' + search + '%'
        results = self.db.getKeysByValueGlob(channel, glob)
        if not results:
            irc.reply('No values matching "%s" found.' % search)
            return
        keys = ['"%s"' % tup[0] for tup in results]
        s = 'Value search for "%s" (%s found): %s' % \
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
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args, required=1)
        fact = self.db.getFactoid(channel, key)
        if not fact:
            irc.error('No such factoid: "%s"' % key)
            return
        locked = self.db.locked(channel, key)
        if locked:
            irc.error("Factoid is locked, cannot remove.")
            return
        self.db.removeFactoid(channel, key)
        irc.replySuccess()

    def randomfactoid(self, irc, msg, args):
        """takes no arguments

        Displays a random factoid (along with its key) from the database.
        """
        channel = privmsgs.getChannel(msg, args)
        results = self.db.randomFactoid(channel)
        if not results:
            irc.error('No factoids in the database.')
            return
        (fact, key) = results
        irc.reply('Random factoid: "%s" is "%s"' % (key, fact))

Class = MoobotFactoids

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
