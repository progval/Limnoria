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
Keeps track of URLs posted to a channel, along with relevant context.  Allows
searching for URLs and returning random URLs.  Also provides statistics on the
URLs in the database.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import os
import re
import sets
import time
import shutil
import getopt
import urllib2
import urlparse
import itertools

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.webutils as webutils
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('URL', True)
    if yn("""This plugin offers a snarfer that will go to tinyurl.com and get
             a shorter version of long URLs that are sent to the channel.
             Would you like this snarfer to be enabled?""", default=False):
        conf.supybot.plugins.URL.tinyurlSnarfer.setValue(True)
    if yn("""This plugin also offers a snarfer that will try to fetch the
             title of URLs that it sees in the channel.  Would like you this
             snarfer to be enabled?""", default=False):
        conf.supybot.plugins.URL.titleSnarfer.setValue(True)

conf.registerPlugin('URL')
conf.registerChannelValue(conf.supybot.plugins.URL, 'tinyurlSnarfer',
    registry.Boolean(False, """Determines whether the
    tinyurl snarfer is enabled.  This snarfer will watch for URLs in the
    channel, and if they're sufficiently long (as determined by
    supybot.plugins.URL.tinyurlSnarfer.minimumLength) it will post a smaller
    from tinyurl.com."""))
conf.registerChannelValue(conf.supybot.plugins.URL.tinyurlSnarfer,
    'minimumLength',
    registry.PositiveInteger(48, """The minimum length a URL must be before the
    tinyurl snarfer will snarf it."""))
conf.registerChannelValue(conf.supybot.plugins.URL, 'titleSnarfer',
    registry.Boolean(False, """Determines whether the bot will output the HTML
    title of URLs it sees in the channel."""))
conf.registerChannelValue(conf.supybot.plugins.URL, 'nonSnarfingRegexp',
    registry.Regexp(None, """Determines what URLs are to be snarfed and stored
    in the database in the channel; URLs matchin the regexp given will not be
    snarfed.  Give the empty string if you have no URLs that you'd like to
    exclude from being snarfed."""))

class URLDB(object):
    def __init__(self, channel, log):
        self.log = log
        dataDir = conf.supybot.directories.data()
        self.filename = os.path.join(dataDir, '%s-URL.db' % channel)

    def _getFile(self):
        try:
            fd = file(self.filename)
            return fd
        except EnvironmentError, e:
            self.log.warning('Couldn\'t open %s: %s',
                             self.filename, utils.exnToString(e))
        return None

    def _formatRecord(self, url, nick):
        return '%s %s\n' % (url, nick)

    def addUrl(self, url, nick):
        fd = file(self.filename, 'a')
        fd.write(self._formatRecord(url, nick))
        fd.close()

    def numUrls(self):
        fd = self._getFile()
        if fd is None:
            return 0
        try:
            return itertools.ilen(fd)
        finally:
            fd.close()

    def getUrlsAndNicks(self, p=None):
        L = []
        fd = self._getFile()
        if fd is None:
            return []
        try:
            for line in fd:
                line = line.strip()
                (url, nick) = line.split()
                if p(url, nick):
                    L.append((url, nick))
            seen = sets.Set()
            L.reverse()
            for (i, (url, nick)) in enumerate(L):
                if url in seen:
                    L[i] = None
                else:
                    seen.add(url)
            L = filter(None, L)
            return L
        finally:
            fd.close()

    def getUrls(self, p):
        return [url for (url, nick) in self.getUrlsAndNicks(p)]

    def vacuum(self):
        filename = utils.mktemp()
        out = file(filename, 'w')
        notAdded = 0
        urls = self.getUrlsAndNicks(lambda *args: True)
        seen = sets.Set()
        for (i, (url, nick)) in enumerate(urls):
            if url not in seen:
                seen.add(url)
            else:
                urls[i] = None
                notAdded += 1
        urls.reverse()
        for urlNick in urls:
            if urlNick is not None:
                out.write(self._formatRecord(*urlNick))
        out.close()
        shutil.move(filename, self.filename)
        self.log.info('Vacuumed %s, removed %s records.',
                      self.filename, notAdded)
                
        

