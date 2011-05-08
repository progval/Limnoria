###
# Copyright (c) 2011, espes
# Copyright (c) 2011, Valentin Lorentz
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

import struct
import zlib
from StringIO import StringIO


class IncompleteDataError(Exception):
    pass

class DataBuffer(StringIO):
    def lenLeft(self):
        return len(self.getvalue())-self.tell()

    def read(self, size=None):
        if size is None:
            return StringIO.read(self)

        if self.lenLeft() < size:
            raise IncompleteDataError
        return StringIO.read(self, size)

    def peek(self, size=None):
        if size is None:
            return self.getvalue()[self.tell():]

        if self.lenLeft() < size:
            raise IncompleteDataError
        return self.getvalue()[self.tell():self.tell()+size]

def readStruct(formatString, dataBuffer):
    length = struct.calcsize(formatString)
    try:
        return struct.unpack(formatString, dataBuffer.read(length))
    except struct.error:
        raise IncompleteDataError

class Format(object):
    def __init__(self, format):
        self.format = format
    def decode(self, dataBuffer):
        for char in self.format:
            if char == "S": # minecraft string
                length, = readStruct("!h", dataBuffer)
                yield unicode(dataBuffer.read(length*2), "utf_16_be")
            elif char == "8": # minecraft string8
                length, = readStruct("!h", dataBuffer)
                yield dataBuffer.read(length)
            elif char == "M": # hack
                yield tuple(EntityMetadataFormat().decode(dataBuffer))
            else:
                res, = readStruct("!"+char, dataBuffer)
                yield res

    def encode(self, *args):
        assert len(self.format) == len(args)
        data = ""
        for char, arg in zip(self.format, args):
            if char == "S": # minecraft string
                data += struct.pack("!h", len(arg))
                data += arg.encode("utf_16_be")
            elif char == "8":
                data += struct.pack("!h", len(arg))
                data += arg.encode("utf_8")
            elif char in ("b", "B") and isinstance(arg, str) and len(arg) == 1:                 # Byte as string
                data += arg
            elif char == "M": # hack
                # TODO : implement this
                pass
            else:
                data += struct.pack("!"+char, arg)

        return data

class MultiBlockChangeFormat(Format):
    def __init__(self):
        pass

    def decode(self, dataBuffer):
        x, z, size = readStruct("!iih", dataBuffer)
        yield x, z

        coords = readStruct("!%dh" % size, dataBuffer)
        types = readStruct("!%db" % size, dataBuffer)
        metadatas = readStruct("!%db" % size, dataBuffer)

        for coord, type, metadata in zip(coords, types, metadatas):
            bx = coord >> (8+4)
            bz = (coord >> 8) & 0b1111
            by = coord & 0xFF

            yield ((bx, by, bz), type, metadata)


class WindowItemsFormat(Format):
    def __init__(self):
        pass
    def decode(self, dataBuffer):
        type, count = readStruct("!bh", dataBuffer)

        yield type
        #yield count

        items = {}
        for i in xrange(count):
            itemId, = readStruct("!h", dataBuffer)
            if itemId == -1: continue

            count, health = readStruct("!bh", dataBuffer)
            items[i] = (itemId, count, health)
        yield items


class SetSlotFormat(Format):
    def __init__(self):
        pass

    def decode(self, dataBuffer):
        type, slot, itemId = readStruct("!bhh", dataBuffer)

        yield type
        yield slot

        if itemId >= 0:
            count, health = readStruct("!bh", dataBuffer)
            yield (itemId, count, health)
        else:
            yield None

class WindowClickFormat(Format):
    def __init__(self):
        pass

    def encode(
              self,
              windowId,
              slot,
              rightClick,
              actionNumber,
              shiftClick,
              item
              ):
        if item is None:
            return struct.pack("!bhbhbh",
                              windowId,
                              slot,
                              rightClick,
                              actionNumber,
                              shiftClick,
                              -1
                              )
        else:
            itemId, count, uses = item
            return struct.pack("!bhbhbhbh",
                              windowId,
                              slot,
                              rightClick,
                              actionNumber,
                              shiftClick,
                              itemId,
                              count,
                              uses
                              )

class ExplosionFormat(Format):
    def __init__(self):
        pass

    def decode(self, dataBuffer):
        x, y, z, unk1, count = readStruct("!dddfi", dataBuffer)
        for i in xrange(count):
            dx, dy, dz = readStruct("!bbb", dataBuffer)

class BlockPlaceFormat(Format):
    def __init__(self):
        pass
    def encode(self, x, y, z, direction, item):
        if item is None:
            return struct.pack("!ibibh", x, y, z, direction, -1)
        else:
            itemId, count, uses = item
            return struct.pack("!ibibhbh", x, y, z, direction, itemId, count, uses)
    def decode(self, dataBuffer):
        x, y, z, face, itemId = readStruct("!ibibh", dataBuffer)
        if itemId >= 0:
            count, health = readStruct("!bb", dataBuffer)

class ChunkFormat(Format):
    def __init__(self):
        pass

    def decode(self, dataBuffer):
        x, y, z, sx, sy, sz, chunkSize = readStruct("!ihibbbi", dataBuffer)

        sx += 1
        sy += 1
        sz += 1

        yield (x, y, z)
        yield (sx, sy, sz)

        yield zlib.decompress(dataBuffer.read(chunkSize))

        #chunkData = zlib.decompress(data[:chunkSize])
        #yield chunkData[:sx*sy*sz] #block types
        #i = sx*sy*sz
        #metaData = []
        #for j in range(sx*sy*sz):
        #    metaData.append(chunkData[i+j/2] >> (4*(i%2)))


class EntityMetadataFormat(Format):
    def __init__(self):
        self.formatMap = {
            0: Format('b'),
            1: Format('h'),
            2: Format('i'),
            3: Format('f'),
            4: Format('S'),
            5: Format('hbh')
        }
    def decode(self, dataBuffer):
        while True:
            x, = readStruct("!b", dataBuffer)
            if x == 127: break
            yield tuple(self.formatMap[(x & 0xE0) >> 5].decode(dataBuffer))

    def encode(self, args):
        # TODO: implement this
        return '\x7F'

