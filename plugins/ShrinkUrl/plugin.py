###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009, James Vega
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

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

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

class ShrinkUrl(callbacks.PluginRegexp):
    regexps = ['shrinkSnarfer']
    def __init__(self, irc):
        self.__parent = super(ShrinkUrl, self)
        self.__parent.__init__(irc)
        self.db = ShrunkenUrlDB()

    def die(self):
        self.db.close()

    def callCommand(self, command, irc, msg, *args, **kwargs):
        try:
            self.__parent.callCommand(command, irc, msg, *args, **kwargs)
        except utils.web.Error, e:
            irc.error(str(e))

    def _outFilterThread(self, irc, msg):
        (channel, text) = msg.args
        for m in utils.web.httpUrlRe.finditer(text):
            url = m.group(1)
            if len(url) > self.registryValue('minimumLength', channel):
                cmd = self.registryValue('default', channel)
                try:
                    if cmd == 'ln':
                        (shortUrl, _) = self._getLnUrl(url)
                    elif cmd == 'tiny':
                        shortUrl = self._getTinyUrl(url)
                    text = text.replace(url, shortUrl)
                except utils.web.Error:
                    pass
        newMsg = ircmsgs.privmsg(channel, text, msg=msg)
        newMsg.tag('shrunken')
        irc.queueMsg(newMsg)

    def outFilter(self, irc, msg):
        channel = msg.args[0]
        if msg.command == 'PRIVMSG' and irc.isChannel(channel):
            if not msg.shrunken:
                if self.registryValue('outFilter', channel):
                    if utils.web.httpUrlRe.search(msg.args[1]):
                        self._outFilterThread(irc, msg)
                        return None
        return msg

    def shrinkSnarfer(self, irc, msg, match):
        r"https?://[^\])>\s]{13,}"
        channel = msg.args[0]
        if not irc.isChannel(channel):
            return
        if self.registryValue('shrinkSnarfer', channel):
            url = match.group(0)
            r = self.registryValue('nonSnarfingRegexp', channel)
            if r and r.search(url) is not None:
                self.log.debug('Matched nonSnarfingRegexp: %u', url)
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
                    self.log.info('Couldn\'t get shorturl for %u', url)
                    return
                if self.registryValue('shrinkSnarfer.showDomain', channel):
                    domain = ' (at %s)' % utils.web.getDomain(url)
                else:
                    domain = ''
                if self.registryValue('bold'):
                    s = format('%u%s', ircutils.bold(shorturl), domain)
                else:
                    s = format('%u%s', shorturl, domain)
                m = irc.reply(s, prefixNick=False)
                m.tag('shrunken')
    shrinkSnarfer = urlSnarfer(shrinkSnarfer)

    def _getLnUrl(self, url):
        url = utils.web.urlquote(url)
        try:
            return (self.db.getLn(url), '200')
        except KeyError:
            text = utils.web.getUrl('http://ln-s.net/home/api.jsp?url=' + url)
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
            domain = utils.web.getDomain(url)
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
            s = utils.web.getUrl('http://tinyurl.com/create.php?url=' + url)
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
            if m is not None:
                m.tag('shrunken')
        else:
            s = 'Could not parse the TinyURL.com results page.'
            irc.errorPossibleBug(s)
    tiny = thread(wrap(tiny, ['url']))


Class = ShrinkUrl

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
