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
Handles configuration of the bot while it's running.
"""

import getopt

import conf
import utils
import ircdb
import plugins
import ircutils
import privmsgs
import registry
import callbacks

###
# Now, to setup the registry.
###
import registry

class InvalidRegistryName(callbacks.Error):
    pass

def getWrapper(name):
    parts = name.split('.')
    if not parts or parts[0] != 'supybot':
        raise InvalidRegistryName, name
    group = conf.supybot
    parts.pop(0)
    while parts:
        try:
            group = group.get(parts.pop(0))
        except registry.NonExistentRegistryEntry:
            raise InvalidRegistryName, name
    return group

def getCapability(name):
    capability = 'owner' # Default to requiring the owner capability.
    parts = name.split('.')
    while parts:
        part = parts.pop()
        if ircutils.isChannel(part):
            # If a registry value has a channel in it, it requires a channel.op
            # capability, or so we assume.  We'll see if we're proven wrong.
            capability = ircdb.makeChannelCapability(part, 'op')
        ### Do more later, for specific capabilities/sections.
    return capability


class Config(callbacks.Privmsg):
    def callCommand(self, method, irc, msg, *L):
        try:
            callbacks.Privmsg.callCommand(self, method, irc, msg, *L)
        except InvalidRegistryName, e:
            irc.error('%r is not a valid configuration variable.' % e.args[0])
        except registry.InvalidRegistryValue, e:
            irc.error(str(e))

    def list(self, irc, msg, args):
        """[--groups] <group>

        Returns the configuration variables available under the given
        configuration <group>.  If --groups is given, return the subgroups of
        the <group>.
        """
        (optlist, rest) = getopt.getopt(args, '', ['groups'])
        groups = False
        for (name, arg) in optlist:
            if name == '--groups':
                groups = True
        name = privmsgs.getArgs(rest)
        group = getWrapper(name)
        if groups:
            L = group.children.keys()
            if L:
                utils.sortBy(str.lower, L)
                irc.reply(utils.commaAndify(L))
            else:
                irc.reply('%s has no subgroups.' % name)
        else:
            if hasattr(group, 'getValues'):
                try:
                    L = zip(*group.getValues(fullNames=False))[0]
                    irc.reply(utils.commaAndify(L))
                except TypeError:
                    irc.error('There don\'t seem to be any values in %s'%name)
            else:
                irc.error('%r is not a valid configuration group.' % name)

    def search(self, irc, msg, args):
        """<word>

        Searches for <word> in the current configuration variables.
        """
        word = privmsgs.getArgs(args)
        word = word.lower()
        L = []
        for (name, _) in conf.supybot.getValues(getChildren=True):
            if word in name.lower():
                L.append(name)
        if L:
            irc.reply(utils.commaAndify(L))
        else:
            irc.reply('There were no matching configuration variables.')

    def config(self, irc, msg, args):
        """<name> [<value>]

        If <value> is given, sets the value of <name> to <value>.  Otherwise,
        returns the current value of <name>.
        """
        if len(args) >= 2:
            self._set(irc, msg, args)
        else:
            self._get(irc, msg, args)

    def _get(self, irc, msg, args):
        """<name>

        Shows the current value of the configuration variable <name>.
        """
        name = privmsgs.getArgs(args)
        wrapper = getWrapper(name)
        if wrapper.__class__ is registry.Group:
            irc.error(msg, 'That\'s not a value, it\'s a group.  Use the list '
                           'command in this plugin to see what values are '
                           'available in this group.')
            return
        irc.reply(str(wrapper))

    def _set(self, irc, msg, args):
        """<name> <value>

        Sets the current value of the configuration variable <name> to <value>.
        """
        (name, value) = privmsgs.getArgs(args, required=2)
        capability = getCapability(name)
        if ircdb.checkCapability(msg.prefix, capability):
            wrapper = getWrapper(name)
            wrapper.set(value)
            irc.replySuccess()
        else:
            irc.errorNoCapability(capability)

    def help(self, irc, msg, args):
        """<name>

        Returns the description of the configuration variable <name>.
        """
        name = privmsgs.getArgs(args)
        wrapper = getWrapper(name)
        if wrapper.help:
            irc.reply(wrapper.help)
        else:
            irc.error('%s has no help.' % name)

    def default(self, irc, msg, args):
        """<name>

        Returns the default value of the configuration variable <name>.
        """
        name = privmsgs.getArgs(args)
        wrapper = getWrapper(name)
        irc.reply(wrapper.default)

    def reload(self, irc, msg, args):
        """takes no arguments

        Reloads the various configuration files (user database, channel
        database, registry, etc.).
        """
        # TODO: Reload registry.
        ircdb.users.reload()
        ircdb.channels.reload()
        irc.replySuccess()
    reload = privmsgs.checkCapability(reload, 'owner')
        


Class = Config

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
