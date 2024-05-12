###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2010, James McCoy
# Copyright (c) 2010-2021, Valentin Lorentz
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

import re
import os
import sys
import json
import time
import types
import string
import socket
import threading
import feedparser

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('RSS')

if world.testing:
    INIT_DELAY = 1
else:
    INIT_DELAY = 10

if minisix.PY2:
    from urllib2 import ProxyHandler
else:
    from urllib.request import ProxyHandler

from .config import register_feed_config

def get_feedName(irc, msg, args, state):
    if irc.isChannel(args[0]):
        state.errorInvalid('feed name', args[0], 'must not be channel names.')
    if not registry.isValidRegistryName(args[0]):
        state.errorInvalid('feed name', args[0],
                           'Feed names must not include spaces.')
    if "." in args[0]:
        state.errorInvalid('feed name', args[0],
                           'Feed names must not include dots.')
    state.args.append(callbacks.canonicalName(args.pop(0)))
addConverter('feedName', get_feedName)

announced_headlines_filename = \
        conf.supybot.directories.data.dirize('RSS_announced.flat')

def only_one_at_once(f):
    lock = [False]
    def newf(*args, **kwargs):
        if lock[0]:
            return
        lock[0] = True
        try:
            f(*args, **kwargs)
        finally:
            lock[0] = False
    return newf

def get_entry_id(entry):
    # in order, try elements to use as unique identifier.
    # http://validator.w3.org/feed/docs/rss2.html#hrelementsOfLtitemgt
    id_elements = ('id', 'link', 'title', 'description')
    for id_element in id_elements:
        try:
            return getattr(entry, id_element)
        except AttributeError:
            pass
    raise ValueError('Feed entry is missing both title and description')

class InvalidFeedUrl(ValueError):
    pass

class Feed:
    __slots__ = ('url', 'name', 'data', 'last_update', 'entries',
            'etag', 'modified', 'initial',
            'lock', 'announced_entries', 'last_exception')
    def __init__(self, name, url, initial,
            plugin_is_loading=False, announced=None):
        assert name, name
        if not url:
            url = name
        if not utils.web.httpUrlRe.match(url):
            raise InvalidFeedUrl(url)
        self.name = name
        self.url = url
        self.initial = initial
        self.data = None
        # We don't want to fetch feeds right after the plugin is
        # loaded (the bot could be starting, and thus already busy)
        self.last_update = 0
        self.entries = []
        self.etag = None
        self.modified = None
        self.lock = threading.Lock()
        self.announced_entries = announced or \
                utils.structures.TruncatableSet()
        self.last_exception = None

    def __repr__(self):
        return 'Feed(%r, %r, %r, <bool>, %r)' % \
                (self.name, self.url, self.initial, self.announced_entries)

    def get_command(self, plugin):
        docstring = format(_("""[<number of headlines>]

        Reports the titles for %s at the RSS feed %u.  If
        <number of headlines> is given, returns only that many headlines.
        RSS feeds are only looked up every supybot.plugins.RSS.waitPeriod
        seconds, which defaults to 1800 (30 minutes) since that's what most
        websites prefer."""), self.name, self.url)
        def f(self2, irc, msg, args):
            args.insert(0, self.name)
            self2.rss(irc, msg, args)
        f = utils.python.changeFunctionName(f, self.name, docstring)
        f = types.MethodType(f, plugin)
        return f

_sort_parameters = {
        'oldestFirst':   (('published_parsed', 'updated_parsed'), False),
        'newestFirst':   (('published_parsed', 'updated_parsed'), True),
        'outdatedFirst': (('updated_parsed', 'published_parsed'), False),
        'updatedFirst':  (('updated_parsed', 'published_parsed'), True),
        }
def _sort_arguments(order):
    (fields, reverse) = _sort_parameters[order]
    def key(entry):
        for field in fields:
            if field in entry:
                return entry[field]
        raise KeyError('No date field in entry.')
    return (key, reverse)

def sort_feed_items(items, order):
    """Return feed items, sorted according to sortFeedItems."""
    if order == 'asInFeed':
        return items
    (key, reverse) = _sort_arguments(order)
    try:
        sitems = sorted(items, key=key, reverse=reverse)
    except KeyError:
        # feedparser normalizes required timestamp fields in ATOM and RSS
        # to the "published"/"updated" fields. Feeds missing it are unsortable by date.
        return items
    return sitems

