#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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
Commands that use the dictd protocol to snag stuff off a server.
"""

__revision__ = "$Id$"

import plugins

import sets
import random
import socket

import dictclient

import conf
import utils
import plugins
import ircutils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Dict')
    print 'The default dictd server is dict.org.'
    if yn('Would you like to specify a dictd server?') == 'y':
        server = something('What server?')
        onStart.append('dict config server %s' % server)

replyTimeout = 'Timeout on the dictd server.'
class Dict(callbacks.Privmsg, plugins.Configurable):
    threaded = True
    configurables = plugins.ConfigurableDictionary(
        [('server', plugins.ConfigurableStrType, 'dict.org',
          """Determines what server the bot will connect to to receive
          definitions from."""),]
    )
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        plugins.Configurable.__init__(self)

    def die(self):
        callbacks.Privmsg.die(self)
        plugins.Configurable.die(self)

    def dictionaries(self, irc, msg, args):
        """takes no arguments.

        Returns the dictionaries valid for the dict command.
        """
        try:
            conn = dictclient.Connection(self.configurables.get('server'))
            dbs = conn.getdbdescs().keys()
            dbs.sort()
            irc.reply(msg, utils.commaAndify(dbs))
        except socket.timeout:
            irc.error(msg, replyTimeout)

    def random(self, irc, msg, args):
        """takes no arguments.

        Returns a random valid dictionary.
        """
        try:
            conn = dictclient.Connection(self.configurables.get('server'))
            dbs = conn.getdbdescs().keys()
            irc.reply(msg, random.choice(dbs))
        except socket.timeout:
            irc.error(msg, replyTimeout)

    def dict(self, irc, msg, args):
        """[<dictionary>] <word>

        Looks up the definition of <word> on dict.org's dictd server.
        """
        if not args:
            raise callbacks.ArgumentError
        try:
            conn = dictclient.Connection(self.configurables.get('server'))
        except socket.timeout:
            irc.error(msg, 'Timeout on the dict server.')
            return
        dbs = sets.Set(conn.getdbdescs())
        if args[0] in dbs:
            dictionary = args.pop(0)
        else:
            dictionary = '*'
        word = privmsgs.getArgs(args)
        definitions = conn.define(dictionary, word)
        dbs = sets.Set()
        if not definitions:
            if dictionary == '*':
                irc.reply(msg, 'No definition for %r could be found.' % word)
            else:
                irc.reply(msg, 'No definition for %r could be found in %s' % \
                          (word, ircutils.bold(dictionary)))
            return
        L = []
        for d in definitions:
            dbs.add(ircutils.bold(d.getdb().getname()))
            (db, s) = (d.getdb().getname(), d.getdefstr())
            db = ircutils.bold(db)
            s = utils.normalizeWhitespace(s).rstrip(';.,')
            L.append('%s: %s' % (db, s))
        utils.sortBy(len, L)
        if dictionary == '*' and len(dbs) > 1:
            s = '%s responded: %s' % (utils.commaAndify(dbs), '; '.join(L)) 
        else:
            s = '; '.join(L)
        irc.reply(msg, s)


Class = Dict


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
