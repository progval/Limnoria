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
            onStart.append('Ebay togglesnarfer auction off')

example = utils.wrapLines("""
Add an example IRC session using this module here.
""")

class Ebay(callbacks.PrivmsgCommandAndRegexp):
    """
    Module for eBay stuff. Currently contains a URL snarfer and a command to
    get info about an auction.
    """
    threaded = True
    regexps = ['ebaySnarfer']
    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.snarfers = {'auction' : True}

    _reopts = re.I | re.S
    _info = re.compile(r'<title>eBay item (\d+) \([^)]+\) - ([^<]+)</title>',
        _reopts)

    _bid = re.compile(r'Current bid:.+?<b>([^<]+?)<font', _reopts)
    _getBid = lambda self, s: '%s: %s' % (ircutils.bold('Bid'),
        self._bid.search(s).group(1))

    _winningBid = re.compile(r'(?:Winning bid|Sold for):.+?<b>([^<]+?)<font',
        _reopts)
    _getWinningbid = lambda self, s: '%s: %s' % (ircutils.bold('Winning bid'),
        self._winningBid.search(s).group(1))

    _time = re.compile(r'Time left:.+?<b>([^<]+?)</b>', _reopts)
    _getTime = lambda self, s: '%s: %s' % (ircutils.bold('Time left'),
        self._time.search(s).group(1))

    _bidder = re.compile(r'High bidder:.+?<a href[^>]+>([^<]+)</a>.+?<a '\
        'href[^>]+>(\d+)</a>', _reopts)
    _getBidder = lambda self, s: '%s: %s (%s)' % (ircutils.bold('Bidder'),
        self._bidder.search(s).group(1), self._bidder.search(s).group(2))

    _winningBidder = re.compile(r'(?:Winning bidder|Buyer):.+?<a href[^>]+>'\
        '([^<]+)</a>.+?<a href[^>]+>(\d+)</a>', _reopts)
    _getWinningbidder = lambda self, s: '%s: %s (%s)' % (ircutils.bold(
        'Winning bidder'), self._winningBidder.search(s).group(1),
        self._winningBidder.search(s).group(2))

    _buyNow = re.compile(r'alt="Buy It Now">.*?<b>([^<]+)</b>')
    _getBuynow = lambda self, s: '%s: %s' % (ircutils.bold('Buy It Now'),
        self._buyNow.search(s).group(1))

    _seller = re.compile(r'Seller information.+?<a href[^>]+>([^<]+)</a>'\
        '.+ViewFeedback.+">(\d+)</a>', _reopts)
    _getSeller = lambda self, s: '%s: %s (%s)' % (ircutils.bold('Seller'),
        self._seller.search(s).group(1), self._seller.search(s).group(2))

    def _toggleHelper(self, irc, msg, state, snarfer):
        if not state:
            self.snarfers[snarfer] = not self.snarfers[snarfer] 
        elif state in self._enable:
            self.snarfers[snarfer] = True
        elif state in self._disable:
            self.snarfers[snarfer] = False
        resp = []
        for k in self.snarfers:
            if self.snarfers[k]:
                resp.append('%s%s: On' % (k[0].upper(), k[1:]))
            else:
                resp.append('%s%s: Off' % (k[0].upper(), k[1:]))
        irc.reply(msg, '%s (%s)' % (conf.replySuccess, '; '.join(resp)))

    _enable = ('on', 'enable')
    _disable = ('off', 'disable')
    def togglesnarfer(self, irc, msg, args):
        """<auction> [<on|off>]

        Toggles the snarfer that responds to eBay auction links.  If
        nothing is specified, all snarfers will have their states
        toggled (on -> off, off -> on).  If only a state is specified, all
        snarfers will have their state set to the specified state.  If a
        specific snarfer is specified, the changes will apply only to that
        snarfer.
        """
        (snarfer, state) = privmsgs.getArgs(args, optional=1)
        snarfer = snarfer.lower()
        state = state.lower()
        if snarfer not in self.snarfers:
            raise callbacks.ArgumentError
        if state and state not in self._enable and state not in self._disable:
            raise callbacks.ArgumentError
        self._toggleHelper(irc, msg, state, snarfer)
    togglesnarfer=privmsgs.checkCapability(togglesnarfer, 'admin')

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
        r"http://cgi\.ebay\.com/ws/eBayISAPI\.dll\?ViewItem(?:&item=\d+|"\
            "&category=\d+)+"
        if not self.snarfers['auction']:
            return
        url = match.group(0)
        self._getResponse(irc, msg, url, snarf = True)

    def _getResponse(self, irc, msg, url, snarf = False):
        fd = urllib2.urlopen(url)
        s = fd.read()
        fd.close()
        searches = (self._getBid, self._getBuynow, self._getWinningbid,
            self._getTime, self._getBidder, self._getWinningbidder,
            self._getSeller)
        try:
            (num, desc) = self._info.search(s).groups()
            resp = ['%s%s: %s' % (ircutils.bold('Item #'), ircutils.bold(num),
                utils.htmlToText(desc))]
            for i in searches:
                try:
                    resp.append('%s' % i(s))
                except AttributeError:
                    pass
            if snarf:
                irc.reply(msg, '%s' % '; '.join(resp), prefixName = False)
            else:
                irc.reply(msg, '%s' % '; '.join(resp))
        except AttributeError:
            irc.error(msg, 'That doesn\'t appear to be a proper eBay Auction '\
                'page. (%s)' % conf.replyPossibleBug)
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

Class = Ebay

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
