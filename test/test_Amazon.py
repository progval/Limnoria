#!/usr/bin/env python

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

from testsupport import *

LICENSE_KEY = 'AMAZONS_NOT_CHECKING_KEYS'

if LICENSE_KEY != 'INITIAL_NON_LICENSE_KEY' and network:
    class AmazonTestCase(PluginTestCase):
        plugins = ('Amazon',)
        def setUp(self):
            PluginTestCase.setUp(self)
            conf.supybot.plugins.amazon.licensekey.set(LICENSE_KEY)

        def testUnicode(self):
            self.assertNotError('artist husker du')

        def testIsbn(self):
            self.assertHelp('isbn')
            self.assertRegexp('isbn 0738203793',
                              r'Buckminster Fuller\'s Universe')
            self.assertRegexp('isbn --url 0738203793',
                              r'Buck.*/exec/obidos/ASIN')

        def testAsin(self):
            self.assertHelp('asin')
            self.assertRegexp('asin B00005JM5E', r'Pirates of the Caribbean')
            self.assertRegexp('asin --url B00005JM5E',
                              r'Pirate.*ASIN/B00005JM5E')

        def testUpc(self):
            self.assertHelp('upc')
            self.assertRegexp('upc 093624586425', r'Short Bus')
            self.assertRegexp('upc --url 093624586425',
                              r'Short Bus.*/exec/obidos')

        def testAuthor(self):
            self.assertHelp('amazon author')
            self.assertNotError('amazon author torvalds')
            self.assertNotError('amazon author --url torvalds')

        def testArtist(self):
            self.assertHelp('artist')
            self.assertNotError('artist rahzel')
            self.assertNotError('artist --url rahzel')
            self.assertError('artist --classical rahzel')
            self.assertNotError('artist --classical vivaldi')

        def testActor(self):
            self.assertHelp('actor')
            self.assertNotError('actor bruce lee')
            self.assertNotError('actor --url bruce lee')
            self.assertNotError('actor --vhs bruce lee')
            self.assertNotError('actor --video bruce lee')

        def testDirector(self):
            self.assertHelp('director')
            self.assertNotError('director gore verbinski')
            self.assertNotError('director --url gore verbinski')
            self.assertNotError('director --vhs gore verbinski')
            self.assertNotError('director --video gore verbinski')

        def testManufacturer(self):
            self.assertHelp('manufacturer')
            self.assertNotError('manufacturer iomega')
            self.assertNotError('manufacturer --url iomega')
            self.assertNotError('manufacturer --electronics plextor')
            self.assertNotError('manufacturer --kitchen henckels')
            self.assertNotError('manufacturer --videogames ea')
            self.assertNotError('manufacturer --software adobe')
            self.assertNotError('manufacturer --photo kodak')

        def testBooks(self):
            self.assertHelp('books')
            self.assertNotError('books knowledge of the holy')

        def testVideos(self):
            self.assertHelp('videos')
            self.assertNotError('videos zim')
            self.assertNotError('videos --vhs samuel jackson')

        def testSnarfer(self):
            try:
                orig = conf.supybot.plugins.Amazon.linkSnarfer()
                conf.supybot.plugins.Amazon.linkSnarfer.setValue(True)
                self.assertRegexp('http://www.amazon.com/exec/obidos/tg/'
                                  'detail/-/B0001CSI3S/sr=1-2/qid=1076951698'
                                  '/ref=sr_1_2/002-0542016-6528044?v=glance&'
                                  'n=1044448&s=apparel',
                                  r'.*Spring Parka.*')
            finally:
                conf.supybot.plugins.Amazon.linkSnarfer.setValue(orig)
            self.assertNoResponse('http://www.amazon.com/exec/obidos/tg/detail'
                                  '/-/B0001CSI3S/sr=1-2/qid=1076951698/ref='
                                  'sr_1_2/002-0542016-6528044?v=glance&n='
                                  '1044448&s=apparel')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

