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
Provides basic functionality for handling RSS/RDF feeds.
"""

__revision__ = "$Id$"

import plugins

import sets
import time
import sgmllib
import threading
from itertools import imap

import rssparser

import conf
import utils
import world
import ircmsgs
import ircutils
import privmsgs
import registry
import callbacks

def configure(advanced):
    from questions import output, expect, anything, something, yn
    conf.registerPlugin('RSS', True)
    prompt = 'Would you like to add an RSS feed?'
    while yn(prompt):
        prompt = 'Would you like to add another RSS feed?'
        name = something('What\'s the name of the website?')
        url = something('What\'s the URL of the RSS feed?')
        registerFeed(name, url)

conf.registerPlugin('RSS')
conf.registerChannelValue(conf.supybot.plugins.RSS, 'bold', registry.Boolean(
    True, """Determines whether the bot will bold the title of the feed when it
    announces new news."""))
conf.registerChannelValue(conf.supybot.plugins.RSS, 'headlineSeparator',
    registry.StringSurroundedBySpaces(' || ', """Determines what string is used
    to separate headlines in new feeds."""))
conf.registerChannelValue(conf.supybot.plugins.RSS, 'announcementPrefix',
    registry.StringWithSpaceOnRight('New news from ', """Determines what prefix
    is prepended (if any) to the new news item announcements made in the
    channel."""))
conf.registerChannelValue(conf.supybot.plugins.RSS, 'announce',
    registry.SpaceSeparatedListOfStrings([], """Determines which RSS feeds
    should be announced in the channel; valid input is a list of strings
    (either registered RSS feeds or RSS feed URLs) separated by spaces."""))
conf.registerGlobalValue(conf.supybot.plugins.RSS, 'waitPeriod',
    registry.PositiveInteger(1800, """Indicates how many seconds the bot will
    wait between retrieving RSS feeds; requests made within this period will
    return cached results."""))
conf.registerGroup(conf.supybot.plugins.RSS, 'feeds')
conf.supybot.plugins.RSS.feeds.help = utils.normalizeWhitespace("""These are
the registered feeds for the RSS plugin.""")

def registerFeed(name, url):
    conf.supybot.plugins.RSS.feeds.register(name, registry.String(url, ''))
    
class RSS(callbacks.Privmsg):
    threaded = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.feedNames = sets.Set()
        self.locks = {}
        self.lastRequest = {}
        self.cachedFeeds = {}
        self.gettingLockLock = threading.Lock()
        for (name, url) in registry._cache.iteritems():
            name = name.lower()
            if name.startswith('supybot.plugins.rss.feeds.'):
                name = rsplit(name, '.', 1)[-1]
                v = registry.String('', 'help is not needed here')
                v.set(url)
                url = v()
                self.makeFeedCommand(name, url)

    def __call__(self, irc, msg):
        callbacks.Privmsg.__call__(self, irc, msg)
        irc = callbacks.IrcObjectProxyRegexp(irc, msg)
        L = conf.supybot.plugins.RSS.announce.getValues(fullNames=False)
        newFeeds = {}
        for (channel, v) in L:
            feeds = v() 
            for name in feeds:
                commandName = callbacks.canonicalName(name)
                if self.isCommand(commandName):
                    name = commandName
                    url = self.getCommand(name).url
                else:
                    url = name
                if self.willGetNewFeed(url):
                    newFeeds.setdefault((url, name), []).append(channel)
        for ((url, name), channels) in newFeeds.iteritems():
            # We check if we can acquire the lock right here because if we
            # don't, we'll possibly end up spawning a lot of threads to get
            # the feed, because this thread may run for a number of bytecodes
            # before it switches to a thread that'll get the lock in
            # _newHeadlines.
            if self.acquireLock(url, blocking=False):
                try:
                    t = threading.Thread(target=self._newHeadlines,
                                         name='Fetching <%s>' % url,
                                         args=(irc, channels, name, url))
                    self.log.info('Spawning thread to fetch <%s>', url)
                    world.threadsSpawned += 1
                    t.setDaemon(True)
                    t.start()
                finally:
                    self.releaseLock(url)
                    time.sleep(0.1) # So other threads can run.

    def _newHeadlines(self, irc, channels, name, url):
        try:
            # We acquire the lock here so there's only one announcement thread
            # in this code at any given time.  Otherwise, several announcement
            # threads will getFeed (all blocking, in turn); then they'll all
            # want to sent their news messages to the appropriate channels.
            # Note that we're allowed to acquire this lock twice within the
            # same thread because it's an RLock and not just a normal Lock.
            self.acquireLock(url)
            try:
                oldresults = self.cachedFeeds[url]
                oldheadlines = self.getHeadlines(oldresults)
            except KeyError:
                oldheadlines = []
            newresults = self.getFeed(url)
            newheadlines = self.getHeadlines(newresults)
            def headlineEq(h1, h2):
                return h1.lower().split() == h2.lower().split()
            for (i, oldheadline) in enumerate(oldheadlines):
                try:
                    newheadline = newheadlines[i]
                except IndexError:
                    break
                if headlineEq(oldheadline, newheadline):
                    newheadlines[i] = None
            newheadlines = filter(None, newheadlines) # Removes Nones.
            if newheadlines:
                for channel in channels:
                    bold = self.registryValue('bold', channel)
                    sep = self.registryValue('headlineSeparator', channel)
                    prefix = self.registryValue('announcementPrefix', channel)
                    pre = '%s%s: ' % (prefix, name)
                    if bold:
                        pre = ircutils.bold(pre)
                    irc.replies(newheadlines, prefixer=pre, joiner=sep,
                                to=channel, prefixName=False, private=True)
        finally:
            self.releaseLock(url)
                
    def willGetNewFeed(self, url):
        now = time.time()
        wait = self.registryValue('waitPeriod')
        if url not in self.lastRequest or now - self.lastRequest[url] > wait:
            return True
        else:
            return False

    def acquireLock(self, url, blocking=True):
        try:
            self.gettingLockLock.acquire()
            try:
                lock = self.locks[url]
            except KeyError:
                lock = threading.RLock()
                self.locks[url] = lock
            return lock.acquire(blocking=blocking)
        finally:
            self.gettingLockLock.release()

    def releaseLock(self, url):
        self.locks[url].release()
            
    def getFeed(self, url):
        try:
            # This is the most obvious place to acquire the lock, because a
            # malicious user could conceivably flood the bot with rss commands
            # and DoS the website in question.
            self.acquireLock(url)
            if self.willGetNewFeed(url):
                try:
                    self.log.info('Downloading new feed from <%s>', url)
                    results = rssparser.parse(url)
                except sgmllib.SGMLParseError:
                    self.log.exception('Uncaught exception from rssparser:')
                    raise callbacks.Error, 'Invalid (unparseable) RSS feed.'
                self.cachedFeeds[url] = results
                self.lastRequest[url] = time.time()
            try:
                return self.cachedFeeds[url]
            except KeyError:
                self.lastRequest[url] = 0
                return {'items': [{'title': 'Unable to download feed.'}]}
        finally:
            self.releaseLock(url)

    def getHeadlines(self, feed):
        return [utils.htmlToText(d['title'].strip()) for d in feed['items']]

    def makeFeedCommand(self, name, url):
        docstring = """<number of headlines>

        Reports the titles for %s at the RSS feed <%s>.  If
        <number of headlines> is given, returns only that many headlines.
        RSS feeds are only looked up every supybot.plugins.RSS.waitPeriod
        seconds, which defaults to 1800 (30 minutes) since that's what most
        websites prefer.
        """ % (name, url)
        name = callbacks.canonicalName(name)
        if url not in self.locks:
            self.locks[url] = threading.RLock()
        if hasattr(self, name):
            s = 'I already have a command in this plugin named %s' % name
            raise callbacks.Error, s
        def f(self, irc, msg, args):
            args.insert(0, url)
            self.rss(irc, msg, args)
        f = utils.changeFunctionName(f, name, docstring)
        f.url = url # Used by __call__.
        self.feedNames.add(name)
        setattr(self.__class__, name, f)
        registerFeed(name, url)
        
    def add(self, irc, msg, args):
        """<name> <url>

        Adds a command to this plugin that will look up the RSS feed at the
        given URL.
        """
        (name, url) = privmsgs.getArgs(args, required=2)
        self.makeFeedCommand(name, url)
        irc.replySuccess()

    def remove(self, irc, msg, args):
        """<name>

        Removes the command for looking up RSS feeds at <name> from
        this plugin.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if name not in self.feedNames:
            irc.error('That\'s not a valid RSS feed command name.')
            return
        delattr(self.__class__, name)
        irc.replySuccess()

    def announce(self, irc, msg, args, channel):
        """[<channel>] [<name|url> ...]

        Sets the current list of announced feeds in the channel to the feeds
        given.  Valid feeds include the names of registered feeds as well as
        URLs for a RSS feeds.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        conf.supybot.plugins.RSS.announce.get(channel).setValue(args)
        if not args:
            irc.replySuccess('All previous announced feeds removed.')
        else:
            irc.replySuccess()
    announce = privmsgs.checkChannelCapability(announce, 'op')
            
    def rss(self, irc, msg, args):
        """<url> [<number of headlines>]

        Gets the title components of the given RSS feed.
        If <number of headlines> is given, return only that many headlines.
        """
        (url, n) = privmsgs.getArgs(args, optional=1)
        self.log.debug('Fetching %s', url)
        feed = self.getFeed(url)
        if ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
        else:
            channel = None
        headlines = self.getHeadlines(feed)
        if not headlines:
            irc.error('Couldn\'t get RSS feed')
            return
        if n:
            try:
                n = int(n)
            except ValueError:
                raise callbacks.Error
            headlines = headlines[:n]
        headlines = imap(utils.htmlToText, headlines)
        sep = self.registryValue('headlineSeparator', channel)
        irc.reply(sep.join(headlines))

    def info(self, irc, msg, args):
        """<url|feed>

        Returns information from the given RSS feed, namely the title,
        URL, description, and last update date, if available.
        """
        url = privmsgs.getArgs(args)
        try:
            url = self.registryValue('feeds.%s' % url)
        except registry.NonExistentRegistryEntry:
            pass
        feed = self.getFeed(url)
        info = feed['channel']
        if not info:
            irc.error('I couldn\'t retrieve that RSS feed.')
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
        irc.reply(' '.join(response.split()))


Class = RSS

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=78:
