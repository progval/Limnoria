###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008-2009, James McCoy
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
###

"""
Simple utility functions related to strings.
"""

import re
import sys
import time
import string
import textwrap

from . import minisix
from .iter import any
from .structures import TwoWayDictionary

from . import internationalization as _
internationalizeFunction = _.internationalizeFunction

try:
    from charade.universaldetector import UniversalDetector
    charadeLoaded = True
except ImportError:
    charadeLoaded = False

if minisix.PY3:
    def decode_raw_line(line):
        #first, try to decode using utf-8
        try:
            line = line.decode('utf8', 'strict')
        except UnicodeError:
            # if this fails and charade is loaded, try to guess the correct encoding
            if charadeLoaded:
                u = UniversalDetector()
                u.feed(line)
                u.close()
                if u.result['encoding']:
                    # try to use the guessed encoding
                    try:
                        line = line.decode(u.result['encoding'],
                            'strict')
                    # on error, give up and replace the offending characters
                    except UnicodeError:
                        line = line.decode(errors='replace')
                else:
                    # if no encoding could be guessed, fall back to utf-8 and
                    # replace offending characters
                    line = line.decode('utf8', 'replace')
            # if charade is not loaded, try to decode using utf-8 and replace any
            # offending characters
            else:
                line = line.decode('utf8', 'replace')
        return line
else:
    def decode_raw_line(line):
        return line

def rsplit(s, sep=None, maxsplit=-1):
    """Equivalent to str.split, except splitting from the right."""
    return s.rsplit(sep, maxsplit)

def normalizeWhitespace(s, removeNewline=True):
    r"""Normalizes the whitespace in a string; \s+ becomes one space."""
    if not s:
        return str(s) # not the same reference
    starts_with_space = (s[0] in ' \n\t\r')
    ends_with_space = (s[-1] in ' \n\t\r')
    if removeNewline:
        newline_re = re.compile('[\r\n]+')
        s = ' '.join(filter(bool, newline_re.split(s)))
    s = ' '.join(filter(bool, s.split('\t')))
    s = ' '.join(filter(bool, s.split(' ')))
    if starts_with_space:
        s = ' ' + s
    if ends_with_space:
        s += ' '
    return s

def distance(s, t):
    """Returns the levenshtein edit distance between two strings."""
    n = len(s)
    m = len(t)
    if n == 0:
        return m
    elif m == 0:
        return n
    d = []
    for i in range(n+1):
        d.append([])
        for j in range(m+1):
            d[i].append(0)
            d[0][j] = j
        d[i][0] = i
    for i in range(1, n+1):
        cs = s[i-1]
        for j in range(1, m+1):
            ct = t[j-1]
            cost = int(cs != ct)
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost)
    return d[n][m]

class MultipleReplacer:
    """Return a callable that replaces all dict keys by the associated
    value. More efficient than multiple .replace()."""

    # We use an object instead of a lambda function because it avoids the
    # need for using the staticmethod() on the lambda function if assigning
    # it to a class in Python 3.
    def __init__(self, dict_):
        self._dict = dict_
        dict_ = dict([(re.escape(key), val) for key,val in dict_.items()])
        self._matcher = re.compile('|'.join(dict_.keys()))
    def __call__(self, s):
        return self._matcher.sub(lambda m: self._dict[m.group(0)], s)
def multipleReplacer(dict_):
    return MultipleReplacer(dict_)

class MultipleRemover:
    """Return a callable that removes all words in the list. A bit more
    efficient than multipleReplacer"""
    # See comment of  MultipleReplacer
    def __init__(self, list_):
        list_ = [re.escape(x) for x in list_]
        self._matcher = re.compile('|'.join(list_))
    def __call__(self, s):
        return self._matcher.sub(lambda m: '', s)

_soundextrans = MultipleReplacer(dict(list(zip(string.ascii_uppercase,
                                 '01230120022455012623010202'))))
def soundex(s, length=4):
    """Returns the soundex hash of a given string.

    length=0 doesn't truncate the hash.
    """
    s = s.upper() # Make everything uppercase.
    s = ''.join([x for x in s if x in string.ascii_uppercase])
    if not s:
        raise ValueError('Invalid string for soundex: %s')
    firstChar = s[0] # Save the first character.
    s = _soundextrans(s) # Convert to soundex numbers.
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
    encoding = 'string_escape' if minisix.PY2 else 'unicode_escape'
    if minisix.PY2 and isinstance(s, unicode):
        s = s.encode('utf8', 'replace')
    return '"%s"' % s.encode(encoding).decode().replace('"', '\\"')

