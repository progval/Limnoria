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
Shrinks URLs using tinyurl.com and ln-s.net.
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
import supybot.ircmsgs as ircmsgs
from supybot.commands import *
import supybot.webutils as webutils
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('ShrinkUrl', True)
    if yn("""This plugin offers a snarfer that will go to tinyurl.com and get
             a shorter version of long URLs that are sent to the channel.
             Would you like this snarfer to be enabled?""", default=False):
        conf.supybot.plugins.ShrinkUrl.tinyurlSnarfer.setValue(True)

class ShrinkService(registry.OnlySomeStrings):
    validStrings = ('ln', 'tiny')

conf.registerPlugin('ShrinkUrl')
conf.registerChannelValue(conf.supybot.plugins.ShrinkUrl, 'shrinkSnarfer',
    registry.Boolean(False, """Determines whether the
    shrink snarfer is enabled.  This snarfer will watch for URLs in the
    channel, and if they're sufficiently long (as determined by
    supybot.plugins.ShrinkUrl.minimumLength) it will post a
    smaller URL from either ln-s.net or tinyurl.com, as denoted in
    supybot.plugins.ShrinkUrl.default."""))
conf.registerChannelValue(conf.supybot.plugins.ShrinkUrl, 'minimumLength',
    registry.PositiveInteger(48, """The minimum length a URL must be before
    the bot will shrink it."""))
conf.registerChannelValue(conf.supybot.plugins.ShrinkUrl, 'nonSnarfingRegexp',
    registry.Regexp(None, """Determines what URLs are to be snarfed; URLs
    matching the regexp given will not be snarfed.  Give the empty string if
    you have no URLs that you'd like to exclude from being snarfed."""))
conf.registerChannelValue(conf.supybot.plugins.ShrinkUrl, 'outFilter',
    registry.Boolean(False, """Determines whether the bot will shrink the URLs
    of outgoing messages if those URLs are longer than
    supybot.plugins.ShrinkUrl.minimumLength."""))
conf.registerChannelValue(conf.supybot.plugins.ShrinkUrl, 'default',
    ShrinkService('ln', """Determines what website the bot will use when
    shrinking a URL."""))

class CdbShrunkenUrlDB(object):
    def __init__(self, filename):
        self.tinyDb = conf.supybot.databases.types.cdb.connect(
            filename.replace('.db', '.Tiny.db'))
        self.lnDb = conf.supybot.databases.types.cdb.connect(
            filename.replace('.db', '.Ln.db'))

    def getTiny(self, url):
        return self.tinyDb[url]

    def setTiny(self, url, tinyurl):
        self.tinyDb[url] = tinyurl

    def getLn(self, url):
        return self.lnDb[url]

    def setLn(self, url, lnurl):
        self.lnDb[url] = lnurl

    def close(self):
        self.tinyDb.close()
        self.lnDb.close()

    def flush(self):
        self.tinyDb.flush()
        self.lnDb.flush()

ShrunkenUrlDB = plugins.DB('ShrinkUrl', {'cdb': CdbShrunkenUrlDB})

