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
Provides several commands that go out to websites and get things.
"""

from baseplugin import *

import re
import sets
import time
import random
import urllib
import urllib2

import babelfish

import utils
import debug
import privmsgs
import callbacks
import structures

class FreshmeatException(Exception):
    pass

class Http(callbacks.Privmsg):
    threaded = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.deepthoughtq = structures.queue()
        self.deepthoughts = sets.Set()

    def deepthought(self, irc, msg, args):
        """takes no arguments

        Returns a Deep Thought by Jack Handey.
        """
        url = 'http://www.tremorseven.com/aim/deepaim.php?job=view'
        thought = ' ' * 512
        now = time.time()
        while self.deepthoughtq and now - self.deepthoughtq[0][0] > 86400:
            s = self.deepthoughtq.dequeue()[1]
            self.deepthoughts.remove(s)
        while len(thought) > 430 or thought in self.deepthoughts:
            fd = urllib2.urlopen(url)
            s = fd.read()
            thought = s.split('<br>')[2]
            thought = ' '.join(thought.split())
        self.deepthoughtq.enqueue((now, thought))
        self.deepthoughts.add(thought)
        irc.reply(msg, thought)

    _titleRe = re.compile(r'<title>(.*)</title>', re.I)
    def title(self, irc, msg, args):
        """<url>

        Returns the HTML <title>...</title> of a URL.
        """
        url = privmsgs.getArgs(args)
        if '://' not in url:
            url = 'http://%s' % url
        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            m = self._titleRe.search(text)
            if m is not None:
                irc.reply(msg, m.group(1))
            else:
                irc.reply(msg, 'That URL appears to have no HTML title.')
        except ValueError, e:
            irc.error(msg, str(e))
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

    _fmProject = re.compile('<projectname_full>([^<]+)</projectname_full>')
    _fmVersion = re.compile('<latest_version>([^<]+)</latest_version>')
    _fmVitality = re.compile('<vitality_percent>([^<]+)</vitality_percent>')
    _fmPopular=re.compile('<popularity_percent>([^<]+)</popularity_percent>')
    _fmLastUpdated = re.compile('<date_updated>([^<]+)</date_updated>')
    def freshmeat(self, irc, msg, args):
        """<project name>

        Returns Freshmeat data about a given project.
        """
        project = privmsgs.getArgs(args)
        url = 'http://www.freshmeat.net/projects-xml/%s' % project
        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            fd.close()
            if text.startswith('Error'):
                raise FreshmeatException, text
            project = self._fmProject.search(text).group(1)
            version = self._fmVersion.search(text).group(1)
            vitality = self._fmVitality.search(text).group(1)
            popularity = self._fmPopular.search(text).group(1)
            lastupdated = self._fmLastUpdated.search(text).group(1)
            irc.reply(msg,
              '%s, last updated %s, with a vitality percent of %s '\
              'and a popularity of %s, is in version %s.' % \
              (project, lastupdated, vitality, popularity, version))
        except FreshmeatException, e:
            irc.error(msg, debug.exnToString(e))
        except Exception, e:
            debug.recoverableException()
            irc.error(msg, debug.exnToString(e))

    def stockquote(self, irc, msg, args):
        """<company symbol>

        Gets the information about the current price and change from the
        previous day of a given compny (represented by a stock symbol).
        """
        symbol = privmsgs.getArgs(args)
        url = 'http://finance.yahoo.com/d/quotes.csv?s=%s'\
              '&f=sl1d1t1c1ohgv&e=.csv' % symbol
        try:
            fd = urllib2.urlopen(url)
            quote = fd.read()
            fd.close()
        except Exception, e:
            irc.error(msg, debug.exnToString(e))
            return
        data = quote.split(',')
        #debug.printf(data) # debugging
        if data[1] != '0.00':
            irc.reply(msg,
                       'The current price of %s is %s, as of %s EST.  '\
                       'A change of %s from the last business day.' %\
                       (data[0][1:-1], data[1], data[3][1:-1], data[4]))
            return
        else:
            m = 'I couldn\'t find a listing for %s' % symbol
            irc.error(msg, m)
            return

    def foldoc(self, irc, msg, args):
        """<something to lookup on foldoc>

        FOLDOC is a searchable dictionary of acryonyms, jargon, programming
        languages, tools, architecture, operating systems, networking, theory,
        conventions, standards, methamatics, telecoms, electronics, history,
        in fact anything having to do with computing.  This commands searches
        that dictionary.
        """
        if not args:
            raise callbacks.ArgumentError
        search = '+'.join([urllib.quote(arg) for arg in args])
        url = 'http://foldoc.doc.ic.ac.uk/foldoc/foldoc.cgi?query=%s' % search
        try:
            fd = urllib2.urlopen(url)
            html = fd.read()
            fd.close()
        except Exception, e:
            irc.error(msg, debug.exnToString(e))
            return
        text = html.split('<P>\n', 2)[1]
        text = text.replace('.\n', '.  ')
        text = text.replace('\n', ' ')
        text = utils.htmlToText(text)
        text = text.strip()
        if text:
            irc.reply(msg, text)
        else:
            search = urllib.unquote(search)
            s = 'There appears to be no definition for %s.' % search
            irc.reply(msg, s)


    _cityregex = re.compile(
        r'<td><font size="4" face="arial"><b>'\
        r'(.*?), (.*?),(.*?)</b></font></td>', re.IGNORECASE)
    _interregex = re.compile(
        r'<td><font size="4" face="arial"><b>'\
        r'(.*?), (.*?)</b></font></td>', re.IGNORECASE)
    _condregex = re.compile(
        r'<td width="100%" colspan="2" align="center"><strong>'\
        r'<font face="arial">(.*?)</font></strong></td>', re.IGNORECASE)
    _tempregex = re.compile(
        r'<td valign="top" align="right"><strong><font face="arial">'\
        r'(.*?)</font></strong></td>', re.IGNORECASE)
    def weather2(self, irc, msg, args):
        """<US zip code> <US/Canada city, state> <Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """
        zip = privmsgs.getArgs(args)
        zip = zip.replace(',','')  
        zip = zip.lower().split()
        
        #If we received more than one argument, then we have received
        #a city and state argument that we need to process.
        if len(zip) > 1:
            #If we received more than 1 argument, then we got a city with a
            #multi-word name.  ie ['Garden', 'City', 'KS'] instead of
            #['Liberal', 'KS'].  We join it together with a + to pass
            #to our query
            if len(zip) > 2:
                city = '+'.join(zip[:-1])
                isState = zip[-1]
            else:
                city = zip[0]
                isState = zip[1]
            
            #We must break the States up into two sections.  The US and
            #Canada are the only countries that require a State argument.
            
            #United States
            realStates = sets.Set(['ak', 'al', 'ar', 'ca', 'co', 'ct', 'dc',
                        'de', 'fl', 'ga', 'hi', 'ia', 'id', 'il',
                        'in', 'ks', 'ky', 'la', 'ma', 'md', 'me',
                        'mi', 'mn', 'mo', 'ms', 'mt', 'nc', 'nd',
                        'ne', 'nh', 'nj', 'nm', 'nv', 'ny', 'oh',
                        'ok', 'or', 'pa', 'ri', 'sc', 'sd', 'tn',
                        'tx', 'ut', 'va', 'vt', 'wa', 'wi', 'wv',
                        'wy'])
            #Canadian provinces.  (Province being a metric State measurement
            #mind you. :D)
            fakeStates = sets.Set(['ab', 'bc', 'mb', 'nb', 'nf', 'ns', 'nt',
                        'nu', 'on', 'pe', 'qc', 'sk', 'yk'])
            
            if isState in realStates:
                state = isState
                country = 'us'
            elif isState in fakeStates:
                state = isState
                country = 'ca'
            else:
                state = ''
                country = isState
            
            #debug.printf('State: %s' % (state,))
            #debug.printf('Country: %s' % (country,))
            
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?'\
                    'pass=&dpp=&forecast=zandh&config=&'\
                    'place=%s&state=%s&country=%s' % \
                                (city, state, country)

        #We received a single argument.  Zipcode or station id.
        else:
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?'\
                    'config=&forecast=zandh&pands=%s&Submit=GO' % (zip[0],)

        #debug.printf(url)
        try:
            fd = urllib2.urlopen(url)
            html = fd.read()
            fd.close()
            
            headData = self._cityregex.search(html)
            if headData:
                (city, state, country) = headData.groups()
            else:
                headData = self._interregex.search(html)
                (city, state) = headData.groups()
                
            temp = self._tempregex.search(html).group(1)
            conds = self._condregex.search(html).group(1)
            
            if temp and conds and city and state:
                irc.reply(msg, 'The current temperature in %s, %s is %s'\
                  ' with %s conditions.' % (city.strip(), state.strip(),
                                            temp, conds))
            else:
                irc.error(msg, 'the format of the page was odd.')
                
        except urllib2.URLError:
            irc.error(msg, 'Couldn\'t open the search page.')
        except:
            irc.error(msg, 'the format of the page was odd.')

    _tempregex = re.compile('CLASS=obsTempTextA>(\d+)&deg;F</b></td>',\
                         re.IGNORECASE)
    _cityregex = re.compile(r'Local Forecast for (.*), (.*?) ')
    _condregex = re.compile('CLASS=obsInfo2><b CLASS=obsTextA>(.*)</b></td>',\
                         re.IGNORECASE)
    def weather(self, irc, msg, args):
        """<US zip code>

        Returns the approximate weather conditions at a given US Zip code.
        """
        zip = privmsgs.getArgs(args)
        url = "http://www.weather.com/weather/local/%s?lswe=%s" % (zip, zip)
        try:
            html = urllib2.urlopen(url).read()
            city, state = self._cityregex.search(html).groups()
            temp = self._tempregex.search(html).group(1)
            conds = self._condregex.search(html).group(1)
            irc.reply(msg, 'The current temperature in %s, %s is %dF with %s'\
                           ' conditions' % (city, state, int(temp), conds))
        except AttributeError:
            irc.error(msg, 'the format of the page was odd.')
        except urllib2.URLError:
            irc.error(msg, 'Couldn\'t open the search page.')

    _geekquotere = re.compile('<p class="qt">(.*?)</p>')
    def geekquote(self, irc, msg, args):
        """[<multiline>]

        Returns a random geek quote from bash.org; the optional argument
        <multiline> specifies whether multi-line quotes (which are longer
        than other quotes, generally) are to be allowed.
        """
        multiline = privmsgs.getArgs(args, needed=0, optional=1)
        try:
            fd = urllib2.urlopen('http://bash.org/?random1')
        except urllib2.URLError:
            irc.error(msg, 'Error connecting to geekquote server.')
            return
        html = fd.read()
        fd.close()
        if multiline:
            m = self._geekquotere.search(html, re.M)
        else:
            m = self._geekquotere.search(html)
        if m is None:
            irc.error(msg, 'No quote found.')
            return
        quote = utils.htmlToText(m.group(1))
        quote = ' // '.join(quote.splitlines())
        irc.reply(msg, quote)

    _acronymre = re.compile(r'<td[^w]+width="70[^>]+>(?:<b>)?([^<]+)(?:</b>)?')
    def acronym(self, irc, msg, args):
        """<acronym>

        Displays acronym matches from acronymfinder.com
        """
        acronym = privmsgs.getArgs(args)
        try:
            url = 'http://www.acronymfinder.com/' \
                  'af-query.asp?String=exact&Acronym=%s' % acronym
            request = urllib2.Request(url, headers={'User-agent':
              'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 4.0)'})
            fd = urllib2.urlopen(request)
        except urllib2.URLError:
            irc.error(msg, 'Couldn\'t connect to acronymfinder.com')
            return
        html = fd.read()
        fd.close()
        # The following definitions are stripped and empties are removed.
        defs = filter(None, map(str.strip, self._acronymre.findall(html)))
        debug.printf(defs)
        if len(defs) == 0:
            irc.reply(msg, 'No definitions found.')
        else:
            s = ircutils.privmsgPayload(defs, ', or ')
            irc.reply(msg, '%s could be %s' % (acronym, s))

    _netcraftre = re.compile(r'whatos text -->(.*?)<a href="/up/acc', re.S)
    def netcraft(self, irc, msg, args):
        """<hostname|ip>

        Returns Netcraft.com's determination of what operating system and
        webserver is running on the host given.
        """
        hostname = privmsgs.getArgs(args)
        url = 'http://uptime.netcraft.com/up/graph/?host=%s' % hostname
        fd = urllib2.urlopen(url)
        html = fd.read()
        fd.close()
        m = self._netcraftre.search(html)
        if m:
            html = m.group(1)
            s = utils.htmlToText(html, tagReplace='').strip('\xa0 ')
            irc.reply(msg, s[9:]) # Snip off "the site"
        elif 'We could not get any results' in html:
            irc.reply(msg, 'No results found for %s.' % hostname)
        else:
            irc.error(msg, 'The format of the was odd.')

    _abbrevs = utils.abbrev(map(str.lower, babelfish.available_languages))
    _abbrevs['de'] = 'german'
    _abbrevs['jp'] = 'japanese'
    _abbrevs['kr'] = 'korean'
    _abbrevs['es'] = 'spanish'
    _abbrevs['pt'] = 'portuguese'
    _abbrevs['it'] = 'italian'
    _abbrevs['zh'] = 'chinese'
    for language in babelfish.available_languages:
        _abbrevs[language] = language
    def translate(self, irc, msg, args):
        """<from-language> <to-language> <text>

        Returns the text translated to the new language.
        """
        (fromLang, toLang, text) = privmsgs.getArgs(args, needed=3)
        try:
            fromLang = self._abbrevs[fromLang.lower()]
            toLang = self._abbrevs[toLang.lower()]
            translation = babelfish.translate(text, fromLang, toLang)
            irc.reply(msg, translation)
        except (KeyError, babelfish.LanguageNotAvailableError), e:
            irc.error(msg, '%s is not a valid language.  Valid languages ' \
                      'include %s' % \
                      (e, utils.commaAndify(babelfish.available_languages)))
        except babelfish.BabelizerIOError, e:
            irc.error(msg, e)
        except babelfish.BabelfishChangedError, e:
            irc.error(msg, 'Babelfish has foiled our plans by changing its ' \
                           'webpage format')

    def babelize(self, irc, msg, args):
        """<from-language> <to-language> <text>

        Translates <text> repeatedly between <from-language> and <to-language>
        until it doesn't change anymore or 12 times, whichever is fewer.  One
        of the languages must be English.
        """
        (fromLang, toLang, text) = privmsgs.getArgs(args, needed=3)
        try:
            fromLang = self._abbrevs[fromLang.lower()]
            toLang = self._abbrevs[toLang.lower()]
            if fromLang != 'english' and toLang != 'english':
                irc.error(msg, 'One language must be English.')
                return
            translations = babelfish.babelize(text, fromLang, toLang)
            irc.reply(msg, translations[-1])
        except (KeyError, babelfish.LanguageNotAvailableError), e:
            irc.reply(msg, '%s is not a valid language.  Valid languages ' \
                      'include %s' % \
                      (e, utils.commaAndify(babelfish.available_languages)))
        except babelfish.BabelizerIOError, e:
            irc.reply(msg, e)
        except babelfish.BabelfishChangedError, e:
            irc.reply(msg, 'Babelfish has foiled our plans by changing its ' \
                           'webpage format')

    def randomlanguage(self, irc, msg, args):
        """[<allow-english>]

        Returns a random language supported by babelfish.  If <allow-english>
        is provided, will include English in the list of possible languages.
        """
        allowEnglish = privmsgs.getArgs(args, needed=0, optional=1)
        language = random.sample(babelfish.available_languages, 1)[0]
        while not allowEnglish and language == 'English':
            language = random.sample(babelfish.available_languages, 1)[0]
        irc.reply(msg, language)

Class = Http

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