class URL(callbacks.PrivmsgCommandAndRegexp):
    regexps = ['tinyurlSnarfer', 'titleSnarfer']
    _titleRe = re.compile('<title>(.*?)</title>', re.I | re.S)
    def getDb(self, channel):
        return URLDB(channel, self.log)
    
    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        if ircmsgs.isAction(msg):
            text = ircmsgs.unAction(msg)
        else:
            text = msg.args[1]
        for url in webutils.urlRe.findall(text):
            r = self.registryValue('nonSnarfingRegexp', channel)
            #self.log.warning(repr(r))
            if r and r.search(url):
                self.log.debug('Skipping adding %r to db.', url)
                continue
            self.log.debug('Adding %r to db.', url)
            db.addUrl(url, msg.nick)
        callbacks.PrivmsgCommandAndRegexp.doPrivmsg(self, irc, msg)

    def tinyurlSnarfer(self, irc, msg, match):
        r"https?://[^\])>\s]{18,}"
        channel = msg.args[0]
        if not ircutils.isChannel(channel):
            return
        r = self.registryValue('nonSnarfingRegexp', channel)
        if self.registryValue('tinyurlSnarfer', channel):
            url = match.group(0)
            if r and r.search(url):
                return
            minlen = self.registryValue('tinyurlSnarfer.minimumLength',channel)
            if len(url) >= minlen:
                tinyurl = self._getTinyUrl(url, channel)
                if tinyurl is None:
                    self.log.warning('Couldn\'t get tinyurl for %r', url)
                    return
                domain = webutils.getDomain(url)
                s = '%s (at %s)' % (ircutils.bold(tinyurl), domain)
                irc.reply(s, prefixName=False)
    tinyurlSnarfer = privmsgs.urlSnarfer(tinyurlSnarfer)

    def titleSnarfer(self, irc, msg, match):
        r"https?://[^\])>\s]+"
        channel = msg.args[0]
        if not ircutils.isChannel(channel):
            return
        if callbacks.addressed(irc.nick, msg):
            return
        if self.registryValue('titleSnarfer', channel):
            url = match.group(0)
            r = self.registryValue('nonSnarfingRegexp', channel)
            if r and r.search(url):
                self.log.debug('Not titleSnarfing %r.', url)
                return
            try:
                size = conf.supybot.protocols.http.peekSize()
                text = webutils.getUrl(url, size=size)
            except webutils.WebError, e:
                self.log.info('Couldn\'t snarf title of %s, %s.', url, e)
                return
            m = self._titleRe.search(text)
            if m is not None:
                domain = webutils.getDomain(url)
                title = utils.htmlToText(m.group(1).strip())
                s = 'Title: %s (at %s)' % (title, domain)
                irc.reply(s, prefixName=False)
    titleSnarfer = privmsgs.urlSnarfer(titleSnarfer)

    _tinyRe = re.compile(r'<blockquote><b>(http://tinyurl\.com/\w+)</b>')
    def _getTinyUrl(self, url, channel, cmd=False):
        try:
            fd = urllib2.urlopen('http://tinyurl.com/create.php?url=%s' %
                                 url)
            s = fd.read()
            fd.close()
            m = self._tinyRe.search(s)
            if m is None:
                tinyurl = None
            else:
                tinyurl = m.group(1)
            return tinyurl
        except urllib2.HTTPError, e:
            if cmd:
                raise callbacks.Error, e.msg()
            else:
                self.log.warning(str(e))

    def tiny(self, irc, msg, args):
        """<url>

        Returns a TinyURL.com version of <url>
        """
        url = privmsgs.getArgs(args)
        if len(url) < 20:
            irc.error('Stop being a lazy-biotch and type the URL yourself.')
            return
        channel = msg.args[0]
        snarf = self.registryValue('tinyurlSnarfer', channel)
        minlen = self.registryValue('tinyurlSnarfer.minimumLength', channel)
        r = self.registryValue('nonSnarfingRegexp', channel)
        if snarf and len(url) >= minlen and not r.search(url):
            self.log.debug('Not applying tiny command, snarfer is active.')
            return
        tinyurl = self._getTinyUrl(url, channel, cmd=True)
        if tinyurl is not None:
            irc.reply(tinyurl)
        else:
            s = 'Could not parse the TinyURL.com results page.'
            irc.errorPossibleBug(s)
    tiny = privmsgs.thread(tiny)

    def stats(self, irc, msg, args):
        """[<channel>]

        Returns the number of URLs in the URL database.  <channel> is only
        required if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        db.vacuum()
        count = db.numUrls()
        irc.reply('I have %s in my database.' % utils.nItems('URL', count))

    def last(self, irc, msg, args):
        """[<channel>] [--{from,with,proto}=<value>] --{nolimit}

        Gives the last URL matching the given criteria.  --from is from whom
        the URL came; --proto is the protocol the URL used; --with is something
        inside the URL; If --nolimit is given, returns all the URLs that are
        found. to just the URL.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (optlist, rest) = getopt.getopt(args, '', ['from=', 'with=',
                                                   'proto=', 'nolimit',])
        predicates = []
        nolimit = False
        for (option, arg) in optlist:
            if option == '--nolimit':
                nolimit = True
            elif option == '--from':
                def from_(url, nick, arg=arg):
                    return nick.lower() == arg.lower()
                predicates.append(from_)
            elif option == '--with':
                def with(url, nick, arg=arg):
                    return arg in url
                predicates.append(with)
            elif option == '--proto':
                def proto(url, nick, arg=arg):
                    return url.startswith(arg)
                predicates.append(proto)
        db = self.getDb(channel)
        def predicate(url, nick):
            for predicate in predicates:
                if not predicate(url, nick):
                    return False
            return True
        urls = db.getUrls(predicate)
        if not urls:
            irc.reply('No URLs matched that criteria.')
        else:
            if nolimit:
                urls = ['<%s>' % url for url in urls]
                s = ', '.join(urls)
            else:
                # We should optimize this with another URLDB method eventually.
                s = urls[0]
            irc.reply(s)


Class = URL

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
