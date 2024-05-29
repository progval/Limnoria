###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008, James McCoy
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

from __future__ import print_function

import os
import sys
import ast
import textwrap
import warnings
import functools
import traceback
import collections.abc


from . import crypt
from .str import format
from .file import mktemp
from . import minisix

# will be replaced by supybot.i18n.install()
_ = lambda x: x

def warn_non_constant_time(f):
    @functools.wraps(f)
    def newf(*args, **kwargs):
        # This method takes linear time whereas the subclass could probably
        # do it in constant time.
        warnings.warn('subclass of IterableMap does provide an efficient '
                      'implementation of %s' % f.__name__,
                      DeprecationWarning)
        return f(*args, **kwargs)
    return newf


def abbrev(strings, d=None):
    """Returns a dictionary mapping unambiguous abbreviations to full forms."""
    def eachSubstring(s):
        for i in range(1, len(s)+1):
            yield s[:i]
    if len(strings) != len(set(strings)):
        raise ValueError(
              'strings given to utils.abbrev have duplicates: %r' % strings)
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

def timeElapsed(elapsed, short=False, leadingZeroes=False, years=True,
                weeks=True, days=True, hours=True, minutes=True, seconds=True):
    """Given <elapsed> seconds, returns a string with an English description of
    the amount of time passed.  leadingZeroes determines whether 0 days, 0
    hours, etc. will be printed; the others determine what larger time periods
    should be used.
    """
    ret = []
    before = False
    def Format(s, i):
        if i or leadingZeroes or ret:
            if short:
                ret.append('%s%s' % (i, s[0]))
            else:
                ret.append(format('%n', (i, s)))
    elapsed = int(elapsed)

    # Handle negative times
    if elapsed < 0:
        before = True
        elapsed = -elapsed

    assert years or weeks or days or \
           hours or minutes or seconds, 'One flag must be True'
    if years:
        (yrs, elapsed) = (elapsed // 31536000, elapsed % 31536000)
        Format(_('year'), yrs)
    if weeks:
        (wks, elapsed) = (elapsed // 604800, elapsed % 604800)
        Format(_('week'), wks)
    if days:
        (ds, elapsed) = (elapsed // 86400, elapsed % 86400)
        Format(_('day'), ds)
    if hours:
        (hrs, elapsed) = (elapsed // 3600, elapsed % 3600)
        Format(_('hour'), hrs)
    if minutes or seconds:
        (mins, secs) = (elapsed // 60, elapsed % 60)
        if leadingZeroes or mins:
            Format(_('minute'), mins)
        if seconds:
            leadingZeroes = True
            Format(_('second'), secs)
    if not ret:
        raise ValueError('Time difference not great enough to be noted.')
    result = ''
    if short:
        result = ' '.join(ret)
    else:
        result = format('%L', ret)
    if before:
        result = _('%s ago') % result
    return result

def findBinaryInPath(s):
    """Return full path of a binary if it's in PATH, otherwise return None."""
    cmdLine = None
    for dir in os.getenv('PATH').split(':'):
        filename = os.path.join(dir, s)
        if os.path.exists(filename):
            cmdLine = filename
            break
    return cmdLine

def sortBy(f, L):
    """Uses the decorate-sort-undecorate pattern to sort L by function f."""
    for (i, elt) in enumerate(L):
        L[i] = (f(elt), i, elt)
    L.sort()
    for (i, elt) in enumerate(L):
        L[i] = L[i][2]

def saltHash(password, salt=None, hash='sha'):
    if salt is None:
        salt = mktemp()[:8]
    if hash == 'sha':
        hasher = crypt.sha
    elif hash == 'md5':
        hasher = crypt.md5
    return '|'.join([salt, hasher((salt + password).encode('utf8')).hexdigest()])

_OLD_AST = sys.version_info[0:2] < (3, 8)
"""Whether the AST classes predate the python 3.8 API changes"""

def safeEval(s, namespace=None):
    """Evaluates s, safely.  Useful for turning strings into tuples/lists/etc.
    without unsafely using eval()."""
    try:
        node = ast.parse(s, mode='eval').body
    except SyntaxError as e:
        raise ValueError('Invalid string: %s.' % e)

    def checkNode(node):
        if node.__class__ is ast.Expr:
            node = node.value
        if not _OLD_AST and node.__class__ is ast.Constant:
            return True
        elif node.__class__ in (ast.List,
                              ast.Tuple):
            return all([checkNode(x) for x in node.elts])
        elif node.__class__ is ast.Dict:
            return all([checkNode(x) for x in node.values]) and \
                    all([checkNode(x) for x in node.values])
        elif node.__class__ is ast.Name:
            if namespace is None and node.id in ('True', 'False', 'None'):
                # For Python < 3.4, which does not have NameConstant.
                return True
            elif namespace is not None and node.id in namespace:
                return True
            else:
                return False
        elif _OLD_AST and node.__class__ in (ast.Num, ast.Str, ast.Bytes):
            # ast.Num, ast.Str, ast.Bytes are deprecated since Python 3.8
            # and removed since Python 3.14; replaced by ast.Constant.
            return True
        elif _OLD_AST and node.__class__ is ast.NameConstant:
            # ditto
            return True
        else:
            return False
    if checkNode(node):
        # Probably equivalent to eval() because checkNode(node) is True,
        # but it's an extra security.
        return ast.literal_eval(node)
    else:
        raise ValueError(format('Unsafe string: %q', s))

def exnToString(e):
    """Turns a simple exception instance into a string (better than str(e))"""
    strE = str(e)
    if strE:
        return '%s: %s' % (e.__class__.__name__, strE)
    else:
        return e.__class__.__name__

class IterableMap(object):
    """Define .items() in a class and subclass this to get the other iters.
    """
    __slots__ = ()
    def items(self):
        if minisix.PY3 and hasattr(self, 'iteritems'):
            # For old plugins
            return self.iteritems() # avoid 2to3
        else:
            raise NotImplementedError()
    __iter__ = items

    def keys(self):
        for (key, __) in self.items():
            yield key

    def values(self):
        for (__, value) in self.items():
            yield value


    @warn_non_constant_time
    def __len__(self):
        ret = 0
        for __ in self.items():
            ret += 1
        return ret

    @warn_non_constant_time
    def __bool__(self):
        for __ in self.items():
            return True
        return False
    __nonzero__ = __bool__


class InsensitivePreservingDict(collections.abc.MutableMapping):
    __slots__ = ('data',)
    def key(self, s):
        """Override this if you wish."""
        if s is not None:
            s = s.lower()
        return s

    def __init__(self, dict=None, key=None):
        if key is not None:
            self.key = key
        self.data = {}
        if dict is not None:
            self.update(dict)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.data)

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

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def items(self):
        return self.data.values()

    def items(self):
        return self.data.values()

    def keys(self):
        L = []
        for (k, __) in self.items():
            L.append(k)
        return L

    def __reduce__(self):
        return (self.__class__, (dict(self.data.values()),))


class NormalizingSet(set):
    __slots__ = ()
    def __init__(self, iterable=()):
        iterable = list(map(self.normalize, iterable))
        super(NormalizingSet, self).__init__(iterable)

    def normalize(self, x):
        return x

    def add(self, x):
        return super(NormalizingSet, self).add(self.normalize(x))

    def remove(self, x):
        return super(NormalizingSet, self).remove(self.normalize(x))

    def discard(self, x):
        return super(NormalizingSet, self).discard(self.normalize(x))

    def __contains__(self, x):
        return super(NormalizingSet, self).__contains__(self.normalize(x))
    has_key = __contains__

def stackTrace(frame=None, compact=True):
    if frame is None:
        frame = sys._getframe()
    if compact:
        L = []
        while frame:
            lineno = frame.f_lineno
            funcname = frame.f_code.co_name
            filename = os.path.basename(frame.f_code.co_filename)
            L.append('[%s|%s|%s]' % (filename, funcname, lineno))
            frame = frame.f_back
        return textwrap.fill(' '.join(L))
    else:
        return traceback.format_stack(frame)

def callTracer(fd=None, basename=True):
    if fd is None:
        fd = sys.stdout
    def tracer(frame, event, __):
        if event == 'call':
            code = frame.f_code
            lineno = frame.f_lineno
            funcname = code.co_name
            filename = code.co_filename
            if basename:
                filename = os.path.basename(filename)
            print('%s: %s(%s)' % (filename, funcname, lineno), file=fd)
    return tracer

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
