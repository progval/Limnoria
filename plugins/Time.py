#!/usr/bin/python

###
# Copyright (c) 2004, Jeremiah Fincher
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
A plugin for time-related functions.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch
__contributors__ = {}

import supybot.plugins as plugins

import supybot.conf as conf
import supybot.utils as utils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Time', True)


class Time(callbacks.Privmsg):
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
                irc.errorInvalid('argument', arg, Raise=True)
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

    def at(self, irc, msg, args):
        """<time string>

        Returns the number of seconds since epoch <time string> is.
        <time string> can be any number of natural formats; just try something
        and see if it will work.
        """
        s = privmsgs.getArgs(args)

    def until(self, irc, msg, args):
        """<time string>

        Returns the number of seconds until <time string>.
        """
        s = privmsgs.getArgs(args)

    def ctime(self, irc, msg, args):
        """[<seconds since epoch>]

        Returns the ctime for <seconds since epoch>, or the current ctime if
        no <seconds since epoch> is given.
        """
        seconds = privmsgs.getArgs(args)
        if seconds:
            try:
                seconds = float(seconds)
            except ValueError:
                irc.errorInvalid('seconds', seconds, Raise=True)
        else:
            seconds = time.time()
        irc.reply(time.ctime(seconds))

    def time(self, irc, msg, args):
        """[<format>] [<seconds since epoch>]

        Returns the current time in <format> format, or, if <format> is not
        given, uses the configurable format for the current channel.  If no
        <seconds since epoch> time is given, the current time is used.
        """
        channel = privmsgs.getChannel(msg, args, raiseError=False)
        (format, seconds) = privmsgs.getArgs(args, required=0, optional=2)
        if not format:
            if channel:
                format = self.registryValue('format', channel)
            else:
                format = self.registryValue('format')
        if not seconds:
            seconds = time.time()
        else:
            try:
                seconds = float(seconds)
            except ValueError:
                irc.errorInvalid('seconds', seconds, Raise=True)
        irc.reply(time.strftime(format, time.localtime(seconds)))



Class = Time

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
