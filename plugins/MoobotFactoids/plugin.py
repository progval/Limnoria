###
# Copyright (c) 2003-2005, Daniel DiPaolo
# Copyright (c) 2010-2021, Valentin Lorentz
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

import os
import sys
import time
import string

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
import supybot.shlex as shlex
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('MoobotFactoids')

class OptionList(object):
    separators = '|()'
    def _insideParens(self, lexer):
        ret = []
        while True:
            token = lexer.get_token()
            if not token:
                return '(%s' % ''.join(ret) #)
            elif token == ')':
                if '|' in ret:
                    L = list(map(''.join,
                            utils.iter.split('|'.__eq__, ret,
                                             yieldEmpty=True)))
                    return utils.iter.choice(L)
                else:
                    return '(%s)' % ''.join(ret)
            elif token == '(':
                ret.append(self._insideParens(lexer))
            elif token == '|':
                ret.append(token)
            else:
                ret.append(token)

    def tokenize(self, s):
        lexer = shlex.shlex(minisix.io.StringIO(s))
        lexer.commenters = ''
        lexer.quotes = ''
        lexer.whitespace = ''
        lexer.separators += self.separators
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

class SqliteMoobotDB(object):
    def __init__(self, filename):
        self.filename = filename
        self.dbs = ircutils.IrcDict()

    def close(self):
        for db in self.dbs.values():
            db.close()
        self.dbs.clear()

    def _getDb(self, channel):
        import sqlite3

        if channel in self.dbs:
            return self.dbs[channel]
        filename = plugins.makeChannelFilename(self.filename, channel)
        
        if os.path.exists(filename):
            db = sqlite3.connect(filename, check_same_thread=False)
            if minisix.PY2:
                db.text_factory = str
            self.dbs[channel] = db
            return db
        db = sqlite3.connect(filename, check_same_thread=False)
        if minisix.PY2:
            db.text_factory = str
        self.dbs[channel] = db
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
                          WHERE key LIKE ?""", (key,))
        results = cursor.fetchall()
        if len(results) == 0:
            return None
        else:
            return results[0]

    def getFactinfo(self, channel, key):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT created_by, created_at,
                                 modified_by, modified_at,
                                 last_requested_by, last_requested_at,
                                 requested_count, locked_by, locked_at
                          FROM factoids
                          WHERE key LIKE ?""", (key,))
        results = cursor.fetchall()
        if len(results) == 0:
            return None
        else:
            return results[0]

    def randomFactoid(self, channel):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT fact, key FROM factoids
                          ORDER BY random() LIMIT 1""")
        results = cursor.fetchall()
        if len(results) == 0:
            return None
        else:
            return results[0]

    def addFactoid(self, channel, key, value, creator_id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO factoids VALUES
                          (?, ?, ?, NULL, NULL, NULL, NULL,
                           NULL, NULL, ?, 0)""",
                           (key, creator_id, int(time.time()), value))
        db.commit()

    def updateFactoid(self, channel, key, newvalue, modifier_id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE factoids
                          SET fact=?, modified_by=?,
                          modified_at=? WHERE key LIKE ?""",
                          (newvalue, modifier_id, int(time.time()), key))
        db.commit()

    def updateRequest(self, channel, key, hostmask):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE factoids SET
                          last_requested_by = ?,
                          last_requested_at = ?,
                          requested_count = requested_count + 1
                          WHERE key = ?""",
                          (hostmask, int(time.time()), key))
        db.commit()

    def removeFactoid(self, channel, key):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""DELETE FROM factoids WHERE key LIKE ?""",
                          (key,))
        db.commit()

    def locked(self, channel, key):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute ("""SELECT locked_by FROM factoids
                           WHERE key LIKE ?""", (key,))
        if cursor.fetchone()[0] is None:
            return False
        else:
            return True

    def lock(self, channel, key, locker_id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE factoids
                          SET locked_by=?, locked_at=?
                          WHERE key LIKE ?""",
                          (locker_id, int(time.time()), key))
        db.commit()

    def unlock(self, channel, key):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE factoids
                          SET locked_by=?, locked_at=?
                          WHERE key LIKE ?""", (None, None, key))
        db.commit()

    def mostAuthored(self, channel, limit):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT created_by, count(key) FROM factoids
                          GROUP BY created_by
                          ORDER BY count(key) DESC LIMIT ?""", (limit,))
        return cursor.fetchall()

    def mostRecent(self, channel, limit):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM factoids
                          ORDER BY created_at DESC LIMIT ?""", (limit,))
        return cursor.fetchall()

    def mostPopular(self, channel, limit):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT key, requested_count FROM factoids
                          WHERE requested_count > 0
                          ORDER BY requested_count DESC LIMIT ?""", (limit,))
        results = cursor.fetchall()
        return results

    def getKeysByAuthor(self, channel, authorId):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM factoids WHERE created_by=?
                          ORDER BY key""", (authorId,))
        results = cursor.fetchall()
        return results

    def getKeysByGlob(self, channel, glob):
        db = self._getDb(channel)
        cursor = db.cursor()
        glob = '%%%s%%' % glob
        cursor.execute("""SELECT key FROM factoids WHERE key LIKE ?
                          ORDER BY key""", (glob,))
        results = cursor.fetchall()
        return results

    def getKeysByValueGlob(self, channel, glob):
        db = self._getDb(channel)
        cursor = db.cursor()
        glob = '%%%s%%' % glob
        cursor.execute("""SELECT key FROM factoids WHERE fact LIKE ?
                          ORDER BY key""", (glob,))
        results = cursor.fetchall()
        return results

MoobotDB = plugins.DB('MoobotFactoids', {'sqlite3': SqliteMoobotDB})

class MoobotFactoids(callbacks.Plugin):
    """
    An alternative to the Factoids plugin, this plugin keeps factoids in
    your bot.

    To add factoid say
    ``@something is something`` And when you call ``@something`` the bot says
    ``something is something``.

    If you want the factoid to be in different format say (for example):
    ``@Hi is <reply> Hello`` And when you call ``@hi`` the bot says ``Hello.``

    If you want the bot to use /mes with Factoids, that is possible too.
    ``@test is <action> tests.`` and everytime when someone calls for
    ``test`` the bot answers ``* bot tests.``

    If you want the factoid to have random answers say (for example):
    ``@fruit is <reply> (orange|apple|banana)``. So when ``@fruit`` is called
    the bot will reply with one of the listed fruits (random): ``orange``.
    
    If you want to replace the value of the factoid, for example:
    ``@no Hi is <reply> Hey`` when you call ``@hi`` the bot says ``Hey``.

    If you want to append to the current value of a factoid say:
    ``@Hi is also Hello``, so that when you call ``@hi`` the
    bot says ``Hey, or Hello.`` 
    """
    callBefore = ['Dunno']
    def __init__(self, irc):
        self.db = MoobotDB()
        self.__parent = super(MoobotFactoids, self)
        self.__parent.__init__(irc)

    def die(self):
        self.__parent.die()
        self.db.close()

    def reset(self):
        self.db.close()

    _replyTag = '<reply>'
    _actionTag = '<action>'
    def _parseFactoid(self, irc, msg, fact):
        type = 'define'  # Default is to just spit the factoid back as a
                         # definition of what the key is (i.e., "foo is bar")
        newfact = pickOptions(fact)
        if newfact.startswith(self._replyTag):
            newfact = newfact[len(self._replyTag):]
            type = 'reply'
        elif newfact.startswith(self._actionTag):
            newfact = newfact[len(self._actionTag):]
            type = 'action'
        newfact = newfact.strip()
        newfact = ircutils.standardSubstitute(irc, msg, newfact)
        return (type, newfact)

    def invalidCommand(self, irc, msg, tokens):
        if '=~' in tokens:
            self.changeFactoid(irc, msg, tokens)
        elif tokens and tokens[0] in ('no', 'no,'):
            self.replaceFactoid(irc, msg, tokens)
        elif ['is', 'also'] in utils.seq.window(tokens, 2):
            self.augmentFactoid(irc, msg, tokens)
        else:
            key = ' '.join(tokens)
            key = self._sanitizeKey(key)
            channel = plugins.getChannel(msg.channel or msg.args[0])
            fact = self.db.getFactoid(channel, key)
            if fact:
                self.db.updateRequest(channel, key, msg.prefix)
                # getFactoid returns "all results", so we need to extract the
                # first one.
                fact = fact[0]
                # Update the requested count/requested by for this key
                hostmask = msg.prefix
                # Now actually get the factoid and respond accordingly
                (type, text) = self._parseFactoid(irc, msg, fact)
                if type == 'action':
                    irc.reply(text, action=True)
                elif type == 'reply':
                    irc.reply(text, prefixNick=False)
                elif type == 'define':
                    irc.reply(format(_('%s is %s'), key, text),
                                     prefixNick=False)
                else:
                    assert False, 'Spurious type from _parseFactoid'
            else:
                if 'is' in tokens or '_is_' in tokens:
                    self.addFactoid(irc, msg, tokens)

    def _getUserId(self, irc, prefix):
        try:
            return ircdb.users.getUserId(prefix)
        except KeyError:
            irc.errorNotRegistered(Raise=True)

    def _sanitizeKey(self, key):
        return key.rstrip('!? ')

    def _checkNotLocked(self, irc, channel, key):
        if self.db.locked(channel, key):
            irc.error(format(_('Factoid %q is locked.'), key), Raise=True)

    def _getFactoid(self, irc, channel, key):
        fact = self.db.getFactoid(channel, key)
        if fact is not None:
            return fact
        else:
            irc.error(format(_('Factoid %q not found.'), key), Raise=True)

    def _getKeyAndFactoid(self, tokens):
        if '_is_' in tokens:
            p = '_is_'.__eq__
        elif 'is' in tokens:
            p = 'is'.__eq__
        else:
            self.log.debug('Invalid tokens for {add,replace}Factoid: %s.',
                           tokens)
            s = _('Missing an \'is\' or \'_is_\'.')
            raise ValueError(s)
        (key, newfact) = list(map(' '.join, utils.iter.split(p, tokens, maxsplit=1)))
        key = self._sanitizeKey(key)
        return (key, newfact)

    def addFactoid(self, irc, msg, tokens):
        # First, check and see if the entire message matches a factoid key
        channel = plugins.getChannel(msg.channel or msg.args[0])
        id = self._getUserId(irc, msg.prefix)
        try:
            (key, fact) = self._getKeyAndFactoid(tokens)
        except ValueError as e:
            irc.error(str(e), Raise=True)
        # Check and make sure it's not in the DB already
        if self.db.getFactoid(channel, key):
            irc.error(format(_('Factoid %q already exists.'), key), Raise=True)
        self.db.addFactoid(channel, key, fact, id)
        irc.replySuccess()

    def changeFactoid(self, irc, msg, tokens):
        id = self._getUserId(irc, msg.prefix)
        (key, regexp) = list(map(' '.join,
                            utils.iter.split('=~'.__eq__, tokens, maxsplit=1)))
        channel = plugins.getChannel(msg.channel or msg.args[0])
        # Check and make sure it's in the DB
        fact = self._getFactoid(irc, channel, key)
        self._checkNotLocked(irc, channel, key)
        # It's fair game if we get to here
        try:
            r = utils.str.perlReToReplacer(regexp)
        except ValueError as e:
            irc.errorInvalid('regexp', regexp, Raise=True)
        fact = fact[0]
        new_fact = r(fact)
        self.db.updateFactoid(channel, key, new_fact, id)
        irc.replySuccess()

    def augmentFactoid(self, irc, msg, tokens):
        # Must be registered!
        id = self._getUserId(irc, msg.prefix)
        pairs = list(utils.seq.window(tokens, 2))
        isAlso = pairs.index(['is', 'also'])
        key = ' '.join(tokens[:isAlso])
        new_text = ' '.join(tokens[isAlso+2:])
        channel = plugins.getChannel(msg.channel or msg.args[0])
        fact = self._getFactoid(irc, channel, key)
        self._checkNotLocked(irc, channel, key)
        # It's fair game if we get to here
        fact = fact[0]
        new_fact = format(_('%s, or %s'), fact, new_text)
        self.db.updateFactoid(channel, key, new_fact, id)
        irc.replySuccess()

    def replaceFactoid(self, irc, msg, tokens):
        # Must be registered!
        channel = plugins.getChannel(msg.channel or msg.args[0])
        id = self._getUserId(irc, msg.prefix)
        del tokens[0] # remove the "no,"
        try:
            (key, fact) = self._getKeyAndFactoid(tokens)
        except ValueError as e:
            irc.error(str(e), Raise=True)
        _ = self._getFactoid(irc, channel, key)
        self._checkNotLocked(irc, channel, key)
        self.db.removeFactoid(channel, key)
        self.db.addFactoid(channel, key, fact, id)
        irc.replySuccess()

    @internationalizeDocstring
    def literal(self, irc, msg, args, channel, key):
        """[<channel>] <factoid key>

        Returns the literal factoid for the given factoid key.  No parsing of
        the factoid value is done as it is with normal retrieval.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        fact = self._getFactoid(irc, channel, key)
        fact = fact[0]
        irc.reply(fact)
    literal = wrap(literal, ['channeldb', 'text'])

    @internationalizeDocstring
    def factinfo(self, irc, msg, args, channel, key):
        """[<channel>] <factoid key>

        Returns the various bits of info on the factoid for the given key.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        # Start building the response string
        s = key + ': '
        # Next, get all the info and build the response piece by piece
        info = self.db.getFactinfo(channel, key)
        if not info:
            irc.error(format(_('No such factoid: %q'), key))
            return
        (created_by, created_at, modified_by, modified_at, last_requested_by,
         last_requested_at, requested_count, locked_by, locked_at) = info
        # First, creation info.
        # Map the integer created_by to the username
        created_by = plugins.getUserName(created_by)
        created_at = time.strftime(conf.supybot.reply.format.time(),
                                   time.localtime(int(created_at)))
        s += format(_('Created by %s on %s.'), created_by, created_at)
        # Next, modification info, if any.
        if modified_by is not None:
            modified_by = plugins.getUserName(modified_by)
            modified_at = time.strftime(conf.supybot.reply.format.time(),
                                   time.localtime(int(modified_at)))
            s += format(_(' Last modified by %s on %s.'), modified_by,
                        modified_at)
        # Next, last requested info, if any
        if last_requested_by is not None:
            last_by = last_requested_by  # not an int user id
            last_at = time.strftime(conf.supybot.reply.format.time(),
                                    time.localtime(int(last_requested_at)))
            req_count = requested_count
            s += format(_(' Last requested by %s on %s, requested %n.'),
                        last_by, last_at, (requested_count, 'time'))
        # Last, locked info
        if locked_at is not None:
            lock_at = time.strftime(conf.supybot.reply.format.time(),
                                     time.localtime(int(locked_at)))
            lock_by = plugins.getUserName(locked_by)
            s += format(_(' Locked by %s on %s.'), lock_by, lock_at)
        irc.reply(s)
    factinfo = wrap(factinfo, ['channeldb', 'text'])

    def _lock(self, irc, msg, channel, user, key, locking=True):
        #self.log.debug('in _lock')
        #self.log.debug('id: %s', id)
        id = user.id
        info = self.db.getFactinfo(channel, key)
        if not info:
            irc.error(format(_('No such factoid: %q'), key))
            return
        (created_by, a, a, a, a, a, a, locked_by, a) = info
        # Don't perform redundant operations
        if locking and locked_by is not None:
               irc.error(format(_('Factoid %q is already locked.'), key))
               return
        if not locking and locked_by is None:
               irc.error(format(_('Factoid %q is not locked.'), key))
               return
        # Can only lock/unlock own factoids unless you're an admin
        #self.log.debug('admin?: %s', ircdb.checkCapability(id, 'admin'))
        #self.log.debug('created_by: %s', created_by)
        if not (ircdb.checkCapability(id, 'admin') or created_by == id):
            if locking:
                s = 'lock'
            else:
                s = 'unlock'
            irc.error(format(_('Cannot %s someone else\'s factoid unless you '
                             'are an admin.'), s))
            return
        # Okay, we're done, ready to lock/unlock
        if locking:
           self.db.lock(channel, key, id)
        else:
           self.db.unlock(channel, key)
        irc.replySuccess()

    @internationalizeDocstring
    def lock(self, irc, msg, args, channel, user, key):
        """[<channel>] <factoid key>

        Locks the factoid with the given factoid key.  Requires that the user
        be registered and have created the factoid originally.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        self._lock(irc, msg, channel, user, key, True)
    lock = wrap(lock, ['channeldb', 'user', 'text'])

    @internationalizeDocstring
    def unlock(self, irc, msg, args, channel, user, key):
        """[<channel>] <factoid key>

        Unlocks the factoid with the given factoid key.  Requires that the
        user be registered and have locked the factoid.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._lock(irc, msg, channel, user, key, False)
    unlock = wrap(unlock, ['channeldb', 'user', 'text'])

    @internationalizeDocstring
    def most(self, irc, msg, args, channel, method):
        """[<channel>] {popular|authored|recent}

        Lists the most {popular|authored|recent} factoids.  "popular" lists the
        most frequently requested factoids.  "authored" lists the author with
        the most factoids.  "recent" lists the most recently created factoids.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        method = method.capitalize()
        method = getattr(self, '_most%s' % method, None)
        if method is None:
            raise callbacks.ArgumentError
        limit = self.registryValue('mostCount', channel, irc.network)
        method(irc, channel, limit)
    most = wrap(most, ['channeldb',
                       ('literal', ('popular', 'authored', 'recent'))])

    def _mostAuthored(self, irc, channel, limit):
        results = self.db.mostAuthored(channel, limit)
        L = ['%s (%s)' % (plugins.getUserName(t[0]), int(t[1]))
             for t in results]
        if L:
            author = _('author')
            if len(L) != 1:
                author = _('authors')
            irc.reply(format(_('Most prolific %s: %L'), author, L))
        else:
            irc.error(_('There are no factoids in my database.'))

    def _mostRecent(self, irc, channel, limit):
        results = self.db.mostRecent(channel, limit)
        L = [format('%q', t[0]) for t in results]
        if L:
            if len(L) < 2:
                latest = _('latest factoid')
            else:
                latest = _('latest factoids')
            irc.reply(format(_('%i %s: %L'), len(L), latest, L))
        else:
            irc.error(_('There are no factoids in my database.'))

    def _mostPopular(self, irc, channel, limit):
        results = self.db.mostPopular(channel, limit)
        L = [format('%q (%s)', t[0], t[1]) for t in results]
        if L:
            if len(L) < 2:
                requested = _('requested factoid')
            else:
                requested = _('requested factoids')
            irc.reply(format(_('Top %i %s: %L'), len(L), requested, L))
        else:
            irc.error(_('No factoids have been requested from my database.'))

    @internationalizeDocstring
    def listauth(self, irc, msg, args, channel, author):
        """[<channel>] <author name>

        Lists the keys of the factoids with the given author.  Note that if an
        author has an integer name, you'll have to use that author's id to use
        this function (so don't use integer usernames!).  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        try:
            id = ircdb.users.getUserId(author)
        except KeyError:
            irc.errorNoUser(name=author, Raise=True)
        results = self.db.getKeysByAuthor(channel, id)
        if not results:
            irc.reply(format(_('No factoids by %q found.'), author))
            return
        keys = [format('%q', t[0]) for t in results]
        s = format(_('Author search for %q (%i found): %L'),
                   author, len(keys), keys)
        irc.reply(s)
    listauth = wrap(listauth, ['channeldb', 'something'])

    @internationalizeDocstring
    def listkeys(self, irc, msg, args, channel, search):
        """[<channel>] <text>

        Lists the keys of the factoids whose key contains the provided text.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        results = self.db.getKeysByGlob(channel, search)
        if not results:
            irc.reply(format(_('No keys matching %q found.'), search))
        elif len(results) == 1 and \
             self.registryValue('showFactoidIfOnlyOneMatch',
                                channel, irc.network):
            key = results[0][0]
            self.invalidCommand(irc, msg, [key])
        else:
            keys = [format('%q', tup[0]) for tup in results]
            s = format(_('Key search for %q (%i found): %L'),
                       search, len(keys), keys)
            irc.reply(s)
    listkeys = wrap(listkeys, ['channeldb', 'text'])

    @internationalizeDocstring
    def listvalues(self, irc, msg, args, channel, search):
        """[<channel>] <text>

        Lists the keys of the factoids whose value contains the provided text.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        results = self.db.getKeysByValueGlob(channel, search)
        if not results:
            irc.reply(format(_('No values matching %q found.'), search))
            return
        keys = [format('%q', tup[0]) for tup in results]
        s = format(_('Value search for %q (%i found): %L'),
                   search, len(keys), keys)
        irc.reply(s)
    listvalues = wrap(listvalues, ['channeldb', 'text'])

    @internationalizeDocstring
    def remove(self, irc, msg, args, channel, _, key):
        """[<channel>] <factoid key>

        Deletes the factoid with the given key.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        _ = self._getFactoid(irc, channel, key)
        self._checkNotLocked(irc, channel, key)
        self.db.removeFactoid(channel, key)
        irc.replySuccess()
    remove = wrap(remove, ['channeldb', 'user', 'text'])

    @internationalizeDocstring
    def random(self, irc, msg, args, channel):
        """[<channel>]

        Displays a random factoid (along with its key) from the database.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        results = self.db.randomFactoid(channel)
        if not results:
            irc.error(_('No factoids in the database.'))
            return
        (fact, key) = results
        irc.reply(format('Random factoid: %q is %q', key, fact))
    random = wrap(random, ['channeldb'])
MoobotFactoids = internationalizeDocstring(MoobotFactoids)

Class = MoobotFactoids


# vim:set shiftwidth=4 softtabstop=8 expandtab textwidth=78:
