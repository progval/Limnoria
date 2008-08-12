###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008, James Vega
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

import os
import re
import pwd
import sys
import crypt
import errno
import popen2
import random
import select
import struct

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

def progstats():
    pw = pwd.getpwuid(os.getuid())
    response = format('Process ID %i running as user %q and as group %q '
                      'from directory %q with the command line %q.  '
                      'Running on Python %s.',
                      os.getpid(), pw[0], pw[3],
                      os.getcwd(), ' '.join(sys.argv),
                      sys.version.translate(utils.str.chars, '\r\n'))
    return response

class TimeoutError(IOError):
    pass

def pipeReadline(fd, timeout=2):
    (r, _, _) = select.select([fd], [], [], timeout)
    if r:
        return r[0].readline()
    else:
        raise TimeoutError

class Unix(callbacks.Plugin):
    def errno(self, irc, msg, args, s):
        """<error number or code>

        Returns the number of an errno code, or the errno code of a number.
        """
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
        irc.reply(format('%s (#%i): %s', name, i, os.strerror(i)))
    errno = wrap(errno, ['something'])

    def progstats(self, irc, msg, args):
        """takes no arguments

        Returns various unix-y information on the running supybot process.
        """
        irc.reply(progstats())

    def pid(self, irc, msg, args):
        """takes no arguments

        Returns the current pid of the process for this Supybot.
        """
        irc.reply(format('%i', os.getpid()), private=True)
    pid = wrap(pid, [('checkCapability', 'owner')])

    _cryptre = re.compile(r'[./0-9A-Za-z]')
    def crypt(self, irc, msg, args, password, salt):
        """<password> [<salt>]

        Returns the resulting of doing a crypt() on <password>  If <salt> is
        not given, uses a random salt.  If running on a glibc2 system,
        prepending '$1$' to your salt will cause crypt to return an MD5sum
        based crypt rather than the standard DES based crypt.
        """
        def makeSalt():
            s = '\x00'
            while self._cryptre.sub('', s) != '':
                s = struct.pack('<h', random.randrange(-(2**15), 2**15))
            return s
        if not salt:
            salt = makeSalt()
        irc.reply(crypt.crypt(password, salt))
    crypt = wrap(crypt, ['something', additional('something')])

    def spell(self, irc, msg, args, word):
        """<word>

        Returns the result of passing <word> to aspell/ispell.  The results
        shown are sorted from best to worst in terms of being a likely match
        for the spelling of <word>.
        """
        # We are only checking the first word
        spellCmd = self.registryValue('spell.command')
        if not spellCmd:
           irc.error('A spell checking command doesn\'t seem to be '
                     'installed on this computer.  If one is installed, '
                     'reconfigure supybot.plugins.Unix.spell.command '
                     'appropriately.', Raise=True)
        if word and not word[0].isalpha():
            irc.error('<word> must begin with an alphabet character.')
            return
        if ' ' in word:
            irc.error('Spaces aren\'t allowed in the word.')
            return
        inst = popen2.Popen4([spellCmd, '-a'])
        (r, w) = (inst.fromchild, inst.tochild)
        try:
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
                # cache an extra line in case aspell's first line says the word
                # is spelled correctly, but subsequent lines offer spelling
                # suggestions
                line2 = pipeReadline(r)
            except TimeoutError:
                irc.error('The spell command timed out.')
                return
        finally:
            r.close()
            w.close()
            inst.wait()
        # parse the output
        # aspell will sometimes list spelling suggestions after a '*' or '+'
        # line for complex words.
        if line[0] in '*+' and line2.strip('\r\n'):
            line = line2
        if line[0] in '*+':
            resp = format('%q may be spelled correctly.', word)
        elif line[0] == '#':
            resp = format('I could not find an alternate spelling for %q',word)
        elif line[0] == '&':
            matches = line.split(':')[1].strip()
            resp = format('Possible spellings for %q: %L.',
                          word, matches.split(', '))
        else:
            resp = 'Something unexpected was seen in the [ai]spell output.'
        irc.reply(resp)
    spell = wrap(spell, ['something'])

    def fortune(self, irc, msg, args):
        """takes no arguments

        Returns a fortune from the *nix fortune program.
        """
        fortuneCmd = self.registryValue('fortune.command')
        if fortuneCmd:
            args = [fortuneCmd]
            if self.registryValue('fortune.short'):
                args.append('-s')
            if self.registryValue('fortune.equal'):
                args.append('-e')
            if self.registryValue('fortune.offensive'):
                args.append('-a')
            args.extend(self.registryValue('fortune.files'))
            inst = popen2.Popen4(args)
            (r, w) = (inst.fromchild, inst.tochild)
            try:
                lines = r.readlines()
                lines = map(str.rstrip, lines)
                lines = filter(None, lines)
                if lines:
                    irc.replies(lines, joiner=' ')
                else:
                    irc.error('It seems the configured fortune command was '
                              'not available.')
            finally:
                w.close()
                r.close()
                inst.wait()
        else:
            irc.error('I couldn\'t find the fortune command on this system. '
                      'If it is installed on this system, reconfigure the '
                      'supybot.plugins.Unix.fortune.command configuration '
                      'variable appropriately.')

    def wtf(self, irc, msg, args, _, something):
        """[is] <something>

        Returns wtf <something> is.  'wtf' is a *nix command that first
        appeared in NetBSD 1.5.  In most *nices, it's available in some sort
        of 'bsdgames' package.
        """
        wtfCmd = self.registryValue('wtf.command')
        if wtfCmd:
            def commandError():
                irc.error('It seems the configured wtf command '
                          'was not available.')
            something = something.rstrip('?')
            inst = popen2.Popen4([wtfCmd, something])
            (r, w) = (inst.fromchild, inst.tochild)
            try:
                response = utils.str.normalizeWhitespace(r.readline().strip())
                if response:
                    irc.reply(response)
                else:
                    commandError()
            finally:
                r.close()
                w.close()
                inst.wait()
        else:
            irc.error('I couldn\'t find the wtf command on this system.  '
                      'If it is installed on this system, reconfigure the '
                      'supybot.plugins.Unix.wtf.command configuration '
                      'variable appropriately.')
    wtf = wrap(wtf, [optional(('literal', ['is'])), 'something'])


Class = Unix


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
