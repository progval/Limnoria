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
    def testEbay(self):
        self.assertResponse('ebay --link 3053641570',
            'http://cgi.ebay.com/ws/eBayISAPI.dll?ViewItem&item=3053641570')

    def testSnarfer(self):
        self.assertRegexp('http://cgi.ebay.com/ws/eBayISAPI.dll?ViewItem'\
            '&category=176&item=3053767552', '.*Cisco NP-4T.*Serial Module'\
            '.*US \$74\.95.*')
        self.assertRegexp('http://cgi.ebay.com/ws/eBayISAPI.dll?ViewItem&'\
            'category=28033&item=3053353651', '.*Cisco 2524 Router - NO '\
            'RESERVE.*izontech \(.*')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:


