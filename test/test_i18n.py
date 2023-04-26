# -*- coding: utf8 -*-
###
# Copyright (c) 2012-2021, Valentin Lorentz
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
from supybot.commands import wrap
from supybot.i18n import PluginInternationalization, internationalizeDocstring
import supybot.conf as conf

msg_en = 'The operation succeeded.'
msg_fr = 'Opération effectuée avec succès.'

_ = PluginInternationalization()

@internationalizeDocstring
def foo():
    """The operation succeeded."""
    pass

@wrap
def bar():
    """The operation succeeded."""
    pass

class I18nTestCase(SupyTestCase):
    def testPluginInternationalization(self):
        self.assertEqual(_(msg_en), msg_en)
        with conf.supybot.language.context('fr'):
            self.assertEqual(_(msg_en), msg_fr)
        conf.supybot.language.setValue('en')
        self.assertEqual(_(msg_en), msg_en)
        multiline = '%s\n\n%s' % (msg_en, msg_en)
        self.assertEqual(_(multiline), multiline)

    @retry()
    def testDocstring(self):
        self.assertEqual(foo.__doc__, msg_en)
        self.assertEqual(bar.__doc__, msg_en)
        with conf.supybot.language.context('fr'):
            self.assertEqual(foo.__doc__, msg_fr)
            self.assertEqual(bar.__doc__, msg_fr)
        self.assertEqual(foo.__doc__, msg_en)
        self.assertEqual(bar.__doc__, msg_en)
