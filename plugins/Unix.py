###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

import supybot.plugins as plugins

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

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Unix', True)
    output("""The "progstats" command can reveal potentially sensitive
              information about your machine. Here's an example of its output:

              %s\n""" % progstats())
    if yn('Would you like to disable this command for non-owner users?',
          default=True):
        conf.supybot.commands.disabled().add('Unix.progstats')

def progstats():
    pw = pwd.getpwuid(os.getuid())
    response = 'Process ID %s running as user "%s" and as group "%s" ' \
               'from directory "%s" with the command line "%s".  ' \
               'Running on Python %s.' % \
               (os.getpid(), pw[0], pw[3],
                os.getcwd(), ' '.join(sys.argv),
                sys.version.translate(string.ascii, '\r\n'))
    return response

class TimeoutError(IOError):
    pass

def pipeReadline(fd, timeout=2):
    (r, _, _) = select.select([fd], [], [], timeout)
    if r:
        return r[0].readline()
    else:
        raise TimeoutError

conf.registerPlugin('Unix')
conf.registerGroup(conf.supybot.plugins.Unix, 'fortune')
conf.registerGlobalValue(conf.supybot.plugins.Unix.fortune, 'command',
    registry.String(utils.findBinaryInPath('fortune') or '', """Determines what
    command will be called for the fortune command."""))
conf.registerGlobalValue(conf.supybot.plugins.Unix.fortune, 'short',
    registry.Boolean(True, """Determines whether only short fortunes will be
    used if possible.  This sends the -s option to the fortune program."""))
conf.registerGlobalValue(conf.supybot.plugins.Unix.fortune, 'equal',
    registry.Boolean(True, """Determines whether fortune will give equal
    weight to the different fortune databases.  If false, then larger
    databases will be given more weight.  This sends the -e option to the
    fortune program."""))
conf.registerGlobalValue(conf.supybot.plugins.Unix.fortune, 'offensive',
    registry.Boolean(False, """Determines whether fortune will retrieve
    offensive fortunes along with the normal fortunes.  This sends the -o
    option to the fortune program."""))
conf.registerGlobalValue(conf.supybot.plugins.Unix.fortune, 'files',
    registry.SpaceSeparatedListOfStrings([], """Determines what specific file
    (if any) will be used with the fortune command; if none is given, the
    system-wide default will be used.  Do note that this fortune file must be
    placed with the rest of your system's fortune files."""))

conf.registerGroup(conf.supybot.plugins.Unix, 'spell')
conf.registerGlobalValue(conf.supybot.plugins.Unix.spell, 'command',
    registry.String(utils.findBinaryInPath('aspell') or
                    utils.findBinaryInPath('ispell') or '', """Determines what
    command will be called for the spell command."""))

conf.registerGroup(conf.supybot.plugins.Unix, 'wtf')
conf.registerGlobalValue(conf.supybot.plugins.Unix.wtf, 'command',
    registry.String(utils.findBinaryInPath('wtf') or '', """Determines what
    command will be called for the wtf command."""))


class Unix(callbacks.Privmsg):
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
        irc.reply('%s (#%s): %s' % (name, i, os.strerror(i)))
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
        irc.reply(str(os.getpid()), private=True)
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
                s = struct.pack('<h', random.randrange(2**16))
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
            except TimeoutError:
                irc.error('The spell command timed out.')
                return
        finally:
            r.close()
            w.close()
            inst.wait()
        # parse the output
        if line[0] in '*+':
            resp = '"%s" may be spelled correctly.' % word
        elif line[0] == '#':
            resp = 'I could not find an alternate spelling for "%s"' % word
        elif line[0] == '&':
            matches = line.split(':')[1].strip()
            resp = 'Possible spellings for %s: %s.' % \
                   (utils.quoted(word), utils.commaAndify(matches.split(', ')))
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
                response = utils.normalizeWhitespace(r.readline().strip())
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

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
