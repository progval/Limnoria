###
# Copyright (c) 2010, Valentin Lorentz
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

# pysandbox were originally writen by haypo (under the BSD license), 
# and fschfsch by Tila (under the WTFPL license).

###

IN_MAXLEN = 1000 # bytes
OUT_MAXLEN = 1000 # bytes
TIMEOUT = 3  # seconds

EVAL_MAXTIMESECONDS = TIMEOUT
EVAL_MAXMEMORYBYTES = 75 * 1024 * 1024 # 10 MiB

try:
    import sandbox as S
except ImportError:
    print 'You need pysandbox in order to run fschfsch ' + \
          '[http://github.com/haypo/pysandbox].'
    raise
import re
import os
import sys
import time
import random
import select
import resource as R
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from cStringIO import StringIO


def createSandboxConfig():
    cfg = S.SandboxConfig(
        'stdout',
        'stderr',
        'regex',
        'unicodedata', # flow wants u'\{ATOM SYMBOL}' :-)
        'future',
        'code',
        'time',
        'datetime',
        'math',
        'itertools',
        'random',
        'encodings',
    )
    cfg.allowModule('sys',
        'version', 'hexversion', 'version_info')
    return cfg

def _evalPython(line, locals):
    locals = dict(locals)
    try:
        if "\n" in line:
            raise SyntaxError()
        code = compile(line, "<irc>", "single")
    except SyntaxError:
        code = compile(line, "<irc>", "exec")
    exec code in locals

def evalPython(line, locals=None):
    sandbox = S.Sandbox(config=createSandboxConfig())

    if locals is not None:
        locals = dict(locals)
    else:
        locals = dict()
    try:
        sandbox.call(_evalPython, line, locals)
    except BaseException, e:
        print 'Error: [%s] %s' % (e.__class__.__name__, str(e))
    except:
        print 'Error: <unknown exception>'
    sys.stdout.flush()

def check_output(expr, expected, locals=None):
    from cStringIO import StringIO
    original_stdout = sys.stdout
    try:
        output = StringIO()
        sys.stdout = output
        evalPython(expr, locals)
        stdout = output.getvalue()
        assert stdout == expected, "%r != %r" % (stdout, expected)
    finally:
        sys.stdout = original_stdout

def runTests():
    # single
    check_output('1+1', '2\n')
    check_output('1; 2', '1\n2\n')
    check_output(
        # written in a single line
        "prime=lambda n,i=2:"
            "False if n%i==0 else prime(n,i+1) if i*i<n else True; "
        "prime(17)",
        "True\n")

    # exec
    check_output('def f(): print("hello")\nf()', 'hello\n')
    check_output('print 1\nprint 2', '1\n2\n')
    check_output('text', "'abc'\n", {'text': 'abc'})
    return True

def childProcess(line, w, locals):
    # reseed after a fork to avoid generating the same sequence for each child
    random.seed()

    sys.stdout = sys.stderr = os.fdopen(w, 'w')

    R.setrlimit(R.RLIMIT_CPU, (EVAL_MAXTIMESECONDS, EVAL_MAXTIMESECONDS))
    R.setrlimit(R.RLIMIT_AS, (EVAL_MAXMEMORYBYTES, EVAL_MAXMEMORYBYTES))
    R.setrlimit(R.RLIMIT_NPROC, (0, 0)) # 0 forks

    evalPython(line, locals)

def handleChild(childpid, r):
    txt = ''
    if __import__("__builtin__").any(select.select([r], [], [], TIMEOUT)):
        txt = os.read(r, OUT_MAXLEN + 1)
    os.close(r)

    n = 0
    while n < 6:
        pid, status = os.waitpid(childpid, os.WNOHANG)
        if pid:
            break
        time.sleep(.5)
        n += 1
    if not pid:
        os.kill(childpid, signal.SIGKILL)
        return 'Timeout'
    elif os.WIFEXITED(status):
        return txt.rstrip()
    elif os.WIFSIGNALED(status):
        return 'Killed'

def handle_line(line):
    r, w = os.pipe()
    childpid = os.fork()
    if not childpid:
        os.close(r)
        childProcess(line, w, {})
        os._exit(0)
    else:
        os.close(w)
        result = handleChild(childpid, r)
        return result

class SupySandbox(callbacks.Plugin):
    """Add the help for "@plugin help SupySandbox" here
    This should describe *how* to use this plugin."""
    
    _parser = re.compile(r'(.?sandbox)? (?P<code>.*)')
    def sandbox(self, irc, msg, args):
        """<code>
        
        Runs Python code safely thanks to pysandbox"""
        code = self._parser.match(msg.args[1]).group('code')
        irc.reply(handle_line(code.replace(' $$ ', '\n')))
        
    def runtests(self, irc, msg, args):
        irc.reply(runTests())


Class = SupySandbox


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
