#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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
Lots of stuff relating to random numbers.
"""

from baseplugin import *

import random

import conf
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Random')
    if yn('Do you want to specify a seed to be used for the RNG')=='y':
        seed = something('What seed?  It must be an int or long.')
        while not seed.isdigit():
            print 'That\'s not a valid seed.'
            seed = something('What seed?')
        onStart.append('seed %s' % seed)

example = utils.wrapLines("""
<jemfinch> $list Random
<angryman> diceroll, random, range, sample, seed
<jemfinch> $random
<angryman> 0.478084042957
<jemfinch> $random
<angryman> 0.960634332773
<jemfinch> $seed 50
<angryman> The operation succeeded.
<jemfinch> $random
<angryman> 0.497536568759
<jemfinch> $seed 50
<angryman> The operation succeeded.
<jemfinch> $random
<angryman> 0.497536568759
<jemfinch> $range 1 10
<angryman> 3
<jemfinch> $range 1 10000000000000
<angryman> 6374111614437
<jemfinch> $diceroll
* angryman rolls a 2
<jemfinch> $diceroll
* angryman rolls a 3
<jemfinch> $diceroll 100
* angryman rolls a 97
""")

class Random(callbacks.Privmsg):
    rng = random.Random()
    def random(self, irc, msg, args):
        """takes no arguments

        Returns the next random number from the random number
        generator.
        """
        irc.reply(msg, str(self.rng.random()))

    def seed(self, irc, msg, args):
        """<seed>

        Sets the seed of the random number generator.  <seed> must be an int
        or a long.
        """
        seed = privmsgs.getArgs(args)
        try:
            seed = long(seed)
        except ValueError:
            # It wasn't a valid long!
            irc.error(msg, '<seed> must be a valid int or long.')
            return
        self.rng.seed(seed)
        irc.reply(msg, conf.replySuccess)

    def range(self, irc, msg, args):
        """<start> <end>

        Returns a number between <start> and <end>, inclusive (i.e., the number
        can be either of the endpoints.
        """
        (start, end) = privmsgs.getArgs(args, needed=2)
        try:
            end = int(end)
            start = int(start)
        except ValueError:
            irc.error(msg, '<start> and <end> must both be integers.')
            return
        # .randrange() doesn't include the endpoint, so we use end+1.
        irc.reply(msg, str(self.rng.randrange(start, end+1)))

    def sample(self, irc, msg, args):
        """<number of items> [<text> ...]

        Returns a sample of the <number of items> taken from the remaining
        arguments.  Obviously <number of items> must be less than the number
        of arguments given.
        """
        try:
            n = int(args.pop(0))
        except IndexError: # raised by .pop(0)
            raise callbacks.ArgumentError
        except ValueError:
            irc.error(msg, '<number of items> must be an integer.')
            return
        if n > len(args):
            irc.error(msg, '<number of items> must be less than the number '
                           'of arguments.')
            return
        sample = self.rng.sample(args, n)
        irc.reply(msg, utils.commaAndify(map(repr, sample)))

    def diceroll(self, irc, msg, args):
        """[<number of sides>]

        Rolls a die with <number of sides> sides.  The default number of
        sides is 6.
        """
        try:
            n = privmsgs.getArgs(args, needed=0, optional=1)
            if not n:
                n = 6
            n = int(n)
        except ValueError:
            irc.error(msg, 'Dice have integer numbers of sides.  Use one.')
            return
        s = 'rolls a %s' % self.rng.randrange(1, n)
        irc.queueMsg(ircmsgs.action(ircutils.replyTo(msg), s))
        raise callbacks.CannotNest

Class = Random

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
