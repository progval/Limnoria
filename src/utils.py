#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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
Simple utility functions.
"""

__revision__ = "$Id$"

import supybot.fix as fix

import os
import re
import md5
import new
import sha
import types
import socket
import string
import sgmllib
import compiler
import textwrap
import UserDict
import htmlentitydefs
from itertools import imap, ifilter

from supybot.structures import TwoWayDictionary

curry = new.instancemethod

def normalizeWhitespace(s):
    """Normalizes the whitespace in a string; \s+ becomes one space."""
    return ' '.join(s.split())

class HtmlToText(sgmllib.SGMLParser):
    """Taken from some eff-bot code on c.l.p."""
    entitydefs = htmlentitydefs.entitydefs.copy()
    entitydefs['nbsp'] = ' '
    def __init__(self, tagReplace=' '):
        self.data = []
        self.tagReplace = tagReplace
        sgmllib.SGMLParser.__init__(self)

    def unknown_starttag(self, tag, attr):
        self.data.append(self.tagReplace)

    def unknown_endtag(self, tag):
        self.data.append(self.tagReplace)

    def handle_data(self, data):
        self.data.append(data)

    def getText(self):
        text = ''.join(self.data).strip()
        return normalizeWhitespace(text)

def htmlToText(s, tagReplace=' '):
    """Turns HTML into text.  tagReplace is a string to replace HTML tags with.
    """
    x = HtmlToText(tagReplace)
    x.feed(s)
    return x.getText()

def eachSubstring(s):
    """Returns every substring starting at the first index until the last."""
    for i in xrange(1, len(s)+1):
        yield s[:i]

def abbrev(strings, d=None):
    """Returns a dictionary mapping unambiguous abbreviations to full forms."""
    if d is None:
        d = {}
    for s in strings:
        for abbreviation in eachSubstring(s):
            if abbreviation not in d:
                d[abbreviation] = s
            else:
                if abbreviation not in strings:
                    d[abbreviation] = None
    removals = []
    for key in d:
        if d[key] is None:
            removals.append(key)
    for key in removals:
        del d[key]
    return d

def timeElapsed(elapsed, leadingZeroes=False, years=True, weeks=True,
                days=True, hours=True, minutes=True, seconds=True):
    """Given <elapsed> seconds, returns a string with an English description of
    how much time as passed.  leadingZeroes determines whether 0 days, 0 hours,
    etc. will be printed; the others determine what larger time periods should
    be used.
    """
    elapsed = int(elapsed)
    assert years or weeks or days or \
           hours or minutes or seconds, 'One flag must be True'
    ret = []
    if years:
        yrs, elapsed = elapsed // 31536000, elapsed % 31536000
        if leadingZeroes or yrs:
            if yrs:
                leadingZeroes = True
            ret.append(nItems('year', yrs))
    if weeks:
        wks, elapsed = elapsed // 604800, elapsed % 604800
        if leadingZeroes or wks:
            if wks:
                leadingZeroes = True
            ret.append(nItems('week', wks))
    if days:
        ds, elapsed = elapsed // 86400, elapsed % 86400
        if leadingZeroes or ds:
            if ds:
                leadingZeroes = True
            ret.append(nItems('day', ds))
    if hours:
        hrs, elapsed = elapsed // 3600, elapsed % 3600
        if leadingZeroes or hrs:
            if hrs:
                leadingZeroes = True
            ret.append(nItems('hour', hrs))
    if minutes or seconds:
        mins, secs = elapsed // 60, elapsed % 60
        if leadingZeroes or mins:
            ret.append(nItems('minute', mins))
        if seconds:
            ret.append(nItems('second', secs))
    if len(ret) == 0:
        raise ValueError, 'Time difference not great enough to be noted.'
    if len(ret) == 1:
        return ret[0]
    else:
        return commaAndify(ret)

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

_soundextrans = string.maketrans(string.ascii_uppercase,
                                 '01230120022455012623010202')
_notUpper = string.ascii.translate(string.ascii, string.ascii_uppercase)
def soundex(s, length=4):
    """Returns the soundex hash of a given string."""
    s = s.upper() # Make everything uppercase.
    s = s.translate(string.ascii, _notUpper) # Delete non-letters.
    if not s:
        raise ValueError, 'Invalid string for soundex: %s'
    firstChar = s[0] # Save the first character.
    s = s.translate(_soundextrans) # Convert to soundex numbers.
    s = s.lstrip(s[0]) # Remove all repeated first characters.
    L = [firstChar]
    for c in s:
        if c != L[-1]:
            L.append(c)
    L = [c for c in L if c != '0'] + (['0']*(length-1))
    s = ''.join(L)
    return length and s[:length] or s.rstrip('0')

def dqrepr(s):
    """Returns a repr() of s guaranteed to be in double quotes."""
    # The wankers-that-be decided not to use double-quotes anymore in 2.3.
    # return '"' + repr("'\x00" + s)[6:]
    return '"%s"' % s.encode('string_escape').replace('"', '\\"')

nonEscapedSlashes = re.compile(r'(?<!\\)/')
def perlReToPythonRe(s):
    """Converts a string representation of a Perl regular expression (i.e.,
    m/^foo$/i or /foo|bar/) to a Python regular expression.
    """
    try:
        (kind, regexp, flags) = nonEscapedSlashes.split(s)
    except ValueError: # Unpack list of wrong size.
        raise ValueError, 'Must be of the form m/.../ or /.../'
    regexp = regexp.replace('\\/', '/')
    if kind not in ('', 'm'):
        raise ValueError, 'Invalid kind: must be in ("", "m")'
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
    try:
        (kind, regexp, replace, flags) = nonEscapedSlashes.split(s)
    except ValueError: # Unpack list of wrong size.
        raise ValueError, 'Must be of the form s/.../.../'
    regexp = regexp.replace('\x08', r'\b')
    replace = replace.replace('\\/', '/')
    for i in xrange(10):
        replace = replace.replace(chr(i), r'\%s' % i)
    if kind != 's':
        raise ValueError, 'Invalid kind: must be "s"'
    g = False
    if 'g' in flags:
        g = True
        flags = filter('g'.__ne__, flags)
    r = perlReToPythonRe('/'.join(('', regexp, flags)))
    if g:
        return curry(r.sub, replace)
    else:
        return lambda s: r.sub(replace, s, 1)

def findBinaryInPath(s):
    """Return full path of a binary if it's in PATH, otherwise return None."""
    cmdLine = None
    for dir in os.getenv('PATH').split(':'):
        filename = os.path.join(dir, s)
        if os.path.exists(filename):
            cmdLine = filename
            break
    return cmdLine

