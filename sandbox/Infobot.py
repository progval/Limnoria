#!/usr/bin/env python
# -*- coding:utf-8 -*-

###
# Copyright (c) 2004, Stéphan Kochen
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
A plugin that tries to emulate Infobot somewhat faithfully.
"""

__revision__ = "$Id$"

import plugins

import re
import anydbm
import random
import os.path

import log
import conf
import ircmsgs
import ircutils
import privmsgs
import registry
import callbacks

conf.registerPlugin('Infobot')

conf.registerGlobalValue(conf.supybot.plugins.Infobot, 'infobotStyleStatus',
    registry.Boolean(False, """Whether to reply to the status command with an
    original Infobot style message or with a short message."""))
# FIXME: rename; description
conf.registerChannelValue(conf.supybot.plugins.Infobot,
    'catchWhenNotAddressed', registry.Boolean(True, """Whether to catch
    non-addressed stuff at all."""))
conf.registerChannelValue(conf.supybot.plugins.Infobot,
    'replyQuestionWhenNotAddressed', registry.Boolean(True, """Whether to
    answer to non-addressed stuff we know about."""))
conf.registerChannelValue(conf.supybot.plugins.Infobot,
    'replyDontKnowWhenNotAddressed', registry.Boolean(False, """Whether to
    answer to non-addressed stuff we don't know about."""))
conf.registerChannelValue(conf.supybot.plugins.Infobot,
    'replyWhenNotAddressed', registry.Boolean(False, """Whether to answer to
    non-addressed, non-question stuff."""))

# Replies
# XXX: Move this to a plaintext db of some sort?
# XXX: random.choice() doesn't like sets? :/
repliesHello = [
    'Hello',                    'Hi',
    'Hey',                      'Niihau',
    'Bonjour',                  'Hola',
    'Salut',                    'Que tal',
    'Privet',                   'What\'s up'
]

repliesWelcome = [
    'No problem',               'My pleasure',
    'Sure thing',               'No worries',
    'De nada',                  'De rien',
    'Bitte',                    'Pas de quoi'
]

repliesDontKnow = [
    'I don\'t know.',           'Wish I knew',
    'I don\'t have a clue.',    'No idea.',
    'Bugger all, I dunno.'
]

repliesConfirm = [
    'Gotcha',                   'Ok',
    '10-4',                     'I hear ya',
    'Got it'
]

repliesStatement = [
    '%(key)s %(verb)s %(value)s',
    'I think %(key)s %(verb)s %(value)s',
    'Hmmm... %(key)s %(verb)s %(value)s',
    'It has been said that %(key)s %(verb)s %(value)s',
    '%(key)s %(verb)s probably %(value)s',
    'Rumour has it %(key)s %(verb)s %(value)s',
    'I heard %(key)s %(overb)s %(value)s',
    'Somebody said %(key)s %(overb)s %(value)s',
    'I guess ${key}s %(verb)s %(value)s',
    'Well, %(key)s %(verb)s %(key)s',
    '%(key)s is, like, %(value)s',
    'I\'m pretty sure %(key)s is %(value)s'
]

# XXX: Most of these are a bunch of regexps taken from Infobot.
#      Hopefully this is compatible with it's license (I think it is), but
#      I'm not a lawyer, so someone should take a look at it:
#      http://www.opensource.org/licenses/artistic-license.php
#      We should atleast leave that link and Infobot's address here I think.
canonicalizeRe = [(re.compile(r[0], re.I), r[1]) for r in [
    (r"(.*)", r" \1 "),
	(r"\s\s+", r" "),
    
    (r" si ", r" is "),
    (r" teh ", r "the "),
    
	# where blah is -> where is blah
    # XXX: Why two?
	(r" (where|what|who) (\S+) (is|are) ", r" \1 \3 \2 "),
    # XXX: Non greedy (.*) ?
	(r" (where|what|who) (.*) (is|are) ", r" \1 \3 \2 "),
	
    # XXX: Does absolutely nothing?
	#(r"^\s*(.*?)\s*", r"\1"),
	
	(r" be tellin'?g? ", r" tell "),
	(r" '?bout ", r" about "),

	(r",? any(hoo?w?|ways?) ", r" "),
	(r",?\s?(pretty )*please\?? $", r"\?"),
	
	# Profanity filters; just delete it.
	(r" th(e|at|is) (((m(o|u)th(a|er) ?)?fuck(in'?g?)?|hell|heck|(god-?)?damn?(ed)?) ?)+ ", r" "),
	(r" wtf ", r" where "),
	(r" this (.*) thingy? ", r" \1 "),
	(r" this thingy?( called)? ", r" "),
	(r" ha(s|ve) (an?y?|some|ne) (idea|clue|guess|seen) ", r" know "),
	(r" does (any|ne|some) ?(1|one|body) know ", r" "),
	(r" do you know ", r" "),
	(r" can (you|u|((any|ne|some) ?(1|one|body)))( please)? tell (me|us|him|her) ", r" "),
	(r" where (\S+) can \S+( (a|an|the))? ", r" "),
	(r" (can|do) (i|you|one|we|he|she) (find|get)( this)? ", r" is "),
	(r" (i|one|we|he|she) can (find|get) ", r" is "),
	(r" (the )?(add?ress?|url) (for|to) ", r" "),   # this should be more specific
	(r" (where is )+", r" where is "),

	# Switch person.
	(" \x00[s'] ", " \x00's "),    # fix genitives
	(r" i'm ", " \x00 is "),
	(r" i('?ve| have) ", " \x00 has "),
	(r" i haven'?t ", " \x00 has not "),
	(r" i ", " \x00 "),
	(r" am ", " is "),
	(r" (me|myself) ", " \x00 "),
	(r" my ", " \x00's "),  # turn 'my' into name's
	(r" you'?re ", r" you are "),
    (r" were ", r" are "),
    (r" was ", r" is ")
]]

# Regexps which replace with the bot's nickname
replaceWithSelfRe = [(re.compile(r[0], re.I), r[1]) for r in [
    (r" are you ", " is \x00 "),
    (r" you are ", " \x00 is "),
    (r" you ", " \x00 "),
    (r" your ", " \x00's "),
    (r" yourself ", " \x00 ")
]]

# Check if we're addressed like: "No, supybot, bla is..."
# XXX: We assume the nickname is followed by punctuation here.
addressedRe = re.compile('^(no)[, ]+\x00\\s*([-:,]+)', re.I)

# XXX: Kinda messy
def canonicalSentence(s, myNick, hisNick, addressed):
    # Because we can't alter the pattern in compiled regexps to match a
    # nickname, we substitute it with \x00 here, just search for that
    # instead and at the end reverse it back to normal nicks.
    nickReplaceRe = re.compile(re.escape(hisNick), re.I)
    s = nickReplaceRe.sub('\x00', s)
    for (r, subst) in canonicalizeRe:
        s = r.sub(subst, s)
    s = s.replace('\x00', hisNick)
    nickReplaceRe = re.compile(re.escape(myNick), re.I)
    s = nickReplaceRe.sub('\x00', s)
    (s, n) = addressedRe.subn(r'\1\2', s)
    if n:
        addressed = True
    if addressed:
        for (r, subst) in replaceWithSelfRe:
            s = r.sub(subst, s)
    s = s.replace('\x00', myNick)
    return (s.strip(), addressed)


# FIXME: This should become a subclass of the database backend later on

