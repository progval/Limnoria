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
import time
import email
import getopt
#import pprint

import conf
import world

sys.path.append(conf.pluginDir)

world.startedAt = time.time()

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



def processConfigFile(filename):
    import debug
    import irclib
    import ircmsgs
    import drivers
    import ircutils
    import privmsgs
    def reportConfigError(filename, msg):
        debug.recoverableError('%s: %s' % (filename, msg))
    class ConfigAfter376(irclib.IrcCallback):
        public = False
        def __init__(self, commands):
            self.commands = commands

        def do376(self, irc, msg):
            #debug.printf('Firing ConfigAfter376 messages')
            for command in self.commands:
                #debug.printf(irc.nick)
                #debug.printf(command)
                msg = ircmsgs.privmsg(irc.nick, command, prefix=irc.prefix)
                irc.queueMsg(msg)

        do377 = do376
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
        password = d['password']
        if ':' in server:
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
        irc = irclib.Irc(nick, user, ident, password)
        for Class in privmsgs.standardPrivmsgModules:
            irc.addCallback(Class())
        world.startup = True
        text = m.get_payload()
        while 1:
            # Gotta remove all extra newlines.
            newtext = text.replace('\n\n\n', '\n\n')
            if newtext == text:
                text = newtext
                break
            else:
                text = newtext
        lines = text.splitlines()
        #debug.printf(pprint.pformat(lines))
        (startup, after376) = tuple(itersplit(lines,lambda s: not s, True))
        #debug.printf('startup: %r' % startup)
        #debug.printf('after376: %r' % after376)
        prefix = ircutils.joinHostmask(nick, ident, 'host')
        for line in filter(None, startup):
            if not line.startswith('#'):
                irc.feedMsg(ircmsgs.privmsg(irc.nick, line, prefix=prefix))
        irc.reset()
        world.startup = False
        irc.addCallback(ConfigAfter376(after376))
        driver = drivers.newDriver(server, irc)
    except IOError, e:
        reportConfigError(filename, e)
    except email.Errors.HeaderParseError, e:
        s = str(e)
        problem = s[s.rfind('`')+1:-2]
        msg = 'Invalid configuration format: %s' % problem
        reportConfigError(filename, msg)

def main():
    (optlist, filenames) = getopt.getopt(sys.argv[1:], 'Opc:')
    for (option, argument) in optlist:
        if option == '-c':
            myLocals = {}
            myGlobals = {}
            execfile(argument, myGlobals, myLocals)
            for (key, value) in myGlobals.iteritems():
                setattr(conf, key, value)
            for (key, value) in myLocals.iteritems():
                setattr(conf, key, value)
        else:
            print 'Unexpected argument %s; ignoring.' % option
    import debug
    import drivers
    import schedule
    for filename in filenames:
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
    import sys
    if '-p' in sys.argv:
        import profile, time
        sys.argv.remove('-p')
        profile.run('main()', '%i.prof' % time.time())
    if '-O' in sys.argv:
        import psyco
        psyco.full()
        main()
    else:
        main()
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
