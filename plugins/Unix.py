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
"""

__revision__ = "$Id$"

import plugins

import os
import re
import pwd
import sys
import crypt
import errno
import popen2
import random
import select
import string
import struct


import privmsgs
import callbacks
import utils

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, something, yn
    onStart.append('load Unix')
    spellCmd = utils.findBinaryInPath('aspell')
    if not spellCmd:
        spellCmd = utils.findBinaryInPath('ispell')
    if not spellCmd:
        print 'NOTE: I couldn\'t find aspell or ispell in your path,'
        print 'so that function of this module will not work.  You may'
        print 'choose to install it later.  To re-enable this command then, '
        print 'remove the "disable spell" line from your configuration file.'
        onStart.append('disable spell')
    fortuneCmd = utils.findBinaryInPath('fortune')
    if not fortuneCmd:
        print 'NOTE: I couldn\'t find fortune in your path, so that function '
        print 'of this module will not work.  You may choose to install it '
        print 'later.  To re-enable this command then, remove the '
        print '"disable fortune" command from your configuration file.'
        onStart.append('disable fortune')
    wtfCmd = utils.findBinaryInPath('wtf')
    if not wtfCmd:
        print 'NOTE: I couldn\'t find wtf in your path, so that function of '
        print 'this module won\'t work.  You may choose to install it later; '
        print 'to re-enable this command then, remove the "disable wtf" '
        print 'command from your configuration file or simply tell the bot '
        print '"enable wtf"'
        onStart.append('disable wtf')
    print 'The "progstats" command can reveal potentially sensitive'
    print 'information about your machine.  Here\'s an example of its output:'
    print
    print progstats()
    print
    if yn('Would you like to disable this command for non-owner users?')=='y':
        onStart.append('disable progstats')

def progstats():
    pw = pwd.getpwuid(os.getuid())
    response = 'Process ID %i running as user "%s" and as group "%s" ' \
               'from directory "%s" with the command line "%s".  ' \
               'Running on Python %s.' % \
               (os.getpid(), pw[0], pw[3],
                os.getcwd(), " ".join(sys.argv),
                sys.version.translate(string.ascii, '\r\n'))
    return response

class TimeoutError(IOError):
    pass

def pipeReadline(fd, timeout=0.75):
    (r, _, _) = select.select([fd], [], [], timeout)
    if r:
        return r[0].readline()
    else:
        raise TimeoutError
    


class Unix(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.spellCmd = utils.findBinaryInPath('aspell')
        if not self.spellCmd:
            self.spellCmd = utils.findBinaryInPath('ispell')
        self.fortuneCmd = utils.findBinaryInPath('fortune')
        self.wtfCmd = utils.findBinaryInPath('wtf')

    def errno(self, irc, msg, args):
        """<error number or code>

        Returns the number of an errno code, or the errno code of a number.
        """
        s = privmsgs.getArgs(args)
        try:
            i = int(s)
            name = errno.errorcode[i]
        except ValueError:
            name = s.upper()
            try:
                i = getattr(errno, name)
            except AttributeError:
                irc.reply('I can\'t find the errno number for that code.')
                return
        except KeyError:
            name = '(unknown)'
        irc.reply('%s (#%s): %s' % (name, i, os.strerror(i)))

    def progstats(self, irc, msg, args):
        """takes no arguments

        Returns various unix-y information on the running supybot process.
        """
        irc.reply(progstats())

    _cryptre = re.compile(r'[./0-9A-Za-z]')
    def crypt(self, irc, msg, args):
        """<password> [<salt>]

        Returns the resulting of doing a crypt() on <password>  If <salt> is
        not given, uses a random salt.  If running on a glibc2 system,
        prepending '$1$' to your salt will cause crypt to return an MD5sum
        based crypt rather than the standard DES based crypt.
        """
        def makeSalt():
            s = '\x00'
            while self._cryptre.sub('', s) != '':
                s = struct.pack('<h', random.randrange(2**16))
            return s
        (password, salt) = privmsgs.getArgs(args, optional=1)
        if salt == '':
            salt = makeSalt()
        irc.reply(crypt.crypt(password, salt))

    def spell(self, irc, msg, args):
        """<word>

        Returns the result of passing <word> to aspell/ispell.  The results
        shown are sorted from best to worst in terms of being a likely match
        for the spelling of <word>.
        """
        # We are only checking the first word
        if not self.spellCmd:
           irc.error('A spell checking command doesn\'t seem to be '
                          'installed on this computer.')
           return
        word = privmsgs.getArgs(args)
        if word and not word[0].isalpha():
            irc.error('<word> must begin with an alphabet character.')
            return
        if ' ' in word:
            irc.error('Spaces aren\'t allowed in the word.')
            return
        try:
            (r, w) = popen2.popen4([self.spellCmd, '-a'])
            s = r.readline() # Banner, hopefully.
            if 'sorry' in s.lower():
                irc.error(s)
                return
            w.write(word)
            w.write('\n')
            w.flush()
            try:
                line = pipeReadline(r)
                # aspell puts extra whitespace, ignore it
                while not line.strip('\r\n'):
                    line = pipeReadline(r)
            except TimeoutError:
                irc.error('The spell command timed out.')
                return
        finally:
            r.close()
            w.close()
        # parse the output
        if line[0] in '*+':
            resp = '"%s" may be spelled correctly.' % word
        elif line[0] == '#':
            resp = 'Could not find an alternate spelling for "%s"' % word
        elif line[0] == '&':
            matches = line.split(':')[1].strip()
            resp = 'Possible spellings for %r: %s.' % \
                   (word, utils.commaAndify(matches.split(', ')))
        else:
            resp = 'Something unexpected was seen in the [ai]spell output.'
        irc.reply(resp)

    def fortune(self, irc, msg, args):
        """takes no arguments

        Returns a fortune from the *nix fortune program.
        """
        if self.fortuneCmd is not None:
            (r, w) = popen2.popen4('%s -s' % self.fortuneCmd)
            s = r.read()
            w.close()
            r.close()
            irc.reply(' '.join(s.split()))
        else:
            irc.error('I couldn\'t find the fortune command.')

    def wtf(self, irc, msg, args):
        """[is] <something>

        Returns wtf <something> is.  'wtf' is a *nix command that first
        appeared in NetBSD 1.5.  In most *nices, it's available in some sort
        of 'bsdgames' package.
        """
        if self.wtfCmd is not None:
            if args and args[0] == 'is':
                del args[0]
            something = privmsgs.getArgs(args)
            something = something.rstrip('?')
            (r, w) = popen2.popen4([self.wtfCmd, something])
            response = utils.normalizeWhitespace(r.readline().strip())
            irc.reply(response)
            r.close()
            w.close()
        else:
            irc.error('I couldn\'t find the wtf command.')


Class = Unix
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

