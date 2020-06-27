###
# Copyright (c) 2002-2005, Jeremiah Fincher
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
import base64
import socket

sockerrors = (socket.error,)
try:
    sockerrors += (socket.sslerror,)
except AttributeError:
    pass

from .str import normalizeWhitespace
from . import minisix

if minisix.PY2:
    import urllib
    import urllib2
    from httplib import InvalidURL
    from urlparse import urlsplit, urlunsplit, urlparse
    from htmlentitydefs import entitydefs, name2codepoint
    from HTMLParser import HTMLParser
    from cgi import escape as html_escape
    Request = urllib2.Request
    urlquote = urllib.quote
    urlquote_plus = urllib.quote_plus
    urlunquote = urllib.unquote
    urlopen = urllib2.urlopen
    def urlencode(*args, **kwargs):
        return urllib.urlencode(*args, **kwargs).encode()
    from urllib2 import HTTPError, URLError
    from urllib import splithost, splituser
else:
    from http.client import InvalidURL
    from urllib.parse import urlsplit, urlunsplit, urlparse
    from html.entities import entitydefs, name2codepoint
    from html.parser import HTMLParser
    from html import escape as html_escape
    import urllib.request, urllib.parse, urllib.error
    Request = urllib.request.Request
    urlquote = urllib.parse.quote
    urlquote_plus = urllib.parse.quote_plus
    urlunquote = urllib.parse.unquote
    urlopen = urllib.request.urlopen
    def urlencode(*args, **kwargs):
        return urllib.parse.urlencode(*args, **kwargs)
    from urllib.error import HTTPError, URLError
    from urllib.parse import splithost, splituser

class Error(Exception):
    pass

_octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
_ipAddr = r'%s(?:\.%s){3}' % (_octet, _octet)
# Base domain regex off RFC 1034 and 1738
_label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
_scheme = r'[a-z][a-z0-9+.-]*'
_domain = r'%s(?:\.%s)*\.[0-9a-z][-0-9a-z]+' % (_label, _label)
_urlRe = r'(%s://(?:\S+@)?(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (
        _scheme, _domain, _ipAddr)
urlRe = re.compile(_urlRe, re.I)
_httpUrlRe = r'(https?://(?:\S+@)?(?:%s|%s)(?::\d+)?(?:/[^\]>\s]*)?)' % \
             (_domain, _ipAddr)
httpUrlRe = re.compile(_httpUrlRe, re.I)

REFUSED = 'Connection refused.'
TIMED_OUT = 'Connection timed out.'
UNKNOWN_HOST = 'Unknown host.'
RESET_BY_PEER = 'Connection reset by peer.'
FORBIDDEN = 'Client forbidden from accessing URL.'

def strError(e):
    try:
        n = e.args[0]
    except Exception:
        return str(e)
    if n == 111:
        return REFUSED
    elif n in (110, 10060):
        return TIMED_OUT
    elif n == 104:
        return RESET_BY_PEER
    elif n in (8, 7, 3, 2, -2, -3):
        return UNKNOWN_HOST
    elif n == 403:
        return FORBIDDEN
    else:
        return str(e)

# Used to build defaultHeaders
baseDefaultHeaders = {
    'User-agent': 'Mozilla/5.0 (compatible; utils.web python module)'
    }

# overridable by other modules/plugins.
defaultHeaders = baseDefaultHeaders.copy()

# Other modules should feel free to replace this with an appropriate
# application-specific function.  Feel free to use a callable here.
proxy = None

def getUrlFd(url, headers=None, data=None, timeout=None):
    """getUrlFd(url, headers=None, data=None, timeout=None)

    Opens the given url and returns a file object.  Headers and data are
    a dict and string, respectively, as per urllib.request.Request's
    arguments."""
    if headers is None:
        headers = defaultHeaders
    if minisix.PY3 and isinstance(data, str):
        data = data.encode()
    try:
        if not isinstance(url, Request):
            (scheme, loc, path, query, frag) = urlsplit(url)
            (user, host) = splituser(loc)
            url = urlunsplit((scheme, host, path, query, ''))
            request = Request(url, headers=headers, data=data)
            if user:
                request.add_header('Authorization',
                                   'Basic %s' % base64.b64encode(user))
        else:
            request = url
            request.add_data(data)
        fd = urlopen(request, timeout=timeout)
        return fd
    except socket.timeout as e:
        raise Error(TIMED_OUT)
    except sockerrors as e:
        raise Error(strError(e))
    except InvalidURL as e:
        raise Error('Invalid URL: %s' % e)
    except HTTPError as e:
        raise Error(strError(e))
    except URLError as e:
        raise Error(strError(e.reason))
    # Raised when urllib doesn't recognize the url type
    except ValueError as e:
        raise Error(strError(e))

