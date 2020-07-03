###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import os
import time

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.utils.structures import TimeoutQueue
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Herald')

filename = conf.supybot.directories.data.dirize('Herald.db')

class HeraldDB(plugins.ChannelUserDB):
    def serialize(self, v):
        return [v]

    def deserialize(self, channel, id, L):
        if len(L) != 1:
            raise ValueError
        return L[0]

class Herald(callbacks.Plugin):
    """This plugin allows you to set welcome messages (heralds) to people who
    are recognized by the bot when they join a channel."""
    def __init__(self, irc):
        self.__parent = super(Herald, self)
        self.__parent.__init__(irc)
        self.db = HeraldDB(filename)
        world.flushers.append(self.db.flush)
        self.lastParts = plugins.ChannelUserDictionary()
        splitTimeout = conf.supybot.plugins.Herald.throttle.afterSplit
        self.splitters = TimeoutQueue(splitTimeout)
        self.lastHerald = plugins.ChannelUserDictionary()

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        self.db.close()
        self.__parent.die()

    def doQuit(self, irc, msg):
        # We want to observe netsplits and keep from heralding users rejoining
        # after one.
        if ircmsgs.isSplit(msg):
            self.splitters.enqueue(msg.nick)
            try:
                id = ircdb.users.getUserId(msg.prefix)
                self.splitters.enqueue(id)
            except KeyError:
                pass

    def doJoin(self, irc, msg):
        if ircutils.strEqual(irc.nick, msg.nick):
            return # It's us.
        channel = msg.args[0]
        irc = callbacks.SimpleProxy(irc, msg)
        if self.registryValue('heralding', channel, irc.network):
            try:
                id = ircdb.users.getUserId(msg.prefix)
            except KeyError:
                id = msg.nick
            if id in self.splitters:
                self.log.debug('Not heralding id #%s, recent split.', id)
                return
            now = time.monotonic()
            throttle = self.registryValue('throttle',
                                          channel, irc.network)
            if now - self.lastHerald.get((channel, id), 0) > throttle:
                if (channel, id) in self.lastParts:
                   i = self.registryValue('throttle.afterPart',
                                          channel, irc.network)
                   if now - self.lastParts[channel, id] < i:
                       return
                try:
                    herald = self.db[channel, id]
                except KeyError:
                    herald = self.registryValue('default', channel, irc.network)
                    if herald:
                        herald = ircutils.standardSubstitute(irc, msg, herald)
                        msgmaker = ircmsgs.privmsg
                        if self.registryValue('default.notice',
                                              channel, irc.network):
                            msgmaker = ircmsgs.notice
                        target = msg.nick
                        if self.registryValue('default.public',
                                              channel, irc.network):
                            target = channel
                        self.lastHerald[channel, id] = now
                        irc.queueMsg(msgmaker(target, herald))
                    return
                if herald:
                    self.lastHerald[channel, id] = now
                    herald = ircutils.standardSubstitute(irc, msg, herald)
                    irc.reply(herald, prefixNick=False)

    def doPart(self, irc, msg):
        try:
            id = self._getId(irc, msg.prefix)
        except KeyError:
            id = msg.nick
        self.lastParts[msg.args[0], id] = time.monotonic()

    def _getId(self, irc, userNickHostmask):
        try:
            id = ircdb.users.getUserId(userNickHostmask)
        except KeyError:
            if not ircutils.isUserHostmask(userNickHostmask):
                hostmask = irc.state.nickToHostmask(userNickHostmask)
                id = ircdb.users.getUserId(hostmask)
            else:
                raise KeyError
        return id

    @internationalizeDocstring
    def default(self, irc, msg, args, channel, optlist, text):
        """[<channel>] [--remove|<msg>]

        If <msg> is given, sets the default herald to <msg>.  A <msg> of ""
        will remove the default herald.  If <msg> is not given, returns the
        current default herald.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        if optlist and text:
            raise callbacks.ArgumentError
        for (option, foo) in optlist:
            if option == 'remove':
                self.setRegistryValue('default', '', channel)
                irc.replySuccess()
                return
        if text:
            self.setRegistryValue('default', text, channel)
            irc.replySuccess()
        else:
            resp = self.registryValue('default', channel, irc.network) or \
                   _('I do not have a default herald set for %s.') % channel
            irc.reply(resp)
    default = wrap(default, ['channel',
                             getopts({'remove': ''}),
                             additional('text')])

    @internationalizeDocstring
    def get(self, irc, msg, args, channel, user):
        """[<channel>] [<user|nick>]

        Returns the current herald message for <user> (or the user
        <nick|hostmask> is currently identified or recognized as).  If <user>
        is not given, defaults to the user giving the command.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        try:
            herald = self.db[channel, user.id]
            irc.reply(herald)
        except KeyError:
            irc.error(_('I have no herald for %s.') % user.name)
    get = wrap(get, ['channel', first('otherUser', 'user')])

    def _preCheck(self, irc, msg, user):
        capability = self.registryValue('requireCapability')
        if capability:
            try:
                u = ircdb.users.getUser(msg.prefix)
            except KeyError:
                irc.errorNotRegistered(Raise=True)
            else:
                if u != user:
                    if not ircdb.checkCapability(msg.prefix, capability):
                        irc.errorNoCapability(capability, Raise=True)

    # I chose not to make <user|nick> optional in this command because
    # if it's not a valid username (e.g., if the user tyops and misspells a
    # username), it may be nice not to clobber the user's herald.
    @internationalizeDocstring
    def add(self, irc, msg, args, channel, user, herald):
        """[<channel>] <user|nick> <msg>

        Sets the herald message for <user> (or the user <nick|hostmask> is
        currently identified or recognized as) to <msg>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._preCheck(irc, msg, user)
        self.db[channel, user.id] = herald
        irc.replySuccess()
    add = wrap(add, ['channel', 'otherUser', 'text'])

    @internationalizeDocstring
    def remove(self, irc, msg, args, channel, user):
        """[<channel>] [<user|nick>]

        Removes the herald message set for <user>, or the user
        <nick|hostmask> is currently identified or recognized as.  If <user>
        is not given, defaults to the user giving the command.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        self._preCheck(irc, msg, user)
        try:
            del self.db[channel, user.id]
            irc.replySuccess()
        except KeyError:
            irc.error(_('I have no herald for that user.'))
    remove = wrap(remove, ['channel', first('otherUser', 'user')])

    @internationalizeDocstring
    def change(self, irc, msg, args, channel, user, changer):
        """[<channel>] [<user|nick>] <regexp>

        Changes the herald message for <user>, or the user <nick|hostmask> is
        currently identified or recognized as, according to <regexp>.  If
        <user> is not given, defaults to the calling user. <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._preCheck(irc, msg, user)
        s = self.db[channel, user.id]
        newS = changer(s)
        self.db[channel, user.id] = newS
        irc.replySuccess()
    change = wrap(change, ['channel',
                          first('otherUser', 'user'),
                           'regexpReplacer'])


Class = Herald

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
