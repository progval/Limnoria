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

import plugins

import re
import sets
import time
import urllib2

import utils
import debug
import privmsgs
import callbacks
import structures

example = utils.wrapLines("""
<jemfinch> @list Http
<supybot> acronym, babelize, deepthought, freshmeat, geekquote, netcraft, randomlanguage, stockquote, title, translate, weather
<jemfinch> @acronym ASAP
<supybot> ASAP could be As Soon As Possible, or A Simplified Asset (disposal) Procedure, or A Stupid Acting Person (Dilbert comic strip), or Academic Strategic Alliances Program, or Accelerated Situational Awareness Prototype, or Accelerated Systems Applications and Products (data processing), or Acquisitions Strategies and Plans, or Administrative Services Automation Program, or Administrative Services Automation Project
<jemfinch> @deepthought
<supybot> #331: Probably one of the worst things about being a genie in a magic lamp is a little thing called "lamp stench."
<jemfinch> @freshmeat supybot
<supybot> SupyBot, last updated 2002-08-02 19:07:52, with a vitality percent of 0.00 and a popularity of 0.09, is in version 0.36.1.
<jemfinch> (yeah, I haven't updated that in awhile :))
<jemfinch> @geekquote
<supybot> <Coco13> Girls are a waste of polygons.
<jemfinch> @netcraft slashdot.org
<supybot> slashdot.org is running Apache/1.3.26 (Unix) mod_gzip/1.3.19.1a mod_perl/1.27 mod_ssl/2.8.10 OpenSSL/0.9.7a on Linux.
<jemfinch> @stockquote MSFT
<supybot> The current price of MSFT is 26.39, as of 11:22am EST.  A change of -0.18 from the last business day.
<jemfinch> @title slashdot.org
<supybot> Slashdot: News for nerds, stuff that matters
<jemfinch> @weather 43221
<supybot> The current temperature in Columbus, Ohio is 77F.  Conditions are Mist.
<jemfinch> @weather Paris, FR
<supybot> The current temperature in Paris, France is 27C.  Conditions are Fair.
<jemfinch> @randomlanguage
<supybot> Portuguese
<jemfinch> @babelize en [randomlanguage] [deepthought]
<supybot> # 355: When he was a small boy, had always wanted to be one acrobat. It looked at as thus much amusement, turning through air, to launch itself, fulling it it it he himself with the land in the shoulders of the person. Little knew that when finally one was changedded acrobat, would seem irritating thus. Years later, later this that stopped finally, joined did not work to it for it is as one acrobat after everything. Weirdo of the stre
""")

class FreshmeatException(Exception):
    pass

