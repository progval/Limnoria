#!/usr/bin/python

###
# Copyright (c) 2004, Jeremiah Fincher
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
A module to observe things in the channel and call commands based on what is
seen.
"""

__revision__ = "$Id$"
__author__ = ''

import supybot.plugins as plugins

import random

import supybot.conf as conf
import supybot.utils as utils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Observer', True)

class Probability(registry.Float):
    """Value must be a floating point number in the range (0, 1]."""
    def setValue(self, v):
        if not 0 < v <= 1:
            self.error()
        else:
            super(Probability, self).setValue(v)

conf.registerPlugin('Observer')
# XXX These both need to be CanonicalStrings.
conf.registerGlobalValue(conf.supybot.plugins.Observer, 'observers',
    registry.SpaceSeparatedSetOfStrings([], """Determines what observers are
    available.""", orderAlphabetically=True))
conf.registerChannelValue(conf.supybot.plugins.Observer.observers, 'active',
    registry.SpaceSeparatedListOfStrings([], """Determines what observers are
    active on a channel."""))
                          

def registerObserver(name, regexpString=None,
                     commandString=None, probability=1.0):
    g = conf.registerGlobalValue(conf.supybot.plugins.Observer.observers,
            name, registry.Regexp(regexpString, """Determines what regexp must
            match for this observer to be executed."""))
    if regexpString is not None:
        g.set(regexpString) # This is in case it's been registered.
    conf.registerGlobalValue(g, 'command', registry.String('', """Determines
        what command will be run when this observer is executed."""))
    conf.registerGlobalValue(g, 'probability', Probability(probability, """
        Determines what the probability of executing this observer is if it
        matches."""))
    conf.supybot.plugins.Observer.observers().add(name)
    return g


class Observer(callbacks.Privmsg):
    def _isValidObserverName(self, name):
        return name != 'active' and registry.isValidRegistryName(name)
    
    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        Owner = irc.getCallback('Owner')
        observers = self.registryValue('observers')
        active = self.registryValue('observers.active', channel)
        for name in active:
            if name not in observers:
                self.log.error('Active observers for %s include an '
                               'invalid observer: %s.', channel, name)
                continue
            observer = self.registryValue('observers.%s' % name, value=False)
            probability = observer.probability()
            if random.random() > probability:
                continue
            r = observer() # The regexp.
            m = r.search(msg.args[1])
            if m is not None:
                command = observer.command()
                groups = list(m.groups())
                groups.insert(0, m.group(0))
                for (i, group) in enumerate(groups):
                    command = command.replace('$%s' % i, group)
                tokens = callbacks.tokenize(text, channel=channel)
                Owner.processTokens(irc, msg, tokens)
                
    def list(self, irc, msg, args):
        """[<channel>]

        Lists the currently available observers.  If <channel> is given,
        returns the currently active observers on <channel>.
        """
        if args:
            # We don't use getChannel here because we don't want it to
            # automatically pick the channel if the message is sent in
            # the channel itself.
            channel = args.pop(0)
            if args or not ircutils.isChannel(channel):
                raise callbacks.ArgumentError
            observers = self.registryValue('observers.active', channel)
            # We don't sort because order matters.
        else:
            observers = self.registryValue('observers')
            utils.sortBy(str.lower, observers)
        if observers:
            irc.reply(utils.commaAndify(observers))
        else:
            irc.reply('There were no relevant observers.')

    def enable(self, irc, msg, args):
        """[<channel>] <name>

        Enables the observer <name> in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        name = privmsgs.getArgs(args)
        if name not in self.registryValue('observers'):
            irc.error('There is no observer %s.' % name, Raise=True)
        self.registryValue('observers.active', channel).add(name)
        irc.replySuccess()
    enable = privmsgs.checkChannelCapability(enable, 'op')

    def disable(self, irc, msg, args, channel):
        """[<channel>] <name>

        Disables the observer <name> in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        name = privmsgs.getArgs(args)
        try:
            self.registryValue('observers.active', channel).remove(name)
            irc.replySuccess()
        except KeyError:
            irc.error('The observer %s was not active on %s.' % (name,channel))
    disable = privmsgs.checkChannelCapability(disable, 'op')
            
    def info(self, irc, msg, args):
        """<name>

        Returns the relevant information on the observer specified by <name>.
        """
        name = privmsgs.getArgs(args)
        if name not in self.registryValue('observers'):
            irc.error('That\'s not a valid observer.', Raise=True)
        g = self.registryValue('observers.%s' % name, value=False)
        regexp = g()
        command = g.command()
        probability = g.probability()
        irc.reply('%s matches the regular expression %s and '
                  'runs the command %s with a probability of %s' %
                  (name, regexp, command, probability))
        
    def add(self, irc, msg, args):
        """<name> [<probability>] <regexp> <command>

        Calls <command> when <regexp> matches a given message.  Before
        being called, <command> has the standard substitute applied to it,
        as well as having $1, $2, etc. replaced by the appropriate groups
        of the regexp.  If <probability> is not given, it defaults to 1;
        otherwise it should be a floating point probability that the observer
        will execute if it matches.
        """
        if len(args) < 3:
            raise callbacks.ArgumentError
        try:
            probability = float(args[1])
            del args[1]
        except ValueError:
            probability = 1.0
        (name, regexp, command) = privmsgs.getArgs(args, required=3)
        if not registry.isValidRegistryName(name):
            irc.error('That\'s not a valid observer name.  Please be sure '
                      'there are no spaces in the name.', Raise=True)
        registerObserver(name, regexp, command, probability)
        irc.replySuccess()

    def remove(self, irc, msg, args):
        """<name>

        Removes the observer <name>.
        """
        pass

    


Class = Observer

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
