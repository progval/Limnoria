###
# Copyright (c) 2004, Brett Kelly
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
A complete messaging system that allows users to leave 'notes' for other
users that can be retrieved later.
"""

__revision__ = "$Id$"

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
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

conf.registerPlugin('Note')
conf.registerGroup(conf.supybot.plugins.Note, 'notify')
conf.registerGlobalValue(conf.supybot.plugins.Note.notify, 'onJoin',
    registry.Boolean(False, """Determines whether the bot will notify people of
    their new messages when they join the channel.  Normally it will notify
    them when they send a message to the channel, since oftentimes joins are
    the result of netsplits and not the actual presence of the user."""))
conf.registerGlobalValue(conf.supybot.plugins.Note.notify.onJoin, 'repeatedly',
    registry.Boolean(False, """Determines whether the bot will repeatedly
    notify people of their new messages when they join the channel.  That means
    when they join the channel, the bot will tell them they have unread
    messages, even if it's told them before."""))
conf.registerGlobalValue(conf.supybot.plugins.Note.notify, 'autoSend',
    registry.NonNegativeInteger(0, """Determines the upper limit for
    automatically sending messages instead of notifications.  I.e., if this
    value is 2 and there are 2 new messages to notify a user about, instead of
    sending a notification message, the bot will simply send those new messages.
    If there are 3 new messages, however, the bot will send a notification
    message."""))

class Ignores(registry.SpaceSeparatedListOfStrings):
    List = ircutils.IrcSet

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
##         def p(note):
##             return not note.notified and note.to == to
##         return [note.id for note in self.select(p)]
        return self.unNotified.get(to, [])

    def getUnreadIds(self, to):
##         def p(note):
##             return not note.read and note.to == to
##         return [note.id for note in self.select(p)]
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


class Note(callbacks.Privmsg):
    def __init__(self):
        self.__parent= super(Note, self)
        self.__parent.__init__()
        self.db = NoteDB()

    def die(self):
        self.__parent.die()
        self.db.close()

    def doPrivmsg(self, irc, msg):
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
                s = '#%s: %s' % (id, self._formatNote(self.db.get(id), to))
                irc.reply(s, private=True)
                self.db.setRead(id)
            return
        unnotifiedIds = ['#%s' % nid for nid in ids]
        unnotified = len(unnotifiedIds)
        if unnotified or repeatedly:
            unreadIds = ['#%s' % nid for nid in self.db.getUnreadIds(to)]
            unread = len(unreadIds)
            s = 'You have %s; %s that I haven\'t told you about before now.  '\
                '%s %s still unread.' % \
                (utils.nItems('note', unread, 'unread'), unnotified,
                 utils.commaAndify(unreadIds), utils.be(unread))
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
        public = ircutils.isChannel(msg.args[0])
        sent = []
        for target in targets:
            id = self.db.send(user.id, target.id, public, text)
            s = 'note #%s sent to %s' % (id, target.name)
            sent.append(s)
        irc.reply(utils.commaAndify(sent).capitalize() + '.')
    send = wrap(send, ['user', commalist('otherUser'), 'text'])

    def reply(self, irc, msg, args, user, id, text):
        """<id> <text>

        Sends a note in reply to <id>.
        """
        try:
            note = self.db.get(id)
        except KeyError:
            irc.error('That\'s not a note in my database.', Raise=True)
        if note.to != user.id:
            irc.error('You may only reply to notes '
                      'that have been sent to you.', Raise=True)
        self.db.setRead(id)
        text += ' (in reply to #%s)' % id
        public = ircutils.isChannel(msg.args[0])
        try:
            target = ircdb.users.getUser(note.frm)
        except KeyError:
            irc.error('The user who sent you that note '
                      'is no longer in my user database.', Raise=True)
        id = self.db.send(user.id, note.frm, public, text)
        irc.reply('Note #%s sent to %s.' % (id, target.name))
    reply = wrap(reply, ['user', ('id', 'note'), 'text'])

    def unsend(self, irc, msg, args, user, id):
        """<id>

        Unsends the note with the id given.  You must be the
        author of the note, and it must be unread.
        """
        note = self.db.get(id)
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
            author = ircdb.users.getUser(note.frm).name
            return '%s (Sent by %s %s ago)' % (note.text, author, elapsed)
        else:
            assert note.frm == to, 'Odd, userid isn\'t frm either.'
            recipient = ircdb.users.getUser(note.to).name
            return '%s (Sent to %s %s ago)' % (note.text, recipient, elapsed)

    def note(self, irc, msg, args, user, id):
        """<id>

        Retrieves a single note by its unique note id.  Use the 'note list'
        command to see what unread notes you have.
        """
        try:
            note = self.db.get(id)
        except KeyError:
            irc.error('That\'s not a valid note id.')
            return
        if user.id != note.frm and user.id != note.to:
            s = 'You may only retrieve notes you\'ve sent or received.'
            irc.error(s)
            return
        newnote = self._formatNote(note, user.id)
        irc.reply(newnote, private=(not note.public))
        self.db.setRead(id)
    note = wrap(note, ['user', ('id', 'note')])

    def _formatNoteId(self, msg, note, sent=False):
        if note.public or not ircutils.isChannel(msg.args[0]):
            sender = ircdb.users.getUser(note.frm).name
            if sent:
                return '#%s to %s' % (note.id, sender)
            else:
                return '#%s from %s' % (note.id, sender)
        else:
            return '#%s (private)' % note.id

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
            ids = [self._formatNoteId(msg, note) for note in notes]
            ids = self._condense(ids)
            irc.reply(utils.commaAndify(ids))
    list = wrap(list, ['user', getopts({'old': '', 'sent': '',
                                        'from': 'otherUser',
                                        'to': 'otherUser'})])

    def _condense(self, notes):
        temp = {}
        for note in notes:
            note = note.split(' ', 1)
            if note[1] in temp:
                temp[note[1]].append(note[0])
            else:
                temp[note[1]] = [note[0]]
        notes = []
        for (k,v) in temp.iteritems():
            notes.append('%s %s' % (utils.commaAndify(v), k))
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
            try:
                receiver = ircdb.users.getUserId(receiver)
            except KeyError:
                irc.error('That user is not in my user database.')
                return
            originalP = p
            def p(note):
                return originalP(note) and note.to == receiver
        notes = list(self.db.select(p))
        if not notes:
            irc.error('I couldn\'t find any sent notes for your user.')
        else:
            utils.sortBy(operator.attrgetter('id'), notes)
            notes.reverse() # Most recently sent first.
            ids = [self._formatNoteId(msg, note, sent=True) for note in notes]
            ids = self._condense(ids)
            irc.reply(utils.commaAndify(ids))

    def _oldnotes(self, irc, msg, sender):
        try:
            user = ircdb.users.getUser(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        def p(note):
            return note.to == user.id and note.read
        if sender:
            try:
                sender = ircdb.users.getUser(sender)
            except KeyError:
                irc.error('That user is not in my user database.')
                return
            originalP = p
            def p(note):
                return originalP(note) and note.frm == sender.id
        notes = list(self.db.select(p))
        if not notes:
            irc.reply('I couldn\'t find any matching read notes for your user.')
        else:
            utils.sortBy(operator.attrgetter('id'), notes)
            notes.reverse()
            ids = [self._formatNoteId(msg, note) for note in notes]
            ids = self._condense(ids)
            irc.reply(utils.commaAndify(ids))


Class = Note

# vim: shiftwidth=4 tabstop=8 expandtab textwidth=78:
