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
Add the module docstring here.  This will be used by the setup.py script.
"""

import plugins

import os
import time

import sqlite

import conf
import utils
import ircmsgs
import plugins
import ircutils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load QuoteGrabs')

example = utils.wrapLines("""
Add an example IRC session using this module here.
""")

grabTime = 864000 # 10 days

class QuoteGrabs(plugins.ChannelDBHandler,
                 plugins.Toggleable,
                 callbacks.Privmsg):
    toggles = plugins.ToggleDictionary({'random': False})
    def __init__(self):
        plugins.Toggleable.__init__(self)
        plugins.ChannelDBHandler.__init__(self)
        callbacks.Privmsg.__init__(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(db=filename, mode=0755,
                                  converters={'bool': bool})
        #else:
        db = sqlite.connect(db=filename, mode=0755, coverters={'bool': bool})
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE quotegrabs (
                          id INTEGER PRIMARY KEY,
                          nick TEXT,
                          hostmask TEXT,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          quote TEXT
                          );""")
        db.commit()
        return db
        
    def doPrivmsg(self, irc, msg):
        if ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
            if self.toggles.get('random', channel):
                if len(msg.args[1]) > 8 and len(msg.args[1].split()) > 3:
                    db = self.getDb(channel)
                    cursor = db.cursor()
                    cursor.execute("""SELECT added_at FROM quotegrabs
                                      WHERE nick=%s
                                      ORDER BY id DESC LIMIT 1""", msg.nick)
                    if cursor.rowcount == 0:
                        self._grab(msg, irc.prefix)
                    else:
                        last = int(cursor.fetchone()[0])
                        elapsed = int(time.time()) - last
                        if random.random()*elapsed > grabTime/2:
                            self._grab(msg, irc.prefix)
                            s = 'jots down a new quote for %s' % msg.nick
                            irc.queueMsg(ircmsgs.action(msg.args[0], s))

    def _grab(self, msg, addedBy):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        text = ircmsgs.prettyPrint(msg)
        cursor.execute("""INSERT INTO quotegrabs
                          VALUES (NULL, %s, %s, %s, %s, %s)""",
                       msg.nick, msg.prefix, addedBy, int(time.time()), text)
        db.commit()

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
            if m.command == 'PRIVMSG' and m.nick == nick:
                self._grab(m, msg.prefix)
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
                          WHERE nick=%s
                          ORDER BY id DESC LIMIT 1""", nick)
        if cursor.rowcount == 0:
            irc.error(msg,'I couldn\'t find a matching quotegrab for %s'%nick)
        else:
            text = cursor.fetchone()[0]
            irc.reply(msg, text)


Class = QuoteGrabs

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
