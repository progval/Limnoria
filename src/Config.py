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

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import getopt

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

###
# Now, to setup the registry.
###

class InvalidRegistryName(callbacks.Error):
    pass

def getWrapper(name):
    parts = registry.split(name)
    if not parts or parts[0] not in ('supybot', 'users'):
        raise InvalidRegistryName, name
    group = getattr(conf, parts.pop(0))
    while parts:
        try:
            group = group.get(parts.pop(0))
        except registry.NonExistentRegistryEntry:
            raise InvalidRegistryName, name
    return group

def getCapability(name):
    capability = 'owner' # Default to requiring the owner capability.
    parts = registry.split(name)
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

    def _canonicalizeName(self, name):
        if not name.startswith('supybot') and not name.startswith('users'):
            name = 'supybot.' + name
        return name

    def _list(self, name, groups=False):
        name = self._canonicalizeName(name)
        group = getWrapper(name)
        if groups:
            L = []
            for (vname, v) in group.children.iteritems():
                if v.added:
                    L.append(vname)
            utils.sortBy(str.lower, L)
            return L
        else:
            try:
                L = [t[0] for t in group.getValues(fullNames=False)]
                utils.sortBy(str.lower, L)
                return L
            except TypeError:
                return []
        
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
        L = self._list(name, groups=groups)
        if L:
            irc.reply(utils.commaAndify(L))
        elif groups:
            irc.reply('%s has no subgroups.' % name)
        else:
            irc.error('There don\'t seem to be any values in %s' % name)

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
        returns the current value of <name>.  You may omit the leading
        "supybot." in the name if you so choose.
        """
        if len(args) >= 2:
            self._set(irc, msg, args)
        else:
            self._get(irc, msg, args)

    def channel(self, irc, msg, args):
        """[<channel>] <name> [<value>]

        If <value> is given, sets the channel configuration variable for <name>
        to <value> for <channel>.  Otherwise, returns the current channel
        configuration value of <name>.  <channel> is only necessary if the
        message isn't sent in the channel itself."""
        channel = privmsgs.getChannel(msg, args)
        if not args:
            raise callbacks.ArgumentError
        args[0] = self._canonicalizeName(args[0])
        wrapper = getWrapper(args[0])
        if not wrapper.channelValue:
            irc.error('That configuration variable is not a channel-specific '
                      'configuration variable.')
            return
        components = registry.split(args[0])
        components.append(channel)
        args[0] = registry.join(components)
        self.config(irc, msg, args)

    def _get(self, irc, msg, args):
        """<name>

        Shows the current value of the configuration variable <name>.
        """
        name = privmsgs.getArgs(args)
        name = self._canonicalizeName(name)
        wrapper = getWrapper(name)
        if hasattr(wrapper, 'value'):
            if not wrapper._private:
                irc.reply(str(wrapper))
            else:
                capability = getCapability(name)
                if ircdb.checkCapability(msg.prefix, capability):
                    irc.reply(str(wrapper))
                else:
                    irc.errorNoCapability(capability)
        else:
            irc.error('That registry variable has no value.  Use the list '
                      'command in this plugin to see what values are '
                      'available in this group.')

    def _set(self, irc, msg, args):
        """<name> <value>

        Sets the current value of the configuration variable <name> to <value>.
        """
        (name, value) = privmsgs.getArgs(args, required=2)
        name = self._canonicalizeName(name)
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
        name = self._canonicalizeName(name)
        wrapper = getWrapper(name)
        if hasattr(wrapper, 'help'):
            irc.reply(wrapper.help)
        else:
            irc.error('%s has no help.' % name)

    def default(self, irc, msg, args):
        """<name>

        Returns the default value of the configuration variable <name>.
        """
        name = privmsgs.getArgs(args)
        name = self._canonicalizeName(name)
        wrapper = getWrapper(name)
        v = wrapper.__class__(wrapper.default, '')
        irc.reply(str(v))

    def reload(self, irc, msg, args):
        """takes no arguments

        Reloads the various configuration files (user database, channel
        database, registry, etc.).
        """
        ircdb.users.reload()
        ircdb.channels.reload()
        registry.open(world.registryFilename)
        irc.replySuccess()
    reload = privmsgs.checkCapability(reload, 'owner')
        


Class = Config

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
