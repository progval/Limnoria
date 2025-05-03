###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2010-2022, Valentin Lorentz
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
Module for some slight database-independence for simple databases.
"""

import os
import csv
import math

from . import cdb, utils
from .utils import minisix
from .utils.iter import ilen

class Error(Exception):
    """General error for this module."""

class NoRecordError(KeyError):
    pass

class InvalidDBError(Exception):
    pass

class MappingInterface(object):
    """This is a class to represent the underlying representation of a map
    from integer keys to strings."""
    def __init__(self, filename, **kwargs):
        """Feel free to ignore the filename."""
        raise NotImplementedError

    def get(id):
        """Gets the record matching id.  Raises NoRecordError otherwise."""
        raise NotImplementedError

    def set(id, s):
        """Sets the record matching id to s."""
        raise NotImplementedError

    def add(self, s):
        """Adds a new record, returning a new id for it."""
        raise NotImplementedError

    def remove(self, id):
        "Returns and removes the record with the given id from the database."
        raise NotImplementedError

    def __iter__(self):
        "Return an iterator over (id, s) pairs.  Not required to be ordered."
        raise NotImplementedError

    def flush(self):
        """Flushes current state to disk."""
        raise NotImplementedError

    def close(self):
        """Flushes current state to disk and invalidates the Mapping."""
        raise NotImplementedError

    def vacuum(self):
        "Cleans up in the database, if possible.  Not required to do anything."
        pass


class DirMapping(MappingInterface):
    def __init__(self, filename, **kwargs):
        self.dirname = filename
        if not os.path.exists(self.dirname):
            os.mkdir(self.dirname)
        if not os.path.exists(os.path.join(self.dirname, 'max')):
            self._setMax(1)

    def _setMax(self, id):
        fd = open(os.path.join(self.dirname, 'max'), 'w')
        try:
            fd.write(str(id))
        finally:
            fd.close()

    def _getMax(self):
        fd = open(os.path.join(self.dirname, 'max'))
        try:
            i = int(fd.read())
            return i
        finally:
            fd.close()

    def _makeFilename(self, id):
        return os.path.join(self.dirname, str(id))

    def get(self, id):
        try:
            fd = open(self._makeFilename(id))
            return fd.read()
        except EnvironmentError as e:
            exn = NoRecordError(id)
            exn.realException = e
            raise exn
        finally:
            fd.close()

    def set(self, id, s):
        fd = open(self._makeFilename(id), 'w')
        fd.write(s)
        fd.close()

    def add(self, s):
        id = self._getMax()
        fd = open(self._makeFilename(id), 'w')
        try:
            fd.write(s)
            return id
        finally:
            fd.close()

    def remove(self, id):
        try:
            os.remove(self._makeFilename(id))
        except EnvironmentError:
            raise NoRecordError(id)

class FlatfileMapping(MappingInterface):
    def __init__(self, filename, maxSize=10**6):
        self.filename = filename
        try:
            fd = open(self.filename, encoding='utf8')
            strId = fd.readline().rstrip()
            self.maxSize = len(strId)
            try:
                self.currentId = int(strId)
            except ValueError:
                raise Error('Invalid file for FlatfileMapping: %s' % filename)
        except EnvironmentError as e:
            # File couldn't be opened.
            self.maxSize = int(math.log10(maxSize))
            self.currentId = 0
            self._incrementCurrentId()
        finally:
            if 'fd' in locals():
                fd.close()

    def _canonicalId(self, id):
        if id is not None:
            return str(id).zfill(self.maxSize)
        else:
            return '-'*self.maxSize
    
    def _incrementCurrentId(self, fd=None):
        fdWasNone = fd is None
        if fdWasNone:
            fd = open(self.filename, 'a', encoding='utf8')
        fd.seek(0)
        self.currentId += 1
        fd.write(self._canonicalId(self.currentId))
        fd.write('\n')
        if fdWasNone:
            fd.close()
        
    def _splitLine(self, line):
        line = line.rstrip('\r\n')
        (id, s) = line.split(':', 1)
        return (id, s)

    def _joinLine(self, id, s):
        return '%s:%s\n' % (self._canonicalId(id), s)

    def add(self, s):
        line = self._joinLine(self.currentId, s)
        fd = open(self.filename, 'r+', encoding='utf8')
        try:
            fd.seek(0, 2) # End.
            fd.write(line)
            return self.currentId
        finally:
            self._incrementCurrentId(fd)
            fd.close()

    def get(self, id):
        strId = self._canonicalId(id)
        try:
            fd = open(self.filename, encoding='utf8')
            fd.readline() # First line, nextId.
            for line in fd:
                (lineId, s) = self._splitLine(line)
                if lineId == strId:
                    return s
            raise NoRecordError(id)
        finally:
            fd.close()

    # XXX This assumes it's not been given out.  We should make sure that our
    #     maximum id remains accurate if this is some value we've never given
    #     out -- i.e., self.maxid = max(self.maxid, id) or something.
    def set(self, id, s):
        strLine = self._joinLine(id, s)
        try:
            fd = open(self.filename, 'r+', encoding='utf8')
            self.remove(id, fd)
            fd.seek(0, 2) # End.
            fd.write(strLine)
        finally:
            fd.close()

    def remove(self, id, fd=None):
        fdWasNone = fd is None
        strId = self._canonicalId(id)
        try:
            if fdWasNone:
                fd = open(self.filename, 'r+', encoding='utf8')
            fd.seek(0)
            fd.readline() # First line, nextId
            pos = fd.tell()
            line = fd.readline()
            while line:
                (lineId, _) = self._splitLine(line)
                if lineId == strId:
                    fd.seek(pos)
                    fd.write(self._canonicalId(None))
                    fd.seek(pos)
                    fd.readline() # Same line we just rewrote the id for.
                pos = fd.tell()
                line = fd.readline()
            # We should be at the end.
        finally:
            if fdWasNone:
                fd.close()

    def __iter__(self):
        fd = open(self.filename, encoding='utf8')
        fd.readline() # First line, nextId.
        for line in fd:
            (id, s) = self._splitLine(line)
            if not id.startswith('-'):
                yield (int(id), s)
        fd.close()

    def vacuum(self):
        infd = open(self.filename, encoding='utf8')
        outfd = utils.file.AtomicFile(self.filename,makeBackupIfSmaller=False)
        outfd.write(infd.readline()) # First line, nextId.
        for line in infd:
            if not line.startswith('-'):
                outfd.write(line)
        infd.close()
        outfd.close()

    def flush(self):
        pass # No-op, we maintain no open files.

    def close(self):
        self.vacuum() # Should we do this?  It should be fine.
        

class CdbMapping(MappingInterface):
    def __init__(self, filename, **kwargs):
        self.filename = filename
        self._openCdb() # So it can be overridden later.
        if 'nextId' not in self.db:
            self.db['nextId'] = '1'

    def _openCdb(self, *args, **kwargs):
        self.db = cdb.open_db(self.filename, 'c', **kwargs)

    def _getNextId(self):
        i = int(self.db['nextId'])
        self.db['nextId'] = str(i+1)
        return i

    def get(self, id):
        try:
            return self.db[str(id)]
        except KeyError:
            raise NoRecordError(id)

    # XXX Same as above.
    def set(self, id, s):
        self.db[str(id)] = s

    def add(self, s):
        id = self._getNextId()
        self.set(id, s)
        return id

    def remove(self, id):
        del self.db[str(id)]

    def __iter__(self):
        for (id, s) in self.db.items():
            if id != 'nextId':
                yield (int(id), s)

    def flush(self):
        self.db.flush()

    def close(self):
        self.db.close()


class DB(object):
    Mapping = 'flat' # This is a good, sane default.
    Record = None
    def __init__(self, filename, Mapping=None, Record=None):
        if Record is not None:
            self.Record = Record
        if Mapping is not None:
            self.Mapping = Mapping
        if isinstance(self.Mapping, minisix.string_types):
            self.Mapping = Mappings[self.Mapping]
        self.map = self.Mapping(filename)

    def _newRecord(self, id, s):
        record = self.Record(id=id)
        record.deserialize(s)
        return record 

    def get(self, id):
        s = self.map.get(id)
        return self._newRecord(id, s)

    def set(self, id, record):
        s = record.serialize()
        self.map.set(id, s)

    def add(self, record):
        s = record.serialize()
        id = self.map.add(s)
        record.id = id
        return id

    def remove(self, id):
        self.map.remove(id)

    def __iter__(self):
        yield from self._iter()

    def _iter(self, *, reverse=False):
        if reverse:
            if hasattr(self.map, "__reversed__"):
                # neither FlatfileMapping nor CdbMapping support __reversed__
                # and DirMapping does not support iteration at all, but
                # there is no harm in allowing this short-path in case
                # plugins use their own mapping.
                it = reversed(self.map)
            else:
                # This does load the whole database in memory instead of
                # iterating lazily, but plugins requesting a reverse list
                # would probably need do it themselves otherwise, so it does
                # not make matters worse to do it here.
                it = reversed(list(self.map))
        else:
            it = self.map
        for (id, s) in it:
            # We don't need to yield the id because it's in the record.
            yield self._newRecord(id, s)

    def select(self, p, reverse=False):
        for record in self._iter(reverse=reverse):
            if p(record):
                yield record

    def random(self):
        try:
            return self._newRecord(*utils.iter.choice(self.map))
        except IndexError:
            return None

    def size(self):
        return ilen(self.map)

    def flush(self):
        self.map.flush()

    def vacuum(self):
        self.map.vacuum()

    def close(self):
        self.map.close()

Mappings = {
    'cdb': CdbMapping,
    'flat': FlatfileMapping,
    }


class Record(object):
    def __init__(self, id=None, **kwargs):
        if id is not None:
            assert isinstance(id, int), 'id must be an integer.'
        self.id = id
        self.fields = []
        self.defaults = {}
        self.converters = {}
        for name in self.__fields__:
            if isinstance(name, tuple):
                (name, spec) = name
            else:
                spec = utils.safeEval
            assert name != 'id'
            self.fields.append(name)
            if isinstance(spec, tuple):
                (converter, default) = spec
            else:
                converter = spec
                default = None
            self.defaults[name] = default
            self.converters[name] = converter
        seen = set()
        for (name, value) in kwargs.items():
            assert name in self.fields, 'name must be a record value.'
            seen.add(name)
            setattr(self, name, value)
        for name in self.fields:
            if name not in seen:
                default = self.defaults[name]
                if callable(default):
                    default = default()
                setattr(self, name, default)

    def serialize(self):
        return csv.join([repr(getattr(self, name)) for name in self.fields])

    def deserialize(self, s):
        unseenRecords = set(self.fields)
        for (name, strValue) in zip(self.fields, csv.split(s)):
            setattr(self, name, self.converters[name](strValue))
            unseenRecords.remove(name)
        for name in unseenRecords:
            setattr(self, name, self.defaults[name])

    
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
