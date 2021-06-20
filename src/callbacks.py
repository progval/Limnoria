# -*- coding: utf8 -*-
###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2014, James McCoy
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
This module contains the basic callbacks for handling PRIVMSGs.
"""

import re
import copy
import time
from . import shlex
import codecs
import getopt
import inspect
import warnings

from . import (conf, ircdb, irclib, ircmsgs, ircutils, log, registry,
        utils, world)
from .utils import minisix
from .utils.iter import any, all
from .i18n import PluginInternationalization
_ = PluginInternationalization()

def _addressed(irc, msg, prefixChars=None, nicks=None,
              prefixStrings=None, whenAddressedByNick=None,
              whenAddressedByNickAtEnd=None, payload=None):
    """Determines whether this message is a command to the bot (because of a
    prefix char/string, or because the bot's nick is used as prefix, or because
    it's a private message, etc.).
    Returns the actual content of the command (ie. the content of the message,
    stripped of the prefix that was used to determine if it's addressed).

    If 'payload' is not None, its value is used instead of msg.args[1] as the
    content of the message."""
    if isinstance(irc, str):
        warnings.warn(
            "callbacks.addressed's first argument should now be be the Irc "
            "object instead of the bot's nick.",
            DeprecationWarning)
        network = None
        nick = irc
    else:
        network = irc.network
        nick = irc.nick
    def get(group):
        v = group.getSpecific(network=network, channel=msg.channel)
        return v()
    def stripPrefixStrings(payload):
        for prefixString in prefixStrings:
            if payload.startswith(prefixString):
                payload = payload[len(prefixString):].lstrip()
        return payload

    assert msg.command in ('PRIVMSG', 'TAGMSG')
    target = msg.channel or msg.args[0]
    if not payload:
        payload = msg.args[1]
    if not payload:
        return ''
    if prefixChars is None:
        prefixChars = get(conf.supybot.reply.whenAddressedBy.chars)
    if whenAddressedByNick is None:
        whenAddressedByNick = get(conf.supybot.reply.whenAddressedBy.nick)
    if whenAddressedByNickAtEnd is None:
        r = conf.supybot.reply.whenAddressedBy.nick.atEnd
        whenAddressedByNickAtEnd = get(r)
    if prefixStrings is None:
        prefixStrings = get(conf.supybot.reply.whenAddressedBy.strings)
    # We have to check this before nicks -- try "@google supybot" with supybot
    # and whenAddressedBy.nick.atEnd on to see why.
    if any(payload.startswith, prefixStrings):
        return stripPrefixStrings(payload)
    elif payload[0] in prefixChars:
        return payload[1:].strip()
    if nicks is None:
        nicks = get(conf.supybot.reply.whenAddressedBy.nicks)
        nicks = list(map(ircutils.toLower, nicks))
    else:
        nicks = list(nicks) # Just in case.
    nicks.insert(0, ircutils.toLower(nick))
    # Ok, let's see if it's a private message.
    if ircutils.nickEqual(target, nick):
        payload = stripPrefixStrings(payload)
        while payload and payload[0] in prefixChars:
            payload = payload[1:].lstrip()
        return payload
    # Ok, not private.  Does it start with our nick?
    elif whenAddressedByNick:
        for nick in nicks:
            lowered = ircutils.toLower(payload)
            if lowered.startswith(nick):
                try:
                    (maybeNick, rest) = payload.split(None, 1)
                    toContinue = False
                    while not ircutils.isNick(maybeNick, strictRfc=True):
                        if maybeNick[-1].isalnum():
                            toContinue = True
                            break
                        maybeNick = maybeNick[:-1]
                    if toContinue:
                        continue
                    if ircutils.nickEqual(maybeNick, nick):
                        return rest
                    else:
                        continue
                except ValueError: # split didn't work.
                    continue
            elif whenAddressedByNickAtEnd and lowered.endswith(nick):
                rest = payload[:-len(nick)]
                possiblePayload = rest.rstrip(' \t,;')
                if possiblePayload != rest:
                    # There should be some separator between the nick and the
                    # previous alphanumeric character.
                    return possiblePayload
    if get(conf.supybot.reply.whenNotAddressed):
        return payload
    else:
        return ''

def addressed(irc, msg, **kwargs):
    """If msg is addressed to 'name', returns the portion after the address.
    Otherwise returns the empty string.
    """
    payload = msg.addressed
    if payload is not None:
        return payload
    else:
        payload = _addressed(irc, msg, **kwargs)
        msg.tag('addressed', payload)
        return payload

def canonicalName(command, preserve_spaces=False):
    """Turn a command into its canonical form.

    Currently, this makes everything lowercase and removes all dashes and
    underscores.
    """
    if minisix.PY2 and isinstance(command, unicode):
        command = command.encode('utf-8')
    elif minisix.PY3 and isinstance(command, bytes):
        command = command.decode()
    special = '\t-_'
    if not preserve_spaces:
        special += ' '
    reAppend = ''
    while command and command[-1] in special:
        reAppend = command[-1] + reAppend
        command = command[:-1]
    return ''.join([x for x in command if x not in special]).lower() + reAppend

def reply(*args, **kwargs):
    warnings.warn('callbacks.reply is deprecated. Use irc.reply instead.',
                  DeprecationWarning)
    return _makeReply(dynamic.irc, *args, **kwargs)

def _makeReply(irc, msg, s,
              prefixNick=None, private=None,
              notice=None, to=None, action=None, error=False,
              stripCtcp=True):
    msg.tag('repliedTo')
    # Ok, let's make the target:
    # XXX This isn't entirely right.  Consider to=#foo, private=True.
    target = ircutils.replyTo(msg)
    def isPublic(s):
        return irc.isChannel(irc.stripChannelPrefix(s))
    if to is not None and isPublic(to):
        target = to
    if isPublic(target):
        channel = irc.stripChannelPrefix(target)
    else:
        channel = None
    if notice is None:
        notice = conf.get(conf.supybot.reply.withNotice,
            channel=channel, network=irc.network)
    if private is None:
        private = conf.get(conf.supybot.reply.inPrivate,
            channel=channel, network=irc.network)
    if prefixNick is None:
        prefixNick = conf.get(conf.supybot.reply.withNickPrefix,
            channel=channel, network=irc.network)
    if error:
        notice =conf.get(conf.supybot.reply.error.withNotice,
            channel=channel, network=irc.network) or notice
        private=conf.get(conf.supybot.reply.error.inPrivate,
            channel=channel, network=irc.network) or private
        s = _('Error: ') + s
    if private:
        prefixNick = False
        if to is None:
            target = msg.nick
        else:
            target = to
    if action:
        prefixNick = False
    if to is None:
        to = msg.nick
    if stripCtcp:
        s = s.strip('\x01')
    # Ok, now let's make the payload:
    s = ircutils.safeArgument(s)
    if not s and not action:
        s = _('Error: I tried to send you an empty message.')
    if prefixNick and isPublic(target):
        # Let's may sure we don't do, "#channel: foo.".
        if not isPublic(to):
            s = '%s: %s' % (to, s)
    if not isPublic(target):
        if conf.supybot.reply.withNoticeWhenPrivate():
            notice = True
    # And now, let's decide whether it's a PRIVMSG or a NOTICE.
    msgmaker = ircmsgs.privmsg
    if notice:
        msgmaker = ircmsgs.notice
    # We don't use elif here because actions can't be sent as NOTICEs.
    if action:
        msgmaker = ircmsgs.action
    # Finally, we'll return the actual message.
    ret = msgmaker(target, s)
    ret.tag('inReplyTo', msg)
    if 'msgid' in msg.server_tags \
            and conf.supybot.protocols.irc.experimentalExtensions() \
            and 'message-tags' in irc.state.capabilities_ack:
        # In theory, msgid being in server_tags implies message-tags was
        # negotiated, but the +reply spec requires it explicitly. Plus, there's
        # no harm in doing this extra check, in case a plugin is replying
        # across network (as it may happen with '@network command').
        ret.server_tags['+draft/reply'] = msg.server_tags['msgid']
    return ret

def error(*args, **kwargs):
    warnings.warn('callbacks.error is deprecated. Use irc.error instead.',
                  DeprecationWarning)
    return _makeErrorReply(dynamic.irc, *args, **kwargs)

def _makeErrorReply(irc, msg, s, **kwargs):
    """Makes an error reply to msg with the appropriate error payload."""
    kwargs['error'] = True
    msg.tag('isError')
    return _makeReply(irc, msg, s, **kwargs)

def getHelp(method, name=None, doc=None):
    if name is None:
        name = method.__name__
    if doc is None:
        if method.__doc__ is None:
            doclines = ['This command has no help.  Complain to the author.']
        else:
            doclines = method.__doc__.splitlines()
    else:
        doclines = doc.splitlines()
    s = '%s %s' % (name, doclines.pop(0))
    if doclines:
        help = ' '.join(doclines)
        s = '(%s) -- %s' % (ircutils.bold(s), help)
    return utils.str.normalizeWhitespace(s)

def getSyntax(method, name=None, doc=None):
    if name is None:
        name = method.__name__
    if doc is None:
        doclines = method.__doc__.splitlines()
    else:
        doclines = doc.splitlines()
    return '%s %s' % (name, doclines[0])

class Error(Exception):
    """Generic class for errors in Privmsg callbacks."""
    pass

class ArgumentError(Error):
    """The bot replies with a help message when this is raised."""
    pass

class SilentError(Error):
    """An error that we should not notify the user."""
    pass

class Tokenizer(object):
    # This will be used as a global environment to evaluate strings in.
    # Evaluation is, of course, necessary in order to allow escaped
    # characters to be properly handled.
    #
    # These are the characters valid in a token.  Everything printable except
    # double-quote, left-bracket, and right-bracket.
    separators = '\x00\r\n \t'
    def __init__(self, brackets='', pipe=False, quotes='"'):
        if brackets:
            self.separators += brackets
            self.left = brackets[0]
            self.right = brackets[1]
        else:
            self.left = ''
            self.right = ''
        self.pipe = pipe
        if self.pipe:
            self.separators += '|'
        self.quotes = quotes
        self.separators += quotes


    def _handleToken(self, token):
        if token[0] == token[-1] and token[0] in self.quotes:
            token = token[1:-1]
            # FIXME: No need to tell you this is a hack.
            # It has to handle both IRC commands and serialized configuration.
            #
            # Whoever you are, if you make a single modification to this
            # code, TEST the code with Python 2 & 3, both with the unit
            # tests and on IRC with this: @echo "好"
            if minisix.PY2:
                try:
                    token = token.encode('utf8').decode('string_escape')
                    token = token.decode('utf8')
                except:
                    token = token.decode('string_escape')
            else:
                token = codecs.getencoder('utf8')(token)[0]
                token = codecs.getdecoder('unicode_escape')(token)[0]
                try:
                    token = token.encode('iso-8859-1').decode()
                except: # Prevent issue with tokens like '"\\x80"'.
                    pass
        return token

    def _insideBrackets(self, lexer):
        ret = []
        while True:
            token = lexer.get_token()
            if not token:
                raise SyntaxError(_('Missing "%s".  You may want to '
                                   'quote your arguments with double '
                                   'quotes in order to prevent extra '
                                   'brackets from being evaluated '
                                   'as nested commands.') % self.right)
            elif token == self.right:
                return ret
            elif token == self.left:
                ret.append(self._insideBrackets(lexer))
            else:
                ret.append(self._handleToken(token))
        return ret

    def tokenize(self, s):
        lexer = shlex.shlex(minisix.io.StringIO(s))
        lexer.commenters = ''
        lexer.quotes = self.quotes
        lexer.separators = self.separators
        args = []
        ends = []
        while True:
            token = lexer.get_token()
            if not token:
                break
            elif token == '|' and self.pipe:
                # The "and self.pipe" might seem redundant here, but it's there
                # for strings like 'foo | bar', where a pipe stands alone as a
                # token, but shouldn't be treated specially.
                if not args:
                    raise SyntaxError(_('"|" with nothing preceding.  I '
                                       'obviously can\'t do a pipe with '
                                       'nothing before the |.'))
                ends.append(args)
                args = []
            elif token == self.left:
                args.append(self._insideBrackets(lexer))
            elif token == self.right:
                raise SyntaxError(_('Spurious "%s".  You may want to '
                                   'quote your arguments with double '
                                   'quotes in order to prevent extra '
                                   'brackets from being evaluated '
                                   'as nested commands.') % self.right)
            else:
                args.append(self._handleToken(token))
        if ends:
            if not args:
                raise SyntaxError(_('"|" with nothing following.  I '
                                   'obviously can\'t do a pipe with '
                                   'nothing after the |.'))
            args.append(ends.pop())
            while ends:
                args[-1].append(ends.pop())
        return args

def tokenize(s, channel=None, network=None):
    """A utility function to create a Tokenizer and tokenize a string."""
    pipe = False
    brackets = ''
    nested = conf.supybot.commands.nested
    if nested():
        brackets = nested.brackets.getSpecific(network, channel)()
        if conf.get(nested.pipeSyntax,
                channel=channel, network=network): # No nesting, no pipe.
            pipe = True
    quotes = conf.supybot.commands.quotes.getSpecific(network, channel)()
    try:
        ret = Tokenizer(brackets=brackets,pipe=pipe,quotes=quotes).tokenize(s)
        return ret
    except ValueError as e:
        raise SyntaxError(str(e))

def formatCommand(command):
    return ' '.join(command)

def checkCommandCapability(msg, cb, commandName):
    plugin = cb.name().lower()
    if not isinstance(commandName, minisix.string_types):
        assert commandName[0] == plugin, ('checkCommandCapability no longer '
                'accepts command names that do not start with the callback\'s '
                'name (%s): %s') % (plugin, commandName)
        commandName = '.'.join(commandName)
    def checkCapability(capability):
        assert ircdb.isAntiCapability(capability)
        if ircdb.checkCapability(msg.prefix, capability):
            log.info('Preventing %s from calling %s because of %s.',
                     msg.prefix, commandName, capability)
            raise RuntimeError(capability)
    try:
        antiCommand = ircdb.makeAntiCapability(commandName)
        checkCapability(antiCommand)
        checkAtEnd = [commandName]
        default = conf.supybot.capabilities.default()
        if msg.channel:
            channel = msg.channel
            checkCapability(ircdb.makeChannelCapability(channel, antiCommand))
            chanCommand = ircdb.makeChannelCapability(channel, commandName)
            checkAtEnd += [chanCommand]
            default &= ircdb.channels.getChannel(channel).defaultAllow
        return not (default or \
                    any(lambda x: ircdb.checkCapability(msg.prefix, x),
                        checkAtEnd))
    except RuntimeError as e:
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
        return ircutils.standardSubstitute(self, self.msg, s)

    def _getConfig(self, wrapper):
        return conf.get(wrapper,
            channel=self.msg.channel, network=self.irc.network)

    def replySuccess(self, s='', **kwargs):
        r"""Replies with a success message, configurable with
        ``supybot.replies.success`` or the Success plugin.

        :arg str s:
            Text to append to the standard success message

        :arg \**kwargs:
            See :meth:`NestedCommandsIrcProxy.reply`'s keyword arguments
        """
        v = self._getConfig(conf.supybot.replies.success)
        if v:
            s = self.__makeReply(v, s)
            return self.reply(s, **kwargs)
        else:
            self.noReply()

    def replyError(self, s='', **kwargs):
        v = self._getConfig(conf.supybot.replies.error)
        if 'msg' in kwargs:
            msg = kwargs['msg']
            if ircdb.checkCapability(msg.prefix, 'owner'):
                v = self._getConfig(conf.supybot.replies.errorOwner)
        s = self.__makeReply(v, s)
        return self.reply(s, **kwargs)

    def _getTarget(self, to=None):
        """Compute the target according to self.to, the provided to,
        and self.private, and return it. Mainly used by reply methods."""
        # FIXME: Don't set self.to.
        # I still set it to be sure I don't introduce a regression,
        # but it does not make sense for .reply() and .replies() to
        # change the state of this Irc object.
        if to is not None:
            self.to = self.to or to
        if self.private:
            target = to or self.msg.nick
        elif self.msg.channel is None:
            target = self.msg.nick
        else:
            target = self.to or self.msg.args[0]
        return target

    def replies(self, L, prefixer=None, joiner=None,
                onlyPrefixFirst=False,
                oneToOne=None, **kwargs):
        if prefixer is None:
            prefixer = ''
        if joiner is None:
            joiner = utils.str.commaAndify
        if isinstance(prefixer, minisix.string_types):
            prefixer = prefixer.__add__
        if isinstance(joiner, minisix.string_types):
            joiner = joiner.join
        to = self._getTarget(kwargs.get('to'))
        if oneToOne is None: # Can be True, False, or None
            if self.irc.isChannel(to):
                oneToOne = conf.get(conf.supybot.reply.oneToOne,
                    channel=to, network=self.irc.network)
            else:
                oneToOne = conf.supybot.reply.oneToOne()
        if oneToOne:
            return self.reply(prefixer(joiner(L)), **kwargs)
        else:
            msg = None
            first = True
            for s in L:
                if onlyPrefixFirst:
                    if first:
                        first = False
                        msg = self.reply(prefixer(s), **kwargs)
                    else:
                        msg = self.reply(s, **kwargs)
                else:
                    msg = self.reply(prefixer(s), **kwargs)
            return msg

    def noReply(self, msg=None):
        self.repliedTo = True

    def _error(self, s, Raise=False, **kwargs):
        if Raise:
            raise Error(s)
        else:
            return self.error(s, **kwargs)

    def errorNoCapability(self, capability, s='', **kwargs):
        if 'Raise' not in kwargs:
            kwargs['Raise'] = True
        log.warning('Denying %s for lacking %q capability.',
                    self.msg.prefix, capability)
        # noCapability means "don't send a specific capability error
        # message" not "don't send a capability error message at all", like
        # one would think
        if self._getConfig(conf.supybot.reply.error.noCapability) or \
            capability in conf.supybot.capabilities.private():
            v = self._getConfig(conf.supybot.replies.genericNoCapability)
        else:
            v = self._getConfig(conf.supybot.replies.noCapability)
            try:
                v %= capability
            except TypeError: # No %s in string
                pass
        s = self.__makeReply(v, s)
        if s:
            return self._error(s, **kwargs)
        elif kwargs['Raise']:
            raise Error()

    def errorPossibleBug(self, s='', **kwargs):
        v = self._getConfig(conf.supybot.replies.possibleBug)
        if s:
            s += '  (%s)' % v
        else:
            s = v
        return self._error(s, **kwargs)

    def errorNotRegistered(self, s='', **kwargs):
        v = self._getConfig(conf.supybot.replies.notRegistered)
        return self._error(self.__makeReply(v, s), **kwargs)

    def errorNoUser(self, s='', name='that user', **kwargs):
        if 'Raise' not in kwargs:
            kwargs['Raise'] = True
        v = self._getConfig(conf.supybot.replies.noUser)
        try:
            v = v % name
        except TypeError:
            log.warning('supybot.replies.noUser should have one "%s" in it.')
        return self._error(self.__makeReply(v, s), **kwargs)

    def errorRequiresPrivacy(self, s='', **kwargs):
        v = self._getConfig(conf.supybot.replies.requiresPrivacy)
        return self._error(self.__makeReply(v, s), **kwargs)

    def errorInvalid(self, what, given=None, s='', repr=True, **kwargs):
        if given is not None:
            if repr:
                given = _repr(given)
            else:
                given = '"%s"' % given
            v = _('%s is not a valid %s.') % (given, what)
        else:
            v = _('That\'s not a valid %s.') % what
        if 'Raise' not in kwargs:
            kwargs['Raise'] = True
        if s:
            v += ' ' + s
        return self._error(v, **kwargs)

_repr = repr

class ReplyIrcProxy(RichReplyMethods):
    """This class is a thin wrapper around an irclib.Irc object that gives it
    the reply() and error() methods (as well as everything in RichReplyMethods,
    based on those two)."""
    _mores = ircutils.IrcDict()
    def __init__(self, irc, msg):
        self.irc = irc
        self.msg = msg
        self.getRealIrc()._setMsgChannel(self.msg)

    def getRealIrc(self):
        """Returns the real irclib.Irc object underlying this proxy chain."""
        if isinstance(self.irc, irclib.Irc):
            return self.irc
        else:
            return self.irc.getRealIrc()

    # This should make us be considered equal to our irclib.Irc object for
    # hashing; an important thing (no more "too many open files" exceptions :))
    def __hash__(self):
        return hash(self.getRealIrc())
    def __eq__(self, other):
        return self.getRealIrc() == other
    __req__ = __eq__
    def __ne__(self, other):
        return not (self == other)
    __rne__ = __ne__

    def error(self, s, msg=None, **kwargs):
        if 'Raise' in kwargs and kwargs['Raise']:
            raise Error()
        if msg is None:
            msg = self.msg
        if s:
            m = _makeErrorReply(self, msg, s, **kwargs)
            self.irc.queueMsg(m)
            return m

    def _defaultPrefixNick(self, msg):
        if msg.channel:
            return conf.get(conf.supybot.reply.withNickPrefix,
                channel=msg.channel, network=self.irc.network)
        else:
            return conf.supybot.reply.withNickPrefix()

    def reply(self, s, msg=None, **kwargs):
        """
        Keyword arguments:

        :arg bool noLengthCheck:
            True if the length shouldn't be checked (used for 'more' handling)

        :arg bool prefixNick:
            False if the nick shouldn't be prefixed to the reply.

        :arg bool action:
            True if the reply should be an action.

        :arg bool private:
            True if the reply should be in private.

        :arg bool notice:
            True if the reply should be noticed when the bot is configured
            to do so.

        :arg str to:
            The nick or channel the reply should go to.
            Defaults to msg.args[0] (or msg.nick if private)

        :arg bool sendImmediately:
            True if the reply should use sendMsg() which
            bypasses conf.supybot.protocols.irc.throttleTime
            and gets sent before any queued messages
        """
        if msg is None:
            msg = self.msg
        assert not isinstance(s, ircmsgs.IrcMsg), \
               'Old code alert: there is no longer a "msg" argument to reply.'
        kwargs.pop('noLengthCheck', None)
        if 'target' not in kwargs:
            # TODO: deduplicate this with _getTarget
            # TODO: it looks like 'target' is never in kwargs.
            #       (an old version of this code crashed when 'target' was
            #       not given, but no one complained). Remove the conditional?
            if kwargs.get('private', False) or msg.channel is None:
                kwargs['target'] = msg.nick
            else:
                kwargs['target'] = kwargs.get('to', None) or msg.args[0]
        if 'prefixNick' not in kwargs:
            kwargs['prefixNick'] = self._defaultPrefixNick(msg)
        self._sendReply(s, msg=msg, **kwargs)

    def __getattr__(self, attr):
        return getattr(self.irc, attr)

    def _replyOverhead(self, msg, **kwargs):
        """Returns the number of bytes added to a PRIVMSG payload, either by
        Limnoria itself or by the server.
        Ignores tag bytes, as they are accounted for separately."""
        # FIXME: big hack.
        # _makeReply does a lot of internal state computation, especially
        # related to the final target to use.
        # I tried to get them out of _makeReply but it's a clusterfuck, so I
        # gave up. Instead, we call _makeReply with a dummy payload to guess
        # what overhead it will add.
        payload = 'foo'
        channel = msg.channel
        msg = copy.deepcopy(msg)  # because _makeReply calls .tag('repliedTo')
        msg.channel = channel  # ugh... copy.deepcopy uses msg.__reduce__
        reply_msg = _makeReply(self, msg, payload, **kwargs)

        # strip tags, add prefix
        reply_msg = ircmsgs.IrcMsg(
            msg=reply_msg, server_tags={}, prefix=self.prefix)
        return len(str(reply_msg)) - len(payload)

    def _sendReply(self, s, target, msg, sendImmediately=False,
                   noLengthCheck=False, **kwargs):
        if sendImmediately:
            sendMsg = self.irc.sendMsg
        else:
            sendMsg = self.irc.queueMsg

        if isinstance(self.irc, self.__class__):
            s = s[:conf.supybot.reply.maximumLength()]
            return self.irc.reply(s,
                                  noLengthCheck=noLengthCheck,
                                  **kwargs)
        elif noLengthCheck:
            # noLengthCheck only matters to NestedCommandsIrcProxy, so
            # it's not used here.  Just in case you were wondering.
            m = _makeReply(self, msg, s, **kwargs)
            sendMsg(m)
            return m
        else:
            s = ircutils.safeArgument(s)
            allowedLength = conf.get(conf.supybot.reply.mores.length,
                channel=target, network=self.irc.network)
            if not allowedLength: # 0 indicates this.
                allowedLength = 512 - self._replyOverhead(msg, **kwargs)
            maximumMores = conf.get(conf.supybot.reply.mores.maximum,
                channel=target, network=self.irc.network)
            maximumLength = allowedLength * maximumMores
            if len(s) > maximumLength:
                log.warning('Truncating to %s bytes from %s bytes.',
                            maximumLength, len(s))
                s = s[:maximumLength]
            s_size = len(s.encode()) if minisix.PY3 else len(s)
            if s_size <= allowedLength or \
               not conf.get(conf.supybot.reply.mores,
                    channel=target, network=self.irc.network):
                # There's no need for action=self.action here because
                # action implies noLengthCheck, which has already been
                # handled.  Let's stick an assert in here just in case.
                assert not kwargs.get('action')
                m = _makeReply(self, msg, s, **kwargs)
                sendMsg(m)
                return m
            # The '(XX more messages)' may have not the same
            # length in the current locale
            allowedLength -= len(_('(XX more messages)')) + 1 # bold
            chunks = ircutils.wrap(s, allowedLength)

            # Last messages to display at the beginning of the list
            # (which is used like a stack)
            chunks.reverse()

            instant = conf.get(conf.supybot.reply.mores.instant,
                channel=target, network=self.irc.network)

            # Big complex loop ahead, with lots of cases and opportunities for
            # off-by-one errors. Here is the meaning of each of the variables
            #
            # * 'i' is the number of chunks after the current one
            #
            # * 'is_first' is True when the message is the very first message
            #   (so last iteration of the loop)
            #
            # * 'is_last' is True when the message is the very last (so first
            #   iteration of the loop)
            #
            # * 'is_instant' is True when the message is in one of the messages
            #   sent immediately when the command is called, ie. without
            #   calling @misc more. (when supybot.reply.mores.instant is 1,
            #   which is the default, this is equivalent to 'is_first')
            #
            # * 'is_last_instant' is True when the message is the last of the
            #   instant message (so the first iteration of the loop with an
            #   instant message).
            #
            # We need all this complexity because pagination is hard, and we
            # want:
            #
            # * the '(XX more messages)' suffix on the last instant message,
            #   and every other message (mandatory, it's a great feature),
            #   but not on the other instant messages (mandatory when
            #   multiline is enabled, but very nice to have in general)
            # * the nick prefix on the first message and every other message
            #   that isn't instant (mandatory), but not on the other instant
            #   messages (also mandatory only when multiline is enabled)
            msgs = []
            for (i, chunk) in enumerate(chunks):
                is_first = i == len(chunks) - 1
                is_last = i == 0
                is_instant = len(chunks) - i <= instant
                is_last_instant = len(chunks) - i == instant
                if is_last:
                    # last message, no suffix to add
                    pass
                elif is_instant and not is_last_instant:
                    # one of the first messages, and the next one will
                    # also be sent immediately, so no suffix
                    pass
                else:
                    if i == 1:
                        more = _('more message')
                    else:
                        more = _('more messages')
                    n = ircutils.bold('(%i %s)' % (len(msgs), more))
                    chunk = '%s %s' % (chunk, n)

                if is_instant and not is_first:
                    d = kwargs.copy()
                    d['prefixNick'] = False
                    msgs.append(_makeReply(self, msg, chunk, **d))
                else:
                    msgs.append(_makeReply(self, msg, chunk, **kwargs))

            instant_messages = []

            while instant > 0 and msgs:
                instant -= 1
                response = msgs.pop()
                instant_messages.append(response)
                # XXX We should somehow allow these to be returned, but
                #     until someone complains, we'll be fine :)  We
                #     can't return from here, though, for obvious
                #     reasons.
                # return m

            if conf.supybot.protocols.irc.experimentalExtensions() \
                    and 'draft/multiline' in self.state.capabilities_ack \
                    and len(instant_messages) > 1:
                # More than one message to send now, and we are allowed to use
                # multiline batches, so let's do it
                self.queueMultilineBatches(
                    instant_messages, target, msg.nick, concat=True,
                    allowedLength=allowedLength, sendImmediately=sendImmediately)
            else:
                for instant_msg in instant_messages:
                    sendMsg(instant_msg)

            if not msgs:
                return
            prefix = msg.prefix
            if target and ircutils.isNick(target):
                try:
                    state = self.getRealIrc().state
                    prefix = state.nickToHostmask(target)
                except KeyError:
                    pass # We'll leave it as it is.
            if '!' in prefix and '@' in prefix:
                mask = prefix.split('!', 1)[1]
                self._mores[mask] = msgs
            public = bool(self.msg.channel)
            private = kwargs.get('private', False) or not public
            self._mores[msg.nick] = (private, msgs)
            return response

    def queueMultilineBatches(self, msgs, target, targetNick, concat,
                              allowedLength=0, sendImmediately=False):
        """Queues the msgs passed as argument in batches using draft/multiline
        batches.

        This errors if experimentalExtensions is disabled or draft/multiline
        was not negotiated."""
        assert conf.supybot.protocols.irc.experimentalExtensions()
        assert 'draft/multiline' in self.state.capabilities_ack

        if allowedLength: # 0 indicates this.
            largest_msg_size = allowedLength
        else:
            # Used as upper bound of each message's size to decide how many
            # messages to put in each batch.
            largest_msg_size = max(len(msg.args[1]) for msg in msgs)

        multiline_cap_values = ircutils.parseCapabilityKeyValue(
            self.state.capabilities_ls['draft/multiline'])

        # All the messages in instant_messages are to be sent
        # immediately, in multiline batches.
        max_bytes_per_batch = int(multiline_cap_values['max-bytes'])

        # We have to honor max_bytes_per_batch, but I don't want to
        # encode messages again here just to have their length, so
        # let's assume they all have the maximum length.
        # It's not optimal, but close enough and simplifies the code.
        messages_per_batch = max_bytes_per_batch // largest_msg_size

        # "Clients MUST NOT send tags other than draft/multiline-concat and
        # batch on messages within the batch. In particular, all client-only
        # tags associated with the message must be sent attached to the initial
        # BATCH command."
        # -- <https://ircv3.net/specs/extensions/multiline>
        # So we copy the tags of the first message, discard the tags of all
        # other messages, and apply the tags to the opening BATCH
        server_tags = msgs[0].server_tags

        for batch_msgs in utils.iter.grouper(msgs, messages_per_batch):
            # TODO: should use sendBatch instead of queueBatch if
            # sendImmediately is True
            batch_name = ircutils.makeLabel()
            batch = []
            batch.append(ircmsgs.IrcMsg(command='BATCH',
                args=('+' + batch_name, 'draft/multiline', target),
                server_tags=server_tags))

            for (i, batch_msg) in enumerate(batch_msgs):
                if batch_msg is None:
                    continue  # 'grouper' generates None at the end
                assert 'batch' not in batch_msg.server_tags

                # Discard the existing tags, and add the batch ones.
                batch_msg.server_tags = {'batch': batch_name}
                if concat and i > 0:
                    # Tell clients not to add a newline after this
                    batch_msg.server_tags['draft/multiline-concat'] = None
                batch.append(batch_msg)

            batch.append(ircmsgs.IrcMsg(
                command='BATCH', args=('-' + batch_name,)))

            self.queueBatch(batch)

SimpleProxy = ReplyIrcProxy # Backwards-compatibility

class NestedCommandsIrcProxy(ReplyIrcProxy):
    "A proxy object to allow proper nesting of commands (even threaded ones)."
    def __init__(self, irc, msg, args, nested=0):
        assert isinstance(args, list), 'Args should be a list, not a string.'
        super(NestedCommandsIrcProxy, self).__init__(irc, msg)
        self.nested = nested
        self.repliedTo = False
        if not self.nested and isinstance(irc, self.__class__):
            # This means we were given an NestedCommandsIrcProxy instead of an
            # irclib.Irc, and so we're obviously nested.  But nested wasn't
            # set!  So we take our given Irc's nested value.
            self.nested += irc.nested
        maxNesting = conf.supybot.commands.nested.maximum()
        if maxNesting and self.nested > maxNesting:
            log.warning('%s attempted more than %s levels of nesting.',
                        self.msg.prefix, maxNesting)
            self.error(_('You\'ve attempted more nesting than is '
                              'currently allowed on this bot.'))
            return
        # The deepcopy here is necessary for Scheduler; it re-runs already
        # tokenized commands.  There's a possibility a simple copy[:] would
        # work, but we're being careful.
        self.args = copy.deepcopy(args)
        self.counter = 0
        self._resetReplyAttributes()
        if not args:
            self.finalEvaled = True
            self._callInvalidCommands()
        else:
            self.finalEvaled = False
            world.commandsProcessed += 1
            self.evalArgs()

    def __eq__(self, other):
        return other == self.getRealIrc()

    def __hash__(self):
        return hash(self.getRealIrc())

    def _resetReplyAttributes(self):
        self.to = None
        self.action = None
        self.notice = None
        self.private = None
        self.noLengthCheck = None
        self.prefixNick = self._defaultPrefixNick(self.msg)

    def evalArgs(self, withClass=None):
        while self.counter < len(self.args):
            self.repliedTo = False
            if isinstance(self.args[self.counter], minisix.string_types):
                # If it's a string, just go to the next arg.  There is no
                # evaluation to be done for strings.  If, at some point,
                # we decided to, say, convert every string using
                # ircutils.standardSubstitute, this would be where we would
                # probably put it.
                self.counter += 1
            else:
                assert isinstance(self.args[self.counter], list)
                # It's a list.  So we spawn another NestedCommandsIrcProxy
                # to evaluate its args.  When that class has finished
                # evaluating its args, it will call our reply method, which
                # will subsequently call this function again, and we'll
                # pick up where we left off via self.counter.
                cls = withClass or self.__class__
                cls(self, self.msg, self.args[self.counter],
                        nested=self.nested+1)
                # We have to return here because the new NestedCommandsIrcProxy
                # might not have called our reply method instantly, since
                # its command might be threaded.  So (obviously) we can't
                # just fall through to self.finalEval.
                return
        # Once all the list args are evaluated, we then evaluate our own
        # list of args, since we're assured that they're all strings now.
        assert all(lambda x: isinstance(x, minisix.string_types), self.args)
        self.finalEval()

    def _callInvalidCommands(self):
        log.debug('Calling invalidCommands.')
        threaded = False
        cbs = []
        for cb in self.irc.callbacks:
            if hasattr(cb, 'invalidCommand'):
                cbs.append(cb)
                threaded = threaded or cb.threaded
        def callInvalidCommands():
            self.repliedTo = False
            for cb in cbs:
                log.debug('Calling %s.invalidCommand.', cb.name())
                try:
                    cb.invalidCommand(self, self.msg, self.args)
                except Error as e:
                    self.error(str(e))
                except Exception as e:
                    log.exception('Uncaught exception in %s.invalidCommand.',
                                  cb.name())
                log.debug('Finished calling %s.invalidCommand.', cb.name())
                if self.repliedTo:
                    log.debug('Done calling invalidCommands: %s.',cb.name())
                    return
        if threaded:
            name = 'Thread #%s (for invalidCommands)' % world.threadsSpawned
            t = world.SupyThread(target=callInvalidCommands, name=name)
            t.setDaemon(True)
            t.start()
        else:
            callInvalidCommands()

    def findCallbacksForArgs(self, args):
        """Returns a two-tuple of (command, plugins) that has the command
        (a list of strings) and the plugins for which it was a command."""
        assert isinstance(args, list)
        args = list(map(canonicalName, args))

        # Find a list maxL such that maxL = args[0:n] for the largest n
        # possible such that maxL is a command.
        cbs = []
        maxL = []
        for cb in self.irc.callbacks:
            if not hasattr(cb, 'getCommand'):
                continue
            L = cb.getCommand(args)
            if L and L >= maxL:
                # equivalent to "L and len(L) >= len(maxL)", because L and maxL
                # are both "prefixes" of the same list.
                maxL = L
                cbs.append((cb, L))
                assert isinstance(L, list), \
                       'getCommand now returns a list, not a method.'
                assert utils.iter.startswith(L, args), \
                       'getCommand must return a prefix of the args given.  ' \
                       '(args given: %r, returned: %r)' % (args, L)
        log.debug('findCallbacksForArgs: %r', cbs)

        # Filter out all the entries in cbs that are smaller than maxL (ie.
        # maxL contains them, with more items at the end.)
        cbs = [cb for (cb, L) in cbs if L == maxL]

        if len(maxL) == 1:
            # Special case: one arg determines the callback.  In this case, we
            # have to check, in order:
            # 1. Whether the arg is the same as the name of a callback.  This
            #    callback would then win.
            for cb in cbs:
                if cb.canonicalName() == maxL[0]:
                    return (maxL, [cb])

            # 2. Whether a defaultplugin is defined.
            defaultPlugins = conf.supybot.commands.defaultPlugins
            try:
                defaultPlugin = defaultPlugins.get(maxL[0])()
                log.debug('defaultPlugin: %r', defaultPlugin)
                if defaultPlugin:
                    cb = self.irc.getCallback(defaultPlugin)
                    if cb in cbs:
                        # This is just a sanity check, but there's a small
                        # possibility that a default plugin for a command
                        # is configured to point to a plugin that doesn't
                        # actually have that command.
                        return (maxL, [cb])
            except registry.NonExistentRegistryEntry:
                pass

            # 3. Whether an importantPlugin is one of the responses.
            important = defaultPlugins.importantPlugins()
            important = list(map(canonicalName, important))
            importants = []
            for cb in cbs:
                if cb.canonicalName() in important:
                    importants.append(cb)
            if len(importants) == 1:
                return (maxL, importants)
        return (maxL, cbs)

    def finalEval(self):
        # Now that we've already iterated through our args and made sure
        # that any list of args was evaluated (by spawning another
        # NestedCommandsIrcProxy to evaluated it into a string), we can finally
        # evaluated our own list of arguments.
        assert not self.finalEvaled, 'finalEval called twice.'
        self.finalEvaled = True
        # Now, the way we call a command is we iterate over the loaded plugins,
        # asking each one if the list of args we have interests it.  The
        # way we do that is by calling getCommand on the plugin.
        # The plugin will return a list of args which it considers to be
        # "interesting."  We will then give our args to the plugin which
        # has the *longest* list.  The reason we pick the longest list is
        # that it seems reasonable that the longest the list, the more
        # specific the command is.  That is, given a list of length X, a list
        # of length X+1 would be even more specific (assuming that both lists
        # used the same prefix. Of course, if two plugins return a list of the
        # same length, we'll just error out with a message about ambiguity.
        (command, cbs) = self.findCallbacksForArgs(self.args)
        if not cbs:
            # We used to handle addressedRegexps here, but I think we'll let
            # them handle themselves in getCommand.  They can always just
            # return the full list of args as their "command".
            self._callInvalidCommands()
        elif len(cbs) > 1:
            names = sorted([cb.name() for cb in cbs])
            command = formatCommand(command)
            self.error(format(_('The command %q is available in the %L '
                              'plugins.  Please specify the plugin '
                              'whose command you wish to call by using '
                              'its name as a command before %q.'),
                              command, names, command))
        else:
            cb = cbs[0]
            args = self.args[len(command):]
            if world.isMainThread() and \
               (cb.threaded or conf.supybot.debug.threadAllCommands()):
                t = CommandThread(target=cb._callCommand,
                                  args=(command, self, self.msg, args))
                t.start()
            else:
                cb._callCommand(command, self, self.msg, args)

    def reply(self, s, noLengthCheck=False, prefixNick=None, action=None,
              private=None, notice=None, to=None, msg=None,
              sendImmediately=False, stripCtcp=True):
        # These use and or or based on whether or not they default to True or
        # False.  Those that default to True use and; those that default to
        # False use or.
        assert not isinstance(s, ircmsgs.IrcMsg), \
               'Old code alert: there is no longer a "msg" argument to reply.'
        self.repliedTo = True
        if msg is None:
            msg = self.msg
        if prefixNick is not None:
            self.prefixNick = prefixNick
        if action is not None:
            self.action = self.action or action
            if action:
                self.prefixNick = False
                self.noLengthCheck = True
        if notice is not None:
            self.notice = self.notice or notice
        if private is not None:
            self.private = self.private or private
        target = self._getTarget(to)
        # action=True implies noLengthCheck=True and prefixNick=False
        self.noLengthCheck=noLengthCheck or self.noLengthCheck or self.action
        if not isinstance(s, minisix.string_types): # avoid trying to str() unicode
            s = str(s) # Allow non-string esses.

        if self.finalEvaled:
            try:
                self._sendReply(
                    s=s, target=target, msg=msg,
                    to=self.to,
                    notice=self.notice,
                    action=self.action,
                    private=self.private,
                    prefixNick=self.prefixNick,
                    stripCtcp=stripCtcp,
                    noLengthCheck=self.noLengthCheck,
                    sendImmediately=sendImmediately,
                )
            except:
                log.exception('Error while sending reply')
                raise
            finally:
                self._resetReplyAttributes()
        else:
            if msg.ignored:
                # Since the final reply string is constructed via
                # ' '.join(self.args), the args index for ignored commands
                # needs to be popped to avoid extra spaces in the final reply.
                self.args.pop(self.counter)
                msg.tag('ignored', False)
            else:
                self.args[self.counter] = s
            self.evalArgs()

    def noReply(self, msg=None):
        if msg is None:
            msg = self.msg
        super(NestedCommandsIrcProxy, self).noReply(msg=msg)
        if self.finalEvaled:
            if isinstance(self.irc, NestedCommandsIrcProxy):
                self.irc.noReply(msg=msg)
            else:
                msg.tag('ignored', True)
        else:
            self.args.pop(self.counter)
            msg.tag('ignored', False)
            self.evalArgs()

    def replies(self, L, prefixer=None, joiner=None,
                onlyPrefixFirst=False, to=None,
                oneToOne=None, **kwargs):
        if not self.finalEvaled and oneToOne is None:
            oneToOne = True
        return super(NestedCommandsIrcProxy, self).replies(L,
                prefixer=prefixer, joiner=joiner,
                onlyPrefixFirst=onlyPrefixFirst, to=to,
                oneToOne=oneToOne, **kwargs)

    def error(self, s='', Raise=False, **kwargs):
        r"""Replies with an error.

        :arg str s:
            The error message

        :arg bool Raise:
            If True, this will raise :class:`Error` that will propagate so
            that the caller of this function immediately terminates

        :arg \**kwargs:
            See :meth:`NestedCommandsIrcProxy.reply`'s keyword arguments
        """
        self.repliedTo = True
        if Raise:
            raise Error(s)
        if not isinstance(self.irc, irclib.Irc):
            return self.irc.error(s, **kwargs)
        elif s:
            m = _makeErrorReply(self, self.msg, s, **kwargs)
            self.irc.queueMsg(m)
            return m

    def __getattr__(self, attr):
        return getattr(self.irc, attr)

IrcObjectProxy = NestedCommandsIrcProxy

class CommandThread(world.SupyThread):
    """Just does some extra logging and error-recovery for commands that need
    to run in threads.
    """
    def __init__(self, target=None, args=(), kwargs={}):
        self.command = args[0]
        self.cb = target.__self__
        threadName = 'Thread #%s (for %s.%s)' % (world.threadsSpawned,
                                                 self.cb.name(),
                                                 self.command)
        log.debug('Spawning thread %s (args: %r)', threadName, args)
        self.__parent = super(CommandThread, self)
        self.__parent.__init__(target=target, name=threadName,
                               args=args, kwargs=kwargs)
        self.setDaemon(True)
        self.originalThreaded = self.cb.threaded
        self.cb.threaded = True

    def run(self):
        try:
            self.__parent.run()
        finally:
            self.cb.threaded = self.originalThreaded

class CommandProcess(world.SupyProcess):
    """Just does some extra logging and error-recovery for commands that need
    to run in processes.
    """
    def __init__(self, target=None, args=(), kwargs={}):
        pn = kwargs.pop('pn', 'Unknown')
        cn = kwargs.pop('cn', 'unknown')
        procName = 'Process #%s (for %s.%s)' % (world.processesSpawned,
                                                 pn,
                                                 cn)
        log.debug('Spawning process %s (args: %r)', procName, args)
        self.__parent = super(CommandProcess, self)
        self.__parent.__init__(target=target, name=procName,
                               args=args, kwargs=kwargs)

    def run(self):
        self.__parent.run()

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
    sorted = True
    Value = CanonicalString
    List = CanonicalNameSet

conf.registerGlobalValue(conf.supybot.commands, 'disabled',
    Disabled([], _("""Determines what commands are currently disabled.  Such
    commands will not appear in command lists, etc.  They will appear not even
    to exist.""")))

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

class BasePlugin(object):
    def __init__(self, *args, **kwargs):
        self.cbs = []
        for attr in dir(self):
            if attr != canonicalName(attr):
                continue
            obj = getattr(self, attr)
            if isinstance(obj, type) and issubclass(obj, BasePlugin):
                cb = obj(*args, **kwargs)
                setattr(self, attr, cb)
                self.cbs.append(cb)
                cb.log = log.getPluginLogger('%s.%s' % (self.name(),cb.name()))
        super(BasePlugin, self).__init__()

class MetaSynchronizedAndFirewalled(log.MetaFirewall, utils.python.MetaSynchronized):
    pass
SynchronizedAndFirewalled = MetaSynchronizedAndFirewalled(
        'SynchronizedAndFirewalled', (), {})

class Commands(BasePlugin, SynchronizedAndFirewalled):
    __synchronized__ = (
        '__call__',
        'callCommand',
        'invalidCommand',
        )
    # For a while, a comment stood here to say, "Eventually callCommand."  But
    # that's wrong, because we can't do generic error handling in this
    # callCommand -- plugins need to be able to override callCommand and do
    # error handling there (see the Web plugin for an example).
    __firewalled__ = {'isCommand': None,
                      '_callCommand': None}
    commandArgs = ['self', 'irc', 'msg', 'args']
    # These must be class-scope, so all plugins use the same one.
    _disabled = DisabledCommands()
    pre_command_callbacks = []
    def name(self):
        """Returns the name of this Commands object (usually the plugin
        name)."""
        return self.__class__.__name__

    def canonicalName(self):
        """Same as :py:meth:`name`, but normalized."""
        return canonicalName(self.name())

    def isDisabled(self, command):
        """Returns whether the given ``command`` is disabled."""
        return self._disabled.disabled(command, self.name())

    def isCommandMethod(self, name):
        """Returns whether a given method name is a command in this plugin.
        Plugins only need to implement this if they have a dynamic set of
        commands."""
        # This function is ugly, but I don't want users to call methods like
        # doPrivmsg or __init__ or whatever, and this is good to stop them.

        # Don't normalize this name: consider outFilter(self, irc, msg).
        # name = canonicalName(name)
        if self.isDisabled(name):
            return False
        if name != canonicalName(name):
            return False
        if hasattr(self, name):
            method = getattr(self, name)
            if inspect.ismethod(method):
                code = method.__func__.__code__
                return inspect.getargs(code)[0] == self.commandArgs
            else:
                return False
        else:
            return False

    def isCommand(self, command):
        """Convenience, backwards-compatibility, semi-deprecated."""
        if isinstance(command, minisix.string_types):
            return self.isCommandMethod(command)
        else:
            # Since we're doing a little type dispatching here, let's not be
            # too liberal.
            assert isinstance(command, list)
            return self.getCommand(command) == command

    def getCommand(self, args, stripOwnName=True):
        """Among all the commands in this Commands object, recursively
        searches for the command whose name is the longst substring
        of ``args``, and returns its name, splitted on spaces."""
        assert args == list(map(canonicalName, args))
        first = args[0]
        for cb in self.cbs:
            if first == cb.canonicalName():
                return cb.getCommand(args)
        if first == self.canonicalName() and len(args) > 1 and \
                stripOwnName:
            ret = self.getCommand(args[1:], stripOwnName=False)
            if ret:
                return [first] + ret
        if self.isCommandMethod(first):
            return [first]
        return []

    def getCommandMethod(self, command):
        """Gets the given command from this plugin, using
        :py:meth:`getCommand`.
        Plugins only need to implement this if they have a dynamic set of
        commands."""
        #print '*** %s.getCommandMethod(%r)' % (self.name(), command)
        assert not isinstance(command, minisix.string_types)
        assert command == list(map(canonicalName, command))
        assert self.getCommand(command) == command
        for cb in self.cbs:
            if command[0] == cb.canonicalName():
                return cb.getCommandMethod(command)
        if len(command) > 1:
            assert command[0] == self.canonicalName()
            return self.getCommandMethod(command[1:])
        else:
            method = getattr(self, command[0])
            if inspect.ismethod(method):
                code = method.__func__.__code__
                if inspect.getargs(code)[0] == self.commandArgs:
                    return method
                else:
                    raise AttributeError

    def listCommands(self, pluginCommands=[]):
        """List all the commands in this ``Commands`` object.
        Plugins only need to implement this if they have a dynamic set of
        commands."""
        commands = set(pluginCommands)
        for s in dir(self):
            if self.isCommandMethod(s):
                commands.add(s)
        for cb in self.cbs:
            name = cb.canonicalName()
            for command in cb.listCommands():
                if command == name:
                    commands.add(command)
                else:
                    commands.add(' '.join([name, command]))
        L = list(commands)
        L.sort()
        return L

    def callCommand(self, command, irc, msg, *args, **kwargs):
        """Given a command name, gets the method with
        :py:meth:`getCommandMethod` and calls it."""
        # We run all callbacks before checking if one of them returned True
        if any(bool, list(cb(self, command, irc, msg, *args, **kwargs)
                    for cb in self.pre_command_callbacks)):
            return
        method = self.getCommandMethod(command)
        method(irc, msg, *args, **kwargs)

    def _callCommand(self, command, irc, msg, *args, **kwargs):
        if irc.nick == msg.args[0]:
            self.log.info('%s called in private by %q.', formatCommand(command),
                    msg.prefix)
        else:
            self.log.info('%s called on %s by %q.', formatCommand(command),
                    msg.args[0], msg.prefix)
        try:
            if len(command) == 1 or command[0] != self.canonicalName():
                fullCommandName = [self.canonicalName()] + command
            else:
                fullCommandName = command
            # Let "P" be the plugin and "X Y" the command name. The
            # fullCommandName is "P X Y"

            # check "Y"
            cap = checkCommandCapability(msg, self, command[-1])
            if cap:
                irc.errorNoCapability(cap)
                return

            # check "P", "P.X", and "P.X.Y"
            prefix = []
            for name in fullCommandName:
                prefix.append(name)
                cap = checkCommandCapability(msg, self, prefix)
                if cap:
                    irc.errorNoCapability(cap)
                    return

            try:
                self.callingCommand = command
                self.callCommand(command, irc, msg, *args, **kwargs)
            finally:
                self.callingCommand = None
        except SilentError:
            pass
        except (getopt.GetoptError, ArgumentError) as e:
            self.log.debug('Got %s, giving argument error.',
                           utils.exnToString(e))
            help = self.getCommandHelp(command)
            if 'command has no help.' in help:
                # Note: this case will never happen, unless 'checkDoc' is set
                # to False.
                irc.error(_('Invalid arguments for %s.') % formatCommand(command))
            else:
                irc.reply(help)
        except (SyntaxError, Error) as e:
            self.log.debug('Error return: %s', utils.exnToString(e))
            irc.error(str(e))
        except Exception as e:
            self.log.exception('Uncaught exception in %s.', command)
            if conf.supybot.reply.error.detailed():
                irc.error(utils.exnToString(e))
            else:
                irc.replyError(msg=msg)

    def getCommandHelp(self, command, simpleSyntax=None):
        """Returns the help string of the given command, using
        :py:meth:`getCommandMethod`."""
        method = self.getCommandMethod(command)
        help = getHelp
        chan = None
        net = None
        if dynamic.msg is not None:
            chan = dynamic.msg.channel
        if dynamic.irc is not None:
            net = dynamic.irc.network
        if simpleSyntax is None:
            simpleSyntax = conf.get(conf.supybot.reply.showSimpleSyntax,
                channel=chan, network=net)
        if simpleSyntax:
            help = getSyntax
        if hasattr(method, '__doc__'):
            return help(method, name=formatCommand(command))
        else:
            return format(_('The %q command has no help.'),
                          formatCommand(command))

class PluginMixin(BasePlugin, irclib.IrcCallback):
    public = True
    alwaysCall = ()
    threaded = False
    noIgnore = False
    classModule = None
    Proxy = NestedCommandsIrcProxy
    def __init__(self, irc):
        myName = self.name()
        self.log = log.getPluginLogger(myName)
        self.__parent = super(PluginMixin, self)
        self.__parent.__init__(irc)
        # We can't do this because of the specialness that Owner and Misc do.
        # I guess plugin authors will have to get the capitalization right.
        # self.callAfter = map(str.lower, self.callAfter)
        # self.callBefore = map(str.lower, self.callBefore)

    def canonicalName(self):
        return canonicalName(self.name())

    def __call__(self, irc, msg):
        irc = SimpleProxy(irc, msg)
        if msg.command == 'PRIVMSG':
            if hasattr(self.noIgnore, '__call__'):
                noIgnore = self.noIgnore(irc, msg)
            else:
                noIgnore = self.noIgnore
            if (noIgnore or
               not msg.prefix or  # simulated echo message
               not ircutils.isUserHostmask(msg.prefix) or # Some services impl.
               not ircdb.checkIgnored(msg.prefix, msg.channel)):
                self.__parent.__call__(irc, msg)
        else:
            self.__parent.__call__(irc, msg)

    def registryValue(self, name, channel=None, network=None, *, value=True):
        """Returns the value of a configuration variable specified by
        ``name``.

        If the configuration variable has a channel- or network-specific
        variable (ie. if its value can change across channels or networks),
        ``channel`` and ``network`` allow getting the most specific value.
        If neither is given, returns the generic value.

        If ``value=False``, returns the variable itself (an instance
        of :py:class:`supybot.registry.Value`) instead of its value."""
        if isinstance(network, bool):
            # Network-unaware plugin that uses 'value' as a positional
            # argument.
            (network, value) = (value, network)
        plugin = self.name()
        group = conf.supybot.plugins.get(plugin)
        names = registry.split(name)
        for name in names:
            group = group.get(name)
        if channel or network:
            group = group.getSpecific(network=network, channel=channel)
        if value:
            return group()
        else:
            return group

    def setRegistryValue(self, name, value, channel=None, network=None):
        """Sets a configuration variable. See :py:meth:`registryValue`"""
        plugin = self.name()
        group = conf.supybot.plugins.get(plugin)
        names = registry.split(name)
        for name in names:
            group = group.get(name)
        if network:
            group = group.get(':' + network)
        if channel:
            group = group.get(channel)
        group.setValue(value)

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

    def getPluginHelp(self):
        if hasattr(self, '__doc__'):
            return self.__doc__
        else:
            return None

class Plugin(PluginMixin, Commands):
    pass
Privmsg = Plugin # Backwards compatibility.


class PluginRegexp(Plugin):
    """Same as Plugin, except allows the user to also include regexp-based
    callbacks.  All regexp-based callbacks must be specified in the set (or
    list) attribute "regexps", "addressedRegexps", or "unaddressedRegexps"
    depending on whether they should always be triggered, triggered only when
    the bot is addressed, or triggered only when the bot isn't addressed.
    """
    flags = re.I
    regexps = ()
    """'regexps' methods are called whether the message is addressed or not."""
    addressedRegexps = ()
    """'addressedRegexps' methods are called only when the message is addressed,
    and then, only with the payload (i.e., what is returned from the
    'addressed' function."""
    unaddressedRegexps = ()
    """'unaddressedRegexps' methods are called only when the message is *not*
    addressed."""
    Proxy = SimpleProxy
    def __init__(self, irc):
        self.__parent = super(PluginRegexp, self)
        self.__parent.__init__(irc)
        self.res = []
        self.addressedRes = []
        self.unaddressedRes = []
        for name in self.regexps:
            method = getattr(self, name)
            r = re.compile(method.__doc__, self.flags)
            self.res.append((r, name))
        for name in self.addressedRegexps:
            method = getattr(self, name)
            r = re.compile(method.__doc__, self.flags)
            self.addressedRes.append((r, name))
        for name in self.unaddressedRegexps:
            method = getattr(self, name)
            r = re.compile(method.__doc__, self.flags)
            self.unaddressedRes.append((r, name))

    def _callRegexp(self, name, irc, msg, m):
        method = getattr(self, name)
        try:
            method(irc, msg, m)
        except Error as e:
            irc.error(str(e))
        except Exception as e:
            self.log.exception('Uncaught exception in _callRegexp:')

    def invalidCommand(self, irc, msg, tokens):
        s = ' '.join(tokens)
        for (r, name) in self.addressedRes:
            for m in r.finditer(s):
                self._callRegexp(name, irc, msg, m)

    def doPrivmsg(self, irc, msg):
        if msg.isError:
            return
        proxy = self.Proxy(irc, msg)
        if not msg.addressed:
            for (r, name) in self.unaddressedRes:
                for m in r.finditer(msg.args[1]):
                    self._callRegexp(name, proxy, msg, m)
        for (r, name) in self.res:
            for m in r.finditer(msg.args[1]):
                self._callRegexp(name, proxy, msg, m)
PrivmsgCommandAndRegexp = PluginRegexp


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
