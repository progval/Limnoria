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

import supybot

#deprecated = True

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import os
import re
import time
import random
import cPickle as pickle

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


conf.registerPlugin('Infobot')
conf.registerChannelValue(conf.supybot.plugins.Infobot, 'personality',
    registry.Boolean(True, """Determines whether the bot will respond with
    personable (Infobot-like) responses rather than its standard messages."""))
conf.registerChannelValue(conf.supybot.plugins.Infobot, 'boringDunno',
    registry.String('Dunno.', """Determines what boring dunno should be given
    if supybot.plugins.Infobot.personality is False."""))

conf.registerGroup(conf.supybot.plugins.Infobot, 'unaddressed')
conf.registerChannelValue(conf.supybot.plugins.Infobot.unaddressed,
    'snarfDefinitions', registry.Boolean(True, """Determines whether the bot
    will snarf definitions given in the channel that weren't directly
    addressed to it.  Of course, no confirmation will be given if the bot
    isn't directly addressed."""))
conf.registerChannelValue(conf.supybot.plugins.Infobot.unaddressed,
    'answerQuestions', registry.Boolean(True, """Determines whether the bot
    will answer questions that weren't directly addressed to it.  Of course,
    if it doesn't have an answer, it will remain silent."""))
conf.registerChannelValue(conf.supybot.plugins.Infobot.unaddressed,
    'replyExistingFactoid', registry.Boolean(False, """Determines whether the
    bot will announce that a factoid already exists when it sees a definition
    for a pre-existing factoid."""))

def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Infobot', True)

ends = ['!',
        '.',
        ', $who.',]
dunnos = ['Dunno',
          'No idea',
          'I don\'t know',
          'I have no idea',
          'I don\'t have a clue',
          'Bugger all, I dunno',
          'Wish I knew',]
starts = ['It has been said that ',
          'I guess ',
          '',
          'hmm... ',
          'Rumor has it ',
          'Somebody said ',]
confirms = ['10-4',
            'Okay',
            'Got it',
            'Gotcha',
            'I hear ya']
NORESPONSE = '<reply>'
initialIs = {'who': NORESPONSE,
             'what': NORESPONSE,
             'when': NORESPONSE,
             'where': NORESPONSE,
             'why': NORESPONSE,
             'it': NORESPONSE,
             'that': NORESPONSE,
             'this': NORESPONSE,
            }
initialAre = {'who': NORESPONSE,
              'what': NORESPONSE,
              'when': NORESPONSE,
              'where': NORESPONSE,
              'why': NORESPONSE,
              'it': NORESPONSE,
              'they': NORESPONSE,
              'these': NORESPONSE,
              'those': NORESPONSE,
              'roses': 'red',
              'violets': 'blue',
             }

