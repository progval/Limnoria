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
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import fix

import re
import getopt
import string
import fnmatch
from itertools import imap, ifilter

import conf
import utils
import ircdb
import ircutils
import privmsgs
import callbacks

class User(callbacks.Privmsg):
    def _checkNotChannel(self, irc, msg, password=' '):
        if password and ircutils.isChannel(msg.args[0]):
            raise callbacks.Error, conf.supybot.replies.requiresPrivacy()

    def list(self, irc, msg, args):
        """[--capability <capability>] [<glob>]

        Returns the valid registered usernames matching <glob>.  If <glob> is
        not given, returns all registered usernames.
        """
        (optlist, rest) = getopt.getopt(args, '', ['capability='])
        predicates = []
        for (option, arg) in optlist:
            if option == '--capability':
                def p(u, cap=arg):
                    try:
                        return u.checkCapability(cap)
                    except KeyError:
                        return False
                predicates.append(p)
        glob = privmsgs.getArgs(rest, required=0, optional=1)
        if glob:
            if '*' not in glob and '?' not in glob:
                glob = '*%s*' % glob
            r = re.compile(fnmatch.translate(glob), re.I)
            def p(u):
                return r.match(u.name) is not None
            predicates.append(p)
        users = []
        for u in ircdb.users.itervalues():
            for predicate in predicates:
                if not predicate(u):
                    break
            else:
                users.append(u.name)
        if users:
            utils.sortBy(str.lower, users)
            irc.reply(utils.commaAndify(users))
        else:
            if predicates:
                irc.reply('There are no matching registered users.')
            else:
                irc.reply('There are no registered users.')

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
        addHostmask = True
        hashed = conf.supybot.databases.users.hash()
        for (option, arg) in optlist:
            if option == '--hashed':
                hashed = True
        self._checkNotChannel(irc, msg, password)
        try:
            ircdb.users.getUserId(name)
            irc.error('That name is already assigned to someone.')
            return
        except KeyError:
            pass
        if ircutils.isUserHostmask(name):
            irc.error('Hostmasks aren\'t valid usernames.')
            return
        try:
            u = ircdb.users.getUser(msg.prefix)
            if u.checkCapability('owner'):
                addHostmask = False
            else:
                irc.error('Your hostmask is already registered to %s' % u.name)
                return
        except KeyError:
            pass
        (id, user) = ircdb.users.newUser()
        user.name = name
        user.setPassword(password, hashed=hashed)
        if addHostmask:
            user.addHostmask(msg.prefix)
        ircdb.users.setUser(id, user)
        irc.replySuccess()

    def unregister(self, irc, msg, args):
        """<name> [<password>]

        Unregisters <name> from the user database.  If the user giving this
        command is an owner user, the password is not necessary.
        """
        (name, password) = privmsgs.getArgs(args, optional=1)
        self._checkNotChannel(irc, msg, password)
        try:
            id = ircdb.users.getUserId(name)
            u = ircdb.users.getUser(id)
        except KeyError:
            irc.error('That username isn\'t registered.')
            return
        if not u.checkPassword(password):
            u = ircdb.users.getUser(msg.prefix)
            if not u.checkCapability('owner'):
                irc.error(conf.supybot.replies.incorrectAuthentication())
                return
        ircdb.users.delUser(id)
        irc.replySuccess()

    def changename(self, irc, msg, args):
        """<name> <new name> [<password>]

        Changes your current user database name to the new name given.
        <password> is only necessary if the user isn't recognized by hostmask.
        If you include the <password> parameter, this message must be sent
        to the bot privately (not on a channel).
        """
        (name,newname,password) = privmsgs.getArgs(args,required=2,optional=1)
        self._checkNotChannel(irc, msg, password)
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.error('That username isn\'t registered.')
            return
        try:
            id = ircdb.users.getUserId(newname)
            irc.error('%r is already registered.' % newname)
            return
        except KeyError:
            pass
        if user.checkHostmask(msg.prefix) or user.checkPassword(password):
            user.name = newname
            ircdb.users.setUser(id, user)
            irc.replySuccess()

    def addhostmask(self, irc, msg, args):
        """<name> <hostmask> [<password>]

        Adds the hostmask <hostmask> to the user specified by <name>.  The
        <password> may only be required if the user is not recognized by
        hostmask.  If you include the <password> parameter, this message must
        be sent to the bot privately (not on a channel).  <password> is also
        not required if an owner user is giving the command on behalf of some
        other user.
        """
        (name, hostmask, password) = privmsgs.getArgs(args, 2, 1)
        self._checkNotChannel(irc, msg, password)
        if not ircutils.isUserHostmask(hostmask):
            irc.error('That\'s not a valid hostmask. Make sure your hostmask '
                      'includes a nick, then an exclamation point (!), then '
                      'a user, then an at symbol (@), then a host.  Feel '
                      'free to use wildcards (* and ?, which work just like '
                      'they do on the command line) in any of these parts.')
            return
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.errorNoUser()
            return
        try:
            otherId = ircdb.users.getUserId(hostmask)
            if otherId != id:
                irc.error('That hostmask is already registered.')
                return
        except KeyError:
            pass
        if not user.checkPassword(password) and \
           not user.checkHostmask(msg.prefix):
            try:
                u = ircdb.users.getUser(msg.prefix)
            except KeyError:
                irc.error(conf.supybot.replies.incorrectAuthentication())
                return
            if not u.checkCapability('owner'):
                irc.error(conf.supybot.replies.incorrectAuthentication())
                return
        try:
            user.addHostmask(hostmask)
        except ValueError, e:
            irc.error(str(e))
            return
        ircdb.users.setUser(id, user)
        irc.replySuccess()

    def removehostmask(self, irc, msg, args):
        """<name> <hostmask> [<password>]

        Removes the hostmask <hostmask> from the record of the user specified
        by <name>.  If the hostmask is 'all' then all hostmasks will be
        removed.  The <password> may only be required if the user is not
        recognized by his hostmask.  If you include the <password> parameter,
        this message must be sent to the bot privately (not on a channel).
        """
        (name, hostmask, password) = privmsgs.getArgs(args, 2, 1)
        self._checkNotChannel(irc, msg, password)
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.errorNoUser()
            return
        if not user.checkPassword(password) and \
           not user.checkHostmask(msg.prefix):
            u = ircdb.users.getUser(msg.prefix)
            if not u.checkCapability('owner'):
                irc.error(conf.supybot.replies.incorrectAuthentication())
                return
        try:
            s = ''
            if hostmask == 'all':
                user.hostmasks[:] = []
                s = 'All hostmasks removed.'
            else:
                user.removeHostmask(hostmask)
        except ValueError:
            irc.error('There was no such hostmask.')
            return
        ircdb.users.setUser(id, user)
        irc.replySuccess(s)

    def setpassword(self, irc, msg, args):
        """[--hashed] <name> <old password> <new password>

        Sets the new password for the user specified by <name> to
        <new password>.  Obviously this message must be sent to the bot
        privately (not in a channel).  If --hashed is given, the password will
        be hashed on disk (rather than being stored in plaintext.  If the
        requesting user is an owner user (and the user whose password is being
        changed isn't that same owner user), then <old password> needn't be
        correct.
        """
        (optlist, rest) = getopt.getopt(args, '', ['hashed'])
        (name, oldpassword, newpassword) = privmsgs.getArgs(rest, 3)
        hashed = conf.supybot.databases.users.hash()
        for (option, arg) in optlist:
            if option == '--hashed':
                hashed = True
        self._checkNotChannel(irc, msg, oldpassword+newpassword)
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.errorNoUser()
            return
        u = ircdb.users.getUser(msg.prefix)
        if user.checkPassword(oldpassword) or \
           (u.checkCapability('owner') and not u == user):
            user.setPassword(newpassword, hashed=hashed)
            ircdb.users.setUser(id, user)
            irc.replySuccess()
        else:
            irc.error(conf.supybot.replies.incorrectAuthentication())

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
                irc.errorNoUser()
                return
        try:
            user = ircdb.users.getUser(hostmask)
            irc.reply(user.name)
        except KeyError:
            irc.errorNoUser()

    def hostmasks(self, irc, msg, args):
        """[<name>]

        Returns the hostmasks of the user specified by <name>; if <name> isn't
        specified, returns the hostmasks of the user calling the command.
        """
        if ircutils.isChannel(msg.args[0]):
            irc.errorRequiresPrivacy()
            return
        name = privmsgs.getArgs(args, required=0, optional=1)
        try:
            user = ircdb.users.getUser(msg.prefix)
            if name:
                if name != user.name and not user.checkCapability('owner'):
                    irc.error('You may only retrieve your own hostmasks.')
                else:
                    try:
                        user = ircdb.users.getUser(name)
                        irc.reply(repr(user.hostmasks))
                    except KeyError:
                        irc.errorNoUser()
            else:
                irc.reply(repr(user.hostmasks))
        except KeyError:
            irc.errorNotRegistered()

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
            irc.reply('[%s]' % '; '.join(user.capabilities))
        except KeyError:
            irc.errorNoUser()

    def identify(self, irc, msg, args):
        """<name> <password>

        Identifies the user as <name>. This command (and all other
        commands that include a password) must be sent to the bot privately,
        not in a channel.
        """
        (name, password) = privmsgs.getArgs(args, 2)
        self._checkNotChannel(irc, msg)
        try:
            id = ircdb.users.getUserId(name)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.errorNoUser()
            return
        if user.checkPassword(password):
            try:
                user.setAuth(msg.prefix)
                ircdb.users.setUser(id, user)
                irc.replySuccess()
            except ValueError:
                irc.error('Your secure flag is true and your hostmask '
                               'doesn\'t match any of your known hostmasks.')
        else:
            irc.error(conf.supybot.replies.incorrectAuthentication())

    def unidentify(self, irc, msg, args):
        """takes no arguments

        Un-identifies the user.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.errorNoUser()
            return
        user.unsetAuth()
        ircdb.users.setUser(id, user)
        irc.replySuccess('If you remain recognized after giving this command,'
                         ' you\'re being recognized by hostmask, rather than '
                         'by password.  You must remove whatever hostmask is '
                         'causing you to be recognized in order not to be '
                         'recognized.')

    def whoami(self, irc, msg, args):
        """takes no arguments

        Returns the name of the user calling the command.
        """
        try:
            user = ircdb.users.getUser(msg.prefix)
            irc.reply(user.name)
        except KeyError:
            irc.errorNotRegistered()

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
        self._checkNotChannel(irc, msg, password)
        try:
            id = ircdb.users.getUserId(msg.prefix)
            user = ircdb.users.getUser(id)
        except KeyError:
            irc.errorNotRegistered()
        if value == '':
            value = not user.secure
        elif value.lower() in ('true', 'false'):
            value = eval(value.capitalize())
        else:
            irc.error('%s is not a valid boolean value.' % value)
            return
        if user.checkPassword(password) and \
           user.checkHostmask(msg.prefix, useAuth=False):
            user.secure = value
            ircdb.users.setUser(id, user)
            irc.reply('Secure flag set to %s' % value)
        else:
            irc.error(conf.supybot.replies.incorrectAuthentication())


Class = User

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

