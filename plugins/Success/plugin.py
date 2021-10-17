###
# Copyright (c) 2005, Daniel DiPaolo
# Copyright (c) 2010-2021, Valentin Lorentz
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
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Success')

class Success(plugins.ChannelIdDatabasePlugin):
    """This plugin was written initially to work with MoobotFactoids, the two
    of them to provide a similar-to-moobot-and-blootbot interface for factoids.
    Basically, it replaces the standard 'The operation succeeded.' messages
    with messages kept in a database, able to give more personable
    responses."""

    def __init__(self, irc):
        self.__parent = super(Success, self)
        self.__parent.__init__(irc)
        self.target = None
        pluginSelf = self
        self.originalClass = conf.supybot.replies.success.__class__
        class MySuccessClass(self.originalClass):
            __slots__ = ()
            def __call__(self):
                msg = dynamic.msg
                ret = pluginSelf.db.random(msg.channel or msg.args[0])
                if ret is None:
                    try:
                        self.__class__ = pluginSelf.originalClass
                        ret = self()
                    finally:
                        self.__class__ = MySuccessClass
                else:
                    ret = ret.text
                return ret

            def get(self, attr):
                if irc.isChannel(attr):
                    pluginSelf.target = attr
                return self
        conf.supybot.replies.success.__class__ = MySuccessClass

    def die(self):
        self.__parent.die()
        conf.supybot.replies.success.__class__ = self.originalClass

Success = internationalizeDocstring(Success)

Class = Success

# vim:set shiftwidth=4 softtabstop=8 expandtab textwidth=78:
