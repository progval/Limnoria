#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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
Allows 'aliases' for other commands.
"""

__revision__ = "$Id$"

import plugins

import os
import re
import sets
import types

import conf
import utils
import privmsgs
import callbacks
import structures

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Alias')

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
        Owner.disambiguate(irc, tokens)
        self.Proxy(irc.irc, msg, tokens)
    f = types.FunctionType(f.func_code, f.func_globals,
                           name, closure=f.func_closure)
    f.__doc__ ='<an alias, %s>\n\nAlias for %r' % \
                (utils.nItems(biggestDollar, 'argument'), alias)
    return f


class Alias(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        filename = os.path.join(conf.dataDir, 'Aliases.db')
        # Schema: {name: [alias, locked]}
        self.aliases = structures.PersistentDictionary(filename)

    def __call__(self, irc, msg):
        # Adding the aliases requires an Irc.  So the first time we get called
        # with an Irc, we add our aliases and then delete ourselves :)
        for (name, (alias, locked)) in self.aliases.iteritems():
            try:
                self.addAlias(irc, name, alias, locked)
            except Exception, e:
                self.log.exception('Exception when trying to add alias %s.  '
                                   'Removing from the Alias database.' % name)
                del self.aliases[name]
        del self.__class__.__call__
        
    def die(self):
        self.aliases.close()

    def lock(self, irc, msg, args):
        """<alias>

        Locks an alias so that no one else can change it.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if hasattr(self, name) and self.isCommand(name):
            self.aliases[name][1] = True
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'There is no such alias.')
    lock = privmsgs.checkCapability(lock, 'admin')

    def unlock(self, irc, msg, args):
        """<alias>

        Unlocks an alias so that people can define new aliases over it.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if hasattr(self, name) and self.isCommand(name):
            self.aliases[name][1] = False
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'There is no such alias.')
    unlock = privmsgs.checkCapability(unlock, 'admin')

    _invalidCharsRe = re.compile(r'[\[\]\s]')
    def addAlias(self, irc, name, alias, lock=False):
        if self._invalidCharsRe.search(name):
            raise AliasError, 'Names cannot contain spaces or square brackets.'
        if conf.enablePipeSyntax and '|' in name:
            raise AliasError, 'Names cannot contain pipes.'
        realName = callbacks.canonicalName(name)
        if name != realName:
            s = 'That name isn\'t valid.  Try %r instead.' % realName
            raise AliasError, s
        name = realName
        cbs = callbacks.findCallbackForCommand(irc, name)
        if [cb for cb in cbs if cb != self]:
            s = 'A command with the name %r already exists.' % name
            raise AliasError, s
        if name in self.aliases:
            (currentAlias, locked) = self.aliases[name]
            if locked and currentAlias != alias:
                raise AliasError, 'Alias %r is locked.' % name
        try:
            f = makeNewAlias(name, alias)
        except RecursiveAlias:
            raise AliasError, 'You can\'t define a recursive alias.'
        setattr(self.__class__, name, f)
        self.aliases[name] = [alias, lock]

    def removeAlias(self, name, evenIfLocked=False):
        name = callbacks.canonicalName(name)
        if hasattr(self, name) and self.isCommand(name):
            if evenIfLocked or not self.aliases[name][1]:
                delattr(self.__class__, name)
                del self.aliases[name]
            else:
                raise AliasError, 'That alias is locked.'
        else:
            raise AliasError, 'There is no such alias.'

    def add(self, irc, msg, args):
        """<name> <alias>

        Defines an alias <name> that executes <alias>.  The <alias>
        should be in the standard "command argument [nestedcommand argument]"
        format.  $[digit] (like $1, $2, etc.) can be used to represent
        arguments to the alias; they'll be filled with the first, second, etc.
        arguments.  @1, @2 can be used for optional arguments.  $* simply
        means "all remaining arguments," and cannot be combined with optional
        arguments.
        """
        (name, alias) = privmsgs.getArgs(args, required=2)
        try:
            self.addAlias(irc, name, alias)
            irc.reply(msg, conf.replySuccess)
        except AliasError, e:
            irc.error(msg, str(e))

    def remove(self, irc, msg, args):
        """<name>

        Removes the given alias, if unlocked.
        """
        name = privmsgs.getArgs(args)
        try:
            self.removeAlias(name)
            irc.reply(msg, conf.replySuccess)
        except AliasError, e:
            irc.error(msg, str(e))


Class = Alias

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
