#!/usr/bin/python

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
This is for jemfinch's debugging only.  If this somehow gets added and
committed, remove it immediately.  It must not be released.
"""

import supybot.plugins as plugins

import sys
import exceptions

import supybot.conf as conf
import supybot.utils as utils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from questions import expect, anything, something, yn
    conf.registerPlugin('Debug', True)

def getTracer(fd):
    def tracer(frame, event, _):
        if event == 'call':
            code = frame.f_code
            print >>fd, '%s: %s' % (code.co_filename, code.co_name)
    return tracer


class Debug(privmsgs.CapabilityCheckingPrivmsg):
    capability = 'owner'
    def eval(self, irc, msg, args):
        """<expression>

        Evaluates the given expression.
        """
        s = privmsgs.getArgs(args)
        try:
            irc.reply(repr(eval(s)))
        except Exception, e:
            irc.reply(utils.exnToString(e))

    def exn(self, irc, msg, args):
        """<exception name>

        Raises the exception matching <exception name>.
        """
        name = privmsgs.getArgs(args)
        exn = getattr(exceptions, name)
        raise exn, msg.prefix

    def sendquote(self, irc, msg, args):
        """<raw IRC message>

        Sends (not queues) the raw IRC message given.
        """
        msg = ircmsgs.IrcMsg(privmsgs.getArgs(args))
        irc.sendMsg(msg)

    def settrace(self, irc, msg, args):
        """[<filename>]

        Starts tracing function calls to <filename>.  If <filename> is not
        given, sys.stdout is used.  This causes much output.
        """
        filename = privmsgs.getArgs(args, optional=1, required=0)
        if filename:
            fd = file(filename, 'a')
        else:
            fd = sys.stdout
        sys.settrace(getTracer(fd))
        irc.replySuccess()

    def unsettrace(self, irc, msg, args):
        """takes no arguments

        Stops tracing function calls on stdout.
        """
        sys.settrace(None)
        irc.replySuccess()


Class = Debug

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
