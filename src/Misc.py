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

import fix

import os
import sys
import getopt
from itertools import imap, ifilter

import conf
import utils
import irclib
import ircmsgs
import ircutils
import privmsgs
import callbacks

class Misc(callbacks.Privmsg):
    priority = sys.maxint
    def invalidCommand(self, irc, msg, tokens):
        self.log.debug('Misc.invalidCommand called (tokens %s)', tokens)
        if conf.supybot.reply.whenNotCommand():
            command = tokens and tokens[0] or ''
            irc.error('%r is not a valid command.' % command)
        else:
            if not isinstance(irc.irc, irclib.Irc):
                irc.reply('[%s]' % ' '.join(tokens))
        
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
        name = privmsgs.getArgs(rest, required=0, optional=1)
        name = callbacks.canonicalName(name)
        if not name:
            names = [cb.name() for cb in irc.callbacks
                     if evenPrivate or (hasattr(cb, 'public') and cb.public)]
            names.sort()
            irc.reply(', '.join(names))
        else:
            cb = irc.getCallback(name)
            if cb is None:
                irc.error('No such plugin %r exists.' % name)
            elif isinstance(cb, callbacks.PrivmsgRegexp) or \
                 not isinstance(cb, callbacks.Privmsg):
                irc.error('That plugin exists, but it has no commands.')
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
                    irc.reply(', '.join(commands))
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
            irc.error('No appropriate commands were found.')

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
            cb = irc.getCallback(args[0])
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
                irc.error('There is no such plugin %s' % args[0])
            return
        command = callbacks.canonicalName(privmsgs.getArgs(args))
        # Users might expect "@help @list" to work.
        command = command.lstrip(conf.supybot.prefixChars()) 
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
                assert len(tokens) == 2
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
        irc.reply(conf.version)

    def revision(self, irc, msg, args):
        """[<module>]

        Gives the latest revision of <module>.  If <module> isn't given, gives
        the revision of all supybot modules.
        """
        name = privmsgs.getArgs(args, required=0, optional=1)
        if name:
            if name.endswith('.py'):
                name = name[:-3]
            try:
                modules = {}
                for moduleName in sys.modules:
                    modules[moduleName.lower()] = moduleName
                module = sys.modules[modules[name.lower()]]
            except KeyError:
                irc.error('I couldn\'t find a module named %s' % name)
                return
            if hasattr(module, '__revision__'):
                irc.reply(module.__revision__)
            else:
                irc.error('Module %s has no __revision__.' % name)
        else:
            def getVersion(s):
                try:
                    return s.split(None, 3)[2]
                except:
                    self.log.exception('Couldn\'t get id string: %r', s)
            names = {}
            dirs = map(os.path.abspath, conf.supybot.directories.plugins())
            for (name, module) in sys.modules.items(): # Don't use iteritems.
                if hasattr(module, '__revision__'):
                    if 'supybot' in module.__file__:
                        names[name] = getVersion(module.__revision__)
                    else:
                        for dir in dirs:
                            if dir in module.__file__:
                                names[name] = getVersion(module.__revision__)
                                break
            L = ['%s: %s' % (k, v) for (k, v) in names.items()]
            irc.reply(utils.commaAndify(L))
                        
    def source(self, irc, msg, args):
        """takes no arguments

        Returns a URL saying where to get SupyBot.
        """
        irc.reply('My source is at http://supybot.sf.net/')

    def logfilesize(self, irc, msg, args):
        """[<logfile>]

        Returns the size of the various logfiles in use.  If given a specific
        logfile, returns only the size of that logfile.
        """
        filenameArg = privmsgs.getArgs(args, required=0, optional=1)
        if filenameArg:
            if not filenameArg.endswith('.log'):
                irc.error('That filename doesn\'t appear to be a log.')
                return
            filenameArg = os.path.basename(filenameArg)
        ret = []
        dirname = conf.supybot.directories.log()
        for (dirname,_,filenames) in os.walk(dirname):
            if filenameArg:
                if filenameArg in filenames:
                    filename = os.path.join(dirname, filenameArg)
                    stats = os.stat(filename)
                    ret.append('%s: %s' % (filename, stats.st_size))
            else:
                for filename in filenames:
                    stats = os.stat(os.path.join(dirname, filename))
                    ret.append('%s: %s' % (filename, stats.st_size))
        if ret:
            ret.sort()
            irc.reply(utils.commaAndify(ret))
        else:
            irc.error('I couldn\'t find any logfiles.')

    def plugin(self, irc, msg, args):
        """<command>

        Returns the plugin <command> is in.
        """
        command = callbacks.canonicalName(privmsgs.getArgs(args))
        cbs = callbacks.findCallbackForCommand(irc, command)
        if cbs:
            irc.reply(utils.commaAndify([cb.name() for cb in cbs]))
        else:
            irc.error('There is no such command %s' % command)

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
                irc.error('Sorry, I can\'t find a hostmask for %s' % nick)
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
        """[--{from,in,to,with,regexp}] <args>

        Returns the last message matching the given criteria.  --from requires
        a nick from whom the message came; --in and --to require a channel the
        message was sent to; --with requires some string that had to be in the
        message; --regexp requires a regular expression the message must
        match.  By default, the current channel is searched.
        """
        (optlist, rest) = getopt.getopt(args, '', ['from=', 'in=', 'to=',
                                                   'with=', 'regexp='])
                                                   
        predicates = {}
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
                    return arg in m.args[1]
                predicates.setdefault('with', []).append(f)
            elif option == '--regexp':
                try:
                    r = utils.perlReToPythonRe(arg)
                    def f(m, r=r):
                        return r.search(m.args[1])
                    predicates.setdefault('regexp', []).append(f)
                except ValueError, e:
                    irc.error(str(e))
                    return
        iterable = ifilter(self._validLastMsg, reviter(irc.state.history))
        iterable.next() # Drop the first message.
        predicates = list(utils.flatten(predicates.itervalues()))
        for m in iterable:
            for predicate in predicates:
                if not predicate(m):
                    break
            else:
                irc.reply(ircmsgs.prettyPrint(m))
                return
        irc.error('I couldn\'t find a message matching that criteria in '
                       'my history of %s messages.' % len(irc.state.history))

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
        if not ircutils.isNick(target) and not ircutils.isChannel(target):
            irc.error('%s is not a valid nick or channel.' % target)
            return
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

        Returns the arguments given it, but as an action.
        """
        text = privmsgs.getArgs(args)
        if text:
            irc.queueMsg(ircmsgs.action(ircutils.replyTo(msg), ' '.join(args)))
        else:
            raise callbacks.Error

    def notice(self, irc, msg, args):
        """<text>

        Replies with <text> in a private notice.  Use nested commands to your
        benefit here.
        """
        text = privmsgs.getArgs(args)
        irc.reply(text, notice=True)


Class = Misc

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
