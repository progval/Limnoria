###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008-2010, James McCoy
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

import os
import re
import pwd
import sys
import errno
import random
import select
import struct
import subprocess
import shlex

try:
    import crypt
except ImportError:
    # Python >= 3.13
    crypt = None

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Unix')

def checkAllowShell(irc):
    if not conf.supybot.commands.allowShell():
        irc.error(_('This command is not available, because '
            'supybot.commands.allowShell is False.'), Raise=True)

_progstats_endline_remover = utils.str.MultipleRemover('\r\n')
def progstats():
    pw = pwd.getpwuid(os.getuid())
    response = format('Process ID %i running as user %q and as group %q '
                      'from directory %q with the command line %q.  '
                      'Running on Python %s.',
                      os.getpid(), pw[0], pw[3],
                      os.getcwd(), ' '.join(sys.argv),
                      _progstats_endline_remover(sys.version))
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
    """Provides Utilities for Unix-like systems."""
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

    if crypt is not None:  # Python < 3.13
        _cryptre = re.compile(b'[./0-9A-Za-z]')
        @internationalizeDocstring
        def crypt(self, irc, msg, args, password, salt):
            """<password> [<salt>]

            Returns the resulting of doing a crypt() on <password>.  If <salt> is
            not given, uses a random salt.  If running on a glibc2 system,
            prepending '$1$' to your salt will cause crypt to return an MD5sum
            based crypt rather than the standard DES based crypt.
            """
            def makeSalt():
                s = b'\x00'
                while self._cryptre.sub(b'', s) != b'':
                    s = struct.pack('<h', random.randrange(-(2**15), 2**15))
                return s
            if not salt:
                salt = makeSalt().decode()
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
        spellLang = self.registryValue('spell.language') or 'en'
        if word and not word[0].isalpha():
            irc.error(_('<word> must begin with an alphabet character.'))
            return
        try:
            inst = subprocess.Popen([spellCmd, '-l', spellLang, '-a'], close_fds=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    stdin=subprocess.PIPE)
        except OSError as e:
            irc.error(e, Raise=True)
        ret = inst.poll()
        if ret is not None:
            s = inst.stderr.readline().decode('utf8')
            if not s:
                s = inst.stdout.readline().decode('utf8')
            s = s.rstrip('\r\n')
            s = s.lstrip('Error: ')
            irc.error(s, Raise=True)
        (out, err) = inst.communicate(word.encode())
        inst.wait()
        lines = [x.decode('utf8') for x in out.splitlines() if x]
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
            resp = _('Something unexpected was seen in the [ai]spell output.')
        irc.reply(resp)
    spell = thread(wrap(spell, ['something']))

    @internationalizeDocstring
    def fortune(self, irc, msg, args):
        """takes no arguments

        Returns a fortune from the Unix fortune program.
        """
        channel = msg.channel
        network = irc.network
        fortuneCmd = self.registryValue('fortune.command')
        if fortuneCmd:
            args = [fortuneCmd]
            if self.registryValue('fortune.short', channel, network):
                args.append('-s')
            if self.registryValue('fortune.equal', channel, network):
                args.append('-e')
            if self.registryValue('fortune.offensive', channel, network):
                args.append('-a')
            args.extend(self.registryValue('fortune.files', channel, network))
            try:
                with open(os.devnull) as null:
                    inst = subprocess.Popen(args,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            stdin=null)
            except OSError as e:
                irc.error(_('It seems the configured fortune command was '
                          'not available.'), Raise=True)
            (out, err) = inst.communicate()
            inst.wait()
            if minisix.PY3:
                lines = [i.decode('utf-8').rstrip() for i in out.splitlines()]
                lines = list(map(str, lines))
            else:
                lines = out.splitlines()
                lines = list(map(str.rstrip, lines))
            lines = filter(None, lines)
            irc.replies(lines, joiner=' ')
        else:
            irc.error(_('The fortune command is not configured. If fortune is '
                      'installed on this system, reconfigure the '
                      'supybot.plugins.Unix.fortune.command configuration '
                      'variable appropriately.'))

    @internationalizeDocstring
    def wtf(self, irc, msg, args, foo, something):
        """[is] <something>

        Returns wtf <something> is.  'wtf' is a Unix command that first
        appeared in NetBSD 1.5.  In most Unices, it's available in some sort
        of 'bsdgames' package.
        """
        wtfCmd = self.registryValue('wtf.command')
        if wtfCmd:
            something = something.rstrip('?')
            try:
                with open(os.devnull, 'r+') as null:
                    inst = subprocess.Popen([wtfCmd, something],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT,
                                            stdin=null)
            except OSError:
                irc.error(_('It seems the configured wtf command was not '
                          'available.'), Raise=True)
            (out, foo) = inst.communicate()
            inst.wait()
            if out:
                response = out.decode('utf8').splitlines()[0].strip()
                response = utils.str.normalizeWhitespace(response)
                irc.reply(response)
        else:
            irc.error(_('The wtf command is not configured.  If it is installed '
                      'on this system, reconfigure the '
                      'supybot.plugins.Unix.wtf.command configuration '
                      'variable appropriately.'))
    wtf = thread(wrap(wtf, [optional(('literal', ['is'])), 'something']))

    def _make_ping(command):
        def f(self, irc, msg, args, optlist, host):
            """[--c <count>] [--i <interval>] [--t <ttl>] [--W <timeout>] [--4|--6] <host or ip>

            Sends an ICMP echo request to the specified host.
            The arguments correspond with those listed in ping(8). --c is
            limited to 10 packets or less (default is 5). --i is limited to 5
            or less. --W is limited to 10 or less.
            --4 and --6 can be used if and only if the system has a unified
            ping command.
            """
            pingCmd = self.registryValue(registry.join([command, 'command']))
            if not pingCmd:
               irc.error('The ping command is not configured.  If one '
                         'is installed, reconfigure '
                         'supybot.plugins.Unix.%s.command appropriately.' %
                         command, Raise=True)
            else:
                try: host = host.group(0)
                except AttributeError: pass

                args = [pingCmd]
                for opt, val in optlist:
                    if opt == 'c' and val > 10: val = 10
                    if opt == 'i' and val >  5: val = 5
                    if opt == 'W' and val > 10: val = 10
                    args.append('-%s' % opt)
                    if opt not in ('4', '6'):
                        args.append(str(val))
                if '-c' not in args:
                    args.append('-c')
                    args.append(str(self.registryValue('ping.defaultCount')))
                args.append(host)
                try:
                    with open(os.devnull) as null:
                        inst = subprocess.Popen(args,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE,
                                                stdin=null)
                except OSError as e:
                    irc.error('It seems the configured ping command was '
                              'not available (%s).' % e, Raise=True)
                result = inst.communicate()
                if result[1]: # stderr
                    irc.error(' '.join(result[1].decode('utf8').split()))
                else:
                    response = result[0].decode('utf8').split("\n");
                    if response[1]:
                        irc.reply(' '.join(response[1].split()[3:5]).split(':')[0]
                                  + ': ' + ' '.join(response[-3:]))
                    else:
                        irc.reply(' '.join(response[0].split()[1:3])
                                  + ': ' + ' '.join(response[-3:]))

        f.__name__ = command
        _hostExpr = re.compile(r'^[a-z0-9][a-z0-9\.-]*[a-z0-9]$', re.I)
        return thread(wrap(f, [getopts({'c':'positiveInt','i':'float',
                                        't':'positiveInt','W':'positiveInt',
                                        '4':'', '6':''}),
                           first('ip', ('matches', _hostExpr, 'Invalid hostname'))]))

    ping = _make_ping('ping')
    ping6 = _make_ping('ping6')

    def sysuptime(self, irc, msg, args):
        """takes no arguments

        Returns the uptime from the system the bot is running on.
        """
        uptimeCmd = self.registryValue('sysuptime.command')
        if uptimeCmd:
            args = [uptimeCmd]
            try:
                with open(os.devnull) as null:
                    inst = subprocess.Popen(args,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            stdin=null)
            except OSError as e:
                irc.error('It seems the configured uptime command was '
                          'not available.', Raise=True)
            (out, err) = inst.communicate()
            inst.wait()
            lines = out.splitlines()
            lines = [x.decode('utf8').rstrip() for x in lines]
            lines = filter(None, lines)
            irc.replies(lines, joiner=' ')
        else:
            irc.error('The uptime command is not configured. If uptime is '
                      'installed on this system, reconfigure the '
                      'supybot.plugins.Unix.sysuptime.command configuration '
                      'variable appropriately.')

    def sysuname(self, irc, msg, args):
        """takes no arguments

        Returns the uname -a from the system the bot is running on.
        """
        unameCmd = self.registryValue('sysuname.command')
        if unameCmd:
            args = [unameCmd, '-a']
            try:
                with open(os.devnull) as null:
                    inst = subprocess.Popen(args,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            stdin=null)
            except OSError as e:
                irc.error('It seems the configured uptime command was '
                          'not available.', Raise=True)
            (out, err) = inst.communicate()
            inst.wait()
            lines = out.splitlines()
            lines = [x.decode('utf8').rstrip() for x in lines]
            lines = filter(None, lines)
            irc.replies(lines, joiner=' ')
        else:
            irc.error('The uname command is not configured. If uname is '
                      'installed on this system, reconfigure the '
                      'supybot.plugins.Unix.sysuname.command configuration '
                      'variable appropriately.')

    def call(self, irc, msg, args, text):
        """<command to call with any arguments>
        Calls any command available on the system, and returns its output.
        Requires owner capability.
        Note that being restricted to owner, this command does not do any
        sanity checking on input/output. So it is up to you to make sure
        you don't run anything that will spamify your channel or that
        will bring your machine to its knees.
        """
        checkAllowShell(irc)
        self.log.info('Unix: running command "%s" for %s/%s', text, msg.nick,
                      irc.network)
        args = shlex.split(text)
        try:
            with open(os.devnull) as null:
                inst = subprocess.Popen(args,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdin=null)
        except OSError as e:
            irc.error('It seems the requested command was '
                      'not available (%s).' % e, Raise=True)
        result = inst.communicate()
        if result[1]: # stderr
            irc.error(' '.join(result[1].decode('utf8').split()))
        if result[0]: # stdout
            response = result[0].decode('utf8').splitlines()
            response = [l for l in response if l]
            irc.replies(response)
    call = thread(wrap(call, ["owner", "text"]))

    def shell(self, irc, msg, args, text):
        """<command to call with any arguments>
        Calls any command available on the system using the shell
        specified by the SHELL environment variable, and returns its
        output.
        Requires owner capability.
        Note that being restricted to owner, this command does not do any
        sanity checking on input/output. So it is up to you to make sure
        you don't run anything that will spamify your channel or that
        will bring your machine to its knees.
        """
        checkAllowShell(irc)
        self.log.info('Unix: running command "%s" for %s/%s', text, msg.nick,
                      irc.network)
        try:
            with open(os.devnull) as null:
                inst = subprocess.Popen(text,
                                        shell=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdin=null)
        except OSError as e:
            irc.error('It seems the shell (%s) was not available (%s)' %
                      (os.getenv('SHELL'), e), Raise=True)
        result = inst.communicate()
        if result[1]: # stderr
            irc.error(' '.join(result[1].decode('utf8').split()))
        if result[0]: # stdout
            response = result[0].decode('utf8').splitlines()
            response = [l for l in response if l]
            irc.replies(response)
    shell = thread(wrap(shell, ["owner", "text"]))


Class = Unix
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
