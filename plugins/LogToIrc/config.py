###
# Copyright (c) 2004, Stéphan Kochen
# Copyright (c) 2021, Valentin Lorentz
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

import logging

import supybot.log as log
import supybot.conf as conf
import supybot.ircutils as ircutils
import supybot.registry as registry

from .handler import _ircHandler


class IrcLogLevel(log.ValidLogLevel):
    """Value must be one of INFO, WARNING, ERROR, or CRITICAL."""
    minimumLevel = logging.INFO
    def setValue(self, v):
        log.ValidLogLevel.setValue(self, v)
        _ircHandler.setLevel(self())

class ValidChannelOrNick(registry.String):
    """Value must be a valid channel or a valid nick."""
    def setValue(self, v):
        if not (ircutils.isNick(v) or ircutils.isChannel(v)):
            self.error()
        registry.String.setValue(self, v)

class Targets(registry.SpaceSeparatedListOfStrings):
    Value = ValidChannelOrNick

conf.registerPlugin('LogToIrc')
conf.registerChannelValue(conf.supybot.plugins.LogToIrc, 'level',
    IrcLogLevel(logging.WARNING, """Determines what the minimum priority
    level logged will be to IRC. See supybot.log.level for possible
    values.  DEBUG is disabled due to the large quantity of output."""),
    opSettable=False)
conf.registerNetworkValue(conf.supybot.plugins.LogToIrc, 'targets',
    Targets([], """Space-separated list of channels/nicks the bot should
    log to.  If no channels/nicks are set, this plugin will effectively be
    turned off."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc, 'networks',
    registry.SpaceSeparatedSetOfStrings([], """Determines what networks the
    bot should log to.  If no networks are set, the bot will log on one network
    (whichever happens to be around at the time it feels like logging)."""))
conf.registerNetworkValue(conf.supybot.plugins.LogToIrc, 'channelModesRequired',
    registry.String('s', """Determines what channel modes a channel will be
    required to have for the bot to log to the channel.  If this string is
    empty, no modes will be checked."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc,
    'userCapabilityRequired', registry.String('owner', """Determines what
    capability is required for the bot to log to in private messages to the
    user.  If this is empty, there will be no capability that's checked."""))
conf.registerChannelValue(conf.supybot.plugins.LogToIrc, 'color',
    registry.Boolean(False, """Determines whether the bot's logs to IRC will be
    colorized with mIRC colors."""))
conf.registerChannelValue(conf.supybot.plugins.LogToIrc, 'notice',
    registry.Boolean(False, """Determines whether the bot's logs to IRC will be
    sent via NOTICE instead of PRIVMSG.  Channels will always be PRIVMSGed,
    regardless of this variable; NOTICEs will only be used if this variable is
    True and the target is a nick, not a channel."""))

def configure(advanced):
    from supybot.questions import something, anything, yn, output
    output("""Here you can set which channels and who the bot has to send log
              messages to. Note that by default in order to log to a channel
              the channel has to have mode +s set. Logging to a user requires
              the user to have the Owner capability.""")
    targets = ''
    while not targets:
        try:
            targets = anything('Which channels or users would you like to '
                               'send log messages to?')
            conf.supybot.plugins.LogToIrc.targets.set(targets)
        except registry.InvalidRegistryValue as e:
            output(str(e))
            targets = ''
    colorized = yn('Would you like these messages to be colored?')
    conf.supybot.plugins.LogToIrc.color.setValue(colorized)
    if advanced:
        level = ''
        while not level:
            try:
                level = something('What would you like the minimum priority '
                                  'level to be which will be logged to IRC?')
                conf.supybot.plugins.LogToIrc.level.set(level)
            except registry.InvalidRegistryValue as e:
                output(str(e))
                level = ''
