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
Shrinks URLs using tinyurl.com (and soon, ln-s.net as well).
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
from supybot.commands import wrap
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

conf.registerPlugin('ShrinkUrl')
conf.registerChannelValue(conf.supybot.plugins.ShrinkUrl, 'tinyurlSnarfer',
    registry.Boolean(False, """Determines whether the
    tinyurl snarfer is enabled.  This snarfer will watch for URLs in the
    channel, and if they're sufficiently long (as determined by
    supybot.plugins.ShrinkUrl.minimumLength) it will post a
    smaller URL from tinyurl.com."""))
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

class CdbShrunkenUrlDB(object):
    def __init__(self, filename):
        self.db = conf.supybot.databases.types.cdb.connect(filename)
        
    def get(self, url):
        return self.db[url]

    def set(self, url, tinyurl):
        self.db[url] = tinyurl

    def close(self):
        self.db.close()

    def flush(self):
        self.db.flush()

ShrunkenUrlDB = plugins.DB('ShrinkUrl', {'cdb': CdbShrunkenUrlDB})
        
class ShrinkUrl(callbacks.PrivmsgCommandAndRegexp):
    regexps = ['tinyurlSnarfer']
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
                shortUrl = self._getTinyUrl(url)
                text = text.replace(url, shortUrl)
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
            
    def tinyurlSnarfer(self, irc, msg, match):
        r"https?://[^\])>\s]{13,}"
        channel = msg.args[0]
        if not ircutils.isChannel(channel):
            return
        if self.registryValue('tinyurlSnarfer', channel):
            url = match.group(0)
            r = self.registryValue('nonSnarfingRegexp', channel)
            if r and r.search(url) is not None:
                self.log.debug('Matched nonSnarfingRegexp: %r', url)
                return
            minlen = self.registryValue('minimumLength',channel)
            if len(url) >= minlen:
                tinyurl = self._getTinyUrl(url)
                if tinyurl is None:
                    self.log.info('Couldn\'t get tinyurl for %r', url)
                    return
                domain = webutils.getDomain(url)
                s = '%s (at %s)' % (ircutils.bold(tinyurl), domain)
                m = irc.reply(s, prefixName=False)
                if m is None:
                    print irc, irc.__class__
                m.tag('shrunken')
    tinyurlSnarfer = wrap(tinyurlSnarfer, decorators=['urlSnarfer'])

    _tinyRe = re.compile(r'<blockquote><b>(http://tinyurl\.com/\w+)</b>')
    def _getTinyUrl(self, url):
        # XXX This should use a database, eventually, especially once we write
        # the outFilter.
        try:
            return self.db.get(url)
        except KeyError:
            s = webutils.getUrl('http://tinyurl.com/create.php?url=%s' % url)
            m = self._tinyRe.search(s)
            if m is None:
                tinyurl = None
            else:
                tinyurl = m.group(1)
                self.db.set(url, tinyurl)
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
    tiny = wrap(tiny, ['url'], decorators=['thread'])


Class = ShrinkUrl

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
