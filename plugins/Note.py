#!/usr/bin/env python

###
# Copyright (c) 2003, Brett Kelly
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

import supybot.plugins as plugins

import csv
import sets
import time
import getopt
import os.path
from itertools import imap

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

conf.registerPlugin('Note')
conf.registerGlobalValue(conf.supybot.plugins.Note, 'notifyOnJoin',
    registry.Boolean(False, """Determines whether the bot will notify people of
    their new messages when they join the channel.  Normally it will notify
    them when they send a message to the channel, since oftentimes joins are
    the result of netsplits and not the actual presence of the user."""))
conf.registerGlobalValue(conf.supybot.plugins.Note, 'notifyOnJoinRepeatedly',
    registry.Boolean(False, """Determines whether the bot will repeatedly
    notify people of their new messages when they join the channel.  That means
    when they join the channel, the bot will tell them they have unread
    messages, even if it's told them before."""))
conf.registerUserValue(conf.users.plugins.Note, 'notifyWithNotice',
    registry.Boolean(False, """Determines whether the bot will notify users of
    new messages with a NOTICE, rather than a PRIVMSG, so their clients won't
    open a new query window."""))

class Ignores(registry.SpaceSeparatedListOfStrings):
    List = ircutils.IrcSet

conf.registerUserValue(conf.users.plugins.Note, 'ignores', Ignores([], ''))

class FlatfileNoteDB(plugins.FlatfileDB):
    class Note(object):
        def __init__(self, L=None, to=None, frm=None, text=None):
            if L is not None:
                self.frm = int(L[0])
                self.to = int(L[1])
                self.at = float(L[2])
                self.notified = bool(int(L[3]))
                self.read = bool(int(L[4]))
                self.public = bool(int(L[5]))
                self.text = L[6]
            else:
                self.to = to
                self.frm = frm
                self.text = text
                self.read = False
                self.public = True
                self.at = time.time()
                self.notified = False

        def __str__(self):
            return csv.join(map(str, [self.frm, self.to, self.at,
                                      int(self.notified), int(self.read),
                                      int(self.public), self.text]))

    def serialize(self, n):
        return str(n)

    def deserialize(self, s):
        return self.Note(csv.split(s))

    def setRead(self, id):
        n = self.getRecord(id)
        n.read = True
        n.notified = True
        self.setRecord(id, n)

    def setNotified(self, id):
        n = self.getRecord(id)
        n.notified = True
        self.setRecord(id, n)

    def getUnnotifiedIds(self, to):
        L = []
        for (id, note) in self.records():
            if note.to == to and not note.notified:
                L.append(id)
        return L

    def getUnreadIds(self, to):
        L = []
        for (id, note) in self.records():
            if note.to == to and not note.read:
                L.append(id)
        return L

    def send(self, frm, to, text):
        n = self.Note(frm=frm, to=to, text=text)
        return self.addRecord(n)

    def get(self, id):
        return self.getRecord(id)

    def remove(self, id):
        n = self.getRecord(id)
        assert not n.read
        self.delRecord(id)

    def notes(self, p):
        L = []
        for (id, note) in self.records():
            if p(note):
                L.append((id, note))
        return L
        
    
def NoteDB():
    return FlatfileNoteDB(conf.supybot.directories.data.dirize('Note.db'))


