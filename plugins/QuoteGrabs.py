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
Quotegrabs are like IRC sound bites.  When someone says something funny,
incriminating, stupid, outrageous, ... anything that might be worth
remembering, you can grab that quote for that person.  With this plugin, you
can store many quotes per person and display their most recent quote, as well
as see who "grabbed" the quote in the first place.
"""

__revision__ = "$Id$"

import plugins

import os
import time
import random

import registry         # goes before conf! yell at jamessan, not me

import conf
import ircdb
import utils
import ircmsgs
import plugins
import ircutils
import privmsgs
import callbacks
import configurable

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load QuoteGrabs')

grabTime = 864000 # 10 days
minRandomLength = 8
minRandomWords = 3

conf.registerPlugin('QuoteGrabs')
conf.registerChannelValue(conf.supybot.plugins.QuoteGrabs, 'randomGrabber',
    registry.Boolean(False, """Determines whether the bot will randomly grab
    possibly-suitable quotes for someone."""))

class QuoteGrabs(plugins.ChannelDBHandler,
                 callbacks.Privmsg):
    def __init__(self):
        plugins.ChannelDBHandler.__init__(self)
        callbacks.Privmsg.__init__(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite.connect(filename, converters={'bool': bool})
        else:
            db = sqlite.connect(filename, coverters={'bool': bool})
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE quotegrabs (
                              id INTEGER PRIMARY KEY,
                              nick TEXT,
                              hostmask TEXT,
                              added_by TEXT,
                              added_at TIMESTAMP,
                              quote TEXT
                              );""")
        def p(s1, s2):
            return int(ircutils.nickEqual(s1, s2))
        db.create_function('nickeq', 2, p)
        db.commit()
        return db
        
    def doPrivmsg(self, irc, msg):
        if ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
            if conf.supybot.plugins.QuoteGrabs.randomGrabber():
                if len(msg.args[1]) > minRandomLength and \
                   len(msg.args[1].split()) > minRandomWords:
                    db = self.getDb(channel)
                    cursor = db.cursor()
                    cursor.execute("""SELECT added_at FROM quotegrabs
                                      WHERE nick=%s
                                      ORDER BY id DESC LIMIT 1""", msg.nick)
                    if cursor.rowcount == 0:
                        self._grab(irc, msg, irc.prefix)
                        self._sendGrabMsg(irc, msg)
                    else:
                        last = int(cursor.fetchone()[0])
                        elapsed = int(time.time()) - last
                        if random.random()*elapsed > grabTime/2:
                            self._grab(irc, msg, irc.prefix)
                            self._sendGrabMsg(irc, msg)

    def _grab(self, irc, msg, addedBy):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        text = ircmsgs.prettyPrint(msg)
        # Check to see if the latest quotegrab is identical
        cursor.execute("""SELECT quote FROM quotegrabs
                          WHERE nick=%s
                          ORDER BY id DESC LIMIT 1""", msg.nick)
        if cursor.rowcount != 0:
            if text == cursor.fetchone()[0]:
                return
        cursor.execute("""INSERT INTO quotegrabs
                          VALUES (NULL, %s, %s, %s, %s, %s)""",
                       msg.nick, msg.prefix, addedBy, int(time.time()), text)
        db.commit()

    def _sendGrabMsg(self, irc, msg):
        s = 'jots down a new quote for %s' % msg.nick 
        irc.queueMsg(ircmsgs.action(msg.args[0], s))

    def grab(self, irc, msg, args):
        """[<channel>] <nick>

        Grabs a quote from <channel> by <nick> for the quotegrabs table.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args)
        if nick == msg.nick:
            irc.error('You can\'t quote grab yourself.')
            return
        for m in reviter(irc.state.history):
            if m.command == 'PRIVMSG' and ircutils.nickEqual(m.nick, nick):
                self._grab(irc, m, msg.prefix)
                irc.replySuccess()
                return
        irc.error('I couldn\'t find a proper message to grab.')

    def quote(self, irc, msg, args):
        """[<channel>] <nick>

        Returns <nick>'s latest quote grab in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT quote FROM quotegrabs
                          WHERE nickeq(nick, %s)
                          ORDER BY id DESC LIMIT 1""", nick)
        if cursor.rowcount == 0:
            irc.error('I couldn\'t find a matching quotegrab for %s'%nick)
        else:
            text = cursor.fetchone()[0]
            irc.reply(text)

    def list(self, irc, msg, args):
        """<nick>

        Returns a list of shortened quotes that have been grabbed for <nick>
        as well as the id of each quote.  These ids can be used to get the
        full quote.
        """
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, quote FROM quotegrabs
                          WHERE nick LIKE %s
                          ORDER BY id ASC""", nick)
        if cursor.rowcount == 0:
            irc.error('I couldn\'t find any quotegrabs for %s' % nick)
        else:
            l = []
            for (id, quote) in cursor.fetchall():
                # strip the nick from the quote
                quote = quote.replace('<%s> ' % nick, '', 1)
                item_str = utils.ellipsisify('#%s: %s' % (id, quote), 50)
                l.append(item_str)
            irc.reply(utils.commaAndify(l))

    def randomquote(self, irc, msg, args):
        """[<nick>]

        Returns a randomly grabbed quote, optionally choosing only from those
        quotes grabbed for <nick>.
        """
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args, required=0, optional=1)
        db = self.getDb(channel)
        cursor = db.cursor()
        if nick:
            cursor.execute("""SELECT quote FROM quotegrabs
                              WHERE nick LIKE %s ORDER BY random() LIMIT 1""",
                              nick)
        else:
            cursor.execute("""SELECT quote FROM quotegrabs
                              ORDER BY random() LIMIT 1""")
        if cursor.rowcount == 0:
            if nick:
                irc.error('Couldn\'t get a random quote for that nick.')
            else:
                irc.error('Couldn\'t get a random quote.  Are there any'
                               'grabbed quotes in the database?')
            return
        quote = cursor.fetchone()[0]
        irc.reply(quote)

    def get(self, irc, msg, args):
        """<id>

        Return the quotegrab with the given <id>.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error('%r does not appear to be a valid quotegrab id' % id)
            return
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT quote, hostmask, added_at, added_by
                          FROM quotegrabs WHERE id = %s""", id)
        if cursor.rowcount == 0:
            irc.error('No quotegrab for id %r' % id)
            return
        quote, hostmask, timestamp, grabber_mask = cursor.fetchone()
        time_str = time.strftime(conf.supybot.humanTimestampFormat(),
                                 time.localtime(float(timestamp)))
        try:
            grabber = ircdb.users.getUser(grabber_mask).name
        except:
            grabber = grabber_mask       
        irc.reply('%s (Said by: %s; grabbed by %s on %s)' % \
                  (quote, hostmask, grabber, time_str))


Class = QuoteGrabs

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
