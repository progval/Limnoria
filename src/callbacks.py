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
This module contains the basic callbacks for handling PRIVMSGs.  Both Privmsg
and PrivmsgRegexp classes are provided; for offering callbacks based on
commands and their arguments (much like *nix command line programs) use the
Privmsg class; for offering callbacks based on regular expressions, use the
PrivmsgRegexp class.  Read their respective docstrings for more information on
how to use them.
"""

__revision__ = "$Id$"

import supybot.fix as fix

import re
import copy
import sets
import time
import shlex
import getopt
import string
import inspect
import threading
from cStringIO import StringIO
from itertools import imap, ifilter

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
import supybot.irclib as irclib
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry

def addressed(nick, msg, prefixChars=None,
              prefixStrings=None, whenAddressedByNick=None):
    """If msg is addressed to 'name', returns the portion after the address.
    Otherwise returns the empty string.
    """
    def get(group):
        if ircutils.isChannel(target):
            group = group.get(target)
        return group()
    def stripPrefixStrings(payload):
        for prefixString in prefixStrings:
            if payload.startswith(prefixString):
                payload = payload[len(prefixString):].lstrip()
        return payload

    assert msg.command == 'PRIVMSG'
    (target, payload) = msg.args
    if prefixChars is None:
        prefixChars = get(conf.supybot.reply.whenAddressedBy.chars)
    if whenAddressedByNick is None:
        whenAddressedByNick = get(conf.supybot.reply.whenAddressedBy.nick)
    if prefixStrings is None:
        prefixStrings = get(conf.supybot.reply.whenAddressedBy.strings)
    nick = ircutils.toLower(nick)
    # Ok, let's see if it's a private message.
    if ircutils.nickEqual(target, nick):
        payload = stripPrefixStrings(payload)
        while payload and payload[0] in prefixChars:
            payload = payload[1:].lstrip()
        return payload
    # Ok, not private.  Does it start with our nick?
    elif whenAddressedByNick and \
         ircutils.toLower(payload).startswith(nick):
        try:
            (maybeNick, rest) = payload.split(None, 1)
            while not ircutils.isNick(maybeNick, strictRfc=True):
                if maybeNick[-1].isalnum():
                    return ''
                maybeNick = maybeNick[:-1]
            if ircutils.nickEqual(maybeNick, nick):
                return rest
            else:
                return ''
        except ValueError: # split didn't work.
            return ''
    elif payload and any(payload.startswith, prefixStrings):
        return stripPrefixStrings(payload)
    elif payload and payload[0] in prefixChars:
        return payload[1:].strip()
    elif conf.supybot.reply.whenNotAddressed():
        return payload
    else:
        return ''

def canonicalName(command):
    """Turn a command into its canonical form.

    Currently, this makes everything lowercase and removes all dashes and
    underscores.
    """
    if isinstance(command, unicode):
        command = command.encode('utf-8')
    special = '\t -_'
    reAppend = ''
    while command and command[-1] in special:
        reAppend = command[-1] + reAppend
        command = command[:-1]
    return command.translate(string.ascii, special).lower() + reAppend

def reply(msg, s, prefixName=True, private=None,
          notice=None, to=None, action=None, error=False):
    # Ok, let's make the target:
    target = ircutils.replyTo(msg)
    def getConfig(wrapper):
        if ircutils.isChannel(target):
            return wrapper.get(target)()
        else:
            return wrapper()
    if ircutils.isChannel(target):
        channel = target
    else:
        channel = None
    if notice is None:
        notice = getConfig(conf.supybot.reply.withNotice)
    if private is None:
        private = getConfig(conf.supybot.reply.inPrivate)
    if error:
        notice = getConfig(conf.supybot.reply.errorWithNotice) or notice
        private = getConfig(conf.supybot.reply.errorInPrivate) or private
        s = 'Error: ' + s
    if private:
        prefixName = False
        if to is None:
            target = msg.nick
        else:
            target = to
        # XXX: User value for reply.withNoticeWhenPrivate.
        if conf.supybot.reply.withNoticeWhenPrivate(): # global, no getConfig.
            notice = True
    if to is None:
        to = msg.nick
    # Ok, now let's make the payload:
    s = ircutils.safeArgument(s)
    if not s and not action:
        s = 'Error: I tried to send you an empty message.'
    if prefixName and ircutils.isChannel(target):
        # Let's may sure we don't do, "#channel: foo.".
        if not ircutils.isChannel(to):
            s = '%s: %s' % (to, s)
    # And now, let's decide whether it's a PRIVMSG or a NOTICE.
    msgmaker = ircmsgs.privmsg
    if notice:
        msgmaker = ircmsgs.notice
    # We don't use elif here because actions can't be sent as NOTICEs.
    if action:
        msgmaker = ircmsgs.action
    # Finally, we'll return the actual message.
    return msgmaker(target, s)

def error(msg, s, **kwargs):
    """Makes an error reply to msg with the appropriate error payload."""
    kwargs['error'] = True
    return reply(msg, s, **kwargs)

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
    validChars = string.ascii.translate(string.ascii, '\x00\r\n \t"')
    quotes = '"'
    def __init__(self, tokens=''):
        # Add a '|' to tokens to have the pipe syntax.
        self.validChars = self.validChars.translate(string.ascii, tokens)
        if len(tokens) >= 2:
            self.left = tokens[0]
            self.right = tokens[1]
        else:
            self.left = ''
            self.right = ''

    def _handleToken(self, token):
        if token[0] == token[-1] and token[0] in self.quotes:
            token = token[1:-1]
            token = token.decode('string-escape')
        return token

    def _insideBrackets(self, lexer):
        ret = []
        firstToken = True
        while True:
            token = lexer.get_token()
            if not token:
                raise SyntaxError, 'Missing "%s".  You may want to ' \
                                   'quote your arguments with double ' \
                                   'quotes in order to prevent extra ' \
                                   'brackets from being evaluated ' \
                                   'as nested commands.' % self.right
            elif token == self.right:
                return ret
            elif token == self.left:
                if firstToken:
                    s = 'The command called may not be the result ' \
                        'of a nested command.'
                    raise SyntaxError, 'The command called may not be the ' \
                                       'result or a nested command.'
                ret.append(self._insideBrackets(lexer))
            else:
                ret.append(self._handleToken(token))
            firstToken = False
        return ret

    def tokenize(self, s):
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
            elif token == '|' and conf.supybot.reply.pipeSyntax():
                if not args:
                    raise SyntaxError, '"|" with nothing preceding.  I ' \
                                       'obviously can\'t do a pipe with ' \
                                       'nothing before the |.'
                ends.append(args)
                args = []
            elif token == self.left:
                args.append(self._insideBrackets(lexer))
            elif token == self.right:
                raise SyntaxError, 'Spurious "%s".  You may want to ' \
                                   'quote your arguments with double ' \
                                   'quotes in order to prevent extra ' \
                                   'brackets from being evaluated ' \
                                   'as nested commands.' % self.right
            else:
                args.append(self._handleToken(token))
        if ends:
            if not args:
                raise SyntaxError, '"|" with nothing following.  I ' \
                                   'obviously can\'t do a pipe with ' \
                                   'nothing before the |.'
            args.append(ends.pop())
            while ends:
                args[-1].append(ends.pop())
        return args

def tokenize(s, brackets=None, channel=None):
    """A utility function to create a Tokenizer and tokenize a string."""
    start = time.time()
    try:
        if brackets is None:
            tokens = conf.channelValue(conf.supybot.reply.brackets, channel)
        else:
            tokens = brackets
        if conf.channelValue(conf.supybot.reply.pipeSyntax, channel):
            tokens = '%s|' % tokens
        log.stat('tokenize took %s seconds.' % (time.time() - start))
        return Tokenizer(tokens).tokenize(s)
    except ValueError, e:
        raise SyntaxError, str(e)

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

def formatArgumentError(method, name=None, channel=None):
    if name is None:
        name = method.__name__
    if hasattr(method, '__doc__') and method.__doc__:
        if conf.channelValue(conf.supybot.reply.showSimpleSyntax, channel):
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
        default = conf.supybot.capabilities.default()
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
            checkAtEnd += [chanCommand, chanPlugin, chanPluginCommand]
            default &= ircdb.channels.getChannel(channel).defaultAllow
        return not (default or \
                    any(lambda x: ircdb.checkCapability(msg.prefix, x),
                        checkAtEnd))
    except RuntimeError, e:
        s = ircdb.unAntiCapability(str(e))
        return s


class RichReplyMethods(object):
    """This is a mixin so these replies need only be defined once.  It operates
    under several assumptions, including the fact that 'self' is an Irc object
    of some sort and there is a self.msg that is an IrcMsg."""
    def __makeReply(self, prefix, s):
        if s:
            s = '%s  %s' % (prefix, s)
        else:
            s = prefix
        return plugins.standardSubstitute(self, self.msg, s)

    def _getConfig(self, wrapper):
        return wrapper.get(self.msg.args[0])()
    
    def replySuccess(self, s='', **kwargs):
        v = self._getConfig(conf.supybot.replies.success)
        s = self.__makeReply(v, s)
        self.reply(s, **kwargs)

    def replyError(self, s='', **kwargs):
        v = self._getConfig(conf.supybot.replies.error)
        s = self.__makeReply(v, s)
        self.reply(s, **kwargs)

    def replies(self, L, prefixer=None, joiner=None,
                onlyPrefixFirst=False, **kwargs):
        if prefixer is None:
            prefixer = ''
        if joiner is None:
            joiner = utils.commaAndify
        if isinstance(prefixer, basestring):
            prefixer = prefixer.__add__
        if isinstance(joiner, basestring):
            joiner = joiner.join
        if conf.supybot.reply.oneToOne():
            self.reply(prefixer(joiner(L)), **kwargs)
        else:
            first = True
            for s in L:
                if onlyPrefixFirst:
                    if first:
                        self.reply(prefixer(s), **kwargs)
                        first = False
                    else:
                        self.reply(s, **kwargs)
                else:
                    self.reply(prefixer(s), **kwargs)

    def _error(self, s, Raise, **kwargs):
        if Raise:
            raise Error, s
        else:
            self.error(s, **kwargs)

    def errorNoCapability(self, capability, s='', Raise=False, **kwargs):
        if isinstance(capability, basestring): # checkCommandCapability!
            log.warning('Denying %s for lacking %r capability.',
                        self.msg.prefix, capability)
            if not self._getConfig(conf.supybot.reply.noCapabilityError):
                v = self._getConfig(conf.supybot.replies.noCapability)
                s = self.__makeReply(v % capability, s)
                self._error(s, Raise, **kwargs)
        else:
            log.warning('Denying %s for some unspecified capability '
                        '(or a default).', self.msg.prefix)
            v = self._getConfig(conf.supybot.replies.genericNoCapability)
            self._error(self.__makeReply(v, s), Raise, **kwargs)

    def errorPossibleBug(self, s='', Raise=False, **kwargs):
        v = self._getConfig(conf.supybot.replies.possibleBug)
        if s:
            s += '  (%s)' % v
        else:
            s = v
        self._error(s, Raise, **kwargs)

    def errorNotRegistered(self, s='', Raise=False, **kwargs):
        v = self._getConfig(conf.supybot.replies.notRegistered)
        self._error(self.__makeReply(v, s), Raise, **kwargs)

    def errorNoUser(self, s='', name='that user', Raise=False, **kwargs):
        v = self._getConfig(conf.supybot.replies.noUser)
        try:
            v = v % name
        except TypeError:
            log.warning('supybot.replies.noUser should have one "%s" in it.')
        self._error(self.__makeReply(v, s), Raise, **kwargs)

    def errorRequiresPrivacy(self, s='', Raise=False, **kwargs):
        v = self._getConfig(conf.supybot.replies.requiresPrivacy)
        self._error(self.__makeReply(v, s), Raise, **kwargs)


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
        self.finished = False # Used in _callInvalidCommands.
        self.commandMethod = None # Used in error.
        self._resetReplyAttributes()
        if not args:
            self.finalEvaled = True
            self._callInvalidCommands()
        else:
            self.finalEvaled = False
            world.commandsProcessed += 1
            self.evalArgs()

    def _resetReplyAttributes(self):
        self.to = None
        self.action = None
        self.notice = None
        self.private = None
        self.noLengthCheck = None
        self.prefixName = conf.supybot.reply.withNickPrefix()

    def evalArgs(self):
        while self.counter < len(self.args):
            if type(self.args[self.counter]) == str:
                self.counter += 1
            else:
                IrcObjectProxy(self, self.msg, self.args[self.counter])
                return
        self.finalEval()

    def _callInvalidCommands(self):
        if ircmsgs.isCtcp(self.msg):
            log.debug('Skipping invalidCommand, msg is CTCP.')
            return
        log.debug('Calling invalidCommands.')
        for cb in self.irc.callbacks:
            log.debug('Trying to call %s.invalidCommand.' % cb.name())
            if self.finished:
                log.debug('Finished calling invalidCommand: %s.', cb.name())
                return
            if hasattr(cb, 'invalidCommand'):
                try:
                    # I think I took out this try/except block because we
                    # firewalled invalidCommand, but we've no guarantee that
                    # other classes won't have firewalled it.  Better safe
                    # than sorry, I say.
                    cb.invalidCommand(self, self.msg, self.args)
                except Exception, e:
                    log.exception('Uncaught exception in %s.invalidCommand',
                                  cb.name())

    def _callCommand(self, name, command, cb):
        try:
            self.commandMethod = command
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
        finally:
            self.commandMethod = None

    def finalEval(self):
        assert not self.finalEvaled, 'finalEval called twice.'
        self.finalEvaled = True
        name = canonicalName(self.args[0])
        cbs = findCallbackForCommand(self, name)
        if len(cbs) == 0:
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
                    if canonicalName(cb.name()) == name:
                        del self.args[0]
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
            if cb.threaded or conf.supybot.debug.threadAllCommands():
                t = CommandThread(target=self._callCommand,
                                  args=(name, command, cb))
                t.start()
            else:
                self._callCommand(name, command, cb)

    def reply(self, s, noLengthCheck=False, prefixName=True,
              action=None, private=None, notice=None, to=None, msg=None):
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
        if msg is None:
            msg = self.msg
        if action is not None:
            self.action = self.action or action
        if notice is not None:
            self.notice = self.notice or notice
        if private is not None:
            self.private = self.private or private
        if to is not None:
            self.to = self.to or to
        # action=True implies noLengthCheck=True and prefixName=False
        self.prefixName = prefixName and self.prefixName and not self.action
        self.noLengthCheck=noLengthCheck or self.noLengthCheck or self.action
        if self.finalEvaled:
            try:
                if not isinstance(self.irc, irclib.Irc):
                    self.irc.reply(s, to=self.to,
                                   notice=self.notice,
                                   action=self.action,
                                   private=self.private,
                                   prefixName=self.prefixName,
                                   noLengthCheck=self.noLengthCheck)
                elif self.noLengthCheck:
                    # noLengthCheck only matters to IrcObjectProxy, so it's not
                    # used here.  Just in case you were wondering.
                    self.irc.queueMsg(reply(msg, s, to=self.to,
                                            notice=self.notice,
                                            action=self.action,
                                            private=self.private,
                                            prefixName=self.prefixName))
                else:
                    s = ircutils.safeArgument(s)
                    allowedLength = 450 - len(self.irc.prefix)
                    maximumMores = conf.supybot.reply.mores.maximum()
                    maximumLength = allowedLength * maximumMores
                    if len(s) > maximumLength:
                        log.warning('Truncating to %s bytes from %s bytes.',
                                    maximumLength, len(s))
                        s = s[:maximumLength]
                    if len(s) < allowedLength or conf.supybot.reply.truncate():
                        # In case we're truncating, we add 20 to allowedLength,
                        # because our allowedLength is shortened for the
                        # "(XX more messages)" trailer.
                        s = s[:allowedLength+20]
                        # There's no need for action=self.action here because
                        # action implies noLengthCheck, which has already been
                        # handled.  Let's stick an assert in here just in case.
                        assert not self.action
                        self.irc.queueMsg(reply(msg, s, to=self.to,
                                                notice=self.notice,
                                                private=self.private,
                                                prefixName=self.prefixName))
                        self.finished = True
                        return
                    msgs = ircutils.wrap(s, allowedLength-30) # -30 is for nick:
                    msgs.reverse()
                    instant = conf.supybot.reply.mores.instant()
                    while instant > 1 and msgs:
                        instant -= 1
                        response = msgs.pop()
                        self.irc.queueMsg(reply(msg, response, to=self.to,
                                                notice=self.notice,
                                                private=self.private,
                                                prefixName=self.prefixName))
                    if not msgs:
                        return
                    response = msgs.pop()
                    if msgs:
                        n = ircutils.bold('(%s)')
                        n %= utils.nItems('message', len(msgs), 'more')
                        response = '%s %s' % (response, n)
                    prefix = msg.prefix
                    if self.to and ircutils.isNick(self.to):
                        try:
                            state = self.getRealIrc().state
                            prefix = state.nickToHostmask(self.to)
                        except KeyError:
                            pass # We'll leave it as it is.
                    mask = prefix.split('!', 1)[1]
                    Privmsg._mores[mask] = msgs
                    public = ircutils.isChannel(msg.args[0])
                    private = self.private or not public
                    Privmsg._mores[msg.nick] = (private, msgs)
                    self.irc.queueMsg(reply(msg, response, to=self.to,
                                            action=self.action,
                                            notice=self.notice,
                                            private=self.private,
                                            prefixName=self.prefixName))
                self.finished = True
            finally:
                self._resetReplyAttributes()
        else:
            self.args[self.counter] = s
            self.evalArgs()

    def error(self, s='', Raise=False, **kwargs):
        if Raise:
            if s:
                raise Error, s
            else:
                raise ArgumentError
        if s:
            if not isinstance(self.irc, irclib.Irc):
                self.irc.error(s, **kwargs)
            else:
                self.irc.queueMsg(error(self.msg, s, **kwargs))
        else:
            if self.commandMethod is not None:
                # We can recurse here because it only gets called once.
                self.error(formatArgumentError(self.commandMethod), **kwargs)
            else:
                raise ArgumentError # We shouldn't get here, but just in case.
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
    def __init__(self, target=None, args=(), kwargs={}):
        (self.name, self.command, self.cb) = args
        world.threadsSpawned += 1
        threadName = 'Thread #%s (for %s.%s)' % (world.threadsSpawned,
                                                 self.cb.name(), self.name)
        log.debug('Spawning thread %s' % threadName)
        threading.Thread.__init__(self, target=target,
                                  name=threadName, args=args, kwargs=kwargs)
        self.setDaemon(True)
        self.originalThreaded = self.cb.threaded
        self.cb.threaded = True

    def run(self):
        try:
            threading.Thread.run(self)
        finally:
            self.cb.threaded = self.originalThreaded


class CanonicalString(registry.NormalizedString):
    def normalize(self, s):
        return canonicalName(s)

class CanonicalNameSet(utils.NormalizingSet):
    def normalize(self, s):
        return canonicalName(s)

class CanonicalNameDict(utils.InsensitivePreservingDict):
    def key(self, s):
        return canonicalName(s)

class Disabled(registry.SpaceSeparatedListOf):
    Value = CanonicalString
    List = CanonicalNameSet

conf.registerGlobalValue(conf.supybot.commands, 'disabled',
    Disabled([], """Determines what commands are currently disabled.  Such
    commands will not appear in command lists, etc.  They will appear not even
    to exist."""))

class DisabledCommands(object):
    def __init__(self):
        self.d = CanonicalNameDict()
        for name in conf.supybot.commands.disabled():
            if '.' in name:
                (plugin, command) = name.split('.', 1)
                if command in self.d:
                    if self.d[command] is not None:
                        self.d[command].add(plugin)
                else:
                    self.d[command] = CanonicalNameSet([plugin])
            else:
                self.d[name] = None

    def disabled(self, command, plugin=None):
        if command in self.d:
            if self.d[command] is None:
                return True
            elif plugin in self.d[command]:
                return True
        return False

    def add(self, command, plugin=None):
        if plugin is None:
            self.d[command] = None
        else:
            if command in self.d:
                if self.d[command] is not None:
                    self.d[command].add(plugin)
            else:
                self.d[command] = CanonicalNameSet([plugin])

    def remove(self, command, plugin=None):
        if plugin is None:
            del self.d[command]
        else:
            if self.d[command] is not None:
                self.d[command].remove(plugin)

class Privmsg(irclib.IrcCallback):
    """Base class for all Privmsg handlers."""
    __metaclass__ = log.MetaFirewall
    # For awhile, a comment stood here to say, "Eventually callCommand."  But
    # that's wrong, because we can't do generic error handling in this
    # callCommand -- plugins need to be able to override callCommand and do
    # error handling there (see the Http plugin for an example).
    __firewalled__ = {'isCommand': None,
                      'invalidCommand': None}
    public = True
    handled = False
    errored = False
    alwaysCall = ()
    threaded = False
    noIgnore = False
    Proxy = IrcObjectProxy
    commandArgs = ['self', 'irc', 'msg', 'args']
    # This must be class-scope, so all plugins use the same one.
    _mores = ircutils.IrcDict()
    _disabled = DisabledCommands()
    def __init__(self):
        self.__parent = super(Privmsg, self)
        myName = self.name()
        self.log = log.getPluginLogger(myName)
        ### Setup the dispatcher command.
        canonicalname = canonicalName(myName)
        self._original = getattr(self, canonicalname, None)
        docstring = """<command> [<args> ...]

        Command dispatcher for the %s plugin.  Use 'list %s' to see the
        commands provided by this plugin.  Use 'config list plugins.%s' to see
        the configuration values for this plugin.  In most cases this dispatcher
        command is unnecessary; in cases where more than one plugin defines a
        given command, use this command to tell the bot which plugin's command
        to use.""" % (myName, myName, myName)
        def dispatcher(self, irc, msg, args):
            def handleBadArgs():
                if self._original:
                    self._original(irc, msg, args)
                else:
                    cb = irc.getCallback('Misc')
                    if cb is not None:
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
                        realname = '%s.%s' % (canonicalname, name)
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
            dispatcher.isDispatcher = False
        else:
            dispatcher.__doc__ = docstring
            dispatcher.isDispatcher = True
        setattr(self.__class__, canonicalname, dispatcher)

    def __call__(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if self.noIgnore or not ircdb.checkIgnored(msg.prefix,msg.args[0]):
                self.__parent.__call__(irc, msg)
        else:
            self.__parent.__call__(irc, msg)

    def isCommand(self, methodName):
        """Returns whether a given method name is a command in this plugin."""
        # This function is ugly, but I don't want users to call methods like
        # doPrivmsg or __init__ or whatever, and this is good to stop them.

        # Don't canonicalize this name: consider outFilter(self, irc, msg).
        # methodName = canonicalName(methodName)
        if self._disabled.disabled(methodName, plugin=self.name()):
            return False
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
        self.log.info('%r called by %s', name, msg.prefix)
        self.log.debug('args: %s', L[0])
        start = time.time()
        method(irc, msg, *L)
        elapsed = time.time() - start
        log.stat('%s took %s seconds', name, elapsed)

    def registryValue(self, name, channel=None, value=True):
        plugin = self.name()
        group = conf.supybot.plugins.get(plugin)
        names = registry.split(name)
        for name in names:
            group = group.get(name)
        if channel is not None:
            group = group.get(channel)
        if value:
            return group()
        else:
            return group

    def setRegistryValue(self, name, value, channel=None):
        plugin = self.name()
        group = conf.supybot.plugins.get(plugin)
        names = registry.split(name)
        for name in names:
            group = group.get(name)
        if channel is None:
            group.setValue(value)
        else:
            group.get(channel).setValue(value)

    def userValue(self, name, prefixOrName, default=None):
        try:
            id = str(ircdb.users.getUserId(prefixOrName))
        except KeyError:
            return None
        plugin = self.name()
        group = conf.users.plugins.get(plugin)
        names = registry.split(name)
        for name in names:
            group = group.get(name)
        return group.get(id)()

    def setUserValue(self, name, prefixOrName, value,
                     ignoreNoUser=True, setValue=True):
        try:
            id = str(ircdb.users.getUserId(prefixOrName))
        except KeyError:
            if ignoreNoUser:
                return
            else:
                raise
        plugin = self.name()
        group = conf.users.plugins.get(plugin)
        names = registry.split(name)
        for name in names:
            group = group.get(name)
        group = group.get(id)
        if setValue:
            group.setValue(value)
        else:
            group.set(value)


class SimpleProxy(RichReplyMethods):
    def __init__(self, irc, msg):
        self.irc = irc
        self.msg = msg

    def error(self, s, msg=None, **kwargs):
        if msg is None:
            msg = self.msg
        self.irc.queueMsg(error(msg, s, **kwargs))

    def reply(self, s, msg=None, **kwargs):
        if msg is None:
            msg = self.msg
        assert not isinstance(s, ircmsgs.IrcMsg), \
               'Old code alert: there is no longer a "msg" argument to reply.'
        self.irc.queueMsg(reply(msg, s, **kwargs))

    def __getattr__(self, attr):
        return getattr(self.irc, attr)

IrcObjectProxyRegexp = SimpleProxy

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
    Proxy = SimpleProxy
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
    Proxy = SimpleProxy
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
