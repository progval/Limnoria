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
Provides commands available only on Unix.

Commands include:
  errno
  progstats
  crypt
"""

from baseplugin import *

import os
import re
import pwd
import crypt
import errno
import random
import struct


import privmsgs
import callbacks

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, something, yn
    print 'The "progstats" command can reveal potentially sensitive'
    print 'information about your machine.  Here\'s an example of its output:'
    print
    print progstats()
    print
    if yn('Would you like to disable this command?') == 'y':
        onStart.append('disable progstats')
    
def progstats():
    pw = pwd.getpwuid(os.getuid())
    response = 'Process ID %i running as user "%s" and as group "%s" '\
               'from directory "%s" with the command line "%s".  '\
               'Running on Python %s.' %\
               (os.getpid(), pw[0], pw[3],
                os.getcwd(), " ".join(sys.argv),
                sys.version.translate(string.ascii, '\r\n'))
    return response
    

class Unix(callbacks.Privmsg):
    def errno(self, irc, msg, args):
        "<error number or code>"
        s = privmsgs.getArgs(args)
        try:
            i = int(s)
            name = errno.errorcode[i]
        except ValueError:
            name = s.upper()
            try:
                i = getattr(errno, name)
            except AttributeError:
                irc.reply(msg, 'I can\'t find the errno number for that code.')
                return
        except KeyError:
            name = '(unknown)'
        irc.reply(msg, '%s (#%s): %s' % (name, i, os.strerror(i)))
            
    def progstats(self, irc, msg, args):
        "takes no arguments"
        irc.reply(msg, progstats())

    _cryptre = re.compile(r'[./0-9A-Za-z]')
    def crypt(self, irc, msg, args):
        "<password> [<salt>]"
        def makeSalt():
            s = '\x00'
            while self._cryptre.sub('', s) != '':
                s = struct.pack('<h', random.randrange(2**16))
            return s
        (password, salt) = privmsgs.getArgs(args, optional=1)
        if salt == '':
            salt = makeSalt()
        irc.reply(msg, crypt.crypt(password, salt))


Class = Unix
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
