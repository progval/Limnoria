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

from baseplugin import *

import re
import urllib2
import threading
#import xml.dom.minidom

import debug
import privmsgs
import callbacks

_htmlstripper = re.compile('<[^>]+>')
def stripHtml(s):
    return _htmlstripper.sub('', s)

class FreshmeatException(Exception):
    pass

class Http(callbacks.Privmsg):
    threaded = True
    _fmProject = re.compile('<projectname_full>(.*?)</projectname_full>')
    _fmVersion = re.compile('<latest_version>(.*?)</latest_version>')
    _fmVitality = re.compile('<vitality_percent>(.*?)</vitality_percent>')
    _fmPopularity =re.compile('<popularity_percent>(.*?)</popularity_percent>')
    _fmLastUpdated = re.compile('<date_updated>(.*?)</date_updated>')
    def freshmeat(self, irc, msg, args):
        "<project name>"
        project = privmsgs.getArgs(args)
        url = 'http://www.freshmeat.net/projects-xml/%s' % project
        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            if text.startswith('Error'):
                raise FreshmeatException, text
            project = self._fmProject.search(text).group(1)
            version = self._fmVersion.search(text).group(1)
            vitality = self._fmVitality.search(text).group(1)
            popularity = self._fmPopularity.search(text).group(1)
            lastupdated = self._fmLastUpdated.search(text).group(1)
            irc.reply(msg,
              '%s, last updated %s, with a vitality percent of %s '\
              'and a popularity of %s, is in version %s.' % \
              (project, lastupdated, vitality, popularity, version))
        except FreshmeatException, e:
            irc.reply(msg, debug.exnToString(e))
        except Exception, e:
            debug.recoverableException()
            irc.reply(msg, debug.exnToString(e))

    _htmlTag = re.compile('<.*?>')
    _htmlEntity = re.compile('&.*?;')
    _html = re.compile('<.*?>|&.*?;')
    def cfactive(self, irc, msg, args):
        "takes no arguments."
        try:
            fd = urllib2.urlopen('http://www.coderforums.net/')
        except Exception, e:
            irc.error(msg, debug.exnToString(e))
        text = fd.read()
        text = self._htmlTag.sub('', text)
        lines = text.splitlines()
        sent = False
        for i in range(len(lines) - 1):
            if lines[i].strip().startswith('Most'):
                sent = True
                irc.reply(msg, lines[i+1].strip())
                break
        if not sent:
            irc.reply(msg, 'The format of the page seems odd.')

    def stockquote(self, irc, msg, args):
        "<company symbol>"
        symbol = privmsgs.getArgs(args)
        url = 'http://finance.yahoo.com/d/quotes.csv?s=%s'\
              '&f=sl1d1t1c1ohgv&e=.csv' % symbol
        try:
            quote = urllib2.urlopen(url).read()
        except Exception, e:
            irc.reply(msg, debug.exnToString(e))
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
        "<something to lookup on foldoc>"
        search = '+'.join(args)
        url = 'http://foldoc.doc.ic.ac.uk/foldoc/foldoc.cgi?query=%s' % search
        try:
            html = urllib2.urlopen(url).read()
        except Exception, e:
            irc.error(msg, debug.exnToString(e))
        text = html.split('<P>\n', 2)[1]
        text = text.replace('.\n', '.  ')
        text = text.replace('\n', ' ')
        text = self._html.sub('', text)
        irc.reply(msg, text.strip())

    _gkrating = re.compile(r'<font color="#FFFF33">(\d+)</font>')
    _gkgames = re.compile(r's:&nbsp;&nbsp;</td><td class=sml>(\d+)</td></tr>')
    _gkrecord = re.compile(r'percentile(\d+), .*?%(\d+), .*?%(\d+)')
    def gkstats(self, irc, msg, args):
        "<name>"
        name = privmsgs.getArgs(args)
        gkprofile = 'http://www.gameknot.com/stats.pl?%s' % name
        try:
            profile = urllib2.urlopen(gkprofile).read()
            rating = self._gkrating.search(profile).group(1)
            games = self._gkgames.search(profile).group(1)
            profile = stripHtml(profile)
            (w, l, d) = self._gkrecord.search(profile).groups()
            irc.reply(msg, '%s is rated %s and has %s active games; '
                           'W-%s, L-%s, D-%s' % (name, rating, games, w, l, d))
        except AttributeError:
            irc.error(msg, 'The format of the page was odd.')
        except urllib2.URLError:
            irc.error(msg, 'Couldn\'t connect to gameknot.com.')

    _zipcode = re.compile(r'Local Forecast for (.*), (.*?) ')
    def zipcode(self, irc, msg, args):
        "<US zip code>"
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
        "<US zip code>"
        zip = privmsgs.getArgs(args)
        url = "http://www.weather.com/weather/local/%s?lswe=%s" % (zip, zip)
        try:
            html = urllib2.urlopen(url).read()
            city, state = self._cityregex.search(html).groups()
            temp = self._tempregex.search(html).group(1)
            conds = self._condregex.search(html).group(1).strip()
            irc.reply(msg, 'The current temperature in %s, %s is %dF with %s\
                            conditions' % (city, state, int(temp), conds))
        except AttributeError:
            irc.error(msg, 'the format of the page was odd.')
        except urllib2.URLError:
            irc.error(msg, 'Couldn\'t open the search page.')

Class = Http
