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
Provides commands for manipulating channel topics.
"""

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import supybot.plugins as plugins

import re
import random

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

conf.registerPlugin('Topic')
conf.registerChannelValue(conf.supybot.plugins.Topic, 'separator',
    registry.StringSurroundedBySpaces(' || ', """Determines what separator is
    used between individually added topics in the channel topic."""))

class TopicFormat(registry.String):
    "Value must include $topic, otherwise the actual topic would be left out."
    def setValue(self, v):
        if '$topic' in v or '${topic}' in v:
            registry.String.setValue(self, v)
        else:
            self.error()
            
conf.registerChannelValue(conf.supybot.plugins.Topic, 'format',
    TopicFormat('$topic ($nick)', """Determines what format is used to add
    topics in the topic.  All the standard substitutes apply, in addiction to
    "$topic" for the topic itself."""))

class Topic(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.lastTopics = ircutils.IrcDict()

    def _splitTopic(self, topic, channel):
        separator = self.registryValue('separator', channel)
        return filter(None, topic.split(separator))

    def _joinTopic(self, channel, topics):
        separator = self.registryValue('separator', channel)
        return separator.join(topics)

    def _formatTopic(self, irc, msg, channel, topic):
        formatter = self.registryValue('format', channel)
        env = {'topic': topic}
        return plugins.standardSubstitute(irc, msg, formatter, env)

    def _sendTopic(self, irc, channel, topics):
        topics = [s for s in topics if s and not s.isspace()]
        self.lastTopics[channel] = topics
        newTopic = self._joinTopic(channel, topics)
        irc.queueMsg(ircmsgs.topic(channel, newTopic))

    def _canChangeTopic(self, irc, channel):
        c = irc.state.channels[channel]
        if irc.nick not in c.ops and 't' in c.modes:
            irc.error('I can\'t change the topic, I\'m not opped and %s '
                      'is +t.' % channel, Raise=True)
        else:
            return True
            
    def add(self, irc, msg, args, channel):
        """[<channel>] <topic>

        Adds <topic> to the topics for <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        self._canChangeTopic(irc, channel)
        topic = privmsgs.getArgs(args)
        separator = self.registryValue('separator', channel)
        if separator in topic:
            s = 'You can\'t have %s in your topic' % separator
            irc.error(s)
            return
        currentTopic = irc.state.getTopic(channel)
        formattedTopic = self._formatTopic(irc, msg, channel, topic)
        # Empties are removed by _sendTopic.
        self._sendTopic(irc, channel, [currentTopic, formattedTopic])
    add = privmsgs.channel(add)

    def shuffle(self, irc, msg, args, channel):
        """[<channel>]

        Shuffles the topics in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        self._canChangeTopic(irc, channel)
        newtopic = irc.state.getTopic(channel)
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if len(topics) == 0 or len(topics) == 1:
            irc.error('I can\'t shuffle 1 or fewer topics.')
            return
        elif len(topics) == 2:
            topics.reverse()
        else:
            original = topics[:]
            while topics == original:
                random.shuffle(topics)
        self._sendTopic(irc, channel, topics)
    shuffle = privmsgs.channel(shuffle)

    def reorder(self, irc, msg, args, channel):
        """[<channel>] <number> [<number> ...]

        Reorders the topics from <channel> in the order of the specified
        <number> arguments.  <number> is a one-based index into the topics.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        self._canChangeTopic(irc, channel)
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        num = len(topics)
        if num == 0 or num == 1:
            irc.error('I cannot reorder 1 or fewer topics.')
            return
        if len(args) != num:
            irc.error('All topic numbers must be specified.')
            return
        order = privmsgs.getArgs(args, required=num)
        if topics:
            for i,p in enumerate(order):
                try:
                    p = int(p)
                    if p > 0:
                        order[i] = p - 1
                    elif p == 0:
                        irc.error('0 is not a valid topic number.')
                        return
                    else:
                        order[i] = num + p
                except ValueError:
                    irc.error('The positions must be valid integers.')
                    return
            if sorted(order) != range(num):
                irc.error('Duplicate topic numbers cannot be specified.')
                return
            try:
                newtopics = [topics[i] for i in order]
                self._sendTopic(irc, channel, newtopics)
            except IndexError:
                irc.error('An invalid topic number was specified.')
        else:
            irc.error('There are no topics to reorder.')
    reorder = privmsgs.channel(reorder)

    def list(self, irc, msg, args, channel):
        """[<channel>] <number>

        Returns a list of the topics in <channel>, prefixed by their indexes.
        Mostly useful for topic reordering.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        L = []
        for (i, t) in enumerate(topics):
            L.append('%s: %s' % (i+1, utils.ellipsisify(t, 30)))
        s = utils.commaAndify(L)
        irc.reply(s)
    list = privmsgs.channel(list)

    def get(self, irc, msg, args, channel):
        """[<channel>] <number>

        Returns topic number <number> from <channel>.  <number> is a one-based
        index into the topics.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        number = privmsgs.getArgs(args)
        try:
            number = int(number)
            if number > 0:
                number -= 1
            elif number == 0:
                irc.error('That\'s not a valid topic number.')
                return
        except ValueError:
            irc.error('The argument must be a valid integer.')
            return
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if topics:
            try:
                irc.reply(topics[number])
            except IndexError:
                irc.error('That\'s not a valid topic.')
        else:
            irc.error('There are no topics to get.')
    get = privmsgs.channel(get)

    def change(self, irc, msg, args, channel):
        """[<channel>] <number> <regexp>

        Changes the topic number <number> on <channel> according to the regular
        expression <regexp>.  <number> is the one-based index into the topics;
        <regexp> is a regular expression of the form
        s/regexp/replacement/flags.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        self._canChangeTopic(irc, channel)
        (number, regexp) = privmsgs.getArgs(args, required=2)
        try:
            number = int(number)
            if number > 0:
                number -= 1
            elif number == 0:
                irc.error('That\'s not a valid topic number.')
                return
        except ValueError:
            irc.error('The <number> argument must be a number.')
            return
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error('The regexp wasn\'t valid: %s' % e.args[0])
            return
        except re.error, e:
            irc.error(utils.exnToString(e))
            return
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if not topics:
            irc.error('There are no topics to change.')
            return
        topic = topics.pop(number)
        newTopic = replacer(topic)
        if number < 0:
            number = len(topics)+1+number
        topics.insert(number, newTopic)
        self._sendTopic(irc, channel, topics)
    change = privmsgs.channel(change)

    def remove(self, irc, msg, args, channel):
        """[<channel>] <number>

        Removes topic <number> from the topic for <channel>  Topics are
        numbered starting from 1; you can also use negative indexes to refer
        to topics starting the from the end of the topic.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._canChangeTopic(irc, channel)
        try:
            number = int(privmsgs.getArgs(args))
            if number > 0:
                number -= 1
            elif number == 0:
                irc.error('That\'s not a valid topic number.')
                return
        except ValueError:
            irc.error('The argument must be a number.')
            return
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        try:
            topic = topics.pop(number)
        except IndexError:
            irc.error('That\'s not a valid topic number.')
            return
        self._sendTopic(irc, channel, topics)
    remove = privmsgs.channel(remove)

    def lock(self, irc, msg, args, channel):
        """[<channel>]

        Locks the topic (sets the mode +t) in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.queueMsg(ircmsgs.mode(channel, '+t'))
        else:
            irc.error('How can I unlock the topic, I\'m not opped!')
    lock = privmsgs.channel(lock)

    def unlock(self, irc, msg, args, channel):
        """[<channel>]

        Locks the topic (sets the mode +t) in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        if irc.nick in irc.state.channels[channel].ops:
            irc.queueMsg(ircmsgs.mode(channel, '-t'))
        else:
            irc.error('How can I unlock the topic, I\'m not opped!')
    unlock = privmsgs.channel(unlock)

    def restore(self, irc, msg, args, channel):
        """[<channel>]

        Restores the topic to the last topic set by the bot.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._canChangeTopic(irc, channel)
        try:
            topics = self.lastTopics[channel]
        except KeyError:
            irc.error('I haven\'t yet set the topic in %s.' % channel)
            return
        self._sendTopic(irc, channel, topics)
    restore = privmsgs.channel(restore)

Class = Topic


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