def getUrlTargetAndContent(url, size=None, headers=None, data=None, timeout=None):
    """getUrlTargetAndContent(url, size=None, headers=None, data=None, timeout=None)

    Gets a page.  Returns two strings that are the page gotten and the
    target URL (ie. after redirections).  Size is an integer
    number of bytes to read from the URL.  Headers and data are dicts as per
    urllib.request.Request's arguments."""
    fd = getUrlFd(url, headers=headers, data=data, timeout=timeout)
    try:
        if size is None:
            text = fd.read()
        else:
            text = fd.read(size)
    except socket.timeout:
        raise Error(TIMED_OUT)
    target = fd.geturl()
    fd.close()
    return (target, text)

def getUrlContent(*args, **kwargs):
    """getUrlContent(url, size=None, headers=None, data=None, timeout=None)

    Gets a page.  Returns a string that is the page gotten.  Size is an integer
    number of bytes to read from the URL.  Headers and data are dicts as per
    urllib.request.Request's arguments."""
    (target, text) = getUrlTargetAndContent(*args, **kwargs)
    return text

def getUrl(*args, **kwargs):
    """Alias for getUrlContent."""
    return getUrlContent(*args, **kwargs)

def getDomain(url):
    return urlparse(url)[1]

_charset_re = ('<meta[^a-z<>]+charset='
    """(?P<charset>("[^"]+"|'[^']+'))""")
def getEncoding(s):
    try:
        match = re.search(_charset_re, s, re.MULTILINE)
        if match:
            return match.group('charset')[1:-1]
    except:
        match = re.search(_charset_re.encode(), s, re.MULTILINE)
        if match:
            return match.group('charset').decode()[1:-1]

    try:
        import charade.universaldetector
        u = charade.universaldetector.UniversalDetector()
        u.feed(s)
        u.close()
        return u.result['encoding']
    except:
        return None

class HtmlToText(HTMLParser, object):
    """Taken from some eff-bot code on c.l.p."""
    entitydefs = entitydefs.copy()
    entitydefs['nbsp'] = ' '
    entitydefs['apos'] = '\''
    def __init__(self, tagReplace=' '):
        self.data = []
        self.tagReplace = tagReplace
        super(HtmlToText, self).__init__()

    def append(self, data):
        self.data.append(data)

    def handle_starttag(self, tag, attr):
        self.append(self.tagReplace)

    def handle_endtag(self, tag):
        self.append(self.tagReplace)

    def handle_data(self, data):
        self.append(data)

    def handle_entityref(self, data):
        if minisix.PY3:
            if data in name2codepoint:
                self.append(chr(name2codepoint[data]))
            elif isinstance(data, bytes):
                self.append(data.decode())
            else:
                self.append(data)
        else:
            if data in name2codepoint:
                self.append(unichr(name2codepoint[data]))
            elif isinstance(data, str):
                self.append(data.decode('utf8', errors='replace'))
            else:
                self.append(data)

    def getText(self):
        text = ''.join(self.data).strip()
        return normalizeWhitespace(text)

    def handle_charref(self, name):
        self.append(self.unescape('&#%s;' % name))

def htmlToText(s, tagReplace=' '):
    """Turns HTML into text.  tagReplace is a string to replace HTML tags with.
    """
    encoding = getEncoding(s)
    if encoding:
        s = s.decode(encoding)
    else:
        try:
            if minisix.PY2 or isinstance(s, bytes):
                s = s.decode('utf8')
        except:
            pass
    x = HtmlToText(tagReplace)
    x.feed(s)
    x.close()
    return x.getText()

def mungeEmail(s):
    s = s.replace('@', ' AT ')
    s = s.replace('.', ' DOT ')
    return s


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:


