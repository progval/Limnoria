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
The Dunno module is used to spice up the 'replyWhenNotCommand' behavior with
random 'I dunno'-like responses.  If you want something spicier than '<x> is
not a valid command'-like responses, use this plugin.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.strike

__contributors__ = {
    supybot.authors.jemfinch: ['Flatfile DB implementation.'],
    }

import os
import csv
import sets
import time
import random
import itertools

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.registry as registry
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

conf.registerPlugin('Dunno')
conf.registerChannelValue(conf.supybot.plugins.Dunno, 'prefixNick',
    registry.Boolean(True, """Determines whether the bot will prefix the nick
    of the user giving an invalid command to the "dunno" response."""))

class DbiDunnoDB(plugins.DbiChannelDB):
    class DB(dbi.DB):
        class Record(dbi.Record):
            __fields__ = [
                'at',
                'by',
                'text',
                ]
        def __init__(self, filename):
            # We use self.__class__ here because apparently DB isn't in our
            # scope.  python--
            self.__parent = super(self.__class__, self)
            self.__parent.__init__(filename)

        def add(self, text, by, at):
            return self.__parent.add(self.Record(at=at, by=by, text=text))

        def change(self, id, f):
            dunno = self.get(id)
            dunno.text = f(dunno.text)
            self.set(id, dunno)

DunnoDB = plugins.DB('Dunno', {'flat': DbiDunnoDB})

class Dunno(callbacks.Privmsg):
    """This plugin was written initially to work with MoobotFactoids, the two
    of them to provide a similar-to-moobot-and-blootbot interface for factoids.
    Basically, it replaces the standard 'Error: <X> is not a valid command.'
    messages with messages kept in a database, able to give more personable
    responses."""
    callAfter = ['MoobotFactoids']
    def __init__(self):
        self.__parent = super(Dunno, self)
        self.__parent.__init__()
        self.db = DunnoDB()

    def die(self):
        self.db.close()
        self.__parent.die()

    def invalidCommand(self, irc, msg, tokens):
        channel = msg.args[0]
        if ircutils.isChannel(channel):
            dunno = self.db.random(channel)
            if dunno is not None:
                dunno = dunno.text
                prefixName = self.registryValue('prefixNick', channel)
                dunno = ircutils.standardSubstitute(irc, msg, dunno)
                irc.reply(dunno, prefixName=prefixName)

    def add(self, irc, msg, args, user, at, channel, dunno):
        """[<channel>] <text>

        Adds <text> as a "dunno" to be used as a random response when no
        command or factoid key matches.  Can optionally contain '$who', which
        will be replaced by the user's name when the dunno is displayed.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        id = self.db.add(channel, dunno, user.id, at)
        irc.replySuccess('Dunno #%s added.' % id)
    add = wrap(add, ['user', 'now', 'channeldb', 'text'])

    def remove(self, irc, msg, args, user, channel, id):
        """[<channel>] <id>

        Removes dunno with the given <id>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        # Must be registered to use this
        try:
            dunno = self.db.get(channel, id)
            if user.id != dunno.by:
                # XXX We need to come up with a way to handle this capability
                # checking when channel is None.  It'll probably involve
                # something along the lines of using admin instead of
                # #channel,op.  The function should be added to
                # plugins/__init__.py
                cap = ircdb.makeChannelCapability(channel, 'op')
                if not ircdb.users.checkCapability(cap):
                    irc.errorNoCapability(cap)
            self.db.remove(channel, id)
            irc.replySuccess()
        except KeyError:
            irc.error('No dunno has id #%s.' % id)
    remove = wrap(remove, ['user', 'channeldb', ('id', 'dunno')])

    def search(self, irc, msg, args, channel, text):
        """[<channel>] <text>

        Search for dunno containing the given text.  Returns the ids of the
        dunnos with the text in them.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        def p(dunno):
            return text.lower() in dunno.text.lower()
        ids = [str(dunno.id) for dunno in self.db.select(channel, p)]
        if ids:
            s = 'Dunno search for %s (%s found): %s.' % \
                (utils.quoted(text), len(ids), utils.commaAndify(ids))
            irc.reply(s)
        else:
            irc.reply('No dunnos found matching that search criteria.')
    search = wrap(search, ['channeldb', 'text'])

    def get(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Display the text of the dunno with the given id.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        try:
            dunno = self.db.get(channel, id)
            name = ircdb.users.getUser(dunno.by).name
            at = time.localtime(dunno.at)
            timeStr = time.strftime(conf.supybot.humanTimestampFormat(), at)
            irc.reply("Dunno #%s: %s (added by %s at %s)" % \
                      (id, utils.quoted(dunno.text), name, timeStr))
        except KeyError:
            irc.error('No dunno found with that id.')
    get = wrap(get, ['channeldb', ('id', 'dunno')])

    def change(self, irc, msg, args, channel, id, replacer):
        """[<channel>] <id> <regexp>

        Alters the dunno with the given id according to the provided regexp.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        try:
            # Should this check that Record.by == user.id ||
            # checkChannelCapability like remove() does?
            self.db.change(channel, id, replacer)
        except KeyError:
            irc.error('There is no dunno #%s.' % id)
            return
        irc.replySuccess()
    change = wrap(change, ['channeldb', ('id', 'dunno'), 'regexpReplacer'])

    def stats(self, irc, msg, args, channel):
        """[<channel>]

        Returns the number of dunnos in the dunno database.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        num = self.db.size(channel)
        irc.reply('There %s %s in my database.' %
                  (utils.be(num), utils.nItems('dunno', num)))
    stats = wrap(stats, ['channeldb'])



Class = Dunno

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
