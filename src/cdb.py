###
# Copyright (c) 2002-2005, Jeremiah Fincher
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
Database module, similar to dbhash.  Uses a format similar to (if not entirely
the same as) DJB's CDB <http://cr.yp.to/cdb.html>.
"""

from __future__ import division

import os
import sys
import struct
import os.path

from . import utils
from .utils import minisix

def hash(s):
    """DJB's hash function for CDB."""
    h = 5381
    for c in s:
        h = ((h + (h << 5)) ^ ord(c)) & minisix.L(0xFFFFFFFF)
    return h

def unpack2Ints(s):
    """Returns two ints unpacked from the binary string s."""
    return struct.unpack('<LL', s)

def pack2Ints(i, j):
    """Returns a packed binary string from the two ints."""
    return struct.pack('<LL', i, j)

def dump(map, fd=sys.stdout):
    """Dumps a dictionary-structure in CDB format."""
    for (key, value) in map.items():
        fd.write('+%s,%s:%s->%s\n' % (len(key), len(value), key, value))

def open_db(filename, mode='r', **kwargs):
    """Opens a database; used for compatibility with other database modules."""
    if mode == 'r':
        return Reader(filename, **kwargs)
    elif mode == 'w':
        return ReaderWriter(filename, **kwargs)
    elif mode == 'c':
        if os.path.exists(filename):
            return ReaderWriter(filename, **kwargs)
        else:
            maker = Maker(filename)
            maker.finish()
            return ReaderWriter(filename, **kwargs)
    elif mode == 'n':
        maker = Maker(filename)
        maker.finish()
        return ReaderWriter(filename, **kwargs)
    else:
        raise ValueError('Invalid flag: %s' % mode)

def shelf(filename, *args, **kwargs):
    """Opens a new shelf database object."""
    if os.path.exists(filename):
        return Shelf(filename, *args, **kwargs)
    else:
        maker = Maker(filename)
        maker.finish()
        return Shelf(filename, *args, **kwargs)

def _readKeyValue(fd):
    klen = 0
    dlen = 0
    s = initchar = fd.read(1)
    if s == '':
        return (None, None, None)
    s = fd.read(1)
    while s != ',':
        klen = 10 * klen + int(s)
        s = fd.read(1)
    s = fd.read(1)
    while s != ':':
        dlen = 10 * dlen + int(s)
        s = fd.read(1)
    key = fd.read(klen)
    assert fd.read(2) == '->'
    value = fd.read(dlen)
    assert fd.read(1) == '\n'
    return (initchar, key, value)

def make(dbFilename, readFilename=None):
    """Makes a database from the filename, otherwise uses stdin."""
    if readFilename is None:
        readfd = sys.stdin
    else:
        readfd = open(readFilename, 'rb')
    maker = Maker(dbFilename)
    while True:
        (initchar, key, value) = _readKeyValue(readfd)
        if initchar is None:
            break
        assert initchar == '+'
        maker.add(key, value)
    readfd.close()
    maker.finish()


