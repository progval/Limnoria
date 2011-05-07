###
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

from cStringIO import StringIO

from supybot.minecraftformat import Format, DataBuffer

idToPacket = {}

def ircToMinecraft(ircMsg):
    # TODO: really implement this
    import supybot.minecraftmsgs as minecraftmsgs
    if ircMsg.command == 'PING':
        return minecraftmsgs.KeepAlive()
    elif ircMsg.command == 'USER':
        return minecraftmsgs.Login()
    elif ircMsg.command == 'NICK':
        return minecraftmsgs.Handshake()
    else:
        return minecraftmsgs.Chat(message='MSG: %r' % ircMsg)

class rawToMsgsTranslator:
    def __init__(self, raw):
        raw = StringIO(raw)
        while row.lenLeft() > 0:
            type = ord(raw.read(1))
        receivedAt = time.time()
        msg.tag('receivedAt', receivedAt)



class MinecraftPacketMetaclass(type):
    def __new__(meta, classname, bases, classDict):
        cls = type.__new__(meta, classname, bases, classDict)
        if classDict['__module__'] != __name__:
            # Only register real packets
            idToPacket.update({cls.id: cls})
        return cls

class MinecraftPacket(Format):
    # Most of the packets uses the same base Format. If a packet need a
    # specific format, it will subclass MinecraftPacket and the custom
    # Format class.
    __metaclass__ = MinecraftPacketMetaclass

    def __init__(self, *args, **kwargs):
        # Convert our named format to the one used by encode and decode
        # (they come from esbot)
        self.format = ''.join([x[1] for x in self._format])

        # Be careful, order matters. We may have a packet from the
        # bot without any arguments.
        if args == ():
            # From the bot
            self._createFromArguments(**kwargs)
        elif kwargs == {}:
            # From network
            assert len(args) == 1
            assert isinstance(args[0], DataBuffer)
            self._createFromRaw(args[0])
        else:
            raise

    def _createFromArguments(self, **kwargs):
        names = []
        for name, type, defaultValue in self._format:
            names.append(name)
            if defaultValue is None:
                if name not in kwargs.keys():
                    raise ArgumentError('%r not given but required.' % name)
            else:
                self.__dict__.update({name: defaultValue})
        for name, value in kwargs.iteritems():
            if name not in names:
                raise ArgumentError('%r is not a valid argument' % name)
            else:
                self.__dict__.update({name: value})

    def _createFromRaw(self, raw):
        parts = list(self.decode(raw))
        for name, type, defaultValue, part in [(x[0], x[1], x[2], y) \
                for x,y in zip(self._format, parts)]:
            # self.decode is a generator.
            self.__dict__.update({name: part})

    def __str__(self):
        args = []
        for name, type, defaultValue in self._format:
            args.append(self.__dict__[name])
        return chr(self.id) + self.encode(*args)

    def __repr__(self):
        return '<%s(%s)>' % (repr(self.__class__)[8:-2],
                ', '.join(['%s=%r' % (x,z) for x,y,z in self._format]))


