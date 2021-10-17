###
# Copyright (c) 2004, Brett Kelly
# Copyright (c) 2010, James McCoy
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

import re
import time
import operator

import supybot.dbi as dbi
import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import commands
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Note')

class NoteRecord(dbi.Record):
    __fields__ = [
        'frm',
        'to',
        'at',
        'notified',
        'read',
        'public',
        'text',
        ]

class DbiNoteDB(dbi.DB):
    Mapping = 'flat'
    Record = NoteRecord

    def __init__(self, *args, **kwargs):
        dbi.DB.__init__(self, *args, **kwargs)
        self.unRead = {}
        self.unNotified = {}
        for record in self:
            self._addCache(record)

    def _addCache(self, record):
        if not record.read:
            self.unRead.setdefault(record.to, []).append(record.id)
        if not record.notified:
            self.unNotified.setdefault(record.to, []).append(record.id)

    def _removeCache(self, record):
        if record.notified:
            try:
                self.unNotified[record.to].remove(record.id)
            except (KeyError, ValueError):
                pass
        if record.read:
            try:
                self.unRead[record.to].remove(record.id)
            except (KeyError, ValueError):
                pass

    def setRead(self, id):
        n = self.get(id)
        n.read = True
        n.notified = True
        self._removeCache(n)
        self.set(id, n)

    def setNotified(self, id):
        n = self.get(id)
        n.notified = True
        self._removeCache(n)
        self.set(id, n)

    def getUnnotifiedIds(self, to):
        return self.unNotified.get(to, [])

    def getUnreadIds(self, to):
        return self.unRead.get(to, [])

    def send(self, frm, to, public, text):
        n = self.Record(frm=frm, to=to, text=text,
                        at=time.time(), public=public)
        id = self.add(n)
        self._addCache(n)
        return id

    def unsend(self, id):
        self.remove(id)
        for cache in self.unRead, self.unNotified:
            for (to, ids) in cache.items():
                while id in ids:
                    ids.remove(id)

NoteDB = plugins.DB('Note', {'flat': DbiNoteDB})

