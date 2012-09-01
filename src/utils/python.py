###
# Copyright (c) 2005-2009, Jeremiah Fincher
# Copyright (c) 2009-2010, James McCoy
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

import sys
import types
import fnmatch
import UserDict
import threading

def universalImport(*names):
    """Attempt to import the given modules, in order, returning the first
    successfully imported module.  ImportError will be raised, as usual, if
    no imports succeed.  To emulate ``from ModuleA import ModuleB'', pass the
    string 'ModuleA.ModuleB'"""
    f = sys._getframe(1)
    for name in names:
        try:
            # __import__ didn't gain keyword arguments until 2.5
            ret = __import__(name, f.f_globals)
        except ImportError:
            continue
        else:
            if '.' in name:
                parts = name.split('.')[1:]
                while parts:
                    ret = getattr(ret, parts[0])
                    del parts[0]
            return ret
    raise ImportError, ','.join(names)

def changeFunctionName(f, name, doc=None):
    if doc is None:
        doc = f.__doc__
    newf = types.FunctionType(f.func_code, f.func_globals, name,
                              f.func_defaults, f.func_closure)
    newf.__doc__ = doc
    return newf

class Object(object):
    def __ne__(self, other):
        return not self == other

class Synchronized(type):
    METHODS = '__synchronized__'
    LOCK = '_Synchronized_rlock'
    def __new__(cls, name, bases, dict):
        sync = set()
        for base in bases:
            if hasattr(base, Synchronized.METHODS):
                sync.update(getattr(base, Synchronized.METHODS))
        if Synchronized.METHODS in dict:
            sync.update(dict[Synchronized.METHODS])
        if sync:
            def synchronized(f):
                def g(self, *args, **kwargs):
                    lock = getattr(self, Synchronized.LOCK)
                    lock.acquire()
                    try:
                        f(self, *args, **kwargs)
                    finally:
                        lock.release()
                return changeFunctionName(g, f.func_name, f.__doc__)
            for attr in sync:
                if attr in dict:
                    dict[attr] = synchronized(dict[attr])
            original__init__ = dict.get('__init__')
            def __init__(self, *args, **kwargs):
                if not hasattr(self, Synchronized.LOCK):
                    setattr(self, Synchronized.LOCK, threading.RLock())
                if original__init__:
                    original__init__(self, *args, **kwargs)
                else:
                    # newclass is defined below.
                    super(newclass, self).__init__(*args, **kwargs)
            dict['__init__'] = __init__
        newclass = super(Synchronized, cls).__new__(cls, name, bases, dict)
        return newclass

# Translate glob to regular expression, trimming the "match EOL" portion of
# the regular expression.
if sys.version_info < (2, 6, 0):
    # Pre-2.6 just uses the $ anchor
    def glob2re(g):
        return fnmatch.translate(g)[:-1]
else:
    # Post-2.6 uses \Z(?ms) per http://issues.python.org/6665
    def glob2re(g):
        return fnmatch.translate(g)[:-7]

# vim:set shiftwidth=4 softtabstop=8 expandtab textwidth=78:
