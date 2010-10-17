#!/usr/bin/env python
# this file is under the WTFPLv2 [http://sam.zoy.org/wtfpl]
# v1: 2010/05/23
# Author: Tila

# You need a configuration file: ~/.fschfsch.py. Config example:
# ---
# host = 'irc.freenode.net'
# port = 7000
# ssl = True
# nickname = 'botnickname'
# password = 'secret'
# channels = ['##fschfsch', '#channel2', '#channel3']
# texts = {'help': 'I am fschfsch, a robot snake that evals python code',
#         'sandbox': "I am powered by setrlimit and pysandbox [http://github.com/haypo/pysandbox], I don't fear you"}
# ---

'''
fschfsch is a Python-evaluating bot. fschfsch is pronounced "fssshh! fssshh!".
'''

IN_MAXLEN = 300 # bytes
OUT_MAXLEN = 300 # bytes
TIMEOUT = 3  # seconds

EVAL_MAXTIMESECONDS = TIMEOUT
EVAL_MAXMEMORYBYTES = 10 * 1024 * 1024 # 10 MiB


try:
    import sandbox as S
except ImportError:
    print 'You need pysandbox in order to run fschfsch [http://github.com/haypo/pysandbox].'
    raise
try:
    import twisted
except ImportError:
    print 'You need twisted in order to run fschfsch.'
    raise
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import ssl, reactor
from twisted.words.im.ircsupport import IRCProto
from twisted.words.protocols.irc import IRCClient
# other imports
import re
import sys
import os
import resource as R
import select
import signal
import time
import threading
import random

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
    if any(select.select([r], [], [], TIMEOUT)):
        txt = os.read(r, OUT_MAXLEN + 1)
    os.close(r)
    if OUT_MAXLEN < len(txt):
        txt = txt[:OUT_MAXLEN] + '...'

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
        txts = txt.rstrip().split('\n')
        if len(txts) > 1:
            txt = txts[0].rstrip() + ' [+ %d line(s)]' % (len(txts) - 1)
        else:
            txt = txts[0].rstrip()
        return 'Output: ' + txt
    elif os.WIFSIGNALED(status):
        return 'Killed'



class EvalJob(threading.Thread):
    def __init__(self, line, irc, channel):
        super(EvalJob, self).__init__()
        self.line = line
        self.irc = irc
        self.channel = channel

    def run(self):
        output = self.handle_line(self.line)
        reactor.callFromThread(self.irc.say, self.channel, output)
        self.irc.executionLock.release()

    def handle_line(self, line):
        if IN_MAXLEN < len(line):
            return '(command is too long: %s bytes, the maximum is %s)' % (len(line), IN_MAXLEN)

        print("Process %s" % repr(line))
        r, w = os.pipe()
        childpid = os.fork()
        if not childpid:
            os.close(r)
            childProcess(line, w, self.irc.factory.morevars)
            os._exit(0)
        else:
            os.close(w)
            result = handleChild(childpid, r)
            print("=> %s" % repr(result))
            return result



class EvalBot(IRCClient):
    versionName = 'fschfsch'
    versionNum = '0.1'

    #~ def __init__(self, *a, **k):
    def connectionMade(self):
        self.nickname = self.factory.nick
        self.password = self.factory.password
        self.talkre = re.compile('^%s[>:,] (.*)$' % self.nickname)

        self.executionLock = threading.Semaphore()
        self.pingSelfId = None

        IRCClient.connectionMade(self)

    def signedOn(self):
        self.pingSelfId = reactor.callLater(180, self.pingSelf)
        for chan in self.factory.channels:
            self.join(chan)

    def pingSelf(self):
        # used to avoid some timeouts where fschfsch does not reconnect
        self.ping(self.nickname)
        self.pingSelfId = reactor.callLater(180, self.pingSelf)

    def privmsg(self, user, channel, message):
        if self.pingSelfId is not None:
            self.pingSelfId.reset(180)
        if user.startswith('haypo') and message.startswith('exit'):
            os._exit(0)
        if not channel:
            return
        if not message.startswith(self.nickname):
            return
        if not self.talkre.match(message):
            return
        if not self.executionLock.acquire(blocking=False):
            return

        pyline = self.talkre.match(message).group(1)
        pyline = pyline.replace(' $$ ', '\n')

        self.handleThread = EvalJob(pyline, self, channel)
        self.handleThread.start()


class MyFactory(ReconnectingClientFactory):
    def __init__(self, **kw):
        for k in kw:
            if k in ('nick', 'password', 'channels', 'morevars'):
                setattr(self, k, kw[k])
    protocol = EvalBot

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

def main():
    if len(sys.argv) == 2 and sys.argv[1] == 'tests':
        ok = runTests()
        if ok:
            print("no failure")
        else:
            print("failure!")
        sys.exit(int(not ok))
    elif len(sys.argv) != 1:
        print 'usage: %s -- run the bot' % sys.argv[0]
        print '   or: %s tests -- run self tests' % sys.argv[0]
        print
        print 'Edit ~/.fschfschrc.py first'
        sys.exit(4)

    conf = {}
    execfile(os.path.expanduser('~/.fschfschrc.py'), conf)
    factory = MyFactory(nick=conf['nickname'], password=conf.get('password', None), channels=conf.get('channels', []), morevars=conf.get('texts', {}))
    if conf.get('ssl', 0):
        reactor.connectSSL(conf['host'], conf['port'], factory, ssl.ClientContextFactory())
    else:
        reactor.connectTCP(conf['host'], conf['port'], factory)
    reactor.run()

if __name__ == '__main__':
    main()
