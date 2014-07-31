###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2010, James McCoy
# Copyright (c) 2014, Valentin Lorentz
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
import string
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

def get_feedName(irc, msg, args, state):
    if not registry.isValidRegistryName(args[0]):
        state.errorInvalid('feed name', args[0],
                           'Feed names must not include spaces.')
    state.args.append(callbacks.canonicalName(args.pop(0)))
addConverter('feedName', get_feedName)

class Feed:
    __slots__ = ('url', 'name', 'data', 'last_update', 'entries',
            'lock', 'announced_entries')
    def __init__(self, name, url, plugin_is_loading=False):
        assert name, name
        if not url:
            assert utils.web.httpUrlRe.match(name), name
            url = name
        self.name = name
        self.url = url
        self.data = None
        # We don't want to fetch feeds right after the plugin is
        # loaded (the bot could be starting, and thus already busy)
        self.last_update = time.time() if plugin_is_loading else 0
        self.entries = None
        self.lock = threading.Thread()
        self.announced_entries = utils.structures.TruncatableSet()

    def get_command(self, plugin):
        docstring = format(_("""[<number of headlines>]

        Reports the titles for %s at the RSS feed %u.  If
        <number of headlines> is given, returns only that many headlines.
        RSS feeds are only looked up every supybot.plugins.RSS.waitPeriod
        seconds, which defaults to 1800 (30 minutes) since that's what most
        websites prefer."""), self.name, self.url)
        def f(self2, irc, msg, args):
            args.insert(0, self.url)
            self2.rss(irc, msg, args)
        f = utils.python.changeFunctionName(f, self.name, docstring)
        f = types.MethodType(f, plugin)
        return f

def lock_feed(f):
    def newf(feed, *args, **kwargs):
        with feed.lock:
            return f(feed, *args, **kwargs)
    return f

def sort_feed_items(items, order):
    """Return feed items, sorted according to sortFeedItems."""
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