# Factoids get stored in the db as db['is/are key'] = 'keyvalue'
# This is because the actual key in the database is lowercase so we can do
# lowercase searches, but get the actual string from the value.
class InfobotDatabase(object):
    def __init__(self, filename=None):
        if not filename:
            filename = 'Infobot.db'
            filename = os.path.join(conf.supybot.directories.data(), filename)
        self._db = anydbm.open(filename, 'c')
    
    def die(self):
        self._db.close()

    # Hardly any try-statements here. db[] raises our exceptions for us.
    def getFactoid(self, verb, key):
        factoid = {}
        verb = verb.lower()
        key = key.lower()
        dbKey = '%s %s' % (verb, key)
        factoid['key'] = self._db[dbKey][:len(key)]
        factoid['verb'] = verb
        if verb == 'are':
            factoid['overb'] = 'were'
        else:
            factoid['overb'] = 'was'
        factoid['value'] = self._db[dbKey][len(key):]
        return factoid

    def hasFactoid(self, verb, key):
        verb = verb.lower()
        dbKey = key.lower()
        dbKey = '%s %s' % (verb, dbKey)
        try:
            self._db[dbKey]
            return True
        except KeyError:
            return False

    # FIXME: debugs, baleet
    def insertFactoid(self, key, verb, value):
        verb = verb.lower()
        dbKey = key.lower()
        dbKey = '%s %s' % (verb, dbKey)
        try:
            self._db[dbKey]
        except KeyError:
            log.info('ins: %s =%s= %s' % (key, verb, value))
            self._db[dbKey] = '%s%s' % (key, value)
            return
        log.info('dup: %s !%s! %s' % (key, verb, value))
        raise KeyError, key
    
    def setFactoid(self, key, verb, value):
        verb = verb.lower()
        dbKey = key.lower()
        dbKey = '%s %s' % (verb, dbKey)
        self._db[dbKey] = '%s%s' % (key, value)
        log.info('set: %s => %s' % (key, value))

    def addFactoid(self, key, verb, value):
        verb = verb.lower()
        dbKey = key.lower()
        dbKey = '%s %s' % (verb, dbKey)
        # XXX: should we create new entries here too
        #      if the factoid doesn't exist already?
        currentValue = self._db[dbKey]
        newValue = '%s, or %s' % (currentValue, value)
        self._db[dbKey] = newValue
        log.info('add: %s +%s+ %s' % (key, verb, value))
    
    def deleteFactoid(self, verb, key):
        verb = verb.lower()
        dbKey = key.lower()
        dbKey = '%s %s' % (verb, dbKey)
        del db[dbKey]
        log.info('forgot: %s' % key)
    
    def getNumberOfFactoids(self):
        return len(self._db)
        

