#!/usr/bin/python

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

import conf
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

class QuoteGrabs(plugins.ChannelDBHandler,
                 configurable.Mixin,
                 callbacks.Privmsg):
    configurables = configurable.Dictionary(
        [('random-grabber', configurable.BoolType, False,
          """Determines whether the bot will randomly grab possibly-suitable
          quotes for someone."""),]
    )
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
            if self.configurables.get('random-grabber', channel):
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
            irc.error(msg, 'You can\'t quote grab yourself.')
            return
        for m in reviter(irc.state.history):
            if m.command == 'PRIVMSG' and ircutils.nickEqual(m.nick, nick):
                self._grab(irc, m, msg.prefix)
                irc.reply(msg, conf.replySuccess)
                return
        irc.error(msg, 'I couldn\'t find a proper message to grab.')

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
            irc.error(msg,'I couldn\'t find a matching quotegrab for %s'%nick)
        else:
            text = cursor.fetchone()[0]
            irc.reply(msg, text)

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
                          WHERE nick=%s
                          ORDER BY id ASC""", nick)
        if cursor.rowcount == 0:
            irc.error(msg, 'I couldn\'t find any quotegrabs for %s' % nick)
        else:
            l = []
            for (id, quote) in cursor.fetchall():
                # strip the nick from the quote
                quote = quote.replace('<%s> ' % nick, '', 1)
                item_str = utils.ellipsisify('#%s: %s' % (id, quote), 50)
                l.append(item_str)
            irc.reply(msg, utils.commaAndify(l))

    def get(self, irc, msg, args):
        """<id>

        Return the quotegrab with the given <id>.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, '%r does not appear to be a valid quotegrab id'%id)
            return
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT quote, hostmask, added_at
                          FROM quotegrabs WHERE id = %s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'No quotegrab for id %r' % id)
            return
        quote, hostmask, timestamp = cursor.fetchone()
        time_str = time.strftime(conf.humanTimestampFormat,
                                 time.localtime(float(timestamp)))
        irc.reply(msg, '%s (Said by: %s on %s)' % (quote, hostmask, time_str))


Class = QuoteGrabs

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
