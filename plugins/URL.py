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

import plugins

import os
import re
import time
import getopt
import urllib2
import urlparse

import conf
import utils
import ircmsgs
import webutils
import ircutils
import privmsgs
import registry
import callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

def configure(advanced):
    from questions import output, expect, anything, something, yn
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

class URL(callbacks.PrivmsgCommandAndRegexp,
          plugins.ChannelDBHandler):
    regexps = ['tinyurlSnarfer', 'titleSnarfer']
    _titleRe = re.compile('<title>(.*?)</title>', re.I)
    def __init__(self):
        self.nextMsgs = {}
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        plugins.ChannelDBHandler.__init__(self)

    def die(self):
        callbacks.PrivmsgCommandAndRegexp.die(self)
        plugins.ChannelDBHandler.die(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(filename)
        db = sqlite.connect(filename)
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE urls (
                          id INTEGER PRIMARY KEY,
                          url TEXT,
                          added TIMESTAMP,
                          added_by TEXT,
                          previous_msg TEXT,
                          current_msg TEXT,
                          next_msg TEXT,
                          protocol TEXT,
                          site TEXT,
                          filename TEXT
                          )""")
        cursor.execute("""CREATE TABLE tinyurls (
                          id INTEGER PRIMARY KEY,
                          url_id INTEGER,
                          tinyurl TEXT
                          )""")
        db.commit()
        return db

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        if (msg.nick, channel) in self.nextMsgs:
            L = self.nextMsgs.pop((msg.nick, msg.args[0]))
            for (url, added) in L:
                cursor.execute("""UPDATE urls SET next_msg=%s
                                  WHERE url=%s AND added=%s""",
                               msg.args[1], url, added)
        if ircmsgs.isAction(msg):
            text = ircmsgs.unAction(msg)
        else:
            text = msg.args[1]
        for url in webutils.urlRe.findall(text):
            r = self.registryValue('nonSnarfingRegexp', channel)
            if r and r.search(url):
                continue
            (protocol, site, filename, _, _, _) = urlparse.urlparse(url)
            previousMsg = ''
            for oldMsg in reviter(irc.state.history):
                if oldMsg.command == 'PRIVMSG':
                    if oldMsg.nick == msg.nick and oldMsg.args[0] == channel:
                        previousMsg = oldMsg.args[1]
            addedBy = msg.nick
            added = int(time.time())
            cursor.execute("""INSERT INTO urls VALUES
                              (NULL, %s, %s, %s, %s, %s, '', %s, %s, %s)""",
                           url, added, addedBy, msg.args[1], previousMsg,
                           protocol, site, filename)
            key = (msg.nick, channel)
            self.nextMsgs.setdefault(key, []).append((url, added))
        db.commit()
        super(URL, self).doPrivmsg(irc, msg)

    def tinyurlSnarfer(self, irc, msg, match):
        r"https?://[^\])>\s]{18,}"
        if not ircutils.isChannel(msg.args[0]):
            return
        channel = msg.args[0]
        if self.registryValue('tinyurlSnarfer', channel):
            url = match.group(0)
            minlen = self.registryValue('tinyurlSnarfer.minimumLength',channel)
            if len(url) >= minlen:
                db = self.getDb(channel)
                cursor = db.cursor()
                (tinyurl, updateDb) = self._getTinyUrl(url, channel)
                if tinyurl is None:
                    self.log.warning('tinyurl was None for url %r', url)
                    return
                elif updateDb:
                    self._updateTinyDb(url, tinyurl, channel)
                domain = webutils.getDomain(url)
                s = '%s (at %s)' % (ircutils.bold(tinyurl), domain)
                irc.reply(s, prefixName=False)
    tinyurlSnarfer = privmsgs.urlSnarfer(tinyurlSnarfer)

    def titleSnarfer(self, irc, msg, match):
        r"https?://[^\])>\s]+"
        if not ircutils.isChannel(msg.args[0]):
            return
        channel = msg.args[0]
        if self.registryValue('titleSnarfer', channel):
            url = match.group(0)
            text = webutils.getUrl(url, size=conf.supybot.httpPeekSize())
            m = self._titleRe.search(text)
            if m is not None:
                domain = webutils.getDomain(url)
                title = utils.htmlToText(m.group(1).strip())
                s = 'Title: %s (at %s)' % (title, domain)
                irc.reply(s, prefixName=False)
    titleSnarfer = privmsgs.urlSnarfer(titleSnarfer)
                
    def _updateTinyDb(self, url, tinyurl, channel):
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO tinyurls
                          VALUES (NULL, 0, %s)""", tinyurl)
        cursor.execute("""SELECT id FROM urls WHERE url=%s""", url)
        id = cursor.fetchone()[0]
        cursor.execute("""UPDATE tinyurls SET url_id=%s
                          WHERE tinyurl=%s""", id, tinyurl)
        db.commit()

    _tinyRe = re.compile(r'(http://tinyurl\.com/\w+)</blockquote>')
    def _getTinyUrl(self, url, channel, cmd=False):
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT tinyurls.tinyurl FROM urls, tinyurls
                          WHERE urls.url=%s AND
                          tinyurls.url_id=urls.id""", url)
        if cursor.rowcount == 0:
            updateDb = True
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
            except urllib2.HTTPError, e:
                if cmd:
                    raise callbacks.Error, e.msg()
                else:
                    self.log.warning(str(e))
        else:
            updateDb = False
            tinyurl = cursor.fetchone()[0]
        return (tinyurl, updateDb)

    def _formatUrl(self, url, added, addedBy):
        when = time.strftime(conf.supybot.humanTimestampFormat(),
                             time.localtime(int(added)))
        return '<%s> (added by %s at %s)' % (url, addedBy, when)

    def random(self, irc, msg, args):
        """[<channel>]

        Returns a random URL from the URL database.  <channel> is only required
        if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT url, added, added_by
                          FROM urls
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount == 0:
            irc.reply('I have no URLs in my database for %s' % channel)
        else:
            irc.reply(self._formatUrl(*cursor.fetchone()))

    def tiny(self, irc, msg, args):
        """<url>

        Returns a TinyURL.com version of <url>
        """
        url = privmsgs.getArgs(args)
        if len(url) < 24:
            irc.error(
                      'Stop being a lazy-biotch and type the URL yourself.')
            return
        channel = msg.args[0]
        snarf = self.registryValue('tinyurlSnarfer', channel)
        minlen = self.registryValue('tinyurlSnarfer.minimumLength', channel)
        if snarf and len(url) >= minlen:
            return
        (tinyurl, updateDb) = self._getTinyUrl(url, channel, cmd=True)
        if tinyurl:
            if updateDb:
                self._updateTinyDb(url, tinyurl, channel)
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
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM urls""")
        (count,) = cursor.fetchone()
        irc.reply('I have %s %s in my database.' %
                  (count, int(count) == 1 and 'URL' or 'URLs'))

    def last(self, irc, msg, args):
        """[<channel>] [--{from,with,at,proto,near}=<value>] --{nolimit,fancy}

        Gives the last URL matching the given criteria.  --from is from whom
        the URL came; --at is the site of the URL; --proto is the protocol the
        URL used; --with is something inside the URL; --near is a string in the
        messages before and after the link.  If --nolimit is given, returns as
        many URLs as can fit in the message. --fancy returns information in
        addition to just the URL. <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (optlist, rest) = getopt.getopt(args, '', ['from=', 'with=', 'at=',
                                                   'proto=', 'near=',
                                                   'nolimit', 'fancy'])
        criteria = ['1=1']
        formats = []
        simple = True
        nolimit = False
        for (option, argument) in optlist:
            option = option.lstrip('-') # Strip off the --.
            if option == 'nolimit':
                nolimit = True
            if option == 'fancy':
                simple = False
            elif option == 'from':
                criteria.append('added_by LIKE %s')
                formats.append(argument)
            elif option == 'with':
                if '%' not in argument and '_' not in argument:
                    argument = '%%%s%%' % argument
                criteria.append('url LIKE %s')
                formats.append(argument)
            elif option == 'at':
                if '%' not in argument and '_' not in argument:
                    argument = '%' + argument
                criteria.append('site LIKE %s')
                formats.append(argument)
            elif option == 'proto':
                criteria.append('protocol=%s')
                formats.append(argument)
            elif option == 'near':
                criteria.append("""(previous_msg LIKE %s OR
                                    next_msg LIKE %s OR
                                    current_msg LIKE %s)""")
                if '%' not in argument:
                    argument = '%%%s%%' % argument
                formats.append(argument)
                formats.append(argument)
                formats.append(argument)
        db = self.getDb(channel)
        cursor = db.cursor()
        criterion = ' AND '.join(criteria)
        sql = """SELECT id, url, added, added_by
                 FROM urls
                 WHERE %s ORDER BY id DESC
                 LIMIT 100""" % criterion
        cursor.execute(sql, *formats)
        if cursor.rowcount == 0:
            irc.reply('No URLs matched that criteria.')
        else:
            if nolimit:
                urls = ['<%s>' % t[1] for t in cursor.fetchall()]
                s = ', '.join(urls)
            elif simple:
                s = cursor.fetchone()[1]
            else:
                (id, url, added, added_by) = cursor.fetchone()
                timestamp = time.strftime('%I:%M %p, %B %d, %Y',
                                          time.localtime(int(added)))
                s = '#%s: <%s>, added by %s at %s.' % \
                    (id, url, added_by, timestamp)
            irc.reply(s)


Class = URL

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
