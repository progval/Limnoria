###
# Copyright (c) 2005, Jeremiah Fincher
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

import supybot.conf as conf
import supybot.ircutils as ircutils
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Relay')

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Relay', True)
    if yn(_('Would you like to relay between any channels?')):
        channels = anything(_('What channels?  Separate them by spaces.'))
        conf.supybot.plugins.Relay.channels.set(channels)
    if yn(_('Would you like to use color to distinguish between nicks?')):
        conf.supybot.plugins.Relay.color.setValue(True)
    output("""Right now there's no way to configure the actual connection to
    the server.  What you'll need to do when the bot finishes starting up is
    use the 'start' command followed by the 'connect' command.  Use the 'help'
    command to see how these two commands should be used.""")

class Ignores(registry.SpaceSeparatedListOf):
    List = ircutils.IrcSet
    Value = conf.ValidHostmask
    
class Networks(registry.SpaceSeparatedListOf):
    List = ircutils.IrcSet
    Value = registry.String

Relay = conf.registerPlugin('Relay')
conf.registerChannelValue(Relay, 'color',
    registry.Boolean(True, _("""Determines whether the bot will color relayed
    PRIVMSGs so as to make the messages easier to read.""")))
conf.registerChannelValue(Relay, 'topicSync',
    registry.Boolean(True, _("""Determines whether the bot will synchronize
    topics between networks in the channels it relays.""")))
conf.registerChannelValue(Relay, 'hostmasks',
    registry.Boolean(True, _("""Determines whether the bot will relay the
    hostmask of the person joining or parting the channel when they join
    or part.""")))
conf.registerChannelValue(Relay, 'includeNetwork',
    registry.Boolean(True, _("""Determines whether the bot will include the
    network in relayed PRIVMSGs; if you're only relaying between two networks,
    it's somewhat redundant, and you may wish to save the space.""")))
conf.registerChannelValue(Relay, 'punishOtherRelayBots',
    registry.Boolean(True, _("""Determines whether the bot will detect other
    bots relaying and respond by kickbanning them.""")))
conf.registerGlobalValue(Relay, 'channels',
    conf.SpaceSeparatedSetOfChannels([], _("""Determines which channels the bot
    will relay in.""")))
conf.registerChannelValue(Relay.channels, 'joinOnAllNetworks',
    registry.Boolean(False, _("""Determines whether the bot
    will always join the channel(s) it relays when connecting to any network.
    """)))
conf.registerChannelValue(Relay, 'ignores',
    Ignores([], _("""Determines what hostmasks will not be relayed on a
    channel.""")))
conf.registerChannelValue(Relay, 'noticeNonPrivmsgs',
    registry.Boolean(False, _("""Determines whether the bot will used NOTICEs
    rather than PRIVMSGs for non-PRIVMSG relay messages (i.e., joins, parts,
    nicks, quits, modes, etc.)""")))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
