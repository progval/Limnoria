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

class TopicFormat(registry.String):
    "Value must include $topic, otherwise the actual topic would be left out."
    def setValue(self, v):
        if '$topic' in v or '${topic}' in v:
            registry.String.setValue(self, v)
        else:
            self.error()
            
conf.registerPlugin('Topic')
conf.registerChannelValue(conf.supybot.plugins.Topic, 'separator',
    registry.StringSurroundedBySpaces(' || ', """Determines what separator is
    used between individually added topics in the channel topic."""))
conf.registerChannelValue(conf.supybot.plugins.Topic, 'format',
    TopicFormat('$topic ($nick)', """Determines what format is used to add
    topics in the topic.  All the standard substitutes apply, in addiction to
    "$topic" for the topic itself."""))
conf.registerChannelValue(conf.supybot.plugins.Topic, 'recognizeTopiclen',
    registry.Boolean(True, """Determines whether the bot will recognize the
    TOPICLEN value sent to it by the server and thus refuse to send TOPICs
    longer than the TOPICLEN.  These topics are likely to be truncated by the
    server anyway, so this defaults to True."""))
conf.registerChannelValue(conf.supybot.plugins.Topic, 'default',
    registry.String('', """Determines what the default topic for the channel
    is.  This is used by the default command to set this topic."""))
conf.registerGroup(conf.supybot.plugins.Topic, 'undo')
conf.registerChannelValue(conf.supybot.plugins.Topic.undo, 'max',
    registry.NonNegativeInteger(10, """Determines the number of previous
    topics to keep around in case the undo command is called."""))

class Topic(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.undos = ircutils.IrcDict()
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

    def _addUndo(self, channel, topics):
        try:
            stack = self.undos[channel]
        except KeyError:
            stack = []
            self.undos[channel] = stack
        stack.append(topics)
        maxLen = self.registryValue('undo.max', channel)
        while len(stack) > maxLen:
            del stack[0]

    def _getUndo(self, channel):
        try:
            return self.undos[channel].pop()
        except (KeyError, IndexError):
            return None
        
    def _sendTopics(self, irc, channel, topics):
        topics = [s for s in topics if s and not s.isspace()]
        self.lastTopics[channel] = topics
        newTopic = self._joinTopic(channel, topics)
        try:
            maxLen = irc.state.supported['topiclen']
            if len(newTopic) > maxLen:
                if self.registryValue('recognizeTopiclen', channel):
                    irc.error('That topic is too long for this server '
                              '(maximum length: %s).' % maxLen, Raise=True)
        except KeyError:
            pass
        self._addUndo(channel, topics)
        irc.queueMsg(ircmsgs.topic(channel, newTopic))

    def _canChangeTopic(self, irc, channel):
        c = irc.state.channels[channel]
        if irc.nick not in c.ops and 't' in c.modes:
            irc.error('I can\'t change the topic, I\'m not opped and %s '
                      'is +t.' % channel, Raise=True)
        else:
            return True
            
    def _topicNumber(self, irc, n, topics=None):
        try:
            n = int(n)
            if not n:
                raise ValueError
            if n > 0:
                n -= 1
            if topics is not None:
                topics[n]
            return n
        except (ValueError, IndexError):
            irc.error('That\'s not a valid topic number.', Raise=True)

    def topic(self, irc, msg, args, channel):
        """[<channel>] <topic>

        Sets the topic of <channel> to <topic>.
        """
        topic = privmsgs.getArgs(args)
        self._sendTopics(irc, channel, [topic])
    topic = privmsgs.channel(topic)

    def add(self, irc, msg, args, channel, insert=False):
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
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        formattedTopic = self._formatTopic(irc, msg, channel, topic)
        if insert:
            topics.insert(0, formattedTopic)
        else:
            topics.append(formattedTopic)
        self._sendTopics(irc, channel, topics)
    add = privmsgs.channel(add)

    def insert(self, irc, msg, args):
        """[<channel>] <topic>

        Adds <topic> to the topics for <channel> at the beginning of the topics
        currently on <channel>.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        self.add(irc, msg, args, insert=True)

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
        self._sendTopics(irc, channel, topics)
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
        for i,p in enumerate(order):
            order[i] = self._topicNumber(irc, p, topics=topics)
            if order[i] < 0:
                order[i] += num
        if sorted(order) != range(num):
            irc.error('Duplicate topic numbers cannot be specified.')
            return
        newtopics = [topics[i] for i in order]
        self._sendTopics(irc, channel, newtopics)
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
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if topics:
            number = self._topicNumber(irc, number, topics=topics)
            irc.reply(topics[number])
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
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if not topics:
            irc.error('There are no topics to change.')
            return
        number = self._topicNumber(irc, number, topics=topics)
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error('The regexp wasn\'t valid: %s' % e)
            return
        topics[number] = replacer(topics[number])
        self._sendTopics(irc, channel, topics)
    change = privmsgs.channel(change)

    def set(self, irc, msg, args, channel):
        """[<channel>] <number> <topic>

        Sets the topic <number> to be <text>.  <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        self._canChangeTopic(irc, channel)
        (i, topic) = privmsgs.getArgs(args, required=2)
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        i = self._topicNumber(irc, i, topics=topics)
        topic = self._formatTopic(irc, msg, channel, topic)
        topics[i] = topic
        self._sendTopics(irc, channel, topics)
    set = privmsgs.channel(set)

    def remove(self, irc, msg, args, channel):
        """[<channel>] <number>

        Removes topic <number> from the topic for <channel>  Topics are
        numbered starting from 1; you can also use negative indexes to refer
        to topics starting the from the end of the topic.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._canChangeTopic(irc, channel)
        i = privmsgs.getArgs(args)
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        i = self._topicNumber(irc, i, topics=topics)
        topic = topics.pop(i)
        self._sendTopics(irc, channel, topics)
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
        self._sendTopics(irc, channel, topics)
    restore = privmsgs.channel(restore)

    def undo(self, irc, msg, args, channel):
        """[<channel>]

        Restores the topic to the one previous to the last topic command that
        set it.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        topics = self._getUndo(channel) # This is the last topic sent.
        topics = self._getUndo(channel) # This is the topic list we want.
        if topics is not None:
            self._sendTopics(irc, channel, topics)
        else:
            irc.error('There are no more undos for %s.' % channel)
    undo = privmsgs.channel(undo)

    def default(self, irc, msg, args, channel):
        """[<channel>]

        Sets the topic in <channel> to the default topic for <channel>.  The
        default topic for a channel may be configured via the configuration
        variable supybot.plugins.Topic.default.
        """
        topic = self.registryValue('default', channel)
        if topic:
            self._sendTopics(irc, channel, [topic])
        else:
            irc.error('There is no default topic configured for %s.' % channel)
    default = privmsgs.channel(default)

Class = Topic


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
