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

from supybot.test import *

class ShrinkUrlTestCase(ChannelPluginTestCase):
    plugins = ('ShrinkUrl',)
    if network:
        def testTinyurl(self):
            try:
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(False)
                self.assertRegexp(
                    'shrinkurl tiny http://sourceforge.net/tracker/?'
                    'func=add&group_id=58965&atid=489447',
                    r'http://tinyurl.com/rqac')
                conf.supybot.plugins.ShrinkUrl.default.setValue('tiny')
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(True)
                self.assertRegexp(
                    'shrinkurl tiny http://sourceforge.net/tracker/?'
                    'func=add&group_id=58965&atid=489447',
                    r'http://tinyurl.com/rqac')
            finally:
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(False)

        def testTinysnarf(self):
            try:
                conf.supybot.snarfThrottle.setValue(1)
                conf.supybot.plugins.ShrinkUrl.default.setValue('tiny')
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(True)
                self.assertSnarfRegexp(
                    'http://sourceforge.net/tracker/?func=add&'
                    'group_id=58965&atid=489447',
                    r'http://tinyurl.com/rqac.* \(at')
                self.assertSnarfRegexp(
                    'http://www.urbandictionary.com/define.php?'
                    'term=all+your+base+are+belong+to+us',
                    r'http://tinyurl.com/u479.* \(at')
            finally:
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(False)

        def testLnurl(self):
            try:
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(False)
                self.assertRegexp(
                    'shrinkurl ln http://sourceforge.net/tracker/?'
                    'func=add&group_id=58965&atid=489447',
                    r'http://ln-s.net/25Z')
                conf.supybot.plugins.ShrinkUrl.default.setValue('ln')
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(True)
                self.assertRegexp(
                    'shrinkurl ln http://sourceforge.net/tracker/?'
                    'func=add&group_id=58965&atid=489447',
                    r'http://ln-s.net/25Z')
            finally:
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(False)

        def testLnsnarf(self):
            try:
                conf.supybot.snarfThrottle.setValue(1)
                conf.supybot.plugins.ShrinkUrl.default.setValue('ln')
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(True)
                self.assertSnarfRegexp(
                    'http://sourceforge.net/tracker/?func=add&'
                    'group_id=58965&atid=489447',
                    r'http://ln-s.net/25Z.* \(at')
                self.assertSnarfRegexp(
                    'http://www.urbandictionary.com/define.php?'
                    'term=all+your+base+are+belong+to+us',
                    r'http://ln-s.net/2\$K.* \(at')
            finally:
                conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(False)

        def testNonSnarfing(self):
            tiny = conf.supybot.plugins.ShrinkUrl.shrinkSnarfer()
            snarf = conf.supybot.plugins.ShrinkUrl.nonSnarfingRegexp()
            try:
                conf.supybot.snarfThrottle.setValue(1)
                conf.supybot.plugins.ShrinkUrl.default.setValue('tiny')
                conf.supybot.plugins.ShrinkUrl.nonSnarfingRegexp.set('m/sf/')
                conf.supybot.plugins.ShrinkUrl.minimumLength.setValue(10)
                try:
                    conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(True)
                    self.assertSnarfNoResponse('http://sf.net/', 2)
                    self.assertSnarfRegexp('http://sourceforge.net/',
                                             r'http://tinyurl.com/7vm7.* \(at')
                finally:
                    conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(tiny)
            finally:
                conf.supybot.plugins.ShrinkUrl.nonSnarfingRegexp.setValue(snarf)



# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

