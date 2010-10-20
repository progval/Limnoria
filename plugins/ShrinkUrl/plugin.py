###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009-2010, James Vega
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
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('ShrinkUrl')

class CdbShrunkenUrlDB(object):
    def __init__(self, filename):
        self.dbs = {}
        cdb = conf.supybot.databases.types.cdb
        for service in conf.supybot.plugins.ShrinkUrl.default.validStrings:
            dbname = filename.replace('.db', service.capitalize() + '.db')
            self.dbs[service] = cdb.connect(dbname)

    def get(self, service, url):
        return self.dbs[service][url]

    def set(self, service, url, shrunkurl):
        self.dbs[service][url] = shrunkurl

    def close(self):
        for service in self.dbs:
            self.dbs[service].close()

    def flush(self):
        for service in self.dbs:
            self.dbs[service].flush()

ShrunkenUrlDB = plugins.DB('ShrinkUrl', {'cdb': CdbShrunkenUrlDB})

class ShrinkError(Exception):
    pass

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
                try:
                    cmd = self.registryValue('serviceRotation',
                                             channel, value=False)
                    cmd = cmd.getService().capitalize()
                except ValueError:
                    cmd = self.registryValue('default', channel).capitalize()
                try:
                    shortUrl = getattr(self, '_get%sUrl' % cmd)(url)
                    text = text.replace(url, shortUrl)
                except (utils.web.Error, AttributeError, ShrinkError):
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
            try:
                cmd = self.registryValue('serviceRotation',
                                         channel, value=False)
                cmd = cmd.getService().capitalize()
            except ValueError:
                cmd = self.registryValue('default', channel).capitalize()
            if len(url) >= minlen:
                try:
                    shorturl = getattr(self, '_get%sUrl' % cmd)(url)
                except (utils.web.Error, AttributeError, ShrinkError):
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
                if m is not None:
                    m.tag('shrunken')
    shrinkSnarfer = urlSnarfer(shrinkSnarfer)
    shrinkSnarfer.__doc__ = utils.web._httpUrlRe

    def _getLnUrl(self, url):
        url = utils.web.urlquote(url)
        try:
            return self.db.get('ln', url)
        except KeyError:
            text = utils.web.getUrl('http://ln-s.net/home/api.jsp?url=' + url)
            (code, text) = text.split(None, 1)
            text = text.strip()
            if code == '200':
                self.db.set('ln', url, text)
                return text
            else:
                raise ShrinkError, text

    @internationalizeDocstring
    def ln(self, irc, msg, args, url):
        """<url>

        Returns an ln-s.net version of <url>.
        """
        try:
            lnurl = self._getLnUrl(url)
            m = irc.reply(lnurl)
            if m is not None:
                m.tag('shrunken')
        except ShrinkError, e:
            irc.error(str(e))
    ln = thread(wrap(ln, ['url']))

    def _getTinyUrl(self, url):
        try:
            return self.db.get('tiny', url)
        except KeyError:
            text = utils.web.getUrl('http://tinyurl.com/api-create.php?url=' + url)
            if text.startswith('Error'):
                raise ShrinkError, text[5:]
            self.db.set('tiny', url, text)
            return text

    @internationalizeDocstring
    def tiny(self, irc, msg, args, url):
        """<url>

        Returns a TinyURL.com version of <url>
        """
        try:
            tinyurl = self._getTinyUrl(url)
            m = irc.reply(tinyurl)
            if m is not None:
                m.tag('shrunken')
        except ShrinkError, e:
            irc.errorPossibleBug(str(e))
    tiny = thread(wrap(tiny, ['url']))

    _xrlApi = 'http://metamark.net/api/rest/simple'
    def _getXrlUrl(self, url):
        quotedurl = utils.web.urlquote(url)
        try:
            return self.db.get('xrl', quotedurl)
        except KeyError:
            data = utils.web.urlencode({'long_url': url})
            text = utils.web.getUrl(self._xrlApi, data=data)
            if text.startswith('ERROR:'):
                raise ShrinkError, text[6:]
            self.db.set('xrl', quotedurl, text)
            return text

    @internationalizeDocstring
    def xrl(self, irc, msg, args, url):
        """<url>

        Returns an xrl.us version of <url>.
        """
        try:
            xrlurl = self._getXrlUrl(url)
            m = irc.reply(xrlurl)
            if m is not None:
                m.tag('shrunken')
        except ShrinkError, e:
            irc.error(str(e))
    xrl = thread(wrap(xrl, ['url']))

    _x0Api = 'http://api.x0.no/?%s'
    def _getX0Url(self, url):
        try:
            return self.db.get('x0', url)
        except KeyError:
            text = utils.web.getUrl(self._x0Api % url)
            if text.startswith('ERROR:'):
                raise ShrinkError, text[6:]
            self.db.set('x0', url, text)
            return text

    @internationalizeDocstring
    def x0(self, irc, msg, args, url):
        """<url>

        Returns an x0.no version of <url>.
        """
        try:
            x0url = self._getX0Url(url)
            m = irc.reply(x0url)
            if m is not None:
                m.tag('shrunken')
        except ShrinkError, e:
            irc.error(str(e))
    x0 = thread(wrap(x0, ['url']))

Class = ShrinkUrl

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
