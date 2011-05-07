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

# The data in this module comes from:
# * https://github.com/espes/esbot/blob/master/packets.py
# * http://wiki.vg/Protocol
# Thanks for their great work.

import supybot.conf as conf
from supybot.minecraftprotocol import MinecraftPacket as Packet
import supybot.minecraftformat as mcformat

class KeepAlive(Packet):
    id = 0x00
    _format = []

class Login(Packet):
    id = 0x01
    _format = [
            ('protocolVersion', 'i', 11),
            ('username', 'S', conf.supybot.nick()),
            ('mapSeed', 'q', 0),
            ('dimension', 'b', 0),
            ]

class Handshake(Packet):
    id = 0x02
    _format = [
            ('username', 'S', conf.supybot.nick()),
            ]

class Chat(Packet):
    id = 0x03
    _format = [
            ('message', 'S', ''),
            ]


class Disconnect(Packet):
    id = 0xFF
    _format = [
            ('reason', 'S', 'kicked'),
            ]
