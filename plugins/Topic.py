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

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import re
import random

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
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

def canChangeTopic(irc, msg, args, state):
    assert not state.channel
    callConverter('channel', irc, msg, args, state)
    callConverter('inChannel', irc, msg, args, state)
    if state.channel not in irc.state.channels:
        irc.error('I\'m not currently in %s.' % state.channel, Raise=True)
    c = irc.state.channels[state.channel]
    if irc.nick not in c.ops and 't' in c.modes:
        irc.error('I can\'t change the topic, '
                  'I\'m not opped and %s is +t.' % state.channel, Raise=True)

def getTopic(irc, msg, args, state, format=True):
    separator = state.cb.registryValue('separator', state.channel)
    if separator in args[0]:
        irc.errorInvalid('topic', args[0],
                         'The topic must not include %s.' % separator)
    topic = args.pop(0)
    if format:
        env = {'topic': topic}
        formatter = state.cb.registryValue('format', state.channel)
        topic = ircutils.standardSubstitute(irc, msg, formatter, env)
    state.args.append(topic)

def getTopicNumber(irc, msg, args, state):
    def error(s):
        irc.errorInvalid('topic number', s)
    try:
        n = int(args[0])
        if not n:
            raise ValueError
    except ValueError:
        error(args[0])
    if n > 0:
        n -= 1
    topic = irc.state.getTopic(state.channel)
    separator = state.cb.registryValue('separator', state.channel)
    topics = splitTopic(topic, separator)
    if not topics:
        irc.error('There are no topics in %s.' % state.channel, Raise=True)
    try:
        topics[n]
    except IndexError:
        error(str(n))
    del args[0]
    while n < 0:
        n += len(topics)
    state.args.append(n)

addConverter('topic', getTopic)
addConverter('topicNumber', getTopicNumber)
addConverter('canChangeTopic', canChangeTopic)

def splitTopic(topic, separator):
    return filter(None, topic.split(separator))

