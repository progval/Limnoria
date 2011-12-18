###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008-2010, James Vega
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
import random
import select
import struct
import subprocess
import shlex

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Unix')

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
    threaded = True
    @internationalizeDocstring
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
                irc.reply(_('I can\'t find the errno number for that code.'))
                return
        except KeyError:
            name = _('(unknown)')
        irc.reply(format(_('%s (#%i): %s'), name, i, os.strerror(i)))
    errno = wrap(errno, ['something'])

    @internationalizeDocstring
    def progstats(self, irc, msg, args):
        """takes no arguments

        Returns various unix-y information on the running supybot process.
        """
        irc.reply(progstats())

    @internationalizeDocstring
    def pid(self, irc, msg, args):
        """takes no arguments

        Returns the current pid of the process for this Supybot.
        """
        irc.reply(format('%i', os.getpid()), private=True)
    pid = wrap(pid, [('checkCapability', 'owner')])

    _cryptre = re.compile(r'[./0-9A-Za-z]')
    @internationalizeDocstring
    def crypt(self, irc, msg, args, password, salt):
        """<password> [<salt>]

        Returns the resulting of doing a crypt() on <password>.  If <salt> is
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

    @internationalizeDocstring
    def spell(self, irc, msg, args, word):
        """<word>

        Returns the result of passing <word> to aspell/ispell.  The results
        shown are sorted from best to worst in terms of being a likely match
        for the spelling of <word>.
        """
        # We are only checking the first word
        spellCmd = self.registryValue('spell.command')
        if not spellCmd:
           irc.error(_('The spell checking command is not configured.  If one '
                     'is installed, reconfigure '
                     'supybot.plugins.Unix.spell.command appropriately.'),
                     Raise=True)
        if word and not word[0].isalpha():
            irc.error(_('<word> must begin with an alphabet character.'))
            return
        try:
            inst = subprocess.Popen([spellCmd, '-a'], close_fds=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    stdin=subprocess.PIPE)
        except OSError, e:
            irc.error(e, Raise=True)
        ret = inst.poll()
        if ret is not None:
            s = inst.stderr.readline()
            if not s:
                s = inst.stdout.readline()
            s = s.rstrip('\r\n')
            s = s.lstrip('Error: ')
            irc.error(s, Raise=True)
        (out, err) = inst.communicate(word)
        inst.wait()
        lines = filter(None, out.splitlines())
        lines.pop(0) # Banner
        if not lines:
            irc.error(_('No results found.'), Raise=True)
        line = lines.pop(0)
        line2 = ''
        if lines:
            line2 = lines.pop(0)
        # parse the output
        # aspell will sometimes list spelling suggestions after a '*' or '+'
        # line for complex words.
        if line[0] in '*+' and line2:
            line = line2
        if line[0] in '*+':
            resp = format(_('%q may be spelled correctly.'), word)
        elif line[0] == '#':
            resp = format(_('I could not find an alternate spelling for %q'),
                          word)
        elif line[0] == '&':
            matches = line.split(':')[1].strip()
            resp = format(_('Possible spellings for %q: %L.'),
                          word, matches.split(', '))
        else:
            resp = 'Something unexpected was seen in the [ai]spell output.'
        irc.reply(resp)
    spell = thread(wrap(spell, ['something']))

    @internationalizeDocstring
    def fortune(self, irc, msg, args):
        """takes no arguments

        Returns a fortune from the *nix fortune program.
        """
        channel = msg.args[0]
        fortuneCmd = self.registryValue('fortune.command')
        if fortuneCmd:
            args = [fortuneCmd]
            if self.registryValue('fortune.short', channel):
                args.append('-s')
            if self.registryValue('fortune.equal'):
                args.append('-e')
            if self.registryValue('fortune.offensive', channel):
                args.append('-a')
            args.extend(self.registryValue('fortune.files'))
            try:
                inst = subprocess.Popen(args, close_fds=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdin=file(os.devnull))
            except OSError, e:
                irc.error(_('It seems the configured fortune command was '
                          'not available.'), Raise=True)
            (out, err) = inst.communicate()
            inst.wait()
            lines = out.splitlines()
            lines = map(str.rstrip, lines)
            lines = filter(None, lines)
            irc.replies(lines, joiner=' ')
        else:
            irc.error(_('The fortune command is not configured. If fortune is '
                      'installed on this system, reconfigure the '
                      'supybot.plugins.Unix.fortune.command configuration '
                      'variable appropriately.'))

    @internationalizeDocstring
    def wtf(self, irc, msg, args, _, something):
        """[is] <something>

        Returns wtf <something> is.  'wtf' is a *nix command that first
        appeared in NetBSD 1.5.  In most *nices, it's available in some sort
        of 'bsdgames' package.
        """
        wtfCmd = self.registryValue('wtf.command')
        if wtfCmd:
            something = something.rstrip('?')
            try:
                inst = subprocess.Popen([wtfCmd, something], close_fds=True,
                                        stdout=subprocess.PIPE,
                                        stderr=file(os.devnull),
                                        stdin=file(os.devnull))
            except OSError:
                irc.error(_('It seems the configured wtf command was not '
                          'available.'), Raise=True)
            (out, _) = inst.communicate()
            inst.wait()
            if out:
                response = out.splitlines()[0].strip()
                response = utils.str.normalizeWhitespace(response)
                irc.reply(response)
        else:
            irc.error(_('The wtf command is not configured.  If it is installed '
                      'on this system, reconfigure the '
                      'supybot.plugins.Unix.wtf.command configuration '
                      'variable appropriately.'))
    wtf = thread(wrap(wtf, [optional(('literal', ['is'])), 'something']))

    @internationalizeDocstring
    def ping(self, irc, msg, args, optlist, host):
        """[--c <count>] [--i <interval>] [--t <ttl>] [--W <timeout>] <host or ip>
        Sends an ICMP echo request to the specified host.
        The arguments correspond with those listed in ping(8). --c is
        limited to 10 packets or less (default is 5). --i is limited to 5
        or less. --W is limited to 10 or less.
        """
        pingCmd = self.registryValue('ping.command')
        if not pingCmd:
           irc.error('The ping command is not configured.  If one '
                     'is installed, reconfigure '
                     'supybot.plugins.Unix.ping.command appropriately.',
                     Raise=True)
        else:
            try: host = host.group(0)
            except AttributeError: pass

            args = [pingCmd]
            for opt, val in optlist:
                if opt == 'c' and val > 10: val = 10
                if opt == 'i' and val >  5: val = 5
                if opt == 'W' and val > 10: val = 10
                args.append('-%s' % opt)
                args.append(str(val))
            if '-c' not in args:
                args.append('-c')
                args.append('5')
            args.append(host)
            try:
                inst = subprocess.Popen(args, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE,
                                              stdin=file(os.devnull))
            except OSError, e:
                irc.error('It seems the configured ping command was '
                          'not available (%s).' % e, Raise=True)
            result = inst.communicate()
            if result[1]: # stderr
                irc.error(' '.join(result[1].split()))
            else:
                response = result[0].split("\n");
                if response[1]:
                    irc.reply(' '.join(response[1].split()[3:5]).split(':')[0]
                              + ': ' + ' '.join(response[-3:]))
                else:
                    irc.reply(' '.join(response[0].split()[1:3])
                              + ': ' + ' '.join(response[-3:]))

    _hostExpr = re.compile(r'^[a-z0-9][a-z0-9\.-]*[a-z0-9]$', re.I)
    ping = thread(wrap(ping, [getopts({'c':'positiveInt','i':'float',
                                't':'positiveInt','W':'positiveInt'}), 
                       first('ip', ('matches', _hostExpr, 'Invalid hostname'))]))

    def call(self, irc, msg, args, text):
        """<command to call with any arguments> 
        Calls any command available on the system, and returns its output.
        Requires owner capability.
        Note that being restricted to owner, this command does not do any
        sanity checking on input/output. So it is up to you to make sure
        you don't run anything that will spamify your channel or that 
        will bring your machine to its knees. 
        """
        args = shlex.split(text)
        try:
            inst = subprocess.Popen(args, stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE,
                                          stdin=file(os.devnull))
        except OSError, e:
            irc.error('It seems the requested command was '
                      'not available (%s).' % e, Raise=True)
        result = inst.communicate()
        if result[1]: # stderr
            irc.error(' '.join(result[1].split()))
        if result[0]: # stdout
            response = result[0].split("\n");
            response = [l for l in response if l]
            irc.replies(response)
    call = thread(wrap(call, ["owner", "text"]))

Class = Unix
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
