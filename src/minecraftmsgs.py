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

class UpdateTime(Packet):
    id = 0x04
    _format = [
            ('time', 'q', 0),
            ]

class EntityEquipment(Packet):
    id = 0x05
    _format = [
            ('entityId', 'i', None),
            ('slot', 'h', 4),
            ('itemId', 'h', -1),
            ('damage', 'h', None) # Not sure
            ]

class SpawnPosition(Packet):
    id = 0x06
    _format = [
            ('x', 'i', 117),
            ('y', 'i', 70),
            ('z', 'i', -46),
            ]

class UseEntity(Packet): # Not sure
    id = 0x07
    _format = [
            ('user', 'i', 0),
            ('target', 'i', None),
            ('leftClick', 'b', False), # Not sure
            ]

class UpdateHealth(Packet):
    id = 0x08
    _format = [
            ('health', 'h', 20),
            ]

class Respawn(Packet):
    id = 0x09
    _format = [
            ]

class PlayerOnGround(Packet):
    id = 0x0A
    _format = [
            ('onGround', 'b', True),
            ]

class PlayerPosition(Packet):
    id = 0x0B
    _format = [
            ('x', 'd', None),
            ('y', 'd', None),
            ('stance', 'd', None),
            ('z', 'd', None),
            ('onGround', 'b', True),
            ]

class PlayerLook(Packet):
    id = 0x0C
    _format = [
            ('yaw', 'f', 0),
            ('pitch', 'f', 0),
            ('onGround', 'b', True),
            ]

class PlayerPositionLook(Packet):
    id = 0x0D
    _format = [
            ('x', 'd', None),
            ('y', 'd', None),
            ('stance', 'd', None),
            ('z', 'd', None),
            ('yaw', 'f', 0),
            ('pitch', 'f', 0),
            ('onGround', 'b', True),
            ]
    def _createFromRaw(self, *args, **kwargs):
        Packet._createFromRaw(self, *args, **kwargs)
        self.y, self.stance = self.stance, self.y

class PlayerDigging(Packet):
    STARTED_DIGGING = 0
    FINISHED_DIGGING = 2
    DROP_ITEM = 4
    id = 0x0E
    _format = [
            ('status', 'b', STARTED_DIGGING),
            ('x', 'i', None),
            ('y', 'b', None),
            ('z', 'i', None),
            ('face', 'b', None),
            ]

class PlayerBlockPlacement(Packet):
    id = 0x0F
    def encode(*args, **kwargs):
        return ''
    decode = mcformat.BlockPlaceFormat.decode
    _format = [
            ('x', 'i', None),
            ('y', 'b', None),
            ('z', 'i', None),
            ('direction', 'b', None),
            ('itemId', 'h', -1),
            ('amount', 'b', 0), # Optional
            ('damage', 's', 0), # Optional
            ]

class HoldingChange(Packet):
    # aka ItemSwitch
    id = 0x10
    _format = [
            ('slotId', 'h', None),
            ]

class UseBed(Packet):
    id = 0x11
    _format = [
            ('entityId', 'i', 0),
            ('inBed', 'b', 0), # Not sure
            ('x', 'i', None),
            ('y', 'b', None),
            ('z', 'i', None),
            ]

class Animation(Packet):
    NO_ANIMATION = 0
    SWING_ARM = 1
    DAMAGE = 2
    LEAVE_BED = 3
    CROUCH = 104
    UNCROUCH = 105
    id = 0x12
    _format = [
            ('entityId', 'i', None),
            ('animate', 'b', NO_ANIMATION),
            ]

class EntityAction(Packet): # Not sure
    CROUCH = 1
    UNCROUCH = 2
    LEAVE_BED = 3
    id = 0x13
    _format = [
            ('entityId', 'i', None),
            ('action', 'b', None),
            ]

class NamedEntitySpawn(Packet):
    # Note that it is send when the entity comes into visible range
    id = 0x14
    _format = [
            ('entityId', 'i', None),
            ('playerName', 'S', None),
            ('x', 'i', None),
            ('y', 'i', None),
            ('z', 'i', None),
            ('rotation', 'b', None),
            ('pitch', 'b', None),
            ('currentItem', 'h', None),
            ]

class PickupSpawn(Packet):
    id = 0x15
    _format = [
            ('entityId', 'i', 0),
            ('item', 'h', None),
            ('count', 'b', 1),
            ('data', 'h', 0),
            ('x', 'i', None),
            ('y', 'i', None),
            ('z', 'i', None),
            ('rotation', 'b', None),
            ('pitch', 'b', None),
            ('roll', 'b', None),
            ]

class CollectItem(Packet):
    id = 0x16
    _format = [
            ('collectedId', 'i', None),
            ('collectorId', 'i', 0),
            ]

class AddObject(Packet):
    # Sent by the server
    id = 0x17
    _format = [
            ('entityId', 'i', None),
            ('type', 'b', None),
            ('x', 'i', None),
            ('y', 'i', None),
            ('z', 'i', None),
            ]

class MobSpawn(Packet):
    # Sent by the server
    CREEPER = 50
    SKELETON = 51
    SPIDER = 52
    GIANT_ZOMBIE = 53
    ZOMBIE = 54
    SLIME = 55
    GHAST = 56
    ZOMBIE_PIGMAN = 57
    PIG = 90
    SHEEP = 91
    COW = 92
    HEN = 93
    SQUID = 94
    WOLF = 95
    id = 0x18
    _format = [
            ('entityId', 'i', None),
            ('type', 'b', None),
            ('x', 'i', None),
            ('y', 'i', None),
            ('z', 'i', None),
            ('yaw', 'b', None),
            ('pitch', 'b', None),
            ('data', 'M', None),
            ]

class EntityPainting(Packet):
    id = 0x19
    _format = [
            ('entityId', 'i', None),
            ('title', 'S', None),
            ('x', 'i', None),
            ('y', 'i', None),
            ('z', 'i', None),
            ('direction', 'i', None),
            ]

class Unknown1(Packet): # Unknown
    id = 0x1B
    _format = [
            ('attribute1', 'f', None),
            ('attribute2', 'f', None),
            ('attribute3', 'b', None),
            ('attribute4', 'b', None),
            ('attribute5', 'f', None),
            ('attribute6', 'f', None),
            ]

class EntityVelocity(Packet): # Not sure
    id = 0x1C
    _format = [
            ('entityId', None),
            ('x', 'h', None),
            ('y', 'h', None),
            ('z', 'h', None),
            ]

class DestroyEntity(Packet):
    id = 0x1D
    _format = [
            ('entityId', 'i', None),
            ]

class Entity(Packet):
    id = 0x1E
    _format = [
            ('entityId', 'i', None),
            ]

class EntityRelativeMove(Packet):
    id = 0x1F
    _format = [
            ('entityId', 'i', None),
            ('x', 'b', None),
            ('y', 'b', None),
            ('z', 'b', None),
            ]

class EntityLook(Packet):
    id = 0x20
    _format = [
            ('entityId', 'i', None),
            ('yaw', 'b', None),
            ('pitch', 'b', None),
            ]

class EntityLookAndRelativeMove(Packet):
    id = 0x21
    _format = [
            ('entityId', 'i', None),
            ('x', 'b', None),
            ('y', 'b', None),
            ('z', 'b', None),
            ('yaw', 'b', None),
            ('pitch', 'b', None),
            ]

class EntityTeleport(Packet):
    id = 0x22
    _format = [
            ('entityId', 'i', None),
            ('x', 'b', None),
            ('y', 'b', None),
            ('z', 'b', None),
            ('yaw', 'b', None),
            ('pitch', 'b', None),
            ]

class EntityStatus(Packet): # Not sure
    id = 0x26
    _format = [
            ('entityId', 'i', None),
            ('entityStatus', 'b', None), # Not sure
            ]

class AttachEntity(Packet): # Not sure
    id = 0x27
    _format = [
            ('entityId', 'i', None),
            ('vehicleId', 'i', None),
            ]

class EntityMetadata(Packet):
    id = 0x28
    _format = [
            ('entityId', 'i', None),
            ('data', 'M', None),
            ]

class PreChunck(Packet):
    id = 0x32
    _format = [
            ('x', 'i', None),
            ('z', 'i', None),
            ('mode', 'b', None),
            ]

class MapChunk(Packet):
    id = 0x33
    def encode(*args, **kwargs):
        return ''
    decode = mcformat.ChunkFormat.decode
    _format = []


class Disconnect(Packet):
    id = 0xFF
    _format = [
            ('reason', 'S', 'kicked'),
            ]
