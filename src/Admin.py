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

import fix

import time
import pprint
import string
import smtplib
import textwrap

import conf
import ircdb
import ircmsgs
import privmsgs
import callbacks

class Admin(privmsgs.CapabilityCheckingPrivmsg):
    capability = 'admin'
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
            if channel not in irc.state.channels:
                irc.queueMsg(ircmsgs.who(channel))

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
                irc.error(msg, 'I\'m not currently in %s' % arg)
                return
        irc.queueMsg(ircmsgs.parts(args, msg.nick))

    def disable(self, irc, msg, args):
        """<command>

        Disables the command <command> for all non-owner users.
        """
        command = privmsgs.getArgs(args)
        if command in ('enable', 'identify'):
            irc.error(msg, 'You can\'t disable %s!' % command)
        else:
            # This has to know that defaultCapabilties gets turned into a
            # dictionary.
            try:
                capability = ircdb.makeAntiCapability(command)
            except ValueError:
                irc.error(msg, '%r is not a valid command.' % command)
                return
            if command in conf.defaultCapabilities:
                conf.defaultCapabilities.remove(command)
            conf.defaultCapabilities.add(capability)
            irc.reply(msg, conf.replySuccess)

    def enable(self, irc, msg, args):
        """<command>

        Re-enables the command <command> for all non-owner users.
        """
        command = privmsgs.getArgs(args)
        try:
            anticapability = ircdb.makeAntiCapability(command)
        except ValueError:
            irc.error(msg, '%r is not a valid command.' % command)
            return
        if anticapability in conf.defaultCapabilities:
            conf.defaultCapabilities.remove(anticapability)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'That command wasn\'t disabled.')

    def addcapability(self, irc, msg, args):
        """<name|hostmask> <capability>

        Gives the user specified by <name> (or the user to whom <hostmask>
        currently maps) the specified capability <capability>
        """
        (name, capability) = privmsgs.getArgs(args, 2)
        # This next check to make sure 'admin's can't hand out 'owner'.
        if ircdb.checkCapability(msg.prefix, capability) or \
           '!' in capability:
            try:
                id = ircdb.users.getUserId(name)
                user = ircdb.users.getUser(id)
                user.addCapability(capability)
                ircdb.users.setUser(id, user)
                irc.reply(msg, conf.replySuccess)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
        else:
            s = 'You can\'t add capabilities you don\'t have.'
            irc.error(msg, s)

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
                irc.error(msg, conf.replyNoUser)
                return
            try:
                user.removeCapability(capability)
                ircdb.users.setUser(id, user)
                irc.reply(msg, conf.replySuccess)
            except KeyError:
                irc.error(msg, 'That user doesn\'t have that capability.')
                return
        else:
            s = 'You can\'t remove capabilities you don\'t have.'
            irc.error(msg, s)

    def setprefixchar(self, irc, msg, args):
        """<prefixchars>

        Sets the prefix chars by which the bot can be addressed.
        """
        s = privmsgs.getArgs(args)
        if s.translate(string.ascii, string.ascii_letters) == '':
            irc.error(msg, 'Prefixes cannot contain letters.')
        else:
            conf.prefixChars = s
            irc.reply(msg, conf.replySuccess)

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
        irc.reply(msg, conf.replySuccess)
    reportbug = privmsgs.thread(reportbug)


Class = Admin

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
