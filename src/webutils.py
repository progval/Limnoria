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

__revision__ = "$Id$"

import fix

import re
import socket
import urllib2

class WebError(Exception):
    pass

urlRe = re.compile(r"(\w+://[^\])>\s]+)", re.I)

def getUrlFd(url):
    """Gets a file-like object for a url."""
    try:
        fd = urllib2.urlopen(url)
        return fd
    except socket.error, e:
        if e.args[0] == 111:
            raise WebError, 'Connection refused.'
        elif e.args[0] in (110, 10060):
            raise WebError, 'Connection timed out.'
        elif e.args[0] == 104:
            raise WebError, 'Connection reset by peer.'
        else:
            raise WebError, str(e)
    except (urllib2.HTTPError, urllib2.URLError), e:
        raise WebError, str(e)
    
def getUrl(url, size=None):
    """Gets a page.  Returns a string that is the page gotten."""
    fd = getUrlFd(url)
    if size is None:
        text = fd.read()
    else:
        text = fd.read(size)
    fd.close()
    return text


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

