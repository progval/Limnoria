#!/usr/bin/env python

###
# Copyright (c) 2003-2004, James Vega
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

from testsupport import *

import supybot.plugins.Sourceforge
Sf = conf.supybot.plugins.Sourceforge

class SourceforgeTest(ChannelPluginTestCase):
    plugins = ('Sourceforge',)
    config = {'supybot.plugins.Sourceforge.bold': False}
    if network:
        def testAny(self):
            m = self.getMsg('bugs --any gaim')
            self.failUnless(m, 'No response from Sourceforge.')
            match = re.search(r'#(\d+)', m.args[1])
            self.failUnless(match, 'no bug # found: %r' % m.args[1])
            n = re.search('#(\d+)', m.args[1]).group(1)
            self.assertNotError('tracker %s' % n)
            m = self.getMsg('rfes --any gaim')
            self.failUnless(m, 'No response from Sourceforge.')
            match = re.search(r'#(\d+)', m.args[1])
            self.failUnless(match, 'no bug # found: %r' % m.args[1])
            n = re.search('#(\d+)', m.args[1]).group(1)
            self.assertNotError('tracker %s' % n)

        def testClosed(self):
            m = self.getMsg('bugs --closed gaim')
            self.failUnless(m, 'No response from Sourceforge.')
            match = re.search(r'#(\d+)', m.args[1])
            self.failUnless(match, 'no bug # found: %r' % m.args[1])
            n = re.search('#(\d+)', m.args[1]).group(1)
            self.assertNotError('tracker %s' % n)
            m = self.getMsg('patches --closed gaim')
            self.failUnless(m, 'No response from Sourceforge.')
            match = re.search(r'#(\d+)', m.args[1])
            self.failUnless(match, 'no bug # found: %r' % m.args[1])
            n = re.search('#(\d+)', m.args[1]).group(1)
            self.assertNotError('tracker %s' % n)

        def testDeleted(self):
            m = self.getMsg('bugs --deleted gaim')
            self.failUnless(m, 'No response from Sourceforge.')
            match = re.search(r'#(\d+)', m.args[1])
            self.failUnless(match, 'no bug # found: %r' % m.args[1])
            n = re.search('#(\d+)', m.args[1]).group(1)
            self.assertNotError('tracker %s' % n)
            m = self.getMsg('rfes --deleted gaim')
            self.failUnless(m, 'No response from Sourceforge.')
            match = re.search(r'#(\d+)', m.args[1])
            self.failUnless(match, 'no bug # found: %r' % m.args[1])
            n = re.search('#(\d+)', m.args[1]).group(1)
            self.assertNotError('tracker %s' % n)

        def testOpen(self):
            m = self.getMsg('bugs --open gaim')
            self.failUnless(m, 'No response from Sourceforge.')
            match = re.search(r'#(\d+)', m.args[1])
            self.failUnless(match, 'no bug # found: %r' % m.args[1])
            n = re.search('#(\d+)', m.args[1]).group(1)
            self.assertNotError('tracker %s' % n)
            m = self.getMsg('rfes --open gaim')
            self.failUnless(m, 'No response from Sourceforge.')
            match = re.search(r'#(\d+)', m.args[1])
            self.failUnless(match, 'no bug # found: %r' % m.args[1])
            n = re.search('#(\d+)', m.args[1]).group(1)
            self.assertNotError('tracker %s' % n)

        def testTrackers(self):
            self.assertHelp('bugs')
            self.assertRegexp('bugs 83423', 'use the tracker')
            try:
                original = Sf.defaultProject()
                Sf.defaultProject.set('supybot')
                self.assertRegexp('bugs alkjfi83fa8', 'find the Bugs')
                self.assertNotError('rfes gaim')
                self.assertNotError('patches')
            finally:
                Sf.defaultProject.set(original)

        def testDefaultproject(self):
            try:
                original = Sf.defaultProject()
                Sf.defaultProject.setValue('supybot')
                self.assertNotError('bugs')
                Sf.defaultProject.setValue('')
                self.assertHelp('bugs')
            finally:
                Sf.defaultProject.set(original)

        def testTracker(self):
            bug = r'Bug.*Status.*: \w+'
            rfe = r'Feature Request.*Status.*: \w+'
            self.assertRegexp('tracker 589953', bug)
            self.assertRegexp('tracker 712761', rfe)
            self.assertRegexp('tracker 721761', 'Timo Hoenig')
            self.assertRegexp('tracker 851239', 'Nobody/Anonymous')

        def testSnarfer(self):
            s = r'.*Status.*: \w+'
            try:
                original = Sf.trackerSnarfer()
                Sf.trackerSnarfer.setValue(True)
                self.assertSnarfRegexp('http://sourceforge.net/tracker/index.'
                                       'php?func=detail&aid=589953&group_id='
                                       '58965&atid=489447',
                                       s)
                self.assertSnarfRegexp('http://sourceforge.net/tracker/index.'
                                       'php?func=detail&aid=712761&group_id='
                                       '58965&atid=489450',
                                       s)
                self.assertSnarfRegexp('http://sourceforge.net/tracker/index.'
                                       'php?func=detail&aid=540223&group_id='
                                       '235&atid=300235',
                                       s)
                self.assertSnarfRegexp('http://sourceforge.net/tracker/index.'
                                       'php?func=detail&aid=561547&group_id='
                                       '235&atid=200235',
                                       s)
                self.assertSnarfRegexp('http://sourceforge.net/tracker/index.'
                                       'php?func=detail&aid=400942&group_id='
                                       '235&atid=390395',
                                       s)

                # test that it works without index.php
                self.assertSnarfNotError('http://sourceforge.net/tracker/?'
                                         'func=detail&aid=540223&group_id=235&'
                                         'atid=300235')
                # test that it works with www
                self.assertSnarfNotError('http://www.sourceforge.net/tracker/'
                                         'index.php?func=detail&aid=540223&'
                                         'group_id=235&atid=300235')
                # test that it works with www and without index.php
                self.assertSnarfNotError('http://www.sourceforge.net/tracker/?'
                                         'func=detail&aid=540223&group_id=235&'
                                         'atid=300235')
                # test that it works with sf.net
                self.assertSnarfNotError('http://sf.net/tracker/?func=detail&'
                                         'aid=540223&group_id=235&atid=300235')
                # test that it works
                self.assertSnarfNotError('https://sourceforge.net/tracker/?'
                                         'func=detail&atid=105470&aid=827260&'
                                         'group_id=5470')
                self.assertSnarfNoResponse('https://sourceforge.net/tracker/?'
                                           'group_id=58965&atid=489447')
            finally:
                Sf.trackerSnarfer.setValue(original)

        def testTotal(self):
            self.assertRegexp('total bugs gaim', r'\d+ open / \d+ total')
            self.assertRegexp('total rfes gaim', r'\d+ open / \d+ total')
            self.assertError('total bugs lkjfad')
            self.assertError('total rfes lkjfad')

        def testFight(self):
            self.assertRegexp('fight gaim opengaim',
                              r'\'(open|)gaim\': \d+, \'(open|)gaim\': \d+')
            self.assertRegexp('fight --rfes gaim opengaim',
                              r'\'(open|)gaim\': \d+, \'(open|)gaim\': \d+')
            self.assertRegexp('fight --closed gaim opengaim',
                              r'\'(open|)gaim\': \d+, \'(open|)gaim\': \d+')
            m = self.getMsg('fight --bugs gaim opengaim')
            n = self.getMsg('fight --open gaim opengaim')
            o = self.getMsg('fight gaim opengaim')
            self.assertEqual(m, o)
            self.assertEqual(n, o)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
