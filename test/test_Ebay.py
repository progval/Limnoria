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

from test import *

class EbayTest(PluginTestCase, PluginDocumentation):
    plugins = ('Ebay',)
    def testAuction(self):
        self.assertNotError('auction 3053641570')
        # test 'Invalid Item' checking
        self.assertRegexp('auction 2357056673', 'That auction is invalid')
        self.assertError('auction foobar')

    def testSnarfer(self):
        self.assertNotError('ebay config auction-snarfer on')
        self.assertRegexp('http://cgi.ebay.com/ws/eBayISAPI.dll?ViewItem'
                          '&category=176&item=3053767552',
                         r'.*Cisco NP-4T.*Serial Module.*US \$74\.95.*')
        self.assertRegexp('http://cgi.ebay.com/ws/eBayISAPI.dll?ViewItem&'
                          'category=28033&item=3053353651',
                         r'.*Cisco 2524 Router - NO RESERVE.*izontech \(.*')
        # test snarfing other countries
        self.assertRegexp('http://cgi.ebay.ca/ws/eBayISAPI.dll?ViewItem&'
                          'item=3636820075',
                         r'NEW 34" Itech 8.8 Profile')
        self.assertRegexp('http://cgi.ebay.co.uk/ws/eBayISAPI.dll?ViewItem&'
                          'item=2355464443',
                         r'Any Clear Crazy')
        self.assertRegexp('http://cgi.ebay.com.au/ws/eBayISAPI.dll?ViewItem&'
                          'item=2762983161&category=4607',
                         r'Apple Mac G4')
        # test .com/.*/ws/eBat compatibility
        self.assertRegexp('http://cgi.ebay.com/ebaymotors/ws/eBayISAPI.dll?'
                          'ViewItem&item=2439393310&category=33708',
                         r'88-89 CRX amber')

    def testConfigSnarfer(self):
        self.assertNotError('ebay config auction-snarfer off')
        self.assertNoResponse('http://cgi.ebay.com/ebaymotors/ws/'
                              'eBayISAPI.dll?ViewItem&item=2439393310&'
                              'category=33708')
        self.assertNotError('ebay config auction-snarfer on')
        self.assertNotError('http://cgi.ebay.com/ebaymotors/ws/'
                            'eBayISAPI.dll?ViewItem&item=2439393310&'
                            'category=33708')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
