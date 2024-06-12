###
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

"""
Supybot internationalisation and localisation managment.
"""

__all__ = ['PluginInternationalization', 'internationalizeDocstring']

import os
import sys
import weakref
conf = None
# Don't import conf here ; because conf needs this module

WAITING_FOR_MSGID = 1
IN_MSGID = 2
WAITING_FOR_MSGSTR = 3
IN_MSGSTR = 4
NEXT_IS_FUZZY = 5

MSGID = 'msgid "'
MSGSTR = 'msgstr "'
FUZZY = '#, fuzzy'

currentLocale = 'en'
SUPPORTED_LANGUAGES = ['de', 'en', 'es', 'fi', 'fr', 'it', 'ru']

class PluginNotFound(Exception):
    pass

def getLocaleFromRegistryCache():
    """Called by the 'supybot' script. Gets the locale name before conf is
    loaded."""
    global currentLocale
    import supybot.registry as registry
    try:
        currentLocale = registry._cache['supybot.language']
    except KeyError:
        pass
    else:
        reloadLocales()

def import_conf():
    """Imports the conf into this module"""
    global conf
    conf = __import__('supybot.conf').conf
    class Languages(conf.registry.OnlySomeStrings):
        validStrings = SUPPORTED_LANGUAGES
        errormsg = 'Value should be a supported language (%s), not %%r' % (
            ', '.join(validStrings))
    conf.registerGlobalValue(conf.supybot, 'language',
        Languages(currentLocale, """Determines the bot's default
        language if translations exist. Currently supported are: %s"""
        % ', '.join(Languages.validStrings)))
    conf.supybot.language.addCallback(reloadLocalesIfRequired)

def getPluginDir(plugin_name):
    """Gets the directory of the given plugin"""
    filename = None
    try:
        filename = sys.modules[plugin_name].__file__
    except KeyError: # It sometimes happens with Owner
        pass
    if filename == None:
        try:
            filename = sys.modules['supybot.plugins.' + plugin_name].__file__
        except: # In the case where the plugin is not loaded by Supybot
            try:
                filename = sys.modules['plugin'].__file__
            except:
                filename = sys.modules['__main__'].__file__
    if filename.endswith(".pyc"):
        filename = filename[0:-1]

    allowed_files = ['__init__.py', 'config.py', 'plugin.py', 'test.py']
    for allowed_file in allowed_files:
        if filename.endswith(allowed_file):
            return filename[0:-len(allowed_file)]
    raise PluginNotFound()

def getLocalePath(name, localeName, extension):
    """Gets the path of the locale file of the given plugin ('supybot' stands
    for the core)."""
    if name != 'supybot':
        base = getPluginDir(name)
    else:
        from . import ansi # Any Supybot plugin could fit
        base = ansi.__file__[0:-len('ansi.pyc')]
    directory = os.path.join(base, 'locales')
    return '%s/%s.%s' % (directory, localeName, extension)

i18nClasses = weakref.WeakValueDictionary()
internationalizedCommands = weakref.WeakValueDictionary()

def reloadLocalesIfRequired():
    global currentLocale
    if conf is None:
        return
    if currentLocale != conf.supybot.language():
        currentLocale = conf.supybot.language()
        reloadLocales()

def reloadLocales():
    import supybot.utils as utils

    for pluginClass in i18nClasses.values():
        pluginClass.loadLocale()
    for command in list(internationalizedCommands.values()):
        internationalizeDocstring(command)
    utils.str._relocalizeFunctions(PluginInternationalization())

def normalize(string, removeNewline=False):
    import supybot.utils as utils
    string = string.replace('\\n\\n', '\n\n')
    string = string.replace('\\n', ' ')
    string = string.replace('\\"', '"')
    string = string.replace("\'", "'")
    string = utils.str.normalizeWhitespace(string, removeNewline)
    string = string.strip('\n')
    string = string.strip('\t')
    return string


def parse(translationFile):
    step = WAITING_FOR_MSGID
    translations = set()
    for line in translationFile:
        line = line[0:-1] # Remove the ending \n
        line = line

        if step == WAITING_FOR_MSGID and line.startswith(FUZZY):
            step = NEXT_IS_FUZZY
        elif step == NEXT_IS_FUZZY and line.startswith(MSGID):
            # Don't use fuzzy strings; they may have a mismatched number of %s or be
            # outright wrong; use English instead.
            step = WAITING_FOR_MSGID
        elif line.startswith(MSGID):
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
                translations |= set([(untranslated, data)])
                step = WAITING_FOR_MSGID


        elif step is IN_MSGSTR and line.startswith('"') and \
                                   line.endswith('"'):
            translated += line[1:-1]
        elif step is IN_MSGSTR: # the MSGSTR is finished
            step = WAITING_FOR_MSGID
            if translated == '':
                translated = untranslated
            translations |= set([(untranslated, translated)])
    if step is IN_MSGSTR:
        if translated == '':
            translated = untranslated
        translations |= set([(untranslated, translated)])
    return translations


