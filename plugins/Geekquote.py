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

__revision__ = "$Id$"

import supybot

__author__ = supybot.authors.skorobeus
__contributors__ = {
    supybot.authors.skorobeus: ['geekquote snarfer', 'qdb'],
    }

import supybot.plugins as plugins

import re
import sets
import time
import getopt
import socket
import urllib
import xml.dom.minidom
from itertools import imap, ifilter

import supybot.fix as fix
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import wrap
import supybot.webutils as webutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Geekquote', True)
    output("""The Geekquote plugin has the ability to watch for geekquote
              (bash.org / qdb.us) URLs and respond to them as though the user
              had asked for the geekquote by ID""")
    if yn('Do you want the Geekquote snarfer enabled by default?'):
        conf.supybot.plugins.Geekquote.geekSnarfer.setValue(True)

conf.registerPlugin('Geekquote')
conf.registerChannelValue(conf.supybot.plugins.Geekquote, 'geekSnarfer',
    registry.Boolean(False, """Determines whether the bot will automatically
    'snarf' Geekquote URLs and print information about them."""))

class Geekquote(callbacks.PrivmsgCommandAndRegexp):
    threaded = True
    callBefore = ['URL']
    regexps = ['geekSnarfer']

    def __init__(self):
        self.__parent = super(Geekquote, self)
        self.__parent.__init__()
        self.maxqdbPages = 403
        self.lastqdbRandomTime = 0
        self.randomData = {'qdb.us':[],
                            'bash.org':[]
                            }

    def callCommand(self, method, irc, msg, *L, **kwargs):
        try:
            super(Geekquote, self).callCommand(method, irc, msg, *L, **kwargs)
        except webutils.WebError, e:
            irc.error(str(e))

    _joiner = ' // '
    _qdbReString = r'<tr><td bgcolor="#(?:ffffff|e8e8e8)"><a href="/\d*?">'\
                    r'#\d*?</a>.*?<p>(?P<text>.*?)</p></td></tr>'
    _gkREDict = {'bash.org':re.compile(r'<p class="qt">(?P<text>.*?)</p>',
                    re.M | re.DOTALL),
                'qdb.us':re.compile(_qdbReString, re.M | re.DOTALL)}
    def _gkBackend(self, irc, msg, site, id):
        if id:
            try:
                id = int(id)
            except ValueError:
                irc.error('Invalid id: %s' % id, Raise=True)
            #id = 'quote=%s' % id
        else:
            id = 'random'
        fetchData = True
        quote = ''
        if id == 'random':
            timeRemaining = int(time.time()) - self.lastqdbRandomTime
            if self.randomData[site]:
                quote = self.randomData[site].pop()
            else:
                if (site == 'qdb.us' and
                            int(time.time()) - self.lastqdbRandomTime <= 90):
                    id = 'browse=%s' % fix.choice(range(self.maxqdbPages))
                quote = self._gkFetchData(site, id, random=True)
        else:
            quote = self._gkFetchData(site, id)
        irc.replies(quote.split(self._joiner), joiner=self._joiner)

    def _gkFetchData(self, site, id, random=False):
        html = ''
        try:
            html = webutils.getUrl('http://%s/?%s' % (site, id))
        except webutils.WebError, e:
            self.log.info('%s server returned the error: %s' % \
                    (site, webutils.strError(e)))
        for item in self._gkREDict[site].finditer(html):
            s = item.groupdict()['text']
            s = self._joiner.join(s.splitlines())
            s = utils.htmlToText(s)
            if random and s:
                if s not in self.randomData[site]:
                    self.randomData[site].append(s)
            else:
                break
        if not s:
            return 'Could not find a quote for id %s.' % id
        else:
            if random:
                # To make sure and remove the first quote from the list so it
                self.randomData[site].pop()
            return s

    def geekSnarfer(self, irc, msg, match):
        r'http://(?:www\.)?(?P<site>bash\.org|qdb\.us)/\?(?P<id>\d+)'
        if not self.registryValue('geekSnarfer', msg.args[0]):
            return
        id = match.groupdict()['id']
        site = match.groupdict()['site']
        self.log.info('Snarfing geekquote %s from %s.' % (id, site))
        self._gkBackend(irc, msg, site, id)
    geekSnarfer = wrap(geekSnarfer, decorators=['urlSnarfer'])

    def geekquote(self, irc, msg, args):
        """[<id>]

        Returns a random geek quote from bash.org; the optional argument
        <id> specifies which quote to retrieve.
        """
        id = privmsgs.getArgs(args, required=0, optional=1)
        site = 'bash.org'
        self._gkBackend(irc, msg, site, id)

    def qdb(self, irc, msg, args):
        """[<id>]

        Returns a random geek quote from qdb.us; the optional argument
        <id> specifies which quote to retrieve.
        """
        id = privmsgs.getArgs(args, required=0, optional=1)
        site = 'qdb.us'
        self._gkBackend(irc, msg, site, id)

Class = Geekquote

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
