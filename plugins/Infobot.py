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

import supybot

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
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

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

filename = conf.supybot.directories.data.dirize('Infobot.db')

ends = ['!',
        '.',
        ', $who.',]
dunnos = ['Dunno',
          'No idea',
          'I don\'t know',
          'I have no idea',
          'I don\'t have a clue',]
confirms = ['10-4',
            'Okay',
            'Got it',
            'Gotcha',
            'I hear ya']
initialIs = {'who': '<reply>',
             'what': '<reply>',
             'when': '<reply>',
             'where': '<reply>',
             'why': '<reply>',
             'it': '<reply>',
            }
initialAre = {'who': '<reply>',
              'what': '<reply>',
              'when': '<reply>',
              'where': '<reply>',
              'why': '<reply>',
              'it': '<reply>',
              'roses': 'red',
              'violets': 'blue',
             }

class PickleInfobotDB(object):
    def __init__(self):
        self._changes = 0
        self._responses = 0
        try:
            fd = file(filename)
        except EnvironmentError:
            self._is = utils.InsensitivePreservingDict()
            self._are = utils.InsensitivePreservingDict()
            for (k, v) in initialIs.iteritems():
                self.setIs(k, v)
            for (k, v) in initialAre.iteritems():
                self.setAre(k, v)
            self._changes = 0
        else:
            try:
                (self._is, self._are) = pickle.load(fd)
            except cPickle.UnpicklingError, e:
                raise dbi.InvalidDBError, str(e)

    def flush(self):
        fd = utils.transactionalFile(filename, 'wb')
        pickle.dump((self._is, self._are), fd)
        fd.close()

    def close(self):
        self.flush()

    def changeIs(self, factoid, replacer):
        try:
            old = self._is[factoid]
        except KeyError:
            raise dbi.NoRecordError
        if replacer is not None:
            self._is[factoid] = replacer(old)
            self.flush()
            self._changes += 1

    def getIs(self, factoid):
        ret = self._is[factoid]
        self._responses += 1
        return ret

    def setIs(self, fact, oid):
        self._is[fact] = oid
        self.flush()
        self._changes += 1

    def delIs(self, factoid):
        try:
            del self._is[factoid]
        except KeyError:
            raise dbi.NoRecordError
        self.flush()
        self._changes += 1

    def hasIs(self, factoid):
        return factoid in self._is

    def changeAre(self, factoid, replacer):
        try:
            old = self._are[factoid]
        except KeyError:
            raise dbi.NoRecordError
        if replacer is not None:
            self._are[factoid] = replacer(old)
            self._changes += 1
            self.flush()

    def getAre(self, factoid):
        ret = self._are[factoid]
        self._responses += 1
        return ret

    def hasAre(self, factoid):
        return factoid in self._are

    def setAre(self, fact, oid):
        self._are[fact] = oid
        self.flush()
        self._changes += 1

    def delAre(self, factoid):
        try:
            del self._are[factoid]
        except KeyError:
            raise dbi.NoRecordError
        self.flush()
        self._changes += 1

    def getDunno(self):
        return random.choice(dunnos) + random.choice(ends)

    def getConfirm(self):
        return random.choice(confirms) + random.choice(ends)

    def getChangeCount(self):
        return self._changes

    def getResponseCount(self):
        return self._responses

    def getNumFacts(self):
        return len(self._are.keys()) + len(self._is.keys())

