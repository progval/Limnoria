#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

import supybot.plugins as plugins

import re
import csv
import sets
import random
import itertools

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
import supybot.world as world
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

class DbiFunDBDB(object):
    class FunDBDB(dbi.DB):
        class Record(object):
            __metaclass__ = dbi.Record
            __fields__ = [
                'by',
                'text',
                ]

    def __init__(self):
        self.dbs = ircutils.IrcDict()
        self.filenames = sets.Set()

    def close(self):
        for filename in self.filenames:
            try:
                db = self.FunDBDB(filename)
                db.close()
            except EnvironmentError:
                pass

    def _getDb(self, channel, type):
        type = type.lower()
        if channel not in self.dbs:
            self.dbs[channel] = {}
        if type not in self.dbs[channel]:
            filename = type.capitalize() + '.db'
            filename = plugins.makeChannelFilename(filename, channel)
            self.filenames.add(filename)
            self.dbs[channel][type] = self.FunDBDB(filename)
        return self.dbs[channel][type]

    def get(self, channel, type, id):
        db = self._getDb(channel, type)
        return db.get(id)

    def add(self, channel, type, text, by):
        db = self._getDb(channel, type)
        return db.add(db.Record(by=by, text=text))

    def remove(self, channel, type, id):
        db = self._getDb(channel, type)
        db.remove(id)

    def change(self, channel, type, id, f):
        db = self._getDb(channel, type)
        record = db.get(id)
        record.text = f(record.text)
        db.set(id, record)

    def random(self, channel, type):
        db = self._getDb(channel, type)
        return db.random()

    def size(self, channel, type):
        db = self._getDb(channel, type)
        return itertools.ilen(db)

def FunDBDB():
    return DbiFunDBDB()

conf.registerPlugin('FunDB')
conf.registerChannelValue(conf.supybot.plugins.FunDB, 'showIds',
    registry.Boolean(True, """Determines whether the bot will show the id of an
    insult/praise/lart."""))