def load_announces_db(fd):
    return dict((name, utils.structures.TruncatableSet(entries))
                for (name, entries) in json.load(fd).items())
def save_announces_db(db, fd):
    json.dump(dict((name, list(entries)) for (name, entries) in db), fd)


class RSS(callbacks.Plugin):
    """
    This plugin is useful both for announcing updates to RSS feeds in a
    channel, and for retrieving the headlines of RSS feeds via command.  Use
    the "add" command to add feeds to this plugin, and use the "announce"
    command to determine what feeds should be announced in a given channel.

    Basic usage
    ^^^^^^^^^^^

    1. Add a feed using
       ``@rss add limnoria https://github.com/progval/Limnoria/tags.atom``.

       * This is RSS feed of Limnoria's stable releases.
       * You can now check the latest news from the feed with ``@limnoria``.

    2. To have new news automatically announced on the channel, use
       ``@rss announce add Limnoria``.

    To add another feed, simply replace limnoria and the address using name
    of the feed and address of the feed. For example, YLE News:

    1. ``@rss add yle http://yle.fi/uutiset/rss/uutiset.rss?osasto=news``
    2. ``@rss announce add yle``

    News on their own lines
    ^^^^^^^^^^^^^^^^^^^^^^^

    If you want the feed topics to be on their own lines instead of being separated by
    the separator which you have configured you can set `reply.onetoone` to False.

    Please first read the help for that configuration variable

    ``@config help reply.onetoone``

    and understand what it says and then you can do

    ``@config reply.onetoone False``

    """
    threaded = True
    def __init__(self, irc):
        self.__parent = super(RSS, self)
        self.__parent.__init__(irc)

        if world.starting:
            self._init_time = time.time() # To delay loading the feeds
        else:
            self._init_time = 0

        # Scheme: {name: url}
        self.feed_names = callbacks.CanonicalNameDict()
        # Scheme: {url: feed}
        self.feeds = {}
        if os.path.isfile(announced_headlines_filename):
            with open(announced_headlines_filename) as fd:
                announced = load_announces_db(fd)
        else:
            announced = {}
        for name in self.registryValue('feeds'):
            try:
                url = self.registryValue(registry.join(['feeds', name]))
            except registry.NonExistentRegistryEntry:
                self.log.warning('%s is not a registered feed, removing.',name)
                continue
            try:
                self.register_feed(name, url, True, True, announced.get(name, []))
            except InvalidFeedUrl:
                self.log.error('%s is not a valid feed, removing.', name)
                continue
        world.flushers.append(self._flush)

    def die(self):
        self._flush()
        world.flushers.remove(self._flush)
        self.__parent.die()

    def _flush(self):
        l = [(f.name, f.announced_entries) for f in self.feeds.values()]
        with utils.file.AtomicFile(announced_headlines_filename, 'w',
                                   backupDir='/dev/null') as fd:
            save_announces_db(l, fd)


    ##################
    # Feed registering

    def assert_feed_does_not_exist(self, name, url=None):
        if self.isCommandMethod(name):
            s = format(_('I already have a command in this plugin named %s.'),
                    name)
            raise callbacks.Error(s)
        if url:
            feed = self.feeds.get(url)
            if feed and feed.name != feed.url and feed.name in self.feed_names:
                s = format(_('I already have a feed with that URL named %s.'),
                        feed.name)
                raise callbacks.Error(s)

    def register_feed(self, name, url, initial,
            plugin_is_loading, announced=None):
        if name != url:
            # If name == url, then it's an anonymous feed
            self.feed_names[name] = url
        self.feeds[url] = Feed(name, url, initial,
                plugin_is_loading, announced)

    def remove_feed(self, name_or_url):
        self.feed_names.pop(name_or_url, None)
        while True:
            try:
                conf.supybot.plugins.RSS.feeds().remove(name_or_url)
            except KeyError:
                break
        try:
            conf.supybot.plugins.RSS.feeds.unregister(name_or_url)
        except (KeyError, registry.NonExistentRegistryEntry):
            pass

    ##################
    # Methods handling

    def isCommandMethod(self, name):
        if not self.__parent.isCommandMethod(name):
            return bool(self.get_feed(name))
        else:
            return True

    def listCommands(self):
        return self.__parent.listCommands(self.feed_names.keys())

    def getCommandMethod(self, command):
        try:
            return self.__parent.getCommandMethod(command)
        except AttributeError:
            return self.get_feed(command[0]).get_command(self)

    def __call__(self, irc, msg):
        self.__parent.__call__(irc, msg)
        threading.Thread(target=self.update_feeds).start()


    ##################
    # Status accessors

    def get_feed(self, name):
        return self.feeds.get(self.feed_names.get(name, name), None)

    def is_expired(self, feed):
        assert feed
        period = self.registryValue('waitPeriod')
        if feed.name != feed.url: # Named feed
            specific_period = self.registryValue('feeds.%s.waitPeriod' % feed.name)
            if specific_period:
                period = specific_period
        event_horizon = time.time() - period
        return feed.last_update < event_horizon

    ###############
    # Feed fetching

    @log.firewall
    def update_feed(self, feed):
        handlers = []
        if utils.web.proxy():
            handlers.append(ProxyHandler(
                {'http': utils.force(utils.web.proxy())}))
            handlers.append(ProxyHandler(
                {'https': utils.force(utils.web.proxy())}))
        with feed.lock:
            try:
                d = feedparser.parse(feed.url, etag=feed.etag,
                        modified=feed.modified, handlers=handlers)
            except socket.error as e:
                self.log.warning("Network error while fetching <%s>: %s",
                               feed.url, e)
                feed.last_exception = e
                return
            except http.client.HTTPException as e:
                self.log.warning("HTTP error while fetching <%s>: %s",
                               feed.url, e)
                feed.last_exception = e
                return
            except Exception as e:
                self.log.error("Failed to fetch <%s>: %s", feed.url, e)
                raise  # reraise so @log.firewall prints the traceback
            if 'status' not in d or d.status != 304: # Not modified
                if 'etag' in d:
                    feed.etag = d.etag
                if 'modified' in d:
                    feed.modified = d.modified
                feed.data = d.feed
                feed.entries = d.entries
                feed.last_update = time.time()
                # feedparser will store soft errors in bozo_exception and set
                # the "bozo" bit to 1 on supported platforms:
                # https://pythonhosted.org/feedparser/bozo.html
                # If this error caused us to e.g. not get any entries at all,
                # it may be helpful to show it as well.
                if getattr(d, 'bozo', 0) and hasattr(d, 'bozo_exception'):
                    feed.last_exception = d.bozo_exception
                else:
                    feed.last_exception = None

            (initial, feed.initial) = (feed.initial, False)
        self.announce_feed(feed, initial)

    def update_feed_if_needed(self, feed):
        if self.is_expired(feed) and \
                self._init_time + INIT_DELAY < time.time():
            self.update_feed(feed)

    @only_one_at_once
    def update_feeds(self):
        announced_feeds = {}
        for irc in world.ircs:
            for channel in list(irc.state.channels):
                channel_feed_names = self.registryValue(
                    'announce', channel, irc.network)
                for name in channel_feed_names:
                    announced_feeds[name] = (channel, irc.network)
        for (name, (channel, network)) in announced_feeds.items():
            feed = self.get_feed(name)
            if not feed:
                self.log.warning(
                    'Feed %s is announced in %s@%s, but does not exist. '
                    'Use "rss announce remove %s %s" to remove it from '
                    'announcements.',
                    name, channel, network, channel, name)
                continue
            self.update_feed_if_needed(feed)

    def get_new_entries(self, feed):
        with feed.lock:
            entries = feed.entries
            new_entries = [entry for entry in entries
                    if get_entry_id(entry) not in feed.announced_entries]
            if not new_entries:
                return []
            feed.announced_entries |= set(get_entry_id(entry) for entry in new_entries)
            # We keep a little more because we don't want to re-announce
            # oldest entries if one of the newest gets removed.
            feed.announced_entries.truncate(10*len(entries))
        return new_entries

    def announce_feed(self, feed, initial):
        new_entries = self.get_new_entries(feed)

        order = self.registryValue('sortFeedItems')
        new_entries = sort_feed_items(new_entries, 'newestFirst')
        for irc in world.ircs:
            for channel in list(irc.state.channels):
                # Old bots have it set in plugins.RSS.announce.#channel,
                # new bots set it in plugins.RSS.announce.:network.#channel,
                # so we want to read from both.
                channel_feeds = self.registryValue('announce', channel) \
                    | self.registryValue('announce', channel, irc.network)
                if feed.name not in channel_feeds:
                    continue
                if initial:
                    max_entries = self.registryValue(
                        'initialAnnounceHeadlines', channel, irc.network)
                else:
                    max_entries = self.registryValue(
                        'maximumAnnounceHeadlines', channel, irc.network)
                announced_entries = new_entries[0:max_entries]
                announced_entries = sort_feed_items(announced_entries, order)
                for entry in announced_entries:
                    self.announce_entry(irc, channel, feed, entry)


    #################
    # Entry rendering

    def should_send_entry(self, network, channel, entry):
        whitelist = self.registryValue('keywordWhitelist', channel, network)
        blacklist = self.registryValue('keywordBlacklist', channel, network)

        # fix shadowing by "from supybot.commands import *"
        try:
            all = __builtins__.all
            any = __builtins__.any
        except AttributeError:
            all = __builtins__['all']
            any = __builtins__['any']

        title = getattr(entry, 'title', '')
        description = getattr(entry, 'description', '')

        if whitelist:
            if all(kw not in title and kw not in description
                   for kw in whitelist):
                return False
        if blacklist:
            if any(kw in title or kw in description
                   for kw in blacklist):
                return False
        return True

    _normalize_entry = utils.str.multipleReplacer(
            {'\r': ' ', '\n': ' ', '\x00': ''})
    def format_entry(self, network, channel, feed, entry, is_announce):
        key_name = 'announceFormat' if is_announce else 'format'
        if feed.name in self.registryValue('feeds'):
            specific_key_name = registry.join(['feeds', feed.name, key_name])
            template = self.registryValue(specific_key_name,
                                          channel, network) or \
                    self.registryValue(key_name, channel, network)
        else:
            template = self.registryValue(key_name, channel, network)
        date = entry.get('published_parsed')
        date = utils.str.timestamp(date)
        kwargs = {"feed_%s" % k: v for (k, v) in feed.data.items() if
                  isinstance(v, str)}
        kwargs["feed_name"] = feed.name
        kwargs.update(entry)
        for (key, value) in list(kwargs.items()):
            # First look for plain text
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'value' in item and \
                            item.get('type') == 'text/plain':
                        value = item['value']
                        break
            # Then look for HTML text or URL
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and item.get('type') in \
                            ('text/html', 'application/xhtml+xml'):
                        if 'value' in item:
                            value = utils.web.htmlToText(item['value'])
                        elif 'href' in item:
                            value = item['href']
            # Then fall back to any URL
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'href' in item:
                        value = item['href']
                        break
            # Finally, as a last resort, use the value as-is
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'value' in item:
                        value = item['value']
            kwargs[key] = value

        for key in ('summary', 'title'):
            detail = kwargs.get('%s_detail' % key)
            if isinstance(detail, dict) and detail.get('type') in \
                    ('text/html', 'application/xhtml+xml'):
                kwargs[key] = utils.web.htmlToText(detail['value'])

                if 'description' not in kwargs and kwargs[key]:
                    kwargs['description'] = kwargs[key]

        if 'description' not in kwargs and kwargs.get('content'):
            kwargs['description'] = kwargs['content']

        s = string.Template(template).safe_substitute(entry, **kwargs, date=date)
        return self._normalize_entry(s)

    def announce_entry(self, irc, channel, feed, entry):
        if self.should_send_entry(irc.network, channel, entry):
            s = self.format_entry(irc.network, channel, feed, entry, True)
            if self.registryValue('notice', channel, irc.network):
                m = ircmsgs.notice(channel, s)
            else:
                m = ircmsgs.privmsg(channel, s)
            irc.queueMsg(m)


    ##########
    # Commands

    @internationalizeDocstring
    def add(self, irc, msg, args, name, url):
        """<name> <url>

        Adds a command to this plugin that will look up the RSS feed at the
        given URL.
        """
        self.assert_feed_does_not_exist(name, url)
        register_feed_config(name, url)
        self.register_feed(name, url, True, False)
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

        # If the feed was first created "anonymously", eg. with
        # `@rss announce add http://example.org/rss`, then as a named feed
        # with `@rss add example http://example.org/rss`,
        # `self.get_feed(name)` above gets only one of them; so let's
        # remove the aliased name or URL from the feed names too,
        # or we would have a dangling entry here.
        self.remove_feed(feed.url)
        self.remove_feed(name)
        assert self.get_feed(name) is None

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
            channel_feeds = announce.getSpecific(channel=channel)() \
                | announce.getSpecific(channel=channel, network=irc.network)()
            feeds = format('%L', set(channel_feeds)) # set() to deduplicate
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
            plugin = irc.getCallback('RSS')
            invalid_feeds = [x for x in feeds if not plugin.get_feed(x)
                             and not utils.web.urlRe.match(x)]
            if invalid_feeds:
                irc.error(format(_('These feeds are unknown: %L'),
                    invalid_feeds), Raise=True)
            announce = conf.supybot.plugins.RSS.announce
            S = announce.getSpecific(channel=channel, network=irc.network)()
            for name in feeds:
                S.add(name)
            announce.getSpecific(channel=channel, network=irc.network,
                                 fallback_to_channel=False).setValue(S)
            irc.replySuccess()
            for name in feeds:
                feed = plugin.get_feed(name)
                if not feed:
                    register_feed_config(name, name)
                    plugin.register_feed(name, name, True, False)
                    feed = plugin.get_feed(name)
                plugin.announce_feed(feed, True)
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

            def remove_from_var(var):
                S = var()
                for feed in feeds:
                    S.discard(feed)
                var.setValue(S)

            remove_from_var(announce.get(channel))
            remove_from_var(announce.getSpecific(
                channel=channel, network=irc.network, fallback_to_channel=False))

            irc.replySuccess()
        remove = wrap(remove, [('checkChannelCapability', 'op'),
                               many(first('url', 'feedName'))])

        @internationalizeDocstring
        def channels(self, irc, msg, args, feed):
            """<name|url>

            Returns a list of channels that the given feed name or URL is being
            announced to.
            """
            plugin = irc.getCallback('RSS')
            if not plugin.get_feed(feed):
                irc.error(_("Unknown feed %s" % feed), Raise=True)

            channels = []
            for ircnet in world.ircs:
                for channel in list(ircnet.state.channels):
                    if feed in plugin.registryValue('announce', channel, ircnet.network):
                        channels.append(ircnet.network + channel)

            if channels:
                irc.reply(format("%s is announced to %L.", feed, channels))
            else:
                irc.reply("%s is not announced to any channels." % feed)

        channels = wrap(channels, ['feedName'])

    @internationalizeDocstring
    def rss(self, irc, msg, args, url, n):
        """<name|url> [<number of headlines>]

        Gets the title components of the given RSS feed.
        If <number of headlines> is given, return only that many headlines.
        """
        self.log.debug('Fetching %u', url)
        try:
            feed = self.get_feed(url)
            if not feed:
                feed = Feed(url, url, True)
        except InvalidFeedUrl:
            irc.error('%s is not a valid feed URL or name.' % url, Raise=True)
        channel = msg.channel
        self.update_feed_if_needed(feed)
        entries = feed.entries
        if not entries:
            s = _('Couldn\'t get RSS feed.')
            # If we got a soft parsing exception on our last run, show the error.
            if feed.last_exception is not None:
                s += _(' Parser error: ')
                s += str(feed.last_exception)
            irc.error(s)
            return
        n = n or self.registryValue('defaultNumberOfHeadlines', channel, irc.network)
        entries = list(filter(lambda e:self.should_send_entry(irc.network, channel, e),
                              feed.entries))
        entries = sort_feed_items(entries, 'newestFirst')
        entries = entries[:n]
        entries = sort_feed_items(entries, self.registryValue('sortFeedItems'))
        headlines = map(lambda e:self.format_entry(irc.network, channel, feed, e, False),
                        entries)
        sep = self.registryValue('headlineSeparator', channel, irc.network)
        irc.replies(headlines, joiner=sep)
    rss = wrap(rss, [first('url', 'feedName'), additional('int')])

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
        if not feed:
            feed = Feed(url, url, True)
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
