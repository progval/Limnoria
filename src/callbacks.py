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
This module contains the basic callbacks for handling PRIVMSGs.  Both Privmsg
and PrivmsgRegexp classes are provided; for offering callbacks based on
commands and their arguments (much like *nix command line programs) use the
Privmsg class; for offering callbacks based on regular expressions, use the
PrivmsgRegexp class.  Read their respective docstrings for more information on
how to use them.
"""

import fix

import re
import copy
import sets
import time
import shlex
import types
import getopt
import string
import inspect
import textwrap
import threading
from itertools import imap, ifilter
from cStringIO import StringIO

import conf
import debug
import utils
import world
import ircdb
import irclib
import ircmsgs
import ircutils

###
# Privmsg: handles privmsg commands in a standard fashion.
###
def addressed(nick, msg):
    """If msg is addressed to 'name', returns the portion after the address.
    Otherwise returns the empty string.
    """
    nick = ircutils.toLower(nick)
    if ircutils.nickEqual(msg.args[0], nick):
        if msg.args[1][0] in conf.prefixChars:
            return msg.args[1][1:].strip()
        else:
            return msg.args[1].strip()
    elif ircutils.toLower(msg.args[1]).startswith(nick):
        try:
            (maybeNick, rest) = msg.args[1].split(None, 1)
            while not ircutils.isNick(maybeNick):
                maybeNick = maybeNick[:-1]
            if ircutils.nickEqual(maybeNick, nick):
                return rest
            else:
                return ''
        except ValueError: # split didn't work.
            return ''
    elif msg.args[1] and msg.args[1][0] in conf.prefixChars:
        return msg.args[1][1:].strip()
    else:
        return ''

def canonicalName(command):
    """Turn a command into its canonical form.

    Currently, this makes everything lowercase and removes all dashes and
    underscores.
    """
    assert not isinstance(command, unicode)
    special = '\t -_'
    reAppend = ''
    while command and command[-1] in special:
        reAppend = command[-1] + reAppend
        command = command[:-1]
    return command.translate(string.ascii, special).lower() + reAppend

def reply(msg, s, prefixName=True, private=False, notice=False):
    """Makes a reply to msg with the payload s"""
    s = ircutils.safeArgument(s)
    if ircutils.isChannel(msg.args[0]) and not private:
        if notice or conf.replyWithPrivateNotice:
            m = ircmsgs.notice(msg.nick, s)
        elif prefixName:
            m = ircmsgs.privmsg(msg.args[0], '%s: %s' % (msg.nick, s))
        else:
            m = ircmsgs.privmsg(msg.args[0], s)
    else:
        m = ircmsgs.privmsg(msg.nick, s)
    return m

def error(msg, s):
    """Makes an error reply to msg with the appropriate error payload."""
    return reply(msg, 'Error: ' + s)

def getHelp(method, name=None):
    if name is None:
        name = method.__name__
    doclines = method.__doc__.splitlines()
    s = '%s %s' % (name, doclines.pop(0))
    if doclines:
        doclines = imap(str.strip, ifilter(None, doclines))
        help = ' '.join(doclines)
        s = '(%s) -- %s' % (ircutils.bold(s), help)
    return s

def getSyntax(method, name=None):
    if name is None:
        name = method.__name__
    doclines = method.__doc__.splitlines()
    return '%s %s' % (name, doclines[0])

class Error(Exception):
    """Generic class for errors in Privmsg callbacks."""
    pass

class ArgumentError(Error):
    """The bot replies with a help message when this is raised."""
    pass

class CannotNest(Error):
    """Exception to be raised by commands that cannot be nested."""
    pass

class Tokenizer:
    # This will be used as a global environment to evaluate strings in.
    # Evaluation is, of course, necessary in order to allowed escaped
    # characters to be properly handled.
    #
    # These are the characters valid in a token.  Everything printable except
    # double-quote, left-bracket, and right-bracket.
    validChars = string.ascii.translate(string.ascii, '\x00\r\n \t"[]')
    quotes = '"'
    def __init__(self, tokens=''):
        # Add a '|' to tokens to have the pipe syntax.
        self.validChars = self.validChars.translate(string.ascii, tokens)

    def _handleToken(self, token):
        if token[0] == token[-1] and token[0] in self.quotes:
            token = token[1:-1]
            token = token.decode('string-escape')
        return token

    def _insideBrackets(self, lexer):
        ret = []
        while True:
            token = lexer.get_token()
            if not token:
                raise SyntaxError, 'Missing "]"'
            elif token == ']':
                return ret
            elif token == '[':
                ret.append(self._insideBrackets(lexer))
            else:
                ret.append(self._handleToken(token))
        return ret

    def tokenize(self, s):
        """Tokenizes a string according to supybot's nested argument format."""
        lexer = shlex.shlex(StringIO(s))
        lexer.commenters = ''
        lexer.quotes = self.quotes
        lexer.wordchars = self.validChars
        args = []
        ends = []
        while True:
            token = lexer.get_token()
            #debug.printf(repr(token))
            if not token:
                break
            elif token == '|':
                if not args:
                    raise SyntaxError, '"|" with nothing preceding'
                ends.append(args)
                args = []
            elif token == '[':
                args.append(self._insideBrackets(lexer))
            elif token == ']':
                raise SyntaxError, 'Spurious "["'
            else:
                args.append(self._handleToken(token))
        if ends:
            if not args:
                raise SyntaxError, '"|" with nothing following'
            args.append(ends.pop())
            while ends:
                args[-1].append(ends.pop())
        return args