def PluginInternationalization(name='supybot'):
    # This is a proxy that prevents having several objects for the same plugin
    if name in i18nClasses:
        return i18nClasses[name]
    else:
        return _PluginInternationalization(name)

class _PluginInternationalization:
    """Internationalization managment for a plugin."""
    def __init__(self, name='supybot'):
        self.name = name
        self.translations = {}
        self.currentLocaleName = None
        i18nClasses.update({name: self})
        self.loadLocale()

    def loadLocale(self, localeName=None):
        """(Re)loads the locale used by this class."""
        self.translations = {}
        if localeName is None:
            localeName = currentLocale
        self.currentLocaleName = localeName

        self._loadL10nCode()

        try:
            try:
                translationFile = open(getLocalePath(self.name,
                                                     localeName, 'po'), 'ru')
            except ValueError: # We are using Windows
                translationFile = open(getLocalePath(self.name,
                                                     localeName, 'po'), 'r')
            self._parse(translationFile)
        except (IOError, PluginNotFound): # The translation is unavailable
            pass
        finally:
            if 'translationFile' in locals():
                translationFile.close()

    def _parse(self, translationFile):
        """A .po files parser.

        Give it a file object."""
        self.translations = {}
        for translation in parse(translationFile):
            self._addToDatabase(*translation)

    def _addToDatabase(self, untranslated, translated):
        untranslated = normalize(untranslated, True)
        translated = normalize(translated)
        if translated:
            self.translations.update({untranslated: translated})

    def __call__(self, untranslated):
        """Main function.

        This is the function which is called when a plugin runs _()"""
        normalizedUntranslated = normalize(untranslated, True)
        try:
            string = self._translate(normalizedUntranslated)
            return self._addTracker(string, untranslated)
        except KeyError:
            pass
        if untranslated.__class__ is InternationalizedString:
            return untranslated._original
        else:
            return untranslated

    def _translate(self, string):
        """Translate the string.

        C the string internationalizer if any; else, use the local database"""
        if string.__class__ == InternationalizedString:
            return string._internationalizer(string.untranslated)
        else:
            return self.translations[string]

    def _addTracker(self, string, untranslated):
        """Add a kind of 'tracker' on the string, in order to keep the
        untranslated string (used when changing the locale)"""
        if string.__class__ == InternationalizedString:
            return string
        else:
            string = InternationalizedString(string)
            string._original = untranslated
            string._internationalizer = self
            return string

    def _loadL10nCode(self):
        """Open the file containing the code specific to this locale, and
        load its functions."""
        if self.name != 'supybot':
            return
        path = self._getL10nCodePath()
        try:
            with open(path) as fd:
                exec(compile(fd.read(), path, 'exec'))
        except IOError: # File doesn't exist
            pass

        functions = locals()
        functions.pop('self')
        self._l10nFunctions = functions
            # Remove old functions and come back to the native language

    def _getL10nCodePath(self):
        """Returns the path to the code localization file.

        It contains functions that needs to by fully (code + strings)
        localized"""
        if self.name != 'supybot':
            return
        return getLocalePath('supybot', self.currentLocaleName, 'py')

    def localizeFunction(self, name):
        """Returns the localized version of the function.

        Should be used only by the InternationalizedFunction class"""
        if self.name != 'supybot':
            return
        if hasattr(self, '_l10nFunctions') and \
                name in self._l10nFunctions:
            return self._l10nFunctions[name]


try:
    class InternationalizedString(str):
        """Simple subclass to str, that allow to add attributes. Also used to
        know if a string is already localized"""
        __slots__ = ('_original', '_internationalizer')
except TypeError:
    # Fallback for CPython 2.x:
    # TypeError: Error when calling the metaclass bases
    #     nonempty __slots__ not supported for subtype of 'str'
    class InternationalizedString(str):
        """Simple subclass to str, that allow to add attributes. Also used to
        know if a string is already localized"""
        pass


def internationalizeDocstring(obj):
    """Decorates functions and internationalize their docstring.

    Only useful for commands (commands' docstring is displayed on IRC)"""
    if obj.__doc__ == None:
        return obj
    plugin_module = sys.modules[obj.__module__]
    if '_' in plugin_module.__dict__:
        internationalizedCommands.update({hash(obj): obj})
        try:
            obj.__doc__ = plugin_module._.__call__(obj.__doc__)
            # We use _.__call__() instead of _() because of a pygettext warning.
        except AttributeError:
            # attribute '__doc__' of 'type' objects is not writable
            pass
    return obj


def _install():
    from . import utils
    _ = PluginInternationalization()
    utils.gen._ = _
    utils.str._ = _
    utils.str._relocalizeFunctions(_)

_install()