class FunDB(callbacks.Privmsg):
    """
    Contains the 'fun' commands that require a database.  Currently includes
    commands for larting, praising, and insulting.
    """
    _types = ('insult', 'lart', 'praise')
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = FunDBDB()

    def die(self):
        self.db.close()

    def _getBy(self, by):
        try:
            return ircdb.users.getUser(int(by)).name
        except ValueError:
            return by

    def _validType(self, irc, type, error=True):
        if type not in self._types:
            if error:
                irc.error('%r is not a valid type.  Valid types include %s.' %
                          (type, utils.commaAndify(self._types)))
            return False
        else:
            return True

    def _validId(self, irc, id, error=True):
        try:
            return int(id)
        except ValueError:
            if error:
                irc.error('The <id> argument must be an integer.')
            return None

    def _isRegistered(self, irc, msg):
        try:
            return ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return None

    def add(self, irc, msg, args):
        """[<channel>] <lart|insult|praise> <text>

        Adds another record to the data referred to in the first argument.  For
        commands that will later respond with an ACTION (lart and praise), $who
        should be in the message to show who should be larted or praised.  I.e.
        'fundb add lart slices $who in half with a free AOL cd' would make the
        bot, when it used that lart against, say, jemfinch, to say '/me slices
        jemfinch in half with a free AOL cd'  <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (type, s) = privmsgs.getArgs(args, required=2)
        type = type.lower()
        userId = self._isRegistered(irc, msg)
        if not userId:
            return
        if not self._validType(irc, type):
            return
        if type == "lart" or type == "praise":
            if '$who' not in s:
                irc.error('There must be a $who in the lart/praise somewhere')
                return
        id = self.db.add(channel, type, s, userId)
        irc.replySuccess('(%s #%s added)' % (type, id))

    def remove(self, irc, msg, args):
        """[<channel>] <lart|insult|praise> <id>

        Removes the data, referred to in the first argument, with the id
        number <id> from the database.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (type, id) = privmsgs.getArgs(args, required=2)
        if not self._isRegistered(irc, msg):
            return
        if not self._validType(irc, type):
            return
        id = self._validId(irc, id)
        if id is None:
            return
        try:
            self.db.remove(channel, type, id)
            irc.replySuccess()
        except KeyError:
            irc.error('There is no %s with that id.' % type)

    def change(self, irc, msg, args):
        """[<channel>] <lart|insult|praise> <id> <regexp>

        Changes the data, referred to in the first argument, with the id
        number <id> according to the regular expression <regexp>. <id> is the
        zero-based index into the db; <regexp> is a regular expression of the
        form s/regexp/replacement/flags.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (type, id, regexp) = privmsgs.getArgs(args, required=3)
        if not self._validType(irc, type):
            return
        id = self._validId(irc, id)
        if id is None:
            return
        if not self._isRegistered(irc, msg):
            return
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error('That regexp wasn\'t valid: %s.' % e.args[0])
            return
        except re.error, e:
            irc.error(utils.exnToString(e))
            return
        try:
            self.db.change(channel, type, id, replacer)
            irc.replySuccess()
        except KeyError:
            irc.error('There is no %s with that id.' % type)

    def stats(self, irc, msg, args):
        """[<channel>] <lart|insult|praise>

        Returns the number of records, of the type specified, currently in
        the database.  <channel> is only necessary if the message isn't sent
        in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        type = privmsgs.getArgs(args)
        if not self._validType(irc, type):
            return
        total = self.db.size(channel, type)
        irc.reply('There %s currently %s in my database.' %
                  (utils.be(total), utils.nItems(type, total)))

    def get(self, irc, msg, args):
        """[<channel>] <lart|insult|praise> <id>

        Gets the record with id <id> from the type specified.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (type, id) = privmsgs.getArgs(args, required=2)
        if not self._validType(irc, type):
            return
        id = self._validId(irc, id)
        if id is None:
            return
        try:
            x = self.db.get(channel, type, id)
            irc.reply(x.text)
        except KeyError:
            irc.error('There is no %s with that id.' % type)

    def info(self, irc, msg, args):
        """[<channel>] <lart|insult|praise> <id>

        Gets the info for the record with id <id> from the type specified.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (type, id) = privmsgs.getArgs(args, required=2)
        if not self._validType(irc, type):
            return
        id = self._validId(irc, id)
        if id is None:
            return
        try:
            x = self.db.get(channel, type, id)
            reply = '%s #%s: %r; Created by %s.' % (type, x.id, x.text,
                                                    self._getBy(x.by))
            irc.reply(reply)
        except KeyError:
            irc.error('There is no %s with that id.' % type)

    def _formatResponse(self, s, id, channel):
        if self.registryValue('showIds', channel):
            return '%s (#%s)' % (s, id)
        else:
            return s

    _meRe = re.compile(r'\bme\b', re.I)
    _myRe = re.compile(r'\bmy\b', re.I)
    def _replaceFirstPerson(self, s, nick):
        s = self._meRe.sub(nick, s)
        s = self._myRe.sub('%s\'s' % nick, s)
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
        insult = self.db.random(channel, 'insult')
        if insult is None:
            irc.error('There are currently no available insults.')
        else:
            nick = self._replaceFirstPerson(nick, msg.nick)
            s = '%s: %s' % (nick, insult.text.replace('$who', nick))
            irc.reply(self._formatResponse(s, insult.id, channel),
                      prefixName=False)

    def lart(self, irc, msg, args):
        """[<channel>] [<id>] <text> [for <reason>]

        Uses a lart on <text> (giving the reason, if offered). Will use lart
        number <id> from the database when <id> is given.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (id, nick) = privmsgs.getArgs(args, optional=1)
        id = self._validId(irc, id, error=False)
        if id is None:
            nick = privmsgs.getArgs(args)
        nick = nick.rstrip('.')
        if not nick:
            raise callbacks.ArgumentError
        if ircutils.strEqual(nick, irc.nick):
            nick = msg.nick
        try:
            (nick, reason) = itertools.imap(' '.join,
                             utils.itersplit('for'.__eq__, nick.split(), 1))
        except ValueError:
            reason = ''
        if id:
            try:
                lart = self.db.get(channel, 'lart', id)
            except KeyError:
                irc.error('There is no such lart.')
                return
        else:
            lart = self.db.random(channel, 'lart')
        if lart is None:
            irc.error('There are currently no available larts.')
        else:
            nick = self._replaceFirstPerson(nick, msg.nick)
            reason = self._replaceFirstPerson(reason, msg.nick)
            s = lart.text.replace('$who', nick)
            if reason:
                s = '%s for %s' % (s, reason)
            s = s.rstrip('.')
            irc.reply(self._formatResponse(s, lart.id, channel), action=True)

    def praise(self, irc, msg, args):
        """[<channel>] [<id>] <text> [for <reason>]

        Uses a praise on <text> (giving the reason, if offered). Will use
        praise number <id> from the database when <id> is given.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (id, nick) = privmsgs.getArgs(args, optional=1)
        id = self._validId(irc, id, error=False)
        if id is None:
            nick = privmsgs.getArgs(args)
        nick = nick.rstrip('.')
        if not nick:
            raise callbacks.ArgumentError
        try:
            (nick, reason) = itertools.imap(' '.join,
                             utils.itersplit('for'.__eq__, nick.split(), 1))
        except ValueError:
            reason = ''
        if id:
            try:
                praise = self.db.get(channel, 'praise', id)
            except KeyError:
                irc.error('There is no such praise.')
                return
        else:
            praise = self.db.random(channel, 'praise')
        if praise is None:
            irc.error('There are currently no available praises.')
        else:
            nick = self._replaceFirstPerson(nick, msg.nick)
            reason = self._replaceFirstPerson(reason, msg.nick)
            s = praise.text.replace('$who', nick)
            if reason:
                s = '%s for %s' % (s, reason)
            s = s.rstrip('.')
            irc.reply(self._formatResponse(s, praise.id, channel), action=True)

Class = FunDB


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
