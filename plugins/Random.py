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

import supybot.plugins as plugins

import time
import random

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Random', True)
    if yn('Do you want to specify a seed to be used for the RNG'):
        seed = something('What seed?  It must be an integer or long.')
        while not seed.isdigit():
            print 'That\'s not a valid seed.'
            seed = something('What seed?')
        conf.supybot.plugins.Random.seed.setValue(seed)

class Seed(registry.Integer):
    def __call__(self):
        v = registry.Integer.__call__(self)
        if not v:
            v = int(time.time())
        return v

    def serialize(self):
        # We do this so if it's 0, it doesn't store a real time.
        return str(self.value)
        
conf.registerPlugin('Random')
conf.registerGlobalValue(conf.supybot.plugins.Random, 'seed', Seed(0, """
Sets the seed of the random number generator.  The seed must be a valid
Python integer or long.  If the seed is 0, a seed based on the current
time will be used."""))

class Random(callbacks.Privmsg):
    def __init__(self):
        self.rng = random.Random(self.registryValue('seed'))
        super(Random, self).__init__()

    def random(self, irc, msg, args):
        """takes no arguments

        Returns the next random number from the random number
        generator.
        """
        irc.reply(str(self.rng.random()))

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
            irc.errorInvalid('number', seed)
            return
        self.rng.seed(seed)
        irc.replySuccess()

    def range(self, irc, msg, args):
        """<start> <end>

        Returns a number between <start> and <end>, inclusive (i.e., the number
        can be either of the endpoints.
        """
        (start, end) = privmsgs.getArgs(args, required=2)
        try:
            end = int(end)
            start = int(start)
        except ValueError:
            irc.error('<start> and <end> must both be integers.')
            return
        # .randrange() doesn't include the endpoint, so we use end+1.
        irc.reply(str(self.rng.randrange(start, end+1)))

    def sample(self, irc, msg, args):
        """<number of items> [<text> ...]

        Returns a sample of the <number of items> taken from the remaining
        arguments.  Obviously <number of items> must be less than the number
        of arguments given.
        """
        try:
            n = args.pop(0)
            n = int(n)
        except IndexError: # raised by .pop(0)
            raise callbacks.ArgumentError
        except ValueError:
            irc.errorInvalid('number', n)
            return
        if n > len(args):
            irc.error('<number of items> must be less than the number '
                      'of arguments.')
            return
        sample = self.rng.sample(args, n)
        sample.sort()
        irc.reply(utils.commaAndify(sample))

    def diceroll(self, irc, msg, args):
        """[<number of sides>]

        Rolls a die with <number of sides> sides.  The default number of
        sides is 6.
        """
        try:
            n = privmsgs.getArgs(args, required=0, optional=1)
            if not n:
                n = 6
            n = int(n)
        except ValueError:
            irc.error('Dice have integer numbers of sides.  Use one.')
            return
        s = 'rolls a %s' % self.rng.randrange(1, n)
        irc.reply(s, action=True)

Class = Random

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
