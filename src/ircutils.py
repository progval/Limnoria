###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009,2011,2015 James McCoy
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
import uuid
import base64
import random
import string
import textwrap
import functools
import collections.abc

from . import utils
from .utils import minisix
from .version import version

from .i18n import PluginInternationalization
_ = PluginInternationalization()

def debug(s, *args):
    """Prints a debug string.  Most likely replaced by our logging debug."""
    print('***', s % args)

def warning(s, *args):
    """Prints a debug string.  Most likely replaced by our logging debug."""
    print('###', s % args)

userHostmaskRe = re.compile(r'^(?P<nick>\S+?)!(?P<user>\S+)@(?P<host>\S+?)$')
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
    m = userHostmaskRe.match(hostmask)
    assert m is not None, hostmask
    nick = m.group("nick")
    user = m.group("user")
    host = m.group("host")
    if set("!@") & set(nick+user+host):
        # There should never be either of these characters in the part.
        # As far as I know it never happens in practice aside from networks
        # broken by design.
        warning("Invalid hostmask format: %s", hostmask)
        # TODO: error if strictRfc is True
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
    assert isinstance(nick1, minisix.string_types)
    assert isinstance(nick2, minisix.string_types)
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

def isChannel(s, chantypes='#&!', channellen=50):
    """s => bool
    Returns True if s is a valid IRC channel name."""
    return s and \
           ',' not in s and \
           '\x07' not in s and \
           s[0] in chantypes and \
           len(s) <= channellen and \
           len(s.split(None, 1)) == 1

def areChannels(s, chantypes='#&!', channellen=50):
    """Like 'isChannel(x)' but for comma-separated list."""
    chan = functools.partial(isChannel, chantypes=chantypes,
            channellen=channellen)
    return all(map(chan, s.split(',')))

def areReceivers(s, strictRfc=True, nicklen=None, chantypes='#&!',
        channellen=50):
    """Like 'isNick(x) or isChannel(x)' but for comma-separated list."""
    nick = functools.partial(isNick, strictRfc=strictRfc, nicklen=nicklen)
    chan = functools.partial(isChannel, chantypes=chantypes,
            channellen=channellen)
    return all([nick(x) or chan(x) for x in s.split(',')])

_patternCache = utils.structures.CacheDict(1000)
def _compileHostmaskPattern(pattern):
    try:
        return _patternCache[pattern]
    except KeyError:
        # We make our own regexps, rather than use fnmatch, because fnmatch's
        # case-insensitivity is not IRC's case-insensitity.
        fd = minisix.io.StringIO()
        for c in pattern:
            if c == '*':
                fd.write('.*')
            elif c == '?':
                fd.write('.')
            elif c in '[{':
                fd.write(r'[\[{]')
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
        return f

_hostmaskPatternEqualCache = utils.structures.CacheDict(1000)
def hostmaskPatternEqual(pattern, hostmask):
    """pattern, hostmask => bool
    Returns True if hostmask matches the hostmask pattern pattern."""
    try:
        return _hostmaskPatternEqualCache[(pattern, hostmask)]
    except KeyError:
        matched = _compileHostmaskPattern(pattern)(hostmask) is not None
        _hostmaskPatternEqualCache[(pattern, hostmask)] = matched
        return matched

class HostmaskSet(collections.abc.MutableSet):
    """Stores a set of hostmasks and caches their pattern as compiled
    by _compileHostmaskPattern.

    This is an alternative to hostmaskPatternEqual for sets of patterns that
    do not change often, such as ircdb.IrcUser.
    ircdb.IrcUser used to store a real set, of hostmasks as strings, then
    call hostmaskPatternEqual on each of these strings. This is good enough
    most of the time, as hostmaskPatternEqual has a cache.

    Unfortunately, it is a LRU cache, and hostmasks are checked in order.
    This means that as soon as you have most hostmasks than the size of the
    cache, EVERY call to hostmaskPatternEqual will be a cache miss, so the
    regexp will need to be recompile every time.
    This is VERY expensive, because building the regexp is slow, and
    re.compile() is even slower."""

    def __init__(self, hostmasks=()):
        self.data = {}  # {hostmask_str: _compileHostmaskPattern(hostmask_str)}
        for hostmask in hostmasks:
            self.add(hostmask)

    def add(self, hostmask):
        self.data[hostmask] = _compileHostmaskPattern(hostmask)

    def discard(self, hostmask):
        self.data.pop(hostmask, None)

    def __contains__(self, hostmask):
        return hostmask in self.data

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def match(self, hostname):
        # Potential optimization: join all the patterns into a single one.
        for (pattern, compiled_pattern) in self.data.items():
            if compiled_pattern(hostname) is not None:
                return pattern
        return None

    def __repr__(self):
        return 'HostmaskSet(%r)' % (list(self.data),)


