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
import time
import urllib
import urllib2

import utils
import debug
import privmsgs
import callbacks

class FreshmeatException(Exception):
    pass

class Http(callbacks.Privmsg):
    threaded = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.deepthoughtq = structures.queue()

    def deepthought(self, irc, msg, args):
        """takes no arguments

        Returns a Deep Thought by Jack Handey.
        """
        url = 'http://www.tremorseven.com/aim/deepaim.php?job=view'
        thought = ' ' * 512
        while time.time() - self.deepthoughtq[0][0] > 86400:
            self.deepthoughtq.dequeue()
        while len(thought) > 450 or thought in self.deepthoughtq:
            fd = urllib2.urlopen(url)
            s = fd.read()
            thought = s.split('<br>')[2]
            thought = ' '.join(thought.split())
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
            s = 'There appears to be no definition for %s.' % search
            irc.reply(msg, s)

    _gkrating = re.compile(r'<font color="#FFFF33">(\d+)</font>')
    _gkgames = re.compile(r's:&nbsp;&nbsp;</td><td class=sml>(\d+)</td></tr>')
    _gkrecord = re.compile(r'"#FFFF00">(\d+)[^"]+"#FFFF00">(\d+)[^"]+'\
        '"#FFFF00">(\d+)')
    _gkteam = re.compile(r'Team:(<.*?>)+(?P<name>.*?)</span>')
    _gkseen = re.compile(r'(seen on GK:\s+([^[]+)\s+|.*?is hiding.*?)')
    def gkstats(self, irc, msg, args):
        """<name>

        Returns the stats Gameknot keeps on <name>.  Gameknot is an online
        website for playing chess (rather similar to correspondence chess, just
        somewhat faster) against players from all over the world.
        """
        name = privmsgs.getArgs(args)
        gkprofile = 'http://www.gameknot.com/stats.pl?%s' % name
        try:
            fd = urllib2.urlopen(gkprofile)
            profile = fd.read()
            fd.close()
            rating = self._gkrating.search(profile).group(1)
            games = self._gkgames.search(profile).group(1)
            (w, l, d) = self._gkrecord.search(profile).groups()
            seen = self._gkseen.search(utils.htmlToText(profile))
            if seen.group(0).find("is hiding") != -1:
                seen = '%s is hiding his/her online status.' % name
            elif seen.group(2).startswith('0'):
                seen = '%s is on gameknot right now.' % name
            else:
                seen = '%s was last seen on Gameknot %s.' % (name,
                seen.group(2))
            if profile.find('Team:') >= 0:
                team = self._gkteam.search(profile).group('name')
                irc.reply(msg, '%s (team: %s) is rated %s and has %s active ' \
                          'games and a record of W-%s, L-%s, D-%s.  %s' % \
                          (name, team, rating, games, w, l, d, seen))
            else:
                irc.reply(msg, '%s is rated %s and has %s active games ' \
                          'and a record of W-%s, L-%s, D-%s.  %s' % \
                          (name, rating, games, w, l, d, seen))
        except AttributeError:
            if profile.find('User %s not found!' % name) != -1:
                irc.error(msg, 'No user %s exists.')
            else:
                irc.error(msg, 'The format of the page was odd.')
        except urllib2.URLError:
            irc.error(msg, 'Couldn\'t connect to gameknot.com.')

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
        defs = self._acronymre.findall(html)
        if len(defs) == 0:
            irc.reply(msg, 'No definitions found.')
        else:
            s = ircutils.privmsgPayload([repr(s.strip()) for s in defs[1:-1]],
                                        '," or "')
            irc.reply(msg, '%s could be "%s"' % (acronym, s))

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
        elif html.find('We could not get any results') != -1:
            irc.reply(msg, 'No results found for %s.' % hostname)
        else:
            irc.error(msg, 'The format of the was odd.')


Class = Http

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
