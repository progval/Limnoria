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
Handles "factoids," little tidbits of information held in a database and
available on demand via several commands.
"""

__revision__ = "$Id$"

import plugins

import time
import getopt
import string
import os.path
from itertools import imap

import conf
import utils
import ircdb
import ircutils
import privmsgs
import callbacks
import configurable

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

class Factoids(plugins.ChannelDBHandler,
               callbacks.Privmsg,
               configurable.Mixin):
    configurables = configurable.Dictionary(
        [('learn-separator', configurable.NoSpacesStrType, 'as',
          """Determines what separator must be used in the learn command.
          Defaults to 'as' -- learn <key> as <value>.  Users might feel more
          comfortable with 'is' or something else, so it's configurable."""),
         ('show-factoid-if-only-one-match', configurable.BoolType, True,
          """Determines whether the bot will reply with the single matching
          factoid if only one factoid matches when using the search command.
          """),]
    )
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        configurable.Mixin.__init__(self)
        plugins.ChannelDBHandler.__init__(self)

    def die(self):
        callbacks.Privmsg.die(self)
        configurable.Mixin.die(self)
        plugins.ChannelDBHandler.die(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(filename)
        db = sqlite.connect(filename)
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE keys (
                          id INTEGER PRIMARY KEY,
                          key TEXT UNIQUE ON CONFLICT IGNORE,
                          locked BOOLEAN
                          )""")
        cursor.execute("""CREATE TABLE factoids (
                          id INTEGER PRIMARY KEY,
                          key_id INTEGER,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          fact TEXT
                          )""")
        cursor.execute("""CREATE TRIGGER remove_factoids
                          BEFORE DELETE ON keys
                          BEGIN
                            DELETE FROM factoids WHERE key_id = old.id;
                          END
                       """)
        db.commit()
        return db

    def learn(self, irc, msg, args):
        """[<channel>] <key> as <value>

        Associates <key> with <value>.  <channel> is only necessary if the
        message isn't sent on the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        try:
            separator = self.configurables.get('learn-separator', channel)
            i = args.index(separator)
        except ValueError:
            raise callbacks.ArgumentError
        args.pop(i)
        key = ' '.join(args[:i])
        factoid = ' '.join(args[i:])
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id, locked FROM keys WHERE key LIKE %s", key)
        if cursor.rowcount == 0:
            cursor.execute("""INSERT INTO keys VALUES (NULL, %s, 0)""", key)
            db.commit()
            cursor.execute("SELECT id, locked FROM keys WHERE key LIKE %s",key)
        (id, locked) = imap(int, cursor.fetchone())
        capability = ircdb.makeChannelCapability(channel, 'factoids')
        if not locked:
            if not ircdb.checkCapability(msg.prefix, capability):
                irc.error(msg, conf.replyNoCapability % capability)
                return
            if ircdb.users.hasUser(msg.prefix):
                name = ircdb.users.getUser(msg.prefix).name
            else:
                name = msg.nick
            cursor.execute("""INSERT INTO factoids VALUES
                              (NULL, %s, %s, %s, %s)""",
                           id, name, int(time.time()), factoid)
            db.commit()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'That factoid is locked.')

    def whatis(self, irc, msg, args):
        """[<channel>] <key> [<number>]

        Looks up the value of <key> in the factoid database.  If given a
        number, will return only that exact factoid.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        if len(args) > 1 and args[-1].isdigit():
            number = args.pop()
        else:
            number = ''
        key = privmsgs.getArgs(args)
        if number:
            try:
                number = int(number)
            except ValueError:
                irc.error(msg, '%s is not a valid number.' % number)
                return
        else:
            number = 0
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT factoids.fact FROM factoids, keys WHERE
                          keys.key LIKE %s AND factoids.key_id=keys.id
                          ORDER BY factoids.id
                          LIMIT 20""", key)
        if cursor.rowcount == 0:
            irc.error(msg, 'No factoid matches that key.')
        else:
            if not number:
                factoids = []
                counter = 1
                for result in cursor.fetchall():
                    factoids.append('(#%s) %s' % (counter, result[0]))
                    counter += 1
                irc.reply(msg,'%r could be %s' % (key, ', or '.join(factoids)))
            else:
                try:
                    irc.reply(msg, cursor.fetchall()[number-1][0])
                except IndexError:
                    irc.error(msg, 'That\'s not a valid number for this key.')
                    return

    def lock(self, irc, msg, args):
        """[<channel>] <key>

        Locks the factoid(s) associated with <key> so that they cannot be
        removed or added to.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args)
        db = self.getDb(channel)
        capability = ircdb.makeChannelCapability(channel, 'factoids')
        if ircdb.checkCapability(msg.prefix, capability):
            cursor = db.cursor()
            cursor.execute("UPDATE keys SET locked=1 WHERE key LIKE %s", key)
            db.commit()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def unlock(self, irc, msg, args):
        """[<channel>] <key>

        Unlocks the factoid(s) associated with <key> so that they can be
        removed or added to.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args)
        db = self.getDb(channel)
        capability = ircdb.makeChannelCapability(channel, 'factoids')
        if ircdb.checkCapability(msg.prefix, capability):
            cursor = db.cursor()
            cursor.execute("UPDATE keys SET locked=0 WHERE key LIKE %s", key)
            db.commit()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def forget(self, irc, msg, args):
        """[<channel>] <key> [<number>|*]

        Removes the factoid <key> from the factoids database.  If there are
        more than one factoid with such a key, a number is necessary to
        determine which one should be removed.  A * can be used to remove all
        factoids associated with a key.  <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        if args[-1].isdigit():
            number = int(args.pop())
            number -= 1
            if number < 0:
                irc.error(msg, 'Negative numbers aren\'t valid.')
                return
        elif args[-1] == '*':
            del args[-1]
            number = True
        else:
            number = None
        key = privmsgs.getArgs(args)
        db = self.getDb(channel)
        capability = ircdb.makeChannelCapability(channel, 'factoids')
        if ircdb.checkCapability(msg.prefix, capability):
            cursor = db.cursor()
            cursor.execute("""SELECT keys.id, factoids.id
                              FROM keys, factoids
                              WHERE key LIKE %s AND
                                    factoids.key_id=keys.id""", key)
            if cursor.rowcount == 0:
                irc.error(msg, 'There is no such factoid.')
            elif cursor.rowcount == 1 or number is True:
                (id, _) = cursor.fetchone()
                cursor.execute("""DELETE FROM factoids WHERE key_id=%s""", id)
                cursor.execute("""DELETE FROM keys WHERE key LIKE %s""", key)
                db.commit()
                irc.reply(msg, conf.replySuccess)
            else:
                if number is not None:
                    results = cursor.fetchall()
                    try:
                        (_, id) = results[number]
                    except IndexError:
                        irc.error(msg, 'Invalid factoid number.')
                        return
                    cursor.execute("DELETE FROM factoids WHERE id=%s", id)
                    db.commit()
                    irc.reply(msg, conf.replySuccess)
                else:
                    irc.error(msg, '%s factoids have that key.  ' \
                                   'Please specify which one to remove, ' \
                                   'or use * to designate all of them.' % \
                                   cursor.rowcount)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def random(self, irc, msg, args):
        """[<channel>]

        Returns a random factoid from the database for <channel>.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT fact, key_id FROM factoids
                          ORDER BY random()
                          LIMIT 3""")
        if cursor.rowcount != 0:
            L = []
            for (factoid, id) in cursor.fetchall():
                cursor.execute("""SELECT key FROM keys WHERE id=%s""", id)
                (key,) = cursor.fetchone()
                L.append('"%s": %s' % (ircutils.bold(key), factoid))
            irc.reply(msg, '; '.join(L))
        else:
            irc.error(msg, 'I couldn\'t find a factoid.')

    def info(self, irc, msg, args):
        """[<channel>] <key>

        Gives information about the factoid(s) associated with <key>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id, locked FROM keys WHERE key LIKE %s", key)
        if cursor.rowcount == 0:
            irc.error(msg, 'No factoid matches that key.')
            return
        (id, locked) = imap(int, cursor.fetchone())
        cursor.execute("""SELECT  added_by, added_at FROM factoids
                          WHERE key_id=%s
                          ORDER BY id""", id)
        factoids = cursor.fetchall()
        L = []
        counter = 0
        for (added_by, added_at) in factoids:
            counter += 1
            added_at = time.strftime(conf.humanTimestampFormat,
                                     time.localtime(int(added_at)))
            L.append('#%s was added by %s at %s' % (counter,added_by,added_at))
        factoids = '; '.join(L)
        s = 'Key %r is %s and has %s associated with it: %s' % \
            (key, locked and 'locked' or 'not locked',
             utils.nItems('factoid', counter), factoids)
        irc.reply(msg, s)

    def change(self, irc, msg, args):
        """[<channel>] <key> <number> <regexp>

        Changes the factoid #<number> associated with <key> according to
        <regexp>.
        """
        channel = privmsgs.getChannel(msg, args)
        (key, number, regexp) = privmsgs.getArgs(args, required=3)
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error(msg, 'Invalid regexp: %s' % e)
            return
        try:
            number = int(number)
            if number <= 0:
                raise ValueError
        except ValueError:
            irc.error(msg, 'Invalid key id.')
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT factoids.id, factoids.fact
                          FROM keys, factoids
                          WHERE keys.key LIKE %s AND
                                keys.id=factoids.key_id""", key)
        if cursor.rowcount == 0:
            irc.error(msg, 'I couldn\'t find any key %r' % key)
            return
        elif cursor.rowcount < number:
            irc.error(msg, 'That\'s not a valid key id.')
            return
        (id, fact) = cursor.fetchall()[number-1]
        newfact = replacer(fact)
        cursor.execute("UPDATE factoids SET fact=%s WHERE id=%s", newfact, id)
        db.commit()
        irc.reply(msg, conf.replySuccess)

    _sqlTrans = string.maketrans('*?', '%_')
    def search(self, irc, msg, args):
        """[<channel>] [--{regexp}=<value>] [<glob>]

        Searches the keyspace for keys matching <glob>.  If --regexp is given,
        it associated value is taken as a regexp and matched against the keys.
        """
        channel = privmsgs.getChannel(msg, args)
        (optlist, rest) = getopt.getopt(args, '', ['regexp='])
        if not optlist and not rest:
            raise callbacks.ArgumentError
        criteria = []
        formats = []
        predicateName = 'p'
        db = self.getDb(channel)
        for (option, arg) in optlist:
            if option == '--regexp':
                criteria.append('%s(key)' % predicateName)
                try:
                    r = utils.perlReToPythonRe(arg)
                except ValueError, e:
                    irc.error(msg, 'Invalid regexp: %s' % e)
                    return
                def p(s, r=r):
                    return int(bool(r.search(s)))
                db.create_function(predicateName, 1, p)
                predicateName += 'p'
        for glob in rest:
            if '*' not in glob and '?' not in glob:
                glob = '*%s*' % glob
            criteria.append('key LIKE %s')
            formats.append(glob.translate(self._sqlTrans))
        cursor = db.cursor()
        sql = """SELECT key FROM keys WHERE %s""" % ' AND '.join(criteria)
        cursor.execute(sql, formats)
        if cursor.rowcount == 0:
            irc.reply(msg, 'No keys matched that query.')
        elif cursor.rowcount == 1 and \
             self.configurables.get('show-factoid-if-only-one-match',channel):
            self.whatis(irc, msg, [cursor.fetchone()[0]])
        elif cursor.rowcount > 100:
            irc.reply(msg, 'More than 100 keys matched that query; '
                           'please narrow your query.')
        else:
            keys = [repr(t[0]) for t in cursor.fetchall()]
            s = utils.commaAndify(keys)
            irc.reply(msg, s)

        
Class = Factoids


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
