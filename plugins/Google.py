#!/usr/bin/env python

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

"""
Accesses Google for various things.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import re
import sets
import time
import getopt
import socket
import xml.sax

import SOAP
import google

import supybot.registry as registry

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.webutils as webutils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks
import supybot.structures as structures

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    output('To use Google\'t Web Services, you must have a license key.')
    if yn('Do you have a license key?'):
        key = something('What is it?')
        while len(key) != 32:
            output('That\'s not a valid Google license key.')
            if yn('Are you sure you have a valid Google license key?'):
                key = something('What is it?')
            else:
                key = ''
                break
        if key:
            conf.registerPlugin('Google', True)
            conf.supybot.plugins.Google.licenseKey.setValue(key)
        output("""The Google plugin has the functionality to watch for URLs
                  that match a specific pattern. (We call this a snarfer)
                  When supybot sees such a URL, it will parse the web page
                  for information and reply with the results.

                  Google has two available snarfers: Google Groups link
                  snarfing and a google search snarfer.""")
        if yn('Do you want the Google Groups link snarfer enabled by '
            'default?'):
            conf.supybot.plugins.Google.groupsSnarfer.setValue(True)
        if yn('Do you want the Google search snarfer enabled by default?'):
            conf.supybot.plugins.Google.searchSnarfer.setValue(True)
    else:
        output("""You'll need to get a key before you can use this plugin.
                  You can apply for a key at http://www.google.com/apis/""")


totalSearches = 0
totalTime = 0
last24hours = structures.queue()

def search(log, queries, **kwargs):
    assert not isinstance(queries, basestring), 'Old code: queries is a list.'
    try:
        global totalSearches, totalTime, last24hours
        for (i, query) in enumerate(queries):
            if len(query.split(None, 1)) > 1:
                queries[i] = repr(query)
        proxy = conf.supybot.protocols.http.proxy()
        if proxy:
            kwargs['http_proxy'] = proxy
        data = google.doGoogleSearch(' '.join(queries), **kwargs)
        now = time.time()
        totalSearches += 1
        totalTime += data.meta.searchTime
        last24hours.enqueue(now)
        while last24hours and now - last24hours.peek() > 86400:
            last24hours.dequeue()
        return data
    except socket.error, e:
        if e.args[0] == 110:
            raise callbacks.Error, 'Connection timed out to Google.com.'
        else:
            raise callbacks.Error, 'Error connecting to Google.com.'
    except SOAP.HTTPError, e:
        log.warning('HTTP Error accessing Google: %s', e)
        raise callbacks.Error, 'Error connecting to Google.com.'
    except SOAP.faultType, e:
        log.exception('Uncaught SOAP error:')
        raise callbacks.Error, 'Invalid Google license key.'
    except xml.sax.SAXException, e:
        log.exception('Uncaught SAX error:')
        raise callbacks.Error, 'Google returned an unparsable response.  ' \
                               'The full traceback has been logged.'
    except SOAP.Error, e:
        log.exception('Uncaught SOAP exception in Google.search:')
        raise callbacks.Error, 'Error connecting to Google.com.'

class LicenseKey(registry.String):
    def setValue(self, s):
        if s and len(s) != 32:
            raise registry.InvalidRegistryValue, 'Invalid Google license key.'
        if s:
            registry.String.setValue(self, s)
            google.setLicense(self.value)
        if not s:
            registry.String.setValue(self, '')
            google.setLicense(self.value)

class Language(registry.OnlySomeStrings):
    validStrings = ['lang_' + s for s in 'ar zh-CN zh-TW cs da nl en et fi fr '
                                         'de el iw hu is it ja ko lv lt no pt '
                                         'pl ro ru es sv tr'.split()]
    validStrings.append('')
    def normalize(self, s):
        if not s.startswith('lang_'):
            s = 'lang_' + s
        if not s.endswith('CN') or s.endswith('TW'):
            s = s.lower()
        else:
            s = s.lower()[:-2] + s[-2:]
        return s

conf.registerPlugin('Google')
conf.registerChannelValue(conf.supybot.plugins.Google, 'groupsSnarfer',
    registry.Boolean(False, """Determines whether the groups snarfer is
    enabled.  If so, URLs at groups.google.com will be snarfed and their
    group/title messaged to the channel."""))
conf.registerChannelValue(conf.supybot.plugins.Google, 'searchSnarfer',
    registry.Boolean(False, """Determines whether the search snarfer is
    enabled.  If so, messages (even unaddressed ones) beginning with the word
    'google' will result in the first URL Google returns being sent to the
    channel."""))
