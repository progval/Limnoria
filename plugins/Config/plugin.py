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

def getCapability(irc, name):
    capability = 'owner' # Default to requiring the owner capability.
    if not name.startswith('supybot') and not name.startswith('users'):
        name = 'supybot.' + name
    parts = registry.split(name)
    group = getattr(conf, parts.pop(0))
    while parts:
        part = parts.pop(0)
        group = group.get(part)
        if not getattr(group, '_opSettable', True):
            return 'owner'
        if irc.isChannel(part):
            # If a registry value has a channel in it, it requires a
            # 'channel,op' capability, or so we assume.  We'll see if we're
            # proven wrong.
            capability = ircdb.makeChannelCapability(part, 'op')
        ### Do more later, for specific capabilities/sections.
    return capability

def isReadOnly(name):
    """Prevents changing certain config variables to gain shell access via
    a vulnerable IRC network."""
    parts = registry.split(name.lower())
    if parts[0] != 'supybot':
        parts.insert(0, 'supybot')
    if parts == ['supybot', 'commands', 'allowshell'] and \
            not conf.supybot.commands.allowShell():
        # allow setting supybot.commands.allowShell from True to False,
        # but not from False to True.
        # Otherwise an IRC network could overwrite it.
        return True
    elif parts[0:2] == ['supybot', 'directories'] and \
            not conf.supybot.commands.allowShell():
        # Setting plugins directory allows for arbitrary code execution if
        # an attacker can both use the IRC network to MITM and upload files
        # on the server (eg. with a web CMS).
        # Setting other directories allows writing data at arbitrary
        # locations.
        return True
    else:
        return False

