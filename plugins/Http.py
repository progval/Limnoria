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

    _titleRe = re.compile(r'<title>(.*)</title>')
    def title(self, irc, msg, args):
        """<url>

        Returns the HTML <title>...</title> of a URL.
        """
        url = privmsgs.getArgs(args)
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

    _zipcode = re.compile(r'Local Forecast for (.*), (.*?) ')
    def zipcode(self, irc, msg, args):
        """<US zip code>

        Returns the city and state of a given US Zip code.
        """
        zip = privmsgs.getArgs(args)
        url = "http://www.weather.com/weather/local/%s?lswe=%s" % (zip, zip)
        try:
            html = urllib2.urlopen(url).read()
            (city, state) = self._zipcode.search(html).groups()
            irc.reply(msg, '%s, %s' % (city, state))
        except AttributeError:
            irc.error(msg, 'the format of the page was odd.')
        except urllib2.URLError:
            irc.error(msg, 'Couldn\'t open search page.')

    
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

        Displays the first acronym matches from acronymfinder.com
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

    _debreflags = re.DOTALL | re.IGNORECASE
    _debpkgre = re.compile(r'<a.*>(.*?)</a>', _debreflags)
    _debbrre = re.compile(r'<td align="center">(\S+)\s*</?td>', _debreflags)
    _debtablere = re.compile(r'<table\s*[^>]*>(.*?)</table>', _debreflags)
    _debnumpkgsre = re.compile(r'out of total of (\d+)', _debreflags)
    _debBranches = ('stable', 'testing', 'unstable', 'experimental')
    def debversion(self, irc, msg, args):
        """<package name> [stable|testing|unstable|experimental]
        
        Returns the current version(s) of a Debian package in the given branch
        (if any, otherwise all available ones are displayed).
        """
        if args and args[-1] in self._debBranches:
            branch = args.pop()
        else:
            branch = 'all'
        if not args:
            irc.error(msg, 'You must give a package name.')
        responses = []
        numberOfPackages = 0
        for package in args:
            fd = urllib2.urlopen('http://packages.debian.org/cgi-bin/' \
                                 'search_packages.pl?' \
                                 'keywords=%s&searchon=names&' \
                                 'version=%s&release=all' % \
                                 (package, branch))
            html = fd.read()
            fd.close()
            m = self._debtablere.search(html)
            if m is None:
                responses.append('No package found for: %s (%s)' % \
                                 (package, branch))
            else:
                tableData = m.group(1)
                rows = tableData.split('</TR>')
                m = self._debnumpkgsre.search(tableData)
                if m:
                    numberOfPackages += int(m.group(1))
                for row in rows:
                    pkgMatch = self._debpkgre.search(row)
                    brMatch = self._debbrre.search(row)
                    if pkgMatch and brMatch:
                        s = '%s (%s)' % (pkgMatch.group(1), brMatch.group(1))
                        responses.append(s)
        random.shuffle(responses)
        ircutils.shrinkList(responses, ', ', 400)
        s = 'Total matches: %s, shown: %s.  %s' % \
            (numberOfPackages, len(responses), ', '.join(responses))
        irc.reply(msg, s)

            

Class = Http

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
