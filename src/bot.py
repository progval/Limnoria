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
import getopt

import conf
import debug
import world
import irclib
import drivers
import ircmsgs
import privmsgs
import schedule

sys.path.append(conf.pluginDir)

world.startedAt = time.time()

class ConfigAfter376(irclib.IrcCallback):
    public = False
    def __init__(self, commands):
        self.commands = commands

    def do376(self, irc, msg):
        for command in self.commands:
            msg = ircmsgs.privmsg(irc.nick, command, prefix=irc.prefix)
            irc.queueMsg(msg)

def handleConfigFile():
    nick = conf.config['nick']
    user = conf.config['user']
    ident = conf.config['ident']
    password = conf.config['password']
    irc = irclib.Irc(nick, user, ident, password)
    for Class in privmsgs.standardPrivmsgModules:
        callback = Class()
        if hasattr(callback, 'configure'):
            callback.configure(irc)
        irc.addCallback(callback)
    irc.addCallback(ConfigAfter376(conf.config['afterConnect']))
    drivers.newDriver(conf.config['server'], irc)

def main():
    (optlist, filenames) = getopt.getopt(sys.argv[1:], 'Opc:')
    if len(filenames) != 1:
        conf.reportConfigError('Command line', 'No configuration file given.') 
        
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
    filename = filenames[0]
    conf.processConfig(filename)
    handleConfigFile()
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
    if '-p' in sys.argv:
        import profile
        sys.argv.remove('-p')
        profile.run('main()', '%i.prof' % time.time())
    if '-O' in sys.argv:
        import psyco
        psyco.full()
        main()
    else:
        main()
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