def checkCanSetValue(irc, msg, group):
    if isReadOnly(group._name):
        irc.error(_("This configuration variable is not writeable "
            "via IRC. To change it you have to: 1) use the 'flush' command 2) edit "
            "the config file 3) use the 'config reload' command."), Raise=True)
    capability = getCapability(irc, group._name)
    if not ircdb.checkCapability(msg.prefix, capability):
        irc.errorNoCapability(capability, Raise=True)

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

    def _list(self, irc, group):
        L = []
        for (vname, v) in group._children.items():
            if getattr(group, '_networkValue', False) and \
                    vname.startswith(':'):
                # Skip pseudo-children that are network names
                continue
            if getattr(group, '_channelValue', False) and \
                    irc.isChannel(vname):
                # Skip pseudo-children that are channel names
                continue
            if getattr(v, '_networkValue', False):
                vname = ':' + vname
            if getattr(v, '_channelValue', False):
                vname = '#' + vname
            if v._added and not all(
                    irc.isChannel(child) or child.startswith(':')
                    for child in v._added):
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
        And if a variable is a 'NetworkValue', it is preceded by a ':' sign.
        """
        L = self._list(irc, group)
        if L:
            irc.reply(format('%L', sorted(L)))
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
                last_name_part = registry.split(name)[-1]
                if not irc.isChannel(last_name_part) \
                        and not last_name_part.startswith(':'): # network
                    L.append(name)
        if L:
            irc.reply(format('%L', L))
        else:
            irc.reply(_('There were no matching configuration variables.'))
    search = wrap(search, ['lowered']) # XXX compose with withoutSpaces?

    @internationalizeDocstring
    def searchhelp(self, irc, msg, args, phrase):
        """<phrase>

        Searches for <phrase> in the help of current configuration variables.
        """
        L = []
        for (name, x) in conf.supybot.getValues(getChildren=True):
            if phrase in x.help().lower():
                last_name_part = registry.split(name)[-1]
                if not irc.isChannel(last_name_part) \
                        and not last_name_part.startswith(':'): # network
                    L.append(name)
        if L:
            irc.reply(format('%L', L))
        else:
            irc.reply(_('There were no matching configuration variables.'))
    searchhelp = wrap(searchhelp, ['lowered'])

    @internationalizeDocstring
    def searchvalues(self, irc, msg, args, word):
        """<word>

        Searches for <word> in the values of current configuration variables.
        """
        L = []
        for (name, x) in conf.supybot.getValues(getChildren=True):
            if (hasattr(x, 'value') # not a group
                    and word in str(x()).lower()):
                last_name_part = registry.split(name)[-1]
                L.append(name)
        if L:
            irc.reply(format('%L', L))
        else:
            irc.reply(_('There were no matching configuration variables.'))
    searchvalues = wrap(searchvalues, ['lowered'])

    def _getValue(self, irc, msg, group, network=None, channel=None, addGlobal=False):
        global_group = group
        global_value = str(group) or ' '
        group = group.getSpecific(
            network=network.network, channel=channel, check=False)
        value = str(group) or ' '
        if addGlobal and not irc.nested:
            if global_group._channelValue and channel:
                # TODO: also show the network value when relevant
                value = _(
                    'Global: %(global_value)s; '
                    '%(channel_name)s @ %(network_name)s: %(channel_value)s') % {
                    'global_value': global_value,
                    'channel_name': msg.channel,
                    'network_name': irc.network,
                    'channel_value': value,
                }
            elif global_group._networkValue and network:
                value = _(
                    'Global: %(global_value)s; '
                    '%(network_name)s: %(network_value)s') % {
                    'global_value': global_value,
                    'network_name': irc.network,
                    'network_value': value,
                }
        if hasattr(global_group, 'value'):
            if not global_group._private:
                return (value, None)
            else:
                capability = getCapability(irc, group._name)
                if ircdb.checkCapability(msg.prefix, capability):
                    return (value, True)
                else:
                    irc.errorNoCapability(capability, Raise=True)
        else:
            irc.error(_('That registry variable has no value.  Use the list '
                      'command in this plugin to see what variables are '
                      'available in this group.'), Raise=True)

    def _setValue(self, irc, msg, group, value):
        checkCanSetValue(irc, msg, group)
        # I think callCommand catches exceptions here.  Should it?
        group.set(value)

    @internationalizeDocstring
    def channel(self, irc, msg, args, network, channels, group, value):
        """[<network>] [<channel>] <name> [<value>]

        If <value> is given, sets the channel configuration variable for <name>
        to <value> for <channel> on the <network>.
        Otherwise, returns the current channel
        configuration value of <name>.  <channel> is only necessary if the
        message isn't sent in the channel itself. More than one channel may
        be given at once by separating them with commas.
        <network> defaults to the current network."""
        if not group._channelValue:
            irc.error(_('That configuration variable is not a channel-specific '
                      'configuration variable.'))
            return
        if value is not None:
            for channel in channels:
                assert irc.isChannel(channel)

                # Sets the non-network-specific value, for forward
                # compatibility, ie. this will work even if the owner rolls
                # back Limnoria to an older version.
                # It's also an easy way to support plugins which are not
                # network-aware.
                self._setValue(irc, msg, group.get(channel), value)

                if network != '*':
                    # Set the network-specific value
                    self._setValue(irc, msg, group.get(':' + network.network).get(channel), value)

            irc.replySuccess()
        else:
            if network == '*':
                network = None
            values = []
            private = None
            for channel in channels:
                (value, private_value) = \
                    self._getValue(irc, msg, group, network, channel)
                values.append((channel, value))
                if private_value:
                    private = True
            if len(channels) > 1:
                irc.reply('; '.join(['%s: %s' % (channel, value)
                                     for (channel, value) in values]),
                          private=private)
            else:
                irc.reply(values[0][1], private=private)
    channel = wrap(channel, [optional(first(('literal', '*'), 'networkIrc')),
                             'channels', 'settableConfigVar',
                             additional('text')])

    def network(self, irc, msg, args, network, group, value):
        """[<network>] <name> [<value>]

        If <value> is given, sets the network configuration variable for <name>
        to <value> for <network>.
        Otherwise, returns the current network configuration value of <name>.
        <network> defaults to the current network."""
        if not group._networkValue:
            irc.error(_('That configuration variable is not a network-specific '
                      'configuration variable.'))
            return
        if value is not None:
            self._setValue(irc, msg, group.get(':' + network.network), value)

            irc.replySuccess()
        else:
            values = []
            private = None
            (value, private) = \
                self._getValue(irc, msg, group, network)
            irc.reply(value, private=private)
    network = wrap(network, ['networkIrc', 'settableConfigVar',
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
            irc.replySuccess()
        else:
            (value, private) = self._getValue(
                irc, msg, group, network=irc,
                channel=msg.channel,
                addGlobal=group._channelValue or group._networkValue)
            irc.reply(value, private=private)
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
                    if msg.channel and \
                            msg.channel in group._children:
                        globvalue = str(group)
                        chanvalue = str(group.get(msg.channel))
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
        if not conf.supybot.commands.allowShell():
            # Disallow writing arbitrary files
            irc.error('This command is not available, because '
                'supybot.commands.allowShell is False.', Raise=True)
        registry.close(conf.supybot, filename, private=False)
        irc.replySuccess()
    export = wrap(export, [('checkCapability', 'owner'), 'filename'])

    @internationalizeDocstring
    def setdefault(self, irc, msg, args, group):
        """<name>

        Resets the configuration variable <name> to its default value.
        Use commands 'reset channel' and 'reset network' instead to make
        a channel- or network- specific value inherit from the global one.
        """
        v = str(group.__class__(group._default, ''))
        self._setValue(irc, msg, group, v)
        irc.replySuccess()
    setdefault = wrap(setdefault, ['settableConfigVar'])

    class reset_(callbacks.Commands):
        # to prevent conflict with the reset() command of callbacks, this class
        # is renamed 'reset_'
        def name(self):
            return 'reset'

        @internationalizeDocstring
        def channel(self, irc, msg, args, network, channel, group):
            """[<network>] [<channel>] <name>

            Resets the channel-specific value of variable <name>, so that
            it will match the network-specific value (or the global one
            if the latter isn't set).
            <network> and <channel> default to the current network and
            channel.
            """

            if network != '*':
                # reset group.:network.#channel
                netgroup = group.get(':' + network.network)
                changroup = netgroup.get(channel)
                checkCanSetValue(irc, msg, changroup)
                changroup._setValue(netgroup.value, inherited=True)

            # reset group.#channel
            changroup = group.get(channel)
            checkCanSetValue(irc, msg, changroup)
            changroup._setValue(group.value, inherited=True)

            irc.replySuccess()
        channel = wrap(channel, [
            optional(first(('literal', '*'), 'networkIrc')),
            'channel', 'settableConfigVar'])

        @internationalizeDocstring
        def network(self, irc, msg, args, network, group):
            """[<network>] [<channel>] <name>

            Resets the network-specific value of variable <name>, so that
            it will match the global.
            <network> defaults to the current network and
            channel.
            """
            # reset group.#channel
            changroup = group.get(':' + network.network)
            checkCanSetValue(irc, msg, changroup)
            changroup._setValue(group.value, inherited=True)

            irc.replySuccess()
        network = wrap(network, ['networkIrc', 'settableConfigVar'])

Class = Config

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
