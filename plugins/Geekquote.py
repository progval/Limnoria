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
Provides commands and snarfers for the various different Geekquote-based sites
out there
"""

import supybot

__author__ = supybot.authors.skorobeus
__contributors__ = {
    supybot.authors.skorobeus: ['geekquote snarfer', 'qdb'],
    }

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

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Geekquote', True)
    output("""The Http plugin has the ability to watch for geekquote
              (bash.org / qdb.us) URLs and respond to them as though the user
              had asked for the geekquote by ID""")
    if yn('Do you want the Geekquote snarfer enabled by default?'):
        conf.supybot.plugins.Geekquote.geekSnarfer.setValue(True)

conf.registerPlugin('Geekquote')
conf.registerChannelValue(conf.supybot.plugins.Geekquote, 'geekSnarfer',
    registry.Boolean(False, """Determines whether the bot will automatically
    'snarf' Geekquote auction URLs and print information about them."""))

class Geekquote(callbacks.PrivmsgCommandAndRegexp):
    threaded = True
    regexps = ['geekSnarfer']

    def callCommand(self, method, irc, msg, *L, **kwargs):
        try:
            super(Geekquote, self).callCommand(method, irc, msg, *L, **kwargs)
        except webutils.WebError, e:
            irc.error(str(e))

    _gkREDict = {'bash.org':re.compile('<p class="qt">(?P<text>.*?)</p>', re.M | re.DOTALL),
                'qdb.us':re.compile('<a href=\"/\?\d*\">.*<p>(?P<text>.*?)</p>', re.M | re.DOTALL)}
    def _gkBackend(self, irc, msg, site, id):
        if id:
            try:
                id = int(id)
            except ValueError:
                irc.error('Invalid id: %s' % id, Raise=True)
            #id = 'quote=%s' % id
        else:
            id = 'random'
        html = webutils.getUrl('http://%s/?%s' % (site, id))
        m = self._gkREDict[site].search(html)
        if m is None:
            irc.error('No quote found on %s. %s' % (site, id))
            return
        quote = utils.htmlToText(m.group(1))
        quote = ' // '.join(quote.splitlines())
        irc.reply(quote)

    def geekSnarfer(self, irc, msg, match):
        r"http://(?:www\.)?(?P<site>bash\.org|qdb\.us)/\?(?P<id>\d+)"
        if not self.registryValue('geekSnarfer', msg.args[0]):
            return
        id = match.groupdict()['id']
        site = match.groupdict()['site']
        self.log.info('Snarfing geekquote %s from %s.' % (id, site))
        self._gkBackend(irc, msg, site, id)
    geekSnarfer = privmsgs.urlSnarfer(geekSnarfer)

    def geekquote(self, irc, msg, args):
        """[<id>]

        Returns a random geek quote from bash.org; the optional argument
        id specifies which quote to retrieve.
        """
        id = privmsgs.getArgs(args, required=0, optional=1)
        site = 'bash.org'
        self._gkBackend(irc, msg, site, id)

    def qdb(self, irc, msg, args):
        """[<id>]

        Returns a random geek quote from qdb.us; the optional argument
        id specifies which quote to retrieve.
        """
        id = privmsgs.getArgs(args, required=0, optional=1)
        site = 'qdb.us'
        self._gkBackend(irc, msg, site, id)

Class = Geekquote

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
