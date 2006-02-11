###
# Copyright (c) 2002-2004, Jeremiah Fincher
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
import xml.sax

import SOAP
import google

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

def search(log, queries, **kwargs):
    # We have to keep stats here, rather than in formatData or elsewhere,
    # because not all searching functions use formatData -- fight, lucky, etc.
    assert not isinstance(queries, basestring), 'Old code: queries is a list.'
    try:
        for (i, query) in enumerate(queries):
            if len(query.split(None, 1)) > 1:
                queries[i] = repr(query)
        proxy = conf.supybot.protocols.http.proxy()
        if proxy:
            kwargs['http_proxy'] = proxy
        query = ' '.join(queries).decode('utf-8')
        data = google.doGoogleSearch(query, **kwargs)
        searches = conf.supybot.plugins.Google.state.searches() + 1
        conf.supybot.plugins.Google.state.searches.setValue(searches)
        time = conf.supybot.plugins.Google.state.time() + data.meta.searchTime
        conf.supybot.plugins.Google.state.time.setValue(time)
        last24hours.enqueue(None)
        return data
    except socket.error, e:
        if e.args[0] == 110:
            raise callbacks.Error, 'Connection timed out to Google.com.'
        else:
            raise callbacks.Error, 'Error connecting to Google.com.'
    except SOAP.HTTPError, e:
        log.info('HTTP Error accessing Google: %s', e)
        raise callbacks.Error, 'Error connecting to Google.com.'
    except SOAP.faultType, e:
        if 'Invalid authorization key' in e.faultstring:
            raise callbacks.Error, 'Invalid Google license key.'
        elif 'Problem looking up user record' in e.faultstring:
            raise callbacks.Error, \
                  'Google seems to be having trouble looking up the user for '\
                  'your license key.  This probably isn\'t a problem on your '\
                  'side; it\'s probably a bug on Google\'s side.  It seems '\
                  'to happen intermittently.'
        else:
            log.exception('Unexpected SOAPpy error:')
            raise callbacks.Error, \
                  'Unexpected error from Google; please report this to the ' \
                  'Supybot developers.'
    except xml.sax.SAXException, e:
        log.exception('Uncaught SAX error:')
        raise callbacks.Error, 'Google returned an unparsable response.  ' \
                               'The full traceback has been logged.'
# We don't use SOAPpy anymore, apparently.
##     except SOAPpy.Error, e:
##         log.exception('Uncaught SOAP exception in Google.search:')
##         raise callbacks.Error, 'Error connecting to Google.com.'

last24hours = utils.structures.TimeoutQueue(86400)
totalTime = conf.supybot.plugins.Google.state.time()
searches = conf.supybot.plugins.Google.state.searches()

