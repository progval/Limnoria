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
A module to allow each channel to have "news" which people will be notified of
when they join the channel.  News items may have expiration dates.
"""

from baseplugin import *

import sqlite

import utils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load News')

example = utils.wrapLines("""

""")

class News(callbacks.Privmsg, ChannelDBHandler):
    def __init__(self):
        ChannelDBHandler.__init__(self)
        callbacks.Privmsg.__init__(self)
        self.removeOld = False

    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(filename)
        db = sqlite.connect(filename)
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE news (
                          id INTEGER PRIMARY KEY,
                          item TEXT,
                          added_at TIMESTAMP,
                          expires_at TIMESTAMP,
                          added_by TEXT
                          )""")
        db.commit()
        return db

    def addnews(self, irc, msg, args):
        """[<channel>] <expires> <text>

        Adds a given news item of <text> to a channel.  If <expires> isn't 0,
        that news item will expire <expires> seconds from now.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        pass

    def removenews(self, irc, msg, args):
        """[<channel>] <number>

        Removes the news item with id <number> from <channel>.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        pass

    def changenews(self, irc, msg, args):
        """[<channel>] <number> <regexp>

        Changes the news item with id <number> from <channel> according to the
        regular expression <regexp>.  <regexp> should be of the form
        s/text/replacement/flags.  <channel> is only necessary if the message
        isn't sent on the channel itself.
        """
        pass

    def oldnews(self, irc, msg, args):
        """[<channel>] <number>

        Returns the old news item for <channel> with id <number>.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        pass

Class = News

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
