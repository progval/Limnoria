###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2014, James McCoy
# Copyright (c) 2012-2021, Valentin Lorentz
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
import sys
import types

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Alias')

# Copied from the old privmsgs.py.
def getChannel(irc, msg, args):
    """Returns the channel the msg came over or the channel given in args.

    If the channel was given in args, args is modified (the channel is
    removed).
    """
    if args and msg.channel:
        if conf.supybot.reply.requireChannelCommandsToBeSentInChannel():
            if args[0] != msg.channel:
                s = 'Channel commands must be sent in the channel to which ' \
                    'they apply; if this is not the behavior you desire, ' \
                    'ask the bot\'s administrator to change the registry ' \
                    'variable ' \
                    'supybot.reply.requireChannelCommandsToBeSentInChannel ' \
                    'to False.'
                raise callbacks.Error(s)
        return args.pop(0)
    elif msg.channel:
        return msg.channel
    else:
        raise callbacks.Error('Command must be sent in a channel or ' \
                               'include a channel in its arguments.')

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

dollarRe = re.compile(r'\$(\d+)')
def findBiggestDollar(alias):
    dollars = dollarRe.findall(alias)
    dollars = list(map(int, dollars))
    dollars.sort()
    if dollars:
        return dollars[-1]
    else:
        return 0

atRe = re.compile(r'@(\d+)')
def findBiggestAt(alias):
    ats = atRe.findall(alias)
    ats = list(map(int, ats))
    ats.sort()
    if ats:
        return ats[-1]
    else:
        return 0

def needsEscaping(alias):
    return '.' in alias or '|' in alias

def escapeAlias(alias):
    """Encodes dots and pipes
    Format: a<number of escaped chars>a(<index>(d|p))+<word without dots or pipes>."""
    prefix = ''
    new_alias = ''
    prefixes = 0
    for index, char in enumerate(alias):
        if char == '.':
            prefix += '%sd' % index
            prefixes += 1
        elif char == '|':
            prefix += '%sp' % index
            prefixes += 1
        else:
            new_alias += char
    pre_prefix = 'a%ia' % prefixes
    return pre_prefix + prefix + new_alias

def unescapeAlias(alias):
    alias = alias[1:] # Strip the leading 'a'
    escaped_nb = ''
    while alias[0] in '0123456789':
        escaped_nb += alias[0]
        alias = alias[1:]
    alias = alias[1:]
    escaped_nb = int(escaped_nb)
    escaped_chars = []
    while alias[0] in '0123456789':
        current_group = ''
        while alias[0] in '0123456789':
            current_group += alias[0]
            alias = alias[1:]
        if alias[0] == 'd':
            char = '.'
        elif alias[0] == 'p':
            char = '|'
        else:
            char = alias[0]
        alias = alias[1:]
        escaped_chars.append((int(current_group), char))
        if len(escaped_chars) == escaped_nb:
            break
    new_alias = ''
    index = 0
    for char in alias:
        if escaped_chars and index == escaped_chars[0][0]:
            new_alias += escaped_chars[0][1]
            escaped_chars.pop(0)
            index += 1
        new_alias += char
        index += 1
    return new_alias

