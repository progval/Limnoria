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

import re

from twisted.protocols import dict

import utils
import ircutils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    try:
        import twisted
        onStart.append('load TwistedCommands')
    except ImportError:
        print 'Sorry, you don\'t seem to have Twisted installed.'
        print 'You can\'t use this module without Twisted being installed.'
        print 'Once you\'ve installed Twisted, change conf.driverModule to'
        print '"twistedDrivers" and add "load TwistedCommands" to your config'
        print 'file.'

example = utils.wrapLines("""
<jemfinch> @load TwistedCommands
<supybot> The operation succeeded.
<jemfinch> @list TwistedCommands
<supybot> dict
<jemfinch> @dict rose
<supybot> adj : having a dusty purplish pink color; "the roseate glow of dawn" [syn: {roseate}, {rosaceous}] n 1: any of many plants of the genus Rosa, or pinkish table wine from red grapes whose skins were removed after fermentation began [syn: {blush wine}, {pink wine}, {rose wine}]
""")

class TwistedCommands(callbacks.Privmsg):
    def defaultErrback(self, irc, msg):
        def errback(failure):
            failure.printDetailedTraceback()
            irc.error(msg, failure.getErrorMessage())
        return errback

    dictnumberre = re.compile('^\d+:\s*(.*)$')
    def dictCallback(self, irc, msg, word):
        def formatDictResults(definitions):
            defs = []
            for definition in definitions:
                definition.text.pop(0)
                lines = map(str.strip, map(str, definition.text))
                L = []
                for line in lines:
                    m = self.dictnumberre.match(line)
                    if m:
                        defs.append(' '.join(L))
                        L = []
                        L.append(m.group(1))
                    else:
                        L.append(line)
            if not defs:
                irc.reply(msg, '%s appears to have no definition.' % word)
                return
            s = ircutils.privmsgPayload(defs, ', or ', 400).encode('utf-8')
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


class TwistedRegexp(callbacks.PrivmsgRegexp):
    def dccrecv(self, irc, msg, match):
        r""


Class = TwistedCommands

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
