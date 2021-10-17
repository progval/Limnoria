###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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

import os
import re
import random
import shutil
import tempfile

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization('Topic')

import supybot.ircdb as ircdb

import supybot.utils.minisix as minisix
pickle = minisix.pickle

def canChangeTopic(irc, msg, args, state):
    assert not state.channel
    callConverter('channel', irc, msg, args, state)
    callConverter('inChannel', irc, msg, args, state)
    if state.channel not in irc.state.channels:
        state.error(format(_('I\'m not currently in %s.'), state.channel),
                    Raise=True)
    c = irc.state.channels[state.channel]
    if 't' in c.modes and not c.isHalfopPlus(irc.nick):
        state.error(format(_('I can\'t change the topic, I\'m not (half)opped '
                             'and %s is +t.'), state.channel), Raise=True)


def getTopic(irc, msg, args, state, format=True):
    separator = state.cb.registryValue('separator', state.channel, irc.network)
    if separator in args[0] and not \
            state.cb.registryValue('allowSeparatorinTopics',
                                   state.channel, irc.network):
        state.errorInvalid('topic', args[0],
                           format(_('The topic must not include %q.'),
                                  separator))
    topic = args.pop(0)
    if format:
        env = {'topic': topic}
        formatter = state.cb.registryValue('format', state.channel, irc.network)
        topic = ircutils.standardSubstitute(irc, msg, formatter, env)
    state.args.append(topic)


def getTopicNumber(irc, msg, args, state):
    def error(s):
        state.errorInvalid(_('topic number'), s)
    try:
        n = int(args[0])
        if not n:
            raise ValueError
    except ValueError:
        error(args[0])
    if n > 0:
        n -= 1
    topic = irc.state.getTopic(state.channel)
    separator = state.cb.registryValue('separator', state.channel, irc.network)
    topics = splitTopic(topic, separator)
    if not topics:
        state.error(format(_('There are no topics in %s.'), state.channel),
                    Raise=True)
    try:
        topics[n]
    except IndexError:
        error(args[0])
    del args[0]
    while n < 0:
        n += len(topics)
    state.args.append(n)

addConverter('topic', getTopic)
addConverter('topicNumber', getTopicNumber)
addConverter('canChangeTopic', canChangeTopic)


def splitTopic(topic, separator):
    return list(filter(None, topic.split(separator)))

datadir = conf.supybot.directories.data()
filename = conf.supybot.directories.data.dirize('Topic.pickle')


