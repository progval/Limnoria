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

from fix import *

import re
import time
import shlex
import inspect
import threading
import sre_constants
from cStringIO import StringIO

import conf
import ircdb
import irclib
import ircmsgs
import ircutils

import debug

###
# Privmsg: handles privmsg commands in a standard fashion.
###
def addressed(nick, msg):
    """If msg is addressed to 'name', returns the portion after the address.
    """
    if msg.args[0] == nick:
        if msg.args[1][0] in conf.prefixChars:
            return msg.args[1][1:].strip()
        else:
            return msg.args[1].strip()
    elif ircutils.toLower(msg.args[1]).startswith(nick):
        try:
            return msg.args[1].split(None, 1)[1].strip()
        except IndexError:
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
    return command.translate(string.ascii, '\t -_').lower()

def reply(msg, s):
    """Makes a reply to msg with the payload s"""
    s = ircutils.safeArgument(s)
    if ircutils.isChannel(msg.args[0]):
        m = ircmsgs.privmsg(msg.args[0], '%s: %s' % (msg.nick, s))
    else:
        m = ircmsgs.privmsg(msg.nick, s)
    if len(m) > 450:
        m = reply(msg, 'My response would\'ve been too long.')
    return m
        
class RateLimiter:
    lastRequest = {}
    def __init__(self):
        self.limited = []
        self.unlimited = []

    def get(self):
        if self.unlimited:
            return self.unlimited.pop(0)
        elif self.limited:
            for i in range(len(self.limited)):
                msg = self.limited[i]
                if not self.limit(msg, penalize=False):
                    return self.limited.pop(i)
            return None
        else:
            return None

    def put(self, msg):
        if not self.limit(msg):
            self.unlimited.append(msg)
        else:
            debug.printf('Limiting message from %s' % msg.prefix)
            self.limited.append(msg)

    def limit(self, msg, penalize=True):
        if msg.prefix and ircutils.isUserHostmask(msg.prefix):
            (nick, user, host) = ircutils.splitHostmask(msg.prefix)
            key = '@'.join((user, host))
            now = time.time()
            if ircdb.checkCapabilities(msg.prefix, ('owner', 'admin')):
                return False
            if key in self.lastRequest:
                # Here's how we throttle requests.  We keep a dictionary of
                # (lastRequest, wait period) tuples.  When a request arrives,
                # we check to see if we have a lastRequest tuple, and if so,
                # we check to make sure that lastRequest was more than wait
                # seconds ago.  If not, we're getting flooded, and we set
                # the lastRequest time to the current time and increment wait,
                # thus making it even harder for the flooder to get us to
                # send them messages.
                (t, wait) = self.lastRequest[key]
                if now - t <= wait:
                    if penalize:
                        self.lastRequest[key] = (now, wait+conf.throttleTime)
                    else:
                        self.lastRequest[key] = (now, wait - (now - t))
                    return True
                else:
                    self.lastRequest[key] = (now, conf.throttleTime)
                    return False
            else:
                self.lastRequest[key] = (now, conf.throttleTime)
                return False
        else:
            return False


class Error(Exception):
    """Generic class for errors in Privmsg callbacks."""
    pass

class ArgumentError(Error):
    pass

class Tokenizer:
    quotes = '"`'
    nonbacktickquotes = '"'
    validChars = string.ascii[33:].translate(string.ascii, '"`[]')
    def __init__(self, tokens=''):
        self.validChars = self.validChars.translate(string.ascii, tokens)

    def handleToken(self, token):
        while token and token[0] in self.quotes and token[-1] == token[0]:
            if len(token) > 1:
                token = eval('"%s"' % token[1:-1])
            else:
                break
        return token

    def insideBrackets(self, lexer):
        ret = []
        while True:
            token = lexer.get_token()
            if token == '':
                raise SyntaxError, 'Missing "]"'
            elif token == ']':
                return ret
            elif token == '[':
                ret.append(self.insideBrackets(lexer))
            else:
                ret.append(self.handleToken(token))
        return ret

    def tokenize(self, s):
        lexer = shlex.shlex(StringIO(s))
        lexer.commenters = ''
        lexer.quotes = self.quotes
        lexer.wordchars = self.validChars
        args = []
        while True:
            token = lexer.get_token()
            if token == '':
                break
            elif token == '[':
                args.append(self.insideBrackets(lexer))
            elif token == ']':
                raise SyntaxError, 'Spurious "["'
            else:
                args.append(self.handleToken(token))
        return args

def tokenize(s):
    try:
        return Tokenizer().tokenize(s)
    except ValueError, e:
        raise SyntaxError, str(e)

class IrcObjectProxy:
    def __init__(self, irc, msg, args):
        #debug.printf('__init__: %s' % args)
        self.irc = irc
        self.msg = msg
        self.args = args
        self.counter = 0
        self.finalEvaled = False
        self.evalArgs()

    def findCallback(self, commandName):
        for callback in self.irc.callbacks:
            if hasattr(callback, 'isCommand'):
                if callback.isCommand(commandName):
                    return callback
        return None

    def evalArgs(self):
        while self.counter < len(self.args):
            if type(self.args[self.counter]) == str:
                self.counter += 1
            else:
                IrcObjectProxy(self, self.msg, self.args[self.counter])
                return
        self.finalEval()

    def finalEval(self):
        self.finalEvaled = True
        name = canonicalName(self.args.pop(0))
        callback = self.findCallback(name)
        try:
            if callback is not None:
                anticap = ircdb.makeAntiCapability(name)
                if ircdb.checkCapability(self.msg.prefix, anticap):
                    debug.msg('Preventing %s from calling %s' % \
                              (self.msg.nick, name))
                    return
                recipient = self.msg.args[0]
                if ircutils.isChannel(recipient):
                    chancap = ircdb.makeChannelCapability(recipient, anticap)
                    if ircdb.checkCapability(self.msg.prefix, chancap):
                        debug.msg('Preventing %s from calling %s' % \
                                  (self.msg.nick, name))
                        return
                command = getattr(callback, name)
                callback.callCommand(command, self, self.msg, self.args)
            else:
                self.args.insert(0, name)
                self.reply(self.msg, '[%s]' % ' '.join(self.args))
        except ArgumentError:
            self.reply(self.msg, command.__doc__.splitlines()[0])
        except Error, e:
            self.reply(self.msg, debug.exnToString(e))
        except Exception, e:
            debug.recoverableException()
            self.reply(self.msg, debug.exnToString(e))

    def reply(self, msg, s):
        if self.finalEvaled:
            if isinstance(self.irc, self.__class__):
                self.irc.reply(msg, s)
            else:
                s = ircutils.safeArgument(s)
                self.irc.queueMsg(reply(msg, s))
        else:
            self.args[self.counter] = s
            self.evalArgs()

    def error(self, msg, s):
        self.reply(msg, 'Error: ' + s)

    def killProxy(self):
        if not isinstance(self.irc, irclib.Irc):
            self.irc.killProxy()
        self.__dict__ = {}

    def getRealIrc(self):
        if isinstance(self.irc, irclib.Irc):
            return self.irc
        else:
            return self.irc.getRealIrc()

    def __getattr__(self, attr):
        return getattr(self.irc, attr)


class CommandThread(threading.Thread):
    def __init__(self, command, irc, msg, args):
        name = '%s.%s with args %r' % (command.im_class.__name__,
                                       command.im_func.func_name, args)
        threading.Thread.__init__(self, target=command, name=name,
                                  args=(irc, msg, args))
        self.irc = irc
        self.msg = msg
        self.setDaemon(True)
        
    def run(self):
        try:
            threading.Thread.run(self)
        except Error, e:
            self.irc.reply(self.msg, debug.exnToString(e))
        except Exception, e:
            debug.recoverableException()
            self.irc.error(self.msg, debug.exnToString(e))

        
class Privmsg(irclib.IrcCallback):
    """Base class for all Privmsg handlers."""
    threaded = False
    public = True
    commandArgs = ['self', 'irc', 'msg', 'args']
    def __init__(self):
        self.rateLimiter = RateLimiter()
        self.Proxy = IrcObjectProxy

    def __call__(self, irc, msg):
        irclib.IrcCallback.__call__(self, irc, msg)
        # Now, if there's anything in the rateLimiter...
        msg = self.rateLimiter.get()
        if msg:
            s = addressed(irc.nick, msg)
            try:
                args = tokenize(s)
            except SyntaxError, e:
                irc.queueMsg(reply(msg, debug.exnToString(e)))
            self.Proxy(irc, msg, args)

    def isCommand(self, methodName):
        # This function is ugly, but I don't want users to call methods like
        # doPrivmsg or __init__ or whatever, and this is good to stop them.
        if hasattr(self, methodName):
            method = getattr(self, methodName)
            if inspect.ismethod(method):
                code = method.im_func.func_code
                return inspect.getargs(code) == (self.commandArgs, None, None)
            else:
                return False
        else:
            return False

    def callCommand(self, f, irc, msg, args):
        if self.threaded:
            thread = CommandThread(f, irc, msg, args)
            thread.start()
            debug.printf('Spawned new thread: %s' % thread)
        else:
            # Exceptions aren't caught here because IrcObjectProxy.finalEval
            # catches them and does The Right Thing.
            f(irc, msg, args)

    _r = re.compile(r'^(\w+)')
    def doPrivmsg(self, irc, msg):
        s = addressed(irc.nick, msg)
        #debug.printf('Privmsg.doPrivmsg: s == %r' % s)
        if s:
            recipient = msg.args[0]
            if ircdb.checkIgnored(msg.prefix, recipient):
                debug.printf('Privmsg.doPrivmsg: ignoring.')
                return
            m = self._r.match(s)
            if m and self.isCommand(canonicalName(m.group(1))):
                self.rateLimiter.put(msg)
                msg = self.rateLimiter.get()
                if msg:
                    args = tokenize(s)
                    self.Proxy(irc, msg, args)


class IrcObjectProxyRegexp:
    def __init__(self, irc, *args):
        self.irc = irc

    def error(self, msg, s):
        self.reply(msg, 'Error: ' + s)

    def reply(self, msg, s):
        self.irc.queueMsg(reply(msg, s))

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
    threaded = False # Again, like Privmsg...
    flags = re.I
    def __init__(self):
        Privmsg.__init__(self)
        self.Proxy = IrcObjectProxyRegexp
        self.res = []
        #for name, value in self.__class__.__dict__.iteritems():
        for name, value in self.__class__.__dict__.items():
            value = getattr(self, name)
            if name[0] != '_' and inspect.ismethod(value) and \
               inspect.getargs(value.im_func.func_code) == \
               (['self', 'irc', 'msg', 'match'], None, None):
                try:
                    r = re.compile(value.__doc__, self.flags)
                    self.res.append((r, value))
                except sre_constants.error, e:
                    s = '%s.%s has an invalid regexp %s: %s' % \
                        (self.__class__.__name__, name,
                         value.__doc__, debug.exnToString(e))
                    debug.msg(s)

    def doPrivmsg(self, irc, msg):
        for (r, method) in self.res:
            m = r.search(msg.args[1])
            if m:
                self.rateLimiter.put(msg)
                msg = self.rateLimiter.get()
                if msg:
                    irc = IrcObjectProxyRegexp(irc)
                    self.callCommand(method, irc, msg, m)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
