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

import supybot

from fix import *
from questions import *

import os
import sys
import optparse

import conf
import debug

debug.minimumPriority = 'high'

def main():
    parser = optparse.OptionParser(usage='Usage: %prog [options]',
                                   version='supybot %s' % conf.version)
    parser.add_option('-u', '--username', action='store', default='',
                      dest='name',
                      help='username for the user.')
    parser.add_option('-p', '--password', action='store', default='',
                      dest='password',
                      help='password for the user.')
    parser.add_option('-c', '--capability', action='append',
                      dest='capabilities', metavar='CAPABILITY',
                      help='capability the user should have; '
                           'this option may be given multiple times.')
    filename = os.path.join(conf.confDir, conf.userfile)
    parser.add_option('-f', '--filename', action='store', default=filename,
                      dest='filename',
                      help='filename of your users.conf; '
                           'defaults to %s' % filename)

    (options, args) = parser.parse_args()
    if not options.name:
        name = something('What is the user\'s name?')
    else:
        name = options.name

    if not options.password:
        password = something('What is %s\'s password?' % name)
    else:
        password = options.password

    if not options.capabilities:
        capabilities = []
        prompt = 'Would you like to give %s a capability?' % name
        while yn(prompt) == 'y':
            capabilities.append(anything('What capability?'))
            prompt = 'Would you like to give %s another capability?' % name
    else:
        capabilities = options.capabilities

    conf.confDir = os.path.dirname(options.filename)
    conf.userfile = os.path.basename(options.filename)
    import ircdb

    try:
        # First, let's check to see if the user is already in the database.
        _ = ircdb.users.getUser(name)
        # Uh oh.  That user already exists; otherwise we'd have KeyError'ed.
        sys.stderr.write('That user already exists.  Try another name.\n')
        sys.exit(-1)
    except KeyError:
        # Good.  No such user exists.  We'll pass.
        pass
    (id, user) = ircdb.users.newUser()
    user.name = name
    user.setPassword(password)
    for capability in capabilities:
        user.addCapability(capability)
    ircdb.users.setUser(id, user)
    print 'User %s added.' % name

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