def quoted(s):
    """Returns a quoted s."""
    return '"%s"' % s

_openers = '{[(<'
_closers = '}])>'
def _getSep(s, allowBraces=False):
    if len(s) < 2:
        raise ValueError('string given to _getSep is too short: %r' % s)
    if allowBraces:
        braces = _closers
    else:
        braces = _openers + _closers
    if s.startswith('m') or s.startswith('s'):
        separator = s[1]
    else:
        separator = s[0]
    if separator.isalnum() or separator in braces:
        raise ValueError('Invalid separator: separator must not be alphanumeric or in ' \
              '"%s"' % braces)
    return separator

def perlReToPythonRe(s, allowG=False):
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
        raise ValueError('Must be of the form m/.../ or /.../')
    regexp = regexp.replace('\\'+opener, opener)
    if opener != closer:
        regexp = regexp.replace('\\'+closer, closer)
    flag = 0
    g = False
    try:
        for c in flags.upper():
            if c == 'G' and allowG:
                g = True
                continue
            flag |= getattr(re, c)
    except AttributeError:
        raise ValueError('Invalid flag: %s' % c)
    try:
        r = re.compile(regexp, flag)
    except re.error as e:
        raise ValueError(str(e))
    if allowG:
        return (r, g)
    else:
        return r

def perlReToFindall(s):
    """Converts a string representation of a Perl regular expression (i.e.,
    m/^foo$/i or /foo|bar/) to a Python regular expression, with support for
    G flag
    """
    (r, g) = perlReToPythonRe(s, allowG=True)
    if g:
        return lambda s: r.findall(s)
    else:
        return lambda s: r.search(s) and r.search(s).group(0) or ''

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
        raise ValueError('Must be of the form s/.../.../')
    regexp = regexp.replace('\x08', r'\b')
    replace = replace.replace('\\'+sep, sep)
    for i in range(10):
        replace = replace.replace(chr(i), r'\%s' % i)
    g = False
    if 'g' in flags:
        g = True
        flags = list(filter('g'.__ne__, flags))
    if isinstance(flags, list):
        flags = ''.join(flags)
    r = perlReToPythonRe(sep.join(('', regexp, flags)))
    if g:
        return lambda s: r.sub(replace, s)
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
                try:
                    return str(x)
                except UnicodeEncodeError: # Python 2
                    return str(x).encode('utf8')
        except KeyError:
            if braced:
                return '${%s}' % braced
            else:
                return '$' + unbraced
    return _perlVarSubstituteRe.sub(replacer, text)

def splitBytes(word, size):
    # I'm going to hell for this function
    for i in range(4): # a character takes at most 4 bytes in UTF-8
        try:
            if sys.version_info[0] >= 3:
                word[size-i:].decode()
            else:
                word[size-i:].encode('utf8')
        except UnicodeDecodeError:
            continue
        else:
            return (word[0:size-i], word[size-i:])
    assert False, (word, size)


class ByteTextWrapper(textwrap.TextWrapper):
    def _wrap_chunks(self, words):
        words.reverse() # use it as a stack
        words = [w.encode() for w in words]
        lines = [b'']
        while words:
            word = words.pop(-1)
            if len(word) > self.width:
                (before, after) = splitBytes(word, self.width)
                words.append(after)
                word = before
            if len(lines[-1]) + len(word) <= self.width:
                lines[-1] += word
            else:
                lines.append(word)
        return [l.decode() for l in lines]

def byteTextWrap(text, size, break_on_hyphens=False):
    """Similar to textwrap.wrap(), but considers the size of strings (in bytes)
    instead of their length (in characters)."""
    return ByteTextWrapper(width=size).wrap(text)

def commaAndify(seq, comma=',', And=None):
    """Given a a sequence, returns an English clause for that sequence.

    I.e., given [1, 2, 3], returns '1, 2, and 3'
    """
    if And is None:
        And = _('and')
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

@internationalizeFunction('pluralize')
def pluralize(s):
    """Returns the plural of s.  Put any exceptions to the general English
    rule of appending 's' in the plurals dictionary.
    """
    consonants = 'bcdfghjklmnpqrstvwxz'
    _pluralizeRegex = re.compile('[%s]y$' % consonants)
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

