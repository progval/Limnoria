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

from baseplugin import *

import re
import urllib2

import ircmsgs
import ircutils
import ircutils
import callbacks

htmlStripper = re.compile(r'<[^>]+>')
def stripHtml(s):
    return htmlStripper.sub('', s)

class Forums(callbacks.PrivmsgRegexp):
    threaded = True
    _ggThread = re.compile(r'from thread &quot;<b>(.*?)</b>&quot;')
    _ggGroup = re.compile(r'Newsgroups: <a.*?>(.*?)</a>')
    def googlegroups(self, irc, msg, match):
        r"http://groups.google.com/[^\s]+"
        request = urllib2.Request(match.group(0), headers=\
          {'User-agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 4.0)'})
        fd = urllib2.urlopen(request)
        text = fd.read()
        mThread = self._ggThread.search(text)
        mGroup = self._ggGroup.search(text)
        if mThread and mGroup:
            irc.queueMsg(ircmsgs.privmsg(ircutils.reply(msg),
              'Google Groups: %s, %s' % (mGroup.group(1), mThread.group(1))))
        else:
            irc.queueMsg(ircmsgs.privmsg(msg.args[0],
              'That doesn\'t appear to be a proper Google Groups page.'))

    gkPlayer = re.compile(r"popd\('(Rating[^']+)'\).*?>([^<]+)<")
    def gameknot(self, irc, msg, match):
        r"http://(?:www\.)?gameknot.com/chess.pl\?bd=\d+&r=\d+"
        fd = urllib2.urlopen(match.group(0))
        s = fd.read()
        try:
            ((wRating, wName), (bRating, bName)) = self.gkPlayer.findall(s)
            wName = ircutils.bold(wName)
            bName = ircutils.bold(bName)
            wRating = wRating.replace('<br>', ' ')
            bRating = bRating.replace('<br>', ' ')
            wRating = wRating.replace('Wins', '; Wins')
            bRating = bRating.replace('Wins', '; Wins ')
            irc.queueMsg(ircmsgs.privmsg(msg.args[0],
              '%s (%s) vs. %s (%s)' % (wName, wRating, bName, bRating)))
            
        except ValueError:
            irc.queueMsg(ircmsgs.privmsg(msg.args[0],
              'That doesn\'t appear to be a proper Gameknot game.'))


Class = Forums
