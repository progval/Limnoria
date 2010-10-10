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

import re
import sys
import supybot.conf as conf

WAITING_FOR_MSGID = 1
IN_MSGID = 2
WAITING_FOR_MSGSTR = 3
IN_MSGSTR = 4

MSGID = 'msgid "'
MSGSTR = 'msgstr "'

conf.registerGlobalValue(conf.supybot, 'language',
    conf.registry.String('en', """Determines the bot's default language.
    Valid values are things like en, fr, de, etc."""))

def get_plugin_dir(plugin_name):
    filename = sys.modules[plugin_name].__file__
    if filename.endswith(".pyc"):
	filename = filename[0:-1]
    
    allowed_files = ['__init__.py', 'config.py', 'plugin.py', 'test.py']
    for allowed_file in allowed_files:
	if filename.endswith(allowed_file):
	    return filename[0:-len(allowed_file)]
    return 

i18nClasses = {}
internationalizedCommands = {}

def reloadLocals():
    for pluginName in i18nClasses:
	i18nClasses[pluginName].loadLocale()
    for commandHash in internationalizedCommands:
	internationalizeDocstring(internationalizedCommands[commandHash])

class PluginInternationalization:
    """Internationalization managment for a plugin."""
    def __init__(self, name='supybot'):
	self.name = name
	self.loadLocale()
	i18nClasses.update({name: self})
    
    def loadLocale(self, localeName=None):
	if localeName is None:
	    localeName = conf.supybot.language()
	self.currentLocaleName = localeName
	directory = get_plugin_dir(self.name) + 'locale'
	try:
	    translationFile = open('%s/%s.po' % (directory, localeName), 'ru')
	except IOError: # The translation is unavailable
	    self.translations = {}
	    return
	step = WAITING_FOR_MSGID
	self.translations = {}
	for line in translationFile:
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
		    step = IN_MSGSTR
		else:
		    self._translate(untranslated, data)
		    step = WAITING_FOR_MSGID
		    
		    
	    elif step is IN_MSGSTR and line.startswith('"') and \
			               line.endswith('"'):
		translated += line[1:-1]
	    elif step is IN_MSGSTR: # the MSGSTR is finished
		step = WAITING_FOR_MSGID
		if translated == '':
		    translated = untranslated
		self._translate(untranslated, translated)
    
    def _translate(self, untranslated, translated):
	self.translations.update({self._parse(untranslated): 
						    self._parse(translated)})
    
    def _parse(self, string):
	return str.replace(string, '\\n', '\n') # Replace \\n by \n
    
    def __call__(self, untranslated, *args):
	if self.currentLocaleName != conf.supybot.language():
	    # If the locale has been changed
	    reloadLocals()
	if len(args) == 0:
	    try:
		return self.translations[untranslated]
	    except KeyError:
		return untranslated
	else:
	    translation = self(untranslated)
	    return translation % args


def internationalizeDocstring(obj):
    # FIXME: check if the plugin has an _ object
    internationalizedCommands.update({hash(obj): obj})
    obj.__doc__=sys.modules[obj.__module__]._(obj.__doc__)
    return obj
