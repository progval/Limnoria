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

__revision__ = "$Id$"

import fix

import re
import copy
import sets
import time
import shlex
import getopt
import string
import inspect
import textwrap
import threading
from itertools import imap, ifilter
from cStringIO import StringIO

import log
import conf
import utils
import world
import ircdb
import irclib
import ircmsgs
import ircutils

def addressed(nick, msg):
    """If msg is addressed to 'name', returns the portion after the address.
    Otherwise returns the empty string.
    """
    nick = ircutils.toLower(nick)
    if ircutils.nickEqual(msg.args[0], nick):
        if msg.args[1][0] in conf.supybot.prefixChars():
            return msg.args[1][1:].strip()
        else:
            return msg.args[1].strip()
    elif conf.supybot.reply.whenAddressedByNick() and \
         ircutils.toLower(msg.args[1]).startswith(nick):
        try:
            (maybeNick, rest) = msg.args[1].split(None, 1)
            while not ircutils.isNick(maybeNick):
                if maybeNick[-1].isalnum():
                    return ''
                maybeNick = maybeNick[:-1]
            if ircutils.nickEqual(maybeNick, nick):
                return rest
            else:
                return ''
        except ValueError: # split didn't work.
            return ''
    elif msg.args[1] and msg.args[1][0] in conf.supybot.prefixChars():
        return msg.args[1][1:].strip()
    elif conf.supybot.reply.whenNotAddressed():
        return msg.args[1]
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

def reply(msg, s, prefixName=True, private=False, notice=False, to=None):
    """Makes a reply to msg with the payload s"""
    s = ircutils.safeArgument(s)
    to = to or msg.nick
    if ircutils.isChannel(msg.args[0]) and not private:
        if notice or conf.supybot.reply.withPrivateNotice():
            m = ircmsgs.notice(to, s)
        elif prefixName:
            m = ircmsgs.privmsg(msg.args[0], '%s: %s' % (to, s))
        else:
            m = ircmsgs.privmsg(msg.args[0], s)
    else:
        m = ircmsgs.privmsg(to, s)
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
        help = ' '.join(doclines)
        s = '(%s) -- %s' % (ircutils.bold(s), help)
    return utils.normalizeWhitespace(s)

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
            if conf.supybot.pipeSyntax():
                tokens = '|'
            else:
                tokens = ''
            _lastTokenizeResult = Tokenizer(tokens).tokenize(s)
    except ValueError, e:
        _lastTokenized = None
        _lastTokenizedResult = None
        raise SyntaxError, str(e)
    log.debug('tokenize took %s seconds.' % (time.time() - start))
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
        if conf.supybot.showSimpleSyntax():
            return getSyntax(method, name=name)
        else:
            return getHelp(method, name=name)
    else:
        return 'Invalid arguments for %s.' % method.__name__

def checkCommandCapability(msg, cb, command):
    plugin = cb.name().lower()
    pluginCommand = '%s.%s' % (plugin, command)
    def checkCapability(capability):
        assert ircdb.isAntiCapability(capability)
        if ircdb.checkCapability(msg.prefix, capability):
            log.info('Preventing %s from calling %s because of %s.',
                     msg.prefix, pluginCommand, capability)
            raise RuntimeError, capability
    try:
        antiPlugin = ircdb.makeAntiCapability(plugin)
        antiCommand = ircdb.makeAntiCapability(command)
        antiPluginCommand = ircdb.makeAntiCapability(pluginCommand)
        checkCapability(antiPlugin)
        checkCapability(antiCommand)
        checkCapability(antiPluginCommand)
        checkAtEnd = [command, pluginCommand]
        default = conf.supybot.defaultAllow()
        if ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
            checkCapability(ircdb.makeChannelCapability(channel, antiCommand))
            checkCapability(ircdb.makeChannelCapability(channel, antiPlugin))
            checkCapability(ircdb.makeChannelCapability(channel,
                                                        antiPluginCommand))
            chanPlugin = ircdb.makeChannelCapability(channel, plugin)
            chanCommand = ircdb.makeChannelCapability(channel, command)
            chanPluginCommand = ircdb.makeChannelCapability(channel,
                                                            pluginCommand)
            checkAtEnd += [chanCommand, chanPluginCommand]
            default &= ircdb.channels.getChannel(channel).defaultAllow
        return not (default or \
                    any(lambda x: ircdb.checkCapability(msg.prefix, x),
                        checkAtEnd))
    except RuntimeError, e:
        s = ircdb.unAntiCapability(str(e))
        return s



