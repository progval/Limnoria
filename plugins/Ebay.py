#!/usr/bin/env python

###
# Copyright (c) 2003, James Vega
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
Accesses eBay.com for various things
"""

import re
import sets
import getopt

__revision__ = "$Id$"
__author__ = "James Vega (jamessan) <jamessan@users.sf.net>"

import conf
import utils
import plugins
import ircutils
import privmsgs
import registry
import webutils
import callbacks


def configure(advanced):
    from questions import output, expect, anything, something, yn
    conf.registerPlugin('Ebay', True)
    output("""The Ebay plugin has the functionality to watch for URLs
              that match a specific pattern (we call this a snarfer). When
              supybot sees such a URL, he will parse the web page for
              information and reply with the results.""")
    if yn('Do you want the Ebay snarfer enabled by default?'):
        conf.supybot.plugins.Ebay.auctionSnarfer.setValue(True)

class EbayError(callbacks.Error):
    pass

conf.registerPlugin('Ebay')
conf.registerChannelValue(conf.supybot.plugins.Ebay, 'auctionSnarfer',
    registry.Boolean(False, """Determines whether the bot will automatically
    'snarf' Ebay auction URLs and print information about them."""))

class Ebay(callbacks.PrivmsgCommandAndRegexp):
    """
    Module for eBay stuff. Currently contains a URL snarfer and a command to
    get info about an auction.
    """
    threaded = True
    regexps = ['ebaySnarfer']

    _reopts = re.I | re.S
    _invalid = re.compile(r'(is invalid, still pending, or no longer in our '
                          r'database)', _reopts)
    _info = re.compile(r'<title>eBay item (\d+) \([^)]+\) - ([^<]+)</title>',
                       _reopts)

    _bid = re.compile(r'((?:Current|Starting) bid):.+?<b>([^<]+?)<fo', _reopts)
    _winningBid = re.compile(r'(Winning bid|Sold for):.+?<b>([^<]+?)<font',
                             _reopts)
    _time = re.compile(r'(Time left):.+?<b>([^<]+?)</b>', _reopts)
    _bidder = re.compile(r'(High bidder):.+?(?:">(User ID) (kept private)'
                         r'</font>|<a href[^>]+>([^<]+)</a>.+?'
                         r'<a href[^>]+>(\d+)</a>)', _reopts)
    _winningBidder = re.compile(r'(Winning bidder|Buyer):.+?<a href[^>]+>'
                               r'([^<]+)</a>.+?<a href[^>]+>(\d+)</a>',_reopts)
    _buyNow = re.compile(r'alt="(Buy It Now)">.*?<b>([^<]+)</b>', _reopts)
    _seller = re.compile(r'(Seller information).+?<a href[^>]+>([^<]+)</a>'
                         r'.+ViewFeedback.+">(\d+)</a>', _reopts)
    _searches = (_bid, _winningBid, _time, _bidder,
                 _winningBidder, _buyNow, _seller)
    _multiField = (_bidder, _winningBidder, _seller)

    def auction(self, irc, msg, args):
        """<item>

        Return useful information about the eBay auction with item number
        <item>.
        """
        item = privmsgs.getArgs(args)
        if not item.isdigit():
            irc.error('<item> must be an integer value.')
            return
        url = 'http://cgi.ebay.com/ws/eBayISAPI.dll?ViewItem&item=%s' % item
        try:
            irc.reply('%s <%s>' % (self._getResponse(url), url))
        except EbayError, e:
            irc.reply(str(e))

    def ebaySnarfer(self, irc, msg, match):
        r"http://cgi\.ebay\.(?:com(?:.au)?|ca|co.uk)/(?:.*?/)?(?:ws/)?" \
        r"eBayISAPI\.dll\?ViewItem(?:&item=\d+|&category=\d+)+"
        if not self.registryValue('auctionSnarfer', msg.args[0]):
            return
        url = match.group(0)
        try:
            irc.reply(self._getResponse(url), prefixName=False)
        except EbayError, e:
            self.log.exception('ebaySnarfer exception at %s:', url)
    ebaySnarfer = privmsgs.urlSnarfer(ebaySnarfer)

    def _getResponse(self, url):
        try:
            s = webutils.getUrl(url)
        except webutils.WebError, e:
            raise EbayError, str(e)
        resp = []
        m = self._invalid.search(s)
        if m:
            raise EbayError, 'That auction %s' % m.group(1)
        m = self._info.search(s)
        if m:
            (num, desc) = m.groups()
            resp.append('%s%s: %s' % (ircutils.bold('Item #'),
                                      ircutils.bold(num),
                                      utils.htmlToText(desc)))
        def bold(L):
            return (ircutils.bold(L[0]),) + L[1:]
        for r in self._searches:
            m = r.search(s)
            if m:
                if r in self._multiField:
                    # Have to filter the results from self._bidder since
                    # 2 of the 5 items in its tuple will always be None.
                    #self.log.warning(m.groups())
                    matches = filter(None, m.groups())
                    resp.append('%s: %s (%s)' % bold(matches))
                else:
                    resp.append('%s: %s' % bold(m.groups()))
        if resp:
            return '; '.join(resp)
        else:
            raise EbayError, 'That doesn\'t appear to be a proper eBay ' \
                             'auction page.  (%s)' % \
                             conf.supybot.replies.possibleBug()

Class = Ebay

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
