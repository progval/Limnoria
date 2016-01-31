###
# Copyright (c) 2004, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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

import csv
import time
import datetime

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Later')

class QueueIsFull(Exception):
    pass

class Later(callbacks.Plugin):
    """Used to do things later; currently, it only allows the sending of
    nick-based notes.  Do note (haha!) that these notes are *not* private
    and don't even pretend to be; if you want such features, consider using the
    Note plugin."""
    def __init__(self, irc):
        self.__parent = super(Later, self)
        self.__parent.__init__(irc)
        self._notes = ircutils.IrcDict()
        self.wildcards = []
        self.filename = conf.supybot.directories.data.dirize('Later.db')
        self._openNotes()

    def die(self):
        self._flushNotes()

    def _flushNotes(self):
        fd = utils.file.AtomicFile(self.filename)
        writer = csv.writer(fd)
        for (nick, notes) in self._notes.items():
            for (time, whence, text) in notes:
                writer.writerow([nick, time, whence, text])
        fd.close()

    def _openNotes(self):
        try:
            fd = open(self.filename)
        except EnvironmentError as e:
            self.log.warning('Couldn\'t open %s: %s', self.filename, e)
            return
        reader = csv.reader(fd)
        for (nick, time, whence, text) in reader:
            self._addNote(nick, whence, text, at=float(time), maximum=0)
        fd.close()

    def _timestamp(self, when):
        #format = conf.supybot.reply.format.time()
        diff = when - time.time()
        try:
            return utils.timeElapsed(diff, seconds=False)
        except ValueError:
            return _('just now')

    def _addNote(self, nick, whence, text, at=None, maximum=None):
        if at is None:
            at = time.time()
        if maximum is None:
            maximum = self.registryValue('maximum')
        try:
            notes = self._notes[nick]
            if maximum and len(notes) >= maximum:
                raise QueueIsFull()
            else:
                notes.append((at, whence, text))
        except KeyError:
            self._notes[nick] = [(at, whence, text)]
        if '?' in nick or '*' in nick and nick not in self.wildcards:
            self.wildcards.append(nick)
        self._flushNotes()

    def _validateNick(self, irc, nick):
        """Validate nick according to the IRC RFC 2812 spec.

        Reference: http://tools.ietf.org/rfcmarkup?doc=2812#section-2.3.1

        Some irc clients' tab-completion feature appends 'address' characters
        to nick, such as ':' or ','. We try correcting for that by trimming
        a char off the end.

        If nick incorrigibly invalid, return False, otherwise,
        return (possibly trimmed) nick.
        """
        if not irc.isNick(nick):
            if not irc.isNick(nick[:-1]):
                return False
            else:
                return nick[:-1]
        return nick

    def _deleteExpired(self):
        expiry = self.registryValue('messageExpiry')
        curtime = time.time()
        nickremovals=[]
        for (nick, notes) in self._notes.items():
            removals = []
            for (notetime, whence, text) in notes:
                td = datetime.timedelta(seconds=(curtime - notetime))
                if td.days > expiry:
                    removals.append((notetime, whence, text))
            for note in removals:
                notes.remove(note)
            if len(notes) == 0:
                nickremovals.append(nick)
        for nick in nickremovals:
            del self._notes[nick]
        self._flushNotes()

    ## Note: we call _deleteExpired from 'tell'. This means that it's possible
    ## for expired notes to remain in the database for longer than the maximum,
    ## if no tell's are called.
    ## However, the whole point of this is to avoid crud accumulation in the
    ## database, so it's fine that we only delete expired notes when we try
    ## adding new ones.

    @internationalizeDocstring
    def tell(self, irc, msg, args, nicks, text):
        """<nick1[,nick2[,...]]> <text>

        Tells each <nickX> <text> the next time <nickX> is seen.  <nickX> can
        contain wildcard characters, and the first matching nick will be
        given the note.
        """
        self._deleteExpired()
        validnicks = []
        for nick in nicks:
            if ircutils.strEqual(nick, irc.nick):
                irc.error(_('I can\'t send notes to myself.'))
                return
            validnick = self._validateNick(irc, nick)
            if validnick is False:
                irc.error(_('%s is an invalid IRC nick. Please check your '
                    'input.' % nick))
                return
            validnicks.append(validnick)
        full_queues = []
        for validnick in validnicks:
            try:
                self._addNote(validnick, msg.nick, text)
            except QueueIsFull:
                full_queues.append(validnick)
        if full_queues:
            irc.error(format(
                _('These recipients\' message queue are already full: %L'),
                full_queues))
        else:
            irc.replySuccess()
    tell = wrap(tell, [commalist('somethingWithoutSpaces'), 'text'])

    @internationalizeDocstring
    def notes(self, irc, msg, args, nick):
        """[<nick>]

        If <nick> is given, replies with what notes are waiting on <nick>,
        otherwise, replies with the nicks that have notes waiting for them.
        """
        if nick:
            if nick in self._notes:
                notes = [self._formatNote(when, whence, note)
                         for (when, whence, note) in self._notes[nick]]
                irc.reply(format('%L', notes))
            else:
                irc.error(_('I have no notes for that nick.'))
        else:
            nicks = self._notes.keys()
            if nicks:
                utils.sortBy(ircutils.toLower, nicks)
                irc.reply(format(_('I currently have notes waiting for %L.'),
                                 nicks))
            else:
                irc.error(_('I have no notes waiting to be delivered.'))
    notes = wrap(notes, [additional('something')])

    @internationalizeDocstring
    def remove(self, irc, msg, args, nick):
        """<nick>

        Removes the notes waiting on <nick>.
        """
        try:
            del self._notes[nick]
            self._flushNotes()
            irc.replySuccess()
        except KeyError:
            irc.error(_('There were no notes for %r') % nick)
    remove = wrap(remove, [('checkCapability', 'admin'), 'something'])

    @internationalizeDocstring
    def undo(self, irc, msg, args, nick):
        """<nick>

        Removes the latest note you sent to <nick>.
        """
        if nick not in self._notes:
            irc.error(_('There are no note waiting for %s.') % nick)
            return
        self._notes[nick].reverse()
        for note in self._notes[nick]:
            if note[1] == msg.nick:
                self._notes[nick].remove(note)
                if len(self._notes[nick]) == 0:
                    del self._notes[nick]
                self._flushNotes()
                irc.replySuccess()
                return
        irc.error(_('There are no note from you waiting for %s.') % nick)
    undo = wrap(undo, ['something'])

    def doPrivmsg(self, irc, msg):
        if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
            return
        notes = self._notes.pop(msg.nick, [])
        # Let's try wildcards.
        removals = []
        for wildcard in self.wildcards:
            if ircutils.hostmaskPatternEqual(wildcard, msg.nick):
                removals.append(wildcard)
                notes.extend(self._notes.pop(wildcard))
            for removal in removals:
                self.wildcards.remove(removal)
        if notes:
            old_repliedto = msg.repliedTo
            irc = callbacks.SimpleProxy(irc, msg)
            private = self.registryValue('private')
            for (when, whence, note) in notes:
                s = self._formatNote(when, whence, note)
                irc.reply(s, private=private, prefixNick=not private)
            self._flushNotes()
            msg.tag('repliedTo', old_repliedto)

    def _formatNote(self, when, whence, note):
        return _('Sent %s: <%s> %s') % (self._timestamp(when), whence, note)

    def doJoin(self, irc, msg):
        if self.registryValue('tellOnJoin'):
            self.doPrivmsg(irc, msg)
Later = internationalizeDocstring(Later)

Class = Later

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
