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
These are commands useful for administrating the bot; they all require their
caller to have the 'admin' capability.  This plugin is loaded by default.
"""

__revision__ = "$Id$"

import fix

import time
import pprint
import string
import logging
import smtplib
import textwrap
from itertools import imap

import log
import conf
import ircdb
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks

class Admin(privmsgs.CapabilityCheckingPrivmsg):
    capability = 'admin'
    def __init__(self):
        privmsgs.CapabilityCheckingPrivmsg.__init__(self)
        self.joins = {}
        
    def do471(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc, msg) = self.joins[channel]
            del self.joins[channel]
            irc.error('Cannot join %s, it\'s full.' % channel)
        except KeyError:
            self.log.debug('Got 471 without Admin.join being called.')

    def do473(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc, msg) = self.joins[channel]
            del self.joins[channel]
            irc.error('Cannot join %s, I was not invited.' % channel)
        except KeyError:
            self.log.debug('Got 473 without Admin.join being called.')

    def do474(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc, msg) = self.joins[channel]
            del self.joins[channel]
            irc.error('Cannot join %s, it\'s banned me.' % channel)
        except KeyError:
            self.log.debug('Got 474 without Admin.join being called.')
            
    def do475(self, irc, msg):
        try:
            channel = msg.args[1]
            (irc, msg) = self.joins[channel]
            del self.joins[channel]
            irc.error('Cannot join %s, my keyword was wrong.' % channel)
        except KeyError:
            self.log.debug('Got 475 without Admin.join being called.')

    def doJoin(self, irc, msg):
        if msg.prefix == irc.prefix:
            try:
                del self.joins[msg.args[0]]
            except KeyError:
                s = 'Joined a channel without Admin.join being called'
                self.log.debug(s)

    def doInvite(self, irc, msg):
        if msg.args[1] not in irc.state.channels:
            if conf.alwaysJoinOnInvite:
                irc.queueMsg(ircmsgs.join(msg.args[1]))
            else:
                if ircdb.checkCapability(msg.prefix, 'admin'):
                    irc.queueMsg(ircmsgs.join(msg.args[1]))
    
    def join(self, irc, msg, args):
        """<channel>[,<key>] [<channel>[,<key>] ...]

        Tell the bot to join the whitespace-separated list of channels
        you give it.  If a channel requires a key, attach it behind the
        channel name via a comma.  I.e., if you need to join both #a and #b,
        and #a requires a key of 'aRocks', then you'd call 'join #a,aRocks #b'
        """
        keys = []
        channels = []
        for channel in args:
            if ',' in channel:
                (channel, key) = channel.split(',', 1)
                channels.insert(0, channel)
                keys.insert(0, key)
            else:
                channels.append(channel)
        irc.queueMsg(ircmsgs.joins(channels, keys))
        for channel in channels:
            self.joins[channel] = (irc, msg)
            if channel not in irc.state.channels:
                irc.queueMsg(ircmsgs.who(channel))

    def channels(self, irc, msg, args):
        """takes no arguments

        Returns the channels the bot is on.  Must be given in private, in order
        to protect the secrecy of secret channels.
        """
        if ircutils.isChannel(msg.args[0]):
            irc.errorRequiresPrivacy()
            return
        L = irc.state.channels.keys()
        if L:
            utils.sortBy(ircutils.toLower, L)
            irc.reply(utils.commaAndify(L))
        else:
            irc.reply('I\'m not currently in any channels.')

    def nick(self, irc, msg, args):
        """<nick>

        Changes the bot's nick to <nick>."""
        nick = privmsgs.getArgs(args)
        irc.queueMsg(ircmsgs.nick(nick))

    def part(self, irc, msg, args):
        """<channel> [<channel> ...]

        Tells the bot to part the whitespace-separated list of channels
        you give it.
        """
        if not args:
            args.append(msg.args[0])
        for arg in args:
            if arg not in irc.state.channels:
                irc.error('I\'m not currently in %s' % arg)
                return
        irc.queueMsg(ircmsgs.parts(args, msg.nick))

    def disable(self, irc, msg, args):
        """<command>

        Disables the command <command> for all non-owner users.
        """
        command = privmsgs.getArgs(args)
        if command in ('enable', 'identify'):
            irc.error('You can\'t disable %s!' % command)
        else:
            # This has to know that defaultCapabilties gets turned into a
            # dictionary.
            try:
                capability = ircdb.makeAntiCapability(command)
            except ValueError:
                irc.error('%r is not a valid command.' % command)
                return
            if command in conf.defaultCapabilities:
                conf.defaultCapabilities.remove(command)
            conf.defaultCapabilities.add(capability)
            irc.replySuccess()

    def enable(self, irc, msg, args):
        """<command>

        Re-enables the command <command> for all non-owner users.
        """
        command = privmsgs.getArgs(args)
        try:
            anticapability = ircdb.makeAntiCapability(command)
        except ValueError:
            irc.error('%r is not a valid command.' % command)
            return
        if anticapability in conf.defaultCapabilities:
            conf.defaultCapabilities.remove(anticapability)
            irc.replySuccess()
        else:
            irc.error('That command wasn\'t disabled.')

    def addcapability(self, irc, msg, args):
        """<name|hostmask> <capability>

        Gives the user specified by <name> (or the user to whom <hostmask>
        currently maps) the specified capability <capability>
        """
        # Ok, the concepts that are important with capabilities:
        #
        ### 1) No user should be able to elevate his privilege to owner.
        ### 2) Admin users are *not* superior to #channel.ops, and don't
        ###    have God-like powers over channels.
        ### 3) We assume that Admin users are two things: non-malicious and
        ###    and greedy for power.  So they'll try to elevate their privilege
        ###    to owner, but they won't try to crash the bot for no reason.

        # Thus, the owner capability can't be given in the bot.  Admin users
        # can only give out capabilities they have themselves (which will
        # depend on both conf.defaultAllow and conf.defaultCapabilities), but
        # generally means they can't mess with channel capabilities.
        (name, capability) = privmsgs.getArgs(args, required=2)
        if capability == 'owner':
            irc.error('The "owner" capability can\'t be added in the bot.'
                           '  Use the supybot-adduser program (or edit the '
                           'users.conf file yourself) to add an owner '
                           'capability.')
            return
        if ircdb.checkCapability(msg.prefix, capability) or \
           '-' in capability:
            try:
                id = ircdb.users.getUserId(name)
                user = ircdb.users.getUser(id)
                user.addCapability(capability)
                ircdb.users.setUser(id, user)
                irc.replySuccess()
            except KeyError:
                irc.errorNoUser()
        else:
            s = 'You can\'t add capabilities you don\'t have.'
            irc.error(s)

    def removecapability(self, irc, msg, args):
        """<name|hostmask> <capability>

        Takes from the user specified by <name> (or the uswer to whom
        <hostmask> currently maps) the specified capability <capability>
        """
        (name, capability) = privmsgs.getArgs(args, 2)
        if ircdb.checkCapability(msg.prefix, capability) or \
           '!' in capability:
            try:
                id = ircdb.users.getUserId(name)
                user = ircdb.users.getUser(id)
            except KeyError:
                irc.errorNoUser()
                return
            try:
                user.removeCapability(capability)
                ircdb.users.setUser(id, user)
                irc.replySuccess()
            except KeyError:
                irc.error('That user doesn\'t have that capability.')
                return
        else:
            s = 'You can\'t remove capabilities you don\'t have.'
            irc.error(s)

    def ignore(self, irc, msg, args):
        """<hostmask|nick>

        Ignores <hostmask> or, if a nick is given, ignores whatever hostmask
        that nick is currently using.
        """
        arg = privmsgs.getArgs(args)
        if ircutils.isUserHostmask(arg):
            hostmask = arg
        else:
            try:
                hostmask = irc.state.nickToHostmask(arg)
            except KeyError:
                irc.error('I can\'t find a hostmask for %s' % arg)
                return
        conf.ignores.append(hostmask)
        irc.replySuccess()

    def unignore(self, irc, msg, args):
        """<hostmask|nick>

        Ignores <hostmask> or, if a nick is given, ignores whatever hostmask
        that nick is currently using.
        """
        arg = privmsgs.getArgs(args)
        if ircutils.isUserHostmask(arg):
            hostmask = arg
        else:
            try:
                hostmask = irc.state.nickToHostmask(arg)
            except KeyError:
                irc.error('I can\'t find a hostmask for %s' % arg)
                return
        try:
            conf.ignores.remove(hostmask)
            while hostmask in conf.ignores:
                conf.ignores.remove(hostmask)
            irc.replySuccess()
        except ValueError:
            irc.error('%s wasn\'t in conf.ignores.' % hostmask)
            
    def ignores(self, irc, msg, args):
        """takes no arguments

        Returns the hostmasks currently being globally ignored.
        """
        if conf.ignores:
            irc.reply(utils.commaAndify(imap(repr, conf.ignores)))
        else:
            irc.reply('I\'m not currently globally ignoring anyone.')

    def setprefixchar(self, irc, msg, args):
        """<prefixchars>

        Sets the prefix chars by which the bot can be addressed.
        """
        s = privmsgs.getArgs(args)
        for c in s:
            if c not in conf.validPrefixChars:
                s = 'PrefixChars must be something in %r'%conf.validPrefixChars
                irc.error(s)
                return
        else:
            conf.prefixChars = s
            irc.replySuccess()

    def reportbug(self, irc, msg, args):
        """<description>

        Reports a bug to a private mailing list supybot-bugs.  <description>
        will be the subject of the email.  The most recent 10 or so messages
        the bot receives will be sent in the body of the email.
        """
        description = privmsgs.getArgs(args)
        messages = pprint.pformat(irc.state.history[-10:])
        email = textwrap.dedent("""
        Subject: %s
        From: jemfinch@users.sourceforge.net
        To: supybot-bugs@lists.sourceforge.net
        Date: %s

        Bug report for Supybot %s.
        %s
        """) % (description, time.ctime(), conf.version, messages)
        email = email.strip()
        email = email.replace('\n', '\r\n')
        smtp = smtplib.SMTP('mail.sourceforge.net', 25)
        smtp.sendmail('jemfinch@users.sf.net',
                      ['supybot-bugs@lists.sourceforge.net'],
                      email)
        smtp.quit()
        irc.replySuccess()
    reportbug = privmsgs.thread(reportbug)

    def loglevel(self, irc, msg, args):
        """{DEBUG,INFO,WARNING,ERROR,CRITICAL}

        Sets the logging level of the bot's logs.
        """
        level = privmsgs.getArgs(args)
        try:
            level = getattr(logging, level.upper())
        except AttributeError:
            raise callbacks.ArgumentError
        log.setLevel(level)
        irc.replySuccess()


Class = Admin

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