class Maker(object):
    """Class for making CDB databases."""
    def __init__(self, filename):
        self.fd = utils.file.AtomicFile(filename, 'wb')
        self.filename = filename
        self.fd.seek(2048)
        self.hashPointers = [(0, 0)] * 256
        #self.hashes = [[]] * 256 # Can't use this, [] stays the same...
        self.hashes = []
        for _ in range(256):
            self.hashes.append([])

    def add(self, key, data):
        """Adds a key->value pair to the database."""
        h = hash(key)
        hashPointer = h % 256
        startPosition = self.fd.tell()
        self.fd.write(pack2Ints(len(key), len(data)))
        self.fd.write(key.encode())
        self.fd.write(data.encode())
        self.hashes[hashPointer].append((h, startPosition))

    def finish(self):
        """Finishes the current Maker object.

        Writes the remainder of the database to disk.
        """
        for i in range(256):
            hash = self.hashes[i]
            self.hashPointers[i] = (self.fd.tell(), self._serializeHash(hash))
        self._serializeHashPointers()
        self.fd.flush()
        self.fd.close()

    def _serializeHash(self, hash):
        hashLen = len(hash) * 2
        a = [(0, 0)] * hashLen
        for (h, pos) in hash:
            i = (h // 256) % hashLen
            while a[i] != (0, 0):
                i = (i + 1) % hashLen
            a[i] = (h, pos)
        for (h, pos) in a:
            self.fd.write(pack2Ints(h, pos))
        return hashLen

    def _serializeHashPointers(self):
        self.fd.seek(0)
        for (hashPos, hashLen) in self.hashPointers:
            self.fd.write(pack2Ints(hashPos, hashLen))


class Reader(utils.IterableMap):
    """Class for reading from a CDB database."""
    def __init__(self, filename):
        self.filename = filename
        self.fd = open(filename, 'rb')
        self.loop = 0
        self.khash = 0
        self.kpos = 0
        self.hpos = 0
        self.hslots = 0
        self.dpos = 0
        self.dlen = 0

    def close(self):
        self.fd.close()

    def _read(self, len, pos):
        self.fd.seek(pos)
        return self.fd.read(len)

    def _match(self, key, pos):
        return self._read(len(key), pos) == key

    def items(self):
        # uses loop/hslots in a strange, non-re-entrant manner.
        (self.loop,) = struct.unpack('<i', self._read(4, 0))
        self.hslots = 2048
        while self.hslots < self.loop:
            (klen, dlen) = unpack2Ints(self._read(8, self.hslots))
            dpos = self.hslots + 8 + klen
            ret = (self._read(klen, self.hslots+8).decode(),
                    self._read(dlen, dpos).decode())
            self.hslots = dpos + dlen
            yield ret
        self.loop = 0
        self.hslots = 0

    def _findnext(self, key):
        if not self.loop:
            self.khash = hash(key)
            (self.hpos, self.hslots) = unpack2Ints(self._read(8,
                                                    (self.khash * 8) & 2047))
            if not self.hslots:
                return False
            self.kpos = self.hpos + (((self.khash // 256) % self.hslots) * 8)
        while self.loop < self.hslots:
            (h, p) = unpack2Ints(self._read(8, self.kpos))
            if p == 0:
                return False
            self.loop += 1
            self.kpos += 8
            if self.kpos == self.hpos + (self.hslots * 8):
                self.kpos = self.hpos
            if h == self.khash:
                (u, self.dlen) = unpack2Ints(self._read(8, p))
                if u == len(key):
                    if self._match(key, p+8):
                        self.dpos = p + 8 + u
                        return True
        return False

    def _find(self, key, loop=0):
        self.loop = loop
        return self._findnext(key)

    def _getCurrentData(self):
        return self._read(self.dlen, self.dpos).decode()

    def find(self, key, loop=0):
        if self._find(key, loop=loop):
            return self._getCurrentData()
        else:
            try:
                return self.default
            except AttributeError:
                raise KeyError(key)

    def findall(self, key):
        ret = []
        while self._findnext(key):
            ret.append(self._getCurrentData())
        return ret

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self):
        (start,) = struct.unpack('<i', self._read(4, 0))
        self.fd.seek(0, 2)
        return ((self.fd.tell() - start) // 16)

    has_key = _find
    __contains__ = has_key
    __getitem__ = find


class ReaderWriter(utils.IterableMap):
    """Uses a journal to pretend that a CDB is writable database."""
    def __init__(self, filename, journalName=None, maxmods=0):
        if journalName is None:
            journalName = filename + '.journal'
        self.journalName = journalName
        self.maxmods = maxmods
        self.mods = 0
        self.filename = filename
        self._readJournal()
        self._openFiles()
        self.adds = {}
        self.removals = set()

    def _openFiles(self):
        self.cdb = Reader(self.filename)
        self.journal = open(self.journalName, 'w')

    def _closeFiles(self):
        self.cdb.close()
        self.journal.close()

    def _journalRemoveKey(self, key):
        s = '-%s,%s:%s->%s\n' % (len(key), 0, key, '')
        self.journal.write(s)
        self.journal.flush()

    def _journalAddKey(self, key, value):
        s = '+%s,%s:%s->%s\n' % (len(key), len(value), key, value)
        self.journal.write(s)
        self.journal.flush()

    def _readJournal(self):
        removals = set()
        adds = {}
        try:
            fd = open(self.journalName, 'r')
            while True:
                (initchar, key, value) = _readKeyValue(fd)
                if initchar is None:
                    break
                elif initchar == '+':
                    if key in removals:
                        removals.remove(key)
                    adds[key] = value
                elif initchar == '-':
                    if key in adds:
                        del adds[key]
                    removals.add(key)
            fd.close()
        except IOError:
            pass
        if removals or adds:
            maker = Maker(self.filename)
            cdb = Reader(self.filename)
            for (key, value) in cdb.items():
                if key in removals:
                    continue
                elif key in adds:
                    value = adds[key]
                    if value is not None:
                        maker.add(key, value)
                        adds[key] = None
                else:
                    maker.add(key, value)
            for (key, value) in adds.items():
                if value is not None:
                    maker.add(key, value)
            cdb.close()
            maker.finish()
        if os.path.exists(self.journalName):
            os.remove(self.journalName)

    def close(self):
        self.flush()
        self._closeFiles()

    def flush(self):
        self._closeFiles()
        self._readJournal()
        self._openFiles()

    def _flushIfOverLimit(self):
        if self.maxmods:
            if isinstance(self.maxmods, int):
                if self.mods > self.maxmods:
                    self.flush()
                    self.mods = 0
            elif isinstance(self.maxmods, float):
                assert 0 <= self.maxmods
                if self.mods / max(len(self.cdb), 100) > self.maxmods:
                    self.flush()
                    self.mods = 0

    def __getitem__(self, key):
        if key in self.removals:
            raise KeyError(key)
        else:
            try:
                return self.adds[key]
            except KeyError:
                return self.cdb[key] # If this raises KeyError, we lack key.

    def __delitem__(self, key):
        if key in self.removals:
            raise KeyError(key)
        else:
            if key in self.adds and key in self.cdb:
                self._journalRemoveKey(key)
                del self.adds[key]
                self.removals.add(key)
            elif key in self.adds:
                self._journalRemoveKey(key)
                del self.adds[key]
            elif key in self.cdb:
                self._journalRemoveKey(key)
            else:
                raise KeyError(key)
        self.mods += 1
        self._flushIfOverLimit()

    def __setitem__(self, key, value):
        if key in self.removals:
            self.removals.remove(key)
        self._journalAddKey(key, value)
        self.adds[key] = value
        self.mods += 1
        self._flushIfOverLimit()

    def __contains__(self, key):
        if key in self.removals:
            return False
        else:
            return key in self.adds or key in self.cdb

    has_key = __contains__

    def items(self):
        already = set()
        for (key, value) in self.cdb.items():
            if key in self.removals or key in already:
                continue
            elif key in self.adds:
                already.add(key)
                yield (key, self.adds[key])
            else:
                yield (key, value)
        for (key, value) in self.adds.items():
            if key not in already:
                yield (key, value)

    def setdefault(self, key, value):
        try:
            return self[key]
        except KeyError:
            self[key] = value
            return value

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class Shelf(ReaderWriter):
    """Uses pickle to mimic the shelf module."""
    def __getitem__(self, key):
        return minisix.pickle.loads(ReaderWriter.__getitem__(self, key))

    def __setitem__(self, key, value):
        ReaderWriter.__setitem__(self, key, minisix.pickle.dumps(value, True))

    def items(self):
        for (key, value) in ReaderWriter.items(self):
            yield (key, minisix.pickle.loads(value))


if __name__ == '__main__':
    if sys.argv[0] == 'cdbdump':
        if len(sys.argv) == 2:
            fd = open(sys.argv[1], 'rb')
        else:
            fd = sys.stdin
        db = Reader(fd)
        dump(db)
    elif sys.argv[0] == 'cdbmake':
        if len(sys.argv) == 2:
            make(sys.argv[1])
        else:
            make(sys.argv[1], sys.argv[2])
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