class ExpiringHostmaskDict(collections.abc.MutableMapping):
    """Like HostmaskSet, but behaves like a dict with expiration timestamps
    as values."""

    # To keep it thread-safe, add to self.patterns first, then
    # self.data; and remove from self.data first.
    # And never iterate on self.patterns

    def __init__(self, hostmasks=None):
        if isinstance(hostmasks, (list, tuple)):
            hostmasks = dict(hostmasks)
        self.data = hostmasks or {}
        self.patterns = HostmaskSet(list(self.data))

    def __getitem__(self, hostmask):
        return self.data[hostmask]

    def __setitem__(self, hostmask, expiration):
        """For backward compatibility, in case any plugin depends on it
        being dict-like."""
        self.patterns.add(hostmask)
        self.data[hostmask] = expiration

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __delitem__(self, hostmask):
        del self.data[hostmask]
        self.patterns.discard(hostmask)

    def expire(self):
        now = time.time()
        for (hostmask, expiration) in list(self.data.items()):
            if now >= expiration and expiration:
                self.pop(hostmask, None)

    def match(self, hostname):
        self.expire()
        return self.patterns.match(hostname)

    def clear(self):
        self.data.clear()
        self.patterns.clear()

    def __repr__(self):
        return 'ExpiringHostmaskSet(%r)' % (self.expirations,)


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


def accountExtban(irc, nick):
    """If 'nick' is logged in and the network supports account extbans,
    returns a ban mask for it. If not, returns None."""
    if 'ACCOUNTEXTBAN' not in irc.state.supported:
        return None
    if 'EXTBAN' not in irc.state.supported:
        return None
    try:
        account = irc.state.nickToAccount(nick)
    except KeyError:
        account = None
    if account is None:
        return None
    account_extban = irc.state.supported['ACCOUNTEXTBAN'].split(',')[0]
    extban_prefix = irc.state.supported['EXTBAN'].split(',', 1)[0]
    return '%s%s:%s'% (extban_prefix, account_extban, account)


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
    args = list(args[1:])
    ret = []
    last = '+'
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

def italic(s):
    """Returns the string s, italicised."""
    return '\x1D%s\x1D' % s

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

def stripItalic(s):
    """Returns the string s, with italics removed."""
    return s.replace('\x1d', '')

_stripColorRe = re.compile(r'\x03(?:\d{1,2},\d{1,2}|\d{1,2}|,\d{1,2}|)')
def stripColor(s):
    """Returns the string s, with color removed."""
    return _stripColorRe.sub('', s)

def stripReverse(s):
    """Returns the string s, with reverse-video removed."""
    return s.replace('\x16', '')

def stripUnderline(s):
    """Returns the string s, with underlining removed."""
    return s.replace('\x1f', '')

def stripFormatting(s):
    """Returns the string s, with all formatting removed."""
    # stripColor has to go first because of some strings, check the tests.
    s = stripColor(s)
    s = stripBold(s)
    s = stripReverse(s)
    s = stripUnderline(s)
    s = stripItalic(s)
    return s.replace('\x0f', '')

