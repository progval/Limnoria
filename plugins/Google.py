#re!/usr/bin/env python

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
Acceses Google for various things.
"""

import plugins

import re
import sets
import time
import getopt
import urllib2

import google

import conf
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks
import structures

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, something, yn
    print 'To use Google\'t Web Services, you must have a license key.'
    if yn('Do you have a license key?') == 'y':
        key = something('What is it?')
        while len(key) != 32:
            print 'That\'s not a valid Google license key.'
            if yn('Are you sure you have a valid Google license key?') == 'y':
                key = something('What is it?')
            else:
                key = ''
                break
        if key:
            onStart.append('load Google')
            onStart.append('google licensekey %s' % key)
        if 'load Alias' not in onStart:
            print 'Google depends on the Alias module for some commands.'
            if yn('Would you like to load the Alias module now?') == 'y':
                onStart.append('load Alias')
            else:
                print 'You can still use the Google module, but you won\'t ' \
                      'be asked any further questions.'
                return
        onStart.append('alias googlelinux "google --restrict=linux $1"')
        onStart.append('alias googlebsd "google --restrict=bsd $1"')
        onStart.append('alias googlemac "google --restrict=mac $1"')
    else:
        print 'You\'ll need to get a key before you can use this plugin.'
        print 'You can apply for a key at http://www.google.com/apis/'


example = utils.wrapLines("""
<jemfinch> @list googletools
<supybot> google, googlefight, googleinfo, googlelicensekey, googlesite, googlespell, metagoogle
<jemfinch> @google jemfinch
<supybot> [Twisted-commits] Like, you know, a bugfix. jemfinch reported.: http://twistedmatrix.com/pipermail/twisted-commits/2002-August/002956.html :: Character Analysis of JemFinch NetEssays.NET - Thousands of FREE ...: http://www.netessays.net/viewpaper/1379.html :: SourceForge.net: Developer Profile: http://sourceforge.net/users/jemfinch/ (search took 0.174663 seconds)
<jemfinch> @googlefight jemfinch supybot moobot ddipaolo
<supybot> 'moobot': 959, 'jemfinch': 236, 'ddipaolo': 229, 'supybot': 80
<jemfinch> @googleinfo
<supybot> This google module has been called 5 times total; 5 times in the past 24 hours.  Google has spent 1.229932 seconds searching for me.
<jemfinch> @googlespell recind
<supybot> rescind
<jemfinch> @metagoogle jemfinch
<supybot> Search for 'jemfinch' returned approximately 214 results in 0.072376 seconds.
<jemfinch> @googlesite slashdot.org SCO
<supybot> Slashdot | How SCO Helped Linux Go Enterprise: http://yro.slashdot.org/yro/03/07/22/0528203.shtml?tid=106&tid=185 :: Slashdot | SCO Threatens Red Hat and SuSE: http://science.slashdot.org/articles/03/04/23/1925259.shtml :: Slashdot | Linus Torvalds about SCO , IP, MS and Transmeta: http://slashdot.org/articles/03/07/05/1728201.shtml?tid=106&tid=185 (search took 0.210749 seconds)
""")

totalSearches = 0
totalTime = 0
last24hours = structures.queue()

def search(*args, **kwargs):
    global totalSearches, totalTime, last24hours
    data = google.doGoogleSearch(*args, **kwargs)
    now = time.time()
    totalSearches += 1
    totalTime += data.meta.searchTime
    last24hours.enqueue(now)
    while last24hours and now - last24hours.peek() > 86400:
        last24hours.dequeue()
    return data

class Google(callbacks.PrivmsgCommandAndRegexp):
    threaded = True
    regexps = sets.Set(['googleSnarfer', 'googleGroups'])
    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.total = 0
        self.totalTime = 0
        self.snarfer = True
        self.last24hours = structures.queue()

    def formatData(self, data):
        time = 'Search took %s seconds: ' % data.meta.searchTime
        results = []
        for result in data.results:
            title = utils.htmlToText(result.title.encode('utf-8'))
            url = result.URL
            if title:
                results.append('\x02%s\x0F: <%s>' % (title, url))
            else:
                results.append(url)
        if not results:
            return 'No matches found %s' % time
        else:
            return '%s %s' % (time, '; '.join(results))

    def licensekey(self, irc, msg, args):
        """<key>

        Sets the Google license key for using Google's Web Services API.  This
        is necessary before you can do any searching with this module.
        """
        key = privmsgs.getArgs(args)
        google.setLicense(key)
        irc.reply(msg, conf.replySuccess)
    licensekey = privmsgs.checkCapability(licensekey, 'admin')

    def togglesnarfer(self, irc, msg, args):
        """takes no argument

        Disables the snarfer that responds to all Sourceforge Tracker links
        """
        self.snarfer = not self.snarfer
        if self.snarfer:
            irc.reply(msg, '%s (Snarfer is enabled)' % conf.replySuccess)
        else:
            irc.reply(msg, '%s (Snarfer is disabled)' % conf.replySuccess)
    togglesnarfer=privmsgs.checkCapability(togglesnarfer, 'admin')

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
        kwargs = {'language': 'lang_en', 'safeSearch': 1}
        for (option, argument) in optlist:
            if option == '--notsafe':
                kwargs['safeSearch'] = False
            elif option == '--similar':
                kwargs['filter'] = False
            else:
                kwargs[option[2:]] = argument
        searchString = privmsgs.getArgs(rest)
        data = search(searchString, **kwargs)
        irc.reply(msg, self.formatData(data))

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
        searchString = privmsgs.getArgs(rest)
        data = search(searchString, **kwargs)
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
        irc.reply(msg, s)

    def fight(self, irc, msg, args):
        """<search string> <search string> [<search string> ...]

        Returns the results of each search, in order, from greatest number
        of results to least.
        """

        results = []
        for arg in args:
            data = search(arg)
            results.append((data.meta.estimatedTotalResultsCount, arg))
        results.sort()
        results.reverse()
        s = ', '.join(['%r: %s' % (s, i) for (i, s) in results])
        irc.reply(msg, s)

    def spell(self, irc, msg, args):
        """<word>

        Returns Google's spelling recommendation for <word>.
        """
        word = privmsgs.getArgs(args)
        result = google.doSpellingSuggestion(word)
        if result:
            irc.reply(msg, result)
        else:
            irc.reply(msg, 'No spelling suggestion made.')

    def info(self, irc, msg, args):
        """takes no arguments

        Returns interesting information about this Google module.  Mostly
        useful for making sure you don't go over your 1000 requests/day limit.
        """
        recent = len(last24hours)
        irc.reply(msg, 'This google module has been called %s time%stotal; '\
                       '%s time%sin the past 24 hours.  ' \
                       'Google has spent %s seconds searching for me.' % \
                  (totalSearches, totalSearches != 1 and 's ' or ' ',
                   recent, recent != 1 and 's ' or ' ',
                   totalTime))

    def googleSnarfer(self, irc, msg, match):
        r"^google\s+(.*)$"
        if not self.snarfer:
            return
        searchString = match.group(1)
        data = search(searchString, safeSearch=1)
        if data.results:
            url = data.results[0].URL
            irc.reply(msg, url)
        else:
            irc.reply(msg, 'No results for "%s"' % searchString)

    _ggThread = re.compile(r'<br>Subject: ([^<]+)<br>')
    _ggGroup = re.compile(r'Newsgroups: <a[^>]+>([^<]+)</a>')
    def googleGroups(self, irc, msg, match):
        r"http://groups.google.com/[^\s]+"
        if not self.snarfer:
            return
        request = urllib2.Request(match.group(0), headers=\
          {'User-agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 4.0)'})
        fd = urllib2.urlopen(request)
        text = fd.read()
        fd.close()
        if match.group(0).find('&prev=/') >= 0:
            path = re.search('view the <a href=([^>]+)>no',text)
            if path is None:
                return
            url = 'http://groups.google.com'
            request = urllib2.Request('%s%s' % (url,path.group(1)),
              headers={'User-agent': 'Mozilla/4.0 (compatible; MSIE 5.5;'
              'Windows NT 4.0)'})
            fd = urllib2.urlopen(request)
            text = fd.read()
            fd.close()
        mThread = self._ggThread.search(text)
        mGroup = self._ggGroup.search(text)
        if mThread and mGroup:
            irc.reply(msg, 'Google Groups: %s, %s' % (mGroup.group(1),
                mThread.group(1)), prefixName = False)
        else:
            irc.error(msg, 'That doesn\'t appear to be a proper '\
                'Google Groups page. (%s)' % conf.replyPossibleBug)


Class = Google


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
