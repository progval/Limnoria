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

import string

import conf
import utils
import ircdb
import ircutils
import privmsgs
import callbacks

class UserCommands(callbacks.Privmsg):
    def _checkNotChannel(self, irc, msg, password=' '):
        if password and ircutils.isChannel(msg.args[0]):
            irc.error(msg, conf.replyRequiresPrivacy)
            return False
        else:
            return True

    def register(self, irc, msg, args):
        """<name> <password>

        Registers <name> with the given password <password> and the current
        hostmask of the person registering.
        """
        (name, password) = privmsgs.getArgs(args, needed=2)
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
        (id, user) = ircdb.users.newUser()
        user.name = name
        user.setPassword(password)
        user.addHostmask(msg.prefix)
        ircdb.users.setUser(id, user)
        irc.reply(msg, conf.replySuccess)

    def unregister(self, irc, msg, args):
        """<name> <password>

        Unregisters <name> from the user database.
        """
        (name, password) = privmsgs.getArgs(args, needed=2)
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
        """
        (name, newname, password) = privmsgs.getArgs(args, needed=2,optional=1)
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
        hostmask.
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
        recognized by his hostmask.
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
        """<name> <old password> <new password>

        Sets the new password for the user specified by <name> to
        <new password>.
        """
        (name, oldpassword, newpassword) = privmsgs.getArgs(args, 3)
        if not self._checkNotChannel(irc, msg, oldpassword+newpassword):
            return
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        if user.checkPassword(oldpassword):
            user.setPassword(newpassword)
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

        Identifies the user as <name>.
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
            user.setAuth(msg.prefix)
            ircdb.users.setUser(id, user)
            irc.reply(msg, conf.replySuccess)
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


Class = UserCommands

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

