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
Various utility commands, mostly useful for manipulating nested commands.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import string

import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks

class Utilities(callbacks.Privmsg):
    def ignore(self, irc, msg, args):
        """requires no arguments

        Does nothing.  Useful sometimes for sequencing commands when you don't
        care about their non-error return values.
        """
        pass

    def reply(self, irc, msg, args):
        """<text>

        Replies with <text>.  Equivalent to the alias, 'echo $nick: $1'.
        """
        text = privmsgs.getArgs(args)
        irc.reply(text)

    def success(self, irc, msg, args):
        """[<text>]

        Does nothing except to reply with a success message.  This is useful
        when you want to run multiple commands as nested commands, and don't
        care about their output as long as they're successful.  An error, of
        course, will break out of this command.  <text>, if given, will be
        appended to the end of the success message.
        """
        text = privmsgs.getArgs(args, required=0, optional=1)
        irc.replySuccess(text)

    def last(self, irc, msg, args):
        """<text> [<text> ...]

        Returns the last argument given.  Useful when you'd like multiple
        nested commands to run, but only the output of the last one to be
        returned.
        """
        if args:
            irc.reply(args[-1])
        else:
            raise callbacks.Error

    def strlen(self, irc, msg, args):
        """<text>

        Returns the length of <text>.
        """
        total = 0
        for arg in args:
            total += len(arg)
        total += len(args)-1 # spaces between the arguments.
        irc.reply(str(total))

    def echo(self, irc, msg, args):
        """takes any number of arguments

        Returns the arguments given it.  Uses our standard substitute on the
        string(s) given to it; $nick (or $who), $randomNick, $randomInt,
        $botnick, $channel, $user, $host, $today, $now, and $randomDate are all
        handled appropriately.
        """
        if not args:
            raise callbacks.ArgumentError
        text = privmsgs.getArgs(args)
        text = plugins.standardSubstitute(irc, msg, text)
        irc.reply(text, prefixName=False)

    def re(self, irc, msg, args):
        """<regexp> <text>

        If <regexp> is of the form m/regexp/flags, returns the portion of
        <text> that matches the regexp.  If <regexp> is of the form
        s/regexp/replacement/flags, returns the result of applying such a
        regexp to <text>
        """
        (regexp, text) = privmsgs.getArgs(args, required=2)
        self.log.info('re command called with regexp %r from %s' %
                      (regexp, msg.prefix))
        if len(regexp) > 512:
            irc.error('Your regexp is just plain too long.')
            return
        f = None
        try:
            r = utils.perlReToPythonRe(regexp)
            f = lambda s: r.search(s) and r.search(s).group(0) or ''
        except ValueError, e:
            try:
                f = utils.perlReToReplacer(regexp)
            except ValueError, e:
                irc.error('Invalid regexp: %s' % e.args[0])
                return
            if f is None:
                irc.error('Invalid regexp: %s' % e.args[0])
                return
        if f('') and len(f(' ')) > len(f(''))+1: # Matches the empty string.
            s = 'You probably don\'t want to match the empty string.'
            irc.error(s)
        else:
            irc.reply(f(text))
    re = privmsgs.checkCapability(re, 'trusted')

    def apply(self, irc, msg, args):
        """<command> <text>

        Tokenizes <text> and calls <command> with the resulting arguments.
        """
        if not args:
            raise callbacks.ArgumentError
        command = args.pop(0)
        args = [token and token or '""' for token in args]
        text = privmsgs.getArgs(args)
        commands = command.split()
        commands = map(callbacks.canonicalName, commands)
        tokens = callbacks.tokenize(text)
        allTokens = commands + tokens
        print '***', allTokens
        Owner = irc.getCallback('Owner')
        Owner.processTokens(irc, msg, allTokens)



Class = Utilities
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
