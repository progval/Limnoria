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
import string
import socket

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.plugins as plugins
import supybot.commands as commands
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Web')

if minisix.PY3:
    from html.parser import HTMLParser
    from html.entities import entitydefs
    import http.client as http_client
else:
    from HTMLParser import HTMLParser
    from htmlentitydefs import entitydefs
    import httplib as http_client

class Title(utils.web.HtmlToText):
    entitydefs = entitydefs.copy()
    entitydefs['nbsp'] = ' '
    def __init__(self):
        self.inTitle = False
        self.inSvg = False
        utils.web.HtmlToText.__init__(self)

    @property
    def inHtmlTitle(self):
        return self.inTitle and not self.inSvg

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.inTitle = True
        elif tag == 'svg':
            self.inSvg = True

    def handle_endtag(self, tag):
        if tag == 'title':
            self.inTitle = False
        elif tag == 'svg':
            self.inSvg = False

    def append(self, data):
        if self.inHtmlTitle:
            super(Title, self).append(data)

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

if hasattr(http_client, '_MAXHEADERS'):
    def fetch_sandbox(f):
        """Runs a command in a forked process with limited memory resources
        to prevent memory bomb caused by specially crafted http responses.

        On CPython versions with support for limiting the number of headers,
        this is the identity function"""
        return f
else:
    # For the following CPython versions (as well as the matching Pypy
    # versions):
    # * 2.6 before 2.6.9
    # * 2.7 before 2.7.9
    # * 3.2 before 3.2.6
    # * 3.3 before 3.3.3
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
                        timeout=10, heap_size=10*1024*1024,
                        pn=self.name(), cn=f.__name__)
            except (commands.ProcessTimeoutError, MemoryError):
                raise utils.web.Error(_('Page is too big or the server took '
                        'too much time to answer the request.'))
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
    return utils.python.changeFunctionName(newf, f.__name__, f.__doc__)