def makeNewAlias(name, alias):
    original = alias
    biggestDollar = findBiggestDollar(original)
    biggestAt = findBiggestAt(original)
    wildcard = '$*' in original
    if biggestAt and wildcard:
        raise AliasError('Can\'t mix $* and optional args (@1, etc.)')
    if original.count('$*') > 1:
        raise AliasError('There can be only one $* in an alias.')
    testTokens = callbacks.tokenize(original)
    if testTokens and isinstance(testTokens[0], list):
        raise AliasError('Commands may not be the result of nesting.')
    def f(self, irc, msg, args):
        alias = original.replace('$nick', msg.nick)
        if '$channel' in original:
            channel = getChannel(irc, msg, args)
            alias = alias.replace('$channel', channel)
        tokens = callbacks.tokenize(alias)
        if biggestDollar or biggestAt:
            args = getArgs(args, required=biggestDollar, optional=biggestAt,
                            wildcard=wildcard)
        max_len = conf.supybot.reply.maximumLength()
        args = list([x[:max_len] for x in args])
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
        # Limit memory use by constraining the size of the message being passed
        # in to the alias.  Also tracking nesting to avoid endless recursion.
        maxLength = conf.supybot.reply.maximumLength()
        tokens = [t[:maxLength] for t in tokens]
        self.Proxy(irc, msg, tokens, nested=irc.nested + 1)
    flexargs = ''
    if biggestDollar and (wildcard or biggestAt):
        flexargs = _(' at least')
    try:
        doc = format(_('<an alias,%s %n>\n\nAlias for %q.'),
                    flexargs, (biggestDollar, _('argument')), alias)
    except UnicodeDecodeError:
        if minisix.PY2:
            alias = alias.decode('utf8')
        doc = format(_('<an alias,%s %n>\n\nAlias for %q.'),
                    flexargs, (biggestDollar, _('argument')), alias)
    f = utils.python.changeFunctionName(f, name, doc)
    return f

class Alias(callbacks.Plugin):
    """
    This plugin allows users to define aliases to commands and combinations
    of commands (via nesting).
    This plugin is only kept for backward compatibility, you should use the
    built-in Aka plugin instead (you can migrate your existing aliases using
    the 'importaliasdatabase' command.

    To add an alias, ``trout``, which expects a word as an argument::

        <jamessan> @alias add trout "action slaps $1 with a large trout"
        <bot> jamessan: The operation succeeded.
        <jamessan> @trout me
        * bot slaps me with a large trout

    Add an alias, ``randpercent``, which returns a random percentage value::

        @alias add randpercent "squish [dice 1d100]%"

    This requires the ``Filter`` and ``Games`` plugins to be loaded.

    Note that nested commands in an alias should be quoted, or they will only
    run once when you create the alias, and not each time the alias is
    called. (In this case, not quoting the nested command would mean that
    ``@randpercent`` always responds with the same value!)
    """
    def __init__(self, irc):
        self.__parent = super(Alias, self)
        self.__parent.__init__(irc)
        # Schema: {alias: [command, locked, commandMethod]}
        self.aliases = {}
        # XXX This should go.  aliases should be a space separate list, etc.
        group = conf.supybot.plugins.Alias.aliases
        group2 = conf.supybot.plugins.Alias.escapedaliases
        prefixLen = len(registry.split('supybot.plugins.alias.aliases'))
        for (name, alias) in registry._cache.items():
            name = name.lower()
            nameSplit = registry.split(name)
            if len(nameSplit) > prefixLen+1:
                continue
            if name.startswith('supybot.plugins.alias.aliases.'):
                name = nameSplit[-1]
                conf.registerGlobalValue(group, name, registry.String('', ''))
                conf.registerGlobalValue(group.get(name), 'locked',
                                         registry.Boolean(False, ''))
            elif name.startswith('supybot.plugins.alias.escapedaliases.'):
                name = nameSplit[-1]
                conf.registerGlobalValue(group2, name,
                        registry.String('', ''))
                conf.registerGlobalValue(group2.get(name),
                    'locked', registry.Boolean(False, ''))
        for (name, value) in group.getValues(fullNames=False):
            name = name.lower() # Just in case.
            command = value()
            locked = value.locked()
            self.aliases[name] = [command, locked, None]
        for (name, value) in group2.getValues(fullNames=False):
            name = name.lower() # Just in case.
            command = value()
            locked = value.locked()
            self.aliases[unescapeAlias(name)] = [command, locked, None]
        for (alias, (command, locked, _)) in self.aliases.copy().items():
            try:
                self.addAlias(irc, alias, command, locked)
            except Exception as e:
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

    def aliasRegistryGroup(self, name):
        if needsEscaping(name):
            return self.registryValue('escapedaliases', value=False)
        else:
            return self.registryValue('aliases', value=False)

    def aliasRegistryNode(self, name):
        group = self.aliasRegistryGroup(name)
        if needsEscaping(name):
            return group.get(escapeAlias(name))
        else:
            return group.get(name)

    def aliasRegistryRemove(self, name):
        group = self.aliasRegistryGroup(name)
        if needsEscaping(name):
            group.unregister(escapeAlias(name))
        else:
            group.unregister(name)


    def setLocked(self, name, value):
        self.aliases[name][1] = value
        self.aliasRegistryNode(name).locked.setValue(value)

    def isValidName(self, name):
        if not re.search(self.registryValue('validName'), name):
            return False
        if not registry.isValidRegistryName(name):
            return False
        return True

    @internationalizeDocstring
    def lock(self, irc, msg, args, name):
        """<alias>

        Locks an alias so that no one else can change it.
        """
        if name in self.aliases and self.isCommandMethod(name):
            self.setLocked(name, True)
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
            self.setLocked(name, False)
            irc.replySuccess()
        else:
            irc.error(_('There is no such alias.'))
    unlock = wrap(unlock, [('checkCapability', 'admin'), 'commandName'])

    def addAlias(self, irc, name, alias, lock=False):
        if not self.isValidName(name):
            raise AliasError('Invalid alias name.')
        realName = callbacks.canonicalName(name)
        if name != realName:
            s = format(_('That name isn\'t valid.  Try %q instead.'), realName)
            raise AliasError(s)
        name = realName
        if self.isCommandMethod(name):
            if realName not in self.aliases:
                s = 'You can\'t overwrite commands in this plugin.'
                raise AliasError(s)
        if name in self.aliases:
            (currentAlias, locked, _) = self.aliases[name]
            if locked and currentAlias != alias:
                raise AliasError(format('Alias %q is locked.', name))
        f = makeNewAlias(name, alias)
        f = types.MethodType(f, self)
        if name in self.aliases:
            # We gotta remove it so its value gets updated.
            self.aliasRegistryRemove(name)
        aliasGroup = self.aliasRegistryGroup(name)
        if needsEscaping(name):
            confname = escapeAlias(name)
        else:
            confname = name
        conf.registerGlobalValue(aliasGroup, confname,
                                 registry.String(alias, ''))
        conf.registerGlobalValue(aliasGroup.get(confname), 'locked',
                                 registry.Boolean(lock, ''))
        self.aliases[name] = [alias, lock, f]

    def removeAlias(self, name, evenIfLocked=False):
        name = callbacks.canonicalName(name)
        if name in self.aliases and self.isCommandMethod(name):
            if evenIfLocked or not self.aliases[name][1]:
                del self.aliases[name]
                self.aliasRegistryRemove(name)
            else:
                raise AliasError('That alias is locked.')
        else:
            raise AliasError('There is no such alias.')

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
        except AliasError as e:
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
        except AliasError as e:
            irc.error(str(e))
    remove = wrap(remove, ['commandName'])

    @internationalizeDocstring
    def list(self, irc, msg, args, optlist):
        """[--locked|--unlocked]

        Lists alias names of a particular type, defaults to all aliases if no
        --locked or --unlocked option is given.
        """
        optlist = dict(optlist)
        if len(optlist)>1:
            irc.error(_('Cannot specify --locked and --unlocked simultaneously'))
            return
        aliases = []
        for name in self.aliases.keys():
            if self.isCommandMethod(name):
                if 'locked' in optlist:
                    if self.aliases[name][1]: aliases.append(name)
                elif 'unlocked' in optlist:
                    if not self.aliases[name][1]: aliases.append(name)
                else:
                    aliases.append(name)
        if aliases:
            aliases.sort()
            irc.reply(format('%L', aliases))
        else:
            if len(optlist):
                irc.reply(_('There are no aliases of that type.'))
            else:
                irc.reply(_('There are no aliases.'))
    list = wrap(list, [getopts({'locked':'', 'unlocked':''})])


Class = Alias

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
