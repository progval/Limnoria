#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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
Allows aliases for other commands.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import os
import re
import sets

import supybot.conf as conf
import supybot.utils as utils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks
import supybot.structures as structures
import supybot.unpreserve as unpreserve

class AliasError(Exception):
    pass

class RecursiveAlias(AliasError):
    pass

def findAliasCommand(s, alias):
    s = re.escape(s)
    r = re.compile(r'(?:(^|\[)\s*\b%s\b|\|\s*\b%s\b)' % (s, s))
    return bool(r.search(alias))

dollarRe = re.compile(r'\$(\d+)')
def findBiggestDollar(alias):
    dollars = dollarRe.findall(alias)
    dollars = map(int, dollars)
    dollars.sort()
    if dollars:
        return dollars[-1]
    else:
        return 0

atRe = re.compile(r'@(\d+)')
def findBiggestAt(alias):
    ats = atRe.findall(alias)
    ats = map(int, ats)
    ats.sort()
    if ats:
        return ats[-1]
    else:
        return 0

def makeNewAlias(name, alias):
    original = alias
    if findAliasCommand(name, alias):
        raise RecursiveAlias
    biggestDollar = findBiggestDollar(original)
    biggestAt = findBiggestAt(original)
    wildcard = '$*' in original
    if biggestAt and wildcard:
        raise AliasError, 'Can\'t mix $* and optional args (@1, etc.)'
    if original.count('$*') > 1:
        raise AliasError, 'There can be only one $* in an alias.'
    testTokens = callbacks.tokenize(original)
    if testTokens and isinstance(testTokens[0], list):
        raise AliasError, 'Commands may not be the result of nesting.'
    def f(self, irc, msg, args):
        alias = original.replace('$nick', msg.nick)
        if '$channel' in original:
            channel = privmsgs.getChannel(msg, args)
            alias = alias.replace('$channel', channel)
        tokens = callbacks.tokenize(alias)
        if not wildcard and biggestDollar or biggestAt:
            args = privmsgs.getArgs(args,
                                    required=biggestDollar,
                                    optional=biggestAt)
            # Gotta have a mutable sequence (for replace).
            if biggestDollar + biggestAt == 1: # We got a string, no tuple.
                args = [args]
        def regexpReplace(m):
            idx = int(m.group(1))
            return args[idx-1]
        def replace(tokens, replacer):
            for (i, token) in enumerate(tokens):
                if isinstance(token, list):
                    replace(token, replacer)
                else:
                    tokens[i] = replacer(token)
        replace(tokens, lambda s: dollarRe.sub(regexpReplace, s))
        if biggestAt:
            assert not wildcard
            args = args[biggestDollar:]
            replace(tokens, lambda s: atRe.sub(regexpReplace, s))
        if wildcard:
            assert not biggestAt
            # Gotta remove the things that have already been subbed in.
            i = biggestDollar
            while i:
                args.pop(0)
                i -= 1
            def everythingReplace(tokens):
                for (i, token) in enumerate(tokens):
                    if isinstance(token, list):
                        if everythingReplace(token):
                            return
                    if token == '$*':
                        tokens[i:i+1] = args
                        return True
                    elif '$*' in token:
                        tokens[i] = token.replace('$*', ' '.join(args))
                        return True
                return False
            everythingReplace(tokens)
        Owner = irc.getCallback('Owner')
        d = Owner.disambiguate(irc, tokens)
        if d:
            Owner.ambiguousError(irc, msg, d)
        else:
            self.Proxy(irc.irc, msg, tokens)
    doc ='<an alias, %s>\n\nAlias for %r' % \
          (utils.nItems('argument', biggestDollar), alias)
    f = utils.changeFunctionName(f, name, doc)
    return f

