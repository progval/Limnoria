#!/usr/bin/env python

###
# Copyright (c) 2004, Jeremiah Fincher
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

"""
Maintains various arbitrary information on users.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

conf.registerPlugin('UserInfo')
conf.registerUserValue(conf.users, 'name',
    registry.String('', ''))
conf.registerUserValue(conf.users, 'email',
    registry.String('', ''))
conf.registerUserValue(conf.users, 'pgpkey',
    registry.String('', ''))

def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('UserInfo', True)


class UserInfo(callbacks.Privmsg):
    def userinfo(self, irc, msg, args):
        """[<name>]

        Returns the arbitrary data associated with the user <name>.  If <name>
        is not given, returns the data associated with the user giving the
        command.
        """
        name = privmsgs.getArgs(args, required=0, optional=1)
        if not name:
            name = msg.prefix
        try:
            id = ircdb.users.getUserId(name)
        except KeyError:
            irc.errorNoUser()
            return
        L = []
        end = '.%s' % id
        for name, wrapper in conf.users.getValues(getChildren=True):
            if name.endswith(end):
                L.append('%s: %s' % ('.'.join(name.split('.')[1:-1]), wrapper))
        if L:
            irc.reply(utils.commaAndify(L))
        else:
            irc.reply('I don\'t have any info on that user.')

    def set(self, irc, msg, args):
        """<name> <value>

        Sets some arbitrary data for the user giving the command.  Some good
        things to set are 'name', 'email', and 'pgpkey'.  Other names will
        depend on the plugins to which they belong.
        """
        (name, value) = privmsgs.getArgs(args, required=2)
        try:
            id = str(ircdb.users.getUserId(msg.prefix))
            group = conf.users
            for name in name.split('.'):
                group = group.get(name)
            group = group.get(id)
            group.set(value)
            irc.replySuccess()
        except KeyError:
            irc.errorNoUser()
        except registry.NonExistentRegistryEntry:
            irc.error('You may only associate data with "name", "email", '
                      'or "pgpkey".')
        except registry.InvalidRegistryValue, e:
            irc.error(str(e))


Class = UserInfo

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
