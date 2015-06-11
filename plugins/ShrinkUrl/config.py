###
# Copyright (c) 2005, Jeremiah Fincher
# Copyright (c) 2009-2010, James McCoy
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
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('ShrinkUrl')

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('ShrinkUrl', True)
    if yn(_("""This plugin offers a snarfer that will go retrieve a shorter
             version of long URLs that are sent to the channel.  Would you
             like this snarfer to be enabled?"""), default=False):
        conf.supybot.plugins.ShrinkUrl.shrinkSnarfer.setValue(True)

class ShrinkService(registry.OnlySomeStrings):
    """Valid values include 'tiny', 'ur1', and 'x0'."""
    validStrings = ('tiny', 'ur1', 'x0')

class ShrinkCycle(registry.SpaceSeparatedListOfStrings):
    """Valid values include 'ln', 'tiny', 'ur1', and 'x0'."""
    Value = ShrinkService

    def __init__(self, *args, **kwargs):
        super(ShrinkCycle, self).__init__(*args, **kwargs)
        self.lastIndex = -1

    def setValue(self, v):
        super(self.__class__, self).setValue(v)
        self.lastIndex = -1

    def getService(self):
        L = self()
        if L:
            self.lastIndex = (self.lastIndex + 1) % len(L)
            return L[self.lastIndex]
        raise ValueError('No services have been configured for rotation.  ' \
                'See conf.supybot.plugins.ShrinkUrl.serviceRotation.')

ShrinkUrl = conf.registerPlugin('ShrinkUrl')
conf.registerChannelValue(ShrinkUrl, 'shrinkSnarfer',
    registry.Boolean(False, _("""Determines whether the
    shrink snarfer is enabled.  This snarfer will watch for URLs in the
    channel, and if they're sufficiently long (as determined by
    supybot.plugins.ShrinkUrl.minimumLength) it will post a
    smaller URL from the service as denoted in
    supybot.plugins.ShrinkUrl.default.""")))
conf.registerChannelValue(ShrinkUrl.shrinkSnarfer, 'showDomain',
    registry.Boolean(True, _("""Determines whether the snarfer will show the
    domain of the URL being snarfed along with the shrunken URL.""")))
conf.registerChannelValue(ShrinkUrl, 'minimumLength',
    registry.PositiveInteger(48, _("""The minimum length a URL must be before
    the bot will shrink it.""")))
conf.registerChannelValue(ShrinkUrl, 'nonSnarfingRegexp',
    registry.Regexp(None, _("""Determines what URLs are to be snarfed; URLs
    matching the regexp given will not be snarfed.  Give the empty string if
    you have no URLs that you'd like to exclude from being snarfed.""")))
conf.registerChannelValue(ShrinkUrl, 'outFilter',
    registry.Boolean(False, _("""Determines whether the bot will shrink the
    URLs of outgoing messages if those URLs are longer than
    supybot.plugins.ShrinkUrl.minimumLength.""")))
conf.registerChannelValue(ShrinkUrl, 'default',
    ShrinkService('x0', _("""Determines what website the bot will use when
    shrinking a URL.""")))
conf.registerGlobalValue(ShrinkUrl, 'bold',
    registry.Boolean(True, _("""Determines whether this plugin will bold
    certain portions of its replies.""")))
conf.registerChannelValue(ShrinkUrl, 'serviceRotation',
    ShrinkCycle([], _("""If set to a non-empty value, specifies the list of
    services to rotate through for the shrinkSnarfer and outFilter.""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
