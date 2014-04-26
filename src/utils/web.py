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
import urllib
import urllib2
import httplib
import sgmllib
import urlparse
import htmlentitydefs

sockerrors = (socket.error,)
try:
    sockerrors += (socket.sslerror,)
except AttributeError:
    pass

from .str import normalizeWhitespace

Request = urllib2.Request
urlquote = urllib.quote
urlunquote = urllib.unquote
urlencode = urllib.urlencode

class Error(Exception):
    pass

_octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
_ipAddr = r'%s(?:\.%s){3}' % (_octet, _octet)
# Base domain regex off RFC 1034 and 1738
_label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
_domain = r'%s(?:\.%s)*\.[0-9a-z][-0-9a-z]+' % (_label, _label)
_urlRe = r'(\w+://(?:\S+@)?(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (_domain,
                                                                   _ipAddr)
urlRe = re.compile(_urlRe, re.I)
_httpUrlRe = r'(https?://(?:\S+@)?(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % \
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

defaultHeaders = {
    'User-agent': 'Mozilla/5.0 (compatible; utils.web python module)'
    }

# Other modules should feel free to replace this with an appropriate
# application-specific function.  Feel free to use a callable here.
proxy = None

def getUrlFd(url, headers=None, data=None, timeout=None):
    """getUrlFd(url, headers=None, data=None, timeout=None)

    Opens the given url and returns a file object.  Headers and data are
    a dict and string, respectively, as per urllib2.Request's arguments."""
    if headers is None:
        headers = defaultHeaders
    try:
        if not isinstance(url, urllib2.Request):
            (scheme, loc, path, query, frag) = urlparse.urlsplit(url)
            (user, host) = urllib.splituser(loc)
            url = urlparse.urlunsplit((scheme, host, path, query, ''))
            request = urllib2.Request(url, headers=headers, data=data)
            if user:
                request.add_header('Authorization',
                                   'Basic %s' % base64.b64encode(user))
        else:
            request = url
            request.add_data(data)
        httpProxy = force(proxy)
        if httpProxy:
            request.set_proxy(httpProxy, 'http')
        fd = urllib2.urlopen(request, timeout=timeout)
        return fd
    except socket.timeout, e:
        raise Error, TIMED_OUT
    except sockerrors, e:
        raise Error, strError(e)
    except httplib.InvalidURL, e:
        raise Error, 'Invalid URL: %s' % e
    except urllib2.HTTPError, e:
        raise Error, strError(e)
    except urllib2.URLError, e:
        raise Error, strError(e.reason)
    # Raised when urllib doesn't recognize the url type
    except ValueError, e:
        raise Error, strError(e)

def getUrl(url, size=None, headers=None, data=None, timeout=None):
    """getUrl(url, size=None, headers=None, data=None, timeout=None)

    Gets a page.  Returns a string that is the page gotten.  Size is an integer
    number of bytes to read from the URL.  Headers and data are dicts as per
    urllib2.Request's arguments."""
    fd = getUrlFd(url, headers=headers, data=data, timeout=timeout)
    try:
        if size is None:
            text = fd.read()
        else:
            text = fd.read(size)
    except socket.timeout, e:
        raise Error, TIMED_OUT
    fd.close()
    return text

def getDomain(url):
    return urlparse.urlparse(url)[1]

class HtmlToText(sgmllib.SGMLParser):
    """Taken from some eff-bot code on c.l.p."""
    entitydefs = htmlentitydefs.entitydefs.copy()
    entitydefs['nbsp'] = ' '
    def __init__(self, tagReplace=' '):
        self.data = []
        self.tagReplace = tagReplace
        sgmllib.SGMLParser.__init__(self)

    def unknown_starttag(self, tag, attr):
        self.data.append(self.tagReplace)

    def unknown_endtag(self, tag):
        self.data.append(self.tagReplace)

    def handle_data(self, data):
        self.data.append(data)

    def getText(self):
        text = ''.join(self.data).strip()
        return normalizeWhitespace(text)

def htmlToText(s, tagReplace=' '):
    """Turns HTML into text.  tagReplace is a string to replace HTML tags with.
    """
    x = HtmlToText(tagReplace)
    x.feed(s)
    return x.getText()

def mungeEmail(s):
    s = s.replace('@', ' AT ')
    s = s.replace('.', ' DOT ')
    return s

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

