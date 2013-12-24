###
# Copyright (c) 2012, Valentin Lorentz
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

import time

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('NickAuth')

@internationalizeDocstring
class NickAuth(callbacks.Plugin):
    """Support authentication based on nicks and network services."""
    def __init__(self, irc):
        super(NickAuth, self).__init__(irc)
        self._requests = {}
    class nick(callbacks.Commands):
        def _check_auth(self, irc, msg, user):
            if user is None:
                irc.error(_('You are not authenticated.'), Raise=True)
            if not user.checkHostmask(msg.prefix):
                try:
                    u = ircdb.users.getUser(msg.prefix)
                except KeyError:
                    irc.error(_('You are not authenticated.'),
                              Raise=True)
                if not u._checkCapability('owner'):
                    irc.error(_('You must be owner to do that.'),
                              Raise=True)

        @internationalizeDocstring
        def add(self, irc, msg, args, network, user, nick):
            """[<network>] <user> <nick>

            Add <nick> to the list of nicks owned by the <user> on the
            <network>. You have to register this nick to the network
            services to be authenticated.
            <network> defaults to the current network.
            """
            network = network.network or irc.network
            user = user or ircdb.users.getUser(msg.prefix)
            self._check_auth(irc, msg, user)
            try:
                user.addNick(network, nick)
            except KeyError:
                irc.error(_('This nick is already used by someone on this '
                    'network.'), Raise=True)
            irc.replySuccess()
        add = wrap(add, [optional('networkIrc'),
                         optional('otherUser'),
                         'nick'])

        @internationalizeDocstring
        def remove(self, irc, msg, args, network, user, nick):
            """[<network>] <user> <nick>

            Remove <nick> from the list of nicks owned by the <user> on the
            <network>.
            <network> defaults to the current network.
            """
            network = network.network or irc.network
            user = user or ircdb.users.getUser(msg.prefix)
            self._check_auth(irc, msg, user)
            try:
                user.removeNick(network, nick)
            except KeyError:
                irc.error(_('This nick is not registered to you on this '
                    'network.'), Raise=True)
            irc.replySuccess()
        remove = wrap(remove, [optional('networkIrc'),
                               optional('otherUser'),
                               'nick'])

        @internationalizeDocstring
        def list(self, irc, msg, args, network, user):
            """[<network>] [<user>]

            Lists nicks of the <user> on the network.
            <network> defaults to the current network.
            """
            network = network.network or irc.network
            try:
                user = user or ircdb.users.getUser(msg.prefix)
            except KeyError:
                irc.error(_('You are not identified and <user> is not given.'),
                        Raise=True)
            self._check_auth(irc, msg, user)
            try:
                list_ = user.nicks[network]
                if list_:
                    irc.reply(format('%L', list_))
                else:
                    raise KeyError
            except KeyError:
                irc.error(_('You have no recognized nick on this '
                        'network.'), Raise=True)
        list = wrap(list, [optional('networkIrc'),
                           optional('otherUser')])

    @internationalizeDocstring
    def auth(self, irc, msg, args):
        """takes no argument

        Tries to authenticate you using network services.
        If you get no reply, it means you are not authenticated to the
        network services."""
        nick = ircutils.toLower(msg.nick)
        self._requests[(irc.network, msg.nick)] = (time.time(), msg.prefix, irc)
        irc.queueMsg(ircmsgs.whois(nick, nick))
    auth = wrap(auth, [])

    def do330(self, irc, msg):
        mynick, theirnick, theiraccount, garbage = msg.args
        # I would like to use a dict comprehension, but we have to support
        # Python 2.6 :(
        self._requests = dict([(x,y) for x,y in self._requests.items()
                if y[0]+60>time.time()])
        try:
            (timestamp, prefix, irc) = self._requests.pop((irc.network, theirnick))
        except KeyError:
            return
        user = ircdb.users.getUserFromNick(irc.network, theiraccount)
        if not user:
            user = ircdb.users.getUserFromNick(irc.network, theirnick)
        if user:
            user.addAuth(prefix)
            ircdb.users.setUser(user, flush=False)
            irc.reply(_('You are now authenticated as %s.') % user.name)
        else:
            irc.error(_('No user has this nick on this network.'))


Class = NickAuth


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
