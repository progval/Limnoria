###
# Copyright (c) 2003-2005, Daniel DiPaolo
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

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('News')


class DbiNewsDB(plugins.DbiChannelDB):
    class DB(dbi.DB):
        class Record(dbi.Record):
            __fields__ = [
                'subject',
                'text',
                'at',
                'expires',
                'by',
                ]

            def __str__(self):
                user = plugins.getUserName(self.by)
                if self.expires == 0:
                    s = format(_('%s (Subject: %q, added by %s on %s)'),
                               self.text, self.subject, self.by,
                               utils.str.timestamp(self.at))
                else:
                    s = format(_('%s (Subject: %q, added by %s on %s, '
                               'expires at %s)'),
                               self.text, self.subject, user,
                               utils.str.timestamp(self.at),
                               utils.str.timestamp(self.expires))
                return s

        def __init__(self, filename):
            # We use self.__class__ here because apparently DB isn't in our
            # scope.  python--
            self.__parent = super(self.__class__, self)
            self.__parent.__init__(filename)

        def add(self, subject, text, at, expires, by):
            return self.__parent.add(self.Record(at=at, by=by, text=text,
                                     subject=subject, expires=expires))

        def getOld(self, id=None):
            now = time.time()
            if id:
                return self.get(id)
            else:
                L = [R for R in self if R.expires < now and R.expires != 0]
                if not L:
                    raise dbi.NoRecordError
                else:
                    return L

        def get(self, id=None):
            now = time.time()
            if id:
                return self.__parent.get(id)
            else:
                L = [R for R in self if R.expires >= now or R.expires == 0]
                if not L:
                    raise dbi.NoRecordError
                return L

        def change(self, id, f):
            news = self.get(id)
            s = '%s: %s' % (news.subject, news.text)
            s = f(s)
            (news.subject, news.text) = s.split(': ', 1)
            self.set(id, news)

NewsDB = plugins.DB('News', {'flat': DbiNewsDB})

class News(callbacks.Plugin):
    """This plugin provides a means of maintaining News for a channel."""
    def __init__(self, irc):
        self.__parent = super(News, self)
        self.__parent.__init__(irc)
        self.db = NewsDB()

    def die(self):
        self.__parent.die()
        self.db.close()

    @internationalizeDocstring
    def add(self, irc, msg, args, channel, user, at, expires, news):
        """[<channel>] <expires> <subject>: <text>

        Adds a given news item of <text> to a channel with the given <subject>.
        If <expires> isn't 0, that news item will expire <expires> seconds from
        now.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        try:
            (subject, text) = news.split(': ', 1)
        except ValueError:
            raise callbacks.ArgumentError
        id = self.db.add(channel, subject, text, at, expires, user.id)
        irc.replySuccess(format(_('(News item #%i added)'), id))
    add = wrap(add, ['channeldb', 'user', 'now', 'expiry', 'text'])

    @internationalizeDocstring
    def news(self, irc, msg, args, channel, id):
        """[<channel>] [<id>]

        Display the news items for <channel> in the format of '(#id) subject'.
        If <id> is given, retrieve only that news item; otherwise retrieve all
        news items.  <channel> is only necessary if the message isn't sent in
        the channel itself.
        """
        if not id:
            try:
                records = self.db.get(channel)
                items = [format('(#%i) %s', R.id, R.subject) for R in records]
                s = format(_('News for %s: %s'), channel, '; '.join(items))
                irc.reply(s)
            except dbi.NoRecordError:
                irc.reply(format(_('No news for %s.'), channel))
        else:
            try:
                record = self.db.get(channel, id)
                irc.reply(str(record))
            except dbi.NoRecordError as id:
                irc.errorInvalid(_('news item id'), id)
    news = wrap(news, ['channeldb', additional('positiveInt')])

    @internationalizeDocstring
    def remove(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Removes the news item with <id> from <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        try:
            self.db.remove(channel, id)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.errorInvalid(_('news item id'), id)
    remove = wrap(remove, ['channeldb', 'positiveInt'])

    @internationalizeDocstring
    def change(self, irc, msg, args, channel, id, replacer):
        """[<channel>] <id> <regexp>

        Changes the news item with <id> from <channel> according to the
        regular expression <regexp>.  <regexp> should be of the form
        s/text/replacement/flags.  <channel> is only necessary if the message
        isn't sent on the channel itself.
        """
        try:
            self.db.change(channel, id, replacer)
            irc.replySuccess()
        except dbi.NoRecordError:
            irc.errorInvalid(_('news item id'), id)
    change = wrap(change, ['channeldb', 'positiveInt', 'regexpReplacer'])

    @internationalizeDocstring
    def old(self, irc, msg, args, channel, id):
        """[<channel>] [<id>]

        Returns the old news item for <channel> with <id>.  If no number is
        given, returns all the old news items in reverse order.  <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        if id:
            try:
                record = self.db.getOld(channel, id)
                irc.reply(str(record))
            except dbi.NoRecordError as id:
                irc.errorInvalid(_('news item id'), id)
        else:
            try:
                records = self.db.getOld(channel)
                items = [format('(#%i) %s', R.id, R.subject) for R in records]
                s = format(_('Old news for %s: %s'), channel, '; '.join(items))
                irc.reply(s)
            except dbi.NoRecordError:
                irc.reply(format(_('No old news for %s.'), channel))
    old = wrap(old, ['channeldb', additional('positiveInt')])


Class = News


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
