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
import time
import getopt
import pprint
import smtplib
import textwrap

import conf
import debug
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks

class MiscCommands(callbacks.Privmsg):
    def list(self, irc, msg, args):
        """[<module name>]

        Lists the commands available in the given plugin.  If no plugin is
        given, lists the public plugins available.
        """
        name = privmsgs.getArgs(args, needed=0, optional=1)
        name = name.lower()
        if not name:
            names = [cb.name() for cb in irc.callbacks
                     if hasattr(cb, 'public') and cb.public]
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

    def help(self, irc, msg, args):
        """<command>

        Gives the help for a specific command.  To find commands,
        use the 'list' command to go see the commands offered by a plugin.
        The 'list' command by itself will show you what plugins have commands.
        """
        command = privmsgs.getArgs(args, needed=0, optional=1)
        if not command:
            command = 'help'
        command = callbacks.canonicalName(command)
        cb = irc.findCallback(command)
        if cb:
            method = getattr(cb, command)
            if hasattr(method, '__doc__') and method.__doc__ is not None:
                doclines = method.__doc__.strip().splitlines()
                help = doclines.pop(0)
                if doclines:
                    s = '%s %s (for more help use the morehelp command)'
                else:
                    s = '%s %s'
                irc.reply(msg, s % (command, help))
            else:
                irc.reply(msg, 'That command exists, but has no help.')
        else:
            cb = irc.getCallback(command)
            if cb:
                if hasattr(cb, '__doc__') and cb.__doc__ is not None:
                    doclines = cb.__doc__.strip().splitlines()
                    help = ' '.join(map(str.strip, doclines))
                    if not help.endswith('.'):
                        help += '.'
                    help += '  Use the list command to see what commands ' \
                            'this plugin supports.'
                    irc.reply(msg, help)
                else:
                    module = __import__(cb.__module__)
                    if hasattr(module, '__doc__') and module.__doc__:
                        doclines = module.__doc__.strip().splitlines()
                        help = ' '.join(map(str.strip, doclines))
                        if not help.endswith('.'):
                            help += '.'
                        help += '  Use the list command to see what ' \
                                'commands this plugin supports.'
                        irc.reply(msg, help)
                    else:
                        irc.error(msg, 'That plugin has no help.')
            else:
                irc.error(msg, 'There is no such command or plugin.')

    def morehelp(self, irc, msg, args):
        """<command>

        This command gives more help than is provided by the simple argument
        list given by the command 'help'.
        """
        command = callbacks.canonicalName(privmsgs.getArgs(args))
        cb = irc.findCallback(command)
        if cb:
            method = getattr(cb, command)
            if hasattr(method, '__doc__') and method.__doc__ is not None:
                doclines = method.__doc__.splitlines()
                simplehelp = doclines.pop(0)
                if doclines:
                    doclines = filter(None, doclines)
                    doclines = map(str.strip, doclines)
                    help = ' '.join(doclines)
                    irc.reply(msg, help)
                else:
                    irc.reply(msg, 'That command has no more help.  '\
                                   'The original help is this: %s %s' % \
                                   (command, simplehelp))
            else:
                irc.error(msg, 'That command has no help at all.')

    def bug(self, irc, msg, args):
        """<description>

        Reports a bug to a private mailing list supybot-bugs.  <description>
        will be the subject of the email.  The most recent 10 or so messages
        the bot receives will be sent in the body of the email.
        """
        description = privmsgs.getArgs(args)
        messages = pprint.pformat(irc.state.history[-10:])
        email = textwrap.dedent("""
        Subject: %s
        Date: %s

        Bug report for Supybot %s.
        %s
        """) % (description, time.ctime(), conf.version, messages)
        email = email.strip()
        email = email.replace('\n', '\r\n')
        debug.printf(`email`)
        smtp = smtplib.SMTP('mail.sourceforge.net', 25)
        smtp.sendmail('jemfinch@users.sf.net',
                      ['supybot-bugs@lists.sourceforge.net'],
                      email)
        smtp.quit()
        irc.reply(msg, conf.replySuccess)
    bug = privmsgs.thread(bug)

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
        cb = irc.findCallback(command)
        if cb is not None:
            irc.reply(msg, cb.name())
        else:
            irc.error(msg, 'There is no such command %s' % command)

    def more(self, irc, msg, args):
        """[<nick>]

        If the last command was truncated due to IRC message length
        limitations, returns the next chunk of the result of the last command.
        If <nick> is given, return the continuation of the last command from
        <nick> instead of the person sending this message.
        """
        nick = privmsgs.getArgs(args, needed=0, optional=1)
        userHostmask = msg.prefix.split('!', 1)[1]
        if nick:
            try:
                hostmask = irc.state.nickToHostmask(nick)
                otherUserHostmask = hostmask.split('!', 1)[1]
                L = self._mores[otherUserHostmask][:]
                self._mores[userHostmask] = L
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
        for m in reviter(irc.state.history):
            if first:
                first = False
                continue
            if not m.prefix or m.command != 'PRIVMSG':
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



Class = MiscCommands

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
