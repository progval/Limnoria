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
Provides fun commands that require a database to operate.
"""

__revision__ = "$Id$"

import plugins

import re
import sets
import time
import getopt
import string
import os.path
from itertools import imap

import sqlite

import conf
import ircdb
import utils
import world
import ircmsgs
import ircutils
import privmsgs
import callbacks
import configurable

tableCreateStatements = {
    'larts': ("""CREATE TABLE larts (
                 id INTEGER PRIMARY KEY,
                 lart TEXT,
                 added_by TEXT
                 )""",),
    'praises': ("""CREATE TABLE praises (
                   id INTEGER PRIMARY KEY,
                   praise TEXT,
                   added_by TEXT
                   )""",),
    'insults': ("""CREATE TABLE insults (
                   id INTEGER PRIMARY KEY,
                   insult TEXT,
                   added_by TEXT
                   )""",),
    'excuses': ("""CREATE TABLE excuses (
                   id INTEGER PRIMARY KEY,
                   excuse TEXT,
                   added_by TEXT
                   )""",),
    }
    
class FunDB(callbacks.Privmsg, configurable.Mixin, plugins.ChannelDBHandler):
    """
    Contains the 'fun' commands that require a database.  Currently includes
    database-backed commands for crossword puzzle solving, anagram searching,
    larting, praising, excusing, and insulting.
    """
    configurables = configurable.Dictionary(
        [('show-ids', configurable.BoolType, False,
          """Determines whether the bot will show the id of an
          excuse/insult/praise/lart.""")]
    )
    _tables = sets.Set(['lart', 'insult', 'excuse', 'praise'])
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        configurable.Mixin.__init__(self)
        plugins.ChannelDBHandler.__init__(self)

    def die(self):
        callbacks.Privmsg.die(self)
        configurable.Mixin.die(self)
        plugins.ChannelDBHandler.die(self)

    def makeDb(self, dbfilename, replace=False):
        if os.path.exists(dbfilename):
            if replace:
                os.remove(dbfilename)
        db = sqlite.connect(dbfilename)
        cursor = db.cursor()
        for table in tableCreateStatements:
            try:
                cursor.execute("""SELECT * FROM %s LIMIT 1""" % table)
            except sqlite.DatabaseError: # The table doesn't exist.
                for sql in tableCreateStatements[table]:
                    cursor.execute(sql)
        db.commit()
        return db

    def add(self, irc, msg, args):
        """[<channel>] <lart|excuse|insult|praise> <text>

        Adds another record to the data referred to in the first argument.  For
        commands that will later respond with an ACTION (lart and praise), $who
        should be in the message to show who should be larted or praised.  I.e.
        'dbadd lart slices $who in half with a free AOL cd' would make the bot,
        when it used that lart against, say, jemfinch, to say '/me slices
        jemfinch in half with a free AOL cd'  <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (table, s) = privmsgs.getArgs(args, required=2)
        table = table.lower()
        try:
            name = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        if table == "lart" or table == "praise":
            if '$who' not in s:
                irc.error(msg, 'There must be a $who in the lart/praise '\
                               'somewhere.')
                return
        elif table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' %
                           (table, utils.commaAndify(self._tables)))
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        sql = """INSERT INTO %ss VALUES (NULL, %%s, %%s)""" % table
        cursor.execute(sql, s, name)
        db.commit()
        sql = """SELECT id FROM %ss WHERE %s=%%s""" % (table, table)
        cursor.execute(sql, s)
        id = cursor.fetchone()[0]
        response = '%s (%s #%s)' % (conf.replySuccess, table, id)
        irc.reply(msg, response)

    def remove(self, irc, msg, args):
        """[<channel>] <lart|excuse|insult|praise> <id>

        Removes the data, referred to in the first argument, with the id
        number <id> from the database.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (table, id) = privmsgs.getArgs(args, required=2)
        table = table.lower()
        try:
            ircdb.users.getUser(msg.prefix).name
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' %
                           (table, utils.commaAndify(self._tables)))
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        sql = """DELETE FROM %ss WHERE id=%%s""" % table
        cursor.execute(sql, id)
        db.commit()
        irc.reply(msg, conf.replySuccess)

    def change(self, irc, msg, args):
        """[<channel>] <lart|excuse|insult|praise> <id> <regexp>

        Changes the data, referred to in the first argument, with the id
        number <id> according to the regular expression <regexp>. <id> is the
        zero-based index into the db; <regexp> is a regular expression of the
        form s/regexp/replacement/flags.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (table, id, regexp) = privmsgs.getArgs(args, required=3)
        table = table.lower()
        try:
            name = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' %
                           (table, utils.commaAndify(self._tables)))
            return
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error(msg, 'The regexp wasn\'t valid: %s.' % e.args[0])
        except re.error, e:
            irc.error(msg, utils.exnToString(e))
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        sql = """SELECT %s FROM %ss WHERE id=%%s""" % (table, table)
        cursor.execute(sql, id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such %s.' % table)
        else:
            old_entry = cursor.fetchone()[0]
            new_entry = replacer(old_entry)
            sql = """UPDATE %ss SET %s=%%s, added_by=%%s WHERE id=%%s""" % \
                  (table, table)
            cursor.execute(sql, new_entry, name, id)
            db.commit()
            irc.reply(msg, conf.replySuccess)

    def num(self, irc, msg, args):
        """[<channel>] <lart|excuse|insult|praise>

        Returns the number of records, of the type specified, currently in
        the database.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        table = privmsgs.getArgs(args)
        table = table.lower()
        if table not in self._tables:
            irc.error(msg, '%r is not valid. Valid values include %s.' %
                           (table, utils.commaAndify(self._tables)))
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        sql = """SELECT count(*) FROM %ss""" % table
        cursor.execute(sql)
        total = int(cursor.fetchone()[0])
        irc.reply(msg, 'There %s currently %s in my database.' %
                  (utils.be(total), utils.nItems(total, table)))

    def get(self, irc, msg, args):
        """[<channel>] <lart|excuse|insult|praise> <id>

        Gets the record with id <id> from the table specified.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (table, id) = privmsgs.getArgs(args, required=2)
        table = table.lower()
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' %
                           (table, utils.commaAndify(self._tables)))
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        sql = """SELECT %s FROM %ss WHERE id=%%s""" % (table, table)
        cursor.execute(sql, id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such %s.' % table)
        else:
            reply = cursor.fetchone()[0]
            irc.reply(msg, reply)

    def info(self, irc, msg, args):
        """[<channel>] <lart|excuse|insult|praise> <id>

        Gets the info for the record with id <id> from the table specified.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (table, id) = privmsgs.getArgs(args, required=2)
        table = table.lower()
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' %
                           (table, utils.commaAndify(self._tables)))
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        sql = """SELECT added_by FROM %ss WHERE id=%%s""" % table
        cursor.execute(sql, id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such %s.' % table)
        else:
            add = cursor.fetchone()[0]
            reply = '%s #%s: Created by %s.' % (table, id, add)
            irc.reply(msg, reply)

    def _formatResponse(self, s, id, showids):
        if showids:
            return '%s (#%s)' % (s, id)
        else:
            return s
        
    def insult(self, irc, msg, args):
        """[<channel>] <nick>

        Insults <nick>.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args)
        if not nick:
            raise callbacks.ArgumentError
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, insult FROM insults
                          WHERE insult NOT NULL
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error(msg, 'There are currently no available insults.')
        else:
            (id, insult) = cursor.fetchone()
            nick = re.sub(r'\bme\b', msg.nick, nick)
            nick = re.sub(r'\bmy\b', '%s\'s' % msg.nick, nick)
            insult = insult.replace('$who', nick)
            showid = self.configurables.get('show-ids', channel)
            irc.reply(msg, self._formatResponse(insult, id, showid), to=nick)

    def excuse(self, irc, msg, args):
        """[<channel>] [<id>]

        Gives you a standard, random BOFH excuse or the excuse with the given 
        <id>.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args, required=0, optional=1)
        db = self.getDb(channel)
        cursor = db.cursor()
        if id:
            try:
                id = int(id)
            except ValueError:
                irc.error(msg, 'The <id> argument must be an integer.')
                return
            cursor.execute("""SELECT id, excuse FROM excuses WHERE id=%s""",
                           id)
            if cursor.rowcount == 0:
                irc.error(msg, 'There is no such excuse.')
                return
        else:
            cursor.execute("""SELECT id, excuse FROM excuses
                              WHERE excuse NOTNULL
                              ORDER BY random()
                              LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error(msg, 'There are currently no available excuses.')
        else:
            (id, excuse) = cursor.fetchone()
            showid = self.configurables.get('show-ids', channel)
            irc.reply(msg, self._formatResponse(excuse, id, showid))

    def lart(self, irc, msg, args):
        """[<channel>] [<id>] <text> [for <reason>]

        Uses a lart on <text> (giving the reason, if offered). Will use lart
        number <id> from the database when <id> is given.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (id, nick) = privmsgs.getArgs(args, optional=1)
        try:
            id = int(id)
            if id < 1:
                irc.error(msg, 'There is no such lart.')
                return
        except ValueError:
            nick = ' '.join([id, nick]).strip()
            id = 0
        if not nick:
            raise callbacks.ArgumentError
        if nick == irc.nick:
            nick = msg.nick
        try:
            (nick, reason) = imap(' '.join,
                             utils.itersplit('for'.__eq__, nick.split(), 1))
        except ValueError:
            reason = ''
        db = self.getDb(channel)
        cursor = db.cursor()
        if id:
            cursor.execute("""SELECT id, lart FROM larts WHERE id=%s""", id)
            if cursor.rowcount == 0:
                irc.error(msg, 'There is no such lart.')
                return
        else:
            cursor.execute("""SELECT id, lart FROM larts
                              WHERE lart NOTNULL
                              ORDER BY random()
                              LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error(msg, 'There are currently no available larts.')
        else:
            (id, lart) = cursor.fetchone()
            nick = re.sub(r'\bme\b', msg.nick, nick)
            reason = re.sub(r'\bme\b', msg.nick, reason)
            nick = re.sub(r'\bmy\b', '%s\'s' % msg.nick, nick)
            reason = re.sub(r'\bmy\b', '%s\'s' % msg.nick, reason)
            lartee = nick
            s = lart.replace('$who', lartee)
            if reason:
                s = '%s for %s' % (s, reason)
            s = s.rstrip('.')
            showid = self.configurables.get('show-ids', channel)
            irc.reply(msg, self._formatResponse(s, id, showid), action=True)

    def praise(self, irc, msg, args):
        """[<channel>] [<id>] <text> [for <reason>]

        Uses a praise on <text> (giving the reason, if offered). Will use
        praise number <id> from the database when <id> is given.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (id, nick) = privmsgs.getArgs(args, optional=1)
        try:
            id = int(id)
            if id < 1:
                irc.error(msg, 'There is no such praise.')
                return
        except ValueError:
            nick = ' '.join([id, nick]).strip()
            id = 0
        if not nick:
            raise callbacks.ArgumentError
        try:
            (nick, reason) = imap(' '.join,
                             utils.itersplit('for'.__eq__, nick.split(), 1))
        except ValueError:
            reason = ''
        db = self.getDb(channel)
        cursor = db.cursor()
        if id:
            cursor.execute("""SELECT id, praise FROM praises WHERE id=%s""",id)
            if cursor.rowcount == 0:
                irc.error(msg, 'There is no such praise.')
                return
        else:
            cursor.execute("""SELECT id, praise FROM praises
                              WHERE praise NOTNULL
                              ORDER BY random()
                              LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error(msg, 'There are currently no available praises.')
        else:
            (id, praise) = cursor.fetchone()
            nick = re.sub(r'\bme\b', msg.nick, nick)
            reason = re.sub(r'\bme\b', msg.nick, reason)
            nick = re.sub(r'\bmy\b', '%s\'s' % msg.nick, nick)
            reason = re.sub(r'\bmy\b', '%s\'s' % msg.nick, reason)
            praisee = nick
            s = praise.replace('$who', praisee)
            if reason:
                s = '%s for %s' % (s, reason)
            s = s.rstrip('.')
            showid = self.configurables.get('show-ids', channel)
            irc.reply(msg, self._formatResponse(s, id, showid), action=True)

