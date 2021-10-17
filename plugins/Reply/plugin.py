###
# Copyright (c) 2005, Daniel DiPaolo
# Copyright (c) 2010-2021, Valentin Lorentz
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

from supybot.commands import *
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Reply')


class Reply(callbacks.Plugin):
    """This plugin contains a few commands that construct various types of
    replies.  Some bot owners would be wise to not load this plugin because it
    can be easily abused.
    """
    @internationalizeDocstring
    def private(self, irc, msg, args, text):
        """<text>

        Replies with <text> in private.  Use nested commands to your benefit
        here.
        """
        irc.reply(text, private=True)
    private = wrap(private, ['text'])

    @internationalizeDocstring
    def action(self, irc, msg, args, text):
        """<text>

        Replies with <text> as an action.  Use nested commands to your benefit
        here.
        """
        if text:
            irc.reply(text, action=True)
        else:
            raise callbacks.ArgumentError
    action = wrap(action, ['text'])

    @internationalizeDocstring
    def notice(self, irc, msg, args, text):
        """<text>

        Replies with <text> in a notice.  Use nested commands to your benefit
        here.  If you want a private notice, nest the private command.
        """
        irc.reply(text, notice=True)
    notice = wrap(notice, ['text'])

    @internationalizeDocstring
    def reply(self, irc, msg, args, text):
        """<text>

        Replies with <text>.  Equivalent to the alias, 'echo $nick: $1'.
        """
        irc.reply(text, prefixNick=True)
    reply = wrap(reply, ['text'])

    @internationalizeDocstring
    def replies(self, irc, msg, args, strings):
        """<str> [<str> ...]

        Replies with each of its arguments <str> in separate replies, depending
        the configuration of supybot.reply.oneToOne.
        """
        irc.replies(strings)
    replies = wrap(replies, [many('something')])
Reply = internationalizeDocstring(Reply)

Class = Reply


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
