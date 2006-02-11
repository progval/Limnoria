###
# Copyright (c) 2004-2005, Jeremiah Fincher
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
import supybot.utils as utils
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Channel', True)

class BanmaskStyle(registry.SpaceSeparatedSetOfStrings):
    validStrings = ('exact', 'nick', 'user', 'host')
    def __init__(self, *args, **kwargs):
        assert self.validStrings, 'There must be some valid strings.  ' \
                                  'This is a bug.'
        registry.SpaceSeparatedSetOfStrings.__init__(self, *args, **kwargs)
        self.__doc__ = format('Valid values include %L.',
                              map(repr, self.validStrings))

    def help(self):
        strings = [s for s in self.validStrings if s]
        return format('%s  Valid strings: %L.', self._help, strings)

    def normalize(self, s):
        lowered = s.lower()
        L = list(map(str.lower, self.validStrings))
        try:
            i = L.index(lowered)
        except ValueError:
            return s # This is handled in setValue.
        return self.validStrings[i]

    def setValue(self, v):
        v = map(self.normalize, v)
        for s in v:
            if s not in self.validStrings:
                self.error()
        registry.SpaceSeparatedSetOfStrings.setValue(self, self.List(v))

Channel = conf.registerPlugin('Channel')
conf.registerChannelValue(Channel, 'alwaysRejoin',
    registry.Boolean(True, """Determines whether the bot will always try to
    rejoin a channel whenever it's kicked from the channel."""))
conf.registerChannelValue(Channel, 'banmask',
    BanmaskStyle(['user', 'host'], """Determines what will be used as the
    default banmask style."""))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
