###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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

import types
import random

from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Utilities')

class Utilities(callbacks.Plugin):
    """Provides useful commands for bot scripting / command nesting."""
    # Yes, I really do mean "requires no arguments" below.  "takes no
    # arguments" would probably lead people to think it was a useless command.
    @internationalizeDocstring
    def ignore(self, irc, msg, args):
        """requires no arguments

        Does nothing.  Useful sometimes for sequencing commands when you don't
        care about their non-error return values.
        """
        msg.tag('ignored')
        irc.noReply()
    # Do be careful not to wrap this unless you do any('something').

    @internationalizeDocstring
    def success(self, irc, msg, args, text):
        """[<text>]

        Does nothing except to reply with a success message.  This is useful
        when you want to run multiple commands as nested commands, and don't
        care about their output as long as they're successful.  An error, of
        course, will break out of this command.  <text>, if given, will be
        appended to the end of the success message.
        """
        irc.replySuccess(text)
    success = wrap(success, [additional('text')])

    @internationalizeDocstring
    def last(self, irc, msg, args):
        """<text> [<text> ...]

        Returns the last argument given.  Useful when you'd like multiple
        nested commands to run, but only the output of the last one to be
        returned.
        """
        args = list(filter(None, args))
        if args:
            irc.reply(args[-1])
        else:
            raise callbacks.ArgumentError

    @internationalizeDocstring
    def echo(self, irc, msg, args, text):
        """<text>

        Returns the arguments given it.  Uses our standard substitute on the
        string(s) given to it; $nick (or $who), $randomNick, $randomInt,
        $botnick, $channel, $user, $host, $today, $now, and $randomDate are all
        handled appropriately.
        """
        text = ircutils.standardSubstitute(irc, msg, text)
        irc.reply(text, prefixNick=False)
    echo = wrap(echo, ['text'])

    @internationalizeDocstring
    def shuffle(self, irc, msg, args, things):
        """<arg> [<arg> ...]

        Shuffles the arguments given.
        """
        random.shuffle(things)
        irc.reply(' '.join(things))
    shuffle = wrap(shuffle, [many('anything')])

    @internationalizeDocstring
    def sort(self, irc, msg, args, things):
        """<arg> [<arg> ...]

        Sorts the arguments given.
        """
        irc.reply(' '.join(map(str, sorted(things))))
    # Keep ints as ints, floats as floats, without comparing between numbers
    # and strings.
    sort = wrap(sort, [first(many(first('int', 'float')), many('anything'))])

    @internationalizeDocstring
    def sample(self, irc, msg, args, num, things):
        """<num> <arg> [<arg> ...]

        Randomly chooses <num> items out of the arguments given.
        """
        try:
            samp = random.sample(things, num)
            irc.reply(' '.join(samp))
        except ValueError as e:
            irc.error('%s' % (e,))
    sample = wrap(sample, ['positiveInt', many('anything')])

    @internationalizeDocstring
    def countargs(self, irc, msg, args, things):
        """<arg> [<arg> ...]

        Counts the arguments given.
        """
        irc.reply(len(things))
    countargs = wrap(countargs, [any('anything')])

    @internationalizeDocstring
    def apply(self, irc, msg, args, command, rest):
        """<command> <text>

        Tokenizes <text> and calls <command> with the resulting arguments.
        """
        args = [token and token or '""' for token in rest]
        text = ' '.join(args)
        commands = command.split()
        commands = list(map(callbacks.canonicalName, commands))
        tokens = callbacks.tokenize(text,
            channel=msg.channel, network=irc.network)
        allTokens = commands + tokens
        self.Proxy(irc, msg, allTokens)
    apply = wrap(apply, ['something', many('something')])

    def let(self, irc, msg, args, var_name, _, value, __, command):
        """<variable> = <value> in <command>

        Defines <variable> to be equal to <value> in the <command>
        and runs the <command>.
        '=' and 'in' can be omitted."""
        if msg.reply_env and var_name in msg.reply_env:
            # For security reason (eg. a Sudo-like plugin), we don't want
            # to make it possible to override stuff like $nick.
            irc.error(_('Cannot set a variable that already exists.'),
                    Raise=True)

        fake_msg = ircmsgs.IrcMsg(msg=msg)
        if fake_msg.reply_env is None:
            fake_msg.reply_env = {}
        fake_msg.reply_env[var_name] = value
        tokens = callbacks.tokenize(command,
            channel=msg.channel, network=irc.network)
        self.Proxy(irc, fake_msg, tokens)

    let = wrap(let, [
            'something', optional(('literal', ['='])), 'something',
            optional(('literal', ['in'])), 'text'])


Class = Utilities

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
