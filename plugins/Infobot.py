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
Infobot compatibility, for the parts that we don't support already.
"""

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import supybot.plugins as plugins

import os
import re
import random
import cPickle as pickle

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

conf.registerPlugin('Infobot')
conf.registerGlobalValue(conf.supybot.plugins.Infobot, 'personality',
    registry.Boolean(True, """Determines whether the bot will respond with
    personable (Infobot-like) responses rather than its standard messages."""))
conf.registerGlobalValue(conf.supybot.plugins.Infobot, 'boringDunno',
    registry.String('Dunno.', """Determines what boring dunno should be given
    if supybot.plugins.Infobot.personality is False."""))
conf.registerGlobalValue(conf.supybot.plugins.Infobot,
    'snarfUnaddressedDefinitions', registry.Boolean(True, """Determines whether
    the bot will snarf definitions given in the channel that weren't directly
    addressed to it.  Of course, no confirmation will be given if the bot isn't
    directly addressed."""))
conf.registerGlobalValue(conf.supybot.plugins.Infobot,
    'answerUnaddressedQuestions', registry.Boolean(True, """Determines whether
    the bot will answer questions that weren't directly addressed to it.  Of
    course, if it doesn't have an answer, it will remain silent."""))

def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Infobot', True)

filename = os.path.join(conf.supybot.directories.data(), 'Infobot.db')

class InfobotDB(object):
    def __init__(self):
        try:
            fd = file(filename)
        except EnvironmentError:
            self._is = utils.InsensitivePreservingDict()
            self._are = utils.InsensitivePreservingDict()
        else:
            (self._is, self._are) = pickle.load(fd)
        self._changes = 0
        self._responses = 0
        self._ends = ['!',
                      '.',
                      ', $who.',]
        self._dunnos = ['Dunno',
                        'No idea',
                        'I don\'t know',
                        'I have no idea',
                        'I don\'t have a clue',]
        self._confirms = ['10-4',
                          'Okay',
                          'Got it',
                          'Gotcha',
                          'I hear ya']

    def flush(self):
        fd = file(filename, 'w')
        pickle.dump((self._is, self._are), fd)
        fd.close()

    def close(self):
        self.flush()

    def getIs(self, factoid):
        ret = self._is[factoid]
        self._responses += 1
        return ret

    def setIs(self, fact, oid):
        self._changes += 1
        self._is[fact] = oid
        self.flush()

    def delIs(self, factoid):
        del self._is[factoid]
        self._changes += 1
        self.flush()

    def hasIs(self, factoid):
        return factoid in self._is

    def getAre(self, factoid):
        ret = self._are[factoid]
        self._responses += 1
        return ret

    def hasAre(self, factoid):
        return factoid in self._are

    def setAre(self, fact, oid):
        self._changes += 1
        self._are[fact] = oid
        self.flush()

    def delAre(self, factoid):
        del self._are[factoid]
        self._changes += 1
        self.flush()

    def getDunno(self):
        return random.choice(self._dunnos) + random.choice(self._ends)

    def getConfirm(self):
        return random.choice(self._confirms) + random.choice(self._ends)

    def getChangeCount(self):
        return self._changes

    def getResponseCount(self):
        return self._responses

