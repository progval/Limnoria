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

import sys

###
# csv.{join,split} -- useful functions that should exist.
###
import csv
import cStringIO as StringIO
def join(L):
    fd = StringIO.StringIO()
    writer = csv.writer(fd)
    writer.writerow(L)
    return fd.getvalue().rstrip('\r\n')

def split(s):
    fd = StringIO.StringIO(s)
    reader = csv.reader(fd)
    return reader.next()
csv.join = join
csv.split = split

# We use this often enough that we're going to stick it in builtins.
def force(x):
    if callable(x):
        return x()
    else:
        return x
__builtins__['force'] = force

if sys.version_info < (2, 4, 0):
    def reversed(L):
        """Iterates through a sequence in reverse."""
        for i in xrange(len(L) - 1, -1, -1):
            yield L[i]
    __builtins__['reversed'] = reversed

    def sorted(iterable, cmp=None, key=None, reversed=False):
        L = list(iterable)
        if key is not None:
            assert cmp is None, 'Can\'t use both cmp and key.'
            sortBy(key, L)
        else:
            L.sort(cmp)
        if reversed:
            L.reverse()
        return L

    __builtins__['sorted'] = sorted

    import operator
    def itemgetter(i):
        return lambda x: x[i]

    def attrgetter(attr):
        return lambda x: getattr(x, attr)
    operator.itemgetter = itemgetter
    operator.attrgetter = attrgetter

    import sets
    __builtins__['set'] = sets.Set
    __builtins__['frozenset'] = sets.ImmutableSet

    import socket
    # Some socket modules don't have sslerror, so we'll just make it an error.
    if not hasattr(socket, 'sslerror'):
        socket.sslerror = socket.error

# These imports need to happen below the block above, so things get put into
# __builtins__ appropriately.
from .gen import *
from . import crypt, error, file, iter, net, python, seq, str, transaction, web

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
