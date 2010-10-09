###
# Copyright (c) 2010, Valentin Lorentz
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

"""
Supybot internationalisation and localisation managment.
"""

__all__ = ['PluginInternationalization']

import sys
import supybot.conf as conf

WAITING_FOR_MSGID = 1
IN_MSGID = 2
WAITING_FOR_MSGSTR = 3
IN_MSGSTR = 4

MSGID = 'msgid "'
MSGSTR = 'msgstr "'

#registerGlobalValue(supybot, 'language',
#    ValidNick('supybot', """Determines the bot's default language.
#    Valid values are things like en, fr, de, etc."""))

def get_plugin_dir(plugin_name):
    filename = sys.modules[plugin_name].__file__
    if filename.endswith("plugin.pyc"):
	return filename[0:-len("plugin.pyc")]
    elif filename.endswith("plugin.py"):
	return filename[0:-len("plugin.py")]
    else:
	return 

i18nClasses = {}

class PluginInternationalization:
    """Internationalization managment for a plugin."""
    def __init__(self, name='supybot'):
	self.name = name
	self.load_locale('toto')
	i18nClasses.update({name: self})
    
    def load_locale(self, locale_name):
	directory = get_plugin_dir(self.name) + 'locale/'
	try:
	    translation_file = open('%s%s.po' % (directory, locale_name), 'ru')
	except IOError: # The translation is unavailable
	    self.translations = {}
	    return
	step = WAITING_FOR_MSGID
	self.translations = {}
	for line in translation_file:
	    line = line[0:-1] # Remove the ending \n
	    
	    if line.startswith(MSGID):
		# Don't check if step is WAITING_FOR_MSGID
		untranslated = ''
		translated = ''
		data = line[len(MSGID):-1]
		if len(data) == 0: # Multiline mode
		    step = IN_MSGID
		else:
		    untranslated += data
		    step = WAITING_FOR_MSGSTR
		    
		    
	    elif step is IN_MSGID and line.startswith('"') and \
			              line.endswith('"'):
		untranslated += line[1:-1]
	    elif step is IN_MSGID and untranslated == '': # Empty MSGID
		step = WAITING_FOR_MSGID
	    elif step is IN_MSGID: # the MSGID is finished
		step = WAITING_FOR_MSGSTR
		
		
	    if step is WAITING_FOR_MSGSTR and line.startswith(MSGSTR):
		data = line[len(MSGSTR):-1]
		if len(data) == 0: # Multiline mode
		    step = IN_MSGID
		else:
		    self.translations.update({untranslated: data})
		    step = WAITING_FOR_MSGID
		    
		    
	    elif step is IN_MSGSTR and line.startswith('"') and \
			               line.endswith('"'):
		untranslated += line[1:-1]
	    elif step is IN_MSGSTR: # the MSGSTR is finished
		step = WAITING_FOR_MSGID
		if translated == '':
		    translated = untranslated
		self.translations.update({untranslated: translated})
    
    def __call__(self, untranslated, *args):
	if len(args) == 0:
	    try:
		return self.translations[untranslated]
	    except KeyError:
		return untranslated
	else:
	    translation = self(untranslated)
	    return translation % args