class Infobot(callbacks.PrivmsgCommandAndRegexp):
    regexps = ['doForget', 'doFactoid', 'doUnknown']
    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        try:
            self.db = InfobotDB()
        except Exception:
            self.log.exception('Error loading %s:', filename)
            raise # So it doesn't get loaded without its database.
        self.irc = None
        self.msg = None
        self.force = False
        self.replied = False
        self.addressed = False

    def die(self):
        self.db.close()

    def reply(self, s, irc=None, msg=None, action=False):
        if self.replied:
            self.log.debug('Already replied, not replying again.')
            return
        if irc is None:
            assert self.irc is not None
            irc = self.irc
        if msg is None:
            assert self.msg is not None
            msg = self.msg
        self.replied = True
        irc.reply(plugins.standardSubstitute(irc, msg, s), prefixName=False,
                  action=action)

    def confirm(self, irc=None, msg=None):
        if self.registryValue('personality'):
            self.reply(self.db.getConfirm(), irc=irc, msg=msg)
        else:
            assert self.irc is not None
            self.irc.replySuccess()

    def dunno(self, irc=None, msg=None):
        if self.registryValue('personality'):
            self.reply(self.db.getDunno(), irc=irc, msg=msg)
        else:
            self.reply(self.registryValue('boringDunno'), irc=irc, msg=msg)

    def factoid(self, key, irc=None, msg=None):
        if irc is None:
            assert self.irc is not None
            irc = self.irc
        if msg is None:
            assert self.msg is not None
            msg = self.msg
        isAre = None
        if self.db.hasIs(key):
            isAre = 'is'
            value = self.db.getIs(key)
        elif self.db.hasAre(key):
            isAre = 'are'
            value = self.db.getAre(key)
        if isAre is None:
            if self.addressed:
                self.dunno(irc=irc, msg=msg)
        else:
            # XXX
            value = random.choice(value.split('|'))
            if value.startswith('<reply>'):
                self.reply('%s' % value[7:].strip(), irc=irc, msg=msg)
            elif value.startswith('<action>'):
                self.reply('%s' % value[8:].strip(), irc=irc, msg=msg,
                           action=True)
            else:
                self.reply('%s %s %s, $who.' % (key,isAre,value), irc=irc, msg=msg)

    def normalize(self, s):
        s = ircutils.stripFormatting(s)
        s = s.strip() # After stripFormatting for formatted spaces.
        s = utils.normalizeWhitespace(s)
        contractions = [('what\'s', 'what is'), ('where\'s', 'where is'),
                        ('who\'s', 'who is'),]
        for (contraction, replacement) in contractions:
            if s.startswith(contraction):
                s = replacement + s[len(contraction):]
        return s

    _forceRe = re.compile(r'^no[,: -]+', re.I)
    def doPrivmsg(self, irc, msg):
        try:
            if ircmsgs.isCtcp(msg):
                return
            maybeAddressed = callbacks.addressed(irc.nick, msg,
                                                 whenAddressedByNick=True)
            if maybeAddressed:
                self.addressed = True
                payload = maybeAddressed
            else:
                payload = msg.args[1]
            payload = self.normalize(payload)
            maybeForced = self._forceRe.sub('', payload)
            if maybeForced != payload:
                self.force = True
                payload = maybeForced
            # Let's make sure we dump out of Infobot if the privmsg is an
            # actual command otherwise we could get multiple responses.
            if self.addressed:
                try:
                    tokens = callbacks.tokenize(payload)
                    if callbacks.findCallbackForCommand(irc, tokens[0]):
                        return
                    else:
                        payload += '?'
                except SyntaxError:
                    pass
            if payload.endswith(irc.nick):
                self.addressed = True
                payload = payload[:-len(irc.nick)]
                payload = payload.strip(', ') # Strip punctuation separating nick.
                payload += '?' # So doUnknown gets called.
            msg = ircmsgs.privmsg(msg.args[0], payload, prefix=msg.prefix)
            callbacks.PrivmsgCommandAndRegexp.doPrivmsg(self, irc, msg)
        finally:
            self.force = False
            self.replied = False
            self.addressed = False

    def callCommand(self, f, irc, msg, *L, **kwargs):
        try:
            self.irc = irc
            self.msg = msg
            callbacks.PrivmsgCommandAndRegexp.callCommand(self, f, irc, msg,
                                                          *L, **kwargs)
        finally:
            self.irc = None
            self.msg = None

    def doForget(self, irc, msg, match):
        r"^forget\s+(.+?)[?!. ]*$"
        fact = match.group(1)
        deleted = False
        for method in [self.db.delIs, self.db.delAre]:
            try:
                method(fact)
                deleted = True
            except KeyError:
                pass
        if deleted:
            self.confirm()
        else:
            # XXX: Should this be genericified?
            irc.reply('I\'ve never heard of %s, %s!' % (fact, msg.nick))

    def doUnknown(self, irc, msg, match):
        r"^(.+?)\?[?!. ]*$"
        key = match.group(1)
        if self.addressed or self.registryValue('answerUnaddressedQuestions'):
            self.factoid(key) # Does the dunno'ing for us itself.
    # TODO: Add invalidCommand.

    def doFactoid(self, irc, msg, match):
        r"^(.+)\s+(?<!\\)(was|is|am|were|are)\s+(also\s+)?(.+?)[?!. ]*$"
        (key, isAre, also, value) = match.groups()
        key = key.replace('\\', '')
        if key.lower() in ('where', 'what', 'who'):
            # It's a question.
            if self.addressed or \
               self.registryValue('answerUnaddressedQuestions'):
                self.factoid(value)
            return
        if not self.addressed and \
           not self.registryValue('snarfUnaddressedDefinitions'):
            return
        isAre = isAre.lower()
        if isAre in ('was', 'is', 'am'):
            if self.db.hasIs(key):
                if also:
                    self.log.info('Adding %r to %r.', key, value)
                    value = '%s or %s' % (self.db.getIs(key), value)
                elif self.force:
                    self.log.info('Forcing %r to %r.', key, value)
                elif self.addressed:
                    value = self.db.getIs(key)
                    self.reply('But %s is %s, %s.' % (key, value, msg.nick))
                    return
            self.db.setIs(key, value)
        else:
            if self.db.hasAre(key):
                if also:
                    self.log.info('Adding %r to %r.', key, value)
                    value = '%s or %s' % (self.db.getAre(key), value)
                elif self.force:
                    self.log.info('Forcing %r to %r.', key, value)
                elif self.addressed:
                    value = self.db.getAre(key)
                    self.reply('But %s are %s, %s.' % (key, value, msg.nick))
                    return
            self.db.setAre(key, value)
        if self.addressed or self.force or also:
            self.confirm()

    def stats(self, irc, msg, args):
        """takes no arguments

        Returns the number of changes and requests made to the Infobot database
        since the plugin was loaded.
        """
        irc.reply('There have been %s answered and %s made '
                  'to the database since this plugin was loaded.' %
                  (utils.nItems('request', self.db.getChangeCount()),
                   utils.nItems('change', self.db.getResponseCount())))


Class = Infobot

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
