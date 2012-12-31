###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008-2009, James McCoy
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
Simple utility functions related to strings.
"""

import re
import new
import sys
import string
import textwrap

from .iter import all, any
from .structures import TwoWayDictionary

curry = new.instancemethod
chars = string.maketrans('', '')

def rsplit(s, sep=None, maxsplit=-1):
    """Equivalent to str.split, except splitting from the right."""
    if sys.version_info < (2, 4, 0):
        if sep is not None:
            sep = sep[::-1]
        L = s[::-1].split(sep, maxsplit)
        L.reverse()
        return [s[::-1] for s in L]
    else:
        return s.rsplit(sep, maxsplit)

def normalizeWhitespace(s):
    """Normalizes the whitespace in a string; \s+ becomes one space."""
    return ' '.join(s.split())

def distance(s, t):
    """Returns the levenshtein edit distance between two strings."""
    n = len(s)
    m = len(t)
    if n == 0:
        return m
    elif m == 0:
        return n
    d = []
    for i in xrange(n+1):
        d.append([])
        for j in xrange(m+1):
            d[i].append(0)
            d[0][j] = j
        d[i][0] = i
    for i in xrange(1, n+1):
        cs = s[i-1]
        for j in xrange(1, m+1):
            ct = t[j-1]
            cost = int(cs != ct)
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost)
    return d[n][m]

_soundextrans = string.maketrans(string.ascii_uppercase,
                                 '01230120022455012623010202')
_notUpper = chars.translate(chars, string.ascii_uppercase)
def soundex(s, length=4):
    """Returns the soundex hash of a given string.

    length=0 doesn't truncate the hash.
    """
    s = s.upper() # Make everything uppercase.
    s = s.translate(chars, _notUpper) # Delete non-letters.
    if not s:
        raise ValueError, 'Invalid string for soundex: %s'
    firstChar = s[0] # Save the first character.
    s = s.translate(_soundextrans) # Convert to soundex numbers.
    s = s.lstrip(s[0]) # Remove all repeated first characters.
    L = [firstChar]
    for c in s:
        if c != L[-1]:
            L.append(c)
    L = [c for c in L if c != '0']
    s = ''.join(L)
    if length:
        s = s.ljust(length, '0')[:length]
    return s

def dqrepr(s):
    """Returns a repr() of s guaranteed to be in double quotes."""
    # The wankers-that-be decided not to use double-quotes anymore in 2.3.
    # return '"' + repr("'\x00" + s)[6:]
    return '"%s"' % s.encode('string_escape').replace('"', '\\"')

def quoted(s):
    """Returns a quoted s."""
    return '"%s"' % s

_openers = '{[(<'
_closers = '}])>'
def _getSep(s, allowBraces=False):
    if len(s) < 2:
        raise ValueError, 'string given to _getSep is too short: %r' % s
    if allowBraces:
        braces = _closers
    else:
        braces = _openers + _closers
    if s.startswith('m') or s.startswith('s'):
        separator = s[1]
    else:
        separator = s[0]
    if separator.isalnum() or separator in braces:
        raise ValueError, \
              'Invalid separator: separator must not be alphanumeric or in ' \
              '"%s"' % braces
    return separator

def perlReToPythonRe(s):
    """Converts a string representation of a Perl regular expression (i.e.,
    m/^foo$/i or /foo|bar/) to a Python regular expression.
    """
    opener = closer = _getSep(s, True)
    if opener in '{[(<':
        closer = _closers[_openers.index(opener)]
    opener = re.escape(opener)
    closer = re.escape(closer)
    matcher = re.compile(r'm?%s((?:\\.|[^\\])*)%s(.*)' % (opener, closer))
    try:
        (regexp, flags) = matcher.match(s).groups()
    except AttributeError: # Unpack list of wrong size.
        raise ValueError, 'Must be of the form m/.../ or /.../'
    regexp = regexp.replace('\\'+opener, opener)
    if opener != closer:
        regexp = regexp.replace('\\'+closer, closer)
    flag = 0
    try:
        for c in flags.upper():
            flag |= getattr(re, c)
    except AttributeError:
        raise ValueError, 'Invalid flag: %s' % c
    try:
        return re.compile(regexp, flag)
    except re.error, e:
        raise ValueError, str(e)

def perlReToReplacer(s):
    """Converts a string representation of a Perl regular expression (i.e.,
    s/foo/bar/g or s/foo/bar/i) to a Python function doing the equivalent
    replacement.
    """
    sep = _getSep(s)
    escaped = re.escape(sep)
    matcher = re.compile(r's%s((?:\\.|[^\\])*)%s((?:\\.|[^\\])*)%s(.*)'
                         % (escaped, escaped, escaped))
    try:
        (regexp, replace, flags) = matcher.match(s).groups()
    except AttributeError: # Unpack list of wrong size.
        raise ValueError, 'Must be of the form s/.../.../'
    regexp = regexp.replace('\x08', r'\b')
    replace = replace.replace('\\'+sep, sep)
    for i in xrange(10):
        replace = replace.replace(chr(i), r'\%s' % i)
    g = False
    if 'g' in flags:
        g = True
        flags = filter('g'.__ne__, flags)
    r = perlReToPythonRe(sep.join(('', regexp, flags)))
    if g:
        return curry(r.sub, replace)
    else:
        return lambda s: r.sub(replace, s, 1)

_perlVarSubstituteRe = re.compile(r'\$\{([^}]+)\}|\$([a-zA-Z][a-zA-Z0-9]*)')
def perlVariableSubstitute(vars, text):
    def replacer(m):
        (braced, unbraced) = m.groups()
        var = braced or unbraced
        try:
            x = vars[var]
            if callable(x):
                return x()
            else:
                return str(x)
        except KeyError:
            if braced:
                return '${%s}' % braced
            else:
                return '$' + unbraced
    return _perlVarSubstituteRe.sub(replacer, text)

def commaAndify(seq, comma=',', And='and'):
    """Given a a sequence, returns an English clause for that sequence.

    I.e., given [1, 2, 3], returns '1, 2, and 3'
    """
    L = list(seq)
    if len(L) == 0:
        return ''
    elif len(L) == 1:
        return ''.join(L) # We need this because it raises TypeError.
    elif len(L) == 2:
        L.insert(1, And)
        return ' '.join(L)
    else:
        L[-1] = '%s %s' % (And, L[-1])
        sep = '%s ' % comma
        return sep.join(L)

_unCommaTheRe = re.compile(r'(.*),\s*(the)$', re.I)
def unCommaThe(s):
    """Takes a string of the form 'foo, the' and turns it into 'the foo'."""
    m = _unCommaTheRe.match(s)
    if m is not None:
        return '%s %s' % (m.group(2), m.group(1))
    else:
        return s

def ellipsisify(s, n):
    """Returns a shortened version of s.  Produces up to the first n chars at
    the nearest word boundary.
    """
    if len(s) <= n:
        return s
    else:
        return (textwrap.wrap(s, n-3)[0] + '...')

plurals = TwoWayDictionary({})
def matchCase(s1, s2):
    """Matches the case of s1 in s2"""
    if s1.isupper():
        return s2.upper()
    else:
        L = list(s2)
        for (i, char) in enumerate(s1[:len(s2)]):
            if char.isupper():
                L[i] = L[i].upper()
        return ''.join(L)

consonants = 'bcdfghjklmnpqrstvwxz'
_pluralizeRegex = re.compile('[%s]y$' % consonants)
def pluralize(s):
    """Returns the plural of s.  Put any exceptions to the general English
    rule of appending 's' in the plurals dictionary.
    """
    lowered = s.lower()
    # Exception dictionary
    if lowered in plurals:
        return matchCase(s, plurals[lowered])
    # Words ending with 'ch', 'sh' or 'ss' such as 'punch(es)', 'fish(es)
    # and miss(es)
    elif any(lowered.endswith, ['x', 'ch', 'sh', 'ss']):
        return matchCase(s, s+'es')
    # Words ending with a consonant followed by a 'y' such as
    # 'try (tries)' or 'spy (spies)'
    elif _pluralizeRegex.search(lowered):
        return matchCase(s, s[:-1] + 'ies')
    # In all other cases, we simply add an 's' to the base word
    else:
        return matchCase(s, s+'s')

_depluralizeRegex = re.compile('[%s]ies' % consonants)
def depluralize(s):
    """Returns the singular of s."""
    lowered = s.lower()
    if lowered in plurals:
        return matchCase(s, plurals[lowered])
    elif any(lowered.endswith, ['ches', 'shes', 'sses']):
        return s[:-2]
    elif re.search(_depluralizeRegex, lowered):
        return s[:-3] + 'y'
    else:
        if lowered.endswith('s'):
            return s[:-1] # Chop off 's'.
        else:
            return s # Don't know what to do.

def nItems(n, item, between=None):
    """Works like this:

    >>> nItems(1, 'clock')
    '1 clock'

    >>> nItems(10, 'clock')
    '10 clocks'

    >>> nItems(10, 'clock', between='grandfather')
    '10 grandfather clocks'
    """
    assert isinstance(n, int) or isinstance(n, long), \
           'The order of the arguments to nItems changed again, sorry.'
    if between is None:
        if n != 1:
            return format('%s %p', n, item)
        else:
            return format('%s %s', n, item)
    else:
        if n != 1:
            return format('%s %s %p', n, between, item)
        else:
            return format('%s %s %s', n, between, item)

def ordinal(i):
    """Returns i + the ordinal indicator for the number.

    Example: ordinal(3) => '3rd'
    """
    i = int(i)
    if i % 100 in (11,12,13):
        return '%sth' % i
    ord = 'th'
    test = i % 10
    if test == 1:
        ord = 'st'
    elif test == 2:
        ord = 'nd'
    elif test == 3:
        ord = 'rd'
    return '%s%s' % (i, ord)

def be(i):
    """Returns the form of the verb 'to be' based on the number i."""
    if i == 1:
        return 'is'
    else:
        return 'are'

def has(i):
    """Returns the form of the verb 'to have' based on the number i."""
    if i == 1:
        return 'has'
    else:
        return 'have'

def toBool(s):
    s = s.strip().lower()
    if s in ('true', 'on', 'enable', 'enabled', '1'):
        return True
    elif s in ('false', 'off', 'disable', 'disabled', '0'):
        return False
    else:
        raise ValueError, 'Invalid string for toBool: %s' % quoted(s)

# When used with Supybot, this is overriden when supybot.conf is loaded
def timestamp(t):
    if t is None:
        t = time.time()
    return time.ctime(t)

_formatRe = re.compile('%((?:\d+)?\.\d+f|[bfhiLnpqrstu%])')
def format(s, *args, **kwargs):
    """w00t.

    %: literal %.
    i: integer
    s: string
    f: float
    r: repr
    b: form of the verb 'to be' (takes an int)
    h: form of the verb 'to have' (takes an int)
    L: commaAndify (takes a list of strings or a tuple of ([strings], and))
    p: pluralize (takes a string)
    q: quoted (takes a string)
    n: nItems (takes a 2-tuple of (n, item) or a 3-tuple of (n, between, item))
    t: time, formatted (takes an int)
    u: url, wrapped in braces (this should be configurable at some point)
    """
    args = list(args)
    args.reverse() # For more efficient popping.
    def sub(match):
        char = match.group(1)
        if char == 's':
            return str(args.pop())
        elif char == 'i':
            # XXX Improve me!
            return str(args.pop())
        elif char.endswith('f'):
            return ('%'+char) % args.pop()
        elif char == 'b':
            return be(args.pop())
        elif char == 'h':
            return has(args.pop())
        elif char == 'L':
            t = args.pop()
            if isinstance(t, list):
                return commaAndify(t)
            elif isinstance(t, tuple) and len(t) == 2:
                if not isinstance(t[0], list):
                    raise ValueError, \
                          'Invalid list for %%L in format: %s' % t
                if not isinstance(t[1], basestring):
                    raise ValueError, \
                          'Invalid string for %%L in format: %s' % t
                return commaAndify(t[0], And=t[1])
            else:
                raise ValueError, 'Invalid value for %%L in format: %s' % t
        elif char == 'p':
            return pluralize(args.pop())
        elif char == 'q':
            return quoted(args.pop())
        elif char == 'r':
            return repr(args.pop())
        elif char == 'n':
            t = args.pop()
            if not isinstance(t, (tuple, list)):
                raise ValueError, 'Invalid value for %%n in format: %s' % t
            if len(t) == 2:
                return nItems(*t)
            elif len(t) == 3:
                return nItems(t[0], t[2], between=t[1])
            else:
                raise ValueError, 'Invalid value for %%n in format: %s' % t
        elif char == 't':
            return timestamp(args.pop())
        elif char == 'u':
            return '<%s>' % args.pop()
        elif char == '%':
            return '%'
        else:
            raise ValueError, 'Invalid char in sub (in format).'
    try:
        return _formatRe.sub(sub, s)
    except IndexError:
        raise ValueError, 'Extra format chars in format spec: %r' % s

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
