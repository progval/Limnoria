###
# Copyright (c) 2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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
import sys
import socket
import HTMLParser
import htmlentitydefs

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.commands as commands
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Web')

class Title(HTMLParser.HTMLParser):
    entitydefs = htmlentitydefs.entitydefs.copy()
    entitydefs['nbsp'] = ' '
    entitydefs['apos'] = '\''
    def __init__(self):
        self.inTitle = False
        self.title = ''
        HTMLParser.HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.inTitle = True

    def handle_endtag(self, tag):
        if tag == 'title':
            self.inTitle = False

    def handle_data(self, data):
        if self.inTitle:
            self.title += data

    def handle_entityref(self, name):
        if self.inTitle:
            if name in self.entitydefs:
                self.title += self.entitydefs[name]

class DelayedIrc:
    def __init__(self, irc):
        self._irc = irc
        self._replies = []
    def reply(self, *args, **kwargs):
        self._replies.append(('reply', args, kwargs))
    def error(self, *args, **kwargs):
        self._replies.append(('error', args, kwargs))
    def __getattr__(self, name):
        assert name not in ('reply', 'error', '_irc', '_msg', '_replies')
        return getattr(self._irc, name)

def fetch_sandbox(f):
    """Runs a command in a forked process with limited memory resources
    to prevent memory bomb caused by specially crafted http responses."""
    def process(self, irc, msg, *args, **kwargs):
        delayed_irc = DelayedIrc(irc)
        f(self, delayed_irc, msg, *args, **kwargs)
        return delayed_irc._replies
    def newf(self, irc, *args):
        try:
            replies = commands.process(process, self, irc, *args,
                    timeout=5, heap_size=1024*1024,
                    pn=self.name(), cn=f.__name__)
        except commands.ProcessTimeoutError:
            raise utils.web.Error(_('Page is too big.'))
        else:
            for (method, args, kwargs) in replies:
                getattr(irc, method)(*args, **kwargs)
    newf.__doc__ = f.__doc__
    return newf

def catch_web_errors(f):
    """Display a nice error instead of "An error has occurred"."""
    def newf(self, irc, *args, **kwargs):
        try:
            f(self, irc, *args, **kwargs)
        except utils.web.Error as e:
            irc.reply(str(e))
    newf.__doc__ = f.__doc__
    return newf

