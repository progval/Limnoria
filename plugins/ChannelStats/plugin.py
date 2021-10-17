###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009-2010, James McCoy
# Copyright (c) 2010-2021, Valentin Lorentz
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

import re
import math
import types

import supybot.log as log
import supybot.conf as conf
from supybot.i18n import PluginInternationalization, internationalizeDocstring
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.utils.math_evaluator import safe_eval, InvalidNode

_ = PluginInternationalization('ChannelStats')

class ChannelStat(irclib.IrcCommandDispatcher):
    _values = ['actions', 'chars', 'frowns', 'joins', 'kicks','modes',
               'msgs', 'parts', 'quits', 'smileys', 'topics', 'words', 'users']
    def __init__(self, actions=0, chars=0, frowns=0, joins=0, kicks=0, modes=0,
                 msgs=0, parts=0, quits=0, smileys=0, topics=0, words=0,
                 users=0):
        self.actions = actions
        self.chars = chars
        self.frowns = frowns
        self.joins = joins
        self.kicks = kicks
        self.modes = modes
        self.msgs = msgs
        self.parts = parts
        self.quits = quits
        self.smileys = smileys
        self.topics = topics
        self.words = words
        self.users = users

    def values(self):
        return [getattr(self, s) for s in self._values]

    def addMsg(self, msg):
        self.msgs += 1
        method = self.dispatchCommand(msg.command, msg.args)
        if method is not None:
            method(msg)

    def doPayload(self, channel, payload):
        channel = plugins.getChannel(channel)
        self.chars += len(payload)
        self.words += len(payload.split())
        fRe = conf.supybot.plugins.ChannelStats.get('frowns').get(channel)()
        sRe =conf.supybot.plugins.ChannelStats.get('smileys').get(channel)()
        self.frowns += len(fRe.findall(payload))
        self.smileys += len(sRe.findall(payload))

    def doPrivmsg(self, msg):
        isAction = ircmsgs.isAction(msg)
        if ircmsgs.isCtcp(msg) and not isAction:
            return
        self.doPayload(*msg.args)
        if isAction:
            self.actions += 1

    def doTopic(self, msg):
        self.doPayload(*msg.args)
        self.topics += 1

    def doKick(self, msg):
        self.kicks += 1

    def doPart(self, msg):
        if len(msg.args) == 2:
            self.doPayload(*msg.args)
        self.parts += 1

    def doJoin(self, msg):
        if len(msg.args) == 2:
            self.doPayload(*msg.args)
        self.joins += 1
        # Handle max-users in the plugin since we need an irc object

    def doMode(self, msg):
        self.modes += 1

    # doQuit is handled by the plugin.


class UserStat(ChannelStat):
    _values = ['kicked'] + ChannelStat._values
    def __init__(self, kicked=0, *args):
        ChannelStat.__init__(self, *args)
        self.kicked = kicked

    def doKick(self, msg):
        self.doPayload(msg.args[0], msg.args[2])
        self.kicks += 1

class StatsDB(plugins.ChannelUserDB):
    def __init__(self, *args, **kwargs):
        plugins.ChannelUserDB.__init__(self, *args, **kwargs)

    def serialize(self, v):
        return v.values()

    def deserialize(self, channel, id, L):
        L = list(map(int, L))
        if id == 'channelStats':
            return ChannelStat(*L)
        else:
            return UserStat(*L)

    def addMsg(self, irc, msg, id=None):
        if msg.channel:
            channel = plugins.getChannel(msg.channel)
            if (channel, 'channelStats') not in self:
                self[channel, 'channelStats'] = ChannelStat()
            self[channel, 'channelStats'].addMsg(msg)
            try:
                if id is None:
                    id = ircdb.users.getUserId(msg.prefix)
            except KeyError:
                return
            if (channel, id) not in self:
                self[channel, id] = UserStat()
            self[channel, id].addMsg(msg)

    def getChannelStats(self, channel):
        return self[channel, 'channelStats']

    def getUserStats(self, channel, id):
        return self[channel, id]

