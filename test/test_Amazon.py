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

from testsupport import *

class AmazonTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('Amazon',)
    def setUp(self):
        PluginTestCase.setUp(self)
        self.assertNotError('licensekey test')

    def testIsbn(self):
        self.assertHelp('isbn')
        self.assertRegexp('isbn 0738203793', r'Buckminster Fuller\'s Universe')
        self.assertRegexp('isbn --url 0738203793', r'Buck.*/exec/obidos/ASIN')

    def testAsin(self):
        self.assertHelp('asin')
        self.assertRegexp('asin B00005JM5E', r'Pirates of the Caribbean')
        self.assertRegexp('asin --url B00005JM5E', r'Pirate.*ASIN/B00005JM5E')

    def testUpc(self):
        self.assertHelp('upc')
        self.assertRegexp('upc 093624586425', r'Short Bus')
        self.assertRegexp('upc --url 093624586425', r'Short Bus.*/exec/obidos')

    def testAuthor(self):
        self.assertHelp('author')
        self.assertRegexp('author torvalds', r'Just for Fun')
        self.assertRegexp('author --url torvalds', r'Linus.*/exec/obidos')

    def testArtist(self):
        self.assertHelp('artist')
        self.assertRegexp('artist rahzel', r'Audio CD')
        self.assertRegexp('artist --url rahzel', r'Audio CD.*/exec/obidos')
        self.assertRegexp('artist --classical rahzel', r'No items were found')
        self.assertRegexp('artist --classical vivaldi', r'Audio CD')

    def testActor(self):
        self.assertHelp('actor')
        self.assertRegexp('actor bruce lee', r'DVD')
        self.assertRegexp('actor --url bruce lee', r'DVD.*/exec/obidos/')
        self.assertRegexp('actor --vhs bruce lee', r'VHS Tape')
        self.assertRegexp('actor --video bruce lee', r'DVD|VHS Tape')

    def testDirector(self):
        self.assertHelp('director')
        self.assertRegexp('director gore verbinski', r'DVD')
        self.assertRegexp('director --url gore verbinski',
                          r'DVD.*/exec/obidos/')
        self.assertRegexp('director --vhs gore verbinski', r'VHS Tape')
        self.assertRegexp('director --video gore verbinski', r'DVD|VHS Tape')

    def testManufacturer(self):
        self.assertHelp('manufacturer')
        self.assertRegexp('manufacturer iomega', r'Iomega')
        self.assertRegexp('manufacturer --url iomega',
                          r'Iomega.*/exec/obidos/')
        self.assertRegexp('manufacturer --electronics plextor', r'Plextor')
        self.assertRegexp('manufacturer --kitchen henckels', r'Henckels')
        self.assertRegexp('manufacturer --videogames ea', r'Madden')
        self.assertRegexp('manufacturer --software adobe', r'Photoshop')
        self.assertRegexp('manufacturer --photo kodak', r'Kodak')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

