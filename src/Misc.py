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
Miscellaneous commands.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch
__contributors__ = {
    supybot.authors.skorobeus: ['contributors'],
    }

import supybot.fix as fix

import os
import sys
import time
import getopt
from itertools import imap, ifilter

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.webutils as webutils
import supybot.registry as registry
import supybot.callbacks as callbacks

conf.registerPlugin('Misc')
conf.registerGlobalValue(conf.supybot.plugins.Misc, 'listPrivatePlugins',
    registry.Boolean(True, """Determines whether the bot will list private
    plugins with the list command if given the --private switch.  If this is
    disabled, non-owner users should be unable to see what private plugins
    are loaded."""))
conf.registerGlobalValue(conf.supybot.plugins.Misc, 'timestampFormat',
    registry.String('[%H:%M:%S]', """Determines the format string for
    timestamps in the Misc.last command.  Refer to the Python documentation
    for the time module to see what formats are accepted. If you set this
    variable to the empty string, the timestamp will not be shown."""))

class Misc(callbacks.Privmsg):
    def __init__(self):
        super(Misc, self).__init__()
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
                                 'observed at %s.  Consider ignoring this bot '
                                 'permanently.', log.timestamp())
            ircdb.ignores.add(banmask, time.time() + punishment)
            irc.reply('You\'ve given me %s invalid commands within the last '
                      'minute; I\'m now ignoring you for %s.' %
                      (maximum, utils.timeElapsed(punishment, seconds=False)))
            return
        # Now, for normal handling.
        channel = msg.args[0]
        if conf.get(conf.supybot.reply.whenNotCommand, channel):
            command = tokens and tokens[0] or ''
            irc.errorInvalid('command', command)
        else:
            if tokens:
                # echo [] will get us an empty token set, but there's no need
                # to log this in that case anyway, it being a nested command.
                self.log.info('Not replying to %s, not a command.' % tokens[0])
            if not isinstance(irc.irc, irclib.Irc):
                brackets = conf.get(conf.supybot.reply.brackets, channel)
                if brackets:
                    (left, right) = brackets
                    irc.reply(left + ' '.join(tokens) + right)
                else:
                    pass # Let's just do nothing, I can't think of better.

    def list(self, irc, msg, args):
        """[--private] [<module name>]

        Lists the commands available in the given plugin.  If no plugin is
        given, lists the public plugins available.  If --private is given,
        lists the private plugins.
        """
        (optlist, rest) = getopt.getopt(args, '', ['private'])
        private = False
        for (option, argument) in optlist:
            if option == '--private':
                private = True
                if not self.registryValue('listPrivatePlugins') and \
                   not ircdb.checkCapability(msg.prefix, 'owner'):
                    irc.errorNoCapability('owner')
                    return
        name = privmsgs.getArgs(rest, required=0, optional=1)
        name = callbacks.canonicalName(name)
        if not name:
            def isPublic(cb):
                name = cb.name()
                return conf.supybot.plugins.get(name).public()
            names = [cb.name() for cb in irc.callbacks
                     if (private and not isPublic(cb)) or
                        (not private and isPublic(cb))]
            names.sort()
            if names:
                irc.reply(utils.commaAndify(names))
            else:
                if private:
                    irc.reply('There are no private plugins.')
                else:
                    irc.reply('There are no public plugins.')
        else:
            cb = irc.getCallback(name)
            if cb is None:
                irc.error('No such plugin %r exists.' % name)
            elif isinstance(cb, callbacks.PrivmsgRegexp) or \
                 not isinstance(cb, callbacks.Privmsg):
                irc.error('That plugin exists, but it has no commands.  '
                          'You may wish to check if it has any useful '
                          'configuration variables with the command '
                          '"config list supybot.plugins.%s".' % name)
            else:
                commands = []
                for s in dir(cb):
                    if cb.isCommand(s) and \
                       (s != name or cb._original) and \
                       s == callbacks.canonicalName(s):
                        method = getattr(cb, s)
                        if hasattr(method, '__doc__') and method.__doc__:
                            commands.append(s)
                if commands:
                    commands.sort()
                    irc.reply(utils.commaAndify(commands))
                else:
                    irc.error('That plugin exists, but it has no '
                              'commands with help.')

    def apropos(self, irc, msg, args):
        """<string>

        Searches for <string> in the commands currently offered by the bot,
        returning a list of the commands containing that string.
        """
        s = privmsgs.getArgs(args)
        commands = {}
        L = []
        for cb in irc.callbacks:
            if isinstance(cb, callbacks.Privmsg) and \
               not isinstance(cb, callbacks.PrivmsgRegexp):
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
            irc.reply(utils.commaAndify(L))
        else:
            irc.reply('No appropriate commands were found.')

    def help(self, irc, msg, args):
        """[<plugin>] <command>

        This command gives a useful description of what <command> does.
        <plugin> is only necessary if the command is in more than one plugin.
        """
        def getHelp(method, name=None):
            if hasattr(method, '__doc__') and method.__doc__:
                irc.reply(callbacks.getHelp(method, name=name))
            else:
                irc.error('%s has no help.' % name)
        if len(args) > 1:
            cb = irc.getCallback(args[0]) # No pop, we'll use this later.
            if cb is not None:
                command = callbacks.canonicalName(privmsgs.getArgs(args[1:]))
                prefixChars = conf.supybot.reply.whenAddressedBy.chars()
                command = command.lstrip(prefixChars)
                name = ' '.join(args)
                if hasattr(cb, 'isCommand') and cb.isCommand(command):
                    method = getattr(cb, command)
                    getHelp(method, name)
                else:
                    irc.error('There is no such command %s.' % name)
            else:
                irc.error('There is no such plugin %s.' % args[0])
            return
        name = privmsgs.getArgs(args)
        cb = irc.getCallback(name)
        if cb is not None and cb.__doc__ and not hasattr(cb, '_original'):
            irc.reply(utils.normalizeWhitespace(cb.__doc__))
            return
        command = callbacks.canonicalName(name)
        # Users might expect "@help @list" to work.
        # command = command.lstrip(conf.supybot.reply.whenAddressedBy.chars())
        cbs = callbacks.findCallbackForCommand(irc, command)
        if len(cbs) > 1:
            tokens = [command]
            ambiguous = {}
            Owner = irc.getCallback('Owner')
            Owner.disambiguate(irc, tokens, ambiguous)
            if ambiguous:
                names = [cb.name() for cb in cbs]
                names.sort()
                irc.error('That command exists in the %s plugins.  '
                          'Please specify exactly which plugin command '
                          'you want help with.'% utils.commaAndify(names))
                return
            else:
                if len(tokens) == 1:
                    # It's a src plugin that wasn't disambiguated.
                    tokens.append(tokens[0])
                assert len(tokens) == 2, tokens
                cb = irc.getCallback(tokens[0])
                method = getattr(cb, tokens[1])
                getHelp(method)
        elif not cbs:
            irc.error('There is no such command %s.' % command)
        else:
            cb = cbs[0]
            method = getattr(cb, command)
            getHelp(method)

    def hostmask(self, irc, msg, args):
        """[<nick>]

        Returns the hostmask of <nick>.  If <nick> isn't given, return the
        hostmask of the person giving the command.
        """
        nick = privmsgs.getArgs(args, required=0, optional=1)
        if nick:
            try:
                irc.reply(irc.state.nickToHostmask(nick))
            except KeyError:
                irc.error('I haven\'t seen anyone named %r' % nick)
        else:
            irc.reply(msg.prefix)

    def version(self, irc, msg, args):
        """takes no arguments

        Returns the version of the current bot.
        """
        try:
            newest = webutils.getUrl('http://supybot.sf.net/version.txt')
            newest ='The newest version available online is %s.'%newest.strip()
        except webutils.WebError, e:
            self.log.warning('Couldn\'t get website version: %r', e)
            newest = 'I couldn\'t fetch the newest version ' \
                     'from the Supybot website.'
        s = 'The current (running) version of this Supybot is %s.  %s' % \
            (conf.version, newest)
        irc.reply(s)
    version = privmsgs.thread(version)

    def revision(self, irc, msg, args):
        """[<module>]

        Gives the latest revision of <module>.  If <module> isn't given, gives
        the revision of all Supybot modules.
        """
        def normalize(name):
            if name.endswith('.py'):
                name = name[:-3]
            return name
        def getRevisionNumber(module, name):
            def getVersion(s, n):
                try:
                    return s.split(None, 3)[2]
                except:
                    self.log.exception('Getting %s module\'s revision number '
                                       'from __revision__ string: %s', n, s)
            if hasattr(module, '__revision__'):
                if 'supybot' in module.__file__:
                    return getVersion(module.__revision__, name)
                else:
                    for dir in conf.supybot.directories.plugins():
                        if module.__file__.startswith(dir):
                            return getVersion(module.__revision__, name)
        if len(args) == 1 and '*' not in args[0] and '?' not in args[0]:
            # wildcards are handled below.
            name = normalize(args[0])
            try:
                def startsWithPluginsDir(filename):
                    for dir in conf.supybot.directories.plugins():
                        if filename.startswith(dir):
                            return True
                    return False
                modules = {}
                for (moduleName, module) in sys.modules.iteritems():
                    if hasattr(module, '__file__'):
                        if startsWithPluginsDir(module.__file__):
                            modules[moduleName.lower()] = moduleName
                try:
                    module = sys.modules[name]
                    if not startsWithPluginsDir(module.__file__):
                        raise KeyError
                except KeyError:
                    try:
                        module = sys.modules[modules[name.lower()]]
                        if not startsWithPluginsDir(module.__file__):
                            raise KeyError
                    except KeyError:
                        module = sys.modules[name.lower()]
                        if not startsWithPluginsDir(module.__file__):
                            raise KeyError
            except KeyError:
                irc.error('I couldn\'t find a Supybot module named %s.' % name)
                return
            if hasattr(module, '__revision__'):
                irc.reply(module.__revision__)
            else:
                irc.error('Module %s has no __revision__ string.' % name)
        else:
            names = []
            if not args:
                # I shouldn't use iteritems here for some reason.
                for (name, module) in sys.modules.items():
                    names.append((name, getRevisionNumber(module, name)))
            elif len(args) == 1: # wildcards
                pattern = args[0]
                for (name, module) in sys.modules.items():
                    if ircutils.hostmaskPatternEqual(pattern, name):
                        names.append((name, getRevisionNumber(module, name)))
            else:
                for name in args:
                    name = normalize(name)
                    if name not in sys.modules:
                        irc.error('I couldn\'t find a Supybot named %s.'%name)
                        return
                    module = sys.modules[name]
                    names.append((name, getRevisionNumber(module, name)))
            names.sort()
            L = ['%s: %s' % (k, v) for (k, v) in names if v]
            irc.reply(utils.commaAndify(L))

    def source(self, irc, msg, args):
        """takes no arguments

        Returns a URL saying where to get Supybot.
        """
        irc.reply('My source is at http://supybot.sf.net/')

    def plugin(self, irc, msg, args):
        """<command>

        Returns the plugin <command> is in.
        """
        command = callbacks.canonicalName(privmsgs.getArgs(args))
        cbs = callbacks.findCallbackForCommand(irc, command)
        if cbs:
            names = [cb.name() for cb in cbs]
            names.sort()
            irc.reply(utils.commaAndify(names))
        else:
            irc.error('There is no such command %s.' % command)

    def author(self, irc, msg, args):
        """<plugin>

        Returns the author of <plugin>.  This is the person you should talk to
        if you have ideas, suggestions, or other comments about a given plugin.
        """
        plugin = privmsgs.getArgs(args)
        cb = irc.getCallback(plugin)
        if cb is None:
            irc.error('That plugin does not seem to be loaded.')
            return
        module = sys.modules[cb.__class__.__module__]
        if hasattr(module, '__author__') and module.__author__:
            irc.reply(utils.mungeEmailForWeb(module.__author__))
        else:
            irc.reply('That plugin doesn\'t have an author that claims it.')

    def more(self, irc, msg, args):
        """[<nick>]

        If the last command was truncated due to IRC message length
        limitations, returns the next chunk of the result of the last command.
        If <nick> is given, it takes the continuation of the last command from
        <nick> instead of the person sending this message.
        """
        nick = privmsgs.getArgs(args, required=0, optional=1)
        userHostmask = msg.prefix.split('!', 1)[1]
        if nick:
            try:
                (private, L) = self._mores[nick]
                if not private:
                    self._mores[userHostmask] = L[:]
                else:
                    irc.error('%s has no public mores.' % nick)
                    return
            except KeyError:
                irc.error('Sorry, I can\'t find any mores for %s' % nick)
                return
        try:
            L = self._mores[userHostmask]
            chunk = L.pop()
            if L:
                chunk += ' \x02(%s)\x0F' % \
                         utils.nItems('message', len(L), 'more')
            irc.reply(chunk, True)
        except KeyError:
            irc.error('You haven\'t asked me a command!')
        except IndexError:
            irc.error('That\'s all, there is no more.')

    def _validLastMsg(self, msg):
        return msg.prefix and \
               msg.command == 'PRIVMSG' and \
               ircutils.isChannel(msg.args[0])

    def last(self, irc, msg, args):
        """[--{from,in,on,with,without,regexp,nolimit}] <args>

        Returns the last message matching the given criteria.  --from requires
        a nick from whom the message came; --in requires a channel the message
        was sent to; --on requires a netowkr the message was sent on; --with
        requires some string that had to be in the message; --regexp requires
        a regular expression the message must i match; --nolimit returns all
        the messages that can be found.  By default, the current channel is
        searched.
        """
        (optlist, rest) = getopt.getopt(args, '', ['from=', 'in=', 'on=',
                                                   'with=', 'regexp=',
                                                   'without=', 'nolimit'])
        predicates = {}
        nolimit = False
        if ircutils.isChannel(msg.args[0]):
            predicates['in'] = lambda m: ircutils.strEqual(m.args[0],
                                                           msg.args[0])
        predicates['on'] = lambda m: m.receivedOn == msg.receivedOn
        for (option, arg) in optlist:
            if option == '--from':
                def f(m, arg=arg):
                    return ircutils.hostmaskPatternEqual(arg, m.nick)
                predicates['from'] = f
            elif option == '--in':
                def f(m, arg=arg):
                    return ircutils.strEqual(m.args[0], arg)
                predicates['in'] = f
            elif option == '--on':
                def f(m, arg=arg):
                    return m.receivedOn == arg
                predicates['on'] = f
            elif option == '--with':
                def f(m, arg=arg):
                    return arg.lower() in m.args[1].lower()
                predicates.setdefault('with', []).append(f)
            elif option == '--without':
                def f(m, arg=arg):
                    return arg.lower() not in m.args[1].lower()
                predicates.setdefault('without', []).append(f)
            elif option == '--regexp':
                try:
                    r = utils.perlReToPythonRe(arg)
                    def f(m, r=r):
                        if ircmsgs.isAction(m):
                            return r.search(ircmsgs.unAction(m))
                        else:
                            return r.search(m.args[1])
                    predicates.setdefault('regexp', []).append(f)
                except ValueError, e:
                    irc.error(str(e))
                    return
            elif option == '--nolimit':
                nolimit = True
        iterable = ifilter(self._validLastMsg, reversed(irc.state.history))
        iterable.next() # Drop the first message.
        predicates = list(utils.flatten(predicates.itervalues()))
        resp = []
        tsf = self.registryValue('timestampFormat')
        for m in iterable:
            for predicate in predicates:
                if not predicate(m):
                    break
            else:
                if nolimit:
                    resp.append(ircmsgs.prettyPrint(m, timestampFormat=tsf))
                else:
                    irc.reply(ircmsgs.prettyPrint(m, timestampFormat=tsf))
                    return
        if not resp:
            irc.error('I couldn\'t find a message matching that criteria in '
                      'my history of %s messages.' % len(irc.state.history))
        else:
            irc.reply(utils.commaAndify(resp))

    def tell(self, irc, msg, args):
        """<nick> <text>

        Tells the <nick> whatever <text> is.  Use nested commands to your
        benefit here.
        """
        (target, text) = privmsgs.getArgs(args, required=2)
        if target.lower() == 'me':
            target = msg.nick
        elif ircutils.isChannel(target):
            irc.error('Dude, just give the command.  No need for the tell.')
            return
        elif not ircutils.isNick(target):
            irc.errorInvalid('nick', target, Raise=True)
        elif ircutils.nickEqual(target, irc.nick):
            irc.error('You just told me, why should I tell myself?',Raise=True)
        elif target not in irc.state.nicksToHostmasks and \
             not ircdb.checkCapability(msg.prefix, 'owner'):
            # We'll let owners do this.
            s = 'I haven\'t seen %s, I\'ll let you do the telling.' % target
            irc.error(s)
            return
        if irc.action:
            irc.action = False
            text = '* %s %s' % (irc.nick, text)
        s = '%s wants me to tell you: %s' % (msg.nick, text)
        irc.reply(s, to=target, private=True)

    def private(self, irc, msg, args):
        """<text>

        Replies with <text> in private.  Use nested commands to your benefit
        here.
        """
        text = privmsgs.getArgs(args)
        irc.reply(text, private=True)

    def action(self, irc, msg, args):
        """<text>

        Replies with <text> as an action.  use nested commands to your benefit
        here.
        """
        text = privmsgs.getArgs(args)
        if text:
            irc.reply(text, action=True)
        else:
            raise callbacks.ArgumentError

    def notice(self, irc, msg, args):
        """<text>

        Replies with <text> in a notice.  Use nested commands to your benefit
        here.  If you want a private notice, nest the private command.
        """
        text = privmsgs.getArgs(args)
        irc.reply(text, notice=True)

    def contributors(self, irc, msg, args):
        """<plugin> [<nick>]

        Replies with a list of people who made contributions to a given plugin.
        If <nick> is specified, that person's specific contributions will
        be listed.  Note: The <nick> is the part inside of the parentheses
        in the people listing.
        """
        (plugin, nick) = privmsgs.getArgs(args, required=1, optional=1)
        nick = nick.lower()
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
            return utils.commaAndify(L)
        def sortAuthors():
            """
            Sort the list of 'long names' based on the number of contributions
            associated with each.
            """
            L = module.__contributors__.items()
            def negativeSecondElement(x):
                return -len(x[1])
            utils.sortBy(negativeSecondElement, L)
            return [t[0] for t in L]
        def buildPeopleString(module):
            """
            Build the list of author + contributors (if any) for the requested
            plugin.
            """
            head = 'The %s plugin' % plugin
            author = 'has not been claimed by an author'
            conjunction = 'and'
            contrib = 'has no contributors listed'
            hasAuthor = False
            hasContribs = False
            if getattr(module, '__author__', None):
                author = 'was written by %s' % \
                    utils.mungeEmailForWeb(str(module.__author__))
                hasAuthor = True
            if getattr(module, '__contributors__', None):
                contribs = sortAuthors()
                if hasAuthor:
                    try:
                        contribs.remove(module.__author__)
                    except ValueError:
                        pass
                if contribs:
                    contrib = '%s %s contributed to it.' % \
                        (buildContributorsString(contribs),
                        utils.has(len(contribs)))
                    hasContribs = True
                elif hasAuthor:
                    contrib = 'has no additional contributors listed'
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
                       'contributor' % nick
            fullName = utils.mungeEmailForWeb(str(authorInfo))
            contributions = []
            if hasattr(module, '__contributors__'):
                if authorInfo not in module.__contributors__:
                    return 'The %s plugin does not have \'%s\' listed as a ' \
                           'contributor' % (plugin, nick)
                contributions = module.__contributors__[authorInfo]
            if getattr(module, '__author__', False) == authorInfo:
                isAuthor = True
            # XXX Partition needs moved to utils.
            (nonCommands, commands) = fix.partition(lambda s: ' ' in s, 
                                                    contributions)
            results = []
            if commands:
                results.append(
                    'the %s %s' %(utils.commaAndify(commands),
                                  utils.pluralize('command',len(commands))))
            if nonCommands:
                results.append('the %s' % utils.commaAndify(nonCommands))
            if results and isAuthor:
                return '%s wrote the %s plugin and also contributed %s' % \
                    (fullName, plugin, utils.commaAndify(results))
            elif results and not isAuthor:
                return '%s contributed %s to the %s plugin' % \
                    (fullName, utils.commaAndify(results), plugin)
            elif isAuthor and not results:
                return '%s wrote the %s plugin' % (fullName, plugin)
            else:
                return '%s has no listed contributions for the %s plugin %s' %\
                    (fullName, plugin)
        # First we need to check and see if the requested plugin is loaded
        cb = irc.getCallback(plugin)
        if cb is None:
            irc.error('No such plugin %r exists.' % plugin)
            return
        module = sys.modules[cb.__class__.__module__]
        if not nick:
            irc.reply(buildPeopleString(module))
        else:
            irc.reply(buildPersonString(module))

Class = Misc

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
