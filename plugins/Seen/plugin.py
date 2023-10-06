###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010-2011, 2013, James McCoy
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
import sys
import time

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.irclib as irclib
import supybot.utils.minisix as minisix
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Seen')

class IrcStringAndIntDict(utils.InsensitivePreservingDict):
    def key(self, x):
        if isinstance(x, int):
            return x
        else:
            return ircutils.toLower(x)

class SeenDB(plugins.ChannelUserDB):
    IdDict = IrcStringAndIntDict
    def serialize(self, v):
        return list(v)

    def deserialize(self, channel, id, L):
        (seen, saying) = L
        return (float(seen), saying)

    def update(self, channel, nickOrId, saying):
        seen = time.time()
        self[channel, nickOrId] = (seen, saying)
        self[channel, '<last>'] = (seen, saying)

    def seenWildcard(self, channel, nick):
        nicks = ircutils.IrcSet()
        nickRe = re.compile('^%s$' % '.*'.join(nick.split('*')), re.I)
        for (searchChan, searchNick) in self.keys():
            #print 'chan: %s ... nick: %s' % (searchChan, searchNick)
            if isinstance(searchNick, int):
                # We need to skip the reponses that are keyed by id as they
                # apparently duplicate the responses for the same person that
                # are keyed by nick-string
                continue
            if ircutils.strEqual(searchChan, channel):
                if nickRe.search(searchNick) is not None:
                    nicks.add(searchNick)
        L = [[nick, self.seen(channel, nick)] for nick in nicks]
        def negativeTime(x):
            return -x[1][0]
        utils.sortBy(negativeTime, L)
        return L

    def seen(self, channel, nickOrId):
        return self[channel, nickOrId]

filename = conf.supybot.directories.data.dirize('Seen.db')
anyfilename = conf.supybot.directories.data.dirize('Seen.any.db')

