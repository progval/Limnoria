###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2010, James McCoy
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

import re
import cgi
import json
import time
import socket
import urllib

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class Google(callbacks.PluginRegexp):
    threaded = True
    callBefore = ['Web']
    regexps = ['googleSnarfer']

    _colorGoogles = {}
    def _getColorGoogle(self, m):
        s = m.group(1)
        ret = self._colorGoogles.get(s)
        if not ret:
            L = list(s)
            L[0] = ircutils.mircColor(L[0], 'blue')[:-1]
            L[1] = ircutils.mircColor(L[1], 'red')[:-1]
            L[2] = ircutils.mircColor(L[2], 'yellow')[:-1]
            L[3] = ircutils.mircColor(L[3], 'blue')[:-1]
            L[4] = ircutils.mircColor(L[4], 'green')[:-1]
            L[5] = ircutils.mircColor(L[5], 'red')
            ret = ''.join(L)
            self._colorGoogles[s] = ret
        return ircutils.bold(ret)

    _googleRe = re.compile(r'\b(google)\b', re.I)
    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG' and \
           self.registryValue('colorfulFilter', msg.args[0]):
            s = msg.args[1]
            s = re.sub(self._googleRe, self._getColorGoogle, s)
            msg = ircmsgs.privmsg(msg.args[0], s, msg=msg)
        return msg

    _gsearchUrl = 'http://ajax.googleapis.com/ajax/services/search/web'
    def search(self, query, channel, options={}):
        """Perform a search using Google's AJAX API.
        search("search phrase", options={})

        Valid options are:
            smallsearch - True/False (Default: False)
            filter - {active,moderate,off} (Default: "moderate")
            language - Restrict search to documents in the given language
                       (Default: "lang_en")
        """
        ref = self.registryValue('referer')
        if not ref:
            ref = 'http://%s/%s' % (dynamic.irc.server,
                                    dynamic.irc.nick)
        headers = utils.web.defaultHeaders
        headers['Referer'] = ref
        opts = {'q': query, 'v': '1.0'}
        for (k, v) in options.iteritems():
            if k == 'smallsearch':
                if v:
                    opts['rsz'] = 'small'
                else:
                    opts['rsz'] = 'large'
            elif k == 'filter':
                opts['safe'] = v
            elif k == 'language':
                opts['lr'] = v
        defLang = self.registryValue('defaultLanguage', channel)
        if 'lr' not in opts and defLang:
            opts['lr'] = defLang
        if 'safe' not in opts:
            opts['safe'] = self.registryValue('searchFilter', dynamic.channel)
        if 'rsz' not in opts:
            opts['rsz'] = 'large'

        fd = utils.web.getUrlFd('%s?%s' % (self._gsearchUrl,
                                           urllib.urlencode(opts)),
                                headers)
        resp = json.load(fd)
        fd.close()
        if resp['responseStatus'] != 200:
            raise callbacks.Error, 'We broke The Google!'
        return resp

    def formatData(self, data, bold=True, max=0):
        if isinstance(data, basestring):
            return data
        results = []
        if max:
            data = data[:max]
        for result in data:
            title = utils.web.htmlToText(result['titleNoFormatting']\
                                         .encode('utf-8'))
            url = result['unescapedUrl'].encode('utf-8')
            if title:
                if bold:
                    title = ircutils.bold(title)
                results.append(format('%s: %u', title, url))
            else:
                results.append(url)
        if not results:
            return format('No matches found.')
        else:
            return format('; '.join(results))

    def lucky(self, irc, msg, args, text):
        """<search>

        Does a google search, but only returns the first result.
        """
        data = self.search(text, msg.args[0], {'smallsearch': True})
        if data['responseData']['results']:
            url = data['responseData']['results'][0]['unescapedUrl']
            irc.reply(url.encode('utf-8'))
        else:
            irc.reply('Google found nothing.')
    lucky = wrap(lucky, ['text'])

    def google(self, irc, msg, args, optlist, text):
        """<search> [--{filter,language} <value>]

        Searches google.com for the given string.  As many results as can fit
        are included.  --language accepts a language abbreviation; --filter
        accepts a filtering level ('active', 'moderate', 'off').
        """
        if 'language' in optlist and optlist['language'].lower() not in \
           conf.supybot.plugins.Google.safesearch.validStrings:
            irc.errorInvalid('language')
        data = self.search(text, msg.args[0], dict(optlist))
        if data['responseStatus'] != 200:
            irc.reply('We broke The Google!')
            return
        bold = self.registryValue('bold', msg.args[0])
        max = self.registryValue('maximumResults', msg.args[0])
        irc.reply(self.formatData(data['responseData']['results'],
                                  bold=bold, max=max))
    google = wrap(google, [getopts({'language':'something',
                                    'filter':''}),
                           'text'])

    def cache(self, irc, msg, args, url):
        """<url>

        Returns a link to the cached version of <url> if it is available.
        """
        data = self.search(url, msg.args[0], {'smallsearch': True})
        if data['responseData']['results']:
            m = data['responseData']['results'][0]
            if m['cacheUrl']:
                url = m['cacheUrl'].encode('utf-8')
                irc.reply(url)
                return
        irc.error('Google seems to have no cache for that site.')
    cache = wrap(cache, ['url'])

    def fight(self, irc, msg, args):
        """<search string> <search string> [<search string> ...]

        Returns the results of each search, in order, from greatest number
        of results to least.
        """
        channel = msg.args[0]
        results = []
        for arg in args:
            data = self.search(arg, channel, {'smallsearch': True})
            count = data['responseData']['cursor'].get('estimatedResultCount',
                                                       0)
            results.append((int(count), arg))
        results.sort()
        results.reverse()
        if self.registryValue('bold', msg.args[0]):
            bold = ircutils.bold
        else:
            bold = repr
        s = ', '.join([format('%s: %i', bold(s), i) for (i, s) in results])
        irc.reply(s)

    def googleSnarfer(self, irc, msg, match):
        r"^google\s+(.*)$"
        if not self.registryValue('searchSnarfer', msg.args[0]):
            return
        searchString = match.group(1)
        data = self.search(searchString, msg.args[0], {'smallsearch': True})
        if data['responseData']['results']:
            url = data['responseData']['results'][0]['unescapedUrl']
            irc.reply(url.encode('utf-8'), prefixNick=False)
    googleSnarfer = urlSnarfer(googleSnarfer)

Class = Google


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