_lastTokenized = None
_lastTokenizeResult = None
def tokenize(s):
    """A utility function to create a Tokenizer and tokenize a string."""
    global _lastTokenized, _lastTokenizeResult
    start = time.time()
    try:
        if s != _lastTokenized:
            _lastTokenized = s
            if conf.enablePipeSyntax:
                tokens = '|'
            else:
                tokens = ''
            _lastTokenizeResult = Tokenizer(tokens).tokenize(s)
    except ValueError, e:
        _lastTokenized = None
        _lastTokenizedResult = None
        raise SyntaxError, str(e)
    debug.msg('tokenize took %s seconds.' % (time.time() - start), 'verbose')
    return copy.deepcopy(_lastTokenizeResult)

def getCommands(tokens):
    """Given tokens as output by tokenize, returns the command names."""
    L = []
    if tokens and isinstance(tokens, list):
        L.append(tokens[0])
        for elt in tokens:
            L.extend(getCommands(elt))
    return L

def findCallbackForCommand(irc, commandName):
    """Given a command name and an Irc object, returns a list of callbacks that
    commandName is in."""
    L = []
    for callback in irc.callbacks:
        if not isinstance(callback, PrivmsgRegexp):
            if hasattr(callback, 'isCommand'):
                if callback.isCommand(commandName):
                    L.append(callback)
    return L

def formatArgumentError(method, name=None):
    if name is None:
        name = method.__name__
    if hasattr(method, '__doc__') and method.__doc__:
        if conf.showOnlySyntax:
            return getSyntax(method, name=name)
        else:
            return getHelp(method, name=name)
    else:
        return 'Invalid arguments for %s.' % method.__name__