class Note(callbacks.Plugin):
    """Allows you to send notes to other users."""
    def __init__(self, irc):
        self.__parent= super(Note, self)
        self.__parent.__init__(irc)
        self.db = NoteDB()

    def die(self):
        self.__parent.die()
        self.db.close()

    def doPrivmsg(self, irc, msg):
        if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
            return
        self._notify(irc, msg)

    def doJoin(self, irc, msg):
        if self.registryValue('notify.onJoin'):
            repeatedly = self.registryValue('notify.onJoin.repeatedly')
            self._notify(irc, msg, repeatedly)

    def _notify(self, irc, msg, repeatedly=False):
        irc = callbacks.SimpleProxy(irc, msg)
        try:
            to = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            return
        ids = self.db.getUnnotifiedIds(to)
        if len(ids) <= self.registryValue('notify.autoSend'):
            for id in ids:
                irc.reply(self._formatNote(self.db.get(id), to), private=True)
                self.db.setRead(id)
            return
        unnotifiedIds = ['#%s' % nid for nid in ids]
        unnotified = len(unnotifiedIds)
        if unnotified or repeatedly:
            unreadIds = ['#%s' % nid for nid in self.db.getUnreadIds(to)]
            unread = len(unreadIds)
            s = format('You have %n; %i that I haven\'t told you about '
                       'before now.  %L %b still unread.',
                       (unread, 'unread', 'note'), unnotified,
                       unreadIds, unread)
            # Later we'll have a user value for allowing this to be a NOTICE.
            irc.reply(s, private=True)
            for nid in unnotifiedIds:
                id = int(nid[1:])
                self.db.setNotified(id)

    def _getUserId(self, irc, name):
        if ircdb.users.hasUser(name):
            return ircdb.users.getUserId(name)
        else:
            try:
                hostmask = irc.state.nickToHostmask(name)
                return ircdb.users.getUserId(hostmask)
            except KeyError:
                return None

    def send(self, irc, msg, args, user, targets, text):
        """<recipient>,[<recipient>,[...]] <text>

        Sends a new note to the user specified.  Multiple recipients may be
        specified by separating their names by commas.
        """
        # Let's get the from user.
        public = bool(msg.channel)
        sent = []
        for target in targets:
            id = self.db.send(user.id, target.id, public, text)
            s = format('note #%i sent to %s', id, target.name)
            sent.append(s)
        irc.reply(format('%L.', sent).capitalize())
    send = wrap(send, ['user', commalist('otherUser'), 'text'])

    def reply(self, irc, msg, args, user, id, text):
        """<id> <text>

        Sends a note in reply to <id>.
        """
        try:
            note = self.db.get(id)
        except dbi.NoRecordError:
            irc.error('That\'s not a note in my database.', Raise=True)
        if note.to != user.id:
            irc.error('You may only reply to notes '
                      'that have been sent to you.', Raise=True)
        self.db.setRead(id)
        text += ' (in reply to #%s)' % id
        public = bool(msg.channel)
        try:
            target = ircdb.users.getUser(note.frm)
        except KeyError:
            irc.error('The user who sent you that note '
                      'is no longer in my user database.', Raise=True)
        id = self.db.send(user.id, note.frm, public, text)
        irc.reply(format('Note #%i sent to %s.', id, target.name))
    reply = wrap(reply, ['user', ('id', 'note'), 'text'])

    def unsend(self, irc, msg, args, user, id):
        """<id>

        Unsends the note with the id given.  You must be the
        author of the note, and it must be unread.
        """
        try:
            note = self.db.get(id)
        except dbi.NoRecordError:
            irc.errorInvalid('note id')
        if note.frm == user.id:
            if not note.read:
                self.db.unsend(id)
                irc.replySuccess()
            else:
                irc.error('That note has been read already.')
        else:
            irc.error('That note wasn\'t sent by you.')
    unsend = wrap(unsend, ['user', ('id', 'note')])

    def _formatNote(self, note, to):
        elapsed = utils.timeElapsed(time.time() - note.at)
        if note.to == to:
            author = plugins.getUserName(note.frm)
            return format('#%i: %s (Sent by %s %s ago)',
                          note.id, note.text, author, elapsed)
        else:
            assert note.frm == to, 'Odd, userid isn\'t frm either.'
            recipient = plugins.getUserName(note.to)
            return format('#%i: %s (Sent to %s %s ago)',
                          note.id, note.text, recipient, elapsed)

    def note(self, irc, msg, args, user, id):
        """<id>

        Retrieves a single note by its unique note id.  Use the 'note list'
        command to see what unread notes you have.
        """
        try:
            note = self.db.get(id)
        except dbi.NoRecordError:
            irc.errorInvalid('note id')
        if user.id != note.frm and user.id != note.to:
            s = 'You may only retrieve notes you\'ve sent or received.'
            irc.error(s)
            return
        newnote = self._formatNote(note, user.id)
        irc.reply(newnote, private=(not note.public))
        self.db.setRead(id)
    note = wrap(note, ['user', ('id', 'note')])

    def _formatNoteId(self, irc, msg, note, sent=False):
        if note.public or not msg.channel:
            if sent:
                sender = plugins.getUserName(note.to)
                return format('#%i to %s', note.id, sender)
            else:
                sender = plugins.getUserName(note.frm)
                return format('#%i from %s', note.id, sender)
        else:
            return format('#%i (private)', note.id)

    def search(self, irc, msg, args, user, optlist, glob):
        """[--{regexp} <value>] [--sent] [<glob>]

        Searches your received notes for ones matching <glob>.  If --regexp is
        given, its associated value is taken as a regexp and matched against
        the notes.  If --sent is specified, only search sent notes.
        """
        criteria = []
        def to(note):
            return note.to == user.id
        def frm(note):
            return note.frm == user.id
        own = to
        for (option, arg) in optlist:
            if option == 'regexp':
                criteria.append(lambda s:
                                regexp_wrapper(s, reobj=arg, timeout=0.1,
                                               plugin_name=self.name(),
                                               fcn_name='search'))
            elif option == 'sent':
                own = frm
        if glob:
            glob = utils.python.glob2re(glob)
            criteria.append(re.compile(glob).search)
        def match(note):
            for p in criteria:
                if not p(note.text):
                    return False
            return True
        notes = list(self.db.select(lambda n: match(n) and own(n)))
        if not notes:
            irc.reply('No matching notes were found.')
        else:
            utils.sortBy(operator.attrgetter('id'), notes)
            ids = [self._formatNoteId(irc, msg, note) for note in notes]
            ids = self._condense(ids)
            irc.reply(format('%L', ids))
    search = wrap(search,
                  ['user', getopts({'regexp': ('regexpMatcher', True),
                                    'sent': ''}),
                   additional('glob')])

    def list(self, irc, msg, args, user, optlist):
        """[--{old,sent}] [--{from,to} <user>]

        Retrieves the ids of all your unread notes.  If --old is given, list
        read notes.  If --sent is given, list notes that you have sent.  If
        --from is specified, only lists notes sent to you from <user>.  If
        --to is specified, only lists notes sent by you to <user>.
        """
        (sender, receiver, old, sent) = (None, None, False, False)
        for (option, arg) in optlist:
            if option == 'old':
                old = True
            if option == 'sent':
                sent = True
            if option == 'from':
                sender = arg
            if option == 'to':
                receiver = arg
                sent = True
        if old:
            return self._oldnotes(irc, msg, sender)
        if sent:
            return self._sentnotes(irc, msg, receiver)
        def p(note):
            return not note.read and note.to == user.id
        if sender:
            originalP = p
            def p(note):
                return originalP(note) and note.frm == sender.id
        notes = list(self.db.select(p))
        if not notes:
            irc.reply('You have no unread notes.')
        else:
            utils.sortBy(operator.attrgetter('id'), notes)
            ids = [self._formatNoteId(irc, msg, note) for note in notes]
            ids = self._condense(ids)
            irc.reply(format('%L.', ids))
    list = wrap(list, ['user', getopts({'old': '', 'sent': '',
                                        'from': 'otherUser',
                                        'to': 'otherUser'})])

    def next(self, irc, msg, args, user):
        """takes no arguments

        Retrieves your next unread note, if any.
        """
        notes = self.db.getUnreadIds(user.id)
        if not notes:
            irc.reply('You have no unread notes.')
        else:
            found = False
            for id in notes:
                try:
                    note = self.db.get(id)
                except KeyError:
                    continue
                found = True
                break
            if not found:
                irc.reply('You have no unread notes.')
            else:
                irc.reply(self._formatNote(note, user.id), private=(not note.public))
                self.db.setRead(note.id)
    next = wrap(next, ['user'])

    def _condense(self, notes):
        temp = {}
        for note in notes:
            note = note.split(' ', 1)
            if note[1] in temp:
                temp[note[1]].append(note[0])
            else:
                temp[note[1]] = [note[0]]
        notes = []
        for (k,v) in temp.items():
            if '(private)' in k:
                k = k.replace('(private)', format('%b private', len(v)))
            notes.append(format('%L %s', v, k))
        return notes

    def _sentnotes(self, irc, msg, receiver):
        try:
            user = ircdb.users.getUser(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        def p(note):
            return note.frm == user.id
        if receiver:
            originalP = p
            def p(note):
                return originalP(note) and note.to == receiver.id
        notes = list(self.db.select(p))
        if not notes:
            irc.error('I couldn\'t find any sent notes for your user.')
        else:
            utils.sortBy(operator.attrgetter('id'), notes)
            notes.reverse() # Most recently sent first.
            ids = [self._formatNoteId(irc, msg, note, sent=True) for note in notes]
            ids = self._condense(ids)
            irc.reply(format('%L.', ids))

    def _oldnotes(self, irc, msg, sender):
        try:
            user = ircdb.users.getUser(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        def p(note):
            return note.to == user.id and note.read
        if sender:
            originalP = p
            def p(note):
                return originalP(note) and note.frm == sender.id
        notes = list(self.db.select(p))
        if not notes:
            irc.reply('I couldn\'t find any matching read notes '
                      'for your user.')
        else:
            utils.sortBy(operator.attrgetter('id'), notes)
            notes.reverse()
            ids = [self._formatNoteId(irc, msg, note) for note in notes]
            ids = self._condense(ids)
            irc.reply(format('%L.', ids))


Class = Note

# vim: shiftwidth=4 softtabstop=4 expandtab textwidth=79:
