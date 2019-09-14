###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('URL')

class UrlRecord(dbi.Record):
    __fields__ = [
        ('url', eval),
        ('by', eval),
        ('near', eval),
        ('at', eval),
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

class URL(callbacks.Plugin):
    """This plugin records how many URLs have been mentioned in
    a channel and what the last URL was."""
    def __init__(self, irc):
        self.__parent = super(URL, self)
        self.__parent.__init__(irc)
        self.db = URLDB()

    def doPrivmsg(self, irc, msg):
        if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
            return
        if msg.channel:
            if ircmsgs.isAction(msg):
                text = ircmsgs.unAction(msg)
            else:
                text = msg.args[1]
            for url in utils.web.urlRe.findall(text):
                r = self.registryValue('nonSnarfingRegexp',
                                       msg.channel, irc.network)
                if r and r.search(url):
                    self.log.debug('Skipping adding %u to db.', url)
                    continue
                self.log.debug('Adding %u to db.', url)
                self.db.add(msg.channel, url, msg)

    @internationalizeDocstring
    def stats(self, irc, msg, args, channel):
        """[<channel>]

        Returns the number of URLs in the URL database.  <channel> is only
        required if the message isn't sent in the channel itself.
        """
        self.db.vacuum(channel)
        count = self.db.size(channel)
        irc.reply(format(_('I have %n in my database.'), (count, 'URL')))
    stats = wrap(stats, ['channeldb'])

    @internationalizeDocstring
    def last(self, irc, msg, args, channel, optlist):
        """[<channel>] [--{from,with,without,near,proto} <value>] [--nolimit]

        Gives the last URL matching the given criteria.  --from is from whom
        the URL came; --proto is the protocol the URL used; --with is something
        inside the URL; --without is something that should not be in the URL;
        --near is something in the same message as the URL.  If --nolimit is
        given, returns all the URLs that are found to just the URL.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        predicates = []
        f = None
        nolimit = False
        for (option, arg) in optlist:
            if isinstance(arg, minisix.string_types):
                arg = arg.lower()
            if option == 'nolimit':
                nolimit = True
            elif option == 'from':
                def f(record, arg=arg):
                    return ircutils.strEqual(record.by, arg)
            elif option == 'with':
                def f(record, arg=arg):
                    return arg in record.url.lower()
            elif option == 'without':
                def f(record, arg=arg):
                    return arg not in record.url.lower()
            elif option == 'proto':
                def f(record, arg=arg):
                    return record.url.lower().startswith(arg)
            elif option == 'near':
                def f(record, arg=arg):
                    return arg in record.near.lower()
            if f is not None:
                predicates.append(f)
        def predicate(record):
            for predicate in predicates:
                if not predicate(record):
                    return False
            return True
        urls = [record.url for record in self.db.urls(channel, predicate)]
        if not urls:
            irc.reply(_('No URLs matched that criteria.'))
        else:
            if nolimit:
                urls = [format('%u', url) for url in urls]
                s = ', '.join(urls)
            else:
                # We should optimize this with another URLDB method eventually.
                s = urls[0]
            irc.reply(s)
    last = wrap(last, ['channeldb',
                       getopts({'from': 'something', 'with': 'something',
                                'near': 'something', 'proto': 'something',
                                'nolimit': '', 'without': 'something',})])

Class = URL

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