class RichReplyMethods(object):
    """This is a mixin so these replies need only be defined once."""
    def __makeReply(self, prefix, s):
        if s:
            s = '%s  %s' % (prefix, s)
        else:
            s = prefix
        return s

    def replySuccess(self, s='', **kwargs):
        v = conf.supybot.replies.success.get(self.msg.args[0])()
        s = self.__makeReply(v, s)
        self.reply(s, **kwargs)

    def replyError(self, s='', **kwargs):
        v = conf.supybot.replies.error.get(self.msg.args[0])()
        s = self.__makeReply(v, s)
        self.reply(s, **kwargs)

    def replies(self, L, prefixer=''.join,
                joiner=utils.commaAndify, onlyPrefixFirst=False):
        if prefixer is None:
            prefixer = ''
        if joiner is None:
            joiner = utils.commaAndify
        if isinstance(prefixer, basestring):
            prefixer = prefixer.__add__
        if isinstance(joiner, basestring):
            joiner = joiner.join
        if conf.supybot.reply.oneToOne():
            self.reply(prefixer(joiner(L)))
        else:
            first = True
            for s in L:
                if onlyPrefixFirst:
                    if first:
                        self.reply(prefixer(s))
                        first = False
                    else:
                        self.reply(s)
                else:
                    self.reply(prefixer(s))

    def errorNoCapability(self, capability, s='', **kwargs):
        if isinstance(capability, basestring): # checkCommandCapability!
            log.warning('Denying %s for lacking %r capability',
                        self.msg.prefix, capability)
            if not conf.supybot.reply.noCapabilityError():
                v = conf.supybot.replies.noCapability.get(self.msg.args[0])()
                s = self.__makeReply(v % capability, s)
                self.error(s, **kwargs)
        else:
            log.warning('Denying %s for some unspecified capability '
                        '(or a default)', self.msg.prefix)
            v = conf.supybot.replies.genericNoCapability.get(msg.args[0])()
            self.error(self.__makeReply(v, s), **kwargs)

    def errorPossibleBug(self, s='', **kwargs):
        v = conf.supybot.replies.possibleBug.get(self.msg.args[0])()
        if s:
            s += '  (%s)' % v
        else:
            s = v
        self.error(s, **kwargs)

    def errorNotRegistered(self, s='', **kwargs):
        v = conf.supybot.replies.notRegistered.get(self.msg.args[0])()
        self.error(self.__makeReply(v, s), **kwargs)

    def errorNoUser(self, s='', **kwargs):
        v = conf.supybot.replies.noUser.get(self.msg.args[0])()
        self.error(self.__makeReply(v, s), **kwargs)

    def errorRequiresPrivacy(self, s='', **kwargs):
        v = conf.supybot.replies.requiresPrivacy.get(self.msg.args[0])()
        self.error(self.__makeReply(v, s), **kwargs)

            
