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
Main program file for running the bot.
"""

from fix import *

import sys
import email

import conf
import world
import debug
import ircdb
import irclib
import ircmsgs
import drivers
import schedule
import privmsgs
import asyncoreDrivers

sys.path.append(conf.pluginDir)

class ConfigurationDict(dict):
    def __init__(self, L=None):
        if L is not None:
            L = [(key.lower(), value) for (key, value) in L]
        dict.__init__(self, L)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key.lower(), value)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key.lower())
        except KeyError:
            return ''

    def __contains__(self, key):
        return dict.__contains__(self, key.lower())


class ConfigAfter376(irclib.IrcCallback):
    public = False
    def __init__(self, msgs):
        self.msgs = msgs

    def do376(self, irc, msg):
        for msg in self.msgs:
            irc.queueMsg(msg)

    do377 = do376

def reportConfigError(filename, msg):
    debug.recoverableError('%s: %s' % (filename, msg))

def processConfigFile(filename):
    try:
        fd = file(filename)
        m = email.message_from_file(fd)
        d = ConfigurationDict(m.items())
        if 'nick' not in d:
            reportConfigError(filename, 'No nick defined.')
            return
        if 'server' not in d:
            reportConfigError(filename, 'No server defined.')
            return
        nick = d['nick']
        server = d['server']
        if server.find(':') != -1:
            (server, port) = server.split(':', 1)
            try:
                server = (server, int(port))
            except ValueError:
                reportConfigError(filename, 'Server has invalid port.')
                return
        else:
            server = (server, 6667)
        user = d['user'] or nick
        ident = d['ident'] or nick
        irc = irclib.Irc(nick, user, ident)
        for cls in privmsgs.standardPrivmsgModules:
            irc.addCallback(cls())
        ircdb.startup = True
        lines = m.get_payload()
        if lines.find('\n\n') != -1:
            (startup, after376) = lines.split('\n\n')
        else:
            (startup, after376) = (lines, '')
        for line in filter(None, startup.splitlines()):
            if not line.startswith('#'):
                irc.feedMsg(ircmsgs.privmsg(irc.nick, line))
        irc.reset()
        ircdb.startup = False
        msgs = [ircmsgs.privmsg(irc.nick, s) for s in after376.splitlines()]
        irc.addCallback(ConfigAfter376(filter(None, msgs)))
        driver = asyncoreDrivers.AsyncoreDriver(server)
        driver.irc = irc
    except IOError, e:
        reportConfigError(filename, e)
    except email.Errors.HeaderParseError, e:
        s = str(e)
        problem = s[s.rfind('`')+1:-2]
        msg = 'Invalid configuration format: %s' % problem
        reportConfigError(filename, msg)

def main():
    for filename in sys.argv[1:]:
        processConfigFile(filename)
    schedule.addPeriodicEvent(world.upkeep, 300)
    try:
        while world.ircs:
            drivers.run()
    except:
        try:
            debug.recoverableException()
        except: # It must have been deadly on purpose.
            sys.exit(0)

if __name__ == '__main__':
    main()
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