class PickleInfobotDB(object):
    def __init__(self, filename):
        self.filename = filename
        self.dbs = ircutils.IrcDict()
        self.changes = ircutils.IrcDict()
        self.responses = ircutils.IrcDict()

    def _getDb(self, channel):
        filename = plugins.makeChannelFilename(self.filename, channel)
        if filename in self.dbs:
            pass
        elif os.path.exists(filename):
            fd = file(filename)
            try:
                (Is, Are) = pickle.load(fd)
                self.dbs[filename] = (Is, Are)
                self.changes[filename] = 0
                self.responses[filename] = 0
            except cPickle.UnpicklingError, e:
                fd.close()
                raise dbi.InvalidDBError, str(e)
            fd.close()
        else:
            self.dbs[filename] = (utils.InsensitivePreservingDict(),
                                  utils.InsensitivePreservingDict())
            for (k, v) in initialIs.iteritems():
                self.setIs(channel, k, v)
            for (k, v) in initialAre.iteritems():
                self.setAre(channel, k, v)
            self.changes[filename] = 0
            self.responses[filename] = 0
        return (self.dbs[filename], filename)

    def flush(self, db=None, filename=None):
        if db is None and filename is None:
            for (filename, db) in self.dbs.iteritems():
                fd = utils.transactionalFile(filename, 'wb')
                pickle.dump(db, fd)
                fd.close()
        else:
            fd = utils.transactionalFile(filename, 'wb')
            pickle.dump(db, fd)
            fd.close()
            self.dbs[filename] = db

    def close(self):
        self.flush()

    def incChanges(self):
        filename = dynamic.filename
        print '*** self.changes: %s' % self.changes
        self.changes[filename] += 1

    def incResponses(self):
        self.responses[dynamic.filename] += 1

    def changeIs(self, channel, factoid, replacer):
        ((Is, Are), filename) = self._getDb(channel)
        try:
            old = Is[factoid]
        except KeyError:
            raise dbi.NoRecordError
        if replacer is not None:
            Is[factoid] = replacer(old)
            self.flush((Is, Are), filename)
            self.incChanges()

    def getIs(self, channel, factoid):
        ((Is, Are), filename) = self._getDb(channel)
        ret = Is[factoid]
        self.incResponses()
        return ret

    def setIs(self, channel, key, value):
        ((Is, Are), filename) = self._getDb(channel)
        Is[key] = value
        self.flush((Is, Are), filename)
        self.incChanges()

    def delIs(self, channel, factoid):
        ((Is, Are), filename) = self._getDb(channel)
        try:
            Is.pop(factoid)
        except KeyError:
            raise dbi.NoRecordError
        self.flush((Is, Are), filename)
        self.incChanges()

    def hasIs(self, channel, factoid):
        ((Is, Are), _) = self._getDb(channel)
        return factoid in Is

    def changeAre(self, channel, factoid, replacer):
        ((Is, Are), filename) = self._getDb(channel)
        try:
            old = Are[factoid]
        except KeyError:
            raise dbi.NoRecordError
        if replacer is not None:
            Are[factoid] = replacer(old)
            self.flush((Is, Are), filename)
            self.incChanges()

    def getAre(self, channel, factoid):
        ((Is, Are), filename) = self._getDb(channel)
        ret = Are[factoid]
        self.incResponses()
        return ret

    def hasAre(self, channel, factoid):
        ((Is, Are), _) = self._getDb(channel)
        return factoid in Are

    def setAre(self, channel, key, value):
        ((Is, Are), filename) = self._getDb(channel)
        Are[key] = value
        self.flush((Is, Are), filename)
        self.incChanges()

    def delAre(self, channel, factoid):
        ((Is, Are), filename) = self._getDb(channel)
        try:
            Are.pop(factoid)
        except KeyError:
            raise dbi.NoRecordError
        self.flush((Is, Are), filename)
        self.incChanges()

    def getDunno(self):
        return random.choice(dunnos) + random.choice(ends)

    def getConfirm(self):
        return random.choice(confirms) + random.choice(ends)

    def getChangeCount(self, channel):
        (_, filename) = self._getDb(channel)
        return self.changes[filename]

    def getResponseCount(self, channel):
        (_, filename) = self._getDb(channel)
        return self.responses[filename]

    def getNumFacts(self, channel):
        ((Is, Are), _) = self._getDb(channel)
        return len(Are.keys()) + len(Is.keys())