_containsFormattingRe = re.compile(r'[\x02\x03\x16\x1f]')
def formatWhois(irc, replies, caller='', channel='', command='whois'):
    """Returns a string describing the target of a WHOIS command.

    Arguments are:
    * irc: the irclib.Irc object on which the replies was received

    * replies: a dict mapping the reply codes ('311', '312', etc.) to their
      corresponding ircmsg.IrcMsg

    * caller: an optional nick specifying who requested the whois information

    * channel: an optional channel specifying where the reply will be sent

    If provided, caller and channel will be used to avoid leaking information
    that the caller/channel shouldn't be privy to.
    """
    hostmask = '@'.join(replies['311'].args[2:4])
    nick = replies['318'].args[1]
    user = replies['311'].args[-1]
    START_CODE = '311' if command == 'whois' else '314'
    hostmask = '@'.join(replies[START_CODE].args[2:4])
    user = replies[START_CODE].args[-1]
    if _containsFormattingRe.search(user) and user[-1] != '\x0f':
        # For good measure, disable any formatting
        user = '%s\x0f' % user
    if '319' in replies:
        channels = []
        for msg in replies['319']:
            channels.extend(msg.args[-1].split())
        ops = []
        voices = []
        normal = []
        halfops = []
        for chan in channels:
            origchan = chan
            chan = chan.lstrip('@%+~!')
            # UnrealIRCd uses & for user modes and disallows it as a
            # channel-prefix, flying in the face of the RFC.  Have to
            # handle this specially when processing WHOIS response.
            testchan = chan.lstrip('&')
            if testchan != chan and irc.isChannel(testchan):
                chan = testchan
            diff = len(chan) - len(origchan)
            modes = origchan[:diff]
            chanState = irc.state.channels.get(chan)
            # The user is in a channel the bot is in, so the ircd may have
            # responded with otherwise private data.
            if chanState:
                # Skip channels the caller isn't in.  This prevents
                # us from leaking information when the channel is +s or the
                # target is +i.
                if caller not in chanState.users:
                    continue
                # Skip +s/+p channels the target is in only if the reply isn't
                # being sent to that channel.
                if set(('p', 's')) & set(chanState.modes.keys()) and \
                   not strEqual(channel or '', chan):
                    continue
            if not modes:
                normal.append(chan)
            elif utils.iter.any(lambda c: c in modes,('@', '&', '~', '!')):
                ops.append(chan)
            elif utils.iter.any(lambda c: c in modes, ('%',)):
                halfops.append(chan)
            elif utils.iter.any(lambda c: c in modes, ('+',)):
                voices.append(chan)
        L = []
        if ops:
            L.append(format(_('is an op on %L'), ops))
        if halfops:
            L.append(format(_('is a halfop on %L'), halfops))
        if voices:
            L.append(format(_('is voiced on %L'), voices))
        if normal:
            if L:
                L.append(format(_('is also on %L'), normal))
            else:
                L.append(format(_('is on %L'), normal))
    else:
        if command == 'whois':
            L = [_('isn\'t on any publicly visible channels')]
        else:
            L = []
    channels = format('%L', L)
    if '317' in replies:
        idle = utils.timeElapsed(replies['317'].args[2])
        signon = utils.str.timestamp(float(replies['317'].args[3]))
    else:
        idle = _('<unknown>')
        signon = _('<unknown>')
    if '312' in replies:
        server = replies['312'].args[2]
        if len(replies['312']) > 3:
            signoff = replies['312'].args[3]
    else:
        server = _('<unknown>')
    if '301' in replies:
        away = _(' %s is away: %s.') % (nick, replies['301'].args[2])
    else:
        away = ''
    if '320' in replies:
        if replies['320'].args[2]:
            identify = _(' identified')
        else:
            identify = ''
    else:
        identify = ''
    if command == 'whois':
        s = _('%s (%s) has been%s on server %s since %s (idle for %s). %s '
              '%s.%s') % (user, hostmask, identify, server,
                          signon, idle, nick, channels, away)
    else:
        s = _('%s (%s) has been%s on server %s and disconnected on %s.') % \
                (user, hostmask, identify, server, signoff)
    return s

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

    def size(self):
        """Returns the number of bytes needed to reproduce this context in an
        IRC string."""
        prefix_size = self.bold + self.reverse + self.underline + \
                bool(self.fg) + bool(self.bg)
        if self.fg and self.bg:
            prefix_size += 6 # '\x03xx,yy%s'
        elif self.fg or self.bg:
            prefix_size += 3 # '\x03xx%s'
        if prefix_size:
            return prefix_size + 1 # '\x0f'
        else:
            return 0

