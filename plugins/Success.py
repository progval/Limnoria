###
# Copyright (c) 2004, Jeremiah Fincher
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
The Success plugin spices up success replies just like Dunno spices up
"no such command" replies.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import time

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.plugins as plugins
from supybot.commands import wrap
import supybot.registry as registry
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

conf.registerPlugin('Success')
conf.registerChannelValue(conf.supybot.plugins.Success, 'prefixNick',
    registry.Boolean(True, """Determines whether the bot will prefix the nick
    of the user giving an invalid command to the success response."""))

class DbiSuccessDB(plugins.DbiChannelDB):
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

SuccessDB = plugins.DB('Success', {'flat': DbiSuccessDB})

class Success(callbacks.Privmsg):
    """This plugin was written initially to work with MoobotFactoids, the two
    of them to provide a similar-to-moobot-and-blootbot interface for factoids.
    Basically, it replaces the standard 'Error: <X> is not a valid command.'
    messages with messages kept in a database, able to give more personable
    responses."""
    def __init__(self):
        self.__parent = super(Success, self)
        self.__parent.__init__()
        self.target = None
        self.db = SuccessDB()
        pluginSelf = self
        self.originalClass = conf.supybot.replies.success.__class__
        class MySuccessClass(self.originalClass):
            def __call__(self):
                ret = pluginSelf.db.random(pluginSelf.target)
                if ret is None:
                    try:
                        self.__class__ = pluginSelf.originalClass
                        ret = self()
                    finally:
                        self.__class__ = MySuccessClass
                else:
                    ret = ret.text
                return ret

            def get(self, attr):
                if ircutils.isChannel(attr):
                    pluginSelf.target = attr
                return self
        conf.supybot.replies.success.__class__ = MySuccessClass

    def die(self):
        self.db.close()
        self.__parent.die()
        conf.supybot.replies.success.__class__ = self.originalClass

    def inFilter(self, irc, msg):
        # We need the target, but we need it before Owner.doPrivmsg is called,
        # so this seems like the only way to do it.
        self.target = msg.args[0]
        return msg

    def add(self, irc, msg, args, user, at, channel, text):
        """[<channel>] <text>

        Adds <text> as a "success" to be used as a random response when a
        success message is needed.  Can optionally contain '$who', which
        will be replaced by the user's name when the dunno is displayed.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        id = self.db.add(channel, text, user.id, at)
        irc.replySuccess('Success #%s added.' % id)
    add = wrap(add, ['user', 'now', 'channeldb', 'text'])

    def remove(self, irc, msg, args, channel, id, user):
        """[<channel>] <id>

        Removes success with the given <id>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        # Must be registered to use this
        try:
            success = self.db.get(channel, id)
            if user.id != success.by:
                cap = ircdb.makeChannelCapability(channel, 'op')
                if not ircdb.users.checkCapability(cap):
                    irc.errorNoCapability(cap)
            self.db.remove(channel, id)
            irc.replySuccess()
        except KeyError:
            irc.error('No success has id #%s.' % id)
    remove = wrap(remove, ['channeldb', ('id', 'success'), 'user'])

    def search(self, irc, msg, args, channel, text):
        """[<channel>] <text>

        Search for success containing the given text.  Returns the ids of the
        successes with the text in them.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        def p(success):
            return text.lower() in success.text.lower()
        ids = [str(success.id) for success in self.db.select(channel, p)]
        if ids:
            s = 'Success search for %r (%s found): %s.' % \
                (text, len(ids), utils.commaAndify(ids))
            irc.reply(s)
        else:
            irc.reply('No successes found matching that search criteria.')
    search = wrap(search, ['channeldb', 'text'])

    def get(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Display the text of the success with the given id.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        try:
            success = self.db.get(channel, id)
            name = ircdb.users.getUser(success.by).name
            at = time.localtime(success.at)
            timeStr = time.strftime(conf.supybot.humanTimestampFormat(), at)
            irc.reply("Success #%s: %r (added by %s at %s)" % \
                      (id, success.text, name, timeStr))
        except KeyError:
            irc.error('No success found with that id.')
    get = wrap(get, ['channeldb', ('id', 'success')])

    def change(self, irc, msg, args, user, channel, id, replacer):
        """[<channel>] <id> <regexp>

        Alters the success with the given id according to the provided regexp.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        try:
            self.db.change(channel, id, replacer)
            irc.replySuccess()
        except KeyError:
            irc.error('There is no success #%s.' % id)
    change = wrap(change, ['user', 'channeldb',
                           ('id', 'success'), 'regexpReplacer'])
                            

    def stats(self, irc, msg, args, channel):
        """[<channel>]

        Returns the number of successes in the success database.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        num = self.db.size(channel)
        irc.reply('There %s %s in my database.' %
                  (utils.be(num), utils.nItems('success', num)))
    stats = wrap(stats, ['channeldb'])



Class = Success

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