class SqliteInfobotDB(object):
    def __init__(self, filename):
        self.filename = filename
        self.dbs = ircutils.IrcDict()
        self.changes = ircutils.IrcDict()
        self.responses = ircutils.IrcDict()

    def _getDb(self, channel):
        try:
            import sqlite
        except ImportError:
            raise callbacks.Error, 'You need to have PySQLite installed to '\
                                   'use this plugin.  Download it at '\
                                   '<http://pysqlite.sf.net/>'
        try:
            filename = plugins.makeChannelFilename(self.filename, channel)
            if filename not in self.changes:
                self.changes[filename] = 0
            if filename not in self.responses:
                self.responses[filename] = 0
            if filename in self.dbs:
                return (self.dbs[filename], filename)
            if os.path.exists(filename):
                self.dbs[filename] = sqlite.connect(filename)
                return (self.dbs[filename], filename)
            db = sqlite.connect(filename)
            self.dbs[filename] = db
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE isFacts (
                              key TEXT UNIQUE ON CONFLICT REPLACE,
                              value TEXT
                              );""")
            cursor.execute("""CREATE TABLE areFacts (
                              key TEXT UNIQUE ON CONFLICT REPLACE,
                              value TEXT
                              );""")
            db.commit()
            for (k, v) in initialIs.iteritems():
                self.setIs(channel, k, v)
            for (k, v) in initialAre.iteritems():
                self.setAre(channel, k, v)
            self.changes[filename] = 0
            self.responses[filename] = 0
            return (db, filename)
        except sqlite.DatabaseError, e:
            raise dbi.InvalidDBError, str(e)

    def close(self):
        for db in self.dbs.itervalues():
            db.close()
        self.dbs.clear()

    def incChanges(self):
        self.changes[dynamic.filename] += 1

    def incResponses(self):
        self.changes[dynamic.filename] += 1

    def changeIs(self, channel, factoid, replacer):
        (db, filename) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT value FROM isFacts WHERE key=%s""", factoid)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        old = cursor.fetchone()[0]
        if replacer is not None:
            cursor.execute("""UPDATE isFacts SET value=%s WHERE key=%s""",
                           replacer(old), factoid)
            db.commit()
            self.incChanges()

    def getIs(self, channel, factoid):
        (db, filename) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT value FROM isFacts WHERE key=%s""", factoid)
        ret = cursor.fetchone()[0]
        self.incResponses()
        return ret

    def setIs(self, channel, fact, oid):
        (db, filename) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO isFacts VALUES (%s, %s)""", fact, oid)
        db.commit()
        self.incChanges()

    def delIs(self, channel, factoid):
        (db, filename) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""DELETE FROM isFacts WHERE key=%s""", factoid)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        db.commit()
        self.incChanges()

    def hasIs(self, channel, factoid):
        (db, _) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM isFacts WHERE key=%s""", factoid)
        return cursor.rowcount == 1

    def changeAre(self, channel, factoid, replacer):
        (db, filename) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT value FROM areFacts WHERE key=%s""", factoid)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        old = cursor.fetchone()[0]
        if replacer is not None:
            cursor.execute("""UPDATE areFacts SET value=%s WHERE key=%s""",
                           replacer(old), factoid)
            db.commit()
            self.incChanges()

    def getAre(self, channel, factoid):
        (db, filename) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT value FROM areFacts WHERE key=%s""", factoid)
        ret = cursor.fetchone()[0]
        self.incResponses()
        return ret

    def setAre(self, channel, fact, oid):
        (db, filename) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO areFacts VALUES (%s, %s)""", fact, oid)
        db.commit()
        self.incChanges()

    def delAre(self, channel, factoid):
        (db, filename) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""DELETE FROM areFacts WHERE key=%s""", factoid)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        db.commit()
        self.incChanges()

    def hasAre(self, channel, factoid):
        (db, _) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM areFacts WHERE key=%s""", factoid)
        return cursor.rowcount == 1

    def getDunno(self):
        return random.choice(dunnos) + random.choice(ends)

    def getConfirm(self):
        return random.choice(confirms) + random.choice(ends)

    def getChangeCount(self, channel):
        (_, filename) = self._getDb(channel)
        try:
            return self.changes[filename]
        except KeyError:
            return 0

    def getResponseCount(self, channel):
        (_, filename) = self._getDb(channel)
        try:
            return self.responses[filename]
        except KeyError:
            return 0

    def getNumFacts(self, channel):
        (db, _) = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM areFacts""")
        areFacts = int(cursor.fetchone()[0])
        cursor.execute("""SELECT COUNT(*) FROM isFacts""")
        isFacts = int(cursor.fetchone()[0])
        return areFacts + isFacts


InfobotDB = plugins.DB('Infobot',
                       {'sqlite': SqliteInfobotDB,
                        'pickle': PickleInfobotDB})

class Dunno(Exception):
    pass

