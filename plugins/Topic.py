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

import plugins

import re
import random

import conf
import debug
import utils
import ircdb
import ircmsgs
import privmsgs
import callbacks

example = utils.wrapLines("""
--- Topic for #sourcereview is If you notice *anything* that seems unintuitive about supybot, post it at http://tinyurl.com/nvct (jemfinch) || Supybot 0.72.1 released! (jemfinch) || If anyone is working on the .deb package for supybot please send me or jemfinch a note via the bot (Strike)
--- Topic for #sourcereview set by supybot at Mon Sep 29 15:56:10
<jemfinch> @list Topic
<supybot> jemfinch: addtopic, changetopic, removetopic, shuffletopic, topic
<jemfinch> @removetopic 2
--- supybot has changed the topic to: If you notice *anything* that seems unintuitive about supybot, post it at http://tinyurl.com/nvct (jemfinch) || If anyone is working on the .deb package for supybot please send me or jemfinch a note via the bot (Strike)
<jemfinch> @addtopic Tenative release for Supybot 0.73.0 is set for sunday
--- supybot has changed the topic to: If you notice *anything* that seems unintuitive about supybot, post it at http://tinyurl.com/nvct (jemfinch) || If anyone is working on the .deb package for supybot please send me or jemfinch a note via the bot (Strike) || Tenative release for Supybot 0.73.0 is set for sunday (jemfinch)
<jemfinch> @changetopic -1 s/sun/Sun/
--- supybot has changed the topic to: If you notice *anything* that seems unintuitive about supybot, post it at http://tinyurl.com/nvct (jemfinch) || If anyone is working on the .deb package for supybot please send me or jemfinch a note via the bot (Strike) || Tenative release for Supybot 0.73.0 is set for Sunday (jemfinch)
<jemfinch> @gettopic -2
<supybot> jemfinch: If anyone is working on the .deb package for supybot please send me or jemfinch a note via the bot (Strike)
<jemfinch> @shuffletopic
--- supybot has changed the topic to: If anyone is working on the .deb package for supybot please send me or jemfinch a note via the bot (Strike) || If you notice *anything* that seems unintuitive about supybot, post it at http://tinyurl.com/nvct (jemfinch) || Tenative release for Supybot 0.73.0 is set for Sunday (jemfinch)
""")

class Topic(callbacks.Privmsg):
    topicSeparator = ' || '
    topicFormatter = '%s (%s)'
    topicUnformatter = re.compile('(.*) \((\S+)\)')
    def _splitTopic(self, topic):
        return filter(None, topic.split(self.topicSeparator))

    def add(self, irc, msg, args, channel):
        """[<channel>] <topic>

        Adds <topic> to the topics for <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        topic = privmsgs.getArgs(args)
        if self.topicSeparator in topic:
            s = 'You can\'t have %s in your topic' % self.topicSeparator
            irc.error(msg, s)
            return
        currentTopic = irc.state.getTopic(channel)
        try:
            name = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            name = msg.nick
        formattedTopic = self.topicFormatter % (topic, name)
        if currentTopic:
            newTopic = self.topicSeparator.join((currentTopic,
                                                 formattedTopic))
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
        topics = self._splitTopic(irc.state.getTopic(channel))
        if len(topics) == 0 or len(topics) == 1:
            irc.error(msg, 'I can\'t shuffle 1 or fewer topics.')
            return
        elif len(topics) == 2:
            topics.reverse()
            newtopic = self.topicSeparator.join(topics)
        else:
            random.shuffle(topics)
            newtopic = self.topicSeparator.join(topics)
            while newtopic == irc.state.getTopic(channel):
                random.shuffle(topics)
                newtopic = self.topicSeparator.join(topics)
        irc.queueMsg(ircmsgs.topic(channel, newtopic))
    shuffle = privmsgs.checkChannelCapability(shuffle, 'topic')

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
        topics = self._splitTopic(irc.state.getTopic(channel))
        if topics:
            try:
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
        (number, regexp) = privmsgs.getArgs(args, needed=2)
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
            irc.error(msg, debug.exnToString(e))
            return
        topics = self._splitTopic(irc.state.getTopic(channel))
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
        newTopic = self.topicSeparator.join(topics)
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
        topics = self._splitTopic(irc.state.getTopic(channel))
        try:
            topic = topics.pop(number)
        except IndexError:
            irc.error(msg, 'That\'s not a valid topic number.')
            return
        ## debug.printf(topic)
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
        newTopic = self.topicSeparator.join(topics)
        irc.queueMsg(ircmsgs.topic(channel, newTopic))
    remove = privmsgs.checkChannelCapability(remove, 'topic')


Class = Topic


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
