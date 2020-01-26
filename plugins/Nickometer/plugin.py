###
# Copyright (c) 2004, William Robinson.
# Derived from work (c) 1998, Adam Spiers <adam.spiers@new.ox.ac.uk>
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

###
# This algorithm is almost a direct from a the perl nickometer from
# blootbot. Hardly any of the original code has been used, though most of
# the comments, I copy-pasted. As a matter of courtesy, the original copyright
# message follows:
#
#    #
#    # Lame-o-Nickometer backend
#    #
#    # (c) 1998 Adam Spiers <adam.spiers@new.ox.ac.uk>
#    #
#    # You may do whatever you want with this code, but give me credit.
#    #
#    # $Id: Nickometer.py,v 1.13 2004/10/22 22:19:30 jamessan Exp $
#    #
###

import supybot

import re
import math
import string

import supybot.utils as utils
import supybot.utils.minisix as minisix
import supybot.callbacks as callbacks
from supybot.commands import wrap, additional
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Nickometer')

def slowExponent(x):
    return 1.3 * x * (1 - math.atan(x / 6.0) * 2 / math.pi)

def slowPow(x, y):
    return math.pow(x, slowExponent(y))

def caseShifts(s):
    s=re.sub('[^a-zA-Z]', '', s)
    s=re.sub('[A-Z]+', 'U', s)
    s=re.sub('[a-z]+', 'l', s)
    return len(s)-1

def numberShifts(s):
    s=re.sub('[^a-zA-Z0-9]', '', s)
    s=re.sub('[a-zA-Z]+', 'l', s)
    s=re.sub('[0-9]+', 'n', s)
    return len(s)-1