class Infobot(callbacks.PrivmsgCommandAndRegexp):
    regexps = ['doForce', 'doForget', 'doFactoid', 'doUnknown']
    addressedRegexps = ['doForce', 'doForget', 'doChange', 'doFactoid', 'doUnknown']
    def __init__(self):
        self.__parent = super(Infobot, self)
        self.__parent.__init__()
        self.db = InfobotDB()
        self.irc = None
        self.msg = None
        self.replied = True
        self.changed = False
        self.added = False

    def die(self):
        self.__parent.die()
        self.db.close()

    def reset(self):
        self.db.close()

    def _error(self, s):
        if msg.addressed:
            self.irc.error(s)
        else:
            self.log.warning(s)

    def reply(self, s, irc=None, msg=None, action=False, substitute=True):
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
        if substitute:
            s = ircutils.standardSubstitute(irc, msg, s)
        irc.reply(s, prefixName=False, action=action, msg=msg)

    def confirm(self, irc=None, msg=None):
        if self.registryValue('personality'):
            s = self.db.getConfirm()
        else:
            s = conf.supybot.replies.success()
        self.reply(s, irc=irc, msg=msg)

    def missing(self, fact, irc=None, msg=None):
        if msg is None:
            assert self.msg is not None
            msg = self.msg
        self.reply('I didn\'t have anything matching %s, %s.' %
                   (utils.quoted(fact), msg.nick),
                   irc=irc, msg=msg)

    def dunno(self, irc=None, msg=None):
        if self.registryValue('personality'):
            s = self.db.getDunno()
        else:
            s = self.registryValue('boringDunno')
        self.reply(s, irc=irc, msg=msg)

    def factoid(self, key, irc=None, msg=None, dunno=True, prepend='',
                isAre=None):
        if irc is None:
            assert self.irc is not None
            irc = self.irc
        if msg is None:
            assert self.msg is not None
            msg = self.msg
        if isAre is not None:
            isAre = isAre.lower()
        channel = dynamic.channel
        try:
            if isAre is None:
                if self.db.hasIs(channel, key):
                    isAre = 'is'
                    value = self.db.getIs(channel, key)
                elif self.db.hasAre(channel, key):
                    isAre = 'are'
                    value = self.db.getAre(channel, key)
            elif isAre == 'is':
                if not self.db.hasIs(channel, key):
                    isAre = None
                else:
                    value = self.db.getIs(channel, key)
            elif isAre == 'are':
                if not self.db.hasAre(channel, key):
                    isAre = None
                else:
                    value = self.db.getAre(channel, key)
        except dbi.InvalidDBError, e:
            self._error('Unable to access db: %s' % e)
            return
        if isAre is None:
            if msg.addressed:
                if dunno:
                    self.dunno(irc=irc, msg=msg)
                else:
                    raise Dunno
        else:
            value = random.choice(value.split('|'))
            if value.startswith('<reply>'):
                value = value[7:].strip()
                if value:
                    self.reply(value, irc=irc, msg=msg)
                else:
                    self.log.debug('Not sending empty factoid.')
            elif value.startswith('<action>'):
                self.reply(value[8:].strip(),
                           irc=irc, msg=msg, action=True)
            else:
                s = '%s %s %s, $who' % (key, isAre, value)
                s = prepend + s
                self.reply(s, irc=irc, msg=msg)

    _iAm = (re.compile(r'^i am ', re.I), '%s is ')
    _my = (re.compile(r'^my ', re.I), '%s\'s ')
    _your = (re.compile(r'^your ', re.I), '%s\'s ')
    def normalize(self, s, bot, nick):
        s = ircutils.stripFormatting(s)
        s = s.strip() # After stripFormatting for formatted spaces.
        s = utils.normalizeWhitespace(s)
        s = self._iAm[0].sub(self._iAm[1] % nick, s)
        s = self._my[0].sub(self._my[1] % nick, s)
        s = self._your[0].sub(self._your[1] % bot, s)
        contractions = [('what\'s', 'what is'), ('where\'s', 'where is'),
                        ('who\'s', 'who is'), ('wtf\'s', 'wtf is'),]
        for (contraction, replacement) in contractions:
            if s.startswith(contraction):
                s = replacement + s[len(contraction):]
        return s

    _forceRe = re.compile(r'^no[,: -]+', re.I)
    _karmaRe = re.compile(r'(?:\+\+|--)(?:\s+)?$')
    def doPrivmsg(self, irc, msg):
        try:
            if msg.repliedTo:
                self.replied = True
            if ircmsgs.isCtcp(msg):
                self.log.debug('Returning early from doPrivmsg: isCtcp(msg).')
                return
            if self._karmaRe.search(msg.args[1]):
                self.log.debug('Returning early from doPrivmsg: karma.')
                return
            # For later dynamic scoping
            channel = plugins.getChannel(msg.args[0])
            s = callbacks.addressed(irc.nick, msg)
            payload = self.normalize(s or msg.args[1], irc.nick, msg.nick)
            if s:
                msg.tag('addressed', payload)
            msg = ircmsgs.IrcMsg(args=(msg.args[0], payload), msg=msg)
            self.__parent.doPrivmsg(irc, msg)
        finally:
            self.replied = False
            self.changed = False
            self.added = False

    def callCommand(self, name, irc, msg, *L, **kwargs):
        try:
            self.irc = irc
            self.msg = msg
            self.__parent.callCommand(name, irc, msg, *L, **kwargs)
        finally:
            self.irc = None
            self.msg = None

    def doForget(self, irc, msg, match):
        r"^forget\s+(.+?)[?!. ]*$"
        fact = match.group(1)
        deleted = False
        for method in [self.db.delIs, self.db.delAre]:
            try:
                method(dynamic.channel, fact)
                deleted = True
            except dbi.NoRecordError:
                pass
        if deleted:
            self.confirm()
        elif msg.addressed:
            self.missing(fact, irc=irc, msg=msg)

    def doForce(self, irc, msg, match):
        r"^no,\s+(\w+,\s+)?(.+?)\s+(?<!\\)(was|is|am|were|are)\s+(.+?)[?!. ]*$"
        (nick, key, isAre, value) = match.groups()
        if not msg.addressed:
            if nick is None:
                self.log.debug('Not forcing because we weren\'t addressed and '
                               'payload wasn\'t of the form: no, irc.nick, ..')
                return
            nick = nick.rstrip(' \t,')
            if not ircutils.nickEqual(nick, irc.nick):
                self.log.debug('Not forcing because the regexp nick didn\'t '
                               'match our nick.')
                return
        else:
            if nick is not None:
                stripped = nick.rstrip(' \t,')
                if not ircutils.nickEqual(stripped, irc.nick):
                    key = nick + key
        isAre = isAre.lower()
        if self.added:
            return
        channel = dynamic.channel
        if isAre in ('was', 'is', 'am'):
            if self.db.hasIs(channel, key):
                oldValue = self.db.getIs(channel, key)
                if oldValue.lower() == value.lower():
                    self.reply('I already had it that way, %s.' % msg.nick)
                    return
                self.log.debug('Forcing %s to %s.',
                               utils.quoted(key), utils.quoted(value))
                self.added = True
                self.db.setIs(channel, key, value)
        else:
            if self.db.hasAre(channel, key):
                oldValue = self.db.getAre(channel, key)
                if oldValue.lower() == value.lower():
                    self.reply('I already had it that way, %s.' % msg.nick)
                    return
                self.log.debug('Forcing %s to %s.',
                               utils.quoted(key), utils.quoted(value))
                self.added = True
                self.db.setAre(channel, key, value)
        self.confirm()

    def doChange(self, irc, msg, match):
        r"^(.+)\s+=~\s+(.+)$"
        (fact, regexp) = match.groups()
        changed = False
        try:
            r = utils.perlReToReplacer(regexp)
        except ValueError, e:
            if msg.addressed:
                irc.errorInvalid('regexp', regexp)
            else:
                self.log.debug('Invalid regexp: %s' % regexp)
                return
        if self.changed:
            return
        for method in [self.db.changeIs, self.db.changeAre]:
            try:
                method(dynamic.channel, fact, r)
                self.changed = True
            except dbi.NoRecordError:
                pass
        if changed:
            self.confirm()
        else:
            self.missing(fact, irc=irc, msg=msg)

    def doUnknown(self, irc, msg, match):
        r"^(.+?)\s*(\?[?!. ]*)?$"
        (key, question) = match.groups()
        if not msg.addressed:
            if question is None:
                self.log.debug('Not answering question since we weren\'t '
                               'addressed and there was no question mark.')
                return
            if self.registryValue('unaddressed.answerQuestions'):
                self.factoid(key, prepend=random.choice(starts))
        else:
            self.factoid(key, prepend=random.choice(starts))

    def doFactoid(self, irc, msg, match):
        r"^(.+?)\s+(?<!\\)(was|is|am|were|are)\s+(also\s+)?(.+?)[?!. ]*$"
        (key, isAre, also, value) = match.groups()
        key = key.replace('\\', '')
        if key.lower() in ('where', 'what', 'who', 'wtf'):
            # It's a question.
            if msg.addressed or \
               self.registryValue('unaddressed.answerQuestions'):
                self.factoid(value, isAre=isAre, prepend=random.choice(starts))
            return
        if not msg.addressed and \
           not self.registryValue('unaddressed.snarfDefinitions'):
            return
        isAre = isAre.lower()
        if self.added:
            return
        if isAre in ('was', 'is', 'am'):
            if self.db.hasIs(dynamic.channel, key):
                oldValue = self.db.getIs(dynamic.channel, key)
                if oldValue.lower() == value.lower():
                    self.reply('I already had it that way, %s.' % msg.nick)
                    return
                if also:
                    self.log.debug('Adding %s to %s.',
                                   utils.quoted(key), utils.quoted(value))
                    value = '%s or %s' % (oldValue, value)
                elif msg.addressed:
                    if initialIs.get(key) != value:
                        self.reply('... but %s is %s ...' %
                                   (key, oldValue), substitute=False)
                        return
                else:
                    self.log.debug('Already have a %s key.',
                                   utils.quoted(key))
                    return
            self.added = True
            self.db.setIs(dynamic.channel, key, value)
        else:
            if self.db.hasAre(dynamic.channel, key):
                oldValue = self.db.getAre(dynamic.channel, key)
                if oldValue.lower() == value.lower():
                    self.reply('I already had it that way, %s.' % msg.nick)
                    return
                if also:
                    self.log.debug('Adding %s to %s.',
                                   utils.quoted(key), utils.quoted(value))
                    value = '%s or %s' % (oldValue, value)
                elif msg.addressed:
                    if initialAre.get(key) != value:
                        self.reply('... but %s are %s ...' %
                                   (key, oldValue), substitute=False)
                        return
                else:
                    self.log.debug('Already have a %s key.',
                                   utils.quoted(key))
                    return
            self.added = True
            self.db.setAre(dynamic.channel, key, value)
        if msg.addressed:
            self.confirm()

    def stats(self, irc, msg, args, channel):
        """takes no arguments

        Returns the number of changes and requests made to the Infobot database
        since the plugin was loaded.
        """
        changes = self.db.getChangeCount(channel)
        responses = self.db.getResponseCount(channel)
        now = time.time()
        diff = int(now - world.startedAt)
        mode = {True: 'optional', False: 'require'}
        answer = self.registryValue('unaddressed.answerQuestions')
        irc.reply('Since %s, there %s been %s and %s. I have been awake for %s'
                  ' this session, and currently reference %s. Addressing is in'
                  ' %s mode.' % (time.ctime(world.startedAt),
                                 utils.has(changes),
                                 utils.nItems('modification', changes),
                                 utils.nItems('question', responses),
                                 utils.timeElapsed(int(now - world.startedAt)),
                                 utils.nItems('factoid',
                                              self.db.getNumFacts(channel)),
                                 mode[answer]))
    stats = wrap(stats, ['channeldb'])
    status=stats

    def tell(self, irc, msg, args, channel, nick, _, factoid):
        """<nick> [about] <factoid>

        Tells <nick> about <factoid>.
        """
        try:
            hostmask = irc.state.nickToHostmask(nick)
        except KeyError:
            irc.error('I haven\'t seen %s, I\'ll let you '
                      'do the telling.' % nick, Raise=True)
        newmsg = ircmsgs.privmsg(irc.nick, factoid+'?', prefix=hostmask)
        try:
            prepend = '%s wants you to know that ' % msg.nick
            self.factoid(factoid, msg=newmsg, prepend=prepend)
        except Dunno:
            self.dunno()
    tell = wrap(tell, ['channeldb', 'something',
                       optional(('literal', 'about')), 'text'])


Class = Infobot

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
