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
import supybot.plugins as plugins
import supybot.registry as registry
import supybot.privmsgs as privmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

conf.registerPlugin('Dunno')
conf.registerChannelValue(conf.supybot.plugins.Dunno, 'prefixNick',
    registry.Boolean(True, """Determines whether the bot will prefix the nick
    of the user giving an invalid command to the "dunno" response."""))

class DbiDunnoDB(object):
    class DunnoDB(dbi.DB):
        class Record(object):
            __metaclass__ = dbi.Record
            __fields__ = [
                'at',
                'by',
                'text',
                ]
    def __init__(self):
        self.filenames = sets.Set()

    def _getDb(self, channel):
        # Why cache?  It gains very little.
        filename = plugins.makeChannelFilename(channel, 'Dunno.db')
        self.filenames.add(filename)
        return self.DunnoDB(filename)

    def close(self):
        for filename in self.filenames:
            try:
                db = self.DunnoDB(filename)
                db.close()
            except EnvironmentError:
                pass

    def flush(self):
        pass
    
    def add(self, channel, text, by, at):
        db = self._getDb(channel)
        return db.add(db.Record(at=at, by=by, text=text))

    def remove(self, channel, id):
        db = self._getDb(channel)
        db.remove(id)

    def get(self, channel, id):
        db = self._getDb(channel)
        return db.get(id)

    def change(self, channel, id, f):
        db = self._getDb(channel)
        dunno = db.get(id)
        dunno.text = f(dunno.text)
        db.set(id, dunno)
        
    def random(self, channel):
        db = self._getDb(channel)
        return random.choice(db)

    def search(self, channel, p):
        db = self._getDb(channel)
        return db.select(p)
    
    def size(self, channel):
        try:
            db = self._getDb(channel)
            return itertools.ilen(db)
        except EnvironmentError, e:
            return 0
    
def DunnoDB():
    return DbiDunnoDB()
        
class Dunno(callbacks.Privmsg):
    """This plugin was written initially to work with MoobotFactoids, the two
    of them to provide a similar-to-moobot-and-blootbot interface for factoids.
    Basically, it replaces the standard 'Error: <X> is not a valid command.'
    messages with messages kept in a database, able to give more personable
    responses."""
    priority = 100
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = DunnoDB()

    def die(self):
        self.db.close()

    def invalidCommand(self, irc, msg, tokens):
        channel = msg.args[0]
        if ircutils.isChannel(channel):
            dunno = self.db.random(channel)
            if dunno is not None:
                dunno = dunno.text
                prefixName = self.registryValue('prefixNick', channel)
                dunno = plugins.standardSubstitute(irc, msg, dunno)
                irc.reply(dunno, prefixName=prefixName)

    def add(self, irc, msg, args):
        """[<channel>] <text>

        Adds <text> as a "dunno" to be used as a random response when no
        command or factoid key matches.  Can optionally contain '$who', which
        will be replaced by the user's name when the dunno is displayed.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        try:
            by = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        dunno = privmsgs.getArgs(args)
        at = int(time.time())
        id = self.db.add(channel, dunno, by, at)
        irc.replySuccess('Dunno #%s added.' % id)

    def remove(self, irc, msg, args):
        """[<channel>] <id>

        Removes dunno with the given <id>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        # Must be registered to use this
        channel = privmsgs.getChannel(msg, args)
        try:
            by = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error('Invalid id: %r' % id)
            return
        dunno = self.db.get(channel, id)
        if by != dunno.by:
            cap = ircdb.makeChannelCapability(channel, 'op')
            if not ircdb.users.checkCapability(cap):
                irc.errorNoCapability(cap)
                return
        try:
            self.db.remove(channel, id)
            irc.replySuccess()
        except KeyError:
            irc.error('No dunno has id #%s.' % id)

    def search(self, irc, msg, args):
        """[<channel>] <text>

        Search for dunno containing the given text.  Returns the ids of the
        dunnos with the text in them.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        text = privmsgs.getArgs(args)
        def p(dunno):
            return text.lower() in dunno.text.lower()
        ids = [str(dunno.id) for dunno in self.db.search(channel, p)]
        if ids:
            s = 'Dunno search for %r (%s found): %s.' % \
                (text, len(ids), utils.commaAndify(ids))
            irc.reply(s)
        else:
            irc.reply('No dunnos found matching that search criteria.')

    def get(self, irc, msg, args):
        """[<channel>] <id>

        Display the text of the dunno with the given id.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error('%r is not a valid dunno id.' % id)
            return
        try:
            dunno = self.db.get(channel, id)
            name = ircdb.users.getUser(dunno.by).name
            at = time.localtime(dunno.at)
            timeStr = time.strftime(conf.supybot.humanTimestampFormat(), at)
            irc.reply("Dunno #%s: %r (added by %s at %s)" % \
                      (id, dunno.text, name, timeStr))
        except KeyError:
            irc.error('No dunno found with that id.')

    def change(self, irc, msg, args):
        """[<channel>] <id> <regexp>

        Alters the dunno with the given id according to the provided regexp.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (id, regexp) = privmsgs.getArgs(args, required=2)
        try:
            user_id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        # Check id arg
        try:
            id = int(id)
        except ValueError:
            irc.error('%r is not a valid dunno id.' % id)
            return
        try:
            _ = self.db.get(channel, id)
        except KeyError:
            irc.error('There is no dunno #%s.' % id)
            return
        try:
            replacer = utils.perlReToReplacer(regexp)
        except:
            irc.error('%r is not a valid regular expression.' % regexp)
            return
        self.db.change(channel, id, replacer)
        irc.replySuccess()

    def stats(self, irc, msg, args):
        """[<channel>]

        Returns the number of dunnos in the dunno database.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        num = self.db.size(channel)
        irc.reply('There %s %s in my database.' %
                  (utils.be(num), utils.nItems('dunno', num)))



Class = Dunno

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
