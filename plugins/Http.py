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

__revision__ = "$Id$"

import plugins

import re
import sets
import getopt
import socket
import urllib2
import xml.dom.minidom
from itertools import imap, ifilter

import conf
import utils
import webutils
import privmsgs
import callbacks

class FreshmeatException(Exception):
    pass

class Http(callbacks.Privmsg):
    threaded = True
    maxSize = 4096
    _titleRe = re.compile(r'<title>(.*?)</title>', re.I | re.S)
    def callCommand(self, method, irc, msg, *L):
        try:
            callbacks.Privmsg.callCommand(self, method, irc, msg, *L)
        except webutils.WebError, e:
            irc.error(msg, str(e))
            
    def headers(self, irc, msg, args):
        """<url>

        Returns the HTTP headers of <url>.  Only HTTP urls are valid, of
        course.
        """
        url = privmsgs.getArgs(args)
        if not url.startswith('http://'):
            irc.error(msg, 'Only HTTP urls are valid.')
            return
        try:
            fd = webutils.getUrlFd(url)
            s = ', '.join(['%s: %s' % (k, v) for (k, v) in fd.headers.items()])
            irc.reply(msg, s)
        except webutils.WebError, e:
            irc.error(msg, str(e))
            
    _doctypeRe = re.compile(r'(<!DOCTYPE[^>]+>)', re.M)
    def doctype(self, irc, msg, args):
        """<url>

        Returns the DOCTYPE string of <url>.  Only HTTP urls are valid, of
        course.
        """
        url = privmsgs.getArgs(args)
        if not url.startswith('http://'):
            irc.error(msg, 'Only HTTP urls are valid.')
            return
        try:
            s = webutils.getUrl(url, size=self.maxSize)
            m = self._doctypeRe.search(s)
            if m:
                s = utils.normalizeWhitespace(m.group(0))
                irc.reply(msg, '%s has the following doctype: %s' % (url, s))
            else:
                irc.reply(msg, '%s has no specified doctype.' % url)
        except webutils.WebError, e:
            irc.error(msg, str(e))
            
    def size(self, irc, msg, args):
        """<url>

        Returns the Content-Length header of <url>.  Only HTTP urls are valid,
        of course.
        """
        url = privmsgs.getArgs(args)
        if not url.startswith('http://'):
            irc.error(msg, 'Only HTTP urls are valid.')
            return
        try:
            fd = webutils.getUrlFd(url)
            try:
                size = fd.headers['Content-Length']
                irc.reply(msg, '%s is %s bytes long.' % (url, size))
            except KeyError:
                s = fd.read(self.maxSize)
                if len(s) != self.maxSize:
                    irc.reply(msg, '%s is %s bytes long.' % (url, len(s)))
                else:
                    irc.reply(msg, 'The server didn\'t tell me how long %s is '
                                   'but it\'s longer than %s bytes.' %
                                   (url,self.maxSize))
        except webutils.WebError, e:
            irc.error(msg, str(e))

    def title(self, irc, msg, args):
        """<url>

        Returns the HTML <title>...</title> of a URL.
        """
        url = privmsgs.getArgs(args)
        if '://' not in url:
            url = 'http://%s' % url
        try:
            text = webutils.getUrl(url, size=self.maxSize)
            m = self._titleRe.search(text)
            if m is not None:
                irc.reply(msg, utils.htmlToText(m.group(1).strip()))
            else:
                irc.reply(msg, 'That URL appears to have no HTML title '
                               'within the first %s bytes.' % self.maxSize)
        except ValueError, e:
            irc.error(msg, str(e))

    def freshmeat(self, irc, msg, args):
        """<project name>

        Returns Freshmeat data about a given project.
        """
        project = privmsgs.getArgs(args)
        project = ''.join(project.split())
        url = 'http://www.freshmeat.net/projects-xml/%s' % project
        try:
            text = webutils.getUrl(url)
            if text.startswith('Error'):
                raise FreshmeatException, text
            dom = xml.dom.minidom.parseString(text)
            def getNode(name):
                node = dom.getElementsByTagName(name)[0]
                return str(node.childNodes[0].data)
            project = getNode('projectname_full')
            version = getNode('latest_release_version')
            vitality = getNode('vitality_percent')
            popularity = getNode('popularity_percent')
            lastupdated = getNode('date_updated')
            irc.reply(msg,
                      '%s, last updated %s, with a vitality percent of %s '\
                      'and a popularity of %s, is in version %s.' % \
                      (project, lastupdated, vitality, popularity, version))
        except FreshmeatException, e:
            irc.error(msg, utils.exnToString(e))

    def stockquote(self, irc, msg, args):
        """<company symbol>

        Gets the information about the current price and change from the
        previous day of a given compny (represented by a stock symbol).
        """
        symbol = privmsgs.getArgs(args)
        url = 'http://finance.yahoo.com/d/quotes.csv?s=%s'\
              '&f=sl1d1t1c1ohgv&e=.csv' % symbol
        quote = webutils.getUrl(url)
        data = quote.split(',')
        if data[1] != '0.00':
            irc.reply(msg,
                       'The current price of %s is %s, as of %s EST.  '\
                       'A change of %s from the last business day.' %\
                       (data[0][1:-1], data[1], data[3][1:-1], data[4]))
        else:
            m = 'I couldn\'t find a listing for %s' % symbol
            irc.error(msg, m)

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
    _realStates = sets.Set(['ak', 'al', 'ar', 'az', 'ca', 'co', 'ct', 
    			    'dc', 'de', 'fl', 'ga', 'hi', 'ia', 'id',
			    'il', 'in', 'ks', 'ky', 'la', 'ma', 'md',
			    'me', 'mi', 'mn', 'mo', 'ms', 'mt', 'nc',
			    'nd', 'ne', 'nh', 'nj', 'nm', 'nv', 'ny',
			    'oh', 'ok', 'or', 'pa', 'ri', 'sc', 'sd',
			    'tn', 'tx', 'ut', 'va', 'vt', 'wa', 'wi',
			    'wv', 'wy'])
    # Provinces.  (Province being a metric state measurement mind you. :D)
    _fakeStates = sets.Set(['ab', 'bc', 'mb', 'nb', 'nf', 'ns', 'nt',
                           'nu', 'on', 'pe', 'qc', 'sk', 'yk'])
    # Certain countries are expected to use a standard abbreviation
    # The weather we pull uses weird codes.  Map obvious ones here.
    _countryMap = {'uk': 'gb'}
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
            #We must break the States up into two sections.  The US and
            #Canada are the only countries that require a State argument.
            
            if state in self._realStates:
                country = 'us'
            elif state in self._fakeStates:
                country = 'ca'
            else:
                country = state
                state = ''
	    if country in self._countryMap.keys():
	        country = self._countryMap[country]
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?'\
                  'pass=&dpp=&forecast=zandh&config=&'\
                  'place=%s&state=%s&country=%s' % \
                  (city, state, country)
	    html = webutils.getUrl(url)
	    if 'was not found' in html:
	        url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?'\
		      'pass=&dpp=&forecast=zandh&config=&'\
		      'place=%s&state=&country=%s' % \
		      (city, state)
		html = webutils.getUrl(url)
		if 'was not found' in html:
		    irc.error(msg, 'No such location could be found.')
		    return

        #We received a single argument.  Zipcode or station id.
        else:
            zip = privmsgs.getArgs(args)
            zip = zip.replace(',','')  
            zip = zip.lower().split()
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?'\
                  'config=&forecast=zandh&pands=%s&Submit=GO' % args[0]
            html = webutils.getUrl(url)
	    if 'was not found' in html:
	        irc.error(msg, 'No such location could be found.')
		return
		
        headData = self._cityregex.search(html)
        if headData:
            (city, state, country) = headData.groups()
        else:
            headData = self._interregex.search(html)
	    if headData:
	        (city, state) = headData.groups()
	    else:
	        irc.error(msg, 'No such location could be found.')
		return

        temp = self._tempregex.search(html).group(1)
        conds = self._condregex.search(html).group(1)

        if temp and conds and city and state:
            conds = conds.replace('Tsra', 'Thunder Storms')
            s = 'The current temperature in %s, %s is %s.  ' \
                'Conditions: %s.' % \
                (city.strip(), state.strip(), temp, conds)
            irc.reply(msg, s)
        else:
            irc.error(msg, 'The format of the page was odd.')

    _mlgeekquotere = re.compile('<p class="qt">(.*?)</p>', re.M | re.DOTALL)
    def geekquote(self, irc, msg, args):
        """[--id=<value>]

        Returns a random geek quote from bash.org; the optional argument
        --id specifies which quote to retrieve.
        """
        (optlist, rest) = getopt.getopt(args, '', ['id='])
        id = 'random1'
        for (option, arg) in optlist:
            if option == '--id':
                try:
                    id = int(arg)
                except ValueError, e:
                    irc.error(msg, 'Invalid id: %s' % e)
                    return

        html = webutils.getUrl('http://bash.org/?%s' % id)
        m = self._mlgeekquotere.search(html)
        if m is None:
            irc.error(msg, 'No quote found.')
            return
        quote = utils.htmlToText(m.group(1))
        quote = ' // '.join(quote.splitlines())
        irc.reply(msg, quote)

    _acronymre = re.compile(r'valign="middle" width="7\d%" bgcolor="[^"]+">'
                            r'(?:<b>)?([^<]+)')
    def acronym(self, irc, msg, args):
        """<acronym>

        Displays acronym matches from acronymfinder.com
        """
        acronym = privmsgs.getArgs(args)
        url = 'http://www.acronymfinder.com/' \
              'af-query.asp?String=exact&Acronym=%s' % acronym
        request = urllib2.Request(url, headers={'User-agent':
          'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 4.0)'})
        html = webutils.getUrl(request)
        # The following definitions are stripped and empties are removed.
        defs = filter(None, imap(str.strip, self._acronymre.findall(html)))
        utils.sortBy(lambda s: not s.startswith('[not an acronym]'), defs)
        for (i, s) in enumerate(defs):
            if s.startswith('[not an acronym]'):
                defs[i] = s.split('is ', 1)[1]
        if len(defs) == 0:
            irc.reply(msg,'No definitions found.  (%s)'%conf.replyPossibleBug)
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
        html = webutils.getUrl(url)
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
            try:
                fd = webutils.getUrlFd('http://kernel.org/kdist/finger_banner')
            except webutils.WebError, e:
                irc.error(msg, str(e))
                return
            for line in fd:
                (name, version) = line.split(':')
                if 'latest stable' in name:
                    stable = version.strip()
                elif 'latest beta' in name:
                    beta = version.strip()
        finally:
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
        try:
            L = []
            fd = urllib2.urlopen(url)
            for line in iter(fd.next, ''):
                info = self._pgpkeyre.search(line)
                if info:
                    L.append('%s <%s%s>' % (info.group(3),host,info.group(1)))
            if len(L) == 0:
                irc.reply(msg, 'No results found for %s.' % search)
            else:
                s = 'Matches found for %s: %s' % (search, ' :: '.join(L))
                irc.reply(msg, s)
        finally:
            fd.close()

Class = Http

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
