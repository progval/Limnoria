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
Keeps track of URLs posted to a channel, along with relevant context.  Allows
searching for URLs and returning random URLs.  Also provides statistics on the
URLs in the database.
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
import supybot.webutils as webutils
import supybot.ircutils as ircutils
import supybot.commands as commands
import supybot.privmsgs as privmsgs
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
    supybot.plugins.ShrinkUrl.tinyurlSnarfer.minimumLength) it will post a smaller
    from tinyurl.com."""))
conf.registerChannelValue(conf.supybot.plugins.ShrinkUrl.tinyurlSnarfer,
    'minimumLength',
    registry.PositiveInteger(48, """The minimum length a URL must be before the
    tinyurl snarfer will snarf it."""))
conf.registerChannelValue(conf.supybot.plugins.ShrinkUrl, 'nonSnarfingRegexp',
    registry.Regexp(None, """Determines what URLs are to be snarfed and stored
    in the database in the channel; URLs matching the regexp given will not be
    snarfed.  Give the empty string if you have no URLs that you'd like to
    exclude from being snarfed."""))

class ShrinkUrl(callbacks.PrivmsgCommandAndRegexp):
    regexps = ['tinyurlSnarfer']
    def callCommand(self, name, irc, msg, *L, **kwargs):
        try:
            super(ShrinkUrl, self).callCommand(name, irc, msg, *L, **kwargs)
        except webutils.WebError, e:
            irc = callbacks.SimpleProxy(irc, msg)
            irc.error(str(e))
            
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
            minlen = self.registryValue('tinyurlSnarfer.minimumLength',channel)
            if len(url) >= minlen:
                tinyurl = self._getTinyUrl(url)
                if tinyurl is None:
                    self.log.info('Couldn\'t get tinyurl for %r', url)
                    return
                domain = webutils.getDomain(url)
                s = '%s (at %s)' % (ircutils.bold(tinyurl), domain)
                irc.reply(s, prefixName=False)
    tinyurlSnarfer = privmsgs.urlSnarfer(tinyurlSnarfer)

    _tinyRe = re.compile(r'<blockquote><b>(http://tinyurl\.com/\w+)</b>')
    def _getTinyUrl(self, url):
        s = webutils.getUrl('http://tinyurl.com/create.php?url=%s' % url)
        m = self._tinyRe.search(s)
        if m is None:
            tinyurl = None
        else:
            tinyurl = m.group(1)
        return tinyurl

    def tiny(self, irc, msg, args):
        """<url>

        Returns a TinyURL.com version of <url>
        """
        url = privmsgs.getArgs(args)
        if len(url) < 20:
            irc.error('Stop being a lazy-biotch and type the URL yourself.')
            return
        tinyurl = self._getTinyUrl(url)
        domain = webutils.getDomain(url)
        s = '%s (at %s)' % (ircutils.bold(tinyurl), domain)
        if tinyurl is not None:
            irc.reply(s)
        else:
            s = 'Could not parse the TinyURL.com results page.'
            irc.errorPossibleBug(s)
    tiny = commands.wrap(tiny, decorators=['thread'])


Class = ShrinkUrl

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