class ShrinkUrl(callbacks.PrivmsgCommandAndRegexp):
    regexps = ['shrinkSnarfer']
    def __init__(self):
        self.db = ShrunkenUrlDB()
        self.__parent = super(ShrinkUrl, self)
        self.__parent.__init__()

    def die(self):
        self.db.close()

    def callCommand(self, name, irc, msg, *L, **kwargs):
        try:
            self.__parent.callCommand(name, irc, msg, *L, **kwargs)
        except webutils.WebError, e:
            irc = callbacks.SimpleProxy(irc, msg)
            irc.error(str(e))

    def _outFilterThread(self, irc, msg):
        (channel, text) = msg.args
        for m in webutils.httpUrlRe.finditer(text):
            url = m.group(1)
            if len(url) > self.registryValue('minimumLength', channel):
                cmd = self.registryValue('default', channel)
                try:
                    if cmd == 'ln':
                        (shortUrl, _) = self._getLnUrl(url)
                    elif cmd == 'tiny':
                        shortUrl = self._getTinyUrl(url)
                    text = text.replace(url, shortUrl)
                except webutils.WebError:
                    pass
        newMsg = ircmsgs.privmsg(channel, text, msg=msg)
        newMsg.tag('shrunken')
        irc.queueMsg(newMsg)

    def outFilter(self, irc, msg):
        channel = msg.args[0]
        if msg.command == 'PRIVMSG' and ircutils.isChannel(channel):
            if not msg.shrunken:
                if self.registryValue('outFilter', channel):
                    if webutils.httpUrlRe.search(msg.args[1]):
                        self._outFilterThread(irc, msg)
                        return None
        return msg

    def shrinkSnarfer(self, irc, msg, match):
        r"https?://[^\])>\s]{13,}"
        channel = msg.args[0]
        if not ircutils.isChannel(channel):
            return
        if self.registryValue('shrinkSnarfer', channel):
            url = match.group(0)
            r = self.registryValue('nonSnarfingRegexp', channel)
            if r and r.search(url) is not None:
                self.log.debug('Matched nonSnarfingRegexp: %s',
                               utils.quoted(url))
                return
            minlen = self.registryValue('minimumLength', channel)
            cmd = self.registryValue('default', channel)
            if len(url) >= minlen:
                shorturl = None
                if cmd == 'tiny':
                    shorturl = self._getTinyUrl(url)
                elif cmd == 'ln':
                    (shorturl, _) = self._getLnUrl(url)
                if shorturl is None:
                    self.log.info('Couldn\'t get shorturl for %s',
                                  utils.quoted(url))
                    return
                domain = webutils.getDomain(url)
                s = '%s (at %s)' % (ircutils.bold(shorturl), domain)
                m = irc.reply(s, prefixName=False)
                if m is None:
                    print irc, irc.__class__
                m.tag('shrunken')
    shrinkSnarfer = urlSnarfer(shrinkSnarfer)

    def _getLnUrl(self, url):
        try:
            return (self.db.getLn(url), '200')
        except KeyError:
            text = webutils.getUrl('http://ln-s.net/home/api.jsp?url=%s' % url)
            (code, lnurl) = text.split(None, 1)
            lnurl = lnurl.strip()
            if code == '200':
                self.db.setLn(url, lnurl)
            else:
                lnurl = None
            return (lnurl, code)

    def ln(self, irc, msg, args, url):
        """<url>

        Returns an ln-s.net version of <url>.
        """
        if len(url) < 17:
            irc.error('Stop being a lazy-biotch and type the URL yourself.')
            return
        (lnurl, error) = self._getLnUrl(url)
        if lnurl is not None:
            domain = webutils.getDomain(url)
            m = irc.reply(lnurl)
            m.tag('shrunken')
        else:
            irc.error(error)
    ln = thread(wrap(ln, ['url']))

    _tinyRe = re.compile(r'<blockquote><b>(http://tinyurl\.com/\w+)</b>')
    def _getTinyUrl(self, url):
        try:
            return self.db.getTiny(url)
        except KeyError:
            s = webutils.getUrl('http://tinyurl.com/create.php?url=%s' % url)
            m = self._tinyRe.search(s)
            if m is None:
                tinyurl = None
            else:
                tinyurl = m.group(1)
                self.db.setTiny(url, tinyurl)
            return tinyurl

    def tiny(self, irc, msg, args, url):
        """<url>

        Returns a TinyURL.com version of <url>
        """
        if len(url) < 20:
            irc.error('Stop being a lazy-biotch and type the URL yourself.')
            return
        tinyurl = self._getTinyUrl(url)
        if tinyurl is not None:
            m = irc.reply(tinyurl)
            m.tag('shrunken')
        else:
            s = 'Could not parse the TinyURL.com results page.'
            irc.errorPossibleBug(s)
    tiny = thread(wrap(tiny, ['url']))


Class = ShrinkUrl

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