class IrcObjectProxy:
    "A proxy object to allow proper nested of commands (even threaded ones)."
    def __init__(self, irc, msg, args):
        #debug.printf('IrcObjectProxy.__init__: %s' % args)
        self.irc = irc
        self.msg = msg
        self.args = args
        self.counter = 0
        self.action = False
        self.notice = False
        self.private = False
        self.finished = False
        self.prefixName = True
        self.noLengthCheck = False
        if not args:
            self.finalEvaled = True
            self._callInvalidCommands()
        else:
            self.finalEvaled = False
            world.commandsProcessed += 1
            self.evalArgs()

    def evalArgs(self):
        while self.counter < len(self.args):
            if type(self.args[self.counter]) == str:
                self.counter += 1
            else:
                IrcObjectProxy(self, self.msg, self.args[self.counter])
                return
        self.finalEval()

    def _callInvalidCommands(self):
        for cb in self.irc.callbacks:
            #debug.printf('Trying to call %s.invalidCommand' % cb.name())
            if self.finished:
                break
            if hasattr(cb, 'invalidCommand'):
                cb.invalidCommand(self, self.msg, self.args)
                
    def finalEval(self):
        assert not self.finalEvaled, 'finalEval called twice.'
        self.finalEvaled = True
        name = canonicalName(self.args[0])
        cbs = findCallbackForCommand(self, name)
        if len(cbs) == 0:
            if self.irc.nick == self.msg.nick and not world.testing:
                return
            for cb in self.irc.callbacks:
                if isinstance(cb, PrivmsgRegexp):
                    for (r, _) in cb.res:
                        if r.search(self.msg.args[1]):
                            return
                elif isinstance(cb, PrivmsgCommandAndRegexp):
                    for (r, _) in cb.res:
                        if r.search(self.msg.args[1]):
                            return
                    for (r, _) in cb.addressedRes:
                        if r.search(self.msg.args[1]):
                            return
            # Ok, no regexp-based things matched.
            self._callInvalidCommands()
        else:
            try:
                assert len(cbs) == 1, \
                       'Got command that wasn\'t disambiguated: %s' % name
                del self.args[0]
                cb = cbs[0]
                anticap = ircdb.makeAntiCapability(name)
                #debug.printf('Checking for %s' % anticap)
                if ircdb.checkCapability(self.msg.prefix, anticap):
                    #debug.printf('Being prevented with anticap')
                    debug.msg('Preventing %s from calling %s' % \
                              (self.msg.nick, name), 'normal')
                    s = conf.replyNoCapability % name
                    self.error(self.msg, s, private=True)
                    return
                recipient = self.msg.args[0]
                if ircutils.isChannel(recipient):
                    chancap = ircdb.makeChannelCapability(recipient, anticap)
                    #debug.printf('Checking for %s' % chancap)
                    if ircdb.checkCapability(self.msg.prefix, chancap):
                        #debug.printf('Being prevented with chancap')
                        debug.msg('Preventing %s from calling %s' % \
                                  (self.msg.nick, name), 'normal')
                        s = conf.replyNoCapability % name
                        self.error(self.msg, s, private=True)
                        return
                command = getattr(cb, name)
                if cb.threaded:
                    t = CommandThread(cb.callCommand, command,
                                      self, self.msg, self.args)
                    t.start()
                else:
                    cb.callCommand(command, self, self.msg, self.args)
            except (getopt.GetoptError, ArgumentError):
                self.reply(self.msg, formatArgumentError(command, name=name))
            except CannotNest, e:
                if not isinstance(self.irc, irclib.Irc):
                    self.error(self.msg, 'Command %r cannot be nested.' % name)
            except (SyntaxError, Error), e:
                self.reply(self.msg, debug.exnToString(e))
            except Exception, e:
                debug.recoverableException()
                self.error(self.msg, debug.exnToString(e))

    def reply(self, msg, s, noLengthCheck=False, prefixName=True,
              action=False, private=False, notice=False):
        """reply(msg, text) -> replies to msg with text

        Keyword arguments:
          noLengthCheck=False: True if the length shouldn't be checked
                               (used for 'more' handling)
          prefixName=True:     False if the nick shouldn't be prefixed to the
                               reply.
          action=False:        True if the reply should be an action.
          private=False:       True if the reply should be in private.
          notice=False:        True if the reply should be noticed when the
                               bot is configured to do so.
        """
        # These use |= or &= based on whether or not they default to True or
        # False.  Those that default to True use &=; those that default to
        # False use |=.
        self.action |= action
        self.private |= private
        self.notice |= notice
        self.prefixName &= prefixName
        self.noLengthCheck |= noLengthCheck
        if self.finalEvaled:
            if isinstance(self.irc, self.__class__):
                self.irc.reply(msg, s, self.noLengthCheck, self.prefixName,
                               self.action, self.private, self.notice)
            elif self.noLengthCheck:
                self.irc.queueMsg(reply(msg, s, self.prefixName))
            elif self.action:
                self.irc.queueMsg(ircmsgs.action(msg.args[0], s))
            else:
                s = ircutils.safeArgument(s)
                allowedLength = 450 - len(self.irc.prefix)
                msgs = textwrap.wrap(s, allowedLength-30) # -30 is for "nick:"
                msgs.reverse()
                response = msgs.pop()
                if msgs:
                    response += ' \x02(%s)\x0F' % \
                                utils.nItems(len(msgs), 'message', 'more')
                mask = msg.prefix.split('!', 1)[1]
                Privmsg._mores[mask] = msgs
                private = self.private or not ircutils.isChannel(msg.args[0])
                Privmsg._mores[msg.nick] = (private, msgs)
                if self.private:
                    self.irc.queueMsg(ircmsgs.privmsg(msg.nick, response))
                else:
                    self.irc.queueMsg(reply(msg, response, self.prefixName,
                                            notice=self.notice))
            self.finished = True
        else:
            self.args[self.counter] = s
            self.evalArgs()

    def error(self, msg, s, private=False):
        """error(msg, text) -> replies to msg with an error message of text.

        Keyword arguments:
          private=False: True if the error should be given in private.
        """
        if isinstance(self.irc, self.__class__):
            self.irc.error(msg, s, private)
        else:
            s = 'Error: ' + s
            if private or conf.errorReplyPrivate:
                self.irc.queueMsg(ircmsgs.privmsg(msg.nick, s))
            else:
                self.irc.queueMsg(reply(msg, s))
        self.finished = True

    def killProxy(self):
        """Kills this proxy object and all its parents."""
        if not isinstance(self.irc, irclib.Irc):
            self.irc.killProxy()
        self.__dict__ = {}

    def getRealIrc(self):
        """Returns the real irclib.Irc object underlying this proxy chain."""
        if isinstance(self.irc, irclib.Irc):
            return self.irc
        else:
            return self.irc.getRealIrc()

    def __getattr__(self, attr):
        return getattr(self.irc, attr)