class IrcObjectProxy(RichReplyMethods):
    "A proxy object to allow proper nested of commands (even threaded ones)."
    def __init__(self, irc, msg, args):
        log.debug('IrcObjectProxy.__init__: %s' % args)
        self.irc = irc
        self.msg = msg
        # The deepcopy here is necessary for Scheduler; it re-runs already
        # tokenized commands.
        self.args = copy.deepcopy(args)
        self.counter = 0
        self.to = None
        self.action = False
        self.notice = False
        self.private = False
        self.finished = False
        self.prefixName = conf.supybot.reply.withNickPrefix()
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
        if ircutils.isCtcp(self.msg):
            log.debug('Skipping invalidCommand, msg is CTCP.')
            return
        log.debug('Calling invalidCommands.')
        for cb in self.irc.callbacks:
            log.debug('Trying to call %s.invalidCommand' % cb.name())
            if self.finished:
                log.debug('Finished calling invalidCommand: %s', cb.name())
                return
            if hasattr(cb, 'invalidCommand'):
                cb.invalidCommand(self, self.msg, self.args)

    def _callCommand(self, name, command, cb):
        try:
            cb.callCommand(command, self, self.msg, self.args)
        except (getopt.GetoptError, ArgumentError):
            self.reply(formatArgumentError(command, name=name))
        except CannotNest, e:
            if not isinstance(self.irc, irclib.Irc):
                self.error('Command %r cannot be nested.' % name)
        except (SyntaxError, Error), e:
            cb.log.info('Error return: %s', e)
            self.error(str(e))
        except Exception, e:
            cb.log.exception('Uncaught exception:')
            if conf.supybot.reply.detailedErrors():
                self.error(utils.exnToString(e))
            else:
                self.replyError()
            
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
                    for (r, m) in cb.res:
                        if r.search(self.msg.args[1]):
                            log.debug('Skipping invalidCommand: %s.%s',
                                      m.im_class.__name__,m.im_func.func_name)
                            return
                elif isinstance(cb, PrivmsgCommandAndRegexp):
                    for (r, m) in cb.res:
                        if r.search(self.msg.args[1]):
                            log.debug('Skipping invalidCommand: %s.%s',
                                      m.im_class.__name__,m.im_func.func_name)
                            return
                    payload = addressed(self.irc.nick, self.msg)
                    for (r, m) in cb.addressedRes:
                        if r.search(payload):
                            log.debug('Skipping invalidCommand: %s.%s',
                                      m.im_class.__name__,m.im_func.func_name)
                            return
            # Ok, no regexp-based things matched.
            self._callInvalidCommands()
        else:
            if len(cbs) > 1:
                for cb in cbs:
                    if cb.name().lower() == name:
                        break
                else:
                    # This should've been caught earlier, that's why we
                    # assert instead of raising a ValueError or something.
                    assert False, 'Non-disambiguated command.'
            else:
                del self.args[0]
                cb = cbs[0]
            cap = checkCommandCapability(self.msg, cb, name)
            if cap:
                self.errorNoCapability(cap)
                return
            command = getattr(cb, name)
            Privmsg.handled = True
            if cb.threaded or conf.supybot.threadAllCommands():
                t = CommandThread(target=self._callCommand,
                                  args=(name, command, cb))
                t.start()
            else:
                self._callCommand(name, command, cb)

    def reply(self, s, noLengthCheck=False, prefixName=True,
              action=False, private=False, notice=False, to=None):
        """reply(s) -> replies to msg with s

        Keyword arguments:
          noLengthCheck=False: True if the length shouldn't be checked
                               (used for 'more' handling)
          prefixName=True:     False if the nick shouldn't be prefixed to the
                               reply.
          action=False:        True if the reply should be an action.
          private=False:       True if the reply should be in private.
          notice=False:        True if the reply should be noticed when the
                               bot is configured to do so.
          to=<nick|channel>:   The nick or channel the reply should go to.
                               Defaults to msg.args[0] (or msg.nick if private)
        """
        # These use and or or based on whether or not they default to True or
        # False.  Those that default to True use and; those that default to
        # False use or.
        assert not isinstance(s, ircmsgs.IrcMsg), \
               'Old code alert: there is no longer a "msg" argument to reply.'
        msg = self.msg
        self.action = action or self.action
        self.notice = notice or self.notice
        self.private = private or self.private
        self.to = to or self.to
        self.prefixName = prefixName or self.prefixName
        self.noLengthCheck = noLengthCheck or self.noLengthCheck
        if self.finalEvaled:
            if isinstance(self.irc, self.__class__):
                self.irc.reply(s, self.noLengthCheck, self.prefixName,
                               self.action, self.private, self.notice, self.to)
            elif self.noLengthCheck:
                self.irc.queueMsg(reply(msg, s, self.prefixName,
                                        self.private, self.notice, self.to))
            elif self.action:
                if self.private:
                    target = msg.nick
                else:
                    target = msg.args[0]
                if self.to:
                    target = self.to
                self.irc.queueMsg(ircmsgs.action(target, s))
            else:
                s = ircutils.safeArgument(s)
                allowedLength = 450 - len(self.irc.prefix)
                if len(s) > allowedLength*50:
                    log.warning('Cowardly refusing to "more" %s bytes.'%len(s))
                    s = s[:allowedLength*50]
                if len(s) < allowedLength:
                    self.irc.queueMsg(reply(msg, s, self.prefixName,
                                            self.private,self.notice,self.to))
                    self.finished = True
                    return
                msgs = textwrap.wrap(s, allowedLength-30) # -30 is for "nick:"
                msgs.reverse()
                response = msgs.pop()
                if msgs:
                    n = ircutils.bold('(%s)')
                    n %= utils.nItems('message', len(msgs), 'more')
                    response = '%s %s' % (response, n)
                prefix = msg.prefix
                if self.to and ircutils.isNick(self.to):
                    ### TODO: catch this KeyError.
                    prefix = self.getRealIrc().state.nickToHostmask(self.to)
                mask = prefix.split('!', 1)[1]
                Privmsg._mores[mask] = msgs
                private = self.private or not ircutils.isChannel(msg.args[0])
                Privmsg._mores[msg.nick] = (private, msgs)
                self.irc.queueMsg(reply(msg, response, self.prefixName,
                                        self.private, self.notice, self.to))
            self.finished = True
        else:
            self.args[self.counter] = s
            self.evalArgs()

    def error(self, s, private=False):
        """error(text) -> replies to msg with an error message of text.

        Keyword arguments:
          private=False: True if the error should be given in private.
        """
        if isinstance(self.irc, self.__class__):
            self.irc.error(s, private)
        else:
            s = 'Error: ' + s
            if private or conf.supybot.reply.errorInPrivate():
                self.irc.queueMsg(ircmsgs.privmsg(self.msg.nick, s))
            else:
                self.irc.queueMsg(reply(self.msg, s))
        self.finished = True

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
    def __init__(self, target=None, args=None):
        (self.name, self.command, self.cb) = args
        world.threadsSpawned += 1
        threadName = 'Thread #%s for %s.%s' % (world.threadsSpawned,
                                               self.cb.name(), self.name)
        log.debug('Spawning thread %s' % threadName)
        threading.Thread.__init__(self, target=target,
                                  name=threadName, args=args)
        self.setDaemon(True)
        self.originalThreaded = self.cb.threaded
        self.cb.threaded = True

    def run(self):
        try:
            threading.Thread.run(self)
        finally:
            self.cb.threaded = self.originalThreaded


