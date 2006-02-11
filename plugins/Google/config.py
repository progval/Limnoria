###
# Copyright (c) 2005, Jeremiah Fincher
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

import google

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    output('To use Google\'t Web Services, you must have a license key.')
    if yn('Do you have a license key?'):
        key = something('What is it?')
        while len(key) != 32:
            output('That\'s not a valid Google license key.')
            if yn('Are you sure you have a valid Google license key?'):
                key = something('What is it?')
            else:
                key = ''
                break
        if key:
            conf.registerPlugin('Google', True)
            conf.supybot.plugins.Google.licenseKey.setValue(key)
        output("""The Google plugin has the functionality to watch for URLs
                  that match a specific pattern. (We call this a snarfer)
                  When supybot sees such a URL, it will parse the web page
                  for information and reply with the results.

                  Google has two available snarfers: Google Groups link
                  snarfing and a google search snarfer.""")
        if yn('Do you want the Google Groups link snarfer enabled by '
            'default?'):
            conf.supybot.plugins.Google.groupsSnarfer.setValue(True)
        if yn('Do you want the Google search snarfer enabled by default?'):
            conf.supybot.plugins.Google.searchSnarfer.setValue(True)
    else:
        output("""You'll need to get a key before you can use this plugin.
                  You can apply for a key at http://www.google.com/apis/""")

class LicenseKey(registry.String):
    def setValue(self, s):
        if s and len(s) != 32:
            raise registry.InvalidRegistryValue, 'Invalid Google license key.'
        try:
            s = s or ''
            registry.String.setValue(self, s)
            if s:
                google.setLicense(self.value)
        except AttributeError:
            if world and not world.dying: # At shutdown world can be None.
                raise callbacks.Error, \
                      'It appears that the initial import of ' \
                      'our underlying google.py module has ' \
                      'failed.  Once the cause of that problem ' \
                      'has been diagnosed and fixed, the bot ' \
                      'will need to be restarted in order to ' \
                      'load this plugin.'

class Language(registry.OnlySomeStrings):
    validStrings = ['lang_' + s for s in 'ar zh-CN zh-TW cs da nl en et fi fr '
                                         'de el iw hu is it ja ko lv lt no pt '
                                         'pl ro ru es sv tr'.split()]
    validStrings.append('')
    def normalize(self, s):
        if not s.startswith('lang_'):
            s = 'lang_' + s
        if not s.endswith('CN') or s.endswith('TW'):
            s = s.lower()
        else:
            s = s.lower()[:-2] + s[-2:]
        return s

Google = conf.registerPlugin('Google')
conf.registerChannelValue(Google, 'groupsSnarfer',
    registry.Boolean(False, """Determines whether the groups snarfer is
    enabled.  If so, URLs at groups.google.com will be snarfed and their
    group/title messaged to the channel."""))
conf.registerChannelValue(Google, 'searchSnarfer',
    registry.Boolean(False, """Determines whether the search snarfer is
    enabled.  If so, messages (even unaddressed ones) beginning with the word
    'google' will result in the first URL Google returns being sent to the
    channel."""))
conf.registerChannelValue(Google, 'colorfulFilter',
    registry.Boolean(False, """Determines whether the word 'google' in the
    bot's output will be made colorful (like Google's logo)."""))
conf.registerChannelValue(Google, 'bold',
    registry.Boolean(True, """Determines whether results are bolded."""))
conf.registerChannelValue(Google, 'maximumResults',
    registry.PositiveInteger(10, """Determines the maximum number of results
    returned from the google command."""))
conf.registerChannelValue(Google, 'defaultLanguage',
    Language('lang_en', """Determines what default language is used in
    searches.  If left empty, no specific language will be requested."""))
conf.registerChannelValue(Google, 'safeSearch',
    registry.Boolean(True, "Determines whether safeSearch is on by default."))
conf.registerGlobalValue(Google, 'licenseKey',
    LicenseKey('', """Sets the Google license key for using Google's Web
    Services API.  This is necessary before you can do any searching with this
    module.""", private=True))

conf.registerGroup(Google, 'state')
conf.registerGlobalValue(Google.state, 'searches',
    registry.Integer(0, """Used to keep the total number of searches Google has
    done for this bot.  You shouldn't modify this."""))
conf.registerGlobalValue(Google.state, 'time',
    registry.Float(0.0, """Used to keep the total amount of time Google has
    spent searching for this bot.  You shouldn't modify this."""))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