class CommandThread(threading.Thread):
    """Just does some extra logging and error-recovery for commands that need
    to run in threads.
    """
    def __init__(self, callCommand, command, irc, msg, args, *L):
        self.command = command
        world.threadsSpawned += 1
        try:
            self.commandName = command.im_func.func_name
        except AttributeError:
            self.commandName = command.__name__
        try:
            self.className = command.im_class.__name__
        except AttributeError:
            self.className = '<unknown>'
        name = '%s.%s with args %r' % (self.className, self.commandName, args)
        threading.Thread.__init__(self, target=callCommand, name=name,
                                  args=(command, irc, msg, args)+L)
        debug.msg('Spawning thread %s' % name, 'verbose')
        self.irc = irc
        self.msg = msg
        self.setDaemon(True)

    def run(self):
        try:
            threading.Thread.run(self)
        except (getopt.GetoptError, ArgumentError):
            name = self.commandName
            self.irc.reply(self.msg, formatArgumentError(self.command, name))
        except CannotNest:
            if not isinstance(self.irc.irc, irclib.Irc):
                s = 'Command %r cannot be nested.' % self.commandName
                self.irc.error(self.msg, s)
        except (SyntaxError, Error), e:
            self.irc.reply(self.msg, debug.exnToString(e))
        except Exception, e:
            debug.recoverableException()
            self.irc.error(self.msg, debug.exnToString(e))


class ConfigIrcProxy(object):
    """Used as a proxy Irc object during configuration. """
    def __init__(self, irc):
        self.__dict__['irc'] = irc
        
    def reply(self, msg, s, *args):
        return None

    def error(self, msg, s, *args):
        debug.msg('ConfigIrcProxy saw an error: %s' % s, 'normal')

    def getRealIrc(self):
        irc = self.__dict__['irc']
        while(hasattr(irc, 'getRealIrc')):
            irc = irc.getRealIrc()
        return irc

    def __getattr__(self, attr):
        return getattr(self.getRealIrc(), attr)

    def __setattr__(self, attr, value):
        setattr(self.getRealIrc(), attr, value)

    
