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

from fix import *

import os
import sys
import time
import getopt
import textwrap
from itertools import ifilter

import conf
import debug
import utils
import world
import ircmsgs
import ircutils
import privmsgs
import callbacks

def replyWhenNotCommand(irc, msg, notCommands):
    """This is called when supybot thinks he has received a command but the
    apparent command actually isn't a command.  Replace it with something that
    suits your purposes more, if you want.
    """
    if len(notCommands) == 1:
        s = '%s is not a command.' % notCommands[0]
    else:
        s = '%s are not commands' % \
            utils.commaAndify(notCommands)
    irc.queueMsg(callbacks.reply(msg, s))
    

class MiscCommands(callbacks.Privmsg):
    def doPrivmsg(self, irc, msg):
        # This exists to be able to respond to attempts to command the bot
        # with a "That's not a command!" if the proper conf.variable is set.
        callbacks.Privmsg.doPrivmsg(self, irc, msg)
        if conf.replyWhenNotCommand and msg.nick != irc.nick:
            s = callbacks.addressed(irc.nick, msg)
            if s:
                for cb in irc.callbacks:
                    if isinstance(cb, callbacks.PrivmsgRegexp) or \
                       isinstance(cb, callbacks.PrivmsgCommandAndRegexp):
                        for (r, _) in cb.res:
                            if r.search(msg.args[1]):
                                return
                notCommands = []
                tokens = callbacks.tokenize(s)
                for command in callbacks.getCommands(tokens):
                    command = callbacks.canonicalName(command)
                    if not callbacks.findCallbackForCommand(irc, command):
                        notCommands.append(repr(command))
                if notCommands:
                    replyWhenNotCommand(irc, msg, notCommands)
        
    def list(self, irc, msg, args):
        """[--private] [<module name>]

        Lists the commands available in the given plugin.  If no plugin is
        given, lists the public plugins available.  If --private is given,
        lists all commands, not just the public ones.
        """
        (optlist, rest) = getopt.getopt(args, '', ['private'])
        evenPrivate = False
        for (option, argument) in optlist:
            if option == '--private':
                evenPrivate = True
        name = privmsgs.getArgs(rest, needed=0, optional=1)
        name = name.lower()
        if not name:
            names = [cb.name() for cb in irc.callbacks
                     if evenPrivate or (hasattr(cb, 'public') and cb.public)]
            names.sort()
            irc.reply(msg, ', '.join(names))
        else:
            for cb in irc.callbacks:
                cls = cb.__class__
                if cb.name().lower().startswith(name) and \
                       not issubclass(cls, callbacks.PrivmsgRegexp) and \
                       issubclass(cls, callbacks.Privmsg):
                    commands = [x for x in dir(cls)
                                if cb.isCommand(x) and \
                                hasattr(getattr(cb, x), '__doc__')]
                    commands.sort()
                    irc.reply(msg, ', '.join(commands))
                    return
            irc.error(msg, 'There is no plugin named %s, ' \
                           'or that plugin has no commands.' % name)

    def syntax(self, irc, msg, args):
        """<command>

        Gives the syntax for a specific command.  To find commands,
        use the 'list' command to go see the commands offered by a plugin.
        The 'list' command by itself will show you what plugins have commands.
        """
        command = privmsgs.getArgs(args, needed=0, optional=1)
        if not command:
            command = 'help'
        command = callbacks.canonicalName(command)
        cb = callbacks.findCallbackForCommand(irc, command)
        if cb:
            method = getattr(cb, command)
            if hasattr(method, '__doc__') and method.__doc__ is not None:
                doclines = method.__doc__.strip().splitlines()
                help = doclines.pop(0)
                irc.reply(msg, '%s %s' % (command, help))
            else:
                irc.reply(msg, 'That command exists, '
                               'but has no syntax description.')
        else:
            cb = irc.getCallback(command)
            if cb:
                s = ''
                if hasattr(cb, '__doc__') and cb.__doc__ is not None:
                    s = cb.__doc__
                else:
                    module = sys.modules[cb.__module__]
                    if hasattr(module, '__doc__') and module.__doc__:
                        s = module.__doc__
                if s:
                    s = ' '.join(map(str.strip, s.splitlines()))
                    if not s.endswith('.'):
                        s += '.'
                    s += '  Use the list command to see what commands this ' \
                         'plugin supports.'
                else:
                    s = 'That plugin has no help description.'
                irc.reply(msg, s)
            else:
                irc.error(msg, 'There is no such command or plugin.')

    def help(self, irc, msg, args):
        """<command>

        This command gives a much more useful description than the simple
        argument list given by the command 'syntax'.
        """
        command = callbacks.canonicalName(privmsgs.getArgs(args))
        cb = callbacks.findCallbackForCommand(irc, command)
        if cb:
            method = getattr(cb, command)
            if hasattr(method, '__doc__') and method.__doc__ is not None:
                doclines = method.__doc__.splitlines()
                simplehelp = doclines.pop(0)
                simplehelp = '(%s %s)' % (command, simplehelp)
                if doclines:
                    doclines = filter(None, doclines)
                    doclines = map(str.strip, doclines)
                    help = ' '.join(doclines)
                    s = '%s    %s' % (ircutils.bold(simplehelp),help)
                    irc.reply(msg, s)
                else:
                    irc.reply(msg, 'That command has no help.  '\
                                   'The syntax is this: %s %s' % \
                                   (command, simplehelp))
            else:
                irc.error(msg, '%s has no help or syntax description.'%command)
        else:
            irc.error(msg, 'There is no such command %s.' % command)

    def hostmask(self, irc, msg, args):
        """<nick>

        Returns the hostmask of <nick>.
        """
        nick = privmsgs.getArgs(args)
        try:
            irc.reply(msg, irc.state.nickToHostmask(nick))
        except KeyError:
            irc.error(msg, 'I haven\'t seen anyone named %r' % nick)

    def version(self, irc, msg, args):
        """takes no arguments

        Returns the version of the current bot.
        """
        irc.reply(msg, conf.version)

    def source(self, irc, msg, args):
        """takes no arguments

        Returns a URL saying where to get SupyBot.
        """
        irc.reply(msg, 'My source is at http://www.sf.net/projects/supybot/')

    def logfilesize(self, irc, msg, args):
        """[<logfile>]

        Returns the size of the various logfiles in use.  If given a specific
        logfile, returns only the size of that logfile.
        """
        filename = privmsgs.getArgs(args, needed=0, optional=1)
        if filename:
            if not filename.endswith('.log'):
                irc.error(msg, 'That filename doesn\'t appear to be a log.')
                return
            filenames = [filename]
        else:
            filenames = os.listdir(conf.logDir)
        result = []
        for file in filenames:
            if file.endswith('.log'):
                stats = os.stat(os.path.join(conf.logDir, file))
                result.append((file, str(stats.st_size)))
        irc.reply(msg, ', '.join(map(': '.join, result)))

    def getprefixchar(self, irc, msg, args):
        """takes no arguments

        Returns the prefix character(s) the bot is currently using.
        """
        irc.reply(msg, repr(conf.prefixChars))

    def plugin(self, irc, msg, args):
        """<command>

        Returns the plugin <command> is in.
        """
        command = callbacks.canonicalName(privmsgs.getArgs(args))
        cb = callbacks.findCallbackForCommand(irc, command)
        if cb is not None:
            irc.reply(msg, cb.name())
        else:
            irc.error(msg, 'There is no such command %s' % command)

    def more(self, irc, msg, args):
        """[<nick>]

        If the last command was truncated due to IRC message length
        limitations, returns the next chunk of the result of the last command.
        If <nick> is given, it takes the continuation of the last command from
        <nick> instead of the person sending this message.
        """
        nick = privmsgs.getArgs(args, needed=0, optional=1)
        userHostmask = msg.prefix.split('!', 1)[1]
        if nick:
            try:
                (private, L) = self._mores[nick]
                if not private:
                    self._mores[userHostmask] = L[:]
                else:
                    irc.error(msg, '%s has no public mores.' % nick)
                    return
            except KeyError:
                irc.error(msg, 'Sorry, I can\'t find a hostmask for %s' % nick)
                return
        try:
            L = self._mores[userHostmask]
            chunk = L.pop()
            if L:
                chunk += ' \x02(%s)\x0F' % \
                         utils.nItems(len(L), 'message', 'more')
            irc.reply(msg, chunk, True)
        except KeyError:
            irc.error(msg, 'You haven\'t asked me a command!')
        except IndexError:
            irc.error(msg, 'That\'s all, there is no more.')

    def _validLastMsg(self, msg):
        return msg.prefix and \
               msg.command == 'PRIVMSG' and \
               ircutils.isChannel(msg.args[0])

    def last(self, irc, msg, args):
        """[--{from,in,to,with,regexp,fancy}] <args>

        Returns the last message matching the given criteria.  --from requires
        a nick from whom the message came; --in and --to require a channel the
        message was sent to; --with requires some string that had to be in the
        message; --regexp requires a regular expression the message must match
        --fancy determines whether or not to show the nick; the default is not
        """
        (optlist, rest) = getopt.getopt(args, '', ['from=', 'in=', 'to=',
                                                   'with=', 'regexp=',
                                                   'fancy'])
        fancy = False
        predicates = []
        for (option, arg) in optlist:
            option = option.strip('-')
            if option == 'fancy':
                fancy = True
            elif option == 'from':
                predicates.append(lambda m, arg=arg: m.nick == arg)
            elif option == 'in' or option == 'to':
                if not ircutils.isChannel(arg):
                    irc.error(msg, 'Argument to --%s must be a channel.' % arg)
                    return
                predicates.append(lambda m, arg=arg: m.args[0] == arg)
            elif option == 'with':
                predicates.append(lambda m, arg=arg: arg in m.args[1])
            elif option == 'regexp':
                try:
                    r = utils.perlReToPythonRe(arg)
                except ValueError, e:
                    irc.error(msg, str(e))
                    return
                predicates.append(lambda m: r.search(m.args[1]))
        first = True
        for m in ifilter(self._validLastMsg, reviter(irc.state.history)):
            if first:
                first = False
                continue
            for predicate in predicates:
                if not predicate(m):
                    break
            else:
                if fancy:
                    irc.reply(msg, ircmsgs.prettyPrint(m))
                else:
                    irc.reply(msg, m.args[1])
                return
        irc.error(msg, 'I couldn\'t find a message matching that criteria.')

    def tell(self, irc, msg, args):
        """<nick|channel> <text>

        Tells the <nick|channel> whatever <text> is.  Use nested commands to
        your benefit here.
        """
        (target, text) = privmsgs.getArgs(args, needed=2)
        s = '%s wants me to tell you: %s' % (msg.nick, text)
        irc.queueMsg(ircmsgs.privmsg(target, s))
        raise callbacks.CannotNest

    def private(self, irc, msg, args):
        """<text>

        Replies with <text> in private.  Use nested commands to your benefit
        here.
        """
        text = privmsgs.getArgs(args)
        irc.reply(msg, text, private=True)



Class = MiscCommands

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
