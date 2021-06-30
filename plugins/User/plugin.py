###
# Copyright (c) 2002-2005, Jeremiah Fincher
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
import fnmatch

import supybot.conf as conf
import supybot.gpg as gpg
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('User')

class User(callbacks.Plugin):
    """Provides commands for dealing with users, such as registration and
    authentication to the bot. This is a core Supybot plugin that should
    not be removed!"""
    def _checkNotChannel(self, irc, msg, password=' '):
        if password and msg.channel:
            raise callbacks.Error(conf.supybot.replies.requiresPrivacy())

    @internationalizeDocstring
    def list(self, irc, msg, args, optlist, glob):
        """[--capability=<capability>] [<glob>]

        Returns the valid registered usernames matching <glob>.  If <glob> is
        not given, returns all registered usernames.
        """
        predicates = []
        for (option, arg) in optlist:
            if option == 'capability':
                if arg in conf.supybot.capabilities.private():
                    try:
                        u = ircdb.users.getUser(msg.prefix)
                        if not u._checkCapability('admin'):
                            raise KeyError
                    except KeyError:
                        # Note that it may be raised by checkCapability too.
                        irc.error(_('This is a private capability. Only admins '
                            'can see who has it.'), Raise=True)
                def p(u, cap=arg):
                    try:
                        return u._checkCapability(cap)
                    except KeyError:
                        return False
                predicates.append(p)
        if glob:
            r = re.compile(fnmatch.translate(glob), re.I)
            def p(u):
                return r.match(u.name) is not None
            predicates.append(p)
        users = []
        for u in ircdb.users.values():
            for predicate in predicates:
                if not predicate(u):
                    break
            else:
                users.append(u.name)
        if users:
            utils.sortBy(str.lower, users)
            private = self.registryValue("listInPrivate",
                                         msg.channel, irc.network)
            irc.reply(format('%L', users), private=private)
        else:
            if predicates:
                irc.reply(_('There are no matching registered users.'))
            else:
                irc.reply(_('There are no registered users.'))
    list = wrap(list, [getopts({'capability':'capability'}),
                       additional('glob')])

    @internationalizeDocstring
    def register(self, irc, msg, args, name, password):
        """<name> <password>

        Registers <name> with the given password <password> and the current
        hostmask of the person registering.  You shouldn't register twice; if
        you're not recognized as a user but you've already registered, use the
        hostmask add command to add another hostmask to your already-registered
        user, or use the identify command to identify just for a session.
        This command (and all other commands that include a password) must be
        sent to the bot privately, not in a channel.
        Use "!" instead of <password> to disable password authentication.
        """
        addHostmask = True
        try:
            ircdb.users.getUserId(name)
            irc.error(_('That name is already assigned to someone.'),
                      Raise=True)
        except KeyError:
            pass
        if ircutils.isUserHostmask(name):
            irc.errorInvalid(_('username'), name,
                             _('Hostmasks are not valid usernames.'),
                             Raise=True)
        try:
            u = ircdb.users.getUser(msg.prefix)
            if u._checkCapability('owner'):
                addHostmask = False
            else:
                irc.error(_('Your hostmask is already registered to %s') %
                          u.name)
                return
        except KeyError:
            pass

        if password == "!":
            password = None
        elif len(password) < 3:
            irc.error(_('The password must be at least 3 characters long.'),
                    Raise=True)

        user = ircdb.users.newUser()
        user.name = name
        if password:
            user.setPassword(password)
        if addHostmask:
            user.addHostmask(msg.prefix)
            account = msg.server_tags.get('account')
            if account:
                user.addNick(irc.network, account)
        ircdb.users.setUser(user)
        irc.replySuccess()
    register = wrap(register, ['private', 'something', 'something'])

    @internationalizeDocstring
    def unregister(self, irc, msg, args, user, password):
        """<name> [<password>]

        Unregisters <name> from the user database.  If the user giving this
        command is an owner user, the password is not necessary.
        """
        try:
            caller = ircdb.users.getUser(msg.prefix)
            isOwner = caller._checkCapability('owner')
        except KeyError:
            caller = None
            isOwner = False
        if not conf.supybot.databases.users.allowUnregistration():
            if not caller or not isOwner:
                self.log.warning('%s tried to unregister user %s.',
                                 msg.prefix, user.name)
                irc.error(_('This command has been disabled.  You\'ll have to '
                          'ask the owner of this bot to unregister your '
                          'user.'), Raise=True)
        if isOwner or user.checkPassword(password):
            ircdb.users.delUser(user.id)
            irc.replySuccess()
        else:
            irc.error(conf.supybot.replies.incorrectAuthentication())
    unregister = wrap(unregister, ['private', 'otherUser',
                                   additional('anything')])

    @internationalizeDocstring
    def changename(self, irc, msg, args, user, newname, password):
        """<name> <new name> [<password>]

        Changes your current user database name to the new name given.
        <password> is only necessary if the user isn't recognized by hostmask.
        This message must be sent to the bot privately (not on a channel) since
        it may contain a password.
        """
        try:
            id = ircdb.users.getUserId(newname)
            irc.error(format(_('%q is already registered.'), newname))
            return
        except KeyError:
            pass
        if user.checkHostmask(msg.prefix) or user.checkPassword(password):
            user.name = newname
            ircdb.users.setUser(user)
            irc.replySuccess()
    changename = wrap(changename, ['private', 'otherUser', 'something',
                                   additional('something', '')])

    class set(callbacks.Commands):
        @internationalizeDocstring
        def password(self, irc, msg, args, user, password, newpassword):
            """[<name>] <old password> <new password>

            Sets the new password for the user specified by <name> to <new
            password>. Obviously this message must be sent to the bot
            privately (not in a channel). If the requesting user is an owner
            user, then <old password> needn't be correct.
            If the <new password> is "!", password login will be disabled.
            """
            if password == "!":
                password = None
            elif len(password) < 3:
                irc.error(_('The password must be at least 3 characters long.'),
                        Raise=True)

            try:
                u = ircdb.users.getUser(msg.prefix)
            except KeyError:
                u = None
            if user is None:
                if u is None:
                    irc.errorNotRegistered(Raise=True)
                user = u
            if user.checkPassword(password) or \
               (u and u._checkCapability('owner')):
                user.setPassword(newpassword)
                ircdb.users.setUser(user)
                irc.replySuccess()
            else:
                irc.error(conf.supybot.replies.incorrectAuthentication())
        password = wrap(password, ['private', optional('otherUser'),
                                   'something', 'something'])

        @internationalizeDocstring
        def secure(self, irc, msg, args, user, password, value):
            """<password> [<True|False>]

            Sets the secure flag on the user of the person sending the message.
            Requires that the person's hostmask be in the list of hostmasks for
            that user in addition to the password being correct.  When the
            secure flag is set, the user *must* identify before they can be
            recognized.  If a specific True/False value is not given, it
            inverts the current value.
            """
            if value is None:
                value = not user.secure
            if user.checkPassword(password) and \
               user.checkHostmask(msg.prefix, useAuth=False):
                user.secure = value
                ircdb.users.setUser(user)
                irc.reply(_('Secure flag set to %s') % value)
            else:
                irc.error(conf.supybot.replies.incorrectAuthentication())
        secure = wrap(secure, ['private', 'user', 'something',
                               additional('boolean')])

    @internationalizeDocstring
    def username(self, irc, msg, args, hostmask):
        """<hostmask|nick>

        Returns the username of the user specified by <hostmask> or <nick> if
        the user is registered.
        """
        if ircutils.isNick(hostmask):
            try:
                hostmask = irc.state.nickToHostmask(hostmask)
            except KeyError:
                irc.error(_('I haven\'t seen %s.') % hostmask, Raise=True)
        try:
            user = ircdb.users.getUser(hostmask)
            irc.reply(user.name)
        except KeyError:
            irc.error(_('I don\'t know who that is.'))
    username = wrap(username, [first('nick', 'hostmask')])

    class hostmask(callbacks.Commands):
        @internationalizeDocstring
        def hostmask(self, irc, msg, args, nick):
            """[<nick>]

            Returns the hostmask of <nick>.  If <nick> isn't given, return the
            hostmask of the person giving the command.
            """
            if not nick:
                nick = msg.nick
            irc.reply(irc.state.nickToHostmask(nick))
        hostmask = wrap(hostmask, [additional('seenNick')])

        @internationalizeDocstring
        def list(self, irc, msg, args, name):
            """[<name>]

            Returns the hostmasks of the user specified by <name>; if <name>
            isn't specified, returns the hostmasks of the user calling the
            command.
            """
            def getHostmasks(user):
                hostmasks = list(map(repr, user.hostmasks))
                if hostmasks:
                    hostmasks.sort()
                    return format('%L', hostmasks)
                else:
                    return format(_('%s has no registered hostmasks.'),
                                  user.name)
            try:
                user = ircdb.users.getUser(msg.prefix)
                if name:
                    if name != user.name and \
                       not ircdb.checkCapability(msg.prefix, 'owner'):
                        irc.error(_('You may only retrieve your own '
                                  'hostmasks.'), Raise=True)
                    else:
                        try:
                            user = ircdb.users.getUser(name)
                            irc.reply(getHostmasks(user), private=True)
                        except KeyError:
                            irc.errorNoUser()
                else:
                    irc.reply(getHostmasks(user), private=True)
            except KeyError:
                irc.errorNotRegistered()
        list = wrap(list, [additional('something')])

        @internationalizeDocstring
        def add(self, irc, msg, args, user, hostmask, password):
            """[<name>] [<hostmask>] [<password>]

            Adds the hostmask <hostmask> to the user specified by <name>.  The
            <password> may only be required if the user is not recognized by
            hostmask.  <password> is also not required if an owner user is
            giving the command on behalf of some other user.  If <hostmask> is
            not given, it defaults to your current hostmask.  If <name> is not
            given, it defaults to your currently identified name.  This message
            must be sent to the bot privately (not on a channel) since it may
            contain a password.
            """
            caller_is_owner = ircdb.checkCapability(msg.prefix, 'owner')
            if not hostmask:
                hostmask = msg.prefix
            if not ircutils.isUserHostmask(hostmask):
                irc.errorInvalid(_('hostmask'), hostmask,
                                 _('Make sure your hostmask includes a nick, '
                                 'then an exclamation point (!), then a user, '
                                 'then an at symbol (@), then a host.  Feel '
                                 'free to use wildcards (* and ?, which work '
                                 'just like they do on the command line) in '
                                 'any of these parts.'),
                                 Raise=True)
            try:
                otherId = ircdb.users.getUserId(hostmask)
                if otherId != user.id:
                    if caller_is_owner:
                        err = _('That hostmask is already registered to %s.')
                        err %= otherId
                    else:
                        err = _('That hostmask is already registered.')
                    irc.error(err, Raise=True)
            except KeyError:
                pass
            if not user.checkPassword(password) and \
               not user.checkHostmask(msg.prefix) and \
               not caller_is_owner:
                    irc.error(conf.supybot.replies.incorrectAuthentication(),
                              Raise=True)
            try:
                user.addHostmask(hostmask)
            except ValueError as e:
                irc.error(str(e), Raise=True)
            try:
                ircdb.users.setUser(user)
            except ircdb.DuplicateHostmask as e:
                user.removeHostmask(hostmask)
                if caller_is_owner:
                    err = _('That hostmask is already registered to %s.') \
                              % e.args[0]
                else:
                    err = _('That hostmask is already registered.')
                irc.error(err, Raise=True)
            except ValueError as e:
                irc.error(str(e), Raise=True)
            irc.replySuccess()
        add = wrap(add, ['private', first('otherUser', 'user'),
                         optional('something'), additional('something', '')])

        @internationalizeDocstring
        def remove(self, irc, msg, args, user, hostmask, password):
            """[<name>] [<hostmask>] [<password>]

            Removes the hostmask <hostmask> from the record of the user
            specified by <name>.  If the hostmask given is 'all' then all
            hostmasks will be removed.  The <password> may only be required if
            the user is not recognized by their hostmask.  This message must be
            sent to the bot privately (not on a channel) since it may contain a
            password.  If <hostmask> is
            not given, it defaults to your current hostmask.  If <name> is not
            given, it defaults to your currently identified name.
            """
            if not hostmask:
                hostmask = msg.prefix
            if not user.checkPassword(password) and \
               not user.checkHostmask(msg.prefix):
                if not ircdb.checkCapability(msg.prefix, 'owner'):
                    irc.error(conf.supybot.replies.incorrectAuthentication())
                    return
            try:
                s = ''
                if hostmask == 'all':
                    user.hostmasks.clear()
                    s = _('All hostmasks removed.')
                else:
                    user.removeHostmask(hostmask)
            except KeyError:
                irc.error(_('There was no such hostmask.'))
                return
            ircdb.users.setUser(user)
            irc.replySuccess(s)
        remove = wrap(remove, ['private', first('otherUser', 'user'),
                               optional('something'), additional('something', '')])

    def callCommand(self, command, irc, msg, *args, **kwargs):
        if command[0] != 'gpg' or \
                (gpg.available and self.registryValue('gpg.enable')):
            return super(User, self) \
                    .callCommand(command, irc, msg, *args, **kwargs)
        else:
            irc.error(_('GPG features are not enabled.'))


    @internationalizeDocstring
    def capabilities(self, irc, msg, args, user):
        """[<name>]

        Returns the capabilities of the user specified by <name>; if <name>
        isn't specified, returns the capabilities of the user calling the
        command.
        """
        try:
            u = ircdb.users.getUser(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
        else:
            if u == user or u._checkCapability('admin'):
                irc.reply('[%s]' % '; '.join(user.capabilities), private=True)
            else:
                irc.error(conf.supybot.replies.incorrectAuthentication(),
                          Raise=True)
    capabilities = wrap(capabilities, [first('otherUser', 'user')])

    @internationalizeDocstring
    def identify(self, irc, msg, args, user, password):
        """<name> <password>

        Identifies the user as <name>. This command (and all other
        commands that include a password) must be sent to the bot privately,
        not in a channel.
        """
        if user.checkPassword(password):
            try:
                user.addAuth(msg.prefix)
                ircdb.users.setUser(user, flush=False)
                irc.replySuccess()
            except ValueError:
                irc.error(_('Your secure flag is true and your hostmask '
                          'doesn\'t match any of your known hostmasks.'))
        else:
            self.log.warning('Failed identification attempt by %s (password '
                             'did not match for %s).', msg.prefix, user.name)
            irc.error(conf.supybot.replies.incorrectAuthentication())
    identify = wrap(identify, ['private', 'otherUser', 'something'])

    @internationalizeDocstring
    def unidentify(self, irc, msg, args, user):
        """takes no arguments

        Un-identifies you.  Note that this may not result in the desired
        effect of causing the bot not to recognize you anymore, since you may
        have added hostmasks to your user that can cause the bot to continue to
        recognize you.
        """
        user.clearAuth()
        ircdb.users.setUser(user)
        irc.replySuccess(_('If you remain recognized after giving this command, '
                         'you\'re being recognized by hostmask, rather than '
                         'by password.  You must remove whatever hostmask is '
                         'causing you to be recognized in order not to be '
                         'recognized.'))
    unidentify = wrap(unidentify, ['user'])

    @internationalizeDocstring
    def whoami(self, irc, msg, args):
        """takes no arguments

        Returns the name of the user calling the command.
        """
        try:
            user = ircdb.users.getUser(msg.prefix)
            irc.reply(user.name)
        except KeyError:
            error = self.registryValue('customWhoamiError') or \
                    _('I don\'t recognize you. You can message me either of these two commands: "user identify <username> <password>" to log in or "user register <username> <password>" to register.')
            irc.reply(error)
    whoami = wrap(whoami)

    @internationalizeDocstring
    def stats(self, irc, msg, args):
        """takes no arguments

        Returns some statistics on the user database.
        """
        users = 0
        owners = 0
        admins = 0
        hostmasks = 0
        for user in ircdb.users.values():
            users += 1
            hostmasks += len(user.hostmasks)
            try:
                if user._checkCapability('owner'):
                    owners += 1
                elif user._checkCapability('admin'):
                    admins += 1
            except KeyError:
                pass
        irc.reply(format(_('I have %s registered users '
                         'with %s registered hostmasks; '
                         '%n and %n.'),
                         users, hostmasks,
                         (owners, 'owner'), (admins, 'admin')))
    stats = wrap(stats)


Class = User

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