class Seen(callbacks.Plugin):
    """This plugin allows you to see when and what someone last said and
    what you missed since you left a channel."""
    noIgnore = True
    def __init__(self, irc):
        self.__parent = super(Seen, self)
        self.__parent.__init__(irc)
        self.db = SeenDB(filename)
        self.anydb = SeenDB(anyfilename)
        self.lastmsg = {}
        world.flushers.append(self.db.flush)
        world.flushers.append(self.anydb.flush)

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        else:
            self.log.debug('Odd, no flush in flushers: %r', world.flushers)
        self.db.close()
        if self.anydb.flush in world.flushers:
            world.flushers.remove(self.anydb.flush)
        else:
            self.log.debug('Odd, no flush in flushers: %r', world.flushers)
        self.anydb.close()
        self.__parent.die()

    def __call__(self, irc, msg):
        self.__parent.__call__(irc, msg)

    def doPrivmsg(self, irc, msg):
        if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
            return
        if msg.channel:
            channel = msg.channel
            said = ircmsgs.prettyPrint(msg)
            self.db.update(channel, msg.nick, said)
            self.anydb.update(channel, msg.nick, said)
            try:
                id = ircdb.users.getUserId(msg.prefix)
                self.db.update(channel, id, said)
                self.anydb.update(channel, id, said)
            except KeyError:
                pass # Not in the database.

    def doPart(self, irc, msg):
        channel = msg.args[0]
        said = ircmsgs.prettyPrint(msg)
        self.anydb.update(channel, msg.nick, said)
        try:
            id = ircdb.users.getUserId(msg.prefix)
            self.anydb.update(channel, id, said)
        except KeyError:
            pass # Not in the database.
    doJoin = doPart
    doKick = doPart

    def doQuit(self, irc, msg):
        said = ircmsgs.prettyPrint(msg)
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            id = None # Not in the database.
        for channel in msg.tagged('channels'):
            self.anydb.update(channel, msg.nick, said)
            if id is not None:
                self.anydb.update(channel, id, said)
    doNick = doQuit

    def doMode(self, irc, msg):
        # Filter out messages from network Services
        if msg.nick:
            try:
                id = ircdb.users.getUserId(msg.prefix)
            except KeyError:
                id = None # Not in the database.
            channel = msg.args[0]
            said = ircmsgs.prettyPrint(msg)
            self.anydb.update(channel, msg.nick, said)
            if id is not None:
                self.anydb.update(channel, id, said)
    doTopic = doMode

    def _seen(self, irc, channel, name, any=False):
        if any:
            db = self.anydb
        else:
            db = self.db
        try:
            results = []
            if '*' in name:
                if (len(name.replace('*', '')) <
                        self.registryValue('minimumNonWildcard',
                                           channel, irc.network)):
                    irc.error(_('Not enough non-wildcard characters.'),
                            Raise=True)
                results = db.seenWildcard(channel, name)
            else:
                results = [[name, db.seen(channel, name)]]
            if len(results) == 1:
                (nick, info) = results[0]
                (when, said) = info
                if nick in irc.state.channels[channel].users:
                    reply = format(_('%s was last seen in %s %s ago, and is in the channel now'),
                                     nick, channel,
                                     utils.timeElapsed(time.time()-when))
                else:
                    reply = format(_('%s was last seen in %s %s ago'),
                                     nick, channel,
                                     utils.timeElapsed(time.time()-when))
                if self.registryValue('showLastMessage', channel, irc.network):
                    if minisix.PY2:
                        said = said.decode('utf8')
                    reply = _('%s: %s') % (reply, said)
                irc.reply(reply)
            elif len(results) > 1:
                L = []
                for (nick, info) in results:
                    (when, said) = info
                    if nick in irc.state.channels[channel].users:
                        L.append(format(_('%s (%s ago, and is in the channel now)'), nick,
                                        utils.timeElapsed(time.time()-when)))
                    else:
                        L.append(format(_('%s (%s ago)'), nick,
                                        utils.timeElapsed(time.time()-when)))
                irc.reply(format(_('%s could be %L'), name, (L, _('or'))))
            else:
                irc.reply(format(_('I haven\'t seen anyone matching %s.'), name))
        except KeyError:
            if name in irc.state.channels[channel].users:
                irc.reply(format(_("%s is in the channel right now."), name))
            else:
                irc.reply(format(_('I have not seen %s.'), name))

    def _checkChannelPresence(self, irc, channel, target, you):
        if channel not in irc.state.channels:
            irc.error(_("I'm not in %s." % channel), Raise=True)
        if target not in irc.state.channels[channel].users:
            if you:
                msg = format(_('You must be in %s to use this command.'), channel)
            else:
                msg = format(_('%s must be in %s to use this command.'),
                        target, channel)
            irc.error(msg, Raise=True)

    @internationalizeDocstring
    def seen(self, irc, msg, args, channel, name):
        """[<channel>] <nick>

        Returns the last time <nick> was seen and what <nick> was last seen
        saying. <channel> is only necessary if the message isn't sent on the
        channel itself. <nick> may contain * as a wildcard.
        """
        if name and ircutils.strEqual(name, irc.nick):
            irc.reply(_("You've found me!"))
            return
        self._checkChannelPresence(irc, channel, msg.nick, True)
        self._seen(irc, channel, name)
    seen = wrap(seen, ['channel', 'something'])

    @internationalizeDocstring
    def any(self, irc, msg, args, channel, optlist, name):
        """[<channel>] [--user <name>] [<nick>]

        Returns the last time <nick> was seen and what <nick> was last seen
        doing.  This includes any form of activity, instead of just PRIVMSGs.
        If <nick> isn't specified, returns the last activity seen in
        <channel>.  If --user is specified, looks up name in the user database
        and returns the last time user was active in <channel>.  <channel> is
        only necessary if the message isn't sent on the channel itself.
        """
        if name and ircutils.strEqual(name, irc.nick):
            irc.reply(_("You've found me!"))
            return
        self._checkChannelPresence(irc, channel, msg.nick, True)
        if name and optlist:
            raise callbacks.ArgumentError
        elif name:
            self._seen(irc, channel, name, any=True)
        elif optlist:
            for (option, arg) in optlist:
                if option == 'user':
                    user = arg
            self._user(irc, channel, user, any=True)
        else:
            self._last(irc, channel, any=True)
    any = wrap(any, ['channel', getopts({'user': 'otherUser'}),
                     additional('something')])

    def _last(self, irc, channel, any=False):
        if any:
            db = self.anydb
        else:
            db = self.db
        try:
            (when, said) = db.seen(channel, '<last>')
            pattern = r'<(.*?)>'
            match = re.search(pattern, said)
            if not match:
                irc.error(format(_('I couldn\'t parse the nick of the speaker of the last line.')), Raise=True)
            nick = match.group(1)
            reply = format(_('Last seen in %s was %s, %s ago'),
                 channel, nick, utils.timeElapsed(time.time()-when))
            if self.registryValue('showLastMessage', channel, irc.network):
                reply = _('%s: %s') % (reply, said)
            irc.reply(reply)
        except KeyError:
            irc.reply(_('I have never seen anyone.'))

    @internationalizeDocstring
    def last(self, irc, msg, args, channel):
        """[<channel>]

        Returns the last thing said in <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        self._checkChannelPresence(irc, channel, msg.nick, True)
        self._last(irc, channel)
    last = wrap(last, ['channel'])

    def _user(self, irc, channel, user, any=False):
        if any:
            db = self.anydb
        else:
            db = self.db
        try:
            (when, said) = db.seen(channel, user.id)
            if user.name in irc.state.channels[channel].users:
                reply = format(_('%s was last seen in %s %s ago and is in the channel now'),
                                 user.name, channel,
                                 utils.timeElapsed(time.time()-when))
            else:
                reply = format(_('%s was last seen in %s %s ago'),
                                 user.name, channel,
                                 utils.timeElapsed(time.time()-when))
            if self.registryValue('showLastMessage', channel, irc.network):
                reply = _('%s: %s') % (reply, said)
            irc.reply(reply)
        except KeyError:
            if user.name in irc.state.channels[channel].users:
                irc.reply(format(_("%s is in the channel right now."), user.name))
            else:
                irc.reply(format(_('I have not seen %s.'), user.name))

    @internationalizeDocstring
    def user(self, irc, msg, args, channel, user):
        """[<channel>] <name>

        Returns the last time <name> was seen and what <name> was last seen
        saying.  This looks up <name> in the user seen database, which means
        that it could be any nick recognized as user <name> that was seen.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        self._checkChannelPresence(irc, channel, msg.nick, True)
        self._user(irc, channel, user)
    user = wrap(user, ['channel', 'otherUser'])

    @internationalizeDocstring
    def since(self, irc, msg, args, channel,  nick):
        """[<channel>] [<nick>]

        Returns the messages since <nick> last left the channel.
        If <nick> is not given, it defaults to the nickname of the person
        calling the command.
        """
        if nick is None:
            nick = msg.nick
            you = True
        else:
            you = False
        self._checkChannelPresence(irc, channel, nick, you)
        if nick is None:
            nick = msg.nick
        end = None # By default, up until the most recent message.
        for (i, m) in utils.seq.renumerate(irc.state.history):
            if end is None and m.command == 'JOIN' and \
               ircutils.strEqual(m.args[0], channel) and \
               ircutils.strEqual(m.nick, nick):
                end = i
            if m.command == 'PART' and \
               ircutils.strEqual(m.nick, nick) and \
               ircutils.strEqual(m.args[0], channel):
                break
            elif m.command == 'QUIT' and ircutils.strEqual(m.nick, nick):
                # XXX We assume the person was in-channel at this point.
                break
            elif m.command == 'KICK' and \
                 ircutils.strEqual(m.args[1], nick) and \
                 ircutils.strEqual(m.args[0], channel):
                break
        else: # I never use this; it only kicks in when the for loop exited normally.
            irc.error(format(_('I couldn\'t find in my history of %s messages '
                             'where %r last left %s'),
                             len(irc.state.history), nick, channel))
            return
        msgs = [m for m in irc.state.history[i:end]
                if m.command == 'PRIVMSG' and ircutils.strEqual(m.args[0], channel)]
        if msgs:
            irc.reply(format('%L', list(map(ircmsgs.prettyPrint, msgs))))
        else:
            irc.reply(format(_('Either %s didn\'t leave, '
                             'or no messages were sent while %s was gone.'), nick, nick))
    since = wrap(since, ['channel', additional('nick')])

Class = Seen

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
