###
# Copyright (c) 2004, Jeremiah Fincher
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

try:
    import pytz
except ImportError:
    has_pytz = False
else:
    has_pytz = True

try:
    import dateutil
except ImportError:
    has_dateutil = False
else:
    has_dateutil = True

try:
    import ddate.base
except ImportError:
    has_ddate = False
else:
    has_ddate = True

try:
    from unittest import skipIf
except ImportError: # Python 2.6
    def skipIf(cond, reason):
        if cond:
            print('Skipped: %s' % reason)
            def decorator(f):
                return None
        else:
            def decorator(f):
                return f
        return decorator



class TimeTestCase(PluginTestCase):
    plugins = ('Time','Utilities')
    def testSeconds(self):
        self.assertResponse('seconds 1s', '1')
        self.assertResponse('seconds 10s', '10')
        self.assertResponse('seconds 1m', '60')
        self.assertResponse('seconds 1m 1s', '61')
        self.assertResponse('seconds 1h', '3600')
        self.assertResponse('seconds 1h 1s', '3601')
        self.assertResponse('seconds 1d', '86400')
        self.assertResponse('seconds 1d 1s', '86401')
        self.assertResponse('seconds 2s', '2')
        self.assertResponse('seconds 2m', '120')
        self.assertResponse('seconds 2d 2h 2m 2s', '180122')
        self.assertResponse('seconds 1s', '1')
        self.assertResponse('seconds 1y 1s', '31536001')
        self.assertResponse('seconds 1w 1s', '604801')

    def testNoErrors(self):
        self.assertNotError('ctime')
        self.assertNotError('time %Y')

    @skipIf(not has_pytz, 'pytz is missing')
    def testTztime(self):
        self.assertNotError('tztime Europe/Paris')
        self.assertError('tztime Europe/Gniarf')

    @skipIf(not has_dateutil, 'python-dateutil is missing')
    def testUntil(self):
        self.assertNotError('echo [until 4:00]')
        self.assertNotError('echo [at now]')
    def testNoNestedErrors(self):
        self.assertNotError('echo [seconds 4m]')

    @skipIf(not has_ddate, 'ddate is missing')
    def testDDate(self):
        self.assertNotError('ddate')
        self.assertHelp('ddate 0 0 0') # because nonsense was put in
        self.assertHelp('ddate -1 1 1') # because nonsense was put in
        self.assertHelp('ddate -1 -1 -1') # because nonsense was put in
        # plugin.py:223 would catch these otherwise
        self.assertResponse('ddate 1 1 1', 'Sweetmorn, the 1st day of Chaos in the YOLD 1167') # make sure the laws of physics and time aren't out of wack

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
