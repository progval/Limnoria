###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008, James McCoy
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
import sys
import new
import time
import types
import compiler
import textwrap
import UserDict
import traceback

from . import crypt
from .str import format
from .file import mktemp
from .iter import imap, all

def abbrev(strings, d=None):
    """Returns a dictionary mapping unambiguous abbreviations to full forms."""
    def eachSubstring(s):
        for i in xrange(1, len(s)+1):
            yield s[:i]
    if len(strings) != len(set(strings)):
        raise ValueError, \
              'strings given to utils.abbrev have duplicates: %r' % strings
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
        Format('year', yrs)
    if weeks:
        (wks, elapsed) = (elapsed // 604800, elapsed % 604800)
        Format('week', wks)
    if days:
        (ds, elapsed) = (elapsed // 86400, elapsed % 86400)
        Format('day', ds)
    if hours:
        (hrs, elapsed) = (elapsed // 3600, elapsed % 3600)
        Format('hour', hrs)
    if minutes or seconds:
        (mins, secs) = (elapsed // 60, elapsed % 60)
        if leadingZeroes or mins:
            Format('minute', mins)
        if seconds:
            leadingZeroes = True
            Format('second', secs)
    if not ret:
        raise ValueError, 'Time difference not great enough to be noted.'
    result = ''
    if short:
        result = ' '.join(ret)
    else:
        result = format('%L', ret)
    if before:
        result += ' ago'
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
    return '|'.join([salt, hasher(salt + password).hexdigest()])

def safeEval(s, namespace={'True': True, 'False': False, 'None': None}):
    """Evaluates s, safely.  Useful for turning strings into tuples/lists/etc.
    without unsafely using eval()."""
    try:
        node = compiler.parse(s)
    except SyntaxError, e:
        raise ValueError, 'Invalid string: %s.' % e
    nodes = compiler.parse(s).node.nodes
    if not nodes:
        if node.__class__ is compiler.ast.Module:
            return node.doc
        else:
            raise ValueError, format('Unsafe string: %q', s)
    node = nodes[0]
    if node.__class__ is not compiler.ast.Discard:
        raise ValueError, format('Invalid expression: %q', s)
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
        raise ValueError, format('Unsafe string: %q', s)

def exnToString(e):
    """Turns a simple exception instance into a string (better than str(e))"""
    strE = str(e)
    if strE:
        return '%s: %s' % (e.__class__.__name__, strE)
    else:
        return e.__class__.__name__

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


class InsensitivePreservingDict(UserDict.DictMixin, object):
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
        return '%s(%s)' % (self.__class__.__name__,
                           super(InsensitivePreservingDict, self).__repr__())

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


class NormalizingSet(set):
    def __init__(self, iterable=()):
        iterable = imap(self.normalize, iterable)
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
    def tracer(frame, event, _):
        if event == 'call':
            code = frame.f_code
            lineno = frame.f_lineno
            funcname = code.co_name
            filename = code.co_filename
            if basename:
                filename = os.path.basename(filename)
            print >>fd, '%s: %s(%s)' % (filename, funcname, lineno)
    return tracer

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
