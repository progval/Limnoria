###
# Copyright (c) 2013, Valentin Lorentz
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
import os
import sys
import datetime

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization('Aka')

try:
    import sqlalchemy
    import sqlalchemy.ext
    import sqlalchemy.ext.declarative
except ImportError:
    raise callbacks.Error('You have to install python-sqlalchemy in order '
            'to load this plugin.')

if sqlalchemy:

    Base = sqlalchemy.ext.declarative.declarative_base()
    class Alias(Base):
        __tablename__ = 'aliases'

        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
        alias = sqlalchemy.Column(sqlalchemy.String, nullable=False)

        locked = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False)
        locked_by = sqlalchemy.Column(sqlalchemy.String, nullable=True)
        locked_at = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)

        def __init__(self, name, alias):
            self.name = name
            self.alias = alias
            self.locked = False
            self.locked_by = None
            self.locked_at = None
        def __repr__(self):
            return "<Alias('%r', '%r')>" % (self.name, self.alias)

    # TODO: Add table for usage statistics

    class SqlAlchemyAkaDB(object):
        def __init__(self, filename):
            self.engines = ircutils.IrcDict()
            self.filename = filename
            self.sqlalchemy = sqlalchemy

        def close(self):
            self.dbs.clear()

        def get_db(self, channel):
            if channel in self.engines:
                engine = self.engines[channel]
            else:
                filename = plugins.makeChannelFilename(self.filename, channel)
                exists = os.path.exists(filename)
                engine = sqlalchemy.create_engine('sqlite:///' + filename)
                if not exists:
                    Base.metadata.create_all(engine)
                self.engines[channel] = engine
            assert engine.execute("select 1").scalar() == 1
            Session = sqlalchemy.orm.sessionmaker()
            Session.configure(bind=engine)
            return Session()


        def has_aka(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if sys.version_info[0] < 3 and isinstance(name, str):
                name = name.decode('utf8')
            count = self.get_db(channel).query(Alias) \
                    .filter(Alias.name == name) \
                    .count()
            return bool(count)
        def get_aka_list(self, channel):
            list_ = list(self.get_db(channel).query(Alias.name))
            return list_

        def get_alias(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if sys.version_info[0] < 3 and isinstance(name, str):
                name = name.decode('utf8')
            try:
                return self.get_db(channel).query(Alias.alias) \
                        .filter(Alias.name == name).one()[0]
            except sqlalchemy.orm.exc.NoResultFound:
                return None

        def add_aka(self, channel, name, alias):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if self.has_aka(channel, name):
                raise AkaError(_('This Aka already exists.'))
            if sys.version_info[0] < 3:
                if isinstance(name, str):
                    name = name.decode('utf8')
                if isinstance(alias, str):
                    alias = alias.decode('utf8')
            db = self.get_db(channel)
            db.add(Alias(name, alias))
            db.commit()

        def remove_aka(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if sys.version_info[0] < 3 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            db.query(Alias).filter(Alias.name == name).delete()
            db.commit()

        def lock_aka(self, channel, name, by):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if sys.version_info[0] < 3 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            try:
                aka = db.query(Alias) \
                        .filter(Alias.name == name).one()
            except sqlalchemy.orm.exc.NoResultFound:
                raise AkaError(_('This Aka does not exist'))
            if aka.locked:
                raise AkaError(_('This Aka is already locked.'))
            aka.locked = True
            aka.locked_by = by
            aka.locked_at = datetime.datetime.now()
            db.commit()

        def unlock_aka(self, channel, name, by):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if sys.version_info[0] < 3 and isinstance(name, str):
                name = name.decode('utf8')
            db = self.get_db(channel)
            try:
                aka = db.query(Alias) \
                        .filter(Alias.name == name).one()
            except sqlalchemy.orm.exc.NoResultFound:
                raise AkaError(_('This Aka does not exist'))
            if not aka.locked:
                raise AkaError(_('This Aka is already unlocked.'))
            aka.locked = False
            aka.locked_by = by
            aka.locked_at = datetime.datetime.now()
            db.commit()

        def get_aka_lock(self, channel, name):
            name = callbacks.canonicalName(name, preserve_spaces=True)
            if sys.version_info[0] < 3 and isinstance(name, str):
                name = name.decode('utf8')
            try:
                return self.get_db(channel) \
                        .query(Alias.locked, Alias.locked_by, Alias.locked_at)\
                        .filter(Alias.name == name).one()
            except sqlalchemy.orm.exc.NoResultFound:
                raise AkaError(_('This Aka does not exist'))


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

class AkaError(Exception):
    pass

class RecursiveAlias(AkaError):
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

AkaDB = plugins.DB('Aka', {'sqlalchemy': SqlAlchemyAkaDB})

class Aka(callbacks.Plugin):
    """Add the help for "@plugin help Aka" here
    This should describe *how* to use this plugin."""

    def __init__(self, irc):
        self.__parent = super(Aka, self)
        self.__parent.__init__(irc)
        self._db = AkaDB()

    def isCommandMethod(self, name):
        args = name.split(' ')
        if '|' in args:
            return False
        if len(args) > 1 and \
                callbacks.canonicalName(args[0]) != self.canonicalName():
            for cb in dynamic.irc.callbacks: # including this plugin
                if cb.isCommandMethod(' '.join(args[0:-1])):
                    return False
        if sys.version_info[0] < 3 and isinstance(name, str):
            name = name.decode('utf8')
        channel = dynamic.channel or 'global'
        return self._db.has_aka(channel, name) or \
                self._db.has_aka('global', name) or \
                self.__parent.isCommandMethod(name)
    isCommand = isCommandMethod

    def listCommands(self):
        channel = dynamic.channel or 'global'
        return list(set(map(callbacks.formatCommand,
                            self._db.get_aka_list(channel) +
                            self._db.get_aka_list('global')) +
                ['add', 'remove', 'lock', 'unlock', 'importaliasdatabase']))

    def getCommand(self, args, check_other_plugins=True):
        canonicalName = callbacks.canonicalName
        # All the code from here to the 'for' loop is copied from callbacks.py
        assert args == map(canonicalName, args)
        first = args[0]
        for cb in self.cbs:
            if first == cb.canonicalName():
                return cb.getCommand(args[1:])
        if first == self.canonicalName() and len(args) > 1:
            ret = self.getCommand(args[1:], False)
            if ret:
                return [first] + ret
        for i in xrange(1, len(args)+1):
            if self.isCommandMethod(callbacks.formatCommand(args[0:i])):
                return args[0:i]
        return []

    def getCommandMethod(self, command):
        if len(command) == 1 or command[0] == self.canonicalName():
            try:
                return self.__parent.getCommandMethod(command)
            except AttributeError:
                pass
        name = callbacks.formatCommand(command)
        channel = dynamic.channel or 'global'
        original = self._db.get_alias(channel, name)
        if not original:
            original = self._db.get_alias('global', name)
        biggestDollar = findBiggestDollar(original)
        biggestAt = findBiggestAt(original)
        wildcard = '$*' in original
        def f(irc, msg, args):
            tokens = callbacks.tokenize(original)
            if biggestDollar or biggestAt:
                args = getArgs(args, required=biggestDollar, optional=biggestAt,
                                wildcard=wildcard)
            max_len = conf.supybot.reply.maximumLength()
            args = list(map(lambda x:x[:max_len], args))
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
            maxNesting = conf.supybot.commands.nested.maximum()
            if maxNesting and irc.nested+1 > maxNesting:
                irc.error(_('You\'ve attempted more nesting than is '
                      'currently allowed on this bot.'), Raise=True)
            self.Proxy(irc, msg, tokens)
        if biggestDollar and (wildcard or biggestAt):
            flexargs = _(' at least')
        else:
            flexargs = ''
        try:
            lock = self._db.get_aka_lock(channel, name)
        except AkaError:
            lock = self._db.get_aka_lock('global', name)
        (locked, locked_by, locked_at) = lock
        if locked:
            lock = ' ' + _('Locked by %s at %s') % (locked_by, locked_at)
        else:
            lock = ''
        doc = format(_('<an alias,%s %n>\n\nAlias for %q.%s'),
                    flexargs, (biggestDollar, _('argument')), original, lock)
        f = utils.python.changeFunctionName(f, name, doc)
        return f

    def _add_aka(self, channel, name, alias):
        if self.__parent.isCommandMethod(name):
            raise AkaError(_('You can\'t overwrite commands in '
                    'this plugin.'))
        if self._db.has_aka(channel, name):
            raise AkaError(_('This Aka already exists.'))
        biggestDollar = findBiggestDollar(alias)
        biggestAt = findBiggestAt(alias)
        wildcard = '$*' in alias
        if biggestAt and wildcard:
            raise AkaError(_('Can\'t mix $* and optional args (@1, etc.)'))
        if alias.count('$*') > 1:
            raise AkaError(_('There can be only one $* in an alias.'))
        self._db.add_aka(channel, name, alias)

    def _remove_aka(self, channel, name, evenIfLocked=False):
        if not evenIfLocked:
            (locked, by, at) = self._db.get_aka_lock(channel, name)
            if locked:
                raise AkaError(_('This Aka is locked.'))
        self._db.remove_aka(channel, name)

    def add(self, irc, msg, args, optlist, name, alias):
        """[--channel <#channel>] <name> <command>

        Defines an alias <name> that executes <command>.  The <command>
        should be in the standard "command argument [nestedcommand argument]"
        arguments to the alias; they'll be filled with the first, second, etc.
        arguments.  $1, $2, etc. can be used for required arguments.  @1, @2,
        etc. can be used for optional arguments.  $* simply means "all
        arguments that have not replaced $1, $2, etc.", ie. it will also
        include optional arguments.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not ircutils.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        if ' ' not in alias:
            # If it's a single word, they probably want $*.
            alias += ' $*'
        try:
            self._add_aka(channel, name, alias)
            self.log.info('Adding Aka %r for %r (from %s)',
                          name, alias, msg.prefix)
            irc.replySuccess()
        except AkaError as e:
            irc.error(str(e))
    add = wrap(add, [getopts({
                                'channel': 'somethingWithoutSpaces',
                            }), 'something', 'text'])

    def remove(self, irc, msg, args, optlist, name):
        """[--channel <#channel>] <name>

        Removes the given alias, if unlocked.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not ircutils.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        try:
            self._remove_aka(channel, name)
            self.log.info('Removing Aka %r (from %s)', name, msg.prefix)
            irc.replySuccess()
        except AkaError as e:
            irc.error(str(e))
    remove = wrap(remove, [getopts({
                                'channel': 'somethingWithoutSpaces',
                            }), 'something'])

    def _checkManageCapabilities(self, irc, msg, channel):
        """Check if the user has any of the required capabilities to manage
        the regexp database."""
        if channel != 'global':
            capability = ircdb.makeChannelCapability(channel, 'op')
        else:
            capability = 'admin'
        if not ircdb.checkCapability(msg.prefix, capability):
            irc.errorNoCapability(capability, Raise=True)

    def lock(self, irc, msg, args, optlist, user, name):
        """[--channel <#channel>] <alias>

        Locks an alias so that no one else can change it.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not ircutils.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        self._checkManageCapabilities(irc, msg, channel)
        try:
            self._db.lock_aka(channel, name, user.name)
        except AkaError as e:
            irc.error(str(e))
        else:
            irc.replySuccess()
    lock = wrap(lock, [getopts({
                                'channel': 'somethingWithoutSpaces',
                            }), 'user', 'something'])

    def unlock(self, irc, msg, args, optlist, user, name):
        """[--channel <#channel>] <alias>

        Unlocks an alias so that people can define new aliases over it.
        """
        channel = 'global'
        for (option, arg) in optlist:
            if option == 'channel':
                if not ircutils.isChannel(arg):
                    irc.error(_('%r is not a valid channel.') % arg,
                            Raise=True)
                channel = arg
        self._checkManageCapabilities(irc, msg, channel)
        try:
            self._db.unlock_aka(channel, name, user.name)
        except AkaError as e:
            irc.error(str(e))
        else:
            irc.replySuccess()
    unlock = wrap(unlock, [getopts({
                                'channel': 'somethingWithoutSpaces',
                            }), 'user', 'something'])

    def importaliasdatabase(self, irc, msg, args):
        """takes no arguments

        Imports the Alias database into Aka's, and clean the former."""
        alias_plugin = irc.getCallback('Alias')
        if alias_plugin is None:
            irc.error(_('Alias plugin is not loaded.'), Raise=True)
        errors = {}
        for (name, (command, locked, func)) in alias_plugin.aliases.items():
            try:
                self._add_aka('global', name, command)
            except AkaError as e:
                errors[name] = e.args[0]
            else:
                alias_plugin.removeAlias(name, evenIfLocked=True)
        if errors:
            irc.error(format(_('Error occured when importing the %n: %L'),
                (len(errors), 'following', 'command'),
                map(lambda x:'%s (%s)' % x, errors.items())))
        else:
            irc.replySuccess()
    importaliasdatabase = wrap(importaliasdatabase, ['owner'])


Class = Aka


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
