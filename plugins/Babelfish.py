#!/usr/bin/env python

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

"""
Babelfish-related commands.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jamessan

import sets
import random
from itertools import imap

import babelfish

import supybot.conf as conf
import supybot.utils as utils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

class Languages(registry.OnlySomeStrings):
    validStrings = tuple(map(str.capitalize, babelfish.available_languages))
    normalize = staticmethod(str.capitalize)

class SpaceSeparatedListOfLanguages(registry.SeparatedListOf):
    List = sets.Set
    Value = Languages
    def splitter(self, s):
        return s.split()
    joiner = ' '.join

conf.registerPlugin('Babelfish')
conf.registerChannelValue(conf.supybot.plugins.Babelfish, 'languages',
    SpaceSeparatedListOfLanguages(babelfish.available_languages, """Determines
    which languages are available for translation; valid input is a list of
    languages separated by spaces."""))

class Babelfish(callbacks.Privmsg):
    threaded = True
    _abbrevs = utils.abbrev(imap(str.lower, babelfish.available_languages))
    _abbrevs['de'] = 'german'
    _abbrevs['jp'] = 'japanese'
    _abbrevs['kr'] = 'korean'
    _abbrevs['es'] = 'spanish'
    _abbrevs['pt'] = 'portuguese'
    _abbrevs['it'] = 'italian'
    _abbrevs['zh'] = 'chinese'
    for language in babelfish.available_languages:
        _abbrevs[language] = language

    def _getLang(self, fromLang, toLang, chan):
        fromLang = self._abbrevs[fromLang.lower()]
        toLang = self._abbrevs[toLang.lower()]
        languages = map(str.lower, self.registryValue('languages',chan))
        if fromLang not in languages:
            fromLang = None
        if toLang not in languages:
            toLang = None
        return (fromLang, toLang)

    def languages(self, irc, msg, args):
        """takes no arguments

        Returns the languages that Babelfish can translate to/from.
        """
        irc.reply(utils.commaAndify(babelfish.available_languages))

    def translate(self, irc, msg, args):
        """<from-language> [to] <to-language> <text>

        Returns <text> translated from <from-language> into <to-language>.
        """
        if len(args) >= 2 and args[1] == 'to':
            args.pop(1)
        (fromLang, toLang, text) = privmsgs.getArgs(args, required=3)
        chan = msg.args[0]
        try:
            (fromLang, toLang) = self._getLang(fromLang, toLang, chan)
            if not fromLang or not toLang:
                langs = self.registryValue('languages', chan)
                if not langs:
                    irc.error('I do not speak any other languages.')
                    return
                else:
                    irc.error('I only speak %s.' % utils.commaAndify(langs,
                                                                     And='or'))
                    return
            translation = babelfish.translate(text, fromLang, toLang)
            irc.reply(translation)
        except (KeyError, babelfish.LanguageNotAvailableError), e:
            irc.error('%s is not a valid language.  Valid languages '
                      'include %s.' %
                      (e, self.registryValue('languages', chan)))
        except babelfish.BabelizerIOError, e:
            irc.error(str(e))
        except babelfish.BabelfishChangedError, e:
            irc.error('Babelfish has foiled our plans by changing its '
                      'webpage format.')

    def babelize(self, irc, msg, args):
        """<from-language> <to-language> <text>

        Translates <text> repeatedly between <from-language> and <to-language>
        until it doesn't change anymore or 12 times, whichever is fewer.  One
        of the languages must be English.
        """
        (fromLang, toLang, text) = privmsgs.getArgs(args, required=3)
        chan = msg.args[0]
        try:
            (fromLang, toLang) = self._getLang(fromLang, toLang, chan)
            if fromLang != 'english' and toLang != 'english':
                irc.error('One language in babelize must be English.')
                return
            if not fromLang or not toLang:
                langs = self.registryValue('languages', chan)
                if not langs:
                    irc.error('I do not speak any other languages.')
                    return
                else:
                    irc.error('I only speak %s.' % utils.commaAndify(langs,
                                                                     And='or'))
                    return
            translations = babelfish.babelize(text, fromLang, toLang)
            irc.reply(utils.htmlToText(translations[-1]))
        except (KeyError, babelfish.LanguageNotAvailableError), e:
            irc.reply('%s is not a valid language.  Valid languages '
                      'include %s.' % (e,
                                       self.registryValue('languages', chan)))
        except babelfish.BabelizerIOError, e:
            irc.reply(e)
        except babelfish.BabelfishChangedError, e:
            irc.reply('Babelfish has foiled our plans by changing its '
                      'webpage format.')

    def randomlanguage(self, irc, msg, args):
        """[<allow-english>]

        Returns a random language supported by babelfish.  If <allow-english>
        is provided, will include English in the list of possible languages.
        """
        allowEnglish = privmsgs.getArgs(args, required=0, optional=1)
        languages = self.registryValue('languages', msg.args[0])
        if not languages:
            irc.error('I can\'t speak any other languages.')
        language = random.choice(languages)
        while not allowEnglish and language == 'English':
            language = random.choice(languages)
        irc.reply(language)

Class = Babelfish

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