class Web(callbacks.PluginRegexp):
    """Add the help for "@help Web" here."""
    regexps = ['titleSnarfer']

    @fetch_sandbox
    def titleSnarfer(self, irc, msg, match):
        channel = msg.args[0]
        if not irc.isChannel(channel):
            return
        if callbacks.addressed(irc.nick, msg):
            return
        if self.registryValue('titleSnarfer', channel):
            url = match.group(0)
            r = self.registryValue('nonSnarfingRegexp', channel)
            if r and r.search(url):
                self.log.debug('Not titleSnarfing %q.', url)
                return
            try:
                size = conf.supybot.protocols.http.peekSize()
                fd = utils.web.getUrlFd(url)
                text = fd.read(size)
                fd.close()
            except socket.timeout as e:
                self.log.info('Couldn\'t snarf title of %u: %s.', url, e)
                if self.registryValue('snarferReportIOExceptions', channel):
                     irc.reply(url+" : "+utils.web.TIMED_OUT, prefixNick=False)
                return
            try:
                text = text.decode(utils.web.getEncoding(text) or 'utf8',
                        'replace')
            except:
                pass
            parser = Title()
            try:
                parser.feed(text)
            except HTMLParser.HTMLParseError:
                self.log.debug('Encountered a problem parsing %u.  Title may '
                               'already be set, though', url)
            if parser.title:
                domain = utils.web.getDomain(fd.geturl()
                        if self.registryValue('snarferShowTargetDomain', channel)
                        else url)
                title = utils.web.htmlToText(parser.title.strip())
                if sys.version_info[0] < 3:
                    if isinstance(title, unicode):
                        title = title.encode('utf8', 'replace')
                s = format(_('Title: %s (at %s)'), title, domain)
                irc.reply(s, prefixNick=False)
    titleSnarfer = urlSnarfer(titleSnarfer)
    titleSnarfer.__doc__ = utils.web._httpUrlRe

    def _checkURLWhitelist(self, url):
        if not self.registryValue('urlWhitelist'):
            return True
        passed = False
        for wu in self.registryValue('urlWhitelist'):
            if wu.endswith('/') and url.find(wu) == 0:
                passed = True
                break
            if (not wu.endswith('/')) and (url.find(wu + '/') == 0 or url == wu):
                passed = True
                break
        return passed

    @catch_web_errors
    @fetch_sandbox
    @internationalizeDocstring
    def headers(self, irc, msg, args, url):
        """<url>

        Returns the HTTP headers of <url>.  Only HTTP urls are valid, of
        course.
        """
        if not self._checkURLWhitelist(url):
            irc.error("This url is not on the whitelist.")
            return
        fd = utils.web.getUrlFd(url)
        try:
            s = ', '.join([format(_('%s: %s'), k, v)
                           for (k, v) in fd.headers.items()])
            irc.reply(s)
        finally:
            fd.close()
    headers = wrap(headers, ['httpUrl'])

    _doctypeRe = re.compile(r'(<!DOCTYPE[^>]+>)', re.M)
    @catch_web_errors
    @fetch_sandbox
    @internationalizeDocstring
    def doctype(self, irc, msg, args, url):
        """<url>

        Returns the DOCTYPE string of <url>.  Only HTTP urls are valid, of
        course.
        """
        if not self._checkURLWhitelist(url):
            irc.error("This url is not on the whitelist.")
            return
        size = conf.supybot.protocols.http.peekSize()
        s = utils.web.getUrl(url, size=size) \
                        .decode('utf8')
        m = self._doctypeRe.search(s)
        if m:
            s = utils.str.normalizeWhitespace(m.group(0))
            irc.reply(s)
        else:
            irc.reply(_('That URL has no specified doctype.'))
    doctype = wrap(doctype, ['httpUrl'])

    @catch_web_errors
    @fetch_sandbox
    @internationalizeDocstring
    def size(self, irc, msg, args, url):
        """<url>

        Returns the Content-Length header of <url>.  Only HTTP urls are valid,
        of course.
        """
        if not self._checkURLWhitelist(url):
            irc.error("This url is not on the whitelist.")
            return
        fd = utils.web.getUrlFd(url)
        try:
            try:
                size = fd.headers['Content-Length']
                irc.reply(format(_('%u is %S long.'), url, int(size)))
            except KeyError:
                size = conf.supybot.protocols.http.peekSize()
                s = fd.read(size)
                if len(s) != size:
                    irc.reply(format(_('%u is %S long.'), url, len(s)))
                else:
                    irc.reply(format(_('The server didn\'t tell me how long %u '
                                     'is but it\'s longer than %S.'),
                                     url, size))
        finally:
            fd.close()
    size = wrap(size, ['httpUrl'])

    @catch_web_errors
    @fetch_sandbox
    @internationalizeDocstring
    def title(self, irc, msg, args, optlist, url):
        """[--no-filter] <url>

        Returns the HTML <title>...</title> of a URL.
        If --no-filter is given, the bot won't strip special chars (action,
        DCC, ...).
        """
        if not self._checkURLWhitelist(url):
            irc.error("This url is not on the whitelist.")
            return
        size = conf.supybot.protocols.http.peekSize()
        text = utils.web.getUrl(url, size=size)
        try:
            text = text.decode(utils.web.getEncoding(text) or 'utf8',
                    'replace')
        except:
            pass
        parser = Title()
        try:
            parser.feed(text)
        except HTMLParser.HTMLParseError:
            self.log.debug('Encountered a problem parsing %u.  Title may '
                           'already be set, though', url)
        if parser.title:
            title = utils.web.htmlToText(parser.title.strip())
            if not [y for x,y in optlist if x == 'no-filter']:
                for i in range(1, 4):
                    title = title.replace(chr(i), '')
            irc.reply(title)
        elif len(text) < size:
            irc.reply(_('That URL appears to have no HTML title.'))
        else:
            irc.reply(format(_('That URL appears to have no HTML title '
                             'within the first %S.'), size))
    title = wrap(title, [getopts({'no-filter': ''}), 'httpUrl'])

    @internationalizeDocstring
    def urlquote(self, irc, msg, args, text):
        """<text>

        Returns the URL quoted form of the text.
        """
        irc.reply(utils.web.urlquote(text))
    urlquote = wrap(urlquote, ['text'])

    @internationalizeDocstring
    def urlunquote(self, irc, msg, args, text):
        """<text>

        Returns the text un-URL quoted.
        """
        s = utils.web.urlunquote(text)
        irc.reply(s)
    urlunquote = wrap(urlunquote, ['text'])

    @catch_web_errors
    @fetch_sandbox
    @internationalizeDocstring
    def fetch(self, irc, msg, args, url):
        """<url>

        Returns the contents of <url>, or as much as is configured in
        supybot.plugins.Web.fetch.maximum.  If that configuration variable is
        set to 0, this command will be effectively disabled.
        """
        if not self._checkURLWhitelist(url):
            irc.error("This url is not on the whitelist.")
            return
        max = self.registryValue('fetch.maximum')
        if not max:
            irc.error(_('This command is disabled '
                      '(supybot.plugins.Web.fetch.maximum is set to 0).'),
                      Raise=True)
        fd = utils.web.getUrl(url, size=max) \
                        .decode('utf8')
        irc.reply(fd)
    fetch = wrap(fetch, ['url'])

Class = Web

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