def commaAndify(seq, comma=',', And='and'):
    """Given a a sequence, returns an english clause for that sequence.

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

def wrapLines(s):
    """Word wraps several paragraphs in a string s."""
    L = []
    for line in s.splitlines():
        L.append(textwrap.fill(line))
    return '\n'.join(L)

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
def pluralize(s, i=2):
    """Returns the plural of s based on its number i.  Put any exceptions to
    the general English rule of appending 's' in the plurals dictionary.
    """
    if i == 1:
        return s
    else:
        lowered = s.lower()
        # Exception dictionary
        if lowered in plurals:
            return matchCase(s, plurals[lowered])
        # Words ending with 'ch', 'sh' or 'ss' such as 'punch(es)', 'fish(es)
        # and miss(es)
        elif any(lowered.endswith, ['ch', 'sh', 'ss']):
            return matchCase(s, s+'es')
        # Words ending with a consonant followed by a 'y' such as
        # 'try (tries)' or 'spy (spies)'
        elif re.search(_pluralizeRegex, lowered):
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

def nItems(item, n, between=None):
    """Works like this:

    >>> nItems('clock', 1)
    '1 clock'

    >>> nItems('clock', 10)
    '10 clocks'

    >>> nItems('clock', 10, between='grandfather')
    '10 grandfather clocks'
    """
    if between is None:
        return '%s %s' % (n, pluralize(item, n))
    else:
        return '%s %s %s' % (n, between, pluralize(item, n))

def be(i):
    """Returns the form of the verb 'to be' based on the number i."""
    if i == 1:
        return 'is'
    else:
        return 'are'

def sortBy(f, L):
    """Uses the decorate-sort-undecorate pattern to sort L by function f."""
    for (i, elt) in enumerate(L):
        L[i] = (f(elt), i, elt)
    L.sort()
    for (i, elt) in enumerate(L):
        L[i] = L[i][2]

def sorted(iterable, cmp=None, key=None, reversed=False):
    L = list(iterable)
    if key is not None:
        sortBy(key, L, cmp=cmp)
    else:
        L.sort(cmp)
    if reversed:
        L.reverse()
    return L

__builtins__['sorted'] = sorted

def mktemp(suffix=''):
    """Gives a decent random string, suitable for a filename."""
    import sha
    import md5
    import time
    import random
    r = random.Random()
    m = md5.md5(suffix)
    r.seed(time.time())
    s = str(r.getstate())
    for x in xrange(0, random.randrange(400), random.randrange(1, 5)):
        m.update(str(x))
        m.update(s)
        m.update(str(time.time()))
        s = m.hexdigest()
    return sha.sha(s + str(time.time())).hexdigest() + suffix

def itersplit(isSeparator, iterable, maxsplit=-1, yieldEmpty=False):
    """Splits an iterator based on a predicate isSeparator."""
    acc = []
    for element in iterable:
        if maxsplit == 0 or not isSeparator(element):
            acc.append(element)
        else:
            maxsplit -= 1
            if acc or yieldEmpty:
                yield acc
            acc = []
    if acc or yieldEmpty:
        yield acc

def flatten(seq, strings=False):
    """Flattens a list of lists into a single list.  See the test for examples.
    """
    for elt in seq:
        if not strings and type(elt) == str or type(elt) == unicode:
            yield elt
        else:
            try:
                for x in flatten(elt):
                    yield x
            except TypeError:
                yield elt

def saltHash(password, salt=None, hash='sha'):
    if salt is None:
        salt = mktemp()[:8]
    if hash == 'sha':
        hasher = sha.sha
    elif hash == 'md5':
        hasher = md5.md5
    return '|'.join([salt, hasher(salt + password).hexdigest()])

def safeEval(s, namespace={'True': True, 'False': False, 'None': None}):
    """Evaluates s, safely.  Useful for turning strings into tuples/lists/etc.
    without unsafely using eval()."""
    node = compiler.parse(s)
    nodes = compiler.parse(s).node.nodes
    if not nodes:
        if node.__class__ is compiler.ast.Module:
            return node.doc
        else:
            raise ValueError, 'Unsafe string.'
    node = nodes[0]
    if node.__class__ is not compiler.ast.Discard:
        raise ValueError, 'Invalid expression: %s'
    node = node.getChildNodes()[0]
    def checkNode(node):
        if node.__class__ is compiler.ast.Const:
            return True
        if node.__class__ in (compiler.ast.List,
                              compiler.ast.Tuple,
                              compiler.ast.Dict):
            return all(checkNode, node.getChildNodes())
        if node.__class__ is compiler.ast.Name:
            if node.name in namespace:
                return True
            else:
                return False
        else:
            return False
    if checkNode(node):
        return eval(s, namespace, namespace)
    else:
        raise ValueError, 'Unsafe string.'

def exnToString(e):
    """Turns a simple exception instance into a string (better than str(e))"""
    return '%s: %s' % (e.__class__.__name__, e)

class IterableMap(object):
    """Define .iteritems() in a class and subclass this to get the other iters.
    """
    def iteritems(self):
        raise NotImplementedError

    def iterkeys(self):
        for (key, _) in self.iteritems():
            yield key
    __iter__ = iterkeys

    def itervalues(self):
        for (_, value) in self.iteritems():
            yield value

    def items(self):
        return list(self.iteritems())

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def __len__(self):
        ret = 0
        for _ in self.iteritems():
            ret += 1
        return ret

    def __nonzero__(self):
        for _ in self.iteritems():
            return True
        return False


def nonCommentLines(fd):
    for line in fd:
        if not line.startswith('#'):
            yield line

def nonEmptyLines(fd):
##     for line in fd:
##         if line.strip():
##             yield line
    return ifilter(str.strip, fd)

def nonCommentNonEmptyLines(fd):
    return nonEmptyLines(nonCommentLines(fd))

def changeFunctionName(f, name, doc=None):
    if doc is None:
        doc = f.__doc__
    newf = types.FunctionType(f.func_code, f.func_globals, name,
                              f.func_defaults, f.func_closure)
    newf.__doc__ = doc
    return newf

def getSocket(host):
    """Returns a socket of the correct AF_INET type (v4 or v6) in order to
    communicate with host.
    """
    try:
        host = socket.gethostbyname(host)
    except socket.error:
        raise
    if isIP(host):
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    elif isIPV6(host):
        return socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    else:
        raise socket.error, 'Something wonky happened.'

_ipchars = string.digits + '.'
def isIP(s):
    """Returns whether or not a given string is an IPV4 address.

    >>> isIP('255.255.255.255')
    1

    >>> isIP('abc.abc.abc.abc')
    0
    """
    try:
        return bool(socket.inet_aton(s))
    except socket.error:
        return False

def isIPV6(s):
    """Returns whether or not a given string is an IPV6 address."""
    try:
        return bool(socket.inet_pton(socket.AF_INET6, s))
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, '::')
        except socket.error:
            # We gotta fake it.
            if s.count('::') <= 1:
                L = s.split(':')
                if len(L) <= 8:
                    for x in L:
                        if x:
                            try:
                                int(x, 16)
                            except ValueError:
                                return False
                    return True
        return False

class InsensitivePreservingDict(UserDict.DictMixin, object):
    key = staticmethod(str.lower)
    def __init__(self, dict=None, key=None):
        if key is not None:
            self.key = key
        self.data = {}
        if dict is not None:
            self.update(dict)

    def fromkeys(cls, keys, s=None, dict=None, key=None):
        d = cls(dict=dict, key=key)
        for key in keys:
            d[key] = s
        return d
    fromkeys = classmethod(fromkeys)

    def __getitem__(self, k):
        return self.data[self.key(k)][1]

    def __setitem__(self, k, v):
        self.data[self.key(k)] = (k, v)

    def __delitem__(self, k):
        del self.data[self.key(k)]

    def iteritems(self):
        return self.data.itervalues()

    def keys(self):
        L = []
        for (k, _) in self.iteritems():
            L.append(k)
        return L

    def __reduce__(self):
        return (self.__class__, (dict(self.data.values()),))

def mungeEmailForWeb(s):
    s = s.replace('@', ' AT ')
    s = s.replace('.', ' DOT ')
    return s


if __name__ == '__main__':
    import sys, doctest
    doctest.testmod(sys.modules['__main__'])


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