class FormatParser(object):
    def __init__(self, s):
        self.fd = minisix.io.StringIO(s)
        self.last = None
        self.max_context_size = 0

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
                self.max_context_size = max(
                        self.max_context_size, context.size())
            elif c == '\x16':
                context.reverse = not context.reverse
                self.max_context_size = max(
                        self.max_context_size, context.size())
            elif c == '\x1f':
                context.underline = not context.underline
                self.max_context_size = max(
                        self.max_context_size, context.size())
            elif c == '\x0f':
                context.reset()
            elif c == '\x03':
                self.getColor(context)
                self.max_context_size = max(
                        self.max_context_size, context.size())
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

def wrap(s, length, break_on_hyphens = False):
    # Get the maximum number of bytes needed to format a chunk of the string
    # at any point.
    # This is an overapproximation of what each chunk will need, but it's
    # either that or make the code of byteTextWrap aware of contexts, and its
    # code is complicated enough as it is already.
    parser = FormatParser(s)
    parser.parse()
    format_overhead = parser.max_context_size

    processed = []
    chunks = utils.str.byteTextWrap(s, length - format_overhead)
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
    if minisix.PY2 and isinstance(s, unicode):
        s = s.encode('utf-8')
    elif (minisix.PY2 and not isinstance(s, minisix.string_types)) or \
            (minisix.PY3 and not isinstance(s, str)):
        debug('Got a non-string in safeArgument: %r', s)
        s = str(s)
    if isValidArgument(s):
        return s
    else:
        return repr(s)

def replyTo(msg):
    """Returns the appropriate target to send responses to msg."""
    if msg.channel:
        # if message was sent to +#channel, we want to reply to +#channel;
        # or unvoiced channel users will see the bot reply without the
        # origin query
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
    assert isinstance(i, minisix.integer_types), '%r is not an number.' % i
    L = []
    while len(L) < 4:
        L.append(i % 256)
        i //= 256
    L.reverse()
    return '.'.join(map(str, L))

class IrcString(str):
    """This class does case-insensitive comparison and hashing of nicks."""
    __slots__ = ('lowered',)
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
    __slots__ = ()
    def key(self, s):
        if s is not None:
            s = toLower(s)
        return s

class CallableValueIrcDict(IrcDict):
    __slots__ = ()
    def __getitem__(self, k):
        v = super(IrcDict, self).__getitem__(k)
        if callable(v):
            v = v()
        return v

class IrcSet(utils.NormalizingSet):
    """A sets.Set using IrcStrings instead of regular strings."""
    __slots__ = ()
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
for (k, v) in list(mircColors.items()):
    if k is not None: # Ignore empty string for None.
        sv = str(v)
        mircColors[sv] = sv
        mircColors[sv.zfill(2)] = sv


def standardSubstitutionVariables(irc, msg, env=None):
    """Returns the dict-like object used to make standard substitutions
    on text sent to IRC. Usually you'll want to use
    :py:func:`standardSubstitute` instead, which runs the actual substitution
    itself."""
    def randInt():
        return str(random.randint(-1000, 1000))
    def randDate():
        t = pow(2,30)*random.random()+time.time()/4.0
        return time.ctime(t)
    ctime = time.strftime("%a %b %d %H:%M:%S %Y")
    localtime = time.localtime()
    gmtime = time.strftime("%a %b %d %H:%M:%S %Y", time.gmtime())
    vars = CallableValueIrcDict({
        'now': ctime, 'ctime': ctime,
        'utc': gmtime, 'gmt': gmtime,
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
        'version': version,
        })
    if irc:
        vars.update({
            'botnick': irc.nick,
            'network': irc.network,
            })

    if msg:
        vars.update({
            'who': msg.nick,
            'nick': msg.nick,
            'user': msg.user,
            'host': msg.host,
            })
        if msg.reply_env:
            vars.update(msg.reply_env)

    if irc and msg:
        channel = msg.channel or 'somewhere'
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
        vars.update({
            'randnick': randNick, 'randomnick': randNick,
            'channel': channel,
            })
    else:
        vars.update({
            'channel': 'somewhere',
            'randnick': 'someone', 'randomnick': 'someone',
            })

    if env is not None:
        vars.update(env)

    return vars


