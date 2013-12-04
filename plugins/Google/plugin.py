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
import sys
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
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Google')

import json

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
    @internationalizeDocstring
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

        text = utils.web.getUrl('%s?%s' % (self._gsearchUrl,
                                           urllib.urlencode(opts)),
                                headers=headers).decode('utf8')
        data = json.loads(text)
        if data['responseStatus'] != 200:
            raise callbacks.Error, _('We broke The Google!')
        return data

    def formatData(self, data, bold=True, max=0, onetoone=False):
        if isinstance(data, basestring):
            return data
        results = []
        if max:
            data = data[:max]
        for result in data:
            title = utils.web.htmlToText(result['titleNoFormatting']\
                                         .encode('utf-8'))
            url = result['unescapedUrl']
            if sys.version_info[0] < 3:
                url = url.encode('utf-8')
            if title:
                if bold:
                    title = ircutils.bold(title)
                results.append(format('%s: %u', title, url))
            else:
                results.append(url)
        if sys.version_info[0] < 3:
            repl = lambda x:x if isinstance(x, unicode) else unicode(x, 'utf8')
            results = map(repl, results)
        if not results:
            return [_('No matches found.')]
        elif onetoone:
            return results
        else:
            return [u'; '.join(results)]

    @internationalizeDocstring
    def lucky(self, irc, msg, args, opts, text):
        """[--snippet] <search>

        Does a google search, but only returns the first result.
        If option --snippet is given, returns also the page text snippet.
        """
        opts = dict(opts)
        data = self.search(text, msg.args[0], {'smallsearch': True})
        if data['responseData']['results']:
            url = data['responseData']['results'][0]['unescapedUrl']
            if opts.has_key('snippet'):
                snippet = data['responseData']['results'][0]['content']
                snippet = " | " + utils.web.htmlToText(snippet, tagReplace='')
            else:
                snippet = ""
            result = url + snippet
            irc.reply(result)
        else:
            irc.reply(_('Google found nothing.'))
    lucky = wrap(lucky, [getopts({'snippet':'',}), 'text'])

    @internationalizeDocstring
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
            irc.reply(_('We broke The Google!'))
            return
        bold = self.registryValue('bold', msg.args[0])
        max = self.registryValue('maximumResults', msg.args[0])
        # We don't use supybot.reply.oneToOne here, because you generally
        # do not want @google to echo ~20 lines of results, even if you
        # have reply.oneToOne enabled.
        onetoone = self.registryValue('oneToOne', msg.args[0])
        for result in self.formatData(data['responseData']['results'],
                                  bold=bold, max=max, onetoone=onetoone):
            irc.reply(result)
    google = wrap(google, [getopts({'language':'something',
                                    'filter':''}),
                           'text'])

    @internationalizeDocstring
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
        irc.error(_('Google seems to have no cache for that site.'))
    cache = wrap(cache, ['url'])

    @internationalizeDocstring
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

    @internationalizeDocstring
    def translate(self, irc, msg, args, sourceLang, targetLang, text):
        """<source language> [to] <target language> <text>

        Returns <text> translated from <source language> into <target
        language>.
        """

        channel = msg.args[0]

        headers = utils.web.defaultHeaders
        headers['User-Agent'] = ('Mozilla/5.0 (X11; U; Linux i686) '
                                 'Gecko/20071127 Firefox/2.0.0.11')

        sourceLang = urllib.quote(sourceLang)
        targetLang = urllib.quote(targetLang)

        text = urllib.quote(text)

        result = utils.web.getUrlFd('http://translate.google.com/translate_a/t'
                                    '?client=t&hl=en&sl=%s&tl=%s&multires=1'
                                    '&otf=1&ssel=0&tsel=0&uptl=en&sc=1&text='
                                    '%s' % (sourceLang, targetLang, text),
                                    headers).read().decode('utf8')

        while ',,' in result:
            result = result.replace(',,', ',null,')
        while '[,' in result:
            result = result.replace('[,', '[')
        data = json.loads(result)

        try:
            language = data[2]
        except:
            language = 'unknown'

        irc.reply(''.join(x[0] for x in data[0]), language)
    translate = wrap(translate, ['something', 'to', 'something', 'text'])

    def googleSnarfer(self, irc, msg, match):
        r"^google\s+(.*)$"
        if not self.registryValue('searchSnarfer', msg.args[0]):
            return
        searchString = match.group(1)
        data = self.search(searchString, msg.args[0], {'smallsearch': True})
        if data['responseData']['results']:
            url = data['responseData']['results'][0]['unescapedUrl']
            irc.reply(url, prefixNick=False)
    googleSnarfer = urlSnarfer(googleSnarfer)

    def _googleUrl(self, s, channel):
        s = urllib.quote_plus(s)
        url = r'http://%s/search?q=%s' % \
                (self.registryValue('baseUrl', channel), s)
        return url

    def _googleUrlIG(self, s, channel):
        s = urllib.quote_plus(s)
        url = r'http://%s/ig/calculator?hl=en&q=%s' % \
                (self.registryValue('baseUrl', channel), s)
        return url

    _calcRe1 = re.compile(r'<span class="cwcot".*?>(.*?)</span>', re.I)
    _calcRe2 = re.compile(r'<div class="vk_ans.*?>(.*?)</div>', re.I | re.S)
    _calcRe3 = re.compile(r'<div class="side_div" id="rhs_div">.*?<input class="ucw_data".*?value="(.*?)"', re.I)
    @internationalizeDocstring
    def calc(self, irc, msg, args, expr):
        """<expression>

        Uses Google's calculator to calculate the value of <expression>.
        """
        channel = msg.args[0]
        if not ircutils.isChannel(channel):
            channel = None
        urlig = self._googleUrlIG(expr, channel)
        h = {"User-Agent":"Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36"}
        html = utils.web.getUrl(urlig, headers=h).decode('utf8')
        match = self._calcRe1.search(html)
        if not match:
            match = self._calcRe2.search(html)
            if not match:
                match = self._calcRe3.search(html)
                if not match:
                    irc.reply("I could not find an output from Google Calc for: %s" % expr)
                    self.log.info("HTML: {0}".format(html))
                    return
                else:
                    s = match.group(1)
            else:
                s = match.group(1)
        else:
            s = match.group(1)
        # do some cleanup of text
        s = re.sub(r'<sup>(.*)</sup>&#8260;<sub>(.*)</sub>', r' \1/\2', s)
        s = re.sub(r'<sup>(.*)</sup>', r'^\1', s)
        s = utils.web.htmlToText(s)
        irc.reply("%s = %s" % (expr, s))
    calc = wrap(calc, ['text'])

    _phoneRe = re.compile(r'Phonebook.*?<font size=-1>(.*?)<a href')
    @internationalizeDocstring
    def phonebook(self, irc, msg, args, phonenumber):
        """<phone number>

        Looks <phone number> up on Google.
        """
        channel = msg.args[0]
        if not ircutils.isChannel(channel):
            channel = None
        url = self._googleUrl(phonenumber, channel)
        html = utils.web.getUrl(url).decode('utf8')
        m = self._phoneRe.search(html)
        if m is not None:
            s = m.group(1)
            s = s.replace('<b>', '')
            s = s.replace('</b>', '')
            s = utils.web.htmlToText(s)
            irc.reply(s)
        else:
            irc.reply(_('Google\'s phonebook didn\'t come up with anything.'))
    phonebook = wrap(phonebook, ['text'])


Class = Google


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