conf.registerChannelValue(conf.supybot.plugins.Google, 'bold',
    registry.Boolean(True, """Determines whether results are bolded."""))
conf.registerChannelValue(conf.supybot.plugins.Google, 'maximumResults',
    registry.PositiveInteger(10, """Determines the maximum number of results
    returned from the google command."""))
conf.registerChannelValue(conf.supybot.plugins.Google, 'defaultLanguage',
    Language('lang_en', """Determines what default language is used in
    searches.  If left empty, no specific language will be requested."""))
conf.registerChannelValue(conf.supybot.plugins.Google, 'safeSearch',
    registry.Boolean(True, "Determines whether safeSearch is on by default."))
conf.registerGlobalValue(conf.supybot.plugins.Google, 'licenseKey',
    LicenseKey('', """Sets the Google license key for using Google's Web
    Services API.  This is necessary before you can do any searching with this
    module.""", private=True))

conf.registerGroup(conf.supybot.plugins.Google, 'state')
conf.registerGlobalValue(conf.supybot.plugins.Google.state, 'searches',
    registry.Float(0.0, """Used to keep the total number of searches Google has
    done for this bot.  You shouldn't modify this."""))
conf.registerGlobalValue(conf.supybot.plugins.Google.state, 'time',
    registry.Float(0.0, """Used to keep the total amount of time Google has
    spent searching for this bot.  You shouldn't modify this."""))

class Google(callbacks.PrivmsgCommandAndRegexp):
    threaded = True
    regexps = sets.Set(['googleSnarfer', 'googleGroups'])
    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.total = 0
        self.totalTime = 0
        self.last24hours = structures.queue()

    def formatData(self, data, bold=True, max=0):
        if isinstance(data, basestring):
            return data
        time = 'Search took %s seconds' % data.meta.searchTime
        results = []
        if max:
            data.results = data.results[:max]
        for result in data.results:
            title = utils.htmlToText(result.title.encode('utf-8'))
            url = result.URL
            if title:
                if bold:
                    title = ircutils.bold(title)
                results.append('%s: <%s>' % (title, url))
            else:
                results.append(url)
        if not results:
            return 'No matches found (%s)' % time
        else:
            return '%s: %s' % (time, '; '.join(results))

    def lucky(self, irc, msg, args):
        """<search>

        Does a google search, but only returns the first result.
        """
        if not args:
            raise callbacks.ArgumentError
        data = search(self.log, args)
        if data.results:
            url = data.results[0].URL
            irc.reply(url)
        else:
            irc.reply('Google found nothing.')

    def google(self, irc, msg, args):
        """<search> [--{language,restrict}=<value>] [--{notsafe,similar}]

        Searches google.com for the given string.  As many results as can fit
        are included.  --language accepts a language abbreviation; --restrict
        restricts the results to certain classes of things; --similar tells
        Google not to filter similar results. --notsafe allows possibly
        work-unsafe results.
        """
        (optlist, rest) = getopt.getopt(args, '', ['language=', 'restrict=',
                                                   'notsafe', 'similar'])
        kwargs = {}
        if self.registryValue('safeSearch', channel=msg.args[0]):
            kwargs['safeSearch'] = 1
        lang = self.registryValue('defaultLanguage', channel=msg.args[0])
        if lang:
            kwargs['language'] = lang
        for (option, argument) in optlist:
            if option == '--notsafe':
                kwargs['safeSearch'] = False
            elif option == '--similar':
                kwargs['filter'] = False
            else:
                kwargs[option[2:]] = argument
        if not rest:
            raise callbacks.ArgumentError
        try:
            data = search(self.log, rest, **kwargs)
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

    def metagoogle(self, irc, msg, args):
        """<search> [--(language,restrict)=<value>] [--{similar,notsafe}]

        Searches google and gives all the interesting meta information about
        the search.  See the help for the google command for a detailed
        description of the parameters.
        """
        (optlist, rest) = getopt.getopt(args, '', ['language=', 'restrict=',
                                                   'notsafe', 'similar'])
        kwargs = {'language': 'lang_en', 'safeSearch': 1}
        for option, argument in optlist:
            if option == '--notsafe':
                kwargs['safeSearch'] = False
            elif option == '--similar':
                kwargs['filter'] = False
            else:
                kwargs[option[2:]] = argument
        data = search(self.log, rest, **kwargs)
        meta = data.meta
        categories = [d['fullViewableName'] for d in meta.directoryCategories]
        categories = [utils.dqrepr(s.replace('_', ' ')) for s in categories]
        if categories:
            categories = utils.commaAndify(categories)
        else:
            categories = ''
        s = 'Search for %r returned %s %s results in %s seconds.%s' % \
            (meta.searchQuery,
             meta.estimateIsExact and 'exactly' or 'approximately',
             meta.estimatedTotalResultsCount,
             meta.searchTime,
             categories and '  Categories include %s.' % categories)
        irc.reply(s)

    _cacheUrlRe = re.compile('<code>([^<]+)</code>')
    def cache(self, irc, msg, args):
        """<url>

        Returns a link to the cached version of <url> if it is available.
        """
        url = privmsgs.getArgs(args)
        html = google.doGetCachedPage(url)
        m = self._cacheUrlRe.search(html)
        if m is not None:
            url = m.group(1)
            url = utils.htmlToText(url)
            irc.reply(url)
        else:
            irc.error('Google seems to have no cache for that site.')

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
        s = ', '.join(['%r: %s' % (s, i) for (i, s) in results])
        irc.reply(s)

    def spell(self, irc, msg, args):
        """<word>

        Returns Google's spelling recommendation for <word>.
        """
        word = privmsgs.getArgs(args)
        result = google.doSpellingSuggestion(word)
        if result:
            irc.reply(result)
        else:
            irc.reply('No spelling suggestion made.  This could mean that '
                      'the word you gave is spelled right; it could also '
                      'mean that its spelling was too whacked out even for '
                      'Google to figure out.')

    def info(self, irc, msg, args):
        """takes no arguments

        Returns interesting information about this Google module.  Mostly
        useful for making sure you don't go over your 1000 requests/day limit.
        """
        recent = len(last24hours)
        irc.reply('This google module has been called %s total; '
                       '%s in the past 24 hours.  '
                       'Google has spent %s seconds searching for me.' %
                  (utils.nItems('time', totalSearches),
                   utils.nItems('time', recent), totalTime))

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
            irc.reply(url, prefixName=False)
    googleSnarfer = privmsgs.urlSnarfer(googleSnarfer)

    _ggThread = re.compile(r'<br>Subject: ([^<]+)<br>', re.I)
    _ggGroup = re.compile(r'Newsgroups: (?:<a[^>]+>)?([^<]+)(?:</a>)?', re.I)
    _ggThreadm = re.compile(r'view the <a href=([^>]+)>no', re.I)
    _ggSelm = re.compile(r'selm=[^&]+', re.I)
    def googleGroups(self, irc, msg, match):
        r"http://groups.google.com/[^\s]+"
        if not self.registryValue('groupsSnarfer', msg.args[0]):
            return
        url = match.group(0)
        text = webutils.getUrl(url)
        mThread = None
        mGroup = None
        if 'threadm=' in url:
            path = self._ggThreadm.search(text)
            if path is None:
                return
            url = 'http://groups.google.com%s' % path.group(1)
            text = webutils.getUrl(url)
        elif 'selm=' in url:
            path = self._ggSelm.search(url)
            if path is None:
                return
            url = 'http://groups.google.com/groups?%s' % path.group(0)
            text = webutils.getUrl(url)
        mThread = self._ggThread.search(text)
        mGroup = self._ggGroup.search(text)
        if mThread and mGroup:
            irc.reply('Google Groups: %s, %s' % (mGroup.group(1),
                      mThread.group(1)), prefixName=False)
        else:
            irc.errorPossibleBug('That doesn\'t appear to be a proper '
                                 'Google Groups page.')
    googleGroups = privmsgs.urlSnarfer(googleGroups)

    _calcRe = re.compile(r'<td nowrap><font size=\+1><b>(.*?)</b>', re.I)
    _calcSupRe = re.compile(r'<sup>(.*?)</sup>', re.I)
    _calcFontRe = re.compile(r'<font size=-2>(.*?)</font>')
    _calcTimesRe = re.compile(r'&times;')
    def calc(self, irc, msg, args):
        """<expression>

        Uses Google's calculator to calculate the value of <expression>.
        """
        expr = privmsgs.getArgs(args)
        expr = expr.replace('+', '%2B')
        expr = expr.replace(' ', '+')
        url = r'http://google.com/search?q=%s' % expr
        html = webutils.getUrl(url)
        match = self._calcRe.search(html)
        if match is not None:
            s = match.group(1)
            s = self._calcSupRe.sub(r'^(\1)', s)
            s = self._calcFontRe.sub(r',', s)
            s = self._calcTimesRe.sub(r'*', s)
            irc.reply(s)
        else:
            irc.reply('Google\'s calculator didn\'t come up with anything.')
        


Class = Google


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