def standardSubstitute(irc, msg, text, env=None):
    """Do the standard set of substitutions on text, and return it"""
    vars = standardSubstitutionVariables(irc, msg, env)
    t = string.Template(text)
    t.idpattern = '[a-zA-Z][a-zA-Z0-9]*'
    return t.safe_substitute(vars)


AUTHENTICATE_CHUNK_SIZE = 400
def authenticate_generator(authstring, base64ify=True):
    if base64ify:
        authstring = base64.b64encode(authstring)
        if minisix.PY3:
            authstring = authstring.decode()
    # +1 so we get an empty string at the end if len(authstring) is a multiple
    # of AUTHENTICATE_CHUNK_SIZE (including 0)
    for n in range(0, len(authstring)+1, AUTHENTICATE_CHUNK_SIZE):
        chunk = authstring[n:n+AUTHENTICATE_CHUNK_SIZE] or '+'
        yield chunk

class AuthenticateDecoder(object):
    def __init__(self):
        self.chunks = []
        self.ready = False
    def feed(self, msg):
        assert msg.command == 'AUTHENTICATE'
        chunk = msg.args[0]
        if chunk == '+' or len(chunk) != AUTHENTICATE_CHUNK_SIZE:
            self.ready = True
        if chunk != '+':
            if minisix.PY3:
                chunk = chunk.encode()
            self.chunks.append(chunk)
    def get(self):
        assert self.ready
        return base64.b64decode(b''.join(self.chunks))


def parseCapabilityKeyValue(s):
    """Parses a key-value string, in the format used by 'sts' and
    'draft/multiline."""
    d = {}
    for kv in s.split(','):
        if '=' in kv:
            (k, v) = kv.split('=', 1)
            d[k] = v
        else:
            d[kv] = None

    return d

def parseStsPolicy(logger, policy, tls_connection):
    parsed_policy = parseCapabilityKeyValue(policy)

    for key in ('port', 'duration'):
        if key == 'duration' and not tls_connection:
            if key in parsed_policy:
                del parsed_policy[key]
            continue
        elif key == 'port' and tls_connection:
            if key in parsed_policy:
                del parsed_policy[key]
            continue
        if parsed_policy.get(key) is None:
            logger.error('Missing or empty "%s" key in STS policy. '
                         'Ignoring policy.', key)
            return None
        try:
            parsed_policy[key] = int(parsed_policy[key])
        except ValueError:
            logger.error('Expected integer as value for key "%s" in STS '
                         'policy, got %r instead. Ignoring policy.',
                         key, parsed_policy[key])
            return None

    return parsed_policy


def makeLabel():
    """Returns a unique label for outgoing message tags.

    Unicity is not guaranteed across restarts.
    Returns should be handled as opaque strings, using only equality.

    This is used for <https://ircv3.net/specs/extensions/labeled-response>
    """
    return str(uuid.uuid4())


