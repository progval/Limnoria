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
Add the module docstring here.  This will be used by the setup.py script.
"""

from baseplugin import *

import re
import sre_constants
import gzip
import popen2
from itertools import imap, ifilter

import conf
import utils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Debian')
    if not utils.findBinaryInPath('zegrep'):
        if not advanced:
            print 'I can\'t find zegrep in your path.  This is necessary '
            print 'to run the debfile command.  I\'ll disable this command '
            print 'now.  When you get zegrep in your path, use the command '
            print '"enable debfile" to re-enable the command.'
            onStart.append('disable debfile')
        else:
            print 'I can\'t find zegrep in your path.  If you want to run the '
            print 'debfile command with any sort of expediency, you\'ll need '
            print 'it.  You can use a python equivalent, but it\'s about two '
            print 'orders of magnitude slower.  THIS MEANS IT WILL TAKE AGES '
            print 'TO RUN THIS COMMAND.  Don\'t do this.'
            if yn('Do you want to use a Python equivalent of zegrep?') == 'y':
                onStart.append('usepythonzegrep')
            else:
                print 'I\'ll disable debfile now.'
                onStart.append('disable debfile')


class Debian(callbacks.Privmsg, PeriodicFileDownloader):
    threaded = True
    periodicFiles = {
        'Contents-i386.gz': ('ftp://ftp.us.debian.org/'
                             'debian/dists/unstable/Contents-i386.gz',
                             86400, None)
        }
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        PeriodicFileDownloader.__init__(self)
        self.usePythonZegrep = False

    def usepythonzegrep(self, irc, msg, args):
        """takes no arguments"""
        self.usePythonZegrep = not self.usePythonZegrep
        irc.reply(msg, conf.replySuccess)

    def debfile(self, irc, msg, args):
        self.getFile('Contents-i386.gz')
        regexp = privmsgs.getArgs(args).lstrip('/')
        try:
            r = re.compile(regexp, re.I)
        except sre_constants.error, e:
            irc.error(msg, e)
            return
        if self.usePythonZegrep:
            fd = gzip.open('Contents-i386.gz')
            fd = ifilter(imap(lambda line: r.search(line), fd))
        (fd, _) = popen2.popen2(['zegrep', regexp, 'Contents-i386.gz'])
        packages = []
        for line in fd:
            (filename, package) = line[:-1].split()
            if r.search(filename):
                packages.extend(package.split(','))
            if len(packages) > 40:
                irc.error(msg, '>40 results returned, be more specific.')
                return
        if len(packages) == 0:
            irc.reply(msg, 'I found no packages with that file.')
        else:
            irc.reply(msg, ircutils.privmsgPayload(packages, ', '))
                

Class = Debian

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
