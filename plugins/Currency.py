#!/usr/bin/env python

###
# Copyright (c) 2004, James Vega
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
Provides commands which interface with various websites to perform currency
conversions.
"""

__revision__ = "$Id$"
__author__ = ''

import re

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.webutils as webutils
import supybot.callbacks as callbacks

class CurrencyCommand(registry.String):
    def setValue(self, s):
        m = Currency.currencyCommands
        if s not in m:
            raise registry.InvalidRegistryValue,\
                  'Command must be one of %s' % utils.commaAndify(m)
        else:
            method = getattr(Currency, s)
            Currency.convert.im_func.__doc__ = method.__doc__
        registry.String.setValue(self, s)

class Currency(callbacks.Privmsg):
    currencyCommands = ['xe', 'yahoo']
    threaded = True

    _symbolError = 'Currency must be denoted by it\'s 3-letter symbol.'
    def convert(self, irc, msg, args):
        # This specifically does not have a docstring.
        channel = None
        if ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
        realCommandName = self.registryValue('command', channel)
        realCommand = getattr(self, realCommandName)
        realCommand(irc, msg, args)

    _xeCurrError = re.compile(r'The following error occurred:<BR><BR>\s+'
                              r'(.*)</body>', re.I | re.S)
    _xeConvert = re.compile(r'<TD[^>]+><FONT[^>]+>\s+([\d.]+\s+\w{3}\s+='
                            r'\s+[\d.]+\s+\w{3})', re.I | re.S)
    def xe(self, irc, msg, args):
        """[<number>] <currency1> to <currency2>

        Converts from <currency1> to <currency2>.  If number isn't given, it
        defaults to 1.
        """
        (number, curr1, curr2) = privmsgs.getArgs(args, required=2,
                                                  optional=1)
        try:
            number = int(number)
        except ValueError:
            curr2 = curr1
            curr1 = number
            number = 1
        curr1 = curr1.lower()
        curr2 = curr2.lower()
        if curr2.startswith('to '):
            curr2 = curr2[3:]
        if len(curr1) != 3 and len(curr2) != 3:
            irc.error(self._symbolError)
            return
        url = 'http://www.xe.com/ucc/convert.cgi?Amount=%s&From=%s&To=%s'
        try:
            text = webutils.getUrl(url % (number, curr1, curr2))
        except webutils.WebError, e:
            irc.error(str(e))
            return
        err = self._xeCurrError.search(text)
        if err is not None:
            irc.error('You used an incorrect currency symbol.')
            return
        conv = self._xeConvert.search(text)
        if conv is not None:
            resp = conv.group(1).split()
            resp[0] = str(float(resp[0]) * number)
            if resp[0].endswith('.0'):
                resp[0] = '%s.00' % resp[0][:-2]
            resp[3] = str(float(resp[3]) * number)
            irc.reply(' '.join(resp))
            return
        else:
            irc.error('XE must\'ve changed the format of their site.')
            return

    _yahooConvert = re.compile(r'\w{6}=X</a></td><td class[^>]+><b>([\d.]+)'
                               r'</b></td><td class[^>]+>\w{3} \d\d?</td><td'
                               r' class=[^>]+>[\d.]+</td><td class[^>]+><b>'
                               r'([\d,]+(?:.0{2}))', re.I | re.S)
    def yahoo(self, irc, msg, args):
        """[<number>] <currency1> to <currency2>

        Converts from <currency1> to <currency2>.  If number isn't given, it
        defaults to 1.
        """
        (number, curr1, curr2) = privmsgs.getArgs(args, required=2,
                                                  optional=1)
        try:
            number = int(number)
        except ValueError:
            curr2 = curr1
            curr1 = number
            number = 1
        curr1 = curr1.lower()
        curr2 = curr2.lower()
        if curr2.startswith('to '):
            curr2 = curr2[3:]
        if len(curr1) != 3 and len(curr2) != 3:
            irc.error(self._symbolError)
            return
        url = 'http://finance.yahoo.com/currency/convert?amt=%s&from=%s&'\
              'to=%s&submit=Convert'
        try:
            text = webutils.getUrl(url % (number, curr1, curr2))
        except webutils.WebError, e:
            irc.error(str(e))
            return
        conv = self._yahooConvert.search(text)
        if conv is not None:
            resp = [conv.group(1), curr1.upper(), '=',
                    conv.group(2).replace(',', ''), curr2.upper()]
            if '.' not in resp[0]:
                resp[0] = '%s.00' % resp[0]
            elif resp[0].endswith('.0'):
                resp[0] = '%.00' % resp[:-2]
            irc.reply(' '.join(resp))
            return
        else:
            irc.error('Either you used the wrong currency symbol(s) or Yahoo '
                      'changed the format of their site.')
            return

conf.registerPlugin('Currency')
conf.registerChannelValue(conf.supybot.plugins.Currency, 'command',
    CurrencyCommand('yahoo', """Sets the default command to use when retrieving
    the currency conversion.  Command must be one of %s.""" %
    utils.commaAndify(Currency.currencyCommands, And='or')))

Class = Currency

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
