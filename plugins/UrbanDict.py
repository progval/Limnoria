#!/usr/bin/env python

###
# Copyright (c) 2004, Kevin Murphy
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
Provides an interface to the wonders of UrbanDictionary.com.  This may include
some offensive definitions.
"""

__revision__ = "$Id$"

import supybot

__author__ = supybot.authors.skorobeus

import supybot.plugins as plugins

import re
import sets
import getopt
import socket
import urllib
import xml.dom.minidom
from itertools import imap, ifilter

import supybot.conf as conf
import supybot.utils as utils
import supybot.webutils as webutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

conf.registerPlugin('UrbanDict')

class UrbanDict(callbacks.Privmsg):
    threaded = True
    callBefore = ['URL']
    def callCommand(self, method, irc, msg, *L, **kwargs):
        try:
            super(UrbanDict, self).callCommand(method, irc, msg, *L, **kwargs)
        except webutils.WebError, e:
            irc.error(str(e))

    _wordRE = re.compile(r'<title>UrbanDictionary.com/(?P<word>.*?)</title>')
    _defUsageRE = re.compile(r'<blockquote><p>(?P<definition>.*?)</p>'
                             r'<p><i>(?P<usage>.*?)</i></p>',
                             re.MULTILINE | re.DOTALL)
    def ud(self, irc, msg, args):
        """[<phrase>]

        Returns the definition and usage of a random word from 
        UrbanDictionary.com.  The optional argument <phrase> specifies
        what phrase to define
        """
        phrase = '+'.join(privmsgs.getArgs(args, required=0).split())
        if phrase:
            phrase = 'define.php?term=%s' % phrase
        else:
            phrase = 'random.php'
        site = 'www.urbandictionary.com'
        html = webutils.getUrl('http://%s/%s' % (site, phrase))
        wordMatch = self._wordRE.search(html)
        defMatch = self._defUsageRE.findall(html)
        if not wordMatch or not defMatch:
            irc.error('No definition found.')
            return
        word = '%(word)s' % wordMatch.groupdict()
        definitions = ['%s (%s)' % (pair[0], pair[1]) for pair in defMatch]
        irc.reply(utils.htmlToText('%s: %s' % (word, '; '.join(definitions))))

Class = UrbanDict

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
