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
Plugin for handling basic Karma stuff for a channel.
"""

import os

import sqlite

import utils
import plugins
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Karma')

class Karma(callbacks.PrivmsgCommandAndRegexp, plugins.ChannelDBHandler):
    addressedRegexps = ['increaseKarma', 'decreaseKarma']
    def __init__(self):
        plugins.ChannelDBHandler.__init__(self)
        callbacks.PrivmsgCommandAndRegexp.__init__(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename)
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE karma (
                              id INTEGER PRIMARY KEY,
                              name TEXT,
                              normalized TEXT UNIQUE ON CONFLICT IGNORE,
                              added INTEGER,
                              subtracted INTEGER
                              )""")
            db.commit()
        def p(s1, s2):
            return int(ircutils.nickEqual(s1, s2))
        db.create_function('nickeq', 2, p)
        return db

    def karma(self, irc, msg, args):
        """[<channel>] [<text>]

        Returns the karma of <text>.  If <text> is not given, returns the top
        three and bottom three karmas. <channel> is only necessary if the
        message isn't sent on the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        if len(args) == 1:
            name = args[0]
            normalized = name.lower()
            cursor.execute("""SELECT added, subtracted
                              FROM karma
                              WHERE normalized=%s""", normalized)
            if cursor.rowcount == 0:
                irc.reply(msg, '%s has no karma.' % name)
            else:
                (added, subtracted) = map(int, cursor.fetchone())
                total = added - subtracted
                s = 'Karma for %r has been increased %s %s ' \
                    'and decreased %s %s for a total karma of %s.' % \
                    (name, added, utils.pluralize(added, 'time'),
                     subtracted, utils.pluralize(subtracted, 'time'), total)
                irc.reply(msg, s)
        elif len(args) > 1:
            normalizedArgs = map(str.lower, args)
            criteria = ' OR '.join(['normalized=%s'] * len(args))
            sql = """SELECT name, added-subtracted
                     FROM karma WHERE %s
                     ORDER BY added-subtracted DESC""" % criteria
            cursor.execute(sql, *normalizedArgs)
            if cursor.rowcount > 0:
                s = utils.commaAndify(['%s: %s' % (n, t)
                                       for (n,t) in cursor.fetchall()])
                irc.reply(msg, s + '.')
            else:
                irc.reply(msg, 'I didn\'t know the karma for any '
                               'of those things.')
        else: # No name was given.  Return the top/bottom 3 karmas.
            cursor.execute("""SELECT name, added-subtracted
                              FROM karma
                              ORDER BY added-subtracted DESC
                              LIMIT 3""")
            highest = ['%r (%s)' % (t[0], t[1]) for t in cursor.fetchall()]
            cursor.execute("""SELECT name, added-subtracted
                              FROM karma
                              ORDER BY added-subtracted ASC
                              LIMIT 3""")
            lowest = ['%r (%s)' % (t[0], t[1]) for t in cursor.fetchall()]
            if not (highest and lowest):
                irc.error(msg, 'I have no karma for this channel.')
            else:
                s = 'Highest karma: %s.  Lowest karma: %s.' % \
                    (utils.commaAndify(highest), utils.commaAndify(lowest))
                irc.reply(msg, s)
            
    def increaseKarma(self, irc, msg, match):
        r"^(\S+)\+\+(|\s+)$"
        name = match.group(1)
        normalized = name.lower()
        db = self.getDb(msg.args[0])
        cursor = db.cursor()
        cursor.execute("""INSERT INTO karma VALUES (NULL, %s, %s, 0, 0)""",
                       name, normalized)
        cursor.execute("""UPDATE karma
                          SET added=added+1
                          WHERE normalized=%s""", normalized)

    def decreaseKarma(self, irc, msg, match):
        r"^(\S+)--(|\s+)$"
        name = match.group(1)
        normalized = name.lower()
        db = self.getDb(msg.args[0])
        cursor = db.cursor()
        cursor.execute("""INSERT INTO karma VALUES (NULL, %s, %s, 0, 0)""",
                       name, normalized)
        cursor.execute("""UPDATE karma
                          SET subtracted=subtracted+1
                          WHERE normalized=%s""", normalized)


Class = Karma

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