class Note(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = NoteDB()

    def die(self):
        self.db.close()

    def doPrivmsg(self, irc, msg):
        self._notify(irc, msg)

    def doJoin(self, irc, msg):
        if self.registryValue('notifyOnJoin'):
            repeatedly = self.registryValue('notifyOnJoinRepeatedly')
            self._notify(irc, msg, repeatedly)

    def _notify(self, irc, msg, repeatedly=False):
        try:
            to = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            return
        unnotifiedIds = ['#%s' % nid for nid in self.db.getUnnotifiedIds(to)]
        unnotified = len(unnotifiedIds)
        if unnotified or repeatedly:
            unreadIds = ['#%s' % nid for nid in self.db.getUnreadIds(to)]
            unread = len(unreadIds)
            s = 'You have %s; %s that I haven\'t told you about before now.  '\
                '%s %s still unread.' % \
                (utils.nItems('note', unread, 'unread'), unnotified,
                 utils.commaAndify(unreadIds), utils.be(unread))
            msgmaker = ircmsgs.privmsg
            if self.userValue('notifyWithNotice', msg.prefix):
                msgmaker = ircmsgs.notice
            irc.queueMsg(msgmaker(msg.nick, s))
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

    def _validId(self, irc, id):
        try:
            id = id.lstrip('#')
            return int(id)
        except ValueError:
            irc.error('That\'s not a valid note id.')
            return None

    def send(self, irc, msg, args):
        """<recipient>,[<recipient>,[...]] <text>

        Sends a new note to the user specified.  Multiple recipients may be
        specified by separating their names by commas, with *no* spaces
        between.
        """
        (names, text) = privmsgs.getArgs(args, required=2)
        # Let's get the from user.
        try:
            fromId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        public = ircutils.isChannel(msg.args[0])
        names = names.split(',')
        ids = [self._getUserId(irc, name) for name in names]
        badnames = []
        # Make sure all targets are registered.
        if None in ids:
            for (id, name) in zip(ids, names):
                if id is None:
                    badnames.append(name)
            irc.errorNoUser(name=utils.commaAndify(badnames, And='or'))
            return

        # Make sure the sender isn't being ignored.
        senderName = ircdb.users.getUser(fromId).name
        for name in names:
            if senderName in self.userValue('ignores', name):
                badnames.append(name)
        if badnames:
            irc.error('%s %s ignoring notes from you.' % \
                      (utils.commaAndify(badnames), utils.be(len(badnames))))
            return
        sent = []
        for toId in ids:
            id = self.db.send(fromId, toId, text)
            name = ircdb.users.getUser(toId).name
            s = 'note #%s sent to %s' % (id, name)
            sent.append(s)
        irc.reply(utils.commaAndify(sent).capitalize() + '.')

    def unsend(self, irc, msg, args):
        """<id>

        Unsends the note with the id given.  You must be the
        author of the note, and it must be unread.
        """
        try:
            userid = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        id = privmsgs.getArgs(args)
        id = self._validId(irc, id)
        if id is None:
            return
        note = self.db.get(id)
        if note.frm == userid:
            if not note.read:
                self.db.remove(id)
                irc.replySuccess()
            else:
                irc.error('That note has been read already.')
        else:
            irc.error('That note wasn\'t sent by you.')

    def note(self, irc, msg, args):
        """<note id>

        Retrieves a single note by its unique note id.  Use the 'note list'
        command to see what unread notes you have.
        """
        try:
            userid = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        id = privmsgs.getArgs(args)
        id = self._validId(irc, id)
        if id is None:
            return
        try:
            note = self.db.get(id)
        except KeyError:
            irc.error('That\'s not a valid note id.')
            return
        if userid != note.frm and userid != note.to:
            s = 'You may only retrieve notes you\'ve sent or received.'
            irc.error(s)
            return
        elapsed = utils.timeElapsed(time.time() - note.at)
        if note.to == userid:
            author = ircdb.users.getUser(note.frm).name
            newnote = '%s (Sent by %s %s ago)' % (note.text, author, elapsed)
        elif note.frm == userid:
            recipient = ircdb.users.getUser(note.to).name
            newnote = '%s (Sent to %s %s ago)' % (note.text, recipient,elapsed)
        irc.reply(newnote, private=(not note.public))
        self.db.setRead(id)

    def ignore(self, irc, msg, args):
        """[--remove] <user>

        Ignores all messages from <user>.  If --remove is listed, remove <user>
        from the list of users being ignored.
        """
        remove = False
        while '--remove' in args:
            remove = True
            args.remove('--remove')
        user = privmsgs.getArgs(args)
        try:
            L = self.userValue('ignores', msg.prefix)
            if remove:
                try:
                    L.remove(user)
                except (KeyError, ValueError):
                    irc.error('%r was not in your list of ignores.' % user)
                    return
            else:
                L.add(user)
            self.setUserValue('ignores', msg.prefix, L)
            irc.replySuccess()
        except KeyError:
            irc.errorNoUser()

    def _formatNoteId(self, msg, id, frm, public, sent=False):
        if public or not ircutils.isChannel(msg.args[0]):
            sender = ircdb.users.getUser(frm).name
            if sent:
                return '#%s to %s' % (id, sender)
            else:
                return '#%s from %s' % (id, sender)
        else:
            return '#%s (private)' % id

    def list(self, irc, msg, args):
        """[--{old,sent}] [--{from,to} <user>]

        Retrieves the ids of all your unread notes.  If --old is given, list
        read notes.  If --sent is given, list notes that you have sent.  If
        --from is specified, only lists notes sent to you from <user>.  If
        --to is specified, only lists notes sent by you to <user>.
        """
        options = ['old', 'sent', 'from=', 'to=']
        (optlist, rest) = getopt.getopt(args, '', options)
        sender, receiver, old, sent = ('', '', False, False)
        for (option, arg) in optlist:
            if option == '--old':
                old = True
            if option == '--sent':
                sent = True
            if option == '--from':
                sender = arg
            if option == '--to':
                receiver = arg
                sent = True
        if old:
            return self._oldnotes(irc, msg, sender)
        if sent:
            return self._sentnotes(irc, msg, receiver)
        try:
            userid = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        
        def p(note):
            return not note.read and note.to == userid
        if sender:
            try:
                sender = ircdb.users.getUserId(sender)
                originalP = p
                def p(note):
                    return originalP(note) and note.frm == sender
            except KeyError:
                irc.errorNoUser()
                return
        notesAndIds = self.db.notes(p)
        notesAndIds.sort()
        if not notesAndIds:
            irc.reply('You have no unread notes.')
        else:
            L = [self._formatNoteId(msg, id, n.frm, n.public)
                 for (id, n) in notesAndIds]
            L = self._condense(L)
            irc.reply(utils.commaAndify(L))

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
            userid = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        def p(note):
            return note.frm == userid
        if receiver:
            try:
                receiver = ircdb.users.getUserId(receiver)
            except KeyError:
                irc.error('That user is not in my user database.')
                return
            originalP = p
            def p(note):
                return originalP(note) and note.to == receiver
        notesAndIds = self.db.notes(p)
        notesAndIds.sort()
        if not notesAndIds:
            irc.error('I couldn\'t find any sent notes for your user.')
        else:
            ids = [self._formatNoteId(msg, id, note.to, note.public,sent=True)
                   for (id, note) in notesAndIds]
            ids = self._condense(ids)
            irc.reply(utils.commaAndify(ids))

    def _oldnotes(self, irc, msg, sender):
        try:
            userid = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        def p(note):
            return note.to == userid and note.read
        if sender:
            try:
                sender = ircdb.users.getUserId(sender)
            except KeyError:
                irc.error('That user is not in my user database.')
                return
            originalP = p
            def p(note):
                return originalP(note) and note.frm == sender
        notesAndIds = self.db.notes(p)
        notesAndIds.sort()
        if not notesAndIds:
            irc.reply('I couldn\'t find any matching read notes for your user.')
        else:
            ids = [self._formatNoteId(msg, id, note.frm, note.public)
                   for (id, note) in notesAndIds]
            ids = self._condense(ids)
            irc.reply(utils.commaAndify(ids))


Class = Note

# vim: shiftwidth=4 tabstop=8 expandtab textwidth=78:
