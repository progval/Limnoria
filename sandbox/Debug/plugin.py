#!/usr/bin/python

###
# Copyright (c) 2002-2005, Jeremiah Fincher
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
This is for jemfinch's debugging only.  If this somehow gets added and
committed, remove it immediately.  It must not be released with Supybot.
"""

import supybot.plugins as plugins

import gc
import os
import pwd
import sys
try:
    import exceptions
except ImportError: # Python 3
    import builtins
    class exceptions:
        """Pseudo-module"""
        pass
    for (key, value) in exceptions.__dict__.items():
        if isinstance(value, type) and issubclass(value, Exception):
            exceptions[key] = value

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.callbacks as callbacks

def getTracer(fd):
    def tracer(frame, event, _):
        if event == 'call':
            code = frame.f_code
            print >>fd, '%s: %s' % (code.co_filename, code.co_name)
    return tracer

class Debug(callbacks.Privmsg):
    capability = 'owner'
    def __init__(self, irc):
        # Setup exec command.
        self.__parent = super(Debug, self)
        self.__parent.__init__(irc)
        setattr(self.__class__, 'exec', self.__class__._exec)

    def callCommand(self, name, irc, msg, *args, **kwargs):
        if ircdb.checkCapability(msg.prefix, self.capability):
            self.__parent.callCommand(name, irc, msg, *args, **kwargs)
        else:
            irc.errorNoCapability(self.capability)
            
    _evalEnv = {'_': None,
                '__': None,
                '___': None,
                }
    _evalEnv.update(globals())
    def eval(self, irc, msg, args, s):
        """<expression>

        Evaluates <expression> (which should be a Python expression) and
        returns its value.  If an exception is raised, reports the
        exception (and logs the traceback to the bot's logfile).
        """
        try:
            self._evalEnv.update(locals())
            x = eval(s, self._evalEnv, self._evalEnv)
            self._evalEnv['___'] = self._evalEnv['__']
            self._evalEnv['__'] = self._evalEnv['_']
            self._evalEnv['_'] = x
            irc.reply(repr(x))
        except SyntaxError, e:
            irc.reply(format('%s: %q', utils.exnToString(e), s))
    eval = wrap(eval, ['text'])

    def _exec(self, irc, msg, args, s):
        """<statement>

        Execs <code>.  Returns success if it didn't raise any exceptions.
        """
        exec s
        irc.replySuccess()
    _exec = wrap(_exec, ['text'])

    def simpleeval(self, irc, msg, args, text):
        """<expression>

        Evaluates the given expression.
        """
        try:
            irc.reply(repr(eval(text)))
        except Exception, e:
            irc.reply(utils.exnToString(e))
    simpleeval = wrap(simpleeval, ['text'])

    def exn(self, irc, msg, args, name):
        """<exception name>

        Raises the exception matching <exception name>.
        """
        if isinstance(__builtins__, dict):
            exn = __builtins__[name]
        else:
            exn = getattr(__builtins__, name)
        raise exn, msg.prefix
    exn = wrap(exn, ['text'])

    def sendquote(self, irc, msg, args, text):
        """<raw IRC message>

        Sends (not queues) the raw IRC message given.
        """
        msg = ircmsgs.IrcMsg(text)
        irc.sendMsg(msg)
    sendquote = wrap(sendquote, ['text'])

    def settrace(self, irc, msg, args, filename):
        """[<filename>]

        Starts tracing function calls to <filename>.  If <filename> is not
        given, sys.stdout is used.  This causes much output.
        """
        if filename:
            fd = file(filename, 'a')
        else:
            fd = sys.stdout
        sys.settrace(getTracer(fd))
        irc.replySuccess()
    settrace = wrap(settrace, [additional('filename')])

    def unsettrace(self, irc, msg, args):
        """takes no arguments

        Stops tracing function calls on stdout.
        """
        sys.settrace(None)
        irc.replySuccess()
    unsettrace = wrap(unsettrace)

    def channeldb(self, irc, msg, args, channel):
        """[<channel>]

        Returns the result of the channeldb converter.
        """
        irc.reply(channel)
    channeldb = wrap(channeldb, ['channeldb'])

    def collect(self, irc, msg, args, times):
        """[<times>]

        Does <times> gc collections, returning the number of objects collected
        each time.  <times> defaults to 1.
        """
        L = []
        while times:
            L.append(gc.collect())
            times -= 1
        irc.reply(format('%L', map(str, L)))
    collect = wrap(collect, [additional('positiveInt', 1)])

    _progstats_endline_remover = utils.str.MultipleRemover('\r\n')
    def progstats(self, irc, msg, args):
        """takes no arguments

        Returns various unix-y information on the running supybot process.
        """
        pw = pwd.getpwuid(os.getuid())
        response = 'Process ID %s running as user "%s" and as group "%s" ' \
                   'from directory "%s" with the command line "%s".  ' \
                   'Running on Python %s.' % \
                   (os.getpid(), pw[0], pw[3],
                    os.getcwd(), ' '.join(sys.argv),
                    self._progstats_endline_remover(sys.version))
        irc.reply(response)
    progstats = wrap(progstats)

    def environ(self, irc, msg, args):
        """takes no arguments

        Returns the environment of the supybot process.
        """
        irc.reply(repr(os.environ))
    environ = wrap(environ)


Class = Debug

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
