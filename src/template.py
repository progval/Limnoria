#!/usr/bin/env python

###
# Copyright (c) 2003, Jeremiah Fincher
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
This is the template for bots.  supybot-wizard uses this file to make
customized startup files for bots.
"""

__revision__ = "$Id$"

import re
import os
import sys

if sys.version_info < (2, 3, 0):
    sys.stderr.write('This program requires Python >= 2.3.0\n')
    sys.exit(-1)

if os.name == 'posix':
    if os.getuid() == 0 or os.geteuid() == 0:
        sys.stderr.write('Dude, don\'t even try to run this as root.\n')
        sys.exit(-1)

import time
import optparse

started = time.time()

import supybot

import registry
import conf

registry.open('supybot.conf')
conf.allowEval = "%%allowEval%%"

if not os.path.exists(conf.supybot.directories.data()):
    os.mkdir(conf.supybot.directories.data())
if not os.path.exists(conf.supybot.directories.conf()):
    os.mkdir(conf.supybot.directories.conf())
    
# Must be after import conf.
import log

def main():
    import world
    import drivers
    import schedule
    schedule.addPeriodicEvent(world.upkeep, 300)
    world.startedAt = started
    try:
        while world.ircs:
            drivers.run()
        log.info('No more Irc objects, exiting.')
    except (SystemExit, KeyboardInterrupt):
        log.info('Exiting due to Ctrl-C.')
        raise SystemExit, 'Goodbye!'
    except:
        log.exception('Exception raised out of drivers.run:')

if __name__ == '__main__':
    ###
    # Options:
    # -p (profiling)
    # -O (optimizing)
    # -n, --nick (nick)
    # -s, --server (server)
    # --config (configuration values)
    parser = optparse.OptionParser(usage='Usage: %prog [options]',
                                   version='supybot %s' % conf.version)
    parser.add_option('-P', '--profile', action='store_true', dest='profile',
                      help='enables profiling')
    parser.add_option('-O', action='count', dest='optimize',
                      help='-O optimizes asserts out of the code; ' \
                           '-OO optimizes asserts and uses psyco.')
    parser.add_option('-n', '--nick', action='store',
                      dest='nick', default=conf.supybot.nick(),
                      help='nick the bot should use')
    parser.add_option('-s', '--server', action='store',
                      dest='server', default=conf.supybot.server(),
                      help='server to connect to')
    parser.add_option('-u', '--user', action='store',
                      dest='user', default=conf.supybot.user(),
                      help='full username the bot should use')
    parser.add_option('-i', '--ident', action='store',
                      dest='ident', default=conf.supybot.ident(),
                      help='ident the bot should use')
    parser.add_option('-p', '--password', action='store',
                      dest='password', default=conf.supybot.password(),
                      help='server password the bot should use')
    #parser.add_option('--config', action='append', dest='conf',
    #                  help='file of configuration variables to set')

    (options, args) = parser.parse_args()

    if options.optimize:
        __builtins__.__debug__ = False
        if options.optimize > 1:
            import psyco
            psyco.full()

    #assignmentRe = re.compile('\s*[:=]\s*')
    #if options.conf:
    #    for filename in options.conf:
    #        fd = file(filename)
    #        for line in fd:
    #            (name, valueString) = assignmentRe.split(line.rstrip(), 1)
    #            try:
    #                value = eval(valueString)
    #            except Exception, e:
    #                sys.stderr.write('Invalid configuration value: %r' % \
    #                                 valueString)
    #                sys.exit(-1)

    nick = options.nick
    user = options.user
    ident = options.ident
    password = options.password

    if ':' in options.server:
        serverAndPort = options.server.split(':', 1)
        serverAndPort[1] = int(serverAndPort[1])
        server = tuple(serverAndPort)
    else:
        server = (options.server, 6667)

    import irclib
    import ircmsgs
    import drivers
    import callbacks
    import Owner

    irc = irclib.Irc(nick, user, ident, password)
    callback = Owner.Class()
    irc.addCallback(callback)
    callback.configure(irc)
    driver = drivers.newDriver(server, irc)
    
    if options.profile:
        import profile
        profile.run('main()', '%s-%i.prof' % (nick, time.time()))
    else:
        main()


    
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
