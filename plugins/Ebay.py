#!/usr/bin/python2.3

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
import urllib2

import plugins

import conf
import debug
import utils
import plugins
import ircutils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Ebay')
    if advanced:
        print 'The Ebay plugin has the functionality to watch for URLs'
        print 'that match a specific pattern (we call this a snarfer). When'
        print 'supybot sees such a URL, he will parse the web page for'
        print 'information and reply with the results.\n'
        if yn('Do you want the Ebay snarfer enabled by default?') == 'n':
            onStart.append('Ebay toggle auction off')

class Ebay(callbacks.PrivmsgCommandAndRegexp, plugins.Configurable):
    """
    Module for eBay stuff. Currently contains a URL snarfer and a command to
    get info about an auction.
    """
    threaded = True
    regexps = ['ebaySnarfer']
    configurables = plugins.ConfigurableDictionary(
        [('snarfer', plugins.ConfigurableBoolType, True,
          """Determines whether the bot will automatically 'snarf' Ebay auction
          URLs and print information about them.""")]
    )
    def __init__(self):
        plugins.Configurable.__init__(self)
        callbacks.PrivmsgCommandAndRegexp.__init__(self)

    def die(self):
        plugins.Configurable.die(self)
        callbacks.PrivmsgCommandAndRegexp.die(self)

    _reopts = re.I | re.S
    _invalid = re.compile(r'(is invalid, still pending, or no longer in our '\
        'database)', _reopts)
    _info = re.compile(r'<title>eBay item (\d+) \([^)]+\) - ([^<]+)</title>',
        _reopts)

    _bid = re.compile(r'((?:Current|Starting) bid):.+?<b>([^<]+?)<font',
        _reopts)
    _winningBid = re.compile(r'(Winning bid|Sold for):.+?<b>([^<]+?)<font',
        _reopts)
    _time = re.compile(r'(Time left):.+?<b>([^<]+?)</b>', _reopts)
    _bidder = re.compile(r'(High bidder):.+?(?:">(User ID) (kept private)'\
        '</font>|<a href[^>]+>([^<]+)</a>.+?<a href[^>]+>(\d+)</a>)', _reopts)
    _winningBidder = re.compile(r'(Winning bidder|Buyer):.+?<a href[^>]+>'\
        '([^<]+)</a>.+?<a href[^>]+>(\d+)</a>', _reopts)
    _buyNow = re.compile(r'alt="(Buy It Now)">.*?<b>([^<]+)</b>', _reopts)
    _seller = re.compile(r'(Seller information).+?<a href[^>]+>([^<]+)</a>'\
        '.+ViewFeedback.+">(\d+)</a>', _reopts)
    _searches = (_bid, _winningBid, _time, _bidder, _winningBidder, _buyNow,
        _seller)
    _multiField = (_bidder, _winningBidder, _seller)

    def ebay(self, irc, msg, args):
        """[--link] <item>

        Return useful information about the eBay auction with item number
        <item>. If --link is specified, returns a link to the auction as well.
        """
        (optlist, rest) = getopt.getopt(args, '', ['link'])
        link = False
        for (option, arg) in optlist:
            option = option.strip('-')
            if option == 'link':
                link = True
        item = privmsgs.getArgs(rest)
        url = 'http://cgi.ebay.com/ws/eBayISAPI.dll?ViewItem&item=%s' % item
        if link:
            irc.reply(msg, url)
            return
        self._getResponse(irc, msg, url)

    def ebaySnarfer(self, irc, msg, match):
        r"http://cgi\.ebay\.(?:com(?:.au)?|ca|co.uk)/(?:.*?/)?(?:ws/)?" \
        r"eBayISAPI\.dll\?ViewItem(?:&item=\d+|&category=\d+)+"
        if not self.configurables.get('snarfer', channel=msg.args[0]):
            return
        url = match.group(0)
        #debug.printf(url)
        self._getResponse(irc, msg, url, snarf=True)
    ebaySnarfer = privmsgs.urlSnarfer(ebaySnarfer)

    def _getResponse(self, irc, msg, url, snarf=False):
        def bold(m):
            return (ircutils.bold(m[0]),) + m[1:]
        fd = urllib2.urlopen(url)
        s = fd.read()
        fd.close()
        resp = []
        m = self._invalid.search(s)
        if m:
            if snarf:
                return
            irc.reply(msg, 'That auction %s' % m.group(1))
            return
        m = self._info.search(s)
        if m:
            (num, desc) = m.groups()
            resp.append('%s%s: %s' % (ircutils.bold('Item #'),
                                      ircutils.bold(num),
                                      utils.htmlToText(desc)))
        for r in self._searches:
            m = r.search(s)
            if m:
                if r in self._multiField:
                    #debug.printf(m.groups())
                    # [:3] is to make sure that we don't pass a tuple with
                    # more than 3 items. this allows self._bidder to work
                    # since self._bidder returns a 5 item tuple
                    resp.append('%s: %s (%s)' % bold(m.groups()[:3]))
                else:
                    resp.append('%s: %s' % bold(m.groups()))
        if resp:
            if snarf:
                irc.reply(msg, '%s' % '; '.join(resp), prefixName=False)
            else:
                irc.reply(msg, '%s' % '; '.join(resp))
        else:
            if snarf:
                irc.error(msg, '%s doesn\'t appear to be a proper eBay '\
                    'Auction page. (%s)' % (url, conf.replyPossibleBug))
            else:
                irc.error(msg, 'That doesn\'t appear to be a proper eBay '\
                    'Auction page. (%s)' % conf.replyPossibleBug)

Class = Ebay

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
