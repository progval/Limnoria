###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2010, James McCoy
# Copyright (c) 2010-2021, Valentin Lorentz
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
import json

import supybot.utils as utils
from supybot.commands import *
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
from supybot.dynamicScope import dynamic
_ = PluginInternationalization('Google')

class Google(callbacks.Plugin):
    """
    This plugin provides access to Google services:

    1. translate

       Translates a string
       ``!translate en ar test``

    Check: `Supported language codes`_

    .. _Supported language codes: <https://cloud.google.com/translate/v2/using_rest#language-params>`
    """
    threaded = True

    def _translate(self, sourceLang, targetLang, text):
        headers = dict(utils.web.defaultHeaders)
        headers['User-agent'] = ('Mozilla/5.0 (X11; U; Linux i686) '
                                 'Gecko/20071127 Firefox/2.0.0.11')

        sourceLang = utils.web.urlquote(sourceLang)
        targetLang = utils.web.urlquote(targetLang)

        url = 'https://translate.googleapis.com/translate_a/single?' + \
            utils.web.urlencode({
                'client': 'gtx',
                'dt': 't',
                'sl': sourceLang,
                'tl': targetLang,
                'q': text})
        result = utils.web.getUrlFd(url, headers).read().decode('utf8')
        data = json.loads(result)

        try:
            language = data[2]
        except:
            language = 'unknown'

        if data[0]:
            return (''.join(x[0] for x in data[0]), language)
        else:
            return (_('No translations found.'), language)

    @internationalizeDocstring
    def translate(self, irc, msg, args, sourceLang, targetLang, text):
        """<source language> [to] <target language> <text>

        Returns <text> translated from <source language> into <target
        language>. <source language> and <target language> take language
        codes (not language names), which are listed here:
        https://cloud.google.com/translate/docs/languages
        """
        (text, language) = self._translate(sourceLang, targetLang, text)
        irc.reply(text, language)
    translate = wrap(translate, ['something', 'to', 'something', 'text'])

Class = Google


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
