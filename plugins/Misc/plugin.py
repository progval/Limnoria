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
import sys
import time

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircdb as ircdb
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

from supybot.utils.iter import ifilter

class Misc(callbacks.Privmsg):
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
        # First, we check for invalidCommand floods.  This is rightfully done
        # here since this will be the last invalidCommand called, and thus it
        # will only be called if this is *truly* an invalid command.
        maximum = conf.supybot.abuse.flood.command.invalid.maximum()
        self.invalidCommands.enqueue(msg)
        if self.invalidCommands.len(msg) > maximum and \
           not ircdb.checkCapability(msg.prefix, 'owner'):
            punishment = conf.supybot.abuse.flood.command.invalid.punishment()
            banmask = '*!%s@%s' % (msg.user, msg.host)
            self.log.info('Ignoring %s for %s seconds due to an apparent '
                          'invalid command flood.', banmask, punishment)
            if tokens and tokens[0] == 'Error:':
                self.log.warning('Apparent error loop with another Supybot '
                                 'observed.  Consider ignoring this bot '
                                 'permanently.')
            ircdb.ignores.add(banmask, time.time() + punishment)
            irc.reply('You\'ve given me %s invalid commands within the last '
                      'minute; I\'m now ignoring you for %s.' %
                      (maximum,
                       utils.gen.timeElapsed(punishment, seconds=False)))
            return
        # Now, for normal handling.
        channel = msg.args[0]
        if conf.get(conf.supybot.reply.whenNotCommand, channel):
            command = tokens and tokens[0] or ''
            irc.errorInvalid('command', command, repr=False)
        else:
            if tokens:
                # echo [] will get us an empty token set, but there's no need
                # to log this in that case anyway, it being a nested command.
                self.log.info('Not replying to %s, not a command.' % tokens[0])
            if not isinstance(irc.irc, irclib.Irc):
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
                irc.error('That plugin exists, but it has no '
                          'commands with help.')
    list = wrap(list, [getopts({'private':''}), additional('plugin')])

    def apropos(self, irc, msg, args, s):
        """<string>

        Searches for <string> in the commands currently offered by the bot,
        returning a list of the commands containing that string.
        """
        commands = {}
        L = []
        for cb in irc.callbacks:
            if isinstance(cb, callbacks.Privmsg):
                for attr in dir(cb):
                    if s in attr and cb.isCommand(attr):
                        if attr == callbacks.canonicalName(attr):
                            commands.setdefault(attr, []).append(cb.name())
        for (key, names) in commands.iteritems():
            if len(names) == 1:
                L.append(key)
            else:
                for name in names:
                    L.append('%s %s' % (name, key))
        if L:
            L.sort()
            irc.reply(format('%L', L))
        else:
            irc.reply('No appropriate commands were found.')
    apropos = wrap(apropos, ['lowered'])

    def help(self, irc, msg, args, cb, command):
        """[<plugin>] [<command>]

        This command gives a useful description of what <command> does.
        <plugin> is only necessary if the command is in more than one plugin.
        """
        def getHelp(cb):
            if hasattr(cb, 'isCommand'):
                if cb.isCommand(command):
                    irc.reply(cb.getCommandHelp(command))
                else:
                    irc.error('There is no %s command in the %s plugin.' %
                              (command, cb.name()))
            else:
                irc.error('The %s plugin exists, but has no commands.' %
                          cb.name())
        if cb:
            if command:
                getHelp(cb)
            else:
                irc.reply(cb.getCommandHelp(cb.name()))
        elif command:
            cbs = irc.findCallbackForCommand(command)
            if not cbs:
                irc.error('There is no command %s.' % command)
            elif len(cbs) > 1:
                names = sorted([cb.name() for cb in cbs])
                irc.error(format('That command exists in the %L plugins.  '
                                 'Please specify exactly which plugin command '
                                 'you want help with.', names))
            else:
                getHelp(cbs[0])
        else:
            raise callbacks.ArgumentError
    help = wrap(help, [optional(('plugin', False)), additional('commandName')])

    def hostmask(self, irc, msg, args, nick):
        """[<nick>]

        Returns the hostmask of <nick>.  If <nick> isn't given, return the
        hostmask of the person giving the command.
        """
        if not nick:
            nick = msg.nick
        irc.reply(irc.state.nickToHostmask(nick))
    hostmask = wrap(hostmask, [additional('seenNick')])

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
        irc.reply('My source is at http://supybot.sf.net/')
    source = wrap(source)

    def plugin(self, irc, msg, args, command):
        """<command>

        Returns the plugin (or plugins) <command> is in.  If this command is
        nested, it returns only the plugin name(s).  If given as a normal
        command, it returns a more verbose, user-friendly response.
        """
        cbs = callbacks.findCallbackForCommand(irc, command)
        if cbs:
            names = [cb.name() for cb in cbs]
            names.sort()
            if irc.nested:
                irc.reply(format('%L', names))
            else:
                s = 'plugin'
                if len(names) > 1:
                    s = utils.str.pluralize(s)
                irc.reply(format('The %q command is available in the %L %s.',
                                 command, names, s))
        else:
            irc.error('There is no such command %s.' % command)
    plugin = wrap(plugin, ['commandName'])

    def author(self, irc, msg, args, cb):
        """<plugin>

        Returns the author of <plugin>.  This is the person you should talk to
        if you have ideas, suggestions, or other comments about a given plugin.
        """
        if cb is None:
            irc.error('That plugin does not seem to be loaded.')
            return
        module = sys.modules[cb.__class__.__module__]
        if hasattr(module, '__author__') and module.__author__:
            irc.reply(utils.web.mungeEmail(str(module.__author__)))
        else:
            irc.reply('That plugin doesn\'t have an author that claims it.')
    author = wrap(author, [('plugin')])

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
                chunk += format(' \x02(%n)\x0F', (len(L), 'message', 'more'))
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
        if ircutils.isChannel(msg.args[0]):
            predicates['in'] = lambda m: ircutils.strEqual(m.args[0],
                                                           msg.args[0])
        for (option, arg) in optlist:
            if option == 'from':
                def f(m, arg=arg):
                    return ircutils.hostmaskPatternEqual(arg, m.nick)
                predicates['from'] = f
            elif option == 'in':
                def f(m, arg=arg):
                    return ircutils.strEqual(m.args[0], arg)
                predicates['in'] = f
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
                        return arg.search(ircmsgs.unAction(m))
                    else:
                        return arg.search(m.args[1])
                predicates.setdefault('regexp', []).append(f)
            elif option == 'nolimit':
                nolimit = True
        iterable = ifilter(self._validLastMsg, reversed(irc.state.history))
        iterable.next() # Drop the first message.
        predicates = list(utils.iter.flatten(predicates.itervalues()))
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
        irc.reply(s, to=target, private=True)
    tell = wrap(tell, ['something', 'text'])

    def contributors(self, irc, msg, args, cb, nick):
        """<plugin> [<nick>]

        Replies with a list of people who made contributions to a given plugin.
        If <nick> is specified, that person's specific contributions will
        be listed.  Note: The <nick> is the part inside of the parentheses
        in the people listing.
        """
        def getShortName(authorInfo):
            """
            Take an Authors object, and return only the name and nick values
            in the format 'First Last (nick)'.
            """
            return '%(name)s (%(nick)s)' % authorInfo.__dict__
        def buildContributorsString(longList):
            """
            Take a list of long names and turn it into :
            shortname[, shortname and shortname].
            """
            L = [getShortName(n) for n in longList]
            return format('%L', L)
        def sortAuthors():
            """
            Sort the list of 'long names' based on the number of contributions
            associated with each.
            """
            L = module.__contributors__.items()
            def negativeSecondElement(x):
                return -len(x[1])
            utils.gen.sortBy(negativeSecondElement, L)
            return [t[0] for t in L]
        def buildPeopleString(module):
            """
            Build the list of author + contributors (if any) for the requested
            plugin.
            """
            head = 'The %s plugin' % cb.name()
            author = 'has not been claimed by an author'
            conjunction = 'and'
            contrib = 'has no contributors listed.'
            hasAuthor = False
            hasContribs = False
            if getattr(module, '__author__', None):
                author = 'was written by %s' % \
                    utils.web.mungeEmail(str(module.__author__))
                hasAuthor = True
            if getattr(module, '__contributors__', None):
                contribs = sortAuthors()
                if hasAuthor:
                    try:
                        contribs.remove(module.__author__)
                    except ValueError:
                        pass
                if contribs:
                    contrib = format('%s %h contributed to it.',
                                     buildContributorsString(contribs),
                                     len(contribs))
                    hasContribs = True
                elif hasAuthor:
                    contrib = 'has no additional contributors listed.'
            if hasContribs and not hasAuthor:
                conjunction = 'but'
            return ' '.join([head, author, conjunction, contrib])
        def buildPersonString(module):
            """
            Build the list of contributions (if any) for the requested person
            for the requested plugin
            """
            isAuthor = False
            authorInfo = getattr(supybot.authors, nick, None)
            if not authorInfo:
                return 'The nick specified (%s) is not a registered ' \
                       'contributor.' % nick
            fullName = utils.web.mungeEmail(str(authorInfo))
            contributions = []
            if hasattr(module, '__contributors__'):
                if authorInfo not in module.__contributors__:
                    return 'The %s plugin does not have \'%s\' listed as a ' \
                           'contributor.' % (cb.name(), nick)
                contributions = module.__contributors__[authorInfo]
            if getattr(module, '__author__', False) == authorInfo:
                isAuthor = True
            (nonCommands, commands) = utils.iter.partition(lambda s: ' ' in s,
                                                           contributions)
            results = []
            if commands:
                s = 'command'
                if len(commands) > 1:
                    s = utils.str.pluralize(s)
                results.append(format('the %L %s', commands, s))
            if nonCommands:
                results.append(format('the %L', nonCommands))
            if results and isAuthor:
                return format(
                        '%s wrote the %s plugin and also contributed %L.',
                        (fullName, cb.name(), results))
            elif results and not isAuthor:
                return format('%s contributed %L to the %s plugin.',
                              fullName, results, cb.name())
            elif isAuthor and not results:
                return '%s wrote the %s plugin' % (fullName, cb.name())
            # XXX Does this ever actually get reached?
            else:
                return '%s has no listed contributions for the %s plugin.' % \
                    (fullName, cb.name())
        # First we need to check and see if the requested plugin is loaded
        module = sys.modules[cb.__class__.__module__]
        if not nick:
            irc.reply(buildPeopleString(module))
        else:
            nick = ircutils.toLower(nick)
            irc.reply(buildPersonString(module))
    contributors = wrap(contributors, ['plugin', additional('nick')])

    def ping(self, irc, msg, args):
        """takes no arguments

        Checks to see if the bot is alive.
        """
        irc.reply('pong', prefixName=False)

Class = Misc

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