conf.registerPlugin('Alias')
conf.registerGroup(conf.supybot.plugins.Alias, 'aliases')
filename = os.path.join(conf.supybot.directories.conf(), 'aliases.conf')
class Alias(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        # Schema: {alias: [command, locked]}
        self.aliases = {}
        group = conf.supybot.plugins.Alias.aliases
        for (name, alias) in registry._cache.iteritems():
            name = name.lower()
            if name.startswith('supybot.plugins.alias.aliases.'):
                name = name[len('supybot.plugins.alias.aliases.'):]
                if '.' in name:
                    continue
                conf.registerGlobalValue(group, name, registry.String('', ''))
                conf.registerGlobalValue(group.get(name), 'locked',
                                         registry.Boolean(False, ''))
        for (name, value) in group.getValues(fullNames=False):
            name = name.lower() # Just in case.
            command = value()
            locked = value.locked()
            self.aliases[name] = [command, locked]

    def __call__(self, irc, msg):
        # Adding the aliases requires an Irc.  So the first time we get called
        # with an Irc, we add our aliases and then delete ourselves :)
        for (alias, (command, locked)) in self.aliases.items():
            try:
                self.addAlias(irc, alias, command, locked)
            except Exception, e:
                self.log.exception('Exception when trying to add alias %s.  '
                                   'Removing from the Alias database.' % alias)
                del self.aliases[alias]
        del self.__class__.__call__
        callbacks.Privmsg.__call__(self, irc, msg)

    def lock(self, irc, msg, args):
        """<alias>

        Locks an alias so that no one else can change it.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if hasattr(self, name) and self.isCommand(name):
            self.aliases[name][1] = True
            conf.supybot.plugins.Alias.aliases.get(name).locked.setValue(True)
            irc.replySuccess()
        else:
            irc.error('There is no such alias.')
    lock = privmsgs.checkCapability(lock, 'admin')

    def unlock(self, irc, msg, args):
        """<alias>

        Unlocks an alias so that people can define new aliases over it.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if hasattr(self, name) and self.isCommand(name):
            self.aliases[name][1] = False
            conf.supybot.plugins.Alias.aliases.get(name).locked.setValue(False)
            irc.replySuccess()
        else:
            irc.error('There is no such alias.')
    unlock = privmsgs.checkCapability(unlock, 'admin')

    _invalidCharsRe = re.compile(r'[\[\]\s]')
    def addAlias(self, irc, name, alias, lock=False):
        if self._invalidCharsRe.search(name):
            raise AliasError, 'Names cannot contain spaces or square brackets.'
        if '|' in name:
            raise AliasError, 'Names cannot contain pipes.'
        if irc.getCallback(name):
            raise AliasError, 'Names cannot coincide with names of plugins.'
        realName = callbacks.canonicalName(name)
        if name != realName:
            s = 'That name isn\'t valid.  Try %r instead.' % realName
            raise AliasError, s
        name = realName
        cbs = callbacks.findCallbackForCommand(irc, name)
        if self in cbs:
            if hasattr(self, realName) and realName not in self.aliases:
                s = 'You can\'t overwrite commands in this plugin.'
                raise AliasError, s
        if name in self.aliases:
            (currentAlias, locked) = self.aliases[name]
            if locked and currentAlias != alias:
                raise AliasError, 'Alias %r is locked.' % name
        try:
            f = makeNewAlias(name, alias)
        except RecursiveAlias:
            raise AliasError, 'You can\'t define a recursive alias.'
        if name in self.aliases:
            # We gotta remove it so its value gets updated.
            conf.supybot.plugins.Alias.aliases.unregister(name)
        conf.supybot.plugins.Alias.aliases.register(name,
                                                    registry.String(alias, ''))
        conf.supybot.plugins.Alias.aliases.get(name).register('locked',
                                                    registry.Boolean(lock, ''))
        setattr(self.__class__, name, f)
        self.aliases[name] = [alias, lock]

    def removeAlias(self, name, evenIfLocked=False):
        name = callbacks.canonicalName(name)
        if hasattr(self, name) and self.isCommand(name):
            if evenIfLocked or not self.aliases[name][1]:
                delattr(self.__class__, name)
                del self.aliases[name]
                conf.supybot.plugins.Alias.aliases.unregister(name)
            else:
                raise AliasError, 'That alias is locked.'
        else:
            raise AliasError, 'There is no such alias.'

    def add(self, irc, msg, args):
        """<name> <alias>

        Defines an alias <name> that executes <alias>.  The <alias>
        should be in the standard "command argument [nestedcommand argument]"
        arguments to the alias; they'll be filled with the first, second, etc.
        arguments to the alias; they'll be filled with the first, second, etc.
        arguments.  @1, @2 can be used for optional arguments.  $* simply
        means "all remaining arguments," and cannot be combined with optional
        arguments.
        """
        (name, alias) = privmsgs.getArgs(args, required=2)
        if ' ' not in alias:
            # If it's a single word, they probably want $*.
            alias += ' $*'
        try:
            self.addAlias(irc, name, alias)
            self.log.info('Adding alias %r for %r (from %s)' %
                          (name, alias, msg.prefix))
            irc.replySuccess()
        except AliasError, e:
            irc.error(str(e))

    def remove(self, irc, msg, args):
        """<name>

        Removes the given alias, if unlocked.
        """
        name = privmsgs.getArgs(args)
        try:
            self.removeAlias(name)
            self.log.info('Removing alias %r (from %s)' % (name, msg.prefix))
            irc.replySuccess()
        except AliasError, e:
            irc.error(str(e))


Class = Alias

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
