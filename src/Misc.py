#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import supybot.fix as fix

import os
import sys
import getopt
from itertools import imap, ifilter

import supybot.conf as conf
import supybot.utils as utils
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

class Misc(callbacks.Privmsg):
    priority = sys.maxint
    def invalidCommand(self, irc, msg, tokens):
        self.log.debug('Misc.invalidCommand called (tokens %s)', tokens)
        if conf.supybot.reply.whenNotCommand():
            command = tokens and tokens[0] or ''
            irc.error('%r is not a valid command.' % command)
        else:
            if tokens:
                # echo [] will get us an empty token set, but there's no need
                # to log this in that case anyway, it being a nested command.
                self.log.info('Not replying to %s, not a command.' % tokens[0])
            if not isinstance(irc.irc, irclib.Irc):
                brackets = conf.supybot.reply.brackets.get(msg.args[0])()
                irc.reply(''.join([brackets[0],' '.join(tokens), brackets[1]]))

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
                command = command.lstrip(conf.supybot.prefixChars())
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
        # command = command.lstrip(conf.supybot.prefixChars())
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
        def getRevisionNumber(module):
            def getVersion(s):
                try:
                    return s.split(None, 3)[2]
                except:
                    self.log.exception('Couldn\'t get id string: %r', s)
            if hasattr(module, '__revision__'):
                if 'supybot' in module.__file__:
                    return getVersion(module.__revision__)
                else:
                    for dir in conf.supybot.directories.plugins():
                        if module.__file__.startswith(dir):
                            return getVersion(module.__revision__)
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
                    names.append((name, getRevisionNumber(module)))
            elif len(args) == 1: # wildcards
                pattern = args[0]
                for (name, module) in sys.modules.items():
                    if ircutils.hostmaskPatternEqual(pattern, name):
                        names.append((name, getRevisionNumber(module)))
            else:
                for name in args:
                    name = normalize(name)
                    if name not in sys.modules:
                        irc.error('I couldn\'t find a Supybot named %s.'%name)
                        return
                    module = sys.modules[name]
                    names.append((name, getRevisionNumber(module)))
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
        """[--{from,in,to,with,regexp,nolimit}] <args>

        Returns the last message matching the given criteria.  --from requires
        a nick from whom the message came; --in and --to require a channel the
        message was sent to; --with requires some string that had to be in the
        message; --regexp requires a regular expression the message must i
        match; --nolimit returns all the messages that can be found.  By
        default, the current channel is searched.
        """
        (optlist, rest) = getopt.getopt(args, '', ['from=', 'in=', 'to=',
                                                   'with=', 'regexp=',
                                                   'nolimit'])
        predicates = {}
        nolimit = False
        if ircutils.isChannel(msg.args[0]):
            predicates['in'] = lambda m: m.args[0] == msg.args[0]
        for (option, arg) in optlist:
            if option == '--from':
                def f(m, arg=arg):
                    return ircutils.hostmaskPatternEqual(arg, m.nick)
                predicates['from'] = f
            elif option == '--in' or option == 'to':
                def f(m, arg=arg):
                    return m.args[0] == arg
                predicates['in'] = f
            elif option == '--with':
                def f(m, arg=arg):
                    return arg.lower() in m.args[1].lower()
                predicates.setdefault('with', []).append(f)
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
        for m in iterable:
            for predicate in predicates:
                if not predicate(m):
                    break
            else:
                if nolimit:
                    resp.append(ircmsgs.prettyPrint(m))
                else:
                    irc.reply(ircmsgs.prettyPrint(m))
                    return
        if not resp:
            irc.error('I couldn\'t find a message matching that criteria in '
                      'my history of %s messages.' % len(irc.state.history))
        else:
            irc.reply(utils.commaAndify(resp))

    def seconds(self, irc, msg, args):
        """[<years>y] [<weeks>w] [<days>d] [<hours>h] [<minutes>m] [<seconds>s]

        Returns the number of seconds in the number of <years>, <weeks>,
        <days>, <hours>, <minutes>, and <seconds> given.  An example usage is
        "seconds 2h 30m", which would return 9000, which is 3600*2 + 30*60.
        Useful for scheduling events at a given number of seconds in the
        future.
        """
        if not args:
            raise callbacks.ArgumentError
        seconds = 0
        for arg in args:
            if not arg or arg[-1] not in 'ywdhms':
                raise callbacks.ArgumentError
            (s, kind) = arg[:-1], arg[-1]
            try:
                i = int(s)
            except ValueError:
                irc.error('Invalid argument: %s' % arg)
                return
            if kind == 'y':
                seconds += i*31536000
            elif kind == 'w':
                seconds += i*604800
            elif kind == 'd':
                seconds += i*86400
            elif kind == 'h':
                seconds += i*3600
            elif kind == 'm':
                seconds += i*60
            elif kind == 's':
                seconds += i
        irc.reply(str(seconds))

    def tell(self, irc, msg, args):
        """<nick|channel> <text>

        Tells the <nick|channel> whatever <text> is.  Use nested commands to
        your benefit here.
        """
        (target, text) = privmsgs.getArgs(args, required=2)
        if target.lower() == 'me':
            target = msg.nick
        elif ircutils.isChannel(target):
            irc.error('Dude, just give the command.  No need for the tell.')
            return
        elif not ircutils.isNick(target):
            irc.error('%s is not a valid nick.' % target)
            return
        elif ircutils.nickEqual(target, irc.nick):
            irc.error('You just told me, why should I tell myself?')
            return
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


Class = Misc

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