class Nickometer(callbacks.Plugin):
    """Will tell you how lame a nick is by the command 'nickometer [nick]'."""
    def punish(self, damage, reason):
        self.log.debug('%s lameness points awarded: %s', damage, reason)
        return damage

    @internationalizeDocstring
    def nickometer(self, irc, msg, args, nick):
        """[<nick>]

        Tells you how lame said nick is.  If <nick> is not given, uses the
        nick of the person giving the command.
        """
        score = minisix.L(0)
        if not nick:
            nick = msg.nick
        originalNick = nick
        if not nick:
            irc.error('Give me a nick to judge as the argument, please.')
            return

        specialCost = [('69', 500),
                       ('dea?th', 500),
                       ('dark', 400),
                       ('n[i1]ght', 300),
                       ('n[i1]te', 500),
                       ('fuck', 500),
                       ('sh[i1]t', 500),
                       ('coo[l1]', 500),
                       ('kew[l1]', 500),
                       ('lame', 500),
                       ('dood', 500),
                       ('dude', 500),
                       ('[l1](oo?|u)[sz]er', 500),
                       ('[l1]eet', 500),
                       ('e[l1]ite', 500),
                       ('[l1]ord', 500),
                       ('pron', 1000),
                       ('warez', 1000),
                       ('xx', 100),
                       ('\\[rkx]0', 1000),
                       ('\\0[rkx]', 1000)]

        letterNumberTranslator = utils.str.MultipleReplacer(dict(list(zip(
                '023457+8', 'ozeasttb'))))
        for special in specialCost:
            tempNick = nick
            if special[0][0] != '\\':
                tempNick = letterNumberTranslator(tempNick)

            if tempNick and re.search(special[0], tempNick, re.IGNORECASE):
                score += self.punish(special[1], 'matched special case /%s/' %
                                                                  special[0])

        # I don't really know about either of these next two statements,
        # but they don't seem to do much harm.
        # Allow Perl referencing
        nick=re.sub('^\\\\([A-Za-z])', '\1', nick);

        # C-- ain't so bad either
        nick=re.sub('^C--$', 'C', nick);

        # Punish consecutive non-alphas
        matches=re.findall(r'[^\w\d]{2,}',nick)
        for match in matches:
            score += self.punish(slowPow(10, len(match)),
                                    '%s consecutive non-alphas ' % len(match))

        # Remove balanced brackets ...
        while True:
            nickInitial = nick
            nick = re.sub(r'^([^()]*)(\()(.*)(\))([^()]*)$', r'\1\3\5', nick, 1)
            nick = re.sub(r'^([^{}]*)(\{)(.*)(\})([^{}]*)$', r'\1\3\5', nick, 1)
            nick = re.sub(r'^([^\[\]]*)(\[)(.*)(\])([^\[\]]*)$', r'\1\3\5', nick, 1)
            if nick == nickInitial:
                break
            self.log.debug('Removed some matching brackets %r => %r',
                           nickInitial, nick)
        # ... and punish for unmatched brackets
        unmatched = re.findall('[][(){}]', nick)
        if len(unmatched) > 0:
            score += self.punish(slowPow(10, len(unmatched)),
                                  '%s unmatched parentheses' % len(unmatched))

        # Punish k3wlt0k
        k3wlt0k_weights = (5, 5, 2, 5, 2, 3, 1, 2, 2, 2)
        for i in range(len(k3wlt0k_weights)):
            hits=re.findall(repr(i), nick)
            if (hits and len(hits)>0):
                score += self.punish(k3wlt0k_weights[i] * len(hits) * 30,
                                    '%s occurrences of %s ' % (len(hits), i))

        # An alpha caps is not lame in middle or at end, provided the first
        # alpha is caps.
        nickOriginalCase = nick
        match = re.search('^([^A-Za-z]*[A-Z].*[a-z].*?)[-_]?([A-Z])', nick)
        if match:
            nick = ''.join([nick[:match.start(2)],
                               nick[match.start(2)].lower(),
                               nick[match.start(2)+1:]])

        match = re.search('^([^A-Za-z]*)([A-Z])([a-z])', nick)
        if match:
            nick = ''.join([nick[:match.start(2)],
                               nick[match.start(2):match.end(2)].lower(),
                               nick[match.end(2):]])

        # Punish uppercase to lowercase shifts and vice-versa, modulo
        # exceptions above

        # the commented line is the equivalent of the original, but i think
        # they intended my version, otherwise, the first caps alpha will
        # still be punished
        #cshifts = caseShifts(nickOriginalCase);
        cshifts = caseShifts(nick);
        if cshifts > 1 and re.match('.*[A-Z].*', nick):
            score += self.punish(slowPow(9, cshifts),
                                 '%s case shifts' % cshifts)

        # Punish lame endings
        if re.match('.*[XZ][^a-zA-Z]*$', nickOriginalCase):
            score += self.punish(50, 'the last alphanumeric character was lame')

        # Punish letter to numeric shifts and vice-versa
        nshifts = numberShifts(nick);
        if nshifts > 1:
            score += self.punish(slowPow(9, nshifts),
                                 '%s letter/number shifts' % nshifts)

        # Punish extraneous caps
        caps = re.findall('[A-Z]', nick)
        if caps and len(caps) > 0:
            score += self.punish(slowPow(7, len(caps)),
                                 '%s extraneous caps' % len(caps))

        # one trailing underscore is ok. i also added a - for parasite-
        nick = re.sub('[-_]$','',nick)

        # Punish anything that's left
        remains = re.findall('[^a-zA-Z0-9]', nick)
        if remains and len(remains) > 0:
            score += self.punish(50*len(remains) + slowPow(9, len(remains)),
                                     '%s extraneous symbols' % len(remains))

        # Use an appropriate function to map [0, +inf) to [0, 100)
        percentage = 100 * (1 + math.tanh((score - 400.0) / 400.0)) * \
                     (1 - 1 / (1 + score / 5.0)) / 2

        # if it's above 99.9%, show as many digits as is interesting
        score_string=re.sub('(99\\.9*\\d|\\.\\d).*','\\1',repr(percentage))

        irc.reply(_('The "lame nick-o-meter" reading for "%s" is %s%%.') %
                  (originalNick, score_string))

        self.log.debug('Calculated lameness score for %s as %s '
                       '(raw score was %s)', originalNick, score_string, score)
    nickometer = wrap(nickometer, [additional('text')])

Class = Nickometer

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