class Web(callbacks.PluginRegexp):
    """Add the help for 'help Web' here."""
    regexps = ['titleSnarfer']
    threaded = True

    def noIgnore(self, irc, msg):
        return not self.registryValue('checkIgnored', msg.channel, irc.network)

    def getTitle(self, irc, url, raiseErrors, msg):
        size = conf.supybot.protocols.http.peekSize()
        timeout = self.registryValue('timeout')
        headers = conf.defaultHttpHeaders(irc.network, msg.channel)
        try:
            (target, text) = utils.web.getUrlTargetAndContent(url, size=size,
                timeout=timeout, headers=headers)
        except Exception as e:
            if raiseErrors:
                irc.error(_('That URL raised <' + str(e)) + '>',
                          Raise=True)
            else:
                self.log.info('Web plugin TitleSnarfer: URL <%s> raised <%s>',
                              url, str(e))
                return
        try:
            text = text.decode(utils.web.getEncoding(text) or 'utf8',
                    'replace')
        except UnicodeDecodeError:
            if minisix.PY3:
                if raiseErrors:
                    irc.error(_('Could not guess the page\'s encoding. (Try '
                                'installing python-charade.)'), Raise=True)
                else:
                    self.log.info('Web plugin TitleSnarfer: URL <%s> Could '
                                  'not guess the page\'s encoding. (Try '
                                  'installing python-charade.)', url)
                    return
        try:
            parser = Title()
            parser.feed(text)
        except UnicodeDecodeError:
            # Workaround for Python 2
            # https://github.com/ProgVal/Limnoria/issues/1359
            parser = Title()
            parser.feed(text.encode('utf8'))
        parser.close()
        title = utils.str.normalizeWhitespace(''.join(parser.data).strip())
        if title:
            return (target, title)
        elif raiseErrors:
            if len(text) < size:
                irc.error(_('That URL appears to have no HTML title.'),
                        Raise=True)
            else:
                irc.error(format(_('That URL appears to have no HTML title '
                                 'within the first %S.'), size), Raise=True)
        else:
            if len(text) < size:
                self.log.debug('Web plugin TitleSnarfer: URL <%s> appears '
                               'to have no HTML title. ', url)
            else:
                self.log.debug('Web plugin TitleSnarfer: URL <%s> appears '
                               'to have no HTML title within the first %S.',
                               url, size)

    @fetch_sandbox
    def titleSnarfer(self, irc, msg, match):
        channel = msg.channel
        network = irc.network
        if not channel:
            return
        if callbacks.addressed(irc, msg):
            return
        if self.registryValue('titleSnarfer', channel, network):
            url = match.group(0)
            if not self._checkURLWhitelist(url):
                return
            r = self.registryValue('nonSnarfingRegexp', channel, network)
            if r and r.search(url):
                self.log.debug('Not titleSnarfing %q.', url)
                return
            r = self.getTitle(irc, url, False, msg)
            if not r:
                return
            (target, title) = r
            if title:
                domain = utils.web.getDomain(target
                        if self.registryValue('snarferShowTargetDomain',
                                              channel, network)
                        else url)
                prefix = self.registryValue('snarferPrefix', channel, network)
                if prefix:
                    s = "%s %s" % (prefix, title)
                else:
                    s = title
                if self.registryValue('snarferShowDomain', channel, network):
                    s += format(_(' (at %s)'), domain)
                irc.reply(s, prefixNick=False)
        if self.registryValue('snarfMultipleUrls', channel, network):
            # FIXME: hack
            msg.tag('repliedTo', False)
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

    @wrap(['httpUrl'])
    @catch_web_errors
    @fetch_sandbox
    def headers(self, irc, msg, args, url):
        """<url>

        Returns the HTTP headers of <url>.  Only HTTP urls are valid, of
        course.
        """
        if not self._checkURLWhitelist(url):
            irc.error("This url is not on the whitelist.")
            return
        timeout = self.registryValue('timeout')
        fd = utils.web.getUrlFd(url, timeout=timeout)
        try:
            s = ', '.join([format(_('%s: %s'), k, v)
                           for (k, v) in fd.headers.items()])
            irc.reply(s)
        finally:
            fd.close()

    @wrap(['httpUrl'])
    @catch_web_errors
    @fetch_sandbox
    def location(self, irc, msg, args, url):
        """<url>

        If the <url> is redirected to another page, returns the URL of that
        page. This works even if there are multiple redirects.
        Only HTTP urls are valid.
        Useful to "un-tinify" URLs."""
        timeout = self.registryValue('timeout')
        (target, text) = utils.web.getUrlTargetAndContent(url, size=60,
            timeout=timeout)
        irc.reply(target)

    _doctypeRe = re.compile(r'(<!DOCTYPE[^>]+>)', re.M)
    @wrap(['httpUrl'])
    @catch_web_errors
    @fetch_sandbox
    def doctype(self, irc, msg, args, url):
        """<url>

        Returns the DOCTYPE string of <url>.  Only HTTP urls are valid, of
        course.
        """
        if not self._checkURLWhitelist(url):
            irc.error("This url is not on the whitelist.")
            return
        size = conf.supybot.protocols.http.peekSize()
        timeout = self.registryValue('timeout')
        s = utils.web.getUrl(url, size=size, timeout=timeout).decode('utf8')
        m = self._doctypeRe.search(s)
        if m:
            s = utils.str.normalizeWhitespace(m.group(0))
            irc.reply(s)
        else:
            irc.reply(_('That URL has no specified doctype.'))

    @wrap(['httpUrl'])
    @catch_web_errors
    @fetch_sandbox
    def size(self, irc, msg, args, url):
        """<url>

        Returns the Content-Length header of <url>.  Only HTTP urls are valid,
        of course.
        """
        if not self._checkURLWhitelist(url):
            irc.error("This url is not on the whitelist.")
            return
        timeout = self.registryValue('timeout')
        fd = utils.web.getUrlFd(url, timeout=timeout)
        try:
            try:
                size = fd.headers['Content-Length']
                if size is None:
                    raise KeyError('content-length')
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

    @wrap([getopts({'no-filter': ''}), 'httpUrl'])
    @catch_web_errors
    @fetch_sandbox
    def title(self, irc, msg, args, optlist, url):
        """[--no-filter] <url>

        Returns the HTML <title>...</title> of a URL.
        If --no-filter is given, the bot won't strip special chars (action,
        DCC, ...).
        """
        if not self._checkURLWhitelist(url):
            irc.error("This url is not on the whitelist.")
            return
        r = self.getTitle(irc, url, True, msg)
        if not r:
            return
        (target, title) = r
        if title:
            if not [y for x,y in optlist if x == 'no-filter']:
                for i in range(1, 4):
                    title = title.replace(chr(i), '')
            irc.reply(title)

    @wrap(['text'])
    def urlquote(self, irc, msg, args, text):
        """<text>

        Returns the URL quoted form of the text.
        """
        irc.reply(utils.web.urlquote(text))

    @wrap(['text'])
    def urlunquote(self, irc, msg, args, text):
        """<text>

        Returns the text un-URL quoted.
        """
        s = utils.web.urlunquote(text)
        irc.reply(s)

    @wrap(['url'])
    @catch_web_errors
    @fetch_sandbox
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
        timeout = self.registryValue('fetch.timeout')
        if not max:
            irc.error(_('This command is disabled '
                      '(supybot.plugins.Web.fetch.maximum is set to 0).'),
                      Raise=True)
        fd = utils.web.getUrl(url, size=max, timeout=timeout).decode('utf8')
        irc.reply(fd)

Class = Web

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
