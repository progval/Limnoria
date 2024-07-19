#!/usr/bin/env python3

###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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

from supybot.questions import *

import os
import sys
import optparse

def _main():
    import supybot.log as log
    import supybot.conf as conf
    conf.supybot.log.stdout.setValue(False)
    parser = optparse.OptionParser(usage='Usage: %prog [options] <users.conf>',
                                   version='supybot %s' % conf.version)
    parser.add_option('-u', '--username', action='store', default='',
                      dest='name',
                      help='username for the user.')
    parser.add_option('-p', '--password', action='store', default='',
                      dest='password',
                      help='new password for the user.')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Specify the users.conf file you\'d like to use.  '
                     'Be sure *not* to specify your registry file, generated '
                     'by supybot-wizard.  This is not the file you want.  '
                     'Instead, take a look in your conf directory (usually '
                     'named "conf") and take a gander at the file '
                     '"users.conf".  That\'s the one you want.')

    filename = os.path.abspath(args[0])
    conf.supybot.directories.log.setValue('/')
    conf.supybot.directories.conf.setValue('/')
    conf.supybot.directories.data.setValue('/')
    conf.supybot.directories.plugins.setValue(['/'])
    conf.supybot.databases.users.filename.setValue(filename)
    import supybot.ircdb as ircdb

    if not options.name:
        name = ''
        while not name:
            name = something('What is the user\'s name?')
            try:
                # Check to see if the user is already in the database.
                _ = ircdb.users.getUser(name)
                # Success!
            except KeyError:
                # Failure.  No such user exists.  Try another name.
                output('That user doesn\'t exist.  Try another name.')
                name = ''
    else:
        try:
            _ = ircdb.users.getUser(options.name)
            name = options.name
        except KeyError:
            # Same as above. We exit here instead.
            output('That user doesn\'t exist.  Try another name.')
            sys.exit(-1)

    if not options.password:
        password = getpass('Please enter new password for %s: ' % name)
    else:
        password = options.password

    user = ircdb.users.getUser(name)
    user.setPassword(password)
    ircdb.users.setUser(user)
    ircdb.users.flush()
    ircdb.users.close()
    print('User %s\'s password reset!' % name)

def main():
    try:
        _main()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
