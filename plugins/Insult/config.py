###
# Copyright (c) 2004-2005, Mike Taylor
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

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Insult', True)
    if advanced:
        output("""The Insult plugin constructs an insult in the form of \"You
        are nothing but a(n) {adjective} {amount} of {adjective} {noun}.\"
        """)
        if yn("""Include foul language in pools of randomly chosen adjective,
            amount and noun words?""", default=True):
            conf.supybot.plugins.Insult.allowFoul.setValue(True)

# The list of words came from the mozbot Insult.bm module
# The header of that module has the following credit:
#     This is basically a loose port of insultd, a random insult server,
#     for self-flagellating maniacs, written on 1991-12-09 by
#     garnett@colorado.edu. See http://insulthost.colorado.edu/

Insult = conf.registerPlugin('Insult')
conf.registerGlobalValue(Insult, 'allowFoul',
    registry.Boolean(True, """Determines whether to include foul language in
    pools of randomly chosen adjective, amount and noun words."""))
conf.registerGlobalValue(Insult, 'nouns',
    registry.SpaceSeparatedListOfStrings( ['bat toenails', 'bug spit',
    'cat hair', 'fish heads', 'gunk', 'pond scum', 'rat retch',
    'red dye number-9', 'Sun IPC manuals', 'waffle-house grits', 'yoo-hoo',
    'squirrel guts', 'snake bait', 'buzzard gizzards', 'cat-hair-balls',
    'pods', 'armadillo snouts', 'entrails', 'snake snot', 'eel ooze',
    'toxic waste', 'Stimpy-drool', 'poopy', 'poop',
    'craptacular carpet droppings', 'cold sores', 'IE user'],
    """Determines the base set of words used as the pool for nouns."""))
conf.registerGlobalValue(Insult, 'foulNouns',
    registry.SpaceSeparatedListOfStrings( ['chicken piss', 'dog vomit',
    'dung', 'fat woman\'s stomach-bile', 'guano', 'dog balls', 'seagull puke',
    'cat bladders', 'pus', 'urine samples', 'snake assholes', 'rat-farts',
    'slurpee-backwash', 'jizzum', 'anal warts'],
    """Determines the set of foul words added to the pool of nouns."""))
conf.registerGlobalValue(Insult, 'amounts',
    registry.SpaceSeparatedListOfStrings(['accumulation', 'bucket', 'gob',
    'coagulation', 'half-mouthful', 'heap', 'mass', 'mound', 'petrification',
    'pile', 'puddle', 'stack', 'thimbleful', 'tongueful', 'ooze', 'quart',
    'bag', 'plate'],
    """Determines the base set of words used as the pool for amounts."""))
conf.registerGlobalValue(Insult, 'foulAmounts',
    registry.SpaceSeparatedListOfStrings(['enema-bucketful', 'ass-full',
    'assload'], """Determines the set of foul words added to the pool of
    amounts."""))
conf.registerGlobalValue(Insult, 'adjectives',
    registry.SpaceSeparatedListOfStrings( ['acidic', 'antique',
    'contemptible', 'culturally-unsound', 'despicable', 'evil', 'fermented',
    'festering', 'foul', 'fulminating', 'humid', 'impure', 'inept',
    'inferior', 'industrial', 'left-over', 'low-quality', 'off-color',
    'petrified', 'pointy-nosed', 'salty', 'sausage-snorfling', 'tasteless',
    'tempestuous', 'tepid', 'tofu-nibbling', 'unintelligent', 'unoriginal',
    'uninspiring', 'weasel-smelling', 'wretched', 'spam-sucking',
    'egg-sucking', 'decayed', 'halfbaked', 'infected', 'squishy', 'porous',
    'pickled', 'thick', 'vapid', 'unmuzzled', 'bawdy', 'vain', 'lumpish',
    'churlish', 'fobbing', 'craven', 'jarring', 'fly-bitten', 'fen-sucked',
    'spongy', 'droning', 'gleeking', 'warped', 'currish', 'milk-livered',
    'surly', 'mammering', 'ill-borne', 'beef-witted', 'tickle-brained',
    'half-faced', 'headless', 'wayward', 'onion-eyed', 'beslubbering',
    'villainous', 'lewd-minded', 'cockered', 'full-gorged', 'rude-snouted',
    'crook-pated', 'pribbling', 'dread-bolted', 'fool-born', 'puny',
    'fawning', 'sheep-biting', 'dankish', 'goatish', 'weather-bitten',
    'knotty-pated', 'malt-wormy', 'saucyspleened', 'motley-mind',
    'it-fowling', 'vassal-willed', 'loggerheaded', 'clapper-clawed', 'frothy',
    'ruttish', 'clouted', 'common-kissing', 'folly-fallen', 'plume-plucked',
    'flap-mouthed', 'swag-bellied', 'dizzy-eyed', 'gorbellied', 'weedy',
    'reeky', 'measled', 'spur-galled', 'mangled', 'impertinent', 'bootless',
    'toad-spotted', 'hasty-witted', 'horn-beat', 'yeasty', 'hedge-born',
    'imp-bladdereddle-headed', 'tottering', 'hugger-muggered', 'elf-skinned',
    'Microsoft-loving'], """Determines the base set of words used as the pool
    for adjectives."""))
conf.registerGlobalValue(Insult, 'foulAdjectives',
    registry.SpaceSeparatedListOfStrings(['pignutted', 'pox-marked', 'rank',
    'malodorous', 'penguin-molesting', 'coughed-up', 'hacked-up', 'rump-fed',
    'boil-brained'], """Determines the set of foul words added to the pool of
    adjectives."""))
# XXX Are we going to get overrides like MozBot has?  I.e., if people try to
# insult Supybot, we'll instead insult them.  The overrides should, of course,
# be configurable.


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
