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
Provides basic functionality for handling RSS/RDF feeds.  Depends on the Alias
module for user-friendliness: instead of:

rsstitles http://slashdot.org/slashdot.rss

It'll make the alias:

alias slashdot rsstitles http://slashdot.org/slashdot.rss

And you'll be able to call the command like this:

slashdot

Also includes a function for getting info about a specific feed, rssinfo.
"""

from baseplugin import *

import time

import rssparser

import utils
import privmsgs
import callbacks

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, something, yn
    onStart.append('load RSS')
    if yn('RSS depends on the Alias module.  Is that module loaded?') == 'n':
        if yn('Do you want to load that module now?') == 'y':
            onStart.append('load Alias')
        else:
            print 'You can still use the RSS module, but you won\'t be asked'
            print 'any further questions.'
            return
    prompt = 'Would you like to add an RSS feed?'
    while yn(prompt) == 'y':
        prompt = 'Would you like to add another RSS feed?'
        name = anything('What\'s the name of the website?')
        url = anything('What\'s the URL of the RSS feed?')
        if yn('Would you like to add an alias for accessing ' \
          '%s\'s info?' % name) == 'y':
            if advanced:
                infocmd = anything('What would you like for the info alias?')
            else:
                infocmd = name + "info"
                print 'You will be able to  access %s\'s info via the ' \
                    '\'%s\' command' % (name, infocmd)
        onStart.append('alias %s "rsstitles %s"' % (name, url))
        onStart.append('freeze %s' % name)
        if infocmd:
            onStart.append('alias %s "rssinfo %s"' % (infocmd, url))
            onStart.append('freeze %s' % infocmd)
        

class RSS(callbacks.Privmsg):
    threaded = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.lastRequest = {}
        self.cachedFeeds = {}

    def rsstitles(self, irc, msg, args):
        """<url>

        Gets the title components of the given RSS feed.
        """
        url = privmsgs.getArgs(args)
        now = time.time()
        if url not in self.lastRequest or now - self.lastRequest[url] > 1800:
            results = rssparser.parse(url)
            self.cachedFeeds[url] = results
            self.lastRequest[url] = now

        feed = self.cachedFeeds[url]
        headlines = [d['title'].strip().replace('\n', ' ') \
                     for d in feed['items']]
        headlines = map(utils.htmlToText, headlines)
        payload = ircutils.privmsgPayload(headlines, ' :: ')
        if not payload:
            irc.error(msg, 'Error grabbing RSS feed')
            return
        irc.reply(msg, payload)
    
    def rssinfo(self, irc, msg, args):
        """<url>

        Returns information from the given RSS feed, namely the title,
        URL, description, and last update date, if available.
        """
        url = privmsgs.getArgs(args)
        now = time.time()
        if url not in self.lastRequest or now - self.lastRequest[url] > 1800:
            results = rssparser.parse(url)
            self.cachedFeeds[url] = results
            self.lastRequest[url] = now

        feed = self.cachedFeeds[url]
        info = feed['channel']
        if not info:
            irc.error(msg, 'Error grabbing RSS feed')
            return
        # check the 'modified' key, if it's there, convert it here first
        if 'modified' in feed:
            seconds = time.mktime(feed['modified'])
            when = utils.timeElapsed(time.time() - seconds) + ' ago'
        else:
            when = "time unavailable"
        # The rest of the entries are all available in the channel key
        response = 'Title: %s;  URL: <%s>;  ' \
                   'Description: %s;  Last updated %s.' % (
                       info.get('title', 'unavailable').strip(), 
                       info.get('link', 'unavailable').strip(),
                       info.get('description', 'unavailable').strip(),
                       when)
        irc.reply(msg, ' '.join(response.split()))


Class = RSS

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=78:
