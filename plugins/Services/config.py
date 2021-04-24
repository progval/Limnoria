###
# Copyright (c) 2005, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization('Services')

def registerNick(nick, password=''):
    p = conf.supybot.plugins.Services.Nickserv.get('password')
    h = _('Determines what password the bot will use with NickServ when ' \
        'identifying as %s.') % nick
    v = conf.registerNetworkValue(p, nick,
                                  registry.String(password, h, private=True))
    if password:
        v.setValue(password)

def configure(advanced):
    from supybot.questions import something
    conf.registerPlugin('Services', True)
    nick = something(_('What is your registered nick?'))
    password = something(_('What is your password for that nick?'))
    chanserv = something(_('What is your ChanServ named?'), default='ChanServ')
    nickserv = something(_('What is your NickServ named?'), default='NickServ')
    conf.supybot.plugins.Services.nicks.setValue([nick])
    conf.supybot.plugins.Services.NickServ.setValue(nickserv)
    registerNick(nick, password)
    conf.supybot.plugins.Services.ChanServ.setValue(chanserv)

class ValidNickOrEmptyString(registry.String):
    def setValue(self, v):
        if v and not ircutils.isNick(v):
            raise registry.InvalidRegistryValue('Value must be a valid nick or the empty string.')
        registry.String.setValue(self, v)

class ValidNickSet(conf.ValidNicks):
    List = ircutils.IrcSet

Services = conf.registerPlugin('Services')
conf.registerNetworkValue(Services, 'nicks',
    ValidNickSet([], _("""Determines what nicks the bot will use with
    services.""")))

class Networks(registry.SpaceSeparatedSetOfStrings):
    List = ircutils.IrcSet

conf.registerGlobalValue(Services, 'disabledNetworks',
    Networks(_('QuakeNet').split(), _("""Determines what networks this plugin
    will be disabled on.""")))

conf.registerNetworkValue(Services, 'noJoinsUntilIdentified',
    registry.Boolean(False, _("""Determines whether the bot will not join any
    channels until it is identified.  This may be useful, for instances, if
    you have a vhost that isn't set until you're identified, or if you're
    joining +r channels that won't allow you to join unless you identify.""")))
conf.registerNetworkValue(Services, 'ghostDelay',
    registry.NonNegativeInteger(60, _("""Determines how many seconds the bot will
    wait between successive GHOST attempts. Set this to 0 to disable GHOST.""")))
conf.registerNetworkValue(Services, 'NickServ',
    ValidNickOrEmptyString('NickServ', _("""Determines what nick the 'NickServ' service
    has.""")))
conf.registerGroup(Services.NickServ, 'password')
conf.registerNetworkValue(Services, 'ChanServ',
    ValidNickOrEmptyString('ChanServ', _("""Determines what nick the 'ChanServ' service
    has.""")))
conf.registerChannelValue(Services.ChanServ, 'password',
    registry.String('', _("""Determines what password the bot will use with
    ChanServ."""), private=True))
conf.registerChannelValue(Services.ChanServ, 'op',
    registry.Boolean(False, _("""Determines whether the bot will request to get
    opped by the ChanServ when it joins the channel.""")))
conf.registerChannelValue(Services.ChanServ, 'halfop',
    registry.Boolean(False, _("""Determines whether the bot will request to get
    half-opped by the ChanServ when it joins the channel.""")))
conf.registerChannelValue(Services.ChanServ, 'voice',
    registry.Boolean(False, _("""Determines whether the bot will request to get
    voiced by the ChanServ when it joins the channel.""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
