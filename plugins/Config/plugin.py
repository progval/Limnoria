###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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

import os
import signal

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
from supybot.commands import *
from supybot.utils.iter import all
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Config')

###
# Now, to setup the registry.
###

def getWrapper(name):
    parts = registry.split(name)
    if not parts or parts[0] not in ('supybot', 'users'):
        raise registry.InvalidRegistryName(name)
    group = getattr(conf, parts.pop(0))
    while parts:
        part = parts.pop(0)
        if group.__hasattr__(part):
            group = group.get(part)
        else:
            # We'll raise registry.InvalidRegistryName here so
            # that we have a useful error message for the user.
            raise registry.InvalidRegistryName(name)
    return group

def getCapability(name):
    capability = 'owner' # Default to requiring the owner capability.
    parts = registry.split(name)
    while parts:
        part = parts.pop()
        if ircutils.isChannel(part):
            # If a registry value has a channel in it, it requires a
            # 'channel,op' capability, or so we assume.  We'll see if we're
            # proven wrong.
            capability = ircdb.makeChannelCapability(part, 'op')
        ### Do more later, for specific capabilities/sections.
    return capability

def _reload():
    ircdb.users.reload()
    ircdb.ignores.reload()
    ircdb.channels.reload()
    registry.open_registry(world.registryFilename)

def _hupHandler(sig, frame):
    log.info('Received SIGHUP, reloading configuration.')
    _reload()

if os.name == 'posix':
    signal.signal(signal.SIGHUP, _hupHandler)

def getConfigVar(irc, msg, args, state):
    name = args[0]
    if name.startswith('conf.'):
        name = name[5:]
    if not name.startswith('supybot') and not name.startswith('users'):
        name = 'supybot.' + name
    try:
        group = getWrapper(name)
        state.args.append(group)
        del args[0]
    except registry.InvalidRegistryName as e:
        state.errorInvalid(_('configuration variable'), str(e))
addConverter('configVar', getConfigVar)

def getSettableConfigVar(irc, msg, args, state):
    getConfigVar(irc, msg, args, state)
    if not hasattr(state.args[-1], 'set'):
        state.errorInvalid(_('settable configuration variable'),
                           state.args[-1]._name)
addConverter('settableConfigVar', getSettableConfigVar)

