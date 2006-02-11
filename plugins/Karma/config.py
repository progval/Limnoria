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
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Karma', True)

conf.registerPlugin('Karma')

conf.registerChannelValue(conf.supybot.plugins.Karma, 'simpleOutput',
    registry.Boolean(False, """Determines whether the bot will output shorter
    versions of the karma output when requesting a single thing's karma."""))
conf.registerChannelValue(conf.supybot.plugins.Karma, 'response',
    registry.Boolean(False, """Determines whether the bot will reply with a
    success message when something's karma is increased or decreased."""))
conf.registerChannelValue(conf.supybot.plugins.Karma, 'rankingDisplay',
    registry.Integer(3, """Determines how many highest/lowest karma things are
    shown when karma is called with no arguments."""))
conf.registerChannelValue(conf.supybot.plugins.Karma, 'mostDisplay',
    registry.Integer(25, """Determines how many karma things are shown when
    the most command is called.'"""))
conf.registerChannelValue(conf.supybot.plugins.Karma, 'allowSelfRating',
    registry.Boolean(False, """Determines whether users can adjust the karma
    of their nick."""))
conf.registerChannelValue(conf.supybot.plugins.Karma, 'allowUnaddressedKarma',
    registry.Boolean(False, """Determines whether the bot will
    increase/decrease karma without being addressed."""))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
