# -*- encoding: utf8 -*-
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
Supybot utility functions localization in French.
"""

def pluralize(s):
    """Returns the plural of s.
    """
    lowered = s.lower()
    if lowered.endswith('ou') and \
        lowered in ['bijou', 'caillou', 'chou', 'genou', 'hibou', 'joujou',
                    'pou']:
        return s + 'x'
    elif lowered.endswith('al') and \
        lowered not in ['bal', 'carnaval', 'chacal', 'festival', 'récital',
                  'régal', 'cal', 'étal', 'aval', 'caracal', 'val', 'choral',
                  'corral', 'galgal', 'gayal']:
        return s[0:-2] + 'aux'
    elif lowered.endswith('ail') and \
        lowered not in ['bail', 'corail', 'émail', 'soupirail', 'travail',
                        'ventail', 'vitrail', 'aspirail', 'fermail']:
        return s[0:-3] + 'aux'
    elif lowered.endswith('eau'):
        return s + 'x'
    elif lowered == 'pare-feu':
        return s
    elif lowered.endswith('eu') and \
        lowered not in ['bleu', 'pneu', 'émeu', 'enfeu']:
        # Note: when 'lieu' is a fish, it has a 's' ; else, it has a 'x'
        return s + 'x'
    else:
        return s + 's'

def depluralize(s):
    """Returns the singular of s."""
    lowered = s.lower()
    if lowered.endswith('aux') and \
        lowered in ['baux', 'coraux', 'émaux', 'soupiraux', 'travaux',
                        'ventaux', 'vitraux', 'aspiraux', 'fermaux']:
        return s[0:-3] + 'ail'
    elif lowered.endswith('aux'):
        return s[0:-3] + 'al'
    else:
        return s[0:-1]

def ordinal(i):
    """Returns i + the ordinal indicator for the number.

    Example: ordinal(3) => '3ème'
    """
    i = int(i)
    if i == 1:
        return '1er'
    else:
        return '%sème' % i

def be(i):
    """Returns the form of the verb 'être' based on the number i."""
    # Note: this function is used only for the third person
    if i == 1:
        return 'est'
    else:
        return 'sont'

def has(i):
    """Returns the form of the verb 'avoir' based on the number i."""
    # Note: this function is used only for the third person
    if i == 1:
        return 'a'
    else:
        return 'ont'
