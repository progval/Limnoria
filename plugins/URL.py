###
# Copyright (c) 2002-2004, Jeremiah Fincher
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
import getopt
import urlparse
import itertools

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import wrap
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.webutils as webutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('URL', True)
    if yn("""This plugin also offers a snarfer that will try to fetch the
             title of URLs that it sees in the channel.  Would like you this
             snarfer to be enabled?""", default=False):
        conf.supybot.plugins.URL.titleSnarfer.setValue(True)

conf.registerPlugin('URL')
conf.registerChannelValue(conf.supybot.plugins.URL, 'titleSnarfer',
    registry.Boolean(False, """Determines whether the bot will output the HTML
    title of URLs it sees in the channel."""))
conf.registerChannelValue(conf.supybot.plugins.URL, 'nonSnarfingRegexp',
    registry.Regexp(None, """Determines what URLs are to be snarfed and stored
    in the database in the channel; URLs matching the regexp given will not be
    snarfed.  Give the empty string if you have no URLs that you'd like to
    exclude from being snarfed."""))

class UrlRecord(dbi.Record):
    __fields__ = [
        'url',
        'by',
        'near',
        'at',
        ]

class DbiUrlDB(plugins.DbiChannelDB):
    class DB(dbi.DB):
        Record = UrlRecord
        def add(self, url, msg):
            record = self.Record(url=url, by=msg.nick,
                                 near=msg.args[1], at=msg.receivedAt)
            super(self.__class__, self).add(record)
        def urls(self, p):
            L = list(self.select(p))
            L.reverse()
            return L

URLDB = plugins.DB('URL', {'flat': DbiUrlDB})

class URL(callbacks.PrivmsgCommandAndRegexp):
    priority = 100 # lower than 99, the normal priority.
    regexps = ['titleSnarfer']
    _titleRe = re.compile('<title>(.*?)</title>', re.I | re.S)
    def __init__(self):
        self.__parent = super(URL, self)
        self.__parent.__init__()
        self.db = URLDB()

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        if ircutils.isChannel(channel):
            if ircmsgs.isAction(msg):
                text = ircmsgs.unAction(msg)
            else:
                text = msg.args[1]
            for url in webutils.urlRe.findall(text):
                r = self.registryValue('nonSnarfingRegexp', channel)
                if r and r.search(url):
                    self.log.debug('Skipping adding %r to db.', url)
                    continue
                self.log.debug('Adding %r to db.', url)
                self.db.add(channel, url, msg)
        self.__parent.doPrivmsg(irc, msg)

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
    titleSnarfer = wrap(titleSnarfer, decorators=['urlSnarfer'])

    def stats(self, irc, msg, args):
        """[<channel>]

        Returns the number of URLs in the URL database.  <channel> is only
        required if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        self.db.vacuum(channel)
        count = self.db.size(channel)
        irc.reply('I have %s in my database.' % utils.nItems('URL', count))

    def last(self, irc, msg, args):
        """[<channel>] [--{from,with,near,proto}=<value>] --{nolimit}

        Gives the last URL matching the given criteria.  --from is from whom
        the URL came; --proto is the protocol the URL used; --with is something
        inside the URL; --near is something in the same message as the URL; If
        --nolimit is given, returns all the URLs that are found. to just the
        URL.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (optlist, rest) = getopt.getopt(args, '', ['from=', 'with=', 'near=',
                                                   'proto=', 'nolimit',])
        predicates = []
        f = None
        nolimit = False
        for (option, arg) in optlist:
            if option == '--nolimit':
                nolimit = True
            elif option == '--from':
                def f(record, arg=arg):
                    return ircutils.strEqual(record.by, arg)
            elif option == '--with':
                def f(record, arg=arg):
                    return arg in record.url
            elif option == '--proto':
                def f(record, arg=arg):
                    return record.url.startswith(arg)
            elif option == '--near':
                def f(record, arg=arg):
                    return arg in record.near
            if f is not None:
                predicates.append(f)
        def predicate(record):
            for predicate in predicates:
                if not predicate(record):
                    return False
            return True
        urls = [record.url for record in self.db.urls(channel, predicate)]
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