class Infobot(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = InfobotDatabase()
    
    # Patterns for processing private messages.
    statementRe = re.compile(r'^(no[-:, ]+)?(.+?)\s+(is|are|was|were)'
                                 r'\s+(also\s+)?(.+)$', re.I)
    questionRe = re.compile(r'^(?:what|where|when)\s+(is|are|was|were)'
                            r'\s+(.*)$', re.I)
    # FIXME: Matches everything with a question mark stuck to the end. o_O
    shortQuestionRe = re.compile(r'^(.+)$')
    # XXX: If possible, extend this, because people tend to use
    #      periods inside sentences as well, not just at the end.
    #      (indicating a pause with triple dots for example)
    splitRe = re.compile(r'\s*([^?!.]+)([?!.]*)\s*')
    def doPrivmsg(self, irc, msg):
        channel = privmsgs.getChannel(msg, None, raiseError=False)
        message = callbacks.addressed(irc.nick, msg)
        addressed = bool(message)
        if not addressed:
            message = msg.args[1]
        message = ircutils.stripFormatting(message)
        for m in self.splitRe.finditer(message):
            (s, ending) = m.groups()
            question = '?' in ending
            (s, addressed) = canonicalSentence(s, irc.nick, msg.nick,
                                               addressed)
            log.debug('canonicalSentence(): %s' % s)
            if not (addressed or self.registryValue('catchWhenNotAddressed')):
                continue
            # FIXME: This is a friggin mess.
            # XXX: PrivmsgCommandAndRegexp should take care of this?
            #      (probably not)
            match = self.questionRe.search(s)
            proxy = callbacks.IrcObjectProxyRegexp(irc, msg)
            if match:
                self.question(proxy, match, addressed)
            elif not question:
                match = self.statementRe.search(s)
                if match:
                    self.statement(proxy, match, addressed)
            if not match and question:
                match = self.shortQuestionRe.search(s)
                if match:
                    self.shortQuestion(proxy, match, addressed)
    
    def statement(self, irc, match, addressed):
        (correction, key, verb, addition, value) = match.groups()
        if self.db.hasFactoid(verb, key):
            if correction:
                self.db.setFactoid(key, verb, value)
            elif addition:
                self.db.addFactoid(key, verb, value)
            elif addressed or self.registryValue('replyWhenNotAddressed'):
                factoid = self.db.getFactoid(verb, key)
                if factoid['value'].lower() == value.lower():
                    irc.reply('I already had it like that.')
                else:
                    irc.reply('...but %s %s %s...' % (key, verb, value))
                return
        else:
            self.db.insertFactoid(key, verb, value)
        if addressed or self.registryValue('replyWhenNotAddressed'):
            irc.reply(random.choice(repliesConfirm))

    def question(self, irc, match, addressed):
        (verb, key) = match.groups()
        try:
            factoid = self.db.getFactoid(verb, key)
        except KeyError:
            if addressed or
                        self.registryValue('replyDontKnowWhenNotAddressed'):
                irc.reply(random.choice(repliesDontKnow))
                return
        if addressed or self.registryValue('replyQuestionWhenNotAddressed'):
            irc.reply(random.choice(repliesStatement) % factoid)

    def shortQuestion(self, irc, match, addressed):
        # FIXME: clean up that regexp first.
        return
        key = match.group(1)
        try:
            factoid = self.db.getFactoid('is', key)
        except KeyError:
            try:
                factoid = self.db.getFactoid('are', key)
            except KeyError:
                if addressed or
                        self.registryValue('replyDontKnowWhenNotAddressed'):
                    irc.reply(random.choice(repliesDontKnow))
                    return
        if addressed or self.registryValue('replyQuestionWhenNotAddressed'):
            irc.reply(random.choice(repliesStatement) % factoid)
    
    def forget(self, irc, msg, args):
        """<factoid>
        
        Make the bot forget about <factoid>."""
        key = privmsgs.getArgs()
        try:
            self.db.deleteFactoid('is', key)
        except KeyError:
            try:
                self.db.deleteFactoid('are', key)
            except KeyError:
                irc.reply('I didn\'t know about that in the first place.')
                return
        irc.reply('I forgot %s' % key)

    def whatis(self, irc, msg, args):
        """<factoid>
        
        Explain what <factoid> is."""
        key = privmsgs.getArgs()
        try:
            factoid = self.db.getFactoid('is', key)
        except KeyError:
            try:
                factoid = self.db.getFactoid('are', key)
            except KeyError:
                irc.reply('I don\'t know anything about %s' % key)
                return
        irc.reply(random.choice(repliesStatement) % factoid)

    def stats(self, irc, msg, args):
        """<requires no arguments>
        
        Display some statistics on the infobot database."""
        num = self.db.getNumberOfFactoids()
        if self.registryValue('infobotStyleStatus'):
            # FIXME: Original infobot style status message
            # <Inf0bot> Since Sat Apr 17 19:31:21 2004, there have been 0
            #           modifications and 0 questions.  I have been awake for
            #           59 seconds this session, and currently reference
            #           20 factoids. Addressing is in optional mode.
            pass
        else:
            irc.reply('I know about %s factoids.' % num)


Class = Infobot

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2 and sys.argv[1] not in ('is', 'are'):
        print 'Usage: %s <is|are> <factpack> [<factpack> ...]' % sys.argv[0]
        sys.exit(-1)
    r = re.compile(r'\s+=>\s+')
    db = InfobotDatabase()
    for filename in sys.argv[2:]:
        fd = file(filename)
        for line in fd:
            line = line.strip()
            if not line or line[0] in ('*', '#'):
                continue
            else:
                try:
                    (key, value) = r.split(line, 1)
                    db.setFactoid(key, sys.argv[1], value)
                except Exception, e:
                    print 'Invalid line (%s): %r' %(utils.exnToString(e),line)


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
