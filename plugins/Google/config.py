###
# Copyright (c) 2005, Jeremiah Fincher
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

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Google')

def configure(advanced):
    from supybot.questions import output, yn
    conf.registerPlugin('Google', True)
    output(_("""The Google plugin has the functionality to watch for URLs
              that match a specific pattern. (We call this a snarfer)
              When supybot sees such a URL, it will parse the web page
              for information and reply with the results."""))
    if yn(_('Do you want the Google search snarfer enabled by default?')):
        conf.supybot.plugins.Google.searchSnarfer.setValue(True)

class Language(registry.OnlySomeStrings):
    transLangs = {'Afrikaans': 'af', 'Albanian': 'sq', 'Amharic': 'am',
                  'Arabic': 'ar', 'Armenian': 'hy', 'Azerbaijani': 'az',
                  'Basque': 'eu', 'Belarusian': 'be', 'Bengali': 'bn',
                  'Bulgarian': 'bg', 'Burmese': 'my', 'Catalan': 'ca',
                  'Chinese': 'zh', 'Chinese_simplified': 'zh-CN',
                  'Chinese_traditional': 'zh-TW', 'Croatian': 'hr',
                  'Czech': 'cs', 'Danish': 'da', 'Dhivehi': 'dv',
                  'Dutch': 'nl', 'English': 'en', 'Esperanto': 'eo',
                  'Estonian': 'et', 'Filipino': 'tl', 'Finnish': 'fi',
                  'French': 'fr', 'Galician': 'gl', 'Georgian': 'ka',
                  'German': 'de', 'Greek': 'el', 'Gujarati': 'gu',
                  'Hebrew': 'iw', 'Hindi': 'hi', 'Hungarian': 'hu',
                  'Icelandic': 'is', 'Indonesian': 'id', 'Inuktitut': 'iu',
                  'Italian': 'it', 'Japanese': 'ja', 'Kannada': 'kn',
                  'Kazakh': 'kk', 'Khmer': 'km', 'Korean': 'ko',
                  'Kurdish': 'ku', 'Kyrgyz': 'ky', 'Laothian': 'lo',
                  'Latvian': 'lv', 'Lithuanian': 'lt', 'Macedonian': 'mk',
                  'Malay': 'ms', 'Malayalam': 'ml', 'Maltese': 'mt',
                  'Marathi': 'mr', 'Mongolian': 'mn', 'Nepali': 'ne',
                  'Norwegian': 'no', 'Oriya': 'or', 'Pashto': 'ps',
                  'Persian': 'fa', 'Polish': 'pl', 'Portuguese': 'pt-PT',
                  'Punjabi': 'pa', 'Romanian': 'ro', 'Russian': 'ru',
                  'Sanskrit': 'sa', 'Serbian': 'sr', 'Sindhi': 'sd',
                  'Sinhalese': 'si', 'Slovak': 'sk', 'Slovenian': 'sl',
                  'Spanish': 'es', 'Swedish': 'sv', 'Tajik': 'tg',
                  'Tamil': 'ta', 'Tagalog': 'tl', 'Telugu': 'te',
                  'Thai': 'th', 'Tibetan': 'bo', 'Turkish': 'tr',
                  'Ukranian': 'uk', 'Urdu': 'ur', 'Uzbek': 'uz',
                  'Uighur': 'ug', 'Vietnamese': 'vi',
                  'Detect language': 'auto'}
    validStrings = ['lang_' + s for s in transLangs.values()]
    validStrings.append('')
    def normalize(self, s):
        if s and not s.startswith('lang_'):
            s = 'lang_' + s
        if not s.endswith('CN') or s.endswith('TW') or s.endswith('PT'):
            s = s.lower()
        else:
            s = s.lower()[:-2] + s[-2:]
        return s

class NumSearchResults(registry.PositiveInteger):
    """Value must be 1 <= n <= 8"""
    def setValue(self, v):
        if v > 8:
            self.error()
        super(self.__class__, self).setValue(v)

class SafeSearch(registry.OnlySomeStrings):
    validStrings = ['active', 'moderate', 'off']

Google = conf.registerPlugin('Google')
conf.registerGlobalValue(Google, 'referer',
    registry.String('', _("""Determines the URL that will be sent to Google for
    the Referer field of the search requests.  If this value is empty, a
    Referer will be generated in the following format:
    http://$server/$botName""")))
conf.registerChannelValue(Google, 'baseUrl',
    registry.String('google.com', _("""Determines the base URL used for
    requests.""")))
conf.registerChannelValue(Google, 'searchSnarfer',
    registry.Boolean(False, _("""Determines whether the search snarfer is
    enabled.  If so, messages (even unaddressed ones) beginning with the word
    'google' will result in the first URL Google returns being sent to the
    channel.""")))
conf.registerChannelValue(Google, 'colorfulFilter',
    registry.Boolean(False, _("""Determines whether the word 'google' in the
    bot's output will be made colorful (like Google's logo).""")))
conf.registerChannelValue(Google, 'bold',
    registry.Boolean(True, _("""Determines whether results are bolded.""")))
conf.registerChannelValue(Google, 'oneToOne',
    registry.Boolean(False, _("""Determines whether results are sent in
    different lines or all in the same one.""")))
conf.registerChannelValue(Google, 'maximumResults',
    NumSearchResults(3, _("""Determines the maximum number of results returned
    from the google command.""")))
conf.registerChannelValue(Google, 'defaultLanguage',
    Language('lang_'+ _('en'), _("""Determines what default language is used in
    searches.  If left empty, no specific language will be requested.""")))
conf.registerChannelValue(Google, 'searchFilter',
    SafeSearch('moderate', _("""Determines what level of search filtering to use
    by default.  'active' - most filtering, 'moderate' - default filtering,
    'off' - no filtering""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
