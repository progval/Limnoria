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
Reads URLs from a channel, generally for web-based forums, and messages the
channel with useful information about the URL -- its forum, title, original
poster, etc.
"""

from baseplugin import *

import re
import urllib2

import utils
import debug
import ircmsgs
import ircutils
import callbacks

class Forums(callbacks.PrivmsgRegexp):
    threaded = True
    _ggThread = re.compile(r'<br>Subject: ([^<]+)<br>')
    _ggGroup = re.compile(r'Newsgroups: <a[^>]+>([^<]+)</a>')
    def googlegroups(self, irc, msg, match):
        r"http://groups.google.com/[^\s]+"
        request = urllib2.Request(match.group(0)+'&frame=off', headers=\
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

    _gkPlayer = re.compile(r"popd\('(Rating[^']+)'\).*?>([^<]+)<")
    _gkRating = re.compile(r": (\d+)[^:]+:<br>(\d+)[^,]+, (\d+)[^,]+, (\d+)")
    def gameknot(self, irc, msg, match):
        r"http://(?:www\.)?gameknot.com/chess.pl\?bd=\d+&r=\d+"
        #debug.printf('Got a GK URL from %s' % msg.prefix)
        url = match.group(0)
        fd = urllib2.urlopen(url)
        #debug.printf('Got the connection.')
        s = fd.read()
        #debug.printf('Got the string.')
        fd.close()
        try:
            ((wRating, wName), (bRating, bName)) = self._gkPlayer.findall(s)
            wName = ircutils.bold(wName)
            bName = ircutils.bold(bName)
            (wRating, wWins, wLosses, wDraws) = \
                      self._gkRating.search(wRating).groups()
            (bRating, bWins, bLosses, bDraws) = \
                      self._gkRating.search(bRating).groups()
            wStats = '%s; W-%s, L-%s, D-%s' % (wRating, wWins, wLosses, wDraws)
            bStats = '%s; W-%s, L-%s, D-%s' % (bRating, bWins, bLosses, bDraws)
            irc.queueMsg(ircmsgs.privmsg(msg.args[0],
              '%s (%s) vs. %s (%s) [%s]' % (wName,wStats,bName,bStats,url)))
        except ValueError:
            irc.queueMsg(ircmsgs.privmsg(msg.args[0],
              'That doesn\'t appear to be a proper Gameknot game.'))
        except Exception, e:
            irc.error(msg, debug.exnToString(e))


Class = Forums
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