filename = conf.supybot.directories.data.dirize('ChannelStats.db')
class ChannelStats(callbacks.Plugin):
    """This plugin keeps stats of the channel and returns them with
    the command 'channelstats'."""
    noIgnore = True
    def __init__(self, irc):
        self.__parent = super(ChannelStats, self)
        self.__parent.__init__(irc)
        self.outFiltering = False
        self.db = StatsDB(filename)
        self._flush = self.db.flush
        world.flushers.append(self._flush)

    def die(self):
        world.flushers.remove(self._flush)
        self.db.close()
        self.__parent.die()

    def __call__(self, irc, msg):
        self.db.addMsg(irc, msg)
        super(ChannelStats, self).__call__(irc, msg)

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if msg.channel:
                if self.registryValue('selfStats', msg.channel, irc.network):
                    try:
                        self.outFiltering = True
                        self.db.addMsg(irc, msg, 0)
                    finally:
                        self.outFiltering = False
        return msg

    def _setUsers(self, irc, channel):
        if (channel, 'channelStats') not in self.db:
            self.db[channel, 'channelStats'] = ChannelStat()
        oldUsers = self.db[channel, 'channelStats'].users
        newUsers = len(irc.state.channels[channel].users)
        self.db[channel, 'channelStats'].users = max(oldUsers, newUsers)

    def doJoin(self, irc, msg):
        self._setUsers(irc, msg.args[0])

    def do366(self, irc, msg):
        self._setUsers(irc, msg.args[1])

    def doQuit(self, irc, msg):
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            id = None
        for channel in msg.tagged('channels'):
            if (channel, 'channelStats') not in self.db:
                self.db[channel, 'channelStats'] = ChannelStat()
            self.db[channel, 'channelStats'].quits += 1
            if id is not None:
                if (channel, id) not in self.db:
                    self.db[channel, id] = UserStat()
                self.db[channel, id].quits += 1

    def doKick(self, irc, msg):
        (channel, nick, _) = msg.args
        hostmask = irc.state.nickToHostmask(nick)
        try:
            id = ircdb.users.getUserId(hostmask)
        except KeyError:
            return
        if (channel, id) not in self.db:
            self.db[channel, id] = UserStat()
        self.db.channels[channel][id].kicked += 1

    @internationalizeDocstring
    def stats(self, irc, msg, args, channel, name):
        """[<channel>] [<name>]

        Returns the statistics for <name> on <channel>.  <channel> is only
        necessary if the message isn't sent on the channel itself.  If <name>
        isn't given, it defaults to the user sending the command.
        """
        if channel != '#':
            # Skip this check if databases.plugins.channelspecific is False.
            if msg.nick not in irc.state.channels[channel].users:
                irc.error(format('You must be in %s to use this command.', channel))
                return
        if name and ircutils.strEqual(name, irc.nick):
            id = 0
        elif not name:
            try:
                id = ircdb.users.getUserId(msg.prefix)
                name = ircdb.users.getUser(id).name
            except KeyError:
                irc.error(_('I couldn\'t find you in my user database.'))
                return
        elif not ircdb.users.hasUser(name):
            try:
                hostmask = irc.state.nickToHostmask(name)
                id = ircdb.users.getUserId(hostmask)
            except KeyError:
                irc.errorNoUser()
                return
        else:
            id = ircdb.users.getUserId(name)
        try:
            stats = self.db.getUserStats(channel, id)
            s = format(_('%s has sent %n; a total of %n, %n, '
                       '%n, and %n; %s of those messages %s. '
                       '%s has joined %n, parted %n, quit %n, '
                       'kicked someone %n, been kicked %n, '
                       'changed the topic %n, and changed the '
                       'mode %n.'),
                       name, (stats.msgs, 'message'),
                       (stats.chars, _('character')),
                       (stats.words, _('word')),
                       (stats.smileys, _('smiley')),
                       (stats.frowns, _('frown')),
                       stats.actions,
                       stats.actions == 1 and _('was an ACTION')
                                           or _('were ACTIONs'),
                       name,
                       (stats.joins, _('time')),
                       (stats.parts, _('time')),
                       (stats.quits, _('time')),
                       (stats.kicks, _('time')),
                       (stats.kicked, _('time')),
                       (stats.topics, _('time')),
                       (stats.modes, _('time')))
            irc.reply(s)
        except KeyError:
            irc.error(format(_('I have no stats for that %s in %s.'),
                             name, channel))
    stats = wrap(stats, ['channeldb', additional('something')])

    @internationalizeDocstring
    def rank(self, irc, msg, args, channel, expr):
        """[<channel>] <stat expression>

        Returns the ranking of users according to the given stat expression.
        Valid variables in the stat expression include 'msgs', 'chars',
        'words', 'smileys', 'frowns', 'actions', 'joins', 'parts', 'quits',
        'kicks', 'kicked', 'topics', and 'modes'.  Any simple mathematical
        expression involving those variables is permitted.
        """
        if channel != '#':
            # Skip this check if databases.plugins.channelspecific is False.
            if msg.nick not in irc.state.channels[channel].users:
                irc.error(format('You must be in %s to use this command.', channel))
                return
        expr = expr.lower()
        users = []
        for ((c, id), stats) in self.db.items():
            if ircutils.strEqual(c, channel) and \
               (id == 0 or ircdb.users.hasUser(id)):
                e = {}
                for attr in stats._values:
                    e[attr] = float(getattr(stats, attr))
                try:
                    v = safe_eval(expr, allow_ints=True, variables=e)
                except ZeroDivisionError:
                    v = float('inf')
                except NameError as e:
                    irc.errorInvalid(_('stat variable'), str(e))
                except InvalidNode as e:
                    irc.error(_('Invalid syntax: %s') % e.args[0], Raise=True)
                except Exception as e:
                    irc.error(utils.exnToString(e), Raise=True)
                else:
                    v = float(v)
                if id == 0:
                    users.append((v, irc.nick))
                else:
                    users.append((v, ircdb.users.getUser(id).name))
        users.sort()
        users.reverse()
        s = utils.str.commaAndify(['#%s %s (%.3g)' % (i+1, u, v)
                                   for (i, (v, u)) in enumerate(users)])
        irc.reply(s)
    rank = wrap(rank, ['channeldb', 'text'])

    @internationalizeDocstring
    def channelstats(self, irc, msg, args, channel):
        """[<channel>]

        Returns the statistics for <channel>.  <channel> is only necessary if
        the message isn't sent on the channel itself.
        """
        if channel not in irc.state.channels:
            irc.error(_('I am not in %s.') % channel, Raise=True)
        elif msg.nick not in irc.state.channels[channel].users:
            irc.error(_('You must be in %s to use this command.') % channel,
                    Raise=True)
        try:
            channeldb = conf.supybot.databases.plugins.channelSpecific. \
                    getChannelLink(channel)
            stats = self.db.getChannelStats(channeldb)
            curUsers = len(irc.state.channels[channel].users)
            s = format(_('On %s there %h been %i messages, containing %i '
                       'characters, %n, %n, and %n; '
                       '%i of those messages %s.  There have been '
                       '%n, %n, %n, %n, %n, and %n.  There %b currently %n '
                       'and the channel has peaked at %n.'),
                       channel, stats.msgs, stats.msgs, stats.chars,
                       (stats.words, _('word')),
                       (stats.smileys, _('smiley')),
                       (stats.frowns, _('frown')),
                       stats.actions, stats.actions == 1 and _('was an ACTION')
                                                          or _('were ACTIONs'),
                       (stats.joins, _('join')),
                       (stats.parts, _('part')),
                       (stats.quits, _('quit')),
                       (stats.kicks, _('kick')),
                       (stats.modes, _('mode'), _('change')),
                       (stats.topics, _('topic'), _('change')),
                       curUsers,
                       (curUsers, _('user')),
                       (stats.users, _('user')))
            irc.reply(s)
        except KeyError:
            irc.error(format(_('I\'ve never been on %s.'), channel))
    channelstats = wrap(channelstats, ['channel'])


Class = ChannelStats

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