class Google(callbacks.PluginRegexp):
    threaded = True
    callBefore = ['Web']
    regexps = ['googleSnarfer', 'googleGroups']
    def __init__(self, irc):
        self.__parent = super(Google, self)
        self.__parent.__init__(irc)
        google.setLicense(self.registryValue('licenseKey'))

    def callCommand(self, command, irc, msg, *args, **kwargs):
        try:
            self.__parent.callCommand(command, irc, msg, *args, **kwargs)
        except xml.sax.SAXReaderNotAvailable, e:
            irc.error('No XML parser available.')

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

    def formatData(self, data, bold=True, max=0):
        if isinstance(data, basestring):
            return data
        t = format('Search took %.2f seconds', data.meta.searchTime)
        results = []
        if max:
            data.results = data.results[:max]
        for result in data.results:
            title = utils.web.htmlToText(result.title.encode('utf-8'))
            url = result.URL
            if title:
                if bold:
                    title = ircutils.bold(title)
                results.append(format('%s: %u', title, url))
            else:
                results.append(url)
        if not results:
            return format('No matches found. (%s)', t)
        else:
            return format('%s: %s', t, '; '.join(results))

    def lucky(self, irc, msg, args, text):
        """<search>

        Does a google search, but only returns the first result.
        """
        data = search(self.log, text)
        if data.results:
            url = data.results[0].URL
            irc.reply(url)
        else:
            irc.reply('Google found nothing.')
    lucky = wrap(lucky, [many('something')])

    def google(self, irc, msg, args, optlist, text):
        """<search> [--{language,restrict} <value>] [--{notsafe,similar}]

        Searches google.com for the given string.  As many results as can fit
        are included.  --language accepts a language abbreviation; --restrict
        restricts the results to certain classes of things; --similar tells
        Google not to filter similar results. --notsafe allows possibly
        work-unsafe results.
        """
        kwargs = {}
        if self.registryValue('safeSearch', channel=msg.args[0]):
            kwargs['safeSearch'] = 1
        lang = self.registryValue('defaultLanguage', channel=msg.args[0])
        if lang:
            kwargs['language'] = lang
        for (option, argument) in optlist:
            if option == 'notsafe':
                kwargs['safeSearch'] = False
            elif option == 'similar':
                kwargs['filter'] = False
            else:
                kwargs[option] = argument
        try:
            data = search(self.log, text, **kwargs)
        except google.NoLicenseKey, e:
            irc.error('You must have a free Google web services license key '
                      'in order to use this command.  You can get one at '
                      '<http://google.com/apis/>.  Once you have one, you can '
                      'set it with the command '
                      '"config supybot.plugins.Google.licenseKey <key>".')
            return
        bold = self.registryValue('bold', msg.args[0])
        max = self.registryValue('maximumResults', msg.args[0])
        irc.reply(self.formatData(data, bold=bold, max=max))
    google = wrap(google, [getopts({'language':'something',
                                    'restrict':'something',
                                    'notsafe':'', 'similar':''}),
                           many('something')])

    def meta(self, irc, msg, args, optlist, text):
        """<search> [--{language,restrict} <value>] [--{similar,notsafe}]

        Searches google and gives all the interesting meta information about
        the search.  See the help for the google command for a detailed
        description of the parameters.
        """
        kwargs = {'language': 'lang_en', 'safeSearch': 1}
        for option, argument in optlist:
            if option == 'notsafe':
                kwargs['safeSearch'] = False
            elif option == 'similar':
                kwargs['filter'] = False
            else:
                kwargs[option[2:]] = argument
        data = search(self.log, text, **kwargs)
        meta = data.meta
        categories = [d['fullViewableName'] for d in meta.directoryCategories]
        categories = [format('%q', s.replace('_', ' ')) for s in categories]
        s = format('Search for %q returned %s %i results in %.2f seconds.%s',
                   meta.searchQuery,
                   meta.estimateIsExact and 'exactly' or 'approximately',
                   meta.estimatedTotalResultsCount,
                   meta.searchTime,
                   categories and format('  Categories include %L.',categories))
        irc.reply(s)
    meta= wrap(meta, [getopts({'language':'something',
                               'restrict':'something',
                               'notsafe':'', 'similar':''}),
                      many('something')])

    _cacheUrlRe = re.compile('<code>([^<]+)</code>')
    def cache(self, irc, msg, args, url):
        """<url>

        Returns a link to the cached version of <url> if it is available.
        """
        html = google.doGetCachedPage(url)
        m = self._cacheUrlRe.search(html)
        if m is not None:
            url = m.group(1)
            url = utils.web.htmlToText(url)
            irc.reply(url)
        else:
            irc.error('Google seems to have no cache for that site.')
    cache = wrap(cache, ['url'])

    def fight(self, irc, msg, args):
        """<search string> <search string> [<search string> ...]

        Returns the results of each search, in order, from greatest number
        of results to least.
        """

        results = []
        for arg in args:
            data = search(self.log, [arg])
            results.append((data.meta.estimatedTotalResultsCount, arg))
        results.sort()
        results.reverse()
        if self.registryValue('bold', msg.args[0]):
            bold = ircutils.bold
        else:
            bold = repr
        s = ', '.join([format('%s: %i', bold(s), i) for (i, s) in results])
        irc.reply(s)

    def spell(self, irc, msg, args, word):
        """<word>

        Returns Google's spelling recommendation for <word>.
        """
        result = google.doSpellingSuggestion(word)
        if result:
            irc.reply(result)
        else:
            irc.reply('No spelling suggestion made.  This could mean that '
                      'the word you gave is spelled right; it could also '
                      'mean that its spelling was too whacked out even for '
                      'Google to figure out.')
    spell = wrap(spell, ['text'])

    def stats(self, irc, msg, args):
        """takes no arguments

        Returns interesting information about this Google module.  Mostly
        useful for making sure you don't go over your 1000 requests/day limit.
        """
        recent = len(last24hours)
        time = self.registryValue('state.time')
        searches = self.registryValue('state.searches')
        irc.reply(format('This google module has made %n total; '
                         '%i in the past 24 hours.  '
                         'Google has spent %.2f seconds searching for me.',
                         (searches, 'search'), recent, time))
    stats = wrap(stats)

    def googleSnarfer(self, irc, msg, match):
        r"^google\s+(.*)$"
        if not self.registryValue('searchSnarfer', msg.args[0]):
            return
        searchString = match.group(1)
        try:
            data = search(self.log, [searchString], safeSearch=1)
        except google.NoLicenseKey:
            return
        if data.results:
            url = data.results[0].URL
            irc.reply(url, prefixNick=False)
    googleSnarfer = urlSnarfer(googleSnarfer)

    _ggThread = re.compile(r'Subject: <b>([^<]+)</b>', re.I)
    _ggGroup = re.compile(r'<TITLE>Google Groups :\s*([^<]+)</TITLE>', re.I)
    _ggThreadm = re.compile(r'src="(/group[^"]+)">', re.I)
    _ggSelm = re.compile(r'selm=[^&]+', re.I)
    _threadmThread = re.compile(r'TITLE="([^"]+)">', re.I)
    _threadmGroup = re.compile(r'class=groupname[^>]+>([^<]+)<', re.I)
    def googleGroups(self, irc, msg, match):
        r"http://groups.google.[\w.]+/\S+\?(\S+)"
        if not self.registryValue('groupsSnarfer', msg.args[0]):
            return
        queries = cgi.parse_qsl(match.group(1))
        queries = [q for q in queries if q[0] in ('threadm', 'selm')]
        if not queries:
            return
        queries.append(('hl', 'en'))
        url = 'http://groups.google.com/groups?' + urllib.urlencode(queries)
        text = utils.web.getUrl(url)
        mThread = None
        mGroup = None
        if 'threadm=' in url:
            path = self._ggThreadm.search(text)
            if path is not None:
                url = 'http://groups-beta.google.com' + path.group(1)
                text = utils.web.getUrl(url)
                mThread = self._threadmThread.search(text)
                mGroup = self._threadmGroup.search(text)
        else:
            mThread = self._ggThread.search(text)
            mGroup = self._ggGroup.search(text)
        if mThread and mGroup:
            irc.reply(format('Google Groups: %s, %s',
                             mGroup.group(1), mThread.group(1)),
                      prefixNick=False)
        else:
            self.log.debug('Unable to snarf.  %s doesn\'t appear to be a '
                           'proper Google Groups page.', match.group(1))
    googleGroups = urlSnarfer(googleGroups)

    def _googleUrl(self, s):
        s = s.replace('+', '%2B')
        s = s.replace(' ', '+')
        url = r'http://google.com/search?q=' + s
        return url

    _calcRe = re.compile(r'<td nowrap><font size=\+1><b>(.*?)</b>', re.I)
    _calcSupRe = re.compile(r'<sup>(.*?)</sup>', re.I)
    _calcFontRe = re.compile(r'<font size=-2>(.*?)</font>')
    _calcTimesRe = re.compile(r'&(?:times|#215);')
    def calc(self, irc, msg, args, expr):
        """<expression>

        Uses Google's calculator to calculate the value of <expression>.
        """
        url = self._googleUrl(expr)
        html = utils.web.getUrl(url)
        match = self._calcRe.search(html)
        if match is not None:
            s = match.group(1)
            s = self._calcSupRe.sub(r'^(\1)', s)
            s = self._calcFontRe.sub(r',', s)
            s = self._calcTimesRe.sub(r'*', s)
            irc.reply(s)
        else:
            irc.reply('Google\'s calculator didn\'t come up with anything.')
    calc = wrap(calc, ['text'])

    _phoneRe = re.compile(r'Phonebook.*?<font size=-1>(.*?)<a href')
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
            irc.reply('Google\'s phonebook didn\'t come up with anything.')
    phonebook = wrap(phonebook, ['text'])


Class = Google


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
