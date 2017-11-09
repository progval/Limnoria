###
# Copyright (c) 2017, Ken Spencer
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
import hashlib

from supybot.test import *
import supybot.utils as utils

brown_fox = 'The quick brown fox jumped over the lazy dog'

class HashesTestCase(PluginTestCase):
    plugins = ('Hashes',)

    def testHashes(self):
        self.assertResponse('md5 %s' % brown_fox, '08a008a01d498c404b0c30852b39d3b8')
        self.assertResponse('sha %s' % brown_fox, 'f6513640f3045e9768b239785625caa6a2588842')
        self.assertResponse('sha256 %s' % brown_fox, '7d38b5cd25a2baf85ad3bb5b9311383e671a8a142eb302b324d4a5fba8748c69')
        self.assertResponse('sha512 %s' % brown_fox, 'db25330cfa5d14eaadf11a6263371cfa0e70fcd7a63a433b91f2300ca25d45b66a7b50d2f6747995c8fa0ff365b28974792e7acd5624e1ddd0d66731f346f0e7')

    if hasattr(hashlib, 'algorithms_available'):
        def testMkhash(self):
            self.assertResponse('mkhash md5 %s' % brown_fox, '08a008a01d498c404b0c30852b39d3b8')
            self.assertError('mkhash NonExistant %s' % brown_fox)
            self.assertNotError('algorithms')
    else:
        print("Hashes: Skipping algorithms/mkhash tests as 'hashlib.algorithms_available' is not available.")

