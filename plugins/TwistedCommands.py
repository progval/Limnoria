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
Various commands that depend on Twisted <http://www.twistedmatrix.com/>.
"""

from baseplugin import *

from twisted.protocols import dict

import debug
import ircutils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load TwistedCommands')

class TwistedCommands(callbacks.Privmsg):
    def defaultErrback(self, irc, msg):
        def errback(failure):
            failure.printDetailedTraceback()
            irc.error(msg, failure.getErrorMessage())
        return errback
    
    def dictCallback(self, irc, msg, word):
        def formatDictResults(definitions):
            L = []
            for definition in definitions:
                L.append(' '.join(definition.text))
            if not L:
                irc.reply(msg, '%s appears to have no definition.' % word)
                return
            s = ircutils.privmsgPayload(L, ', or ', 400).encode('utf-8')
            s = ' '.join(s.split()) # Normalize whitespace.
            irc.reply(msg, s)
        return formatDictResults

    def dict(self, irc, msg, args):
        """<word>

        Returns some definitions WordNet gives for <word>.
        """
        word = privmsgs.getArgs(args)
        deferred = dict.define('dict.org', 2628, 'wn', word)
        deferred.addCallback(self.dictCallback(irc, msg, word))
        deferred.addErrback(self.defaultErrback(irc, msg))
            


Class = TwistedCommands

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
