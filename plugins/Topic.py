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

Commands include:
  addtopic
  removetopic
  shuffletopic
"""

from baseplugin import *

import re
import random
import sre_constants

import debug
import utils
import ircdb
import ircmsgs
import privmsgs
import callbacks

class Topic(callbacks.Privmsg):
    topicSeparator = ' || '
    topicFormatter = '%s (%s)'
    topicUnformatter = re.compile('(.*) \((.*)\)')
    def addtopic(self, irc, msg, args):
        """[<channel>] <topic>

        Adds <topic> to the topics for <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'topic')
        topic = privmsgs.getArgs(args)
        if ircdb.checkCapability(msg.prefix, capability):
            if topic.find(self.topicSeparator) != -1:
                s = 'You can\'t have %s in your topic' % self.topicSeparator
                irc.error(msg, s)
                return
            currentTopic = irc.state.getTopic(channel)
            try:
                name = ircdb.users.getUserName(msg.prefix)
            except KeyError:
                name = msg.nick
            formattedTopic = self.topicFormatter % (topic, name)
            if currentTopic:
                newTopic = self.topicSeparator.join((currentTopic,
                                                     formattedTopic))
            else:
                newTopic = formattedTopic
            irc.queueMsg(ircmsgs.topic(channel, newTopic))
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def shuffletopic(self, irc, msg, args):
        """[<channel>]

        Shuffles the topics in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'topic')
        if ircdb.checkCapability(msg.prefix, capability):
            topics = irc.state.getTopic(channel).split(self.topicSeparator)
            random.shuffle(topics)
            newtopic = self.topicSeparator.join(topics)
            irc.queueMsg(ircmsgs.topic(channel, newtopic))
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def topic(self, irc, msg, args):
        """[<channel>] <number>

        Returns topic number <number> from <channel>.  <number> is a zero-based
        index into the topics.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        i = privmsgs.getArgs(args)
        try:
            i = int(i)
        except ValueError:
            irc.error(msg, 'The argument must be a valid integer.')
            return
        topics = irc.state.getTopic(msg.args[0]).split(self.topicSeparator)
        try:
            irc.reply(msg, topics[i])
        except IndexError:
            irc.error(msg, 'That\'s not a valid index.')
            return
        
    def changetopic(self, irc, msg, args):
        """[<channel>] <number> <regexp>

        Changes the topic number <number> on <channel> according to the regular
        expression <regexp>.  <number> is the zero-based index into the topics;
        <regexp> is a regular expression of the form
        s/regexp/replacement/flags.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (number, regexp) = privmsgs.getArgs(args, needed=2)
        try:
            number = int(number)
        except ValueError:
            irc.error(msg, 'The <number> argument must be a number.')
            return
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error(msg, 'The regexp wasn\'t valid: %s' % e.args[0])
        except sre_constants.error, e:
            irc.error(msg, debug.exnToString(e))
            return
        topics = irc.state.getTopic(channel).split(self.topicSeparator)
        topic = topics.pop(number)
        (topic, name) = self.topicUnformatter.match(topic).groups()
        try:
            senderName = ircdb.users.getUserName(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        if name != senderName and \
           not ircdb.checkCapabilities(msg.prfix, ('op', 'admin')):
            irc.error(msg, 'You can only modify your own topics.')
            return
        newTopic = self.topicFormatter % (replacer(topic), name)
        topics.insert(number, newTopic)
        newTopic = self.topicSeparator.join(topics)
        irc.queueMsg(ircmsgs.topic(channel, newTopic))
        
    def removetopic(self, irc, msg, args):
        "[<channel>] (if not sent in the channel itself) <topic number>"
        channel = privmsgs.getChannel(msg, args)
        capability = ircdb.makeChannelCapability(channel, 'topic')
        try:
            number = int(privmsgs.getArgs(args))
        except ValueError:
            irc.error(msg, 'The argument must be a number.')
            return
        if ircdb.checkCapability(msg.prefix, capability):
            topics = irc.state.getTopic(channel).split(self.topicSeparator)
            topic = topics.pop(number)
            debug.printf(topic)
            (topic, name) = self.topicUnformatter.match(topic).groups()
            try:
                username = ircdb.users.getUserName(msg.prefix)
            except KeyError:
                username = msg.nick
            if name != username and \
               not ircdb.checkCapabilities(msg.prefix, ('op', 'admin')):
                irc.error(msg, 'You can only remove your own topics.')
                return
            newTopic = self.topicSeparator.join(topics)
            irc.queueMsg(ircmsgs.topic(channel, newTopic))
        else:
            irc.error(msg, conf.replyNoCapability % capability)


Class = Topic
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