Class = FunDB


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print 'Usage: %s <channel> <larts|excuses|insults|zipcodes> file'\
              ' [<console>]' % sys.argv[0]
        sys.exit(-1)
    if len(sys.argv) == 4:
        added_by = sys.argv.pop()
    else:
        added_by = '<console>'
    (channel, category, filename) = sys.argv[1:]
    plugin = Class()
    db = plugin.getDb(channel)
    cursor = db.cursor()
    for line in open(filename, 'r'):
        line = line.rstrip()
        if not line:
            continue
        elif category == 'larts':
            if '$who' in line:
                cursor.execute("""INSERT INTO larts VALUES (NULL, %s, %s)""",
                               line, added_by)
            else:
                print 'Invalid lart: %s' % line
        elif category == 'praises':
            if '$who' in line:
                cursor.execute("""INSERT INTO praises VALUES (NULL, %s, %s)""",
                               line, added_by)
            else:
                print 'Invalid praise: %s' % line
        elif category == 'insults':
            cursor.execute("""INSERT INTO insults VALUES (NULL, %s, %s)""",
                           line, added_by)
        elif category == 'excuses':
            cursor.execute("""INSERT INTO excuses VALUES (NULL, %s, %s )""",
                           line, added_by)
    db.commit()
    db.close()

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