@internationalizeFunction('depluralize')
def depluralize(s):
    """Returns the singular of s."""
    consonants = 'bcdfghjklmnpqrstvwxz'
    _depluralizeRegex = re.compile('[%s]ies' % consonants)
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

    >>> nItems(4, '<empty>')
    '4'

    >>> nItems(1, 'clock')
    '1 clock'

    >>> nItems(10, 'clock')
    '10 clocks'

    >>> nItems(4, '<empty>', between='grandfather')
    '4 grandfather'

    >>> nItems(10, 'clock', between='grandfather')
    '10 grandfather clocks'
    """
    assert isinstance(n, minisix.integer_types), \
           'The order of the arguments to nItems changed again, sorry.'
    if item == '<empty>':
        if between is None:
            return format('%s', n)
        else:
            return format('%s %s', n, item)
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

@internationalizeFunction('ordinal')
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

@internationalizeFunction('be')
def be(i):
    """Returns the form of the verb 'to be' based on the number i."""
    if i == 1:
        return 'is'
    else:
        return 'are'

@internationalizeFunction('has')
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
        raise ValueError('Invalid string for toBool: %s' % quoted(s))

# When used with Supybot, this is overriden when supybot.conf is loaded
def timestamp(t):
    if t is None:
        t = time.time()
    return time.ctime(t)
def url(url):
    return url

_formatRe = re.compile(r'%((?:\d+)?\.\d+f|[bfhiLnpqrsStTuv%])')
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
    S: returns a human-readable size (takes an int)
    t: time, formatted (takes an int)
    T: time delta, formatted (takes an int)
    u: url, wrapped in braces (this should be configurable at some point)
    v: void : takes one or many arguments, but doesn't display it
       (useful for translation)
    """
    # Note to developers: If you want to add an argument type, do not forget
    # to add the character to the _formatRe regexp or it will be ignored
    # (and hard to debug if you don't know the trick).
    # Of course, you should also document it in the docstring above.
    if minisix.PY2:
        def pred(s):
            if isinstance(s, unicode):
                return s.encode('utf8')
            else:
                return s
        args = map(pred, args)
    args = list(args)
    args.reverse() # For more efficient popping.
    def sub(match):
        char = match.group(1)
        if char == 's':
            token = args.pop()
            if isinstance(token, str):
                return token
            elif minisix.PY2 and isinstance(token, unicode):
                return token.encode('utf8', 'replace')
            else:
                return str(token)
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
            if isinstance(t, tuple) and len(t) == 2:
                if not isinstance(t[0], list):
                    raise ValueError('Invalid list for %%L in format: %s' % t)
                if not isinstance(t[1], minisix.string_types):
                    raise ValueError('Invalid string for %%L in format: %s' % t)
                return commaAndify(t[0], And=t[1])
            elif hasattr(t, '__iter__'):
                return commaAndify(t)
            else:
                raise ValueError('Invalid value for %%L in format: %s' % t)
        elif char == 'p':
            return pluralize(args.pop())
        elif char == 'q':
            return quoted(args.pop())
        elif char == 'r':
            return repr(args.pop())
        elif char == 'n':
            t = args.pop()
            if not isinstance(t, (tuple, list)):
                raise ValueError('Invalid value for %%n in format: %s' % t)
            if len(t) == 2:
                return nItems(*t)
            elif len(t) == 3:
                return nItems(t[0], t[2], between=t[1])
            else:
                raise ValueError('Invalid value for %%n in format: %s' % t)
        elif char == 'S':
            t = args.pop()
            if not isinstance(t, minisix.integer_types):
                raise ValueError('Invalid value for %%S in format: %s' % t)
            for suffix in ['B','KB','MB','GB','TB']:
                if t < 1024:
                    return "%i%s" % (t, suffix)
                t /= 1024

        elif char == 't':
            return timestamp(args.pop())
        elif char == 'T':
            from .gen import timeElapsed
            return timeElapsed(args.pop())
        elif char == 'u':
            return url(args.pop())
        elif char == 'v':
            args.pop()
            return ''
        elif char == '%':
            return '%'
        else:
            raise ValueError('Invalid char in sub (in format).')
    try:
        return _formatRe.sub(sub, s)
    except IndexError:
        raise ValueError('Extra format chars in format spec: %r' % s)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
