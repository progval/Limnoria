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
Provides commands for manipulating channel topics.
"""

__revision__ = "$Id$"

import plugins

import re
import random

import conf
import utils
import ircdb
import ircmsgs
import plugins
import privmsgs
import callbacks
import configurable

def ConfigurableTopicSeparator(s):
    s = configurable.StrType(s)
    if s.lstrip() == s:
        s = ' ' + s
    if s.rstrip() == s:
        s += ' '
    return s

class Topic(callbacks.Privmsg, configurable.Mixin):
    topicFormatter = '%s (%s)'
    topicUnformatter = re.compile('(.*) \((\S+)\)')
    configurables = configurable.Dictionary(
        [('separator', configurable.StrType, ' || ',
          "The separator between individual topics in the channel topic.")]
    )
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        configurable.Mixin.__init__(self)

    def _splitTopic(self, topic, channel):
        separator = self.configurables.get('separator', channel)
        return filter(None, topic.split(separator))

    def _joinTopic(self, topics, channel):
        separator = self.configurables.get('separator', channel)
        return separator.join(topics)

    def add(self, irc, msg, args, channel):
        """[<channel>] <topic>

        Adds <topic> to the topics for <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        topic = privmsgs.getArgs(args)
        separator = self.configurables.get('separator', channel)
        if separator in topic:
            s = 'You can\'t have %s in your topic' % separator
            irc.error(msg, s)
            return
        currentTopic = irc.state.getTopic(channel)
        try:
            name = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            name = msg.nick
        formattedTopic = self.topicFormatter % (topic, name)
        if currentTopic:
            newTopic = self._joinTopic([currentTopic, formattedTopic], channel)
        else:
            newTopic = formattedTopic
        irc.queueMsg(ircmsgs.topic(channel, newTopic))
    add = privmsgs.checkChannelCapability(add, 'topic')

    def shuffle(self, irc, msg, args, channel):
        """[<channel>]

        Shuffles the topics in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        newtopic = irc.state.getTopic(channel)
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if len(topics) == 0 or len(topics) == 1:
            irc.error(msg, 'I can\'t shuffle 1 or fewer topics.')
            return
        elif len(topics) == 2:
            topics.reverse()
            newtopic = self._joinTopic(topics, channel)
        else:
            random.shuffle(topics)
            newtopic = self._joinTopic(topics, channel)
            while newtopic == irc.state.getTopic(channel):
                random.shuffle(topics)
                newtopic = self._joinTopic(topics, channel)
        irc.queueMsg(ircmsgs.topic(channel, newtopic))
    shuffle = privmsgs.checkChannelCapability(shuffle, 'topic')

    def reorder(self, irc, msg, args, channel):
        """[<channel>] <number> [<number> ...]

        Reorders the topics from <channel> in the order of the specified
        <number> arguments.  <number> is a one-based index into the topics.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        num = len(topics)
        if num == 0 or num == 1:
            irc.error(msg, 'I cannot reorder 1 or fewer topics.')
            return
        if len(args) != num:
            irc.error(msg, 'All topic numbers must be specified.')
            return
        order = privmsgs.getArgs(args, required=num)
        if topics:
            for i,p in enumerate(order):
                try:
                    p = int(p)
                    if p > 0:
                        order[i] = p - 1
                    elif p == 0:
                        irc.error(msg, '0 is not a valid topic number.')
                        return
                    else:
                        order[i] = num + p
                except ValueError:
                    irc.error(msg, 'The positions must be valid integers.')
                    return
            if utils.sorted(order) != range(num):
                irc.error(msg, 'Duplicate topic numbers cannot be specified.')
                return
            try:
                newtopics = [topics[i] for i in order]
                newtopic = self._joinTopic(newtopics, channel)
                irc.queueMsg(ircmsgs.topic(channel, newtopic))
            except IndexError:
                irc.error(msg, 'An invalid topic number was specified.')
        else:
            irc.error(msg, 'There are no topics to reorder.')
    reorder = privmsgs.checkChannelCapability(reorder, 'topic')

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
                irc.error(msg, 'That\'s not a valid topic number.')
                return
        except ValueError:
            irc.error(msg, 'The argument must be a valid integer.')
            return
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if topics:
            try:
                match = self.topicUnformatter.match(topics[number])
                if match:
                    irc.reply(msg, match.group(1))
                else:
                    irc.reply(msg, topics[number])
            except IndexError:
                irc.error(msg, 'That\'s not a valid topic.')
        else:
            irc.error(msg, 'There are no topics to get.')
    get = privmsgs.channel(get)

    def change(self, irc, msg, args, channel):
        """[<channel>] <number> <regexp>

        Changes the topic number <number> on <channel> according to the regular
        expression <regexp>.  <number> is the one-based index into the topics;
        <regexp> is a regular expression of the form
        s/regexp/replacement/flags.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        (number, regexp) = privmsgs.getArgs(args, required=2)
        try:
            number = int(number)
            if number > 0:
                number -= 1
            elif number == 0:
                irc.error(msg, 'That\'s not a valid topic number.')
                return
        except ValueError:
            irc.error(msg, 'The <number> argument must be a number.')
            return
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error(msg, 'The regexp wasn\'t valid: %s' % e.args[0])
            return
        except re.error, e:
            irc.error(msg, utils.exnToString(e))
            return
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        if not topics:
            irc.error(msg, 'There are no topics to change.')
            return
        topic = topics.pop(number)
        match = self.topicUnformatter.match(topic)
        if match is None:
            name = ''
        else:
            (topic, name) = match.groups()
        try:
            senderName = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        if name and name != senderName and \
           not ircdb.checkCapabilities(msg.prefix, ('op', 'admin')):
            irc.error(msg, 'You can only modify your own topics.')
            return
        newTopic = self.topicFormatter % (replacer(topic), name)
        if number < 0:
            number = len(topics)+1+number
        topics.insert(number, newTopic)
        newTopic = self._joinTopic(topics, channel)
        irc.queueMsg(ircmsgs.topic(channel, newTopic))
    change = privmsgs.checkChannelCapability(change, 'topic')

    def remove(self, irc, msg, args, channel):
        """[<channel>] <number>

        Removes topic <number> from the topic for <channel>  Topics are
        numbered starting from 1; you can also use negative indexes to refer
        to topics starting the from the end of the topic.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        try:
            number = int(privmsgs.getArgs(args))
            if number > 0:
                number -= 1
            elif number == 0:
                irc.error(msg, 'That\'s not a valid topic number.')
                return
        except ValueError:
            irc.error(msg, 'The argument must be a number.')
            return
        topics = self._splitTopic(irc.state.getTopic(channel), channel)
        try:
            topic = topics.pop(number)
        except IndexError:
            irc.error(msg, 'That\'s not a valid topic number.')
            return
        match = self.topicUnformatter.match(topic)
        if match is None:
            name = ''
        else:
            (topic, name) = match.groups()
        try:
            username = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            username = msg.nick
        if name and name != username and \
           not ircdb.checkCapabilities(msg.prefix, ('op', 'admin')):
            irc.error(msg, 'You can only remove your own topics.')
            return
        newTopic = self._joinTopic(topics, channel)
        irc.queueMsg(ircmsgs.topic(channel, newTopic))
    remove = privmsgs.checkChannelCapability(remove, 'topic')


Class = Topic


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