class Topic(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.undos = ircutils.IrcDict()
        self.redos = ircutils.IrcDict()
        self.lastTopics = ircutils.IrcDict()

    def _splitTopic(self, topic, channel):
        separator = self.registryValue('separator', channel)
        return splitTopic(topic, separator)

    def _joinTopic(self, channel, topics):
        separator = self.registryValue('separator', channel)
        return separator.join(topics)

    def _addUndo(self, channel, topics):
        stack = self.undos.setdefault(channel, [])
        stack.append(topics)
        maxLen = self.registryValue('undo.max', channel)
        del stack[:len(stack)-maxLen]

    def _addRedo(self, channel, topics):
        stack = self.redos.setdefault(channel, [])
        stack.append(topics)
        maxLen = self.registryValue('undo.max', channel)
        del stack[:len(stack)-maxLen]

    def _getUndo(self, channel):
        try:
            return self.undos[channel].pop()
        except (KeyError, IndexError):
            return None

    def _getRedo(self, channel):
        try:
            return self.redos[channel].pop()
        except (KeyError, IndexError):
            return None

    def _sendTopics(self, irc, channel, topics, isDo=False):
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
        if not isDo and channel in self.redos:
            del self.redos[channel]
        irc.queueMsg(ircmsgs.topic(channel, newTopic))

    def topic(self, irc, msg, args, channel):
        """[<channel>]

        Returns the topic for <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        topic = irc.state.channels[channel].topic
        irc.reply(topic)
    topic = wrap(topic, ['inChannel'])

    def add(self, irc, msg, args, channel, topic, insert=False):
        """[<channel>] <topic>

        Adds <topic> to the topics for <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if insert:
            topics.insert(0, topic)
        else:
            topics.append(topic)
        self._sendTopics(irc, channel, topics)
    add = wrap(add, ['canChangeTopic', rest('topic')])

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
        newtopic = irc.state.getTopic(channel)
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if len(topics) == 0 or len(topics) == 1:
            irc.error('I can\'t shuffle 1 or fewer topics.', Raise=True)
        elif len(topics) == 2:
            topics.reverse()
        else:
            original = topics[:]
            while topics == original:
                random.shuffle(topics)
        self._sendTopics(irc, channel, topics)
    shuffle = wrap(shuffle, ['canChangeTopic'])

    def reorder(self, irc, msg, args, channel, numbers):
        """[<channel>] <number> [<number> ...]

        Reorders the topics from <channel> in the order of the specified
        <number> arguments.  <number> is a one-based index into the topics.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        num = len(topics)
        if num == 0 or num == 1:
            irc.error('I cannot reorder 1 or fewer topics.', Raise=True)
        if len(numbers) != num:
            irc.error('All topic numbers must be specified.', Raise=True)
        if sorted(numbers) != range(num):
            irc.error('Duplicate topic numbers cannot be specified.')
            return
        newtopics = [topics[i] for i in numbers]
        self._sendTopics(irc, channel, newtopics)
    reorder = wrap(reorder, ['canChangeTopic', many('topicNumber')])

    def list(self, irc, msg, args, channel):
        """[<channel>]

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
    list = wrap(list, ['inChannel'])

    def get(self, irc, msg, args, channel, number):
        """[<channel>] <number>

        Returns topic number <number> from <channel>.  <number> is a one-based
        index into the topics.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        irc.reply(topics[number])
    get = wrap(get, ['inChannel', 'topicNumber'])

    def change(self, irc, msg, args, channel, number, replacer):
        """[<channel>] <number> <regexp>

        Changes the topic number <number> on <channel> according to the regular
        expression <regexp>.  <number> is the one-based index into the topics;
        <regexp> is a regular expression of the form
        s/regexp/replacement/flags.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        topics[number] = replacer(topics[number])
        self._sendTopics(irc, channel, topics)
    change = wrap(change, ['canChangeTopic', 'topicNumber', 'regexpReplacer'])

    def set(self, irc, msg, args, channel, number, topic):
        """[<channel>] [<number>] <topic>

        Sets the topic <number> to be <text>.  If no <number> is given, this
        sets the entire topic.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        if number:
            topics = self._splitTopic(irc.state.getTopic(channel), channel)
            topics[number] = topic
        else:
            topics = [topic]
        self._sendTopics(irc, channel, topics)
    set = wrap(set, ['canChangeTopic',
                     optional('topicNumber', 0),
                     rest(('topic', False))])

    def remove(self, irc, msg, args, channel, number):
        """[<channel>] <number>

        Removes topic <number> from the topic for <channel>  Topics are
        numbered starting from 1; you can also use negative indexes to refer
        to topics starting the from the end of the topic.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        topic = topics.pop(number)
        self._sendTopics(irc, channel, topics)
    remove = wrap(remove, ['canChangeTopic', 'topicNumber'])

    def lock(self, irc, msg, args, channel):
        """[<channel>]

        Locks the topic (sets the mode +t) in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        irc.queueMsg(ircmsgs.mode(channel, '+t'))
    lock = wrap(lock, ['channel', ('haveOp', 'lock the topic')])

    def unlock(self, irc, msg, args, channel):
        """[<channel>]

        Locks the topic (sets the mode +t) in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        irc.queueMsg(ircmsgs.mode(channel, '-t'))
    unlock = wrap(unlock, ['channel', ('haveOp', 'unlock the topic')])

    def restore(self, irc, msg, args, channel):
        """[<channel>]

        Restores the topic to the last topic set by the bot.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        try:
            topics = self.lastTopics[channel]
        except KeyError:
            irc.error('I haven\'t yet set the topic in %s.' % channel)
            return
        self._sendTopics(irc, channel, topics)
    restore = wrap(restore, ['canChangeTopic'])

    def undo(self, irc, msg, args, channel):
        """[<channel>]

        Restores the topic to the one previous to the last topic command that
        set it.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        self._addRedo(channel, self._getUndo(channel)) # current topic.
        topics = self._getUndo(channel) # This is the topic list we want.
        if topics is not None:
            self._sendTopics(irc, channel, topics, isDo=True)
        else:
            irc.error('There are no more undos for %s.' % channel)
    undo = wrap(undo, ['canChangetopic'])

    def redo(self, irc, msg, args, channel):
        """[<channel>]

        Undoes the last undo.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        topics = self._getRedo(channel)
        if topics is not None:
            self._sendTopics(irc, channel, topics, isDo=True)
        else:
            irc.error('There are no redos for %s.' % channel)
    redo = wrap(redo, ['canChangeTopic'])

    def swap(self, irc, msg, args, channel, first, second):
        """[<channel>] <first topic number> <second topic number>

        Swaps the order of the first topic number and the second topic number.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if first == second:
            irc.error('I refuse to swap the same topic with itself.')
            return
        t = topics[first]
        topics[first] = topics[second]
        topics[second] = t
        self._sendTopics(irc, channel, topics)
    swap = wrap(swap, ['canChangeTopic', 'topicNumber', 'topicNumber'])

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
    default = wrap(default, ['canChangeTopic'])

    def separator(self, irc, msg, args, channel, separator):
        """[<channel>] <separator>

        Sets the topic separator for <channel> to <separator>  Converts the
        current topic appropriately.
        """
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        self.setRegistryValue('separator', separator, channel)
        self._sendTopics(irc, channel, topics)
    separator = wrap(separator, ['canChangeTopic', 'something'])

Class = Topic


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
