###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2010, James McCoy
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

import time
import types
import socket
import threading
import re
import sys
import feedparser

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('RSS')

def getFeedName(irc, msg, args, state):
    if not registry.isValidRegistryName(args[0]):
        state.errorInvalid('feed name', args[0],
                           'Feed names must not include spaces.')
    state.args.append(callbacks.canonicalName(args.pop(0)))
addConverter('feedName', getFeedName)

class RSS(callbacks.Plugin):
    """This plugin is useful both for announcing updates to RSS feeds in a
    channel, and for retrieving the headlines of RSS feeds via command.  Use
    the "add" command to add feeds to this plugin, and use the "announce"
    command to determine what feeds should be announced in a given channel."""
    threaded = True
    def __init__(self, irc):
        self.__parent = super(RSS, self)
        self.__parent.__init__(irc)
        # Schema is feed : [url, command]
        self.feedNames = callbacks.CanonicalNameDict()
        self.locks = {}
        self.lastRequest = {}
        self.cachedFeeds = {}
        self.cachedHeadlines = {}
        self.gettingLockLock = threading.Lock()
        for name in self.registryValue('feeds'):
            self._registerFeed(name)
            try:
                url = self.registryValue(registry.join(['feeds', name]))
            except registry.NonExistentRegistryEntry:
                self.log.warning('%s is not a registered feed, removing.',name)
                continue
            self.makeFeedCommand(name, url)
            self.getFeed(url) # So announced feeds don't announce on startup.

    def isCommandMethod(self, name):
        if not self.__parent.isCommandMethod(name):
            if name in self.feedNames:
                return True
            else:
                return False
        else:
            return True

    def listCommands(self):
        return self.__parent.listCommands(self.feedNames.keys())

    def getCommandMethod(self, command):
        try:
            return self.__parent.getCommandMethod(command)
        except AttributeError:
            return self.feedNames[command[0]][1]

    def _registerFeed(self, name, url=''):
        self.registryValue('feeds').add(name)
        group = self.registryValue('feeds', value=False)
        conf.registerGlobalValue(group, name, registry.String(url, ''))

    def __call__(self, irc, msg):
        self.__parent.__call__(irc, msg)
        irc = callbacks.SimpleProxy(irc, msg)
        newFeeds = {}
        for channel in irc.state.channels:
            feeds = self.registryValue('announce', channel)
            for name in feeds:
                commandName = callbacks.canonicalName(name)
                if self.isCommandMethod(commandName):
                    url = self.feedNames[commandName][0]
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
                                         name=format('Fetching %u', url),
                                         args=(irc, channels, name, url))
                    self.log.info('Checking for announcements at %u', url)
                    world.threadsSpawned += 1
                    t.setDaemon(True)
                    t.start()
                finally:
                    self.releaseLock(url)
                    time.sleep(0.1) # So other threads can run.

    def buildHeadlines(self, headlines, channel, linksconfig='announce.showLinks', dateconfig='announce.showPubDate'):
        newheadlines = []
        for headline in headlines:
            link = ''
            pubDate = ''
            if self.registryValue(linksconfig, channel):
                if headline[1]:
                    if self.registryValue('stripRedirect'):
                        link = re.sub('^.*http://', 'http://', headline[1])
                    else:
                        link = headline[1]
            if self.registryValue(dateconfig, channel):
                if headline[2]:
                    pubDate = ' [%s]' % (headline[2],)
            if sys.version_info[0] < 3:
                if isinstance(headline[0], unicode):
                    newheadlines.append(format('%s %u%s',
                                                headline[0].encode('utf-8','replace'),
                                                link,
                                                pubDate))
                else:
                    newheadlines.append(format('%s %u%s',
                                                headline[0].decode('utf-8','replace'),
                                                link,
                                                pubDate))
            else:
                newheadlines.append(format('%s %u%s',
                                            headline[0],
                                            link,
                                            pubDate))
        return newheadlines

    def _newHeadlines(self, irc, channels, name, url):
        try:
            # We acquire the lock here so there's only one announcement thread
            # in this code at any given time.  Otherwise, several announcement
            # threads will getFeed (all blocking, in turn); then they'll all
            # want to send their news messages to the appropriate channels.
            # Note that we're allowed to acquire this lock twice within the
            # same thread because it's an RLock and not just a normal Lock.
            self.acquireLock(url)
            t = time.time()
            try:
                #oldresults = self.cachedFeeds[url]
                #oldheadlines = self.getHeadlines(oldresults)
                oldheadlines = self.cachedHeadlines[url]
                oldheadlines = list(filter(lambda x: t - x[3] <
                    self.registryValue('announce.cachePeriod'), oldheadlines))
            except KeyError:
                oldheadlines = []
            newresults = self.getFeed(url)
            newheadlines = self.getHeadlines(newresults)
            if len(newheadlines) == 1:
                s = newheadlines[0][0]
                if s in ('Timeout downloading feed.',
                         'Unable to download feed.'):
                    self.log.debug('%s %u', s, url)
                    return
            def normalize(headline):
                return (tuple(headline[0].lower().split()), headline[1])
            oldheadlinesset = set(map(normalize, oldheadlines))
            for (i, headline) in enumerate(newheadlines):
                if normalize(headline) in oldheadlinesset:
                    newheadlines[i] = None
            newheadlines = list(filter(None, newheadlines)) # Removes Nones.
            number_of_headlines = len(oldheadlines)
            oldheadlines.extend(newheadlines)
            self.cachedHeadlines[url] = oldheadlines
            if newheadlines:
                def filter_whitelist(headline):
                    v = False
                    for kw in whitelist:
                        if kw in headline[0] or kw in headline[1]:
                            v = True
                            break
                    return v
                def filter_blacklist(headline):
                    v = True
                    for kw in blacklist:
                        if kw in headline[0] or kw in headline[1]:
                            v = False
                            break
                    return v
                for channel in channels:
                    if  number_of_headlines == 0:
                        channelnewheadlines = newheadlines[:self.registryValue('initialAnnounceHeadlines', channel)]
                    else:
                        channelnewheadlines = newheadlines[:]
                    whitelist = self.registryValue('keywordWhitelist', channel)
                    blacklist = self.registryValue('keywordBlacklist', channel)
                    if len(whitelist) != 0:
                        channelnewheadlines = filter(filter_whitelist, channelnewheadlines)
                    if len(blacklist) != 0:
                        channelnewheadlines = filter(filter_blacklist, channelnewheadlines)
                    channelnewheadlines = list(channelnewheadlines)
                    if len(channelnewheadlines) == 0:
                        return
                    bold = self.registryValue('bold', channel)
                    sep = self.registryValue('headlineSeparator', channel)
                    prefix = self.registryValue('announcementPrefix', channel)
                    suffix = self.registryValue('announcementSeparator', channel)
                    pre = format('%s%s%s', prefix, name, suffix)
                    if bold:
                        pre = ircutils.bold(pre)
                        sep = ircutils.bold(sep)
                    headlines = self.buildHeadlines(channelnewheadlines, channel)
                    irc.replies(headlines, prefixer=pre, joiner=sep,
                                to=channel, prefixNick=False, private=True)
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
        def error(s):
            return {'items': [{'title': s}]}
        try:
            # This is the most obvious place to acquire the lock, because a
            # malicious user could conceivably flood the bot with rss commands
            # and DoS the website in question.
            self.acquireLock(url)
            if self.willGetNewFeed(url):
                results = {}
                try:
                    self.log.debug('Downloading new feed from %u', url)
                    results = feedparser.parse(url)
                    if 'bozo_exception' in results and not results['entries']:
                        raise results['bozo_exception']
                except feedparser.sgmllib.SGMLParseError:
                    self.log.exception('Uncaught exception from feedparser:')
                    raise callbacks.Error('Invalid (unparsable) RSS feed.')
                except socket.timeout:
                    return error('Timeout downloading feed.')
                except Exception as e:
                    # These seem mostly harmless.  We'll need reports of a
                    # kind that isn't.
                    self.log.debug('Allowing bozo_exception %r through.', e)
                if results.get('feed', {}) and self.getHeadlines(results):
                    self.cachedFeeds[url] = results
                    self.lastRequest[url] = time.time()
                else:
                    self.log.debug('Not caching results; feed is empty.')
            try:
                return self.cachedFeeds[url]
            except KeyError:
                wait = self.registryValue('waitPeriod')
                # If there's a problem retrieving the feed, we should back off
                # for a little bit before retrying so that there is time for
                # the error to be resolved.
                self.lastRequest[url] = time.time() - .5 * wait
                return error('Unable to download feed.')
        finally:
            self.releaseLock(url)

    def _getConverter(self, feed):
        toText = utils.web.htmlToText
        if 'encoding' in feed:
            def conv(s):
                # encode() first so there implicit encoding doesn't happen in
                # other functions when unicode and bytestring objects are used
                # together
                s = s.encode(feed['encoding'], 'replace')
                s = toText(s).strip()
                return s
            return conv
        else:
            return lambda s: toText(s).strip()
    def _sortFeedItems(self, items):
        """Return feed items, sorted according to sortFeedItems."""
        order = self.registryValue('sortFeedItems')
        if order not in ['oldestFirst', 'newestFirst']:
            return items
        if order == 'oldestFirst':
            reverse = False
        if order == 'newestFirst':
            reverse = True
        try:
            sitems = sorted(items, key=lambda i: i['updated'], reverse=reverse)
        except KeyError:
            # feedparser normalizes required timestamp fields in ATOM and RSS
            # to the "updated" field. Feeds missing it are unsortable by date.
            return items
        return sitems

    def getHeadlines(self, feed):
        headlines = []
        t = time.time()
        conv = self._getConverter(feed)
        for d in self._sortFeedItems(feed['items']):
            if 'title' in d:
                title = conv(d['title'])
                link = d.get('link')
                pubDate = d.get('pubDate', d.get('updated'))
                headlines.append((title, link, pubDate, t))
        return headlines

    @internationalizeDocstring
    def makeFeedCommand(self, name, url):
        docstring = format("""[<number of headlines>]

        Reports the titles for %s at the RSS feed %u.  If
        <number of headlines> is given, returns only that many headlines.
        RSS feeds are only looked up every supybot.plugins.RSS.waitPeriod
        seconds, which defaults to 1800 (30 minutes) since that's what most
        websites prefer.
        """, name, url)
        if url not in self.locks:
            self.locks[url] = threading.RLock()
        if self.isCommandMethod(name):
            s = format('I already have a command in this plugin named %s.',name)
            raise callbacks.Error(s)
        def f(self, irc, msg, args):
            args.insert(0, url)
            self.rss(irc, msg, args)
        f = utils.python.changeFunctionName(f, name, docstring)
        f = types.MethodType(f, self)
        self.feedNames[name] = (url, f)
        self._registerFeed(name, url)

    @internationalizeDocstring
    def add(self, irc, msg, args, name, url):
        """<name> <url>

        Adds a command to this plugin that will look up the RSS feed at the
        given URL.
        """
        self.makeFeedCommand(name, url)
        irc.replySuccess()
    add = wrap(add, ['feedName', 'url'])

    @internationalizeDocstring
    def remove(self, irc, msg, args, name):
        """<name>

        Removes the command for looking up RSS feeds at <name> from
        this plugin.
        """
        if name not in self.feedNames:
            irc.error(_('That\'s not a valid RSS feed command name.'))
            return
        del self.feedNames[name]
        conf.supybot.plugins.RSS.feeds().remove(name)
        conf.supybot.plugins.RSS.feeds.unregister(name)
        irc.replySuccess()
    remove = wrap(remove, ['feedName'])

    class announce(callbacks.Commands):
        @internationalizeDocstring
        def list(self, irc, msg, args, channel):
            """[<channel>]

            Returns the list of feeds announced in <channel>.  <channel> is
            only necessary if the message isn't sent in the channel itself.
            """
            announce = conf.supybot.plugins.RSS.announce
            feeds = format('%L', list(announce.get(channel)()))
            irc.reply(feeds or _('I am currently not announcing any feeds.'))
        list = wrap(list, ['channel',])

        @internationalizeDocstring
        def add(self, irc, msg, args, channel, feeds):
            """[<channel>] <name|url> [<name|url> ...]

            Adds the list of feeds to the current list of announced feeds in
            <channel>.  Valid feeds include the names of registered feeds as
            well as URLs for RSS feeds.  <channel> is only necessary if the
            message isn't sent in the channel itself.
            """
            announce = conf.supybot.plugins.RSS.announce
            S = announce.get(channel)()
            for feed in feeds:
                S.add(feed)
            announce.get(channel).setValue(S)
            irc.replySuccess()
        add = wrap(add, [('checkChannelCapability', 'op'),
                         many(first('url', 'feedName'))])

        @internationalizeDocstring
        def remove(self, irc, msg, args, channel, feeds):
            """[<channel>] <name|url> [<name|url> ...]

            Removes the list of feeds from the current list of announced feeds
            in <channel>.  Valid feeds include the names of registered feeds as
            well as URLs for RSS feeds.  <channel> is only necessary if the
            message isn't sent in the channel itself.
            """
            announce = conf.supybot.plugins.RSS.announce
            S = announce.get(channel)()
            for feed in feeds:
                S.discard(feed)
            announce.get(channel).setValue(S)
            irc.replySuccess()
        remove = wrap(remove, [('checkChannelCapability', 'op'),
                               many(first('url', 'feedName'))])

    @internationalizeDocstring
    def rss(self, irc, msg, args, url, n):
        """<url> [<number of headlines>]

        Gets the title components of the given RSS feed.
        If <number of headlines> is given, return only that many headlines.
        """
        self.log.debug('Fetching %u', url)
        feed = self.getFeed(url)
        if irc.isChannel(msg.args[0]):
            channel = msg.args[0]
        else:
            channel = None
        headlines = self.getHeadlines(feed)
        if not headlines:
            irc.error(_('Couldn\'t get RSS feed.'))
            return
        headlines = self.buildHeadlines(headlines, channel, 'showLinks', 'showPubDate')
        if n:
            headlines = headlines[:n]
        else:
            headlines = headlines[:self.registryValue('defaultNumberOfHeadlines')]
        sep = self.registryValue('headlineSeparator', channel)
        if self.registryValue('bold', channel):
            sep = ircutils.bold(sep)
        irc.replies(headlines, joiner=sep)
    rss = wrap(rss, ['url', additional('int')])

    @internationalizeDocstring
    def info(self, irc, msg, args, url):
        """<url|feed>

        Returns information from the given RSS feed, namely the title,
        URL, description, and last update date, if available.
        """
        try:
            url = self.registryValue('feeds.%s' % url)
        except registry.NonExistentRegistryEntry:
            pass
        feed = self.getFeed(url)
        conv = self._getConverter(feed)
        info = feed.get('feed')
        if not info:
            irc.error(_('I couldn\'t retrieve that RSS feed.'))
            return
        # check the 'modified_parsed' key, if it's there, convert it here first
        if 'modified' in info:
            seconds = time.mktime(info['modified_parsed'])
            now = time.mktime(time.gmtime())
            when = utils.timeElapsed(now - seconds) + ' ago'
        else:
            when = 'time unavailable'
        title = conv(info.get('title', 'unavailable'))
        desc = conv(info.get('description', 'unavailable'))
        link = conv(info.get('link', 'unavailable'))
        # The rest of the entries are all available in the channel key
        response = format(_('Title: %s;  URL: %u;  '
                          'Description: %s;  Last updated: %s.'),
                          title, link, desc, when)
        irc.reply(utils.str.normalizeWhitespace(response))
    info = wrap(info, [first('url', 'feedName')])
RSS = internationalizeDocstring(RSS)

Class = RSS

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
