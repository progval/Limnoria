###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2010, James Vega
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

simplejson = None

try:
    simplejson = utils.python.universalImport('json')
except ImportError:
    pass

try:
    # The 3rd party simplejson module was included in Python 2.6 and renamed to
    # json.  Unfortunately, this conflicts with the 3rd party json module.
    # Luckily, the 3rd party json module has a different interface so we test
    # to make sure we aren't using it.
    if simplejson is None or hasattr(simplejson, 'read'):
        simplejson = utils.python.universalImport('simplejson',
                                                  'local.simplejson')
except ImportError:
    raise callbacks.Error, \
            'You need Python2.6 or the simplejson module installed to use ' \
            'this plugin.  Download the module at ' \
            '<http://undefined.org/python/#simplejson>.'

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

        fd = utils.web.getUrlFd('%s?%s' % (self._gsearchUrl,
                                           urllib.urlencode(opts)),
                                headers)
        json = simplejson.load(fd)
        fd.close()
        if json['responseStatus'] != 200:
            raise callbacks.Error, _('We broke The Google!')
        return json

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
            return format(_('No matches found.'))
        else:
            return format('; '.join(results))

    @internationalizeDocstring
    def lucky(self, irc, msg, args, opts, text):
        """[--snippet] <search>

        Does a google search, but only returns the first result.
        If option --snippet is given, returns also the page text snippet.
        """
        opts = dict(opts)
        data = self.search(text, msg.args[0], {'smallsearch': True})
        if data['responseData']['results']:
            url = data['responseData']['results'][0]['unescapedUrl'].encode('utf-8')
            if opts.has_key('snippet'):
                snippet = data['responseData']['results'][0]['content'].encode('utf-8')
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
        irc.reply(self.formatData(data['responseData']['results'],
                                  bold=bold, max=max))
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

    _gtranslateUrl='http://ajax.googleapis.com/ajax/services/language/translate'
    @internationalizeDocstring
    def translate(self, irc, msg, args, fromLang, toLang, text):
        """<from-language> [to] <to-language> <text>

        Returns <text> translated from <from-language> into <to-language>.
        Beware that translating to or from languages that use multi-byte
        characters may result in some very odd results.
        """
        channel = msg.args[0]
        ref = self.registryValue('referer')
        if not ref:
            ref = 'http://%s/%s' % (dynamic.irc.server,
                                    dynamic.irc.nick)
        headers = utils.web.defaultHeaders
        headers['Referer'] = ref
        opts = {'q': text, 'v': '1.0'}
        lang = conf.supybot.plugins.Google.defaultLanguage
        if fromLang.capitalize() in lang.transLangs:
            fromLang = lang.transLangs[fromLang.capitalize()]
        elif lang.normalize('lang_'+fromLang)[5:] \
                not in lang.transLangs.values():
            irc.errorInvalid(_('from language'), fromLang,
                             format(_('Valid languages are: %L'),
                                    lang.transLangs.keys()))
        else:
            fromLang = lang.normalize('lang_'+fromLang)[5:]
        if toLang.capitalize() in lang.transLangs:
            toLang = lang.transLangs[toLang.capitalize()]
        elif lang.normalize('lang_'+toLang)[5:] \
                not in lang.transLangs.values():
            irc.errorInvalid(_('to language'), toLang,
                             format(_('Valid languages are: %L'),
                                    lang.transLangs.keys()))
        else:
            toLang = lang.normalize('lang_'+toLang)[5:]
        if fromLang == 'auto':
            fromLang = ''
        if toLang == 'auto':
            irc.error("Destination language cannot be 'auto'.")
            return
        opts['langpair'] = '%s|%s' % (fromLang, toLang)
        fd = utils.web.getUrlFd('%s?%s' % (self._gtranslateUrl,
                                           urllib.urlencode(opts)),
                                headers)
        json = simplejson.load(fd)
        fd.close()
        if json['responseStatus'] != 200:
            raise callbacks.Error, 'Google says: Response Status %s: %s.' % \
                    (json['responseStatus'], json['responseDetails'],)
        if fromLang != '':
            irc.reply(json['responseData']['translatedText'].encode('utf-8'))
        else:
            detected_language = json['responseData']['detectedSourceLanguage'].encode('utf-8')
            translation = json['responseData']['translatedText'].encode('utf-8')
            try:
                long_lang_name = [k for k,v in lang.transLangs.iteritems() if v == detected_language][0]
            except IndexError: #just in case google adds langs we don't know about
                long_lang_name = detected_language
            responsestring = "(Detected source language: %s) %s" % \
                (long_lang_name, translation)
            irc.reply(responsestring)
    translate = wrap(translate, ['something', 'to', 'something', 'text'])

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

    def _googleUrl(self, s):
        s = s.replace('+', '%2B')
        s = s.replace(' ', '+')
        url = r'http://google.com/search?q=' + s
        return url

    def _googleUrlIG(self, s):
        s = s.replace('+', '%2B')
        s = s.replace(' ', '+')
        url = r'http://www.google.com/ig/calculator?hl=en&q=' + s
        return url

    _calcRe1 = re.compile(r'<table.*class="?obcontainer"?[^>]*>(.*?)</table>', re.I)
    _calcRe2 = re.compile(r'<h\d class="?r"?[^>]*>(?:<b>)?(.*?)(?:</b>)?</h\d>', re.I | re.S)
    _calcSupRe = re.compile(r'<sup>(.*?)</sup>', re.I)
    _calcFontRe = re.compile(r'<font size=-2>(.*?)</font>')
    _calcTimesRe = re.compile(r'&(?:times|#215);')
    @internationalizeDocstring
    def calc(self, irc, msg, args, expr):
        """<expression>

        Uses Google's calculator to calculate the value of <expression>.
        """
        urlig = self._googleUrlIG(expr)
        js = utils.web.getUrl(urlig)
        # fix bad google json
        js = js.replace('lhs:','"lhs":').replace('rhs:','"rhs":').replace('error:','"error":').replace('icc:','"icc":')
        js = simplejson.loads(js)

        if js['error'] == '':
            irc.reply("%s = %s" % (js['lhs'].encode('utf8'), js['rhs'].encode('utf8'),))
            return
        
        url = self._googleUrl(expr)
        html = utils.web.getUrl(url)
        match = self._calcRe1.search(html)
        if match is None:
            match = self._calcRe2.search(html)
        if match is not None:
            s = match.group(1)
            s = self._calcSupRe.sub(r'^(\1)', s)
            s = self._calcFontRe.sub(r',', s)
            s = self._calcTimesRe.sub(r'*', s)
            s = utils.web.htmlToText(s)
            irc.reply(s)
        else:
            irc.reply(_('Google says: Error: %s.') % (js['error'],))
            irc.reply('Google\'s calculator didn\'t come up with anything.')
    calc = wrap(calc, ['text'])

    _phoneRe = re.compile(r'Phonebook.*?<font size=-1>(.*?)<a href')
    @internationalizeDocstring
    def phonebook(self, irc, msg, args, phonenumber):
        """<phone number>

        Looks <phone number> up on Google.
        """
        url = self._googleUrl(phonenumber)
        html = utils.web.getUrl(url)
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
