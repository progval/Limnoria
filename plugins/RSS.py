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
Add the module docstring here.  This will be used by the setup.py script.
"""

from baseplugin import *

import time

import rssparser

import privmsgs
import callbacks

class RSS(callbacks.Privmsg):
    threaded = True
    _slashdotTime = 0.0
    def slashdot(self, irc, msg, args):
        """takes no arguments

        Returns the current headlines on slashdot.org, News for Nerds, Stuff
        that Matters.
        """
        if time.time() - self._slashdotTime > 1800:
            results = rssparser.parse('http://slashdot.org/slashdot.rss')
            headlines = [x['title'] for x in results['items']]
            self._slashdotResponse = ' :: '.join(headlines)
            while len(self._slashdotResponse) > 400:
                headlines.pop()
                self._slashdotResponse = ' :: '.join(headlines)
            self._slashdotTime = time.time()
        irc.reply(msg, self._slashdotResponse)


Class = RSS

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
