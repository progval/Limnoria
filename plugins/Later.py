#!/usr/bin/env python

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
Informal notes, mostly for compatibility with other bots.  Based entirely on
nicks, it's an easy way to tell users who refuse to register notes when they
arrive later.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import csv
import time

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Later', True)

conf.registerPlugin('Later')
conf.registerGlobalValue(conf.supybot.plugins.Later, 'maximum',
    registry.NonNegativeInteger(0, """Determines the maximum number of messages
    to be queued for a user.  If this value is 0, there is no maximum."""))
conf.registerGlobalValue(conf.supybot.plugins.Later, 'private',
    registry.Boolean(False, """Determines whether users will be notified in the
    first place in which they're seen, or in private."""))

class Later(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.notes = ircutils.IrcDict()
        self.wildcards = []
        self.filename = conf.supybot.directories.data.dirize('Later.db')
        self._openNotes()

    def die(self):
        self._flushNotes()

    def _flushNotes(self):
        fd = utils.transactionalFile(self.filename)
        writer = csv.writer(fd)
        for (nick, notes) in self.notes.iteritems():
            for (time, whence, text) in notes:
                writer.writerow([nick, time, whence, text])
        fd.close()

    def _openNotes(self):
        try:
            fd = file(self.filename)
        except EnvironmentError, e:
            self.log.warning('Couldn\'t open %s: %s', self.filename, e)
            return
        reader = csv.reader(fd)
        for (nick, time, whence, text) in reader:
            self._addNote(nick, whence, text, at=float(time), maximum=0)
        fd.close()

    def _timestamp(self, when):
        #format = conf.supybot.humanTimestampFormat()
        diff = time.time() - when
        try:
            return utils.timeElapsed(diff, seconds=False) + ' ago'
        except ValueError:
            return 'just now'
        
    def _addNote(self, nick, whence, text, at=None, maximum=None):
        if at is None:
            at = time.time()
        if maximum is None:
            maximum = self.registryValue('maximum')
        try:
            notes = self.notes[nick]
            if maximum and len(notes) >= maximum:
                raise ValueError
            else:
                notes.append((at, whence, text))
        except KeyError:
            self.notes[nick] = [(at, whence, text)]
        if '?' in nick or '*' in nick and nick not in self.wildcards:
            self.wildcards.append(nick)
        self._flushNotes()
        
    def tell(self, irc, msg, args):
        """<nick> <text>

        Tells <nick> <text> the next time <nick> is in seen.  <nick> can
        contain wildcard characters, and the first matching nick will be
        given the note.
        """
        (nick, text) = privmsgs.getArgs(args, required=2)
        if ircutils.strEqual(nick, irc.nick):
            irc.error('I can\'t send notes to myself.')
            return
        try:
            self._addNote(nick, msg.nick, text)
            irc.replySuccess()
        except ValueError:
            irc.error('That person\'s message queue is already full.')

    def doPrivmsg(self, irc, msg):
        try:
            notes = self.notes.pop(msg.nick)
        except KeyError:
            notes = []
        # Let's try wildcards.
        removals = []
        for wildcard in self.wildcards:
            if ircutils.hostmaskPatternEqual(wildcard, msg.nick):
                removals.append(wildcard)
                notes.extend(self.notes.pop(wildcard))
            for removal in removals:
                self.wildcards.remove(removal)
        if notes:
            irc = callbacks.SimpleProxy(irc, msg)
            private = self.registryValue('private')
            for (when, whence, note) in notes:
                s = 'Sent %s: <%s> %s' % (self._timestamp(when), whence, note)
                irc.reply(s, private=private)
            self._flushNotes()
            


Class = Later

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