class Topic(callbacks.Plugin):
    """This plugin allows you to use many topic-related functions,
    such as Add, Undo, and Remove."""

    def __init__(self, irc):
        self.__parent = super(Topic, self)
        self.__parent.__init__(irc)
        self.undos = ircutils.IrcDict()
        self.redos = ircutils.IrcDict()
        self.lastTopics = ircutils.IrcDict()
        self.watchingFor332 = ircutils.IrcSet()
        try:
            pkl = open(filename, 'rb')
            try:
                self.undos = pickle.load(pkl)
                self.redos = pickle.load(pkl)
                self.lastTopics = pickle.load(pkl)
                self.watchingFor332 = pickle.load(pkl)
            except Exception as e:
                self.log.debug('Unable to load pickled data: %s', e)
            pkl.close()
        except IOError as e:
            self.log.debug('Unable to open pickle file: %s', e)
        world.flushers.append(self._flush)

    def die(self):
        world.flushers.remove(self._flush)
        self.__parent.die()

    def _flush(self):
        try:
            pklfd, tempfn = tempfile.mkstemp(suffix='topic', dir=datadir)
            pkl = os.fdopen(pklfd, 'wb')
            try:
                pickle.dump(self.undos, pkl)
                pickle.dump(self.redos, pkl)
                pickle.dump(self.lastTopics, pkl)
                pickle.dump(self.watchingFor332, pkl)
            except Exception as e:
                self.log.warning('Unable to store pickled data: %s', e)
            pkl.close()
            shutil.move(tempfn, filename)
        except (IOError, shutil.Error) as e:
            self.log.warning('File error: %s', e)

    def _splitTopic(self, irc, channel):
        topic = irc.state.getTopic(channel)
        separator = self.registryValue('separator', channel, irc.network)
        return splitTopic(topic, separator)

    def _joinTopic(self, irc, channel, topics):
        separator = self.registryValue('separator', channel, irc.network)
        return separator.join(topics)

    def _addUndo(self, irc, channel, topics):
        stack = self.undos.setdefault(channel, [])
        stack.append(topics)
        maxLen = self.registryValue('undo.max', channel, irc.network)
        del stack[:len(stack) - maxLen]

    def _addRedo(self, irc, channel, topics):
        stack = self.redos.setdefault(channel, [])
        stack.append(topics)
        maxLen = self.registryValue('undo.max', channel, irc.network)
        del stack[:len(stack) - maxLen]

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

    def _formatTopics(self, irc, channel, topics, fit=False):
        topics = [s for s in topics if s and not s.isspace()]
        self.lastTopics[channel] = topics
        newTopic = self._joinTopic(irc, channel, topics)
        try:
            maxLen = irc.state.supported['topiclen']
            if fit:
                while len(newTopic) > maxLen:
                    topics.pop(0)
                    self.lastTopics[channel] = topics
                    newTopic = self._joinTopic(irc, channel, topics)
            elif len(newTopic) > maxLen:
                if self.registryValue('recognizeTopiclen', channel, irc.network):
                    irc.error(format(_('That topic is too long for this '
                                       'server (maximum length: %i; this topic: '
                                       '%i).'), maxLen, len(newTopic)),
                              Raise=True)
        except KeyError:
            pass
        return newTopic

    def _sendTopics(self, irc, channel, topics=None, isDo=False, fit=False):
        if isinstance(topics, list) or isinstance(topics, tuple):
            assert topics is not None
            topics = self._formatTopics(irc, channel, topics, fit)
        self._addUndo(irc, channel, topics)
        if not isDo and channel in self.redos:
            del self.redos[channel]
        irc.queueMsg(ircmsgs.topic(channel, topics))
        irc.noReply()

    def _checkManageCapabilities(self, irc, msg, channel):
        """Check if the user has any of the required capabilities to manage
        the channel topic.

        The list of required capabilities is in requireManageCapability
        channel config.

        Also allow if the user is a chanop. Since they can change the topic
        manually anyway.
        """
        c = irc.state.channels[channel]
        if msg.nick in c.ops or msg.nick in c.halfops or 't' not in c.modes:
            return True
        capabilities = self.registryValue('requireManageCapability',
                                          channel, irc.network)
        if capabilities:
            for capability in re.split(r'\s*;\s*', capabilities):
                if capability.startswith('channel,'):
                    capability = ircdb.makeChannelCapability(
                        channel, capability[8:])
                if capability and ircdb.checkCapability(msg.prefix, capability):
                    return
            capabilities = self.registryValue('requireManageCapability',
                                              channel, irc.network)
            irc.errorNoCapability(capabilities, Raise=True)
        else:
            return

    def doJoin(self, irc, msg):
        if ircutils.strEqual(msg.nick, irc.nick):
            # We're joining a channel, let's watch for the topic.
            self.watchingFor332.add(msg.args[0])

    def do315(self, irc, msg):
        # Try to restore the topic when not set yet.
        channel = msg.args[1]
        c = irc.state.channels.get(channel)
        if c is None or not self.registryValue('setOnJoin', channel, irc.network):
            return
        if irc.nick not in c.ops and 't' in c.modes:
            self.log.debug('Not trying to restore topic in %s. I\'m not opped '
                           'and %s is +t.', channel, channel)
            return
        try:
            topics = self.lastTopics[channel]
        except KeyError:
            self.log.debug('No topic to auto-restore in %s.', channel)
        else:
            newTopic = self._formatTopics(irc, channel, topics)
            if c.topic == '' or (c.topic != newTopic and
                                 self.registryValue('alwaysSetOnJoin',
                                                    channel, irc.network)):
                self._sendTopics(irc, channel, newTopic)

    def do332(self, irc, msg):
        if msg.args[1] in self.watchingFor332:
            self.watchingFor332.remove(msg.args[1])
            # Store an undo for the topic when we join a channel.  This allows
            # us to undo the first topic change that takes place in a channel.
            self._addUndo(irc, msg.args[1], [msg.args[2]])

    def topic(self, irc, msg, args, channel):
        """[<channel>]

        Returns the topic for <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        topic = irc.state.channels[channel].topic
        irc.reply(topic)
    topic = wrap(topic, ['inChannel'])

    def add(self, irc, msg, args, channel, topic):
        """[<channel>] <topic>

        Adds <topic> to the topics for <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        topics.append(topic)
        self._sendTopics(irc, channel, topics)
    add = wrap(add, ['canChangeTopic', rest('topic')])

    def fit(self, irc, msg, args, channel, topic):
        """[<channel>] <topic>

        Adds <topic> to the topics for <channel>.  If the topic is too long
        for the server, topics will be popped until there is enough room.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        topics.append(topic)
        self._sendTopics(irc, channel, topics, fit=True)
    fit = wrap(fit, ['canChangeTopic', rest('topic')])

    def replace(self, irc, msg, args, channel, i, topic):
        """[<channel>] <number> <topic>

        Replaces topic <number> with <topic>.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        topics[i] = topic
        self._sendTopics(irc, channel, topics)
    replace = wrap(replace, ['canChangeTopic', 'topicNumber', rest('topic')])

    def insert(self, irc, msg, args, channel, topic):
        """[<channel>] <topic>

        Adds <topic> to the topics for <channel> at the beginning of the topics
        currently on <channel>.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        topics.insert(0, topic)
        self._sendTopics(irc, channel, topics)
    insert = wrap(insert, ['canChangeTopic', rest('topic')])

    def shuffle(self, irc, msg, args, channel):
        """[<channel>]

        Shuffles the topics in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        if len(topics) == 0 or len(topics) == 1:
            irc.error(_('I can\'t shuffle 1 or fewer topics.'), Raise=True)
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
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        num = len(topics)
        if num == 0 or num == 1:
            irc.error(_('I cannot reorder 1 or fewer topics.'), Raise=True)
        if len(numbers) != num:
            irc.error(_('All topic numbers must be specified.'), Raise=True)
        if sorted(numbers) != list(range(num)):
            irc.error(_('Duplicate topic numbers cannot be specified.'))
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
        topics = self._splitTopic(irc, channel)
        L = []
        for (i, t) in enumerate(topics):
            L.append(format(_('%i: %s'), i + 1, utils.str.ellipsisify(t, 30)))
        s = utils.str.commaAndify(L)
        irc.reply(s)
    list = wrap(list, ['inChannel'])

    def get(self, irc, msg, args, channel, number):
        """[<channel>] <number>

        Returns topic number <number> from <channel>.  <number> is a one-based
        index into the topics.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        topics = self._splitTopic(irc, channel)
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
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        topics[number] = replacer(topics[number])
        self._sendTopics(irc, channel, topics)
    change = wrap(change, ['canChangeTopic', 'topicNumber', 'regexpReplacer'])

    def set(self, irc, msg, args, channel, number, topic):
        """[<channel>] [<number>] <topic>

        Sets the topic <number> to be <text>.  If no <number> is given, this
        sets the entire topic.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        if number is not None:
            topics = self._splitTopic(irc, channel)
            topics[number] = topic
        else:
            topics = [topic]
        self._sendTopics(irc, channel, topics)
    set = wrap(set, ['canChangeTopic',
                     optional('topicNumber'),
                     rest(('topic', False))])

    def remove(self, irc, msg, args, channel, numbers):
        """[<channel>] <number1> [<number2> <number3>...]

        Removes topics <numbers> from the topic for <channel>  Topics are
        numbered starting from 1; you can also use negative indexes to refer
        to topics starting the from the end of the topic.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        numbers = set(numbers)
        for n in numbers:
            # Equivalent of marking the topic for deletion; there's no
            # simple, easy way of removing multiple items from a list.
            # pop() will shift the indices after every run.
            topics[n] = ''
        topics = [topic for topic in topics if topic != '']
        self._sendTopics(irc, channel, topics)
    remove = wrap(remove, ['canChangeTopic', many('topicNumber')])

    def lock(self, irc, msg, args, channel):
        """[<channel>]

        Locks the topic (sets the mode +t) in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        irc.queueMsg(ircmsgs.mode(channel, '+t'))
        irc.noReply()
    lock = wrap(lock, ['channel', ('haveHalfop+', _('lock the topic'))])

    def unlock(self, irc, msg, args, channel):
        """[<channel>]

        Unlocks the topic (sets the mode -t) in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        irc.queueMsg(ircmsgs.mode(channel, '-t'))
        irc.noReply()
    unlock = wrap(unlock, ['channel', ('haveHalfop+', _('unlock the topic'))])

    def restore(self, irc, msg, args, channel):
        """[<channel>]

        Restores the topic to the last topic set by the bot.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        try:
            topics = self.lastTopics[channel]
            if not topics:
                raise KeyError
        except KeyError:
            irc.error(format(_('I haven\'t yet set the topic in %s.'),
                             channel))
            return
        self._sendTopics(irc, channel, topics)
    restore = wrap(restore, ['canChangeTopic'])

    def refresh(self, irc, msg, args, channel):
        """[<channel>]
        Refreshes current topic set by anyone. Restores topic if empty.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topic = irc.state.channels[channel].topic
        if topic:
            self._sendTopics(irc, channel, topic)
            return
        try:
            topics = self.lastTopics[channel]
            if not topics:
                raise KeyError
        except KeyError:
            irc.error(format(_('I haven\'t yet set the topic in %s.'),
                             channel))
            return
        self._sendTopics(irc, channel, topics)
    refresh = wrap(refresh, ['canChangeTopic'])

    def undo(self, irc, msg, args, channel):
        """[<channel>]

        Restores the topic to the one previous to the last topic command that
        set it.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        self._addRedo(irc, channel, self._getUndo(channel))  # current topic.
        topics = self._getUndo(channel)  # This is the topic list we want.
        if topics is not None:
            self._sendTopics(irc, channel, topics, isDo=True)
        else:
            irc.error(format(_('There are no more undos for %s.'), channel))
    undo = wrap(undo, ['canChangetopic'])

    def redo(self, irc, msg, args, channel):
        """[<channel>]

        Undoes the last undo.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._getRedo(channel)
        if topics is not None:
            self._sendTopics(irc, channel, topics, isDo=True)
        else:
            irc.error(format(_('There are no redos for %s.'), channel))
    redo = wrap(redo, ['canChangeTopic'])

    def swap(self, irc, msg, args, channel, first, second):
        """[<channel>] <first topic number> <second topic number>

        Swaps the order of the first topic number and the second topic number.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        if first == second:
            irc.error(_('I refuse to swap the same topic with itself.'))
            return
        t = topics[first]
        topics[first] = topics[second]
        topics[second] = t
        self._sendTopics(irc, channel, topics)
    swap = wrap(swap, ['canChangeTopic', 'topicNumber', 'topicNumber'])

    def save(self, irc, msg, args, channel):
        """[<channel>]

        Saves the topic in <channel> to be restored with 'topic default'
        later. <channel> is only necessary if the message isn't sent in
        the channel itself.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topic = irc.state.getTopic(channel)
        if topic:
            self.setRegistryValue('default', value=topic, channel=channel)
        else:
            self.setRegistryValue('default', value='', channel=channel)
        irc.replySuccess()
    save = wrap(save, ['channel', 'inChannel'])

    def default(self, irc, msg, args, channel):
        """[<channel>]

        Sets the topic in <channel> to the default topic for <channel>.  The
        default topic for a channel may be configured via the configuration
        variable supybot.plugins.Topic.default.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topic = self.registryValue('default', channel, irc.network)
        if topic:
            self._sendTopics(irc, channel, [topic])
        else:
            irc.error(format(_('There is no default topic configured for %s.'),
                             channel))
    default = wrap(default, ['canChangeTopic'])

    def separator(self, irc, msg, args, channel, separator):
        """[<channel>] <separator>

        Sets the topic separator for <channel> to <separator>  Converts the
        current topic appropriately.
        """
        self._checkManageCapabilities(irc, msg, channel)
        topics = self._splitTopic(irc, channel)
        self.setRegistryValue('separator', separator, channel)
        self._sendTopics(irc, channel, topics)
    separator = wrap(separator, ['canChangeTopic', 'something'])

Class = Topic


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
