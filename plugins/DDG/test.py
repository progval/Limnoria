###
# Copyright (c) 2014-2020, James Lu <james@overdrivenetworks.com>
# Copyright (c) 2020-2021, Valentin Lorentz
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

import supybot.conf as conf
from supybot.test import *
from unittest.mock import patch

class DDGTestCase(PluginTestCase):
    plugins = ('DDG',)

    def testSearchFormatAndSeparator(self):
        ddg = self.irc.getCallback('DDG')
        results = [('Title', 'snippet text', 'https://example.com/'),
                   ('Other', 'more text', 'https://example.org/')]
        with patch.object(ddg, 'search_core', return_value=results):
            self.assertResponse(
                'ddg search foo',
                '\x02Title\x02 - snippet text <https://example.com/>, '
                '\x02Other\x02 - more text <https://example.org/>')
            with conf.supybot.plugins.DDG.separator.context(' | '):
                with conf.supybot.plugins.DDG.format.context(
                        '$url - $title $snippet'):
                    self.assertResponse(
                        'ddg search foo',
                        '<https://example.com/> - Title snippet text | '
                        '<https://example.org/> - Other more text')

    if network:

        def testSearch(self):
            self.assertRegexp(
                'ddg search wikipedia', r'Wikipedia.*? - .*?https?\:\/\/')
            self.assertRegexp(
                'ddg search en.wikipedia.org',
                'Wikipedia, the free encyclopedia\x02 - '
                '.* <https://en.wikipedia.org/>')
            with conf.supybot.plugins.DDG.region.context('fr-fr'):
                self.assertRegexp(
                    'ddg search wikipedia',
                    r'Wikipédia, l\'encyclopédie libre - .*?https?\:\/\/')

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