class RSS(callbacks.Plugin):
    """This plugin is useful both for announcing updates to RSS feeds in a
    channel, and for retrieving the headlines of RSS feeds via command.  Use
    the "add" command to add feeds to this plugin, and use the "announce"
    command to determine what feeds should be announced in a given channel."""
    threaded = True
    def __init__(self, irc):
        self.__parent = super(RSS, self)
        self.__parent.__init__(irc)
        # Scheme: {name: url}
        self.feed_names = callbacks.CanonicalNameDict()
        # Scheme: {url: feed}
        self.feeds = {}
        for name in self.registryValue('feeds'):
            self.assert_feed_does_not_exist(name)
            self.register_feed_config(name)
            try:
                url = self.registryValue(registry.join(['feeds', name]))
            except registry.NonExistentRegistryEntry:
                self.log.warning('%s is not a registered feed, removing.',name)
                continue
            self.register_feed(name, url, True)

    ##################
    # Feed registering

    def assert_feed_does_not_exist(self, name):
        if self.isCommandMethod(name):
            s = format('I already have a command in this plugin named %s.',name)
            raise callbacks.Error(s)

    def register_feed_config(self, name, url=''):
        self.registryValue('feeds').add(name)
        group = self.registryValue('feeds', value=False)
        conf.registerGlobalValue(group, name, registry.String(url, ''))

    def register_feed(self, name, url, plugin_is_loading):
        self.feed_names[name] = url
        self.feeds[url] = Feed(name, url, plugin_is_loading)

    def remove_feed(self, feed):
        del self.feed_names[feed.name]
        del self.feeds[feed.url]
        conf.supybot.plugins.RSS.feeds().remove(feed.name)
        conf.supybot.plugins.RSS.feeds.unregister(feed.name)

    ##################
    # Methods handling

    def isCommandMethod(self, name):
        if not self.__parent.isCommandMethod(name):
            return bool(self.get_feed(name))
        else:
            return True

    def listCommands(self):
        return self.__parent.listCommands(self.feeds.keys())

    def getCommandMethod(self, command):
        try:
            return self.__parent.getCommandMethod(command)
        except AttributeError:
            return self.get_feed(command[0]).get_command(self)

    def __call__(self, irc, msg):
        self.__parent.__call__(irc, msg)
        self.update_feeds()


    ##################
    # Status accessors

    def get_feed(self, name):
        return self.feeds.get(self.feed_names.get(name, name), None)

    def is_expired(self, feed):
        assert feed
        event_horizon = time.time() - self.registryValue('waitPeriod')
        return feed.last_update < event_horizon


    ###############
    # Feed fetching

    @lock_feed
    def update_feed(self, feed):
        d = feedparser.parse(feed.url)
        feed.data = d.feed
        feed.entries = d.entries
        self.announce_feed(feed)

    def update_feed_in_thread(self, feed):
        feed.last_update = time.time()
        t = world.SupyThread(target=self.update_feed,
                             name=format('Fetching feed %u', feed.url),
                             args=(feed,))
        t.setDaemon(True)
        t.start()

    def update_feed_if_needed(self, feed):
        if self.is_expired(feed):
            self.update_feed(feed)

    def update_feeds(self):
        for name in self.registryValue('feeds'):
            self.update_feed_if_needed(self.get_feed(name))

    @lock_feed
    def announce_feed(self, feed):
        entries = feed.entries
        new_entries = [entry for entry in entries
                if entry.id not in feed.announced_entries]
        if not new_entries:
            return

        order = self.registryValue('sortFeedItems')
        new_entries = sort_feed_items(new_entries, order)
        for irc in world.ircs:
            for channel in irc.state.channels:
                if feed.name not in self.registryValue('announce', channel):
                    continue
                for entry in new_entries:
                    self.announce_entry(irc, channel, feed, entry)
        feed.announced_entries |= {entry.id for entry in new_entries}
        # We keep a little more because we don't want to re-announce
        # oldest entries if one of the newest gets removed.
        feed.announced_entries.truncate(2*len(entries))


    #################
    # Entry rendering

    def should_send_entry(self, channel, entry):
        whitelist = self.registryValue('keywordWhitelist', channel)
        blacklist = self.registryValue('keywordBlacklist', channel)
        if whitelist:
            if all(kw not in entry.title and kw not in entry.description
                   for kw in whitelist):
                return False
        if blacklist:
            if any(kw in entry.title or kw in entry.description
                   for kw in blacklist):
                return False
        return True

    def format_entry(self, channel, feed, entry, is_announce):
        if is_announce:
            template = self.registryValue('announceFormat', channel)
        else:
            template = self.registryValue('format', channel)
        date = entry.get('published_parsed', entry.get('updated_parsed'))
        date = utils.str.timestamp(date)
        return string.Template(template).safe_substitute(template,
                feed_name=feed.name,
                date=date,
                **entry)

    def announce_entry(self, irc, channel, feed, entry):
        if self.should_send_entry(channel, entry):
            s = format_entry(channel, feed, entry, True)
            irc.sendMsg(ircmsgs.privmsg(channel, s))


    ##########
    # Commands

    @internationalizeDocstring
    def add(self, irc, msg, args, name, url):
        """<name> <url>

        Adds a command to this plugin that will look up the RSS feed at the
        given URL.
        """
        self.assert_feed_does_not_exist(name)
        self.register_feed_config(name, url)
        self.register_feed(name, url, False)
        irc.replySuccess()
    add = wrap(add, ['feedName', 'url'])

    @internationalizeDocstring
    def remove(self, irc, msg, args, name):
        """<name>

        Removes the command for looking up RSS feeds at <name> from
        this plugin.
        """
        feed = self.get_feed(name)
        if not feed:
            irc.error(_('That\'s not a valid RSS feed command name.'))
            return
        self.remove_feed(feed)
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
        feed = self.get_feed(url)
        if not feed:
            feed = Feed(url, url)
        if irc.isChannel(msg.args[0]):
            channel = msg.args[0]
        else:
            channel = None
        self.update_feed_if_needed(feed)
        entries = feed.entries
        if not entries:
            irc.error(_('Couldn\'t get RSS feed.'))
            return
        n = n or self.registryValue('defaultNumberOfHeadlines', channel)
        entries = list(filter(lambda e:self.should_send_entry(channel, e),
                              feed.entries))
        entries = entries[:n]
        headlines = map(lambda e:self.format_entry(channel, feed, e, False),
                        entries)
        sep = self.registryValue('headlineSeparator', channel)
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
        feed = self.get_feed(url)
        self.update_feed_if_needed(feed)
        info = feed.data
        if not info:
            irc.error(_('I couldn\'t retrieve that RSS feed.'))
            return
        # check the 'modified_parsed' key, if it's there, convert it here first
        if 'modified' in info:
            seconds = time.mktime(info['modified_parsed'])
            now = time.mktime(time.gmtime())
            when = utils.timeElapsed(now - seconds) + ' ago'
        else:
            when = _('time unavailable')
        title = info.get('title', _('unavailable'))
        desc = info.get('description', _('unavailable'))
        link = info.get('link', _('unavailable'))
        # The rest of the entries are all available in the channel key
        response = format(_('Title: %s;  URL: %u;  '
                          'Description: %s;  Last updated: %s.'),
                          title, link, desc, when)
        irc.reply(utils.str.normalizeWhitespace(response))
    info = wrap(info, [first('url', 'feedName')])
RSS = internationalizeDocstring(RSS)

Class = RSS

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