class Http(callbacks.Privmsg):
    threaded = True

    _titleRe = re.compile(r'<title>(.*)</title>', re.I | re.S)
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
                irc.reply(msg, utils.htmlToText(m.group(1).strip()))
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
    # States
    _realStates = sets.Set(['ak', 'al', 'ar', 'ca', 'co', 'ct', 'dc',
                            'de', 'fl', 'ga', 'hi', 'ia', 'id', 'il',
                            'in', 'ks', 'ky', 'la', 'ma', 'md', 'me',
                            'mi', 'mn', 'mo', 'ms', 'mt', 'nc', 'nd',
                            'ne', 'nh', 'nj', 'nm', 'nv', 'ny', 'oh',
                            'ok', 'or', 'pa', 'ri', 'sc', 'sd', 'tn',
                            'tx', 'ut', 'va', 'vt', 'wa', 'wi', 'wv', 'wy'])
    # Provinces.  (Province being a metric state measurement mind you. :D)
    _fakeStates = sets.Set(['ab', 'bc', 'mb', 'nb', 'nf', 'ns', 'nt',
                           'nu', 'on', 'pe', 'qc', 'sk', 'yk'])
    def weather(self, irc, msg, args):
        """<US zip code> <US/Canada city, state> <Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """
        
        #If we received more than one argument, then we have received
        #a city and state argument that we need to process.
        if len(args) > 1:
            #If we received more than 1 argument, then we got a city with a
            #multi-word name.  ie ['Garden', 'City', 'KS'] instead of
            #['Liberal', 'KS'].  We join it together with a + to pass
            #to our query
            state = args.pop()
            state = state.lower()
            city = '+'.join(args)
            city = city.rstrip(',')
            city = city.lower()
            #debug.printf((state, city))
            #We must break the States up into two sections.  The US and
            #Canada are the only countries that require a State argument.
            
            if state in self._realStates:
                country = 'us'
            elif state in self._fakeStates:
                country = 'ca'
            else:
                country = state
                state = ''
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?'\
                  'pass=&dpp=&forecast=zandh&config=&'\
                  'place=%s&state=%s&country=%s' % \
                  (city, state, country)
            #debug.printf(url)

        #We received a single argument.  Zipcode or station id.
        else:
            zip = privmsgs.getArgs(args)
            zip = zip.replace(',','')  
            zip = zip.lower().split()
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?'\
                  'config=&forecast=zandh&pands=%s&Submit=GO' % args[0]

        #debug.printf(url)
        try:
            fd = urllib2.urlopen(url)
            html = fd.read()
            fd.close()
            if 'was not found' in html:
                irc.error(msg, 'No such location could be found.')
                return
            headData = self._cityregex.search(html)
            if headData:
                (city, state, country) = headData.groups()
            else:
                headData = self._interregex.search(html)
                (city, state) = headData.groups()
                
            temp = self._tempregex.search(html).group(1)
            conds = self._condregex.search(html).group(1)
            
            if temp and conds and city and state:
                s = 'The current temperature in %s, %s is %s.  ' \
                    'Conditions are %s.' % \
                    (city.strip(), state.strip(), temp, conds)
                irc.reply(msg, s)
            else:
                irc.error(msg, 'The format of the page was odd.')
        except urllib2.URLError:
            irc.error(msg, 'I couldn\'t open the search page.')
        except Exception, e:
            debug.recoverableException()
            irc.error(msg, debug.exnToString(e))

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
        utils.sortBy(lambda s: not s.startswith('[not an acronym]'), defs)
        for (i, s) in enumerate(defs):
            if s.startswith('[not an acronym]'):
                defs[i] = s.split('is ', 1)[1]
        #debug.printf(defs)
        if len(defs) == 0:
            irc.reply(msg, 'No definitions found.')
        else:
            s = ', or '.join(defs)
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
            irc.error(msg, 'The format of page the was odd.')

    def kernel(self, irc, msg, args):
        """takes no arguments

        Returns information about the current version of the Linux kernel.
        """
        try:
            fd = urllib2.urlopen('http://www.kernel.org/kdist/finger_banner')
        except urllib2.URLError:
            irc.error(msg, 'Couldn\'t connect to kernel.org.')
            return
        for line in fd:
            (name, version) = line.split(':')
            if 'latest stable' in name:
                stable = version.strip()
            elif 'latest beta' in name:
                beta = version.strip()
        fd.close()
        irc.reply(msg, 'The latest stable kernel is %s; ' \
                       'the latest beta kernel is %s.' % (stable, beta))

    _pgpkeyre = re.compile(r'pub\s+\d{4}\w/<a '\
        'href="([^"]+)">([^<]+)</a>[^>]+>([^<]+)</a>')
    def pgpkey(self, irc, msg, args):
        """<search words>

        Returns the results of querying pgp.mit.edu for keys that match
        the <search words>.
        """
        search = privmsgs.getArgs(args)
        urlClean = search.replace(' ', '+')
        host = 'http://pgp.mit.edu:11371'
        url = '%s/pks/lookup?op=index&search=%s' % (host, urlClean)
        fd = urllib2.urlopen(url)
        pgpkeys = ''
        line = fd.readline()
        while len(line) != 0:
            info = self._pgpkeyre.search(line)
            if info:
                pgpkeys += '%s <%s> :: ' % (info.group(3), '%s%s' % (host,
                    info.group(1)))
            line = fd.readline()
        if len(pgpkeys) == 0:
            irc.reply(msg, 'No results found for %s.' % search)
            fd.close()
        else:
            irc.reply(msg, 'Matches found for %s: %s' % (search, pgpkeys[:-4]))
            fd.close()

Class = Http

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