class Privmsg(irclib.IrcCallback):
    """Base class for all Privmsg handlers."""
    threaded = False
    public = True
    handled = False
    alwaysCall = ()
    noIgnore = False
    commandArgs = ['self', 'irc', 'msg', 'args']
    _mores = {} # This must be class-scope, so all subclasses use the same one.
    def __init__(self):
        self.__parent = super(Privmsg, self)
        self.Proxy = IrcObjectProxy
        canonicalname = canonicalName(self.name())
        self._original = getattr(self, canonicalname, None)
        docstring = """<command> [<args> ...]
        
        Command dispatcher for the %s plugin.  Use 'list %s' to see the
        commands provided by this plugin.  In most cases this dispatcher
        command is unnecessary; in cases where more than one plugin defines a
        given command, use this command to tell the bot which plugin's command
        to use.""" % (self.name(), self.name())
        def dispatcher(self, irc, msg, args):
            def handleBadArgs():
                if self._original:
                    self._original(irc, msg, args)
                else:
                    cb = irc.getCallback('Misc')
                    cb.help(irc, msg, [self.name()])
            if args:
                name = canonicalName(args[0])
                if name == canonicalName(self.name()):
                    handleBadArgs()
                elif self.isCommand(name):
                    del args[0]
                    method = getattr(self, name)
                    try:
                        method(irc, msg, args)
                    except (getopt.GetoptError, ArgumentError):
                        irc.reply(msg, formatArgumentError(method, name))
                else:
                    handleBadArgs()
            else:
                handleBadArgs()
        dispatcher = types.FunctionType(dispatcher.func_code,
                                        dispatcher.func_globals, canonicalname)
        if self._original:
            dispatcher.__doc__ = self._original.__doc__
        else:
            dispatcher.__doc__ = docstring
        setattr(self.__class__, canonicalname, dispatcher)

    def configure(self, irc):
        fakeIrc = ConfigIrcProxy(irc)
        for args in conf.commandsOnStart:
            args = args[:]
            command = canonicalName(args.pop(0))
            if self.isCommand(command):
                #debug.printf('%s: %r' % (command, args))
                method = getattr(self, command)
                line = '%s %s' % (command, ' '.join(map(utils.dqrepr, args)))
                msg = ircmsgs.privmsg(fakeIrc.nick, line, fakeIrc.prefix)
                try:
                    world.startup = True
                    method(fakeIrc, msg, args)
                finally:
                    world.startup = False

    def __call__(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if self.noIgnore or not ircdb.checkIgnored(msg.prefix,msg.args[0]):
                self.__parent.__call__(irc, msg)
            else:
                debug.msg('Ignoring %s.' % msg.prefix)
        else:
            self.__parent.__call__(irc, msg)

    def isCommand(self, methodName):
        # This function is ugly, but I don't want users to call methods like
        # doPrivmsg or __init__ or whatever, and this is good to stop them.
        if hasattr(self, methodName):
            method = getattr(self, methodName)
            if inspect.ismethod(method):
                code = method.im_func.func_code
                return inspect.getargs(code)[0] == self.commandArgs
            else:
                return False
        else:
            return False

    def callCommand(self, f, irc, msg, *L):
        # Exceptions aren't caught here because IrcObjectProxy.finalEval
        # catches them and does The Right Thing.
        Privmsg.handled = True
        start = time.time()
        f(irc, msg, *L)
        elapsed = time.time() - start
        funcname = '%s.%s' % (f.im_class.__name__, f.im_func.func_name)
        debug.msg('%s took %s seconds' % (funcname, elapsed), 'verbose')


class IrcObjectProxyRegexp(object):
    def __init__(self, irc, *args):
        self.irc = irc

    def error(self, msg, s, private=False):
        private = private or conf.errorReplyPrivate
        self.reply(msg, 'Error: ' + s, private=private)

    def reply(self, msg, s, prefixName=True, action=False, private=False,
              notice=False):
        if action:
            self.irc.queueMsg(ircmsgs.action(ircutils.replyTo(msg), s))
        else:
            self.irc.queueMsg(reply(msg, s, private=private, notice=notice,
                                    prefixName=prefixName))

    def __getattr__(self, attr):
        return getattr(self.irc, attr)


class PrivmsgRegexp(Privmsg):
    """A class to allow a person to create regular expression callbacks.

    Much more primitive, but more flexible than the 'normal' method of using
    the Privmsg class and its lexer, PrivmsgRegexp allows you to write
    callbacks that aren't addressed to the bot, for instance.  There are, of
    course, several other possibilities.  Callbacks are registered with a
    string (the regular expression) and a function to be called (with the Irc
    object, the IrcMsg object, and the match object) when the regular
    expression matches.  Callbacks must have the signature (self, irc, msg,
    match) to be counted as such.

    A class-level flags attribute is used to determine what regexp flags to
    compile the regular expressions with.  By default, it's re.I, which means
    regular expressions are by default case-insensitive.

    If you have a standard command-type callback, though, Privmsg is a much
    better class to use, at the very least for consistency's sake, but also
    because it's much more easily coded and maintained.
    """
    flags = re.I
    commandArgs = ['self', 'irc', 'msg', 'match']
    def __init__(self):
        self.__parent = super(PrivmsgRegexp, self)
        self.__parent.__init__()
        self.Proxy = IrcObjectProxyRegexp
        self.res = []
        #for name, value in self.__class__.__dict__.iteritems():
        for name, value in self.__class__.__dict__.items():
            value = getattr(self, name)
            if self.isCommand(name):
                try:
                    r = re.compile(value.__doc__, self.flags)
                    self.res.append((r, value))
                except re.error, e:
                    s = '%s.%s has an invalid regexp %s: %s' % \
                        (self.__class__.__name__, name,
                         value.__doc__, debug.exnToString(e))
                    debug.msg(s)
        self.res.sort(lambda (r1, m1), (r2, m2): cmp(m1.__name__, m2.__name__))

    def callCommand(self, method, irc, msg, *L):
        try:
            self.__parent.callCommand(method, irc, msg, *L)
        except Exception, e:
            debug.recoverableException()
            irc.error(msg, debug.exnToString(e))

    def doPrivmsg(self, irc, msg):
        for (r, method) in self.res:
            spans = sets.Set()
            for m in r.finditer(msg.args[1]):
                # There's a bug in finditer: http://www.python.org/sf/817234
                if m.span() in spans:
                    break
                else:
                    spans.add(m.span())
                proxy = IrcObjectProxyRegexp(irc)
                self.callCommand(method, proxy, msg, m)


class PrivmsgCommandAndRegexp(Privmsg):
    """Same as Privmsg, except allows the user to also include regexp-based
    callbacks.  All regexp-based callbacks must be specified in a sets.Set
    (or list) attribute "regexps".
    """
    flags = re.I
    regexps = ()
    addressedRegexps = ()
    def __init__(self):
        self.__parent = super(PrivmsgCommandAndRegexp, self)
        self.__parent.__init__()
        self.res = []
        self.addressedRes = []
        for name in self.regexps:
            method = getattr(self, name)
            r = re.compile(method.__doc__, self.flags)
            self.res.append((r, method))
        for name in self.addressedRegexps:
            method = getattr(self, name)
            r = re.compile(method.__doc__, self.flags)
            self.addressedRes.append((r, method))

    def callCommand(self, f, irc, msg, *L, **kwargs):
        try:
            self.__parent.callCommand(f, irc, msg, *L)
        except Exception, e:
            if 'catchErrors' in kwargs and kwargs['catchErrors']:
                irc.error(msg, debug.exnToString(e))
                debug.recoverableException()
            else:
                raise

    def doPrivmsg(self, irc, msg):
        for (r, method) in self.res:
            originalHandled = self.handled
            name = method.__name__
            for m in r.finditer(msg.args[1]):
                if originalHandled and name not in self.alwaysCall:
                    continue
                proxy = IrcObjectProxyRegexp(irc)
                self.callCommand(method, proxy, msg, m, catchErrors=True)
        s = addressed(irc.nick, msg)
        if s:
            for (r, method) in self.addressedRes:
                originalHandled = self.handled
                name = method.__name__
                for m in r.finditer(s):
                    if originalHandled and name not in self.alwaysCall:
                        continue
                    proxy = IrcObjectProxyRegexp(irc)
                    self.callCommand(method,proxy,msg,m,catchErrors=True)
            

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
