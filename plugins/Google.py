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

Commands include:
  google
  googlelinux
  googlebsd
  googlemac
  googlespell
  googlelicensekey
"""

from baseplugin import *

import time
import operator

import google

import utils
import privmsgs
import callbacks

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, something, yn
    print 'To use Google\'t Web Services, you must have a license key.'
    if yn('Do you have a license key?') == 'y':
        key = anything('What is it?')
        onStart.append('load Google')
        onStart.append('googlelicensekey %s' % key)
    else:
        print 'You\'ll need to get a key before you can use this plugin.'
        print 'You can apply for a key from http://www.google.com/apis/'
        
class Google(callbacks.Privmsg):
    threaded = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.total = 0
        self.totalTime = 0
        self.last24hours = queue()

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
        while reduce(operator.add, map((4).__add__,map(len, results)),0) > 400:
            results.pop()
        if not results:
            return 'No matches found %s' % time
        else:
            return '%s %s' % (' :: '.join(results), time)

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
        """<search string>

        Searches google.com for the given string.  As many results as can fit
        are included.
        """
        searchString = privmsgs.getArgs(args)
        data = google.doGoogleSearch(searchString,
                                     language='lang_en',
                                     safeSearch=1)
        irc.reply(msg, self.formatData(data))

    def googlelinux(self, irc, msg, args):
        """<search string>

        Searches Google's Linux repository.
        """
        searchString = privmsgs.getArgs(args)
        data=google.doGoogleSearch(searchString,
                                   restrict='linux',
                                   language='lang_en',
                                   safeSearch=1)
        irc.reply(msg, self.formatData(data))

    def googlebsd(self, irc, msg, args):
        """<search string>

        Searches Google's BSD repository.
        """
        searchString = privmsgs.getArgs(args)
        data = google.doGoogleSearch(searchString,
                                     restrict='bsd',
                                     language='lang_en',
                                     safeSearch=1)
        irc.reply(msg, self.formatData(data))

    def googlemac(self, irc, msg, args):
        """<search string>

        Searches Google's Mac repository.
        """
        searchString = privmsgs.getArgs(args)
        data = google.doGoogleSearch(searchString,
                                     restrict='mac',
                                     language='lang_en',
                                     safeSearch=1)
        irc.reply(msg, self.formatData(data))

    def googlesite(self, irc, msg, args):
        """<site> <search string>

        Searches Google on a specific site.
        """
        searchString = 'site:%s %s' % privmsgs.getArgs(args, needed=2)
        data = google.doGoogleSearch(searchString,
                                     language='lang_en',
                                     safeSearch=1)
        irc.reply(msg, self.formatData(data))

    def googleplex(self, irc, msg, args):
        """<search string> [language, restrict, safe, filter] keyword arguments

        Search google, providing all your own options.
        """
        (args, kwargs) = privmsgs.getKeywordArgs(irc, msg)
        searchString = ' '.join(args)
        if 'safe' in kwargs:
            kwargs['safeSearch'] = int(kwargs['safe'])
            del kwargs['safe']
        data = google.doGoogleSearch(searchString, **kwargs)
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
        """takes no arguments"""
        last24hours = len(self.last24hours)
        irc.reply(msg, 'This google module has been called %s time%stotal; '\
                       '%s time%sin the past 24 hours.  ' \
                       'Google has spent %s seconds searching for me.' % \
                  (self.total, self.total != 1 and 's ' or ' ',
                   last24hours, last24hours != 1 and 's ' or ' ',
                   self.totalTime))


Class = Google

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
