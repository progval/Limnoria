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
Provides commands useful to users in general. This plugin is loaded by default.
"""

__revision__ = "$Id$"

import fix

import getopt
import string

import conf
import ircdb
import ircutils
import privmsgs
import callbacks

class User(callbacks.Privmsg):
    def _checkNotChannel(self, irc, msg, password=' '):
        if password and ircutils.isChannel(msg.args[0]):
            irc.error(msg, conf.replyRequiresPrivacy)
            return False
        else:
            return True

    def register(self, irc, msg, args):
        """[--hashed] <name> <password>

        Registers <name> with the given password <password> and the current
        hostmask of the person registering.  This command (and all other
        commands that include a password) must be sent to the bot privately,
        not in a channel.  If --hashed is given, the password will be hashed
        on disk, rather than being stored in plaintext.
        """
        (optlist, rest) = getopt.getopt(args, '', ['hashed'])
        (name, password) = privmsgs.getArgs(rest, required=2)
        hashed = False
        for (option, arg) in optlist:
            if option == '--hashed':
                hashed = True
        if not self._checkNotChannel(irc, msg, password):
            return
        try:
            ircdb.users.getUserId(name)
            irc.error(msg, 'That name is already assigned to someone.')
            return
        except KeyError:
            pass
        if ircutils.isUserHostmask(name):
            irc.error(msg, 'Hostmasks aren\'t valid usernames.')
            return
        try:
            u = ircdb.users.getUser(msg.prefix)
            irc.error(msg,'Your hostmask is already registered to %s' % u.name)
            return
        except KeyError:
            pass
        (id, user) = ircdb.users.newUser()
        user.name = name
        user.setPassword(password, hashed=hashed)
        user.addHostmask(msg.prefix)
        ircdb.users.setUser(id, user)
        irc.reply(msg, conf.replySuccess)

    def unregister(self, irc, msg, args):
        """<name> <password>

        Unregisters <name> from the user database.
        """
        (name, password) = privmsgs.getArgs(args, required=2)
        if not self._checkNotChannel(irc, msg, password):
            return
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error(msg, 'That username isn\'t registered.')
            return
        if user.checkPassword(password):
            ircdb.users.delUser(id)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyIncorrectAuth)

    def changeusername(self, irc, msg, args):
        """<name> <new name> [<password>]

        Changes your current user database name to the new name given.
        <password> is only necessary if the user isn't recognized by hostmask.
        If you include the <password> parameter, this message must be sent
        to the bot privately (not on a channel).
        """
        (name, newname, password) = privmsgs.getArgs(args, required=2,optional=1)
        if not self._checkNotChannel(irc, msg, password):
            return
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error(msg, 'That username isn\'t registered.')
            return
        try:
            id = ircdb.users.getUserId(newname)
            irc.error(msg, '%r is already registered.' % newname)
            return
        except KeyError:
            pass
        if user.checkHostmask(msg.prefix) or user.checkPassword(password):
            user.name = newname
            ircdb.users.setUser(id, user)
            irc.reply(msg, conf.replySuccess)
            
    def addhostmask(self, irc, msg, args):
        """<name> <hostmask> [<password>]

        Adds the hostmask <hostmask> to the user specified by <name>.  The
        <password> may only be required if the user is not recognized by
        hostmask.  If you include the <password> parameter, this message must
        be sent to the bot privately (not on a channel).
        """
        (name, hostmask, password) = privmsgs.getArgs(args, 2, 1)
        if not self._checkNotChannel(irc, msg, password):
            return
        if not ircutils.isUserHostmask(hostmask):
            irc.error(msg, 'That\'s not a valid hostmask.')
            return
        s = hostmask.translate(string.ascii, '!@*?')
        if len(s) < 10:
            s = 'Hostmask must contain more than 10 non-wildcard characters.'
            irc.error(msg, s)
            return
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        try:
            otherId = ircdb.users.getUserId(hostmask)
            if otherId != id:
                irc.error(msg, 'That hostmask is already registered.')
                return
        except KeyError:
            pass
        if user.checkHostmask(msg.prefix) or user.checkPassword(password):
            user.addHostmask(hostmask)
            ircdb.users.setUser(id, user)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyIncorrectAuth)
            return

    def removehostmask(self, irc, msg, args):
        """<name> <hostmask> [<password>]

        Removes the hostmask <hostmask> from the record of the user specified
        by <name>.  The <password> may only be required if the user is not
        recognized by his hostmask.  If you include the <password> parameter,
        this message must be sent to the bot privately (not on a channel).
        """
        (name, hostmask, password) = privmsgs.getArgs(args, 2, 1)
        if not self._checkNotChannel(irc, msg, password):
            return
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        if user.checkHostmask(msg.prefix) or user.checkPassword(password):
            try:
                user.removeHostmask(hostmask)
            except ValueError:
                irc.error(msg, 'There was no such hostmask.')
                return
            ircdb.users.setUser(id, user)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyIncorrectAuth)
            return

    def setpassword(self, irc, msg, args):
        """[--hashed] <name> <old password> <new password>

        Sets the new password for the user specified by <name> to
        <new password>.  Obviously this message must be sent to the bot
        privately (not in a channel).  If --hashed is given, the password will
        be hashed on disk (rather than being stored in plaintext.
        """
        (optlist, rest) = getopt.getopt(args, '', ['hashed'])
        (name, oldpassword, newpassword) = privmsgs.getArgs(rest, 3)
        hashed = False
        for (option, arg) in optlist:
            if option == '--hashed':
                hashed = True
        if not self._checkNotChannel(irc, msg, oldpassword+newpassword):
            return
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        if user.checkPassword(oldpassword):
            user.setPassword(newpassword, hashed=hashed)
            ircdb.users.setUser(id, user)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyIncorrectAuth)

    def username(self, irc, msg, args):
        """<hostmask|nick>

        Returns the username of the user specified by <hostmask> or <nick> if
        the user is registered.
        """
        hostmask = privmsgs.getArgs(args)
        if not ircutils.isUserHostmask(hostmask):
            try:
                hostmask = irc.state.nickToHostmask(hostmask)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
                return
        try:
            user = ircdb.users.getUser(hostmask)
            irc.reply(msg, user.name)
        except KeyError:
            irc.error(msg, conf.replyNoUser)

    def hostmasks(self, irc, msg, args):
        """[<name>]

        Returns the hostmasks of the user specified by <name>; if <name> isn't
        specified, returns the hostmasks of the user calling the command.
        """
        if not args:
            name = msg.prefix
        else:
            name = privmsgs.getArgs(args)
        try:
            user = ircdb.users.getUser(name)
            irc.reply(msg, repr(user.hostmasks))
        except KeyError:
            irc.error(msg, conf.replyNoUser)

    def capabilities(self, irc, msg, args):
        """[<name>]

        Returns the capabilities of the user specified by <name>; if <name>
        isn't specified, returns the hostmasks of the user calling the command.
        """
        if not args:
            name = msg.prefix
        else:
            name = privmsgs.getArgs(args)
        try:
            user = ircdb.users.getUser(name)
            irc.reply(msg, '[%s]' % ', '.join(user.capabilities))
        except KeyError:
            irc.error(msg, conf.replyNoUser)

    def identify(self, irc, msg, args):
        """<name> <password>

        Identifies the user as <name>. This command (and all other
        commands that include a password) must be sent to the bot privately,
        not in a channel.
        """
        (name, password) = privmsgs.getArgs(args, 2)
        if not self._checkNotChannel(irc, msg):
            return
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        if user.checkPassword(password):
            try:
                user.setAuth(msg.prefix)
                ircdb.users.setUser(id, user)
                irc.reply(msg, conf.replySuccess)
            except ValueError:
                irc.error(msg, 'Your secure flag is true and your hostmask '
                               'doesn\'t match any of your known hostmasks.')
        else:
            irc.error(msg, conf.replyIncorrectAuth)

    def unidentify(self, irc, msg, args):
        """takes no arguments

        Un-identifies the user.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        user.unsetAuth()
        ircdb.users.setUser(id, user)
        irc.reply(msg, conf.replySuccess)

    def whoami(self, irc, msg, args):
        """takes no arguments

        Returns the name of the user calling the command.
        """
        try:
            user = ircdb.users.getUser(msg.prefix)
            irc.reply(msg, user.name)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)

    def setsecure(self, irc, msg, args):
        """<password> [<True|False>]

        Sets the secure flag on the user of the person sending the message.
        Requires that the person's hostmask be in the list of hostmasks for
        that user in addition to the password being correct.  When the secure
        flag is set, the user *must* identify before he can be recognized.
        If a specific True/False value is not given, it inverts the current
        value.
        """
        (password, value) = privmsgs.getArgs(args, optional=1)
        if not self._checkNotChannel(irc, msg, password):
            return
        try:
            id = ircdb.users.getUserId(msg.prefix)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
        if value == '':
            value = not user.secure
        elif value.lower() in ('true', 'false'):
            value = eval(value.capitalize())
        else:
            irc.error(msg, '%s is not a valid boolean value.' % value)
            return
        if user.checkPassword(password) and \
           user.checkHostmask(msg.prefix, useAuth=False):
            user.secure = value
            ircdb.users.setUser(id, user)
            irc.reply(msg, 'Secure flag set to %s' % value)
        else:
            irc.error(msg, conf.replyIncorrectAuth)


Class = User

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

