###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009,2011, James McCoy
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
Provides a great number of useful utility functions for IRC.  Things to muck
around with hostmasks, set bold or color on strings, IRC-case-insensitive
dicts, a nick class to handle nicks (so comparisons and hashing and whatnot
work in an IRC-case-insensitive fashion), and numerous other things.
"""

from __future__ import division
from __future__ import print_function

import re
import sys
import time
import random
import string
import textwrap
import functools
from cStringIO import StringIO as sio

from . import utils
from . import minisix


def debug(s, *args):
    """Prints a debug string.  Most likely replaced by our logging debug."""
    print('***', s % args)

userHostmaskRe = re.compile(r'^\S+!\S+@\S+$')
def isUserHostmask(s):
    """Returns whether or not the string s is a valid User hostmask."""
    return userHostmaskRe.match(s) is not None

def isServerHostmask(s):
    """s => bool
    Returns True if s is a valid server hostmask."""
    return not isUserHostmask(s)

def nickFromHostmask(hostmask):
    """hostmask => nick
    Returns the nick from a user hostmask."""
    assert isUserHostmask(hostmask)
    return splitHostmask(hostmask)[0]

def userFromHostmask(hostmask):
    """hostmask => user
    Returns the user from a user hostmask."""
    assert isUserHostmask(hostmask)
    return splitHostmask(hostmask)[1]

def hostFromHostmask(hostmask):
    """hostmask => host
    Returns the host from a user hostmask."""
    assert isUserHostmask(hostmask)
    return splitHostmask(hostmask)[2]

def splitHostmask(hostmask):
    """hostmask => (nick, user, host)
    Returns the nick, user, host of a user hostmask."""
    assert isUserHostmask(hostmask)
    nick, rest = hostmask.split('!', 1)
    user, host = rest.split('@', 1)
    return (minisix.intern(nick), minisix.intern(user), minisix.intern(host))

def joinHostmask(nick, ident, host):
    """nick, user, host => hostmask
    Joins the nick, ident, host into a user hostmask."""
    assert nick and ident and host
    return minisix.intern('%s!%s@%s' % (nick, ident, host))

_rfc1459trans = utils.str.MultipleReplacer(dict(list(zip(
                                 string.ascii_uppercase + r'\[]~',
                                 string.ascii_lowercase + r'|{}^'))))
def toLower(s, casemapping=None):
    """s => s
    Returns the string s lowered according to IRC case rules."""
    if casemapping is None or casemapping == 'rfc1459':
        return _rfc1459trans(s)
    elif casemapping == 'ascii': # freenode
        return s.lower()
    else:
        raise ValueError('Invalid casemapping: %r' % casemapping)

def strEqual(nick1, nick2):
    """s1, s2 => bool
    Returns True if nick1 == nick2 according to IRC case rules."""
    assert isinstance(nick1, basestring)
    assert isinstance(nick2, basestring)
    return toLower(nick1) == toLower(nick2)

nickEqual = strEqual

_nickchars = r'[]\`_^{|}'
nickRe = re.compile(r'^[A-Za-z%s][-0-9A-Za-z%s]*$'
                    % (re.escape(_nickchars), re.escape(_nickchars)))
def isNick(s, strictRfc=True, nicklen=None):
    """s => bool
    Returns True if s is a valid IRC nick."""
    if strictRfc:
        ret = bool(nickRe.match(s))
        if ret and nicklen is not None:
            ret = len(s) <= nicklen
        return ret
    else:
        return not isChannel(s) and \
               not isUserHostmask(s) and \
               not ' ' in s and not '!' in s

def areNicks(s, strictRfc=True, nicklen=None):
    """Like 'isNick(x)' but for comma-separated list."""
    nick = functools.partial(isNick, strictRfc=strictRfc, nicklen=nicklen)
    return all(map(nick, s.split(',')))

def isChannel(s, chantypes='#&+!', channellen=50):
    """s => bool
    Returns True if s is a valid IRC channel name."""
    return s and \
           ',' not in s and \
           '\x07' not in s and \
           s[0] in chantypes and \
           len(s) <= channellen and \
           len(s.split(None, 1)) == 1

def areChannels(s, chantypes='#&+!',channellen=50):
    """Like 'isChannel(x)' but for comma-separated list."""
    chan = functools.partial(isChannel, chantypes=chantypes,
            channellen=channellen)
    return all(map(chan, s.split(',')))

def areReceivers(s, strictRfc=True, nicklen=None, chantypes='#&+!',
        channellen=50):
    """Like 'isNick(x) or isChannel(x)' but for comma-separated list."""
    nick = functools.partial(isNick, strictRfc=strictRfc, nicklen=nicklen)
    chan = functools.partial(isChannel, chantypes=chantypes,
            channellen=channellen)
    return all([nick(x) or chan(x) for x in s.split(',')])

_patternCache = utils.structures.CacheDict(1000)
def _hostmaskPatternEqual(pattern, hostmask):
    try:
        return _patternCache[pattern](hostmask) is not None
    except KeyError:
        # We make our own regexps, rather than use fnmatch, because fnmatch's
        # case-insensitivity is not IRC's case-insensitity.
        fd = sio()
        for c in pattern:
            if c == '*':
                fd.write('.*')
            elif c == '?':
                fd.write('.')
            elif c in '[{':
                fd.write('[[{]')
            elif c in '}]':
                fd.write(r'[}\]]')
            elif c in '|\\':
                fd.write(r'[|\\]')
            elif c in '^~':
                fd.write('[~^]')
            else:
                fd.write(re.escape(c))
        fd.write('$')
        f = re.compile(fd.getvalue(), re.I).match
        _patternCache[pattern] = f
        return f(hostmask) is not None

_hostmaskPatternEqualCache = utils.structures.CacheDict(1000)
def hostmaskPatternEqual(pattern, hostmask):
    """pattern, hostmask => bool
    Returns True if hostmask matches the hostmask pattern pattern."""
    try:
        return _hostmaskPatternEqualCache[(pattern, hostmask)]
    except KeyError:
        b = _hostmaskPatternEqual(pattern, hostmask)
        _hostmaskPatternEqualCache[(pattern, hostmask)] = b
        return b

def banmask(hostmask):
    """Returns a properly generic banning hostmask for a hostmask.

    >>> banmask('nick!user@host.domain.tld')
    '*!*@*.domain.tld'

    >>> banmask('nick!user@10.0.0.1')
    '*!*@10.0.0.*'
    """
    assert isUserHostmask(hostmask)
    host = hostFromHostmask(hostmask)
    if utils.net.isIPV4(host):
        L = host.split('.')
        L[-1] = '*'
        return '*!*@' + '.'.join(L)
    elif utils.net.isIPV6(host):
        L = host.split(':')
        L[-1] = '*'
        return '*!*@' + ':'.join(L)
    else:
        if len(host.split('.')) > 2: # If it is a subdomain
            return '*!*@*%s' % host[host.find('.'):]
        else:
            return '*!*@'  + host

_plusRequireArguments = 'ovhblkqeI'
_minusRequireArguments = 'ovhbkqeI'
def separateModes(args):
    """Separates modelines into single mode change tuples.  Basically, you
    should give it the .args of a MODE IrcMsg.

    Examples:

    >>> separateModes(['+ooo', 'jemfinch', 'StoneTable', 'philmes'])
    [('+o', 'jemfinch'), ('+o', 'StoneTable'), ('+o', 'philmes')]

    >>> separateModes(['+o-o', 'jemfinch', 'PeterB'])
    [('+o', 'jemfinch'), ('-o', 'PeterB')]

    >>> separateModes(['+s-o', 'test'])
    [('+s', None), ('-o', 'test')]

    >>> separateModes(['+sntl', '100'])
    [('+s', None), ('+n', None), ('+t', None), ('+l', 100)]
    """
    if not args:
        return []
    modes = args[0]
    assert modes[0] in '+-', 'Invalid args: %r' % args
    args = list(args[1:])
    ret = []
    for c in modes:
        if c in '+-':
            last = c
        else:
            if last == '+':
                requireArguments = _plusRequireArguments
            else:
                requireArguments = _minusRequireArguments
            if c in requireArguments:
                if not args:
                    # It happens, for example with "MODE #channel +b", which
                    # is used for getting the list of all bans.
                    continue
                arg = args.pop(0)
                try:
                    arg = int(arg)
                except ValueError:
                    pass
                ret.append((last + c, arg))
            else:
                ret.append((last + c, None))
    return ret

def joinModes(modes):
    """[(mode, targetOrNone), ...] => args
    Joins modes of the same form as returned by separateModes."""
    args = []
    modeChars = []
    currentMode = '\x00'
    for (mode, arg) in modes:
        if arg is not None:
            args.append(arg)
        if not mode.startswith(currentMode):
            currentMode = mode[0]
            modeChars.append(mode[0])
        modeChars.append(mode[1])
    args.insert(0, ''.join(modeChars))
    return args

def bold(s):
    """Returns the string s, bolded."""
    return '\x02%s\x02' % s

def reverse(s):
    """Returns the string s, reverse-videoed."""
    return '\x16%s\x16' % s

def underline(s):
    """Returns the string s, underlined."""
    return '\x1F%s\x1F' % s

# Definition of mircColors dictionary moved below because it became an IrcDict.
def mircColor(s, fg=None, bg=None):
    """Returns s with the appropriate mIRC color codes applied."""
    if fg is None and bg is None:
        return s
    elif bg is None:
        if str(fg) in mircColors:
            fg = mircColors[str(fg)]
        elif len(str(fg)) > 1:
            fg = mircColors[str(fg)[:-1]]
        else:
            # Should not happen
            pass
        return '\x03%s%s\x03' % (fg.zfill(2), s)
    elif fg is None:
        bg = mircColors[str(bg)]
        # According to the mirc color doc, a fg color MUST be specified if a
        # background color is specified.  So, we'll specify 00 (white) if the
        # user doesn't specify one.
        return '\x0300,%s%s\x03' % (bg.zfill(2), s)
    else:
        fg = mircColors[str(fg)]
        bg = mircColors[str(bg)]
        # No need to zfill fg because the comma delimits.
        return '\x03%s,%s%s\x03' % (fg, bg.zfill(2), s)

def canonicalColor(s, bg=False, shift=0):
    """Assigns an (fg, bg) canonical color pair to a string based on its hash
    value.  This means it might change between Python versions.  This pair can
    be used as a *parameter to mircColor.  The shift parameter is how much to
    right-shift the hash value initially.
    """
    h = hash(s) >> shift
    fg = h % 14 + 2 # The + 2 is to rule out black and white.
    if bg:
        bg = (h >> 4) & 3 # The 5th, 6th, and 7th least significant bits.
        if fg < 8:
            bg += 8
        else:
            bg += 2
        return (fg, bg)
    else:
        return (fg, None)

def stripBold(s):
    """Returns the string s, with bold removed."""
    return s.replace('\x02', '')

_stripColorRe = re.compile(r'\x03(?:\d{1,2},\d{1,2}|\d{1,2}|,\d{1,2}|)')
def stripColor(s):
    """Returns the string s, with color removed."""
    return _stripColorRe.sub('', s)

def stripReverse(s):
    """Returns the string s, with reverse-video removed."""
    return s.replace('\x16', '')

def stripUnderline(s):
    """Returns the string s, with underlining removed."""
    return s.replace('\x1f', '').replace('\x1F', '')

def stripFormatting(s):
    """Returns the string s, with all formatting removed."""
    # stripColor has to go first because of some strings, check the tests.
    s = stripColor(s)
    s = stripBold(s)
    s = stripReverse(s)
    s = stripUnderline(s)
    return s.replace('\x0f', '').replace('\x0F', '')

class FormatContext(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.fg = None
        self.bg = None
        self.bold = False
        self.reverse = False
        self.underline = False

    def start(self, s):
        """Given a string, starts all the formatters in this context."""
        if self.bold:
            s = '\x02' + s
        if self.reverse:
            s = '\x16' + s
        if self.underline:
            s = '\x1f' + s
        if self.fg is not None or self.bg is not None:
            s = mircColor(s, fg=self.fg, bg=self.bg)[:-1] # Remove \x03.
        return s

    def end(self, s):
        """Given a string, ends all the formatters in this context."""
        if self.bold or self.reverse or \
           self.fg or self.bg or self.underline:
            # Should we individually end formatters?
            s += '\x0f'
        return s

class FormatParser(object):
    def __init__(self, s):
        self.fd = sio(s)
        self.last = None

    def getChar(self):
        if self.last is not None:
            c = self.last
            self.last = None
            return c
        else:
            return self.fd.read(1)

    def ungetChar(self, c):
        self.last = c

    def parse(self):
        context = FormatContext()
        c = self.getChar()
        while c:
            if c == '\x02':
                context.bold = not context.bold
            elif c == '\x16':
                context.reverse = not context.reverse
            elif c == '\x1f':
                context.underline = not context.underline
            elif c == '\x0f':
                context.reset()
            elif c == '\x03':
                self.getColor(context)
            c = self.getChar()
        return context

    def getInt(self):
        i = 0
        setI = False
        c = self.getChar()
        while c.isdigit():
            j = i * 10
            j += int(c)
            if j >= 16:
                self.ungetChar(c)
                break
            else:
                setI = True
                i = j
                c = self.getChar()
        self.ungetChar(c)
        if setI:
            return i
        else:
            return None

    def getColor(self, context):
        context.fg = self.getInt()
        c = self.getChar()
        if c == ',':
            context.bg = self.getInt()
        else:
            self.ungetChar(c)

def wrap(s, length, break_on_hyphens = False, break_long_words = False):
    processed = []
    wrapper = textwrap.TextWrapper(width=length)
    wrapper.break_long_words = break_long_words
    wrapper.break_on_hyphens = break_on_hyphens
    chunks = wrapper.wrap(s)
    context = None
    for chunk in chunks:
        if context is not None:
            chunk = context.start(chunk)
        context = FormatParser(chunk).parse()
        processed.append(context.end(chunk))
    return processed

def isValidArgument(s):
    """Returns whether s is strictly a valid argument for an IRC message."""

    return '\r' not in s and '\n' not in s and '\x00' not in s

def safeArgument(s):
    """If s is unsafe for IRC, returns a safe version."""
    if sys.version_info[0] < 3 and isinstance(s, unicode):
        s = s.encode('utf-8')
    elif (sys.version_info[0] < 3 and not isinstance(s, basestring)) or \
            (sys.version_info[0] >= 3 and not isinstance(s, str)):
        debug('Got a non-string in safeArgument: %r', s)
        s = str(s)
    if isValidArgument(s):
        return s
    else:
        return repr(s)

def replyTo(msg):
    """Returns the appropriate target to send responses to msg."""
    if isChannel(msg.args[0]):
        return msg.args[0]
    else:
        return msg.nick

def dccIP(ip):
    """Converts an IP string to the DCC integer form."""
    assert utils.net.isIPV4(ip), \
           'argument must be a string ip in xxx.yyy.zzz.www format.'
    i = 0
    x = 256**3
    for quad in ip.split('.'):
        i += int(quad)*x
        x //= 256
    return i

def unDccIP(i):
    """Takes an integer DCC IP and return a normal string IP."""
    assert isinstance(i, (int, long)), '%r is not an number.' % i
    L = []
    while len(L) < 4:
        L.append(i % 256)
        i //= 256
    L.reverse()
    return '.'.join(map(str, L))

class IrcString(str):
    """This class does case-insensitive comparison and hashing of nicks."""
    def __new__(cls, s=''):
        x = super(IrcString, cls).__new__(cls, s)
        x.lowered = str(toLower(x))
        return x

    def __eq__(self, s):
        try:
            return toLower(s) == self.lowered
        except:
            return False

    def __ne__(self, s):
        return not (self == s)

    def __hash__(self):
        return hash(self.lowered)


class IrcDict(utils.InsensitivePreservingDict):
    """Subclass of dict to make key comparison IRC-case insensitive."""
    def key(self, s):
        if s is not None:
            s = toLower(s)
        return s

class CallableValueIrcDict(IrcDict):
    def __getitem__(self, k):
        v = super(IrcDict, self).__getitem__(k)
        if callable(v):
            v = v()
        return v

class IrcSet(utils.NormalizingSet):
    """A sets.Set using IrcStrings instead of regular strings."""
    def normalize(self, s):
        return IrcString(s)

    def __reduce__(self):
        return (self.__class__, (list(self),))


class FloodQueue(object):
    timeout = 0
    def __init__(self, timeout=None, queues=None):
        if timeout is not None:
            self.timeout = timeout
        if queues is None:
            queues = IrcDict()
        self.queues = queues

    def __repr__(self):
        return 'FloodQueue(timeout=%r, queues=%s)' % (self.timeout,
                                                      repr(self.queues))

    def key(self, msg):
        # This really ought to be configurable without subclassing, but for
        # now, it works.
        # used to be msg.user + '@' + msg.host but that was too easily abused.
        return msg.host

    def getTimeout(self):
        if callable(self.timeout):
            return self.timeout()
        else:
            return self.timeout

    def _getQueue(self, msg, insert=True):
        key = self.key(msg)
        try:
            return self.queues[key]
        except KeyError:
            if insert:
                # python--
                # instancemethod.__repr__ calls the instance.__repr__, which
                # means that our __repr__ calls self.queues.__repr__, which
                # calls structures.TimeoutQueue.__repr__, which calls
                # getTimeout.__repr__, which calls our __repr__, which calls...
                getTimeout = lambda : self.getTimeout()
                q = utils.structures.TimeoutQueue(getTimeout)
                self.queues[key] = q
                return q
            else:
                return None

    def enqueue(self, msg, what=None):
        if what is None:
            what = msg
        q = self._getQueue(msg)
        q.enqueue(what)

    def len(self, msg):
        q = self._getQueue(msg, insert=False)
        if q is not None:
            return len(q)
        else:
            return 0

    def has(self, msg, what=None):
        q = self._getQueue(msg, insert=False)
        if q is not None:
            if what is None:
                what = msg
            for elt in q:
                if elt == what:
                    return True
        return False


mircColors = IrcDict({
    'white': '0',
    'black': '1',
    'blue': '2',
    'green': '3',
    'red': '4',
    'brown': '5',
    'purple': '6',
    'orange': '7',
    'yellow': '8',
    'light green': '9',
    'teal': '10',
    'light blue': '11',
    'dark blue': '12',
    'pink': '13',
    'dark grey': '14',
    'light grey': '15',
    'dark gray': '14',
    'light gray': '15',
})

# We'll map integers to their string form so mircColor is simpler.
for (k, v) in mircColors.items():
    if k is not None: # Ignore empty string for None.
        sv = str(v)
        mircColors[sv] = sv

def standardSubstitute(irc, msg, text, env=None):
    """Do the standard set of substitutions on text, and return it"""
    if isChannel(msg.args[0]):
        channel = msg.args[0]
    else:
        channel = 'somewhere'
    def randInt():
        return str(random.randint(-1000, 1000))
    def randDate():
        t = pow(2,30)*random.random()+time.time()/4.0
        return time.ctime(t)
    def randNick():
        if channel != 'somewhere':
            L = list(irc.state.channels[channel].users)
            if len(L) > 1:
                n = msg.nick
                while n == msg.nick:
                    n = utils.iter.choice(L)
                return n
            else:
                return msg.nick
        else:
            return 'someone'
    ctime = time.strftime("%a %b %d %H:%M:%S %Y")
    localtime = time.localtime()
    gmtime = time.strftime("%a %b %d %H:%M:%S %Y", time.gmtime())
    vars = CallableValueIrcDict({
        'who': msg.nick,
        'nick': msg.nick,
        'user': msg.user,
        'host': msg.host,
        'channel': channel,
        'botnick': irc.nick,
        'now': ctime, 'ctime': ctime,
        'utc': gmtime, 'gmt': gmtime,
        'randnick': randNick, 'randomnick': randNick,
        'randdate': randDate, 'randomdate': randDate,
        'rand': randInt, 'randint': randInt, 'randomint': randInt,
        'today': time.strftime('%d %b %Y', localtime),
        'year': localtime[0],
        'month': localtime[1],
        'monthname': time.strftime('%b', localtime),
        'date': localtime[2],
        'day': time.strftime('%A', localtime),
        'h': localtime[3], 'hr': localtime[3], 'hour': localtime[3],
        'm': localtime[4], 'min': localtime[4], 'minute': localtime[4],
        's': localtime[5], 'sec': localtime[5], 'second': localtime[5],
        'tz': time.strftime('%Z', localtime),
        })
    if msg.reply_env:
        vars.update(msg.reply_env)
    if env is not None:
        vars.update(env)
    t = string.Template(text)
    t.idpattern = '[a-zA-Z][a-zA-Z0-9]*'
    return t.safe_substitute(vars)

if __name__ == '__main__':
    import sys, doctest
    doctest.testmod(sys.modules['__main__'])
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
