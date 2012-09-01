###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008, James McCoy
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

import socket

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    dictclient = utils.python.universalImport('dictclient', 'local.dictclient')
except ImportError:
    raise callbacks.Error, \
            'You need to have dictclient installed to use this plugin.  ' \
            'Download it at <http://quux.org:70/devel/dictclient>'

class Dict(callbacks.Plugin):
    threaded = True
    def dictionaries(self, irc, msg, args):
        """takes no arguments

        Returns the dictionaries valid for the dict command.
        """
        try:
            server = conf.supybot.plugins.Dict.server()
            conn = dictclient.Connection(server)
            dbs = list(conn.getdbdescs().keys())
            dbs.sort()
            irc.reply(format('%L', dbs))
        except socket.error, e:
            irc.error(utils.web.strError(e))
    dictionaries = wrap(dictionaries)

    def random(self, irc, msg, args):
        """takes no arguments

        Returns a random valid dictionary.
        """
        try:
            server = conf.supybot.plugins.Dict.server()
            conn = dictclient.Connection(server)
            dbs = conn.getdbdescs().keys()
            irc.reply(utils.iter.choice(dbs))
        except socket.error, e:
            irc.error(utils.web.strError(e))
    random = wrap(random)

    def dict(self, irc, msg, args, words):
        """[<dictionary>] <word>

        Looks up the definition of <word> on the dictd server specified by
        the supybot.plugins.Dict.server config variable.
        """
        try:
            server = conf.supybot.plugins.Dict.server()
            conn = dictclient.Connection(server)
        except socket.error, e:
            irc.error(utils.web.strError(e), Raise=True)
        dbs = set(conn.getdbdescs())
        if words[0] in dbs:
            dictionary = words.pop(0)
        else:
            default = self.registryValue('default', msg.args[0])
            if default in dbs:
                dictionary = default
            else:
                if default:
                    self.log.info('Default dict for %s is not a supported '
                                  'dictionary: %s.', msg.args[0], default)
                dictionary = '*'
        if not words:
            irc.error('You must give a word to define.', Raise=True)
        word = ' '.join(words)
        definitions = conn.define(dictionary, word)
        dbs = set()
        if not definitions:
            if dictionary == '*':
                irc.reply(format('No definition for %q could be found.', word))
            else:
                irc.reply(format('No definition for %q could be found in %s',
                                 word, ircutils.bold(dictionary)))
            return
        L = []
        for d in definitions:
            dbs.add(ircutils.bold(d.getdb().getname()))
            (db, s) = (d.getdb().getname(), d.getdefstr())
            db = ircutils.bold(db)
            s = utils.str.normalizeWhitespace(s).rstrip(';.,')
            L.append('%s: %s' % (db, s))
        utils.sortBy(len, L)
        if dictionary == '*' and len(dbs) > 1:
            s = format('%L responded: %s', list(dbs), '; '.join(L))
        else:
            s = '; '.join(L)
        irc.reply(s)
    dict = wrap(dict, [many('something')])


Class = Dict


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