class SqliteInfobotDB(object):
    def __init__(self):
        self._changes = 0
        self._responses = 0
        self.db = None

    def _getDb(self):
        if self.db is not None:
            return self.db
        try:
            if os.path.exists(filename):
                self.db = sqlite.connect(filename)
                return self.db
            #else:
            self.db = sqlite.connect(filename)
            cursor = self.db.cursor()
            cursor.execute("""CREATE TABLE isFacts (
                              key TEXT UNIQUE ON CONFLICT REPLACE,
                              value TEXT
                              );""")
            cursor.execute("""CREATE TABLE areFacts (
                              key TEXT UNIQUE ON CONFLICT REPLACE,
                              value TEXT
                              );""")
            self.db.commit()
            for (k, v) in initialIs.iteritems():
                self.setIs(k, v)
            for (k, v) in initialAre.iteritems():
                self.setAre(k, v)
            self._changes = 0
            return self.db
        except sqlite.DatabaseError, e:
            raise dbi.InvalidDBError, str(e)

    def close(self):
        if self.db is not None:
            self.db.close()

    def changeIs(self, factoid, replacer):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT value FROM isFacts WHERE key=%s""", factoid)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        old = cursor.fetchone()[0]
        if replacer is not None:
            cursor.execute("""UPDATE isFacts SET value=%s WHERE key=%s""",
                           replacer(old), factoid)
            db.commit()
            self._changes += 1

    def getIs(self, factoid):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT value FROM isFacts WHERE key=%s""", factoid)
        ret = cursor.fetchone()[0]
        self._responses += 1
        return ret

    def setIs(self, fact, oid):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""INSERT INTO isFacts VALUES (%s, %s)""", fact, oid)
        db.commit()
        self._changes += 1

    def delIs(self, factoid):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""DELETE FROM isFacts WHERE key=%s""", factoid)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        db.commit()
        self._changes += 1

    def hasIs(self, factoid):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM isFacts WHERE key=%s""", factoid)
        return cursor.rowcount == 1

    def changeAre(self, factoid, replacer):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT value FROM areFacts WHERE key=%s""", factoid)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        old = cursor.fetchone()[0]
        if replacer is not None:
            cursor.execute("""UPDATE areFacts SET value=%s WHERE key=%s""",
                           replacer(old), factoid)
            db.commit()
            self._changes += 1

    def getAre(self, factoid):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT value FROM areFacts WHERE key=%s""", factoid)
        ret = cursor.fetchone()[0]
        self._responses += 1
        return ret

    def setAre(self, fact, oid):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""INSERT INTO areFacts VALUES (%s, %s)""", fact, oid)
        db.commit()
        self._changes += 1

    def delAre(self, factoid):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""DELETE FROM areFacts WHERE key=%s""", factoid)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        db.commit()
        self._changes += 1

    def hasAre(self, factoid):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM areFacts WHERE key=%s""", factoid)
        return cursor.rowcount == 1

    def getDunno(self):
        return random.choice(dunnos) + random.choice(ends)

    def getConfirm(self):
        return random.choice(confirms) + random.choice(ends)

    def getChangeCount(self):
        return self._changes

    def getResponseCount(self):
        return self._responses

    def getNumFacts(self):
        db = self._getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM areFacts""")
        areFacts = int(cursor.fetchone()[0])
        cursor.execute("""SELECT COUNT(*) FROM isFacts""")
        isFacts = int(cursor.fetchone()[0])
        return areFacts + isFacts

def InfobotDB():
    return SqliteInfobotDB()

class Dunno(Exception):
    pass

class Infobot(callbacks.PrivmsgCommandAndRegexp):
    regexps = ['doForget', 'doChange', 'doFactoid', 'doUnknown']
    def __init__(self):
        super(Infobot, self).__init__()
        try:
            self.db = InfobotDB()
        except Exception:
            self.log.exception('Error loading %s:', filename)
            raise # So it doesn't get loaded without its database.
        self.irc = None
        self.msg = None
        self.force = False
        self.replied = True
        self.badForce = False
        self.addressed = False

    def die(self):
        self.db.close()

    def _error(self, s):
        if self.addressed:
            self.irc.error(s)
        else:
            self.log.warning(s)

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
        irc.reply(plugins.standardSubstitute(irc, msg, s),
                  prefixName=False, action=action, msg=msg)

    def confirm(self, irc=None, msg=None):
        if self.registryValue('personality'):
            self.reply(self.db.getConfirm(), irc=irc, msg=msg)
        else:
            assert self.irc is not None
            self.reply(conf.supybot.replies.success())

    def dunno(self, irc=None, msg=None):
        if self.registryValue('personality'):
            self.reply(self.db.getDunno(), irc=irc, msg=msg)
        else:
            self.reply(self.registryValue('boringDunno'), irc=irc, msg=msg)

    def factoid(self, key, irc=None, msg=None, dunno=True, prepend=''):
        if irc is None:
            assert self.irc is not None
            irc = self.irc
        if msg is None:
            assert self.msg is not None
            msg = self.msg
        isAre = None
        try:
            if self.db.hasIs(key):
                isAre = 'is'
                value = self.db.getIs(key)
            elif self.db.hasAre(key):
                isAre = 'are'
                value = self.db.getAre(key)
        except dbi.InvalidDBError:
            self._error('Unable to access db: %s' % e)
            return
        if isAre is None:
            if self.addressed:
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

    def normalize(self, s):
        s = ircutils.stripFormatting(s)
        s = s.strip() # After stripFormatting for formatted spaces.
        s = utils.normalizeWhitespace(s)
        contractions = [('what\'s', 'what is'), ('where\'s', 'where is'),
                        ('who\'s', 'who is'), ('wtf\'s', 'wtf is'),]
        for (contraction, replacement) in contractions:
            if s.startswith(contraction):
                s = replacement + s[len(contraction):]
        return s

    _forceRe = re.compile(r'^no[,: -]+', re.I)
    _karmaRe = re.compile(r'^\S+(?:\+\+|--)(?:\s+)?$')
    def doPrivmsg(self, irc, msg):
        try:
            if ircmsgs.isCtcp(msg):
                return
            # probably not necessary, but we'll see what the debug logs show
            if getattr(irc, 'finished', False):
                self.log.debug('Received a finished irc object. Bailing.')
                return
            maybeAddressed = callbacks.addressed(irc.nick, msg,
                                                 whenAddressedByNick=True)
            if maybeAddressed:
                self.addressed = True
                payload = maybeAddressed
            else:
                payload = msg.args[1]
            if self._karmaRe.search(payload):
                self.log.debug('Not snarfing a karma adjustment.')
                return
            payload = self.normalize(payload)
            maybeForced = self._forceRe.sub('', payload)
            if maybeForced != payload:
                self.force = True
                # Infobot requires that forces have the form "no, botname, ..."
                # We think that's stupid to require the bot name if the bot is
                # being directly addressed. The following makes sure both
                # "botname: no, botname, ..." and "botname: no, ..." work the
                # same and non-addressed forms require the bots nick.
                nick = irc.nick.lower()
                if not self.addressed:
                    if not maybeForced.lower().startswith(nick):
                        self.badForce = True
                        self.force = False
                if maybeForced.lower().startswith(nick):
                    maybeForced = maybeForced[len(nick):].lstrip(', ')
                payload = maybeForced
            # Let's make sure we dump out of Infobot if the privmsg is an
            # actual command otherwise we could get multiple responses.
            if self.addressed:
                try:
                    tokens = callbacks.tokenize(payload)
                    if callbacks.findCallbackForCommand(irc, tokens[0]):
                        return
                    elif '=~' not in payload:
                        payload += '?'
                    else:       # Looks like we have a doChange expression
                        pass
                except SyntaxError:
                    pass
            if payload.endswith(irc.nick):
                self.addressed = True
                payload = payload[:-len(irc.nick)]
                payload = payload.strip(', ') # Strip punctuation before nick.
                payload += '?' # So doUnknown gets called.
            if not payload.strip():
                self.log.debug('Bailing since we received an empty msg.')
                return
            msg = ircmsgs.privmsg(msg.args[0], payload, prefix=msg.prefix)
            super(Infobot, self).doPrivmsg(irc, msg)
        finally:
            self.force = False
            self.replied = False
            self.badForce = False
            self.addressed = False

    def callCommand(self, f, irc, msg, *L, **kwargs):
        try:
            self.irc = irc
            self.msg = msg
            super(Infobot, self).callCommand(f, irc, msg, *L, **kwargs)
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
            except dbi.NoRecordError:
                pass
        if deleted:
            self.confirm()
        else:
            # XXX: Should this be genericified?
            self.reply('I\'ve never heard of %s, %s!' % (fact, msg.nick))

    def doChange(self, irc, msg, match):
        r"^(.+)\s+=~\s+(.+)$"
        (fact, regexp) = match.groups()
        changed = False
        try:
            r = utils.perlReToReplacer(regexp)
        except ValueError, e:
            if self.addressed:
                irc.error('Invalid regexp: %s' % regexp)
                return
            else:
                self.log.debug('Invalid regexp: %s' % regexp)
                return
        for method in [self.db.changeIs, self.db.changeAre]:
            try:
                method(fact, r)
                changed = True
            except dbi.NoRecordError:
                pass
        if changed:
            self.confirm()
        else:
            # XXX: Should this be genericified?
            self.reply('I\'ve never heard of %s, %s!' % (fact, msg.nick))

    def doUnknown(self, irc, msg, match):
        r"^(.+?)\s*\?[?!. ]*$"
        key = match.group(1)
        if self.addressed or self.registryValue('answerUnaddressedQuestions'):
            self.factoid(key) # Does the dunno'ing for us itself.

    def invalidCommand(self, irc, msg, tokens):
            irc.finished = True

    def doFactoid(self, irc, msg, match):
        r"^(.+?)\s+(?<!\\)(was|is|am|were|are)\s+(also\s+)?(.+?)[?!. ]*$"
        (key, isAre, also, value) = match.groups()
        key = key.replace('\\', '')
        if key.lower() in ('where', 'what', 'who', 'wtf'):
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
                    self.log.debug('Adding %r to %r.', key, value)
                    value = '%s or %s' % (self.db.getIs(key), value)
                elif self.force:
                    self.log.debug('Forcing %r to %r.', key, value)
                elif self.badForce:
                    value = self.db.getIs(key)
                    self.reply('... but %s is %s, %s ...' % (key, value,
                                                             msg.nick))
                    return
                elif self.addressed:
                    value = self.db.getIs(key)
                    self.reply('But %s is %s, %s.' % (key, value, msg.nick))
                    return
                else:
                    self.log.debug('Already have a %r key.', key)
                    return
            self.db.setIs(key, value)
        else:
            if self.db.hasAre(key):
                if also:
                    self.log.debug('Adding %r to %r.', key, value)
                    value = '%s or %s' % (self.db.getAre(key), value)
                elif self.force:
                    self.log.debug('Forcing %r to %r.', key, value)
                elif self.badForce:
                    value = self.db.getAre(key)
                    self.reply('... but %s are %s, %s ...' % (key, value,
                                                              msg.nick))
                    return
                elif self.addressed:
                    value = self.db.getAre(key)
                    self.reply('But %s are %s, %s.' % (key, value, msg.nick))
                    return
                else:
                    self.log.debug('Already have a %r key.', key)
                    return
            self.db.setAre(key, value)
        if self.addressed or self.force or also:
            self.confirm()

    def stats(self, irc, msg, args):
        """takes no arguments

        Returns the number of changes and requests made to the Infobot database
        since the plugin was loaded.
        """
        changes = self.db.getChangeCount()
        responses = self.db.getResponseCount()
        now = time.time()
        diff = int(now - world.startedAt)
        mode = {True: 'optional', False: 'require'}
        answer = self.registryValue('answerUnaddressedQuestions')
        irc.reply('Since %s, there %s been %s and %s. I have been awake for %s'
                  ' this session, and currently reference %s. Addressing is in'
                  ' %s mode.' % (time.ctime(world.startedAt),
                                 utils.has(changes),
                                 utils.nItems('modification', changes),
                                 utils.nItems('question', responses),
                                 utils.timeElapsed(int(now - world.startedAt)),
                                 utils.nItems('factoid',self.db.getNumFacts()),
                                 mode[answer]))
    status=stats

    def tell(self, irc, msg, args):
        """<nick> [about] <factoid>

        Tells <nick> about <factoid>.
        """
        if len(args) < 2:
            raise callbacks.ArgumentError
        if args[1] == 'about':
            del args[1]
        (nick, factoid) = privmsgs.getArgs(args, required=2)
        try:
            hostmask = irc.state.nickToHostmask(nick)
        except KeyError:
            irc.error('I haven\'t seen %s, I\'ll let you do the telling.')
            return
        newmsg = ircmsgs.privmsg(irc.nick, factoid+'?', prefix=hostmask)
        try:
            prepend = '%s wants you to know that ' % msg.nick
            self.factoid(factoid, msg=newmsg, prepend=prepend)
        except Dunno:
            self.dunno()


Class = Infobot

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
