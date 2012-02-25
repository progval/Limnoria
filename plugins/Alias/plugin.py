###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009-2010, James Vega
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
import new

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Alias')

# Copied from the old privmsgs.py.
def getChannel(msg, args=()):
    """Returns the channel the msg came over or the channel given in args.

    If the channel was given in args, args is modified (the channel is
    removed).
    """
    if args and ircutils.isChannel(args[0]):
        if conf.supybot.reply.requireChannelCommandsToBeSentInChannel():
            if args[0] != msg.args[0]:
                s = 'Channel commands must be sent in the channel to which ' \
                    'they apply; if this is not the behavior you desire, ' \
                    'ask the bot\'s administrator to change the registry ' \
                    'variable ' \
                    'supybot.reply.requireChannelCommandsToBeSentInChannel ' \
                    'to False.'
                raise callbacks.Error, s
        return args.pop(0)
    elif ircutils.isChannel(msg.args[0]):
        return msg.args[0]
    else:
        raise callbacks.Error, 'Command must be sent in a channel or ' \
                               'include a channel in its arguments.'

def getArgs(args, required=1, optional=0, wildcard=0):
    if len(args) < required:
        raise callbacks.ArgumentError
    if len(args) < required + optional:
        ret = list(args) + ([''] * (required + optional - len(args)))
    elif len(args) >= required + optional:
        if not wildcard:
            ret = list(args[:required + optional - 1])
            ret.append(' '.join(args[required + optional - 1:]))
        else:
            ret = list(args)
    return ret

class AliasError(Exception):
    pass

class RecursiveAlias(AliasError):
    pass

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
            channel = getChannel(msg, args)
            alias = alias.replace('$channel', channel)
        tokens = callbacks.tokenize(alias)
        if biggestDollar or biggestAt:
            args = getArgs(args, required=biggestDollar, optional=biggestAt,
                            wildcard=wildcard)
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
        self.Proxy(irc, msg, tokens)
    flexargs = ''
    if biggestDollar and (wildcard or biggestAt):
        flexargs = _(' at least')
    doc =format(_('<an alias,%s %n>\n\nAlias for %q.'),
                flexargs, (biggestDollar, _('argument')), alias)
    f = utils.python.changeFunctionName(f, name, doc)
    return f

class Alias(callbacks.Plugin):
    def __init__(self, irc):
        self.__parent = super(Alias, self)
        self.__parent.__init__(irc)
        # Schema: {alias: [command, locked, commandMethod]}
        self.aliases = {}
        # XXX This should go.  aliases should be a space separate list, etc.
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
            self.aliases[name] = [command, locked, None]
        for (alias, (command, locked, _)) in self.aliases.items():
            try:
                self.addAlias(irc, alias, command, locked)
            except Exception, e:
                self.log.exception('Exception when trying to add alias %s.  '
                                   'Removing from the Alias database.', alias)
                del self.aliases[alias]

    def isCommandMethod(self, name):
        if not self.__parent.isCommandMethod(name):
            if name in self.aliases:
                return True
            else:
                return False
        else:
            return True

    def listCommands(self):
        return self.__parent.listCommands(self.aliases.keys())

    def getCommandMethod(self, command):
        try:
            return self.__parent.getCommandMethod(command)
        except AttributeError:
            return self.aliases[command[0]][2]

    @internationalizeDocstring
    def lock(self, irc, msg, args, name):
        """<alias>

        Locks an alias so that no one else can change it.
        """
        if name in self.aliases and self.isCommandMethod(name):
            self.aliases[name][1] = True
            conf.supybot.plugins.Alias.aliases.get(name).locked.setValue(True)
            irc.replySuccess()
        else:
            irc.error(_('There is no such alias.'))
    lock = wrap(lock, [('checkCapability', 'admin'), 'commandName'])

    @internationalizeDocstring
    def unlock(self, irc, msg, args, name):
        """<alias>

        Unlocks an alias so that people can define new aliases over it.
        """
        if name in self.aliases and self.isCommandMethod(name):
            self.aliases[name][1] = False
            conf.supybot.plugins.Alias.aliases.get(name).locked.setValue(False)
            irc.replySuccess()
        else:
            irc.error(_('There is no such alias.'))
    unlock = wrap(unlock, [('checkCapability', 'admin'), 'commandName'])

    _invalidCharsRe = re.compile(r'[\[\]\s]')
    def addAlias(self, irc, name, alias, lock=False):
        if self._invalidCharsRe.search(name):
            raise AliasError, 'Names cannot contain spaces or square brackets.'
        if '|' in name:
            raise AliasError, 'Names cannot contain pipes.'
        realName = callbacks.canonicalName(name)
        if name != realName:
            s = format(_('That name isn\'t valid.  Try %q instead.'), realName)
            raise AliasError, s
        name = realName
        if self.isCommandMethod(name):
            if realName not in self.aliases:
                s = 'You can\'t overwrite commands in this plugin.'
                raise AliasError, s
        if name in self.aliases:
            (currentAlias, locked, _) = self.aliases[name]
            if locked and currentAlias != alias:
                raise AliasError, format('Alias %q is locked.', name)
        try:
            f = makeNewAlias(name, alias)
            f = new.instancemethod(f, self, Alias)
        except RecursiveAlias:
            raise AliasError, 'You can\'t define a recursive alias.'
        aliasGroup = self.registryValue('aliases', value=False)
        if name in self.aliases:
            # We gotta remove it so its value gets updated.
            aliasGroup.unregister(name)
        conf.registerGlobalValue(aliasGroup, name, registry.String(alias, ''))
        conf.registerGlobalValue(aliasGroup.get(name), 'locked',
                                 registry.Boolean(lock, ''))
        self.aliases[name] = [alias, lock, f]

    def removeAlias(self, name, evenIfLocked=False):
        name = callbacks.canonicalName(name)
        if name in self.aliases and self.isCommandMethod(name):
            if evenIfLocked or not self.aliases[name][1]:
                del self.aliases[name]
                conf.supybot.plugins.Alias.aliases.unregister(name)
            else:
                raise AliasError, 'That alias is locked.'
        else:
            raise AliasError, 'There is no such alias.'

    @internationalizeDocstring
    def add(self, irc, msg, args, name, alias):
        """<name> <command>

        Defines an alias <name> that executes <command>.  The <command>
        should be in the standard "command argument [nestedcommand argument]"
        arguments to the alias; they'll be filled with the first, second, etc.
        arguments.  $1, $2, etc. can be used for required arguments.  @1, @2,
        etc. can be used for optional arguments.  $* simply means "all
        remaining arguments," and cannot be combined with optional arguments.
        """
        if ' ' not in alias:
            # If it's a single word, they probably want $*.
            alias += ' $*'
        try:
            self.addAlias(irc, name, alias)
            self.log.info('Adding alias %q for %q (from %s)',
                          name, alias, msg.prefix)
            irc.replySuccess()
        except AliasError, e:
            irc.error(str(e))
    add = wrap(add, ['commandName', 'text'])

    @internationalizeDocstring
    def remove(self, irc, msg, args, name):
        """<name>

        Removes the given alias, if unlocked.
        """
        try:
            self.removeAlias(name)
            self.log.info('Removing alias %q (from %s)', name, msg.prefix)
            irc.replySuccess()
        except AliasError, e:
            irc.error(str(e))
    remove = wrap(remove, ['commandName'])


Class = Alias

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
