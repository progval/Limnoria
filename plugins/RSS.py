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
module for user-friendliness.
"""

__revision__ = "$Id$"

import plugins

import sets
import time
import types
from itertools import imap

import rssparser

import conf
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks
import configurable

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, something, yn
    onStart.append('load RSS')
    prompt = 'Would you like to add an RSS feed?'
    while yn(prompt) == 'y':
        prompt = 'Would you like to add another RSS feed?'
        name = something('What\'s the name of the website?')
        url = something('What\'s the URL of the RSS feed?')
        onStart.append('rss add %s %s' % (name, url))
        #onStart.append('alias lock %s' % name)

def SpaceOnRightStrType(s):
    s = configurable.StrType(s)
    if s.rstrip() == s:
        s += ' '
    return s

class RSS(callbacks.Privmsg, configurable.Mixin):
    threaded = True
    configurables = configurable.Dictionary(
        [('announce-news-feeds', configurable.SpaceSeparatedStrListType,
          [], """Gives the bot a space-separated list of feeds for which it
          should announce updates to the channel.  The feeds should be
          either URLs or names of feeds already added to this plugin."""),
         ('announce-news-bold', configurable.BoolType, True,
          """Determines whether the bot will bold the title of the feed when
          it announces new additions."""),
         ('headline-separator', configurable.SpaceSurroundedStrType, ' :: ',
          """Determines what string is used to seperate headlines in
          feeds."""),
         ('announce-news-prefix', SpaceOnRightStrType,
          'New news from ',
          """Sets the prefix to be added (if any) to the new news item
          announcements made to the channel."""),]
    )
    globalConfigurables = configurable.Dictionary(
         [('wait-period', configurable.PositiveIntType, 1800,
          """Indicates how many seconds the bot will wait between retrieving
          RSS feeds; requests made within this period will return cached
          results."""),]
    )
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.feedNames = sets.Set()
        self.lastRequest = {}
        self.cachedFeeds = {}

    def __call__(self, irc, msg):
        callbacks.Privmsg.__call__(self, irc, msg)
        feeds = self.configurables.getChannels('announce-news-feeds')
        for (channel, d) in feeds.iteritems():
            sep = self.configurables.get('headline-separator', channel)
            bold = self.configurables.get('announce-news-bold', channel)
            prefix = self.configurables.get('announce-news-prefix', channel)
            for name in d:
                if self.isCommand(name):
                    url = self.getCommand(name).url
                else:
                    url = name
                try:
                    oldresults = self.cachedFeeds[url]
                    oldheadlines = self.getHeadlines(oldresults)
                except KeyError:
                    oldheadlines = []
                newresults = self.getFeed(url)
                newheadlines = self.getHeadlines(newresults)
                for headline in oldheadlines:
                    try:
                        newheadlines.remove(headline)
                    except ValueError:
                        pass
                if newheadlines:
                    pre = prefix + name
                    if bold:
                        pre = ircutils.bold(pre)
                    headlines = sep.join(newheadlines)
                    s = '%s: %s' % (pre, headlines)
                    irc.queueMsg(ircmsgs.privmsg(channel, s))
                
    def getFeed(self, url):
        now = time.time()
        wait = self.globalConfigurables.get('wait-period')
        if url not in self.lastRequest or now - self.lastRequest[url] > wait:
            try:
                self.log.info('Downloading new feed from %s', url)
                results = rssparser.parse(url)
            except sgmllib.SGMLParseError:
                self.log.exception('Uncaught exception from rssparser:')
                raise callbacks.Error, 'Invalid (unparseable) RSS feed.'
            self.cachedFeeds[url] = results
            self.lastRequest[url] = now
        return self.cachedFeeds[url]

    def getHeadlines(self, feed):
        return [utils.htmlToText(d['title'].strip()) for d in feed['items']]

    def add(self, irc, msg, args):
        """<name> <url>

        Adds a command to this plugin that will look up the RSS feed at the
        given URL.
        """
        (name, url) = privmsgs.getArgs(args, required=2)
        docstring = """takes no arguments

        Reports the titles for %s at the RSS feed <%s>.  RSS feeds are only
        looked up every half hour at the most (since that's how most
        websites prefer it).
        """ % (name, url)
        name = callbacks.canonicalName(name)
        if hasattr(self, name):
            s = 'I already have a command in this plugin named %s' % name
            irc.error(msg, s)
            return
        def f(self, irc, msg, args):
            args.insert(0, url)
            self.rss(irc, msg, args)
        f = types.FunctionType(f.func_code, f.func_globals,
                               name, closure=f.func_closure)
        f.__doc__ = docstring
        f.url = url # Used by __call__.
        self.feedNames.add(name)
        setattr(self.__class__, name, f)
        irc.reply(msg, conf.replySuccess)

    def remove(self, irc, msg, args):
        """<name>

        Removes the command for looking up RSS feeds at <name> from
        this plugin.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if name not in self.feedNames:
            irc.error(msg, 'That\'s not a valid RSS feed command name.')
            return
        delattr(self.__class__, name)
        irc.reply(msg, conf.replySuccess)
        
    def rss(self, irc, msg, args):
        """<url>

        Gets the title components of the given RSS feed.
        """
        url = privmsgs.getArgs(args)
        feed = self.getFeed(url)
        if ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
        else:
            channel = None
        headlines = self.getHeadlines(feed)
        if not headlines:
            irc.error(msg, 'Couldn\'t get RSS feed')
            return
        headlines = imap(utils.htmlToText, headlines)
        sep = self.configurables.get('headline-separator', channel)
        irc.reply(msg, sep.join(headlines))

    def info(self, irc, msg, args):
        """<url>

        Returns information from the given RSS feed, namely the title,
        URL, description, and last update date, if available.
        """
        url = privmsgs.getArgs(args)
        feed = self.getFeed(url)
        info = feed['channel']
        if not info:
            irc.error(msg, 'I couldn\'t retrieve that RSS feed.')
            return
        # check the 'modified' key, if it's there, convert it here first
        if 'modified' in feed:
            seconds = time.mktime(feed['modified'])
            now = time.mktime(time.gmtime())
            when = utils.timeElapsed(now - seconds) + ' ago'
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