class ConfigIrcProxy(RichReplyMethods):
    """Used as a proxy Irc object during configuration. """
    def __init__(self, irc):
        self.__dict__['irc'] = irc
        
    def reply(self, s, *args, **kwargs):
        assert not isinstance(s, ircmsgs.IrcMsg), \
               'Old code alert: there is no longer a "msg" argument to reply.'
        return None

    def error(self, s, *args, **kwargs):
        log.warning('ConfigIrcProxy saw an error: %s' % s)

    def getRealIrc(self):
        irc = self.__dict__['irc']
        if hasattr(irc, 'getRealIrc'):
            return irc.getRealIrc()
        else:
            return irc

    def __getattr__(self, attr):
        return getattr(self.getRealIrc(), attr)

    def __setattr__(self, attr, value):
        setattr(self.getRealIrc(), attr, value)

    
class Privmsg(irclib.IrcCallback):
    """Base class for all Privmsg handlers."""
    __metaclass__ = log.MetaFirewall
    __firewalled__ = {'invalidCommand': None} # Eventually callCommand.
    threaded = False
    public = True
    alwaysCall = ()
    noIgnore = False
    handled = False
    errored = False
    Proxy = IrcObjectProxy
    commandArgs = ['self', 'irc', 'msg', 'args']
    # This must be class-scope, so all subclasses use the same one.
    _mores = ircutils.IrcDict()
    def __init__(self):
        self.__parent = super(Privmsg, self)
        myName = self.name()
        self.log = log.getPluginLogger(myName)
        ### Setup the dispatcher command.
        canonicalname = canonicalName(myName)
        self._original = getattr(self, canonicalname, None)
        docstring = """<command> [<args> ...]
        
        Command dispatcher for the %s plugin.  Use 'list %s' to see the
        commands provided by this plugin.  In most cases this dispatcher
        command is unnecessary; in cases where more than one plugin defines a
        given command, use this command to tell the bot which plugin's command
        to use.""" % (myName, myName)
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
                    cap = checkCommandCapability(msg, self, name)
                    if cap:
                        irc.errorNoCapability(cap)
                        return
                    del args[0]
                    method = getattr(self, name)
                    try:
                        method(irc, msg, args)
                    except (getopt.GetoptError, ArgumentError):
                        irc.reply(formatArgumentError(method, name))
                else:
                    handleBadArgs()
            else:
                handleBadArgs()
        dispatcher = utils.changeFunctionName(dispatcher, canonicalname)
        if self._original:
            dispatcher.__doc__ = self._original.__doc__
        else:
            dispatcher.__doc__ = docstring
        setattr(self.__class__, canonicalname, dispatcher)

    def __call__(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if self.noIgnore or not ircdb.checkIgnored(msg.prefix,msg.args[0]):
                self.__parent.__call__(irc, msg)
            else:
                # We want this to be under logging.DEBUG: it's not very useful,
                # even for debugging things :)
                self.log.log(0, 'Ignoring %s', msg.prefix)
        else:
            self.__parent.__call__(irc, msg)

    def isCommand(self, methodName):
        """Returns whether a given method name is a command in this plugin."""
        # This function is ugly, but I don't want users to call methods like
        # doPrivmsg or __init__ or whatever, and this is good to stop them.

        # Don't canonicalize this name: consider outFilter(self, irc, msg).
        # methodName = canonicalName(methodName)
        if hasattr(self, methodName):
            method = getattr(self, methodName)
            if inspect.ismethod(method):
                code = method.im_func.func_code
                return inspect.getargs(code)[0] == self.commandArgs
            else:
                return False
        else:
            return False

    def getCommand(self, methodName):
        """Gets the given command from this plugin."""
        assert self.isCommand(methodName)
        methodName = canonicalName(methodName)
        return getattr(self, methodName)

    def callCommand(self, method, irc, msg, *L):
        name = method.im_func.func_name
        assert L, 'Odd, nothing in L.  This can\'t happen.'
        self.log.info('Command %s called with args %s by %s',
                      name, L[0], msg.prefix)
        start = time.time()
        method(irc, msg, *L)
        elapsed = time.time() - start
        self.log.info('%s took %s seconds', name, elapsed)

    def registryValue(self, name, channel=None):
        plugin = self.name()
        group = conf.supybot.plugins.get(plugin)
        names = name.split('.')
        for name in names:
            group = group.get(name)
        if channel is None:
            return group()
        else:
            return group.get(channel)()


class IrcObjectProxyRegexp(RichReplyMethods):
    def __init__(self, irc, msg):
        self.irc = irc
        self.msg = msg

    def error(self, s, **kwargs):
        self.reply('Error: ' + s, **kwargs)

    def reply(self, s, action=False, **kwargs): 
        assert not isinstance(s, ircmsgs.IrcMsg), \
               'Old code alert: there is no longer a "msg" argument to reply.'
        if action:
            self.irc.queueMsg(ircmsgs.action(ircutils.replyTo(self.msg), s))
        else:
            self.irc.queueMsg(reply(self.msg, s, **kwargs))

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
    Proxy = IrcObjectProxyRegexp
    commandArgs = ['self', 'irc', 'msg', 'match']
    def __init__(self):
        self.__parent = super(PrivmsgRegexp, self)
        self.__parent.__init__()
        self.res = []
        #for name, value in self.__class__.__dict__.iteritems():
        for name, value in self.__class__.__dict__.items():
            value = getattr(self, name)
            if self.isCommand(name):
                try:
                    r = re.compile(value.__doc__, self.flags)
                    self.res.append((r, value))
                except re.error, e:
                    self.log.warning('Invalid regexp: %r (%s)',value.__doc__,e)
        self.res.sort(lambda (r1, m1), (r2, m2): cmp(m1.__name__, m2.__name__))

    def callCommand(self, method, irc, msg, *L):
        try:
            self.__parent.callCommand(method, irc, msg, *L)
        except Exception, e:
            # We catch exceptions here because IrcObjectProxy isn't doing our
            # dirty work for us anymore.
            self.log.exception('Uncaught exception from callCommand:')
            if conf.supybot.reply.detailedErrors():
                irc.error(utils.exnToString(e))
            else:
                irc.replyError()

    def doPrivmsg(self, irc, msg):
        if Privmsg.errored:
            self.log.info('%s not running due to Privmsg.errored.',
                          self.name())
            return
        for (r, method) in self.res:
            spans = sets.Set()
            for m in r.finditer(msg.args[1]):
                # There's a bug in finditer: http://www.python.org/sf/817234
                if m.span() in spans:
                    break
                else:
                    spans.add(m.span())
                proxy = self.Proxy(irc, msg)
                self.callCommand(method, proxy, msg, m)


class PrivmsgCommandAndRegexp(Privmsg):
    """Same as Privmsg, except allows the user to also include regexp-based
    callbacks.  All regexp-based callbacks must be specified in a sets.Set
    (or list) attribute "regexps".
    """
    flags = re.I
    regexps = ()
    addressedRegexps = ()
    Proxy = IrcObjectProxyRegexp
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
                self.log.exception('Uncaught exception in callCommand:')
                if conf.supybot.reply.detailedErrors():
                    irc.error(utils.exnToString(e))
                else:
                    irc.replyError()
            else:
                raise

    def doPrivmsg(self, irc, msg):
        if Privmsg.errored:
            self.log.info('%s not running due to Privmsg.errored.',
                          self.name())
            return
        for (r, method) in self.res:
            name = method.__name__
            for m in r.finditer(msg.args[1]):
                proxy = self.Proxy(irc, msg)
                self.callCommand(method, proxy, msg, m, catchErrors=True)
        if not Privmsg.handled:
            s = addressed(irc.nick, msg)
            if s:
                for (r, method) in self.addressedRes:
                    name = method.__name__
                    if Privmsg.handled and name not in self.alwaysCall:
                        continue
                    for m in r.finditer(s):
                        proxy = self.Proxy(irc, msg)
                        self.callCommand(method,proxy,msg,m,catchErrors=True)
                        Privmsg.handled = True
            

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