numerics = {
    # <= 2.10
        # Reply
        '001': 'RPL_WELCOME',
        '002': 'RPL_YOURHOST',
        '003': 'RPL_CREATED',
        '004': 'RPL_MYINFO',
        '005': 'RPL_BOUNCE',
        '302': 'RPL_USERHOST',
        '303': 'RPL_ISON',
        '301': 'RPL_AWAY',
        '305': 'RPL_UNAWAY',
        '306': 'RPL_NOWAWAY',
        '311': 'RPL_WHOISUSER',
        '312': 'RPL_WHOISSERVER',
        '313': 'RPL_WHOISOPERATOR',
        '317': 'RPL_WHOISIDLE',
        '318': 'RPL_ENDOFWHOIS',
        '319': 'RPL_WHOISCHANNELS',
        '314': 'RPL_WHOWASUSER',
        '369': 'RPL_ENDOFWHOWAS',
        '321': 'RPL_LISTSTART',
        '322': 'RPL_LIST',
        '323': 'RPL_LISTEND',
        '325': 'RPL_UNIQOPIS',
        '324': 'RPL_CHANNELMODEIS',
        '331': 'RPL_NOTOPIC',
        '332': 'RPL_TOPIC',
        '341': 'RPL_INVITING',
        '342': 'RPL_SUMMONING',
        '346': 'RPL_INVITELIST',
        '347': 'RPL_ENDOFINVITELIST',
        '348': 'RPL_EXCEPTLIST',
        '349': 'RPL_ENDOFEXCEPTLIST',
        '351': 'RPL_VERSION',
        '352': 'RPL_WHOREPLY',
        '352': 'RPL_WHOREPLY',
        '353': 'RPL_NAMREPLY',
        '366': 'RPL_ENDOFNAMES',
        '364': 'RPL_LINKS',
        '365': 'RPL_ENDOFLINKS',
        '367': 'RPL_BANLIST',
        '368': 'RPL_ENDOFBANLIST',
        '371': 'RPL_INFO',
        '374': 'RPL_ENDOFINFO',
        '372': 'RPL_MOTD',
        '376': 'RPL_ENDOFMOTD',
        '381': 'RPL_YOUREOPER',
        '382': 'RPL_REHASHING',
        '383': 'RPL_YOURESERVICE',
        '391': 'RPL_TIME',
        '392': 'RPL_USERSSTART',
        '393': 'RPL_USERS',
        '394': 'RPL_ENDOFUSERS',
        '395': 'RPL_NOUSERS',
        '200': 'RPL_TRACELINK',
        '201': 'RPL_TRACECONNECTING',
        '202': 'RPL_TRACEHANDSHAKE',
        '203': 'RPL_TRACEUNKNOWN',
        '204': 'RPL_TRACEOPERATOR',
        '205': 'RPL_TRACEUSER',
        '206': 'RPL_TRACESERVER',
        '207': 'RPL_TRACESERVICE',
        '208': 'RPL_TRACENEWTYPE',
        '209': 'RPL_TRACECLASS',
        '210': 'RPL_TRACERECONNECT',
        '261': 'RPL_TRACELOG',
        '262': 'RPL_TRACEEND',
        '211': 'RPL_STATSLINKINFO',
        '212': 'RPL_STATSCOMMANDS',
        '219': 'RPL_ENDOFSTATS',
        '242': 'RPL_STATSUPTIME',
        '243': 'RPL_STATSOLINE',
        '221': 'RPL_UMODEIS',
        '234': 'RPL_SERVLIST',
        '235': 'RPL_SERVLISTEND',
        '251': 'RPL_LUSERCLIENT',
        '252': 'RPL_LUSEROP',
        '253': 'RPL_LUSERUNKNOWN',
        '254': 'RPL_LUSERCHANNELS',
        '255': 'RPL_LUSERME',
        '256': 'RPL_ADMINME',
        '257': 'RPL_ADMINLOC1',
        '258': 'RPL_ADMINLOC2',
        '259': 'RPL_ADMINEMAIL',
        '263': 'RPL_TRYAGAIN',

        # Error
        '401': 'ERR_NOSUCHNICK',
        '402': 'ERR_NOSUCHSERVER',
        '403': 'ERR_NOSUCHCHANNEL',
        '404': 'ERR_CANNOTSENDTOCHAN',
        '405': 'ERR_TOOMANYCHANNELS',
        '406': 'ERR_WASNOSUCHNICK',
        '407': 'ERR_TOOMANYTARGETS',
        '408': 'ERR_NOSUCHSERVICE',
        '409': 'ERR_NOORIGIN',
        '411': 'ERR_NORECIPIENT',
        '412': 'ERR_NOTEXTTOSEND',
        '413': 'ERR_NOTOPLEVEL',
        '414': 'ERR_WILDTOPLEVEL',
        '415': 'ERR_BADMASK',
        '421': 'ERR_UNKNOWNCOMMAND',
        '422': 'ERR_NOMOTD',
        '423': 'ERR_NOADMININFO',
        '424': 'ERR_FILEERROR',
        '431': 'ERR_NONICKNAMEGIVEN',
        '432': 'ERR_ERRONEUSNICKNAME',
        '433': 'ERR_NICKNAMEINUSE',
        '436': 'ERR_NICKCOLLISION',
        '437': 'ERR_UNAVAILRESOURCE',
        '441': 'ERR_USERNOTINCHANNEL',
        '442': 'ERR_NOTONCHANNEL',
        '443': 'ERR_USERONCHANNEL',
        '444': 'ERR_NOLOGIN',
        '445': 'ERR_SUMMONDISABLED',
        '446': 'ERR_USERSDISABLED',
        '451': 'ERR_NOTREGISTERED',
        '461': 'ERR_NEEDMOREPARAMS',
        '462': 'ERR_ALREADYREGISTRED',
        '463': 'ERR_NOPERMFORHOST',
        '464': 'ERR_PASSWDMISMATCH',
        '465': 'ERR_YOUREBANNEDCREEP',
        '466': 'ERR_YOUWILLBEBANNED',
        '467': 'ERR_KEYSET',
        '471': 'ERR_CHANNELISFULL',
        '472': 'ERR_UNKNOWNMODE',
        '473': 'ERR_INVITEONLYCHAN',
        '474': 'ERR_BANNEDFROMCHAN',
        '475': 'ERR_BADCHANNELKEY',
        '476': 'ERR_BADCHANMASK',
        '477': 'ERR_NOCHANMODES',
        '478': 'ERR_BANLISTFULL',
        '481': 'ERR_NOPRIVILEGES',
        '482': 'ERR_CHANOPRIVSNEEDED',
        '483': 'ERR_CANTKILLSERVER',
        '484': 'ERR_RESTRICTED',
        '485': 'ERR_UNIQOPPRIVSNEEDED',
        '491': 'ERR_NOOPERHOST',
        '501': 'ERR_UMODEUNKNOWNFLAG',
        '502': 'ERR_USERSDONTMATCH',

        # Reserved
        '231': 'RPL_SERVICEINFO',
        '232': 'RPL_ENDOFSERVICES',
        '233': 'RPL_SERVICE',
        '300': 'RPL_NONE',
        '316': 'RPL_WHOISCHANOP',
        '361': 'RPL_KILLDONE',
        '362': 'RPL_CLOSING',
        '363': 'RPL_CLOSEEND',
        '373': 'RPL_INFOSTART',
        '384': 'RPL_MYPORTIS',
        '213': 'RPL_STATSCLINE',
        '214': 'RPL_STATSNLINE',
        '215': 'RPL_STATSILINE',
        '216': 'RPL_STATSKLINE',
        '217': 'RPL_STATSQLINE',
        '218': 'RPL_STATSYLINE',
        '240': 'RPL_STATSVLINE',
        '241': 'RPL_STATSLLINE',
        '244': 'RPL_STATSHLINE',
        '244': 'RPL_STATSSLINE',
        '246': 'RPL_STATSPING',
        '247': 'RPL_STATSBLINE',
        '250': 'RPL_STATSDLINE',
        '492': 'ERR_NOSERVICEHOST',

    # IRC v3.1
        # SASL
        '900': 'RPL_LOGGEDIN',
        '901': 'RPL_LOGGEDOUT',
        '902': 'ERR_NICKLOCKED',
        '903': 'RPL_SASLSUCCESS',
        '904': 'ERR_SASLFAIL',
        '905': 'ERR_SASLTOOLONG',
        '906': 'ERR_SASLABORTED',
        '907': 'ERR_SASLALREADY',
        '908': 'RPL_SASLMECHS',

    # IRC v3.2
        # Metadata
        '760': 'RPL_WHOISKEYVALUE',
        '761': 'RPL_KEYVALUE',
        '762': 'RPL_METADATAEND',
        '764': 'ERR_METADATALIMIT',
        '765': 'ERR_TARGETINVALID',
        '766': 'ERR_NOMATCHINGKEY',
        '767': 'ERR_KEYINVALID',
        '768': 'ERR_KEYNOTSET',
        '769': 'ERR_KEYNOPERMISSION',

        # Monitor
        '730': 'RPL_MONONLINE',
        '731': 'RPL_MONOFFLINE',
        '732': 'RPL_MONLIST',
        '733': 'RPL_ENDOFMONLIST',
        '734': 'ERR_MONLISTFULL',
}

if __name__ == '__main__':
    import doctest
    doctest.testmod(sys.modules['__main__'])
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
