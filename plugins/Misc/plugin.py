###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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
import sys
import time

import supybot

import supybot.conf as conf
from supybot import commands
import supybot.utils as utils
from supybot.commands import *
import supybot.ircdb as ircdb
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

from supybot.utils.iter import ifilter

class Misc(callbacks.Plugin):
    def __init__(self, irc):
        self.__parent = super(Misc, self)
        self.__parent.__init__(irc)
        self.invalidCommands = ircutils.FloodQueue(60)

    def callPrecedence(self, irc):
        return ([cb for cb in irc.callbacks if cb is not self], [])

    def invalidCommand(self, irc, msg, tokens):
        assert not msg.repliedTo, 'repliedTo msg in Misc.invalidCommand.'
        assert self is irc.callbacks[-1], 'Misc isn\'t last callback.'
        self.log.debug('Misc.invalidCommand called (tokens %s)', tokens)
        channel = msg.args[0]
        # Only bother with the invaildCommand flood handling if it's actually
        # enabled
        if conf.supybot.abuse.flood.command.invalid():
            # First, we check for invalidCommand floods.  This is rightfully done
            # here since this will be the last invalidCommand called, and thus it
            # will only be called if this is *truly* an invalid command.
            maximum = conf.supybot.abuse.flood.command.invalid.maximum()
            banmasker = conf.supybot.protocols.irc.banmask.makeBanmask
            self.invalidCommands.enqueue(msg)
            if self.invalidCommands.len(msg) > maximum and \
               not ircdb.checkCapability(msg.prefix, 'owner'):
                penalty = conf.supybot.abuse.flood.command.invalid.punishment()
                banmask = banmasker(msg.prefix)
                self.log.info('Ignoring %s for %s seconds due to an apparent '
                              'invalid command flood.', banmask, penalty)
                if tokens and tokens[0] == 'Error:':
                    self.log.warning('Apparent error loop with another Supybot '
                                     'observed.  Consider ignoring this bot '
                                     'permanently.')
                ircdb.ignores.add(banmask, time.time() + penalty)
                if conf.supybot.abuse.flood.command.invalid.notify():
                    irc.reply('You\'ve given me %s invalid commands within '
                              'the last minute; I\'m now ignoring you for %s.' %
                              (maximum,
                               utils.timeElapsed(penalty, seconds=False)))
                return
        # Now, for normal handling.
        if conf.get(conf.supybot.reply.whenNotCommand, channel):
            if len(tokens) >= 2:
                cb = irc.getCallback(tokens[0])
                if cb:
                    plugin = cb.name()
                    irc.error(format('The %q plugin is loaded, but there is '
                                     'no command named %q in it.  Try "list '
                                     '%s" to see the commands in the %q '
                                     'plugin.', plugin, tokens[1],
                                     plugin, plugin))
                else:
                    irc.errorInvalid('command', tokens[0], repr=False)
            else:
                command = tokens and tokens[0] or ''
                irc.errorInvalid('command', command, repr=False)
        else:
            if tokens:
                # echo [] will get us an empty token set, but there's no need
                # to log this in that case anyway, it being a nested command.
                self.log.info('Not replying to %s, not a command.', tokens[0])
            if irc.nested:
                bracketConfig = conf.supybot.commands.nested.brackets
                brackets = conf.get(bracketConfig, channel)
                if brackets:
                    (left, right) = brackets
                    irc.reply(left + ' '.join(tokens) + right)
                else:
                    pass # Let's just do nothing, I can't think of better.

    def list(self, irc, msg, args, optlist, cb):
        """[--private] [<plugin>]

        Lists the commands available in the given plugin.  If no plugin is
        given, lists the public plugins available.  If --private is given,
        lists the private plugins.
        """
        private = False
        for (option, argument) in optlist:
            if option == 'private':
                private = True
                if not self.registryValue('listPrivatePlugins') and \
                   not ircdb.checkCapability(msg.prefix, 'owner'):
                    irc.errorNoCapability('owner')
        if not cb:
            def isPublic(cb):
                name = cb.name()
                return conf.supybot.plugins.get(name).public()
            names = [cb.name() for cb in irc.callbacks
                     if (private and not isPublic(cb)) or
                        (not private and isPublic(cb))]
            names.sort()
            if names:
                irc.reply(format('%L', names))
            else:
                if private:
                    irc.reply('There are no private plugins.')
                else:
                    irc.reply('There are no public plugins.')
        else:
            commands = cb.listCommands()
            if commands:
                commands.sort()
                irc.reply(format('%L', commands))
            else:
                irc.reply(format('That plugin exists, but has no commands.  '
                                 'This probably means that it has some '
                                 'configuration variables that can be '
                                 'changed in order to modify its behavior.  '
                                 'Try "config list supybot.plugins.%s" to see '
                                 'what configuration variables it has.',
                                 cb.name()))
    list = wrap(list, [getopts({'private':''}), additional('plugin')])

    def apropos(self, irc, msg, args, s):
        """<string>

        Searches for <string> in the commands currently offered by the bot,
        returning a list of the commands containing that string.
        """
        commands = {}
        L = []
        for cb in irc.callbacks:
            if isinstance(cb, callbacks.Plugin):
                for command in cb.listCommands():
                    if s in command:
                        commands.setdefault(command, []).append(cb.name())
        for (key, names) in commands.iteritems():
            for name in names:
                L.append('%s %s' % (name, key))
        if L:
            L.sort()
            irc.reply(format('%L', L))
        else:
            irc.reply('No appropriate commands were found.')
    apropos = wrap(apropos, ['lowered'])

    def help(self, irc, msg, args, command):
        """[<plugin>] [<command>]

        This command gives a useful description of what <command> does.
        <plugin> is only necessary if the command is in more than one plugin.
        """
        command = map(callbacks.canonicalName, command)
        (maxL, cbs) = irc.findCallbacksForArgs(command)
        if maxL == command:
            if len(cbs) > 1:
                names = sorted([cb.name() for cb in cbs])
                irc.error(format('That command exists in the %L plugins.  '
                                 'Please specify exactly which plugin command '
                                 'you want help with.', names))
            else:
                assert cbs, 'Odd, maxL == command, but no cbs.'
                irc.reply(cbs[0].getCommandHelp(command, False))
        else:
            irc.error(format('There is no command %q.',
                             callbacks.formatCommand(command)))
    help = wrap(help, [many('something')])

    def version(self, irc, msg, args):
        """takes no arguments

        Returns the version of the current bot.
        """
        try:
            newest = utils.web.getUrl('http://supybot.sf.net/version.txt')
            newest ='The newest version available online is %s.'%newest.strip()
        except utils.web.Error, e:
            self.log.info('Couldn\'t get website version: %s', e)
            newest = 'I couldn\'t fetch the newest version ' \
                     'from the Supybot website.'
        s = 'The current (running) version of this Supybot is %s.  %s' % \
            (conf.version, newest)
        irc.reply(s)
    version = wrap(thread(version))

    def source(self, irc, msg, args):
        """takes no arguments

        Returns a URL saying where to get Supybot.
        """
        irc.reply('My source is at https://github.com/Supybot/Supybot')
    source = wrap(source)

    def more(self, irc, msg, args, nick):
        """[<nick>]

        If the last command was truncated due to IRC message length
        limitations, returns the next chunk of the result of the last command.
        If <nick> is given, it takes the continuation of the last command from
        <nick> instead of the person sending this message.
        """
        userHostmask = msg.prefix.split('!', 1)[1]
        if nick:
            try:
                (private, L) = irc._mores[nick]
                if not private:
                    irc._mores[userHostmask] = L[:]
                else:
                    irc.error('%s has no public mores.' % nick)
                    return
            except KeyError:
                irc.error('Sorry, I can\'t find any mores for %s' % nick)
                return
        try:
            L = irc._mores[userHostmask]
            chunk = L.pop()
            if L:
                chunk += format(' \x02(%n)\x0F', (len(L), 'more', 'message'))
            irc.reply(chunk, True)
        except KeyError:
            irc.error('You haven\'t asked me a command; perhaps you want '
                      'to see someone else\'s more.  To do so, call this '
                      'command with that person\'s nick.')
        except IndexError:
            irc.error('That\'s all, there is no more.')
    more = wrap(more, [additional('seenNick')])

    def _validLastMsg(self, msg):
        return msg.prefix and \
               msg.command == 'PRIVMSG' and \
               ircutils.isChannel(msg.args[0])

    def last(self, irc, msg, args, optlist):
        """[--{from,in,on,with,without,regexp} <value>] [--nolimit]

        Returns the last message matching the given criteria.  --from requires
        a nick from whom the message came; --in requires a channel the message
        was sent to; --on requires a network the message was sent on; --with
        requires some string that had to be in the message; --regexp requires
        a regular expression the message must match; --nolimit returns all
        the messages that can be found.  By default, the channel this command is
        given in is searched.
        """
        predicates = {}
        nolimit = False
        skipfirst = True
        if ircutils.isChannel(msg.args[0]):
            predicates['in'] = lambda m: ircutils.strEqual(m.args[0],
                                                           msg.args[0])
        else:
            skipfirst = False
        for (option, arg) in optlist:
            if option == 'from':
                def f(m, arg=arg):
                    return ircutils.hostmaskPatternEqual(arg, m.nick)
                predicates['from'] = f
            elif option == 'in':
                def f(m, arg=arg):
                    return ircutils.strEqual(m.args[0], arg)
                predicates['in'] = f
                if arg != msg.args[0]:
                    skipfirst = False
            elif option == 'on':
                def f(m, arg=arg):
                    return m.receivedOn == arg
                predicates['on'] = f
            elif option == 'with':
                def f(m, arg=arg):
                    return arg.lower() in m.args[1].lower()
                predicates.setdefault('with', []).append(f)
            elif option == 'without':
                def f(m, arg=arg):
                    return arg.lower() not in m.args[1].lower()
                predicates.setdefault('without', []).append(f)
            elif option == 'regexp':
                def f(m, arg=arg):
                    if ircmsgs.isAction(m):
                        m1 = ircmsgs.unAction(m)
                    else:
                        m1 = m.args[1]
                    return regexp_wrapper(m1, reobj=arg, timeout=0.1,
                                          plugin_name=self.name(),
                                          fcn_name='last')
                predicates.setdefault('regexp', []).append(f)
            elif option == 'nolimit':
                nolimit = True
        iterable = ifilter(self._validLastMsg, reversed(irc.state.history))
        if skipfirst:
            # Drop the first message only if our current channel is the same as
            # the channel we've been instructed to look at.
            iterable.next()
        predicates = list(utils.iter.flatten(predicates.itervalues()))
        # Make sure the user can't get messages from channels they aren't in
        def userInChannel(m):
            return m.args[0] in irc.state.channels \
                    and msg.nick in irc.state.channels[m.args[0]].users
        predicates.append(userInChannel)
        # Make sure the user can't get messages from a +s channel unless
        # they're calling the command from that channel or from a query
        def notSecretMsg(m):
            return not irc.isChannel(msg.args[0]) \
                    or msg.args[0] == m.args[0] \
                    or (m.args[0] in irc.state.channels \
                        and 's' not in irc.state.channels[m.args[0]].modes)
        predicates.append(notSecretMsg)
        resp = []
        if irc.nested and not \
          self.registryValue('last.nested.includeTimestamp'):
            tsf = None
        else:
            tsf = self.registryValue('timestampFormat')
        if irc.nested and not self.registryValue('last.nested.includeNick'):
            showNick = False
        else:
            showNick = True
        for m in iterable:
            for predicate in predicates:
                if not predicate(m):
                    break
            else:
                if nolimit:
                    resp.append(ircmsgs.prettyPrint(m,
                                                    timestampFormat=tsf,
                                                    showNick=showNick))
                else:
                    irc.reply(ircmsgs.prettyPrint(m,
                                                  timestampFormat=tsf,
                                                  showNick=showNick))
                    return
        if not resp:
            irc.error('I couldn\'t find a message matching that criteria in '
                      'my history of %s messages.' % len(irc.state.history))
        else:
            irc.reply(format('%L', resp))
    last = wrap(last, [getopts({'nolimit': '',
                                'on': 'something',
                                'with': 'something',
                                'from': 'something',
                                'without': 'something',
                                'in': 'callerInGivenChannel',
                                'regexp': 'regexpMatcher',})])


    def tell(self, irc, msg, args, target, text):
        """<nick> <text>

        Tells the <nick> whatever <text> is.  Use nested commands to your
        benefit here.
        """
        if irc.nested:
            irc.error('This command cannot be nested.', Raise=True)
        if target.lower() == 'me':
            target = msg.nick
        if ircutils.isChannel(target):
            irc.error('Dude, just give the command.  No need for the tell.')
            return
        if not ircutils.isNick(target):
            irc.errorInvalid('nick', target)
        if ircutils.nickEqual(target, irc.nick):
            irc.error('You just told me, why should I tell myself?',Raise=True)
        if target not in irc.state.nicksToHostmasks and \
             not ircdb.checkCapability(msg.prefix, 'owner'):
            # We'll let owners do this.
            s = 'I haven\'t seen %s, I\'ll let you do the telling.' % target
            irc.error(s, Raise=True)
        if irc.action:
            irc.action = False
            text = '* %s %s' % (irc.nick, text)
        s = '%s wants me to tell you: %s' % (msg.nick, text)
        irc.replySuccess()
        irc.reply(s, to=target, private=True)
    tell = wrap(tell, ['something', 'text'])

    def ping(self, irc, msg, args):
        """takes no arguments

        Checks to see if the bot is alive.
        """
        irc.reply('pong', prefixNick=False)

Class = Misc

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