class Config(callbacks.Plugin):
    """Provides access to the Supybot configuration. This is
    a core Supybot plugin that should not be removed!"""
    def callCommand(self, command, irc, msg, *args, **kwargs):
        try:
            super(Config, self).callCommand(command, irc, msg, *args, **kwargs)
        except registry.InvalidRegistryValue as e:
            irc.error(str(e))

    def _list(self, group):
        L = []
        for (vname, v) in group._children.items():
            if hasattr(group, 'channelValue') and group.channelValue and \
               ircutils.isChannel(vname) and not v._children:
                continue
            if hasattr(v, 'channelValue') and v.channelValue:
                vname = '#' + vname
            if v._added and not all(ircutils.isChannel, v._added):
                vname = '@' + vname
            L.append(vname)
        utils.sortBy(str.lower, L)
        return L

    @internationalizeDocstring
    def list(self, irc, msg, args, group):
        """<group>

        Returns the configuration variables available under the given
        configuration <group>.  If a variable has values under it, it is
        preceded by an '@' sign.  If a variable is a 'ChannelValue', that is,
        it can be separately configured for each channel using the 'channel'
        command in this plugin, it is preceded by an '#' sign.
        """
        L = self._list(group)
        if L:
            irc.reply(format('%L', L))
        else:
            irc.error(_('There don\'t seem to be any values in %s.') % 
                      group._name)
    list = wrap(list, ['configVar'])

    @internationalizeDocstring
    def search(self, irc, msg, args, word):
        """<word>

        Searches for <word> in the current configuration variables.
        """
        L = []
        for (name, x) in conf.supybot.getValues(getChildren=True):
            if word in name.lower():
                possibleChannel = registry.split(name)[-1]
                if not ircutils.isChannel(possibleChannel):
                    L.append(name)
        if L:
            irc.reply(format('%L', L))
        else:
            irc.reply(_('There were no matching configuration variables.'))
    search = wrap(search, ['lowered']) # XXX compose with withoutSpaces?

    def _getValue(self, irc, msg, group, addChannel=False):
        value = str(group) or ' '
        if addChannel and irc.isChannel(msg.args[0]) and not irc.nested:
            s = str(group.get(msg.args[0]))
            value = _('Global: %s; %s: %s') % (value, msg.args[0], s)
        if hasattr(group, 'value'):
            if not group._private:
                irc.reply(value)
            else:
                capability = getCapability(group._name)
                if ircdb.checkCapability(msg.prefix, capability):
                    irc.reply(value, private=True)
                else:
                    irc.errorNoCapability(capability)
        else:
            irc.error(_('That registry variable has no value.  Use the list '
                      'command in this plugin to see what variables are '
                      'available in this group.'))

    def _setValue(self, irc, msg, group, value):
        capability = getCapability(group._name)
        if ircdb.checkCapability(msg.prefix, capability):
            # I think callCommand catches exceptions here.  Should it?
            group.set(value)
            irc.replySuccess()
        else:
            irc.errorNoCapability(capability)

    @internationalizeDocstring
    def channel(self, irc, msg, args, channel, group, value):
        """[<channel>] <name> [<value>]

        If <value> is given, sets the channel configuration variable for <name>
        to <value> for <channel>.  Otherwise, returns the current channel
        configuration value of <name>.  <channel> is only necessary if the
        message isn't sent in the channel itself."""
        if not group.channelValue:
            irc.error(_('That configuration variable is not a channel-specific '
                      'configuration variable.'))
            return
        group = group.get(channel)
        if value is not None:
            self._setValue(irc, msg, group, value)
        else:
            self._getValue(irc, msg, group)
    channel = wrap(channel, ['channel', 'settableConfigVar',
                             additional('text')])

    @internationalizeDocstring
    def config(self, irc, msg, args, group, value):
        """<name> [<value>]

        If <value> is given, sets the value of <name> to <value>.  Otherwise,
        returns the current value of <name>.  You may omit the leading
        "supybot." in the name if you so choose.
        """
        if value is not None:
            self._setValue(irc, msg, group, value)
        else:
            self._getValue(irc, msg, group, addChannel=group.channelValue)
    config = wrap(config, ['settableConfigVar', additional('text')])

    @internationalizeDocstring
    def help(self, irc, msg, args, group):
        """<name>

        Returns the description of the configuration variable <name>.
        """
        if hasattr(group, '_help'):
            s = group.help()
            if s:
                if hasattr(group, 'value') and not group._private:
                    channel = msg.args[0]
                    if irc.isChannel(channel) and \
                            channel in group._children:
                        globvalue = str(group)
                        chanvalue = str(group.get(channel))
                        if chanvalue != globvalue:
                            s += _('  (Current global value: %s;  '
                                    'current channel value: %s)') % \
                                            (globvalue, chanvalue)
                        else:
                            s += _('  (Current value: %s)') % group
                    else:
                        s += _('  (Current value: %s)') % group
                irc.reply(s)
            else:
                irc.reply(_('That configuration group exists, but seems to '
                          'have no help.  Try "config list %s" to see if it '
                          'has any children values.') % group._name)
        else:
            irc.error(_('%s has no help.') % group._name)
    help = wrap(help, ['configVar'])

    @internationalizeDocstring
    def default(self, irc, msg, args, group):
        """<name>

        Returns the default value of the configuration variable <name>.
        """
        v = group.__class__(group._default, '')
        irc.reply(str(v))
    default = wrap(default, ['settableConfigVar'])

    @internationalizeDocstring
    def reload(self, irc, msg, args):
        """takes no arguments

        Reloads the various configuration files (user database, channel
        database, registry, etc.).
        """
        _reload() # This was factored out for SIGHUP handling.
        irc.replySuccess()
    reload = wrap(reload, [('checkCapability', 'owner')])

    @internationalizeDocstring
    def export(self, irc, msg, args, filename):
        """<filename>

        Exports the public variables of your configuration to <filename>.
        If you want to show someone your configuration file, but you don't
        want that person to be able to see things like passwords, etc., this
        command will export a "sanitized" configuration file suitable for
        showing publicly.
        """
        registry.close(conf.supybot, filename, private=False)
        irc.replySuccess()
    export = wrap(export, [('checkCapability', 'owner'), 'filename'])

    @internationalizeDocstring
    def setdefault(self, irc, msg, args, group):
        """<name>

        Resets the configuration variable <name> to its default value.
        """
        v = str(group.__class__(group._default, ''))
        self._setValue(irc, msg, group, v)
    setdefault = wrap(setdefault, ['settableConfigVar'])

Class = Config

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
