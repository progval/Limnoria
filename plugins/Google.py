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
Acceses Google for various things.
"""

from baseplugin import *

import re
import time
import getopt
import urllib2

import google

import utils
import ircmsgs
import privmsgs
import callbacks
import structures

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, something, yn
    print 'To use Google\'t Web Services, you must have a license key.'
    if yn('Do you have a license key?') == 'y':
        key = anything('What is it?')
        onStart.append('load Google')
        onStart.append('googlelicensekey %s' % key)
        if yn('Google depends on the Alias module for some commands.  ' \
              'Is the Alias module loaded?') == 'n':
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
        print 'You can apply for a key from http://www.google.com/apis/'
        
class GooglePrivmsg(callbacks.Privmsg):
    threaded = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.total = 0
        self.totalTime = 0
        self.last24hours = structures.queue()

    def _searched(self, data):
        now = time.time()
        self.total += 1
        self.totalTime += data.meta.searchTime
        self.last24hours.enqueue(now)
        while self.last24hours and now - self.last24hours.peek() > 86400:
            self.last24hours.dequeue()
        
    def formatData(self, data):
        self._searched(data)
        time = '(search took %s seconds)' % data.meta.searchTime
        results = []
        for result in data.results:
            title = utils.htmlToText(result.title.encode('utf-8'))
            url = result.URL
            if title:
                results.append('\x02%s\x02: %s' % (title, url))
            else:
                results.append(url)
        if not results:
            return 'No matches found %s' % time
        else:
            s = ircutils.privmsgPayload(results, ' :: ', 375)
            return '%s %s' % (s, time)

    def googlelicensekey(self, irc, msg, args):
        """<key>

        Sets the Google license key for using Google's Web Services API.  This
        is necessary before you can do any searching with this module.
        """
        key = privmsgs.getArgs(args)
        google.setLicense(key)
        irc.reply(msg, conf.replySuccess)
    googlelicensekey = privmsgs.checkCapability(googlelicensekey, 'admin')
        
    def google(self, irc, msg, args):
        """<search string> [--{language,restrict,safe,filter}=<value>]

        Searches google.com for the given string.  As many results as can fit
        are included.  Use options to set different values for the options
        Google accepts.
        """
        (optlist, rest) = getopt.getopt(args, '', ['language=', 'restrict=',
                                                   'safe=', 'filter='])
        kwargs = {'language': 'lang_en', 'safeSearch': 1}
        for (option, argument) in optlist:
            kwargs[option[2:]] = argument
        searchString = privmsgs.getArgs(rest)
        data = google.doGoogleSearch(searchString, **kwargs)
        irc.reply(msg, self.formatData(data))

    def googlesite(self, irc, msg, args):
        """<site> <search string>

        Searches Google on a specific site.
        """
        (site, s) = privmsgs.getArgs(args, needed=2)
        searchString = 'site:%s %s' % (site, s)
        data = google.doGoogleSearch(searchString,
                                     language='lang_en',
                                     safeSearch=1)
        irc.reply(msg, self.formatData(data))

    def googlespell(self, irc, msg, args):
        "<word>"
        word = privmsgs.getArgs(args)
        result = google.doSpellingSuggestion(word)
        if result:
            irc.reply(msg, result)
        else:
            irc.reply(msg, 'No spelling suggestion made.')

    def googleinfo(self, irc, msg, args):
        """takes no arguments

        Returns interesting information about this Google module.  Mostly
        useful for making sure you don't go over your 1000 requests/day limit.
        """
        last24hours = len(self.last24hours)
        irc.reply(msg, 'This google module has been called %s time%stotal; '\
                       '%s time%sin the past 24 hours.  ' \
                       'Google has spent %s seconds searching for me.' % \
                  (self.total, self.total != 1 and 's ' or ' ',
                   last24hours, last24hours != 1 and 's ' or ' ',
                   self.totalTime))


class GooglePrivmsgRegexp(callbacks.PrivmsgRegexp):
    threaded = True
    def googleSnarfer(self, irc, msg, match):
        r"^google\s+(.*)$"
        data = google.doGoogleSearch(match.group(1), safeSearch=1)
        url = data.results[0].URL
        irc.queueMsg(ircmsgs.privmsg(ircutils.replyTo(msg), url))

    _ggThread = re.compile(r'<br>Subject: ([^<]+)<br>')
    _ggGroup = re.compile(r'Newsgroups: <a[^>]+>([^<]+)</a>')
    def googlegroups(self, irc, msg, match):
        r"http://groups.google.com/[^\s]+"
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
            irc.queueMsg(ircmsgs.privmsg(ircutils.replyTo(msg),
              'Google Groups: %s, %s' % (mGroup.group(1), mThread.group(1))))
        else:
            irc.queueMsg(ircmsgs.privmsg(msg.args[0],
              'That doesn\'t appear to be a proper Google Groups page.'))



class Google(callbacks.Combine):
    classes = [GooglePrivmsg, GooglePrivmsgRegexp]

Class = Google

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
