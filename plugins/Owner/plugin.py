###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008-2009, James McCoy
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

import gc
import os
import sys
import time
import socket
import string
import linecache

import re

import supybot.log as log
import supybot.conf as conf
import supybot.i18n as i18n
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
import supybot.irclib as irclib
import supybot.plugin as plugin
import supybot.plugins as plugins
import supybot.drivers as drivers
import supybot.utils.minisix as minisix
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.commands import additional, getopts, optional, wrap
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Owner')

###
# supybot.commands.
###

def registerDefaultPlugin(command, plugin):
    command = callbacks.canonicalName(command)
    conf.registerGlobalValue(conf.supybot.commands.defaultPlugins,
                             command, registry.String(plugin, ''))
    # This must be set, or the quotes won't be removed.
    conf.supybot.commands.defaultPlugins.get(command).set(plugin)


registerDefaultPlugin('list', 'Misc')
registerDefaultPlugin('help', 'Misc')
registerDefaultPlugin('ignore', 'Admin')
registerDefaultPlugin('reload', 'Owner')
registerDefaultPlugin('enable', 'Owner')
registerDefaultPlugin('disable', 'Owner')
registerDefaultPlugin('unignore', 'Admin')
registerDefaultPlugin('capabilities', 'User')
registerDefaultPlugin('addcapability', 'Admin')
registerDefaultPlugin('removecapability', 'Admin')

class Owner(callbacks.Plugin):
    """Owner-only commands for core Supybot. This is a core Supybot module
    that should not be removed!"""
    # This plugin must be first; its priority must be lowest; otherwise odd
    # things will happen when adding callbacks.
    def __init__(self, irc=None):
        if irc is not None:
            assert not irc.getCallback(self.name())
        self.__parent = super(Owner, self)
        self.__parent.__init__(irc)
        # Setup command flood detection.
        self.commands = ircutils.FloodQueue(conf.supybot.abuse.flood.interval())
        conf.supybot.abuse.flood.interval.addCallback(self.setFloodQueueTimeout)
        # Setup plugins and default plugins for commands.
        #
        # This needs to be done before we connect to any networks so that the
        # children of supybot.plugins (the actual plugins) exist and can be
        # loaded.
        for (name, s) in registry._cache.items():
            if 'alwaysLoadDefault' in name or 'alwaysLoadImportant' in name:
                continue
            if name.startswith('supybot.plugins'):
                try:
                    (_, _, name) = registry.split(name)
                except ValueError: # unpack list of wrong size.
                    continue
                # This is just for the prettiness of the configuration file.
                # There are no plugins that are all-lowercase, so we'll at
                # least attempt to capitalize them.
                if name == name.lower():
                    name = name.capitalize()
                conf.registerPlugin(name)
            if name.startswith('supybot.commands.defaultPlugins'):
                try:
                    (_, _, _, name) = registry.split(name)
                except ValueError: # unpack list of wrong size.
                    continue
                registerDefaultPlugin(name, s)
        # Setup Irc objects, connected to networks.  If world.ircs is already
        # populated, chances are that we're being reloaded, so don't do this.
        if not world.ircs:
            for network in conf.supybot.networks():
                try:
                    self._connect(network)
                except socket.error as e:
                    self.log.error('Could not connect to %s: %s.', network, e)
                except Exception as e:
                    self.log.exception('Exception connecting to %s:', network)
                    self.log.error('Could not connect to %s: %s.', network, e)

    def callPrecedence(self, irc):
        return ([], [cb for cb in irc.callbacks if cb is not self])

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG' and not world.testing:
            if ircutils.strEqual(msg.args[0], irc.nick):
                self.log.warning('Tried to send a message to myself: %r.', msg)
                return None
        return msg

    def reset(self):
        # This has to be done somewhere, I figure here is as good place as any.
        callbacks.IrcObjectProxy._mores.clear()
        self.__parent.reset()

    def _connect(self, network, serverPort=None, password='', ssl=False):
        try:
            group = conf.supybot.networks.get(network)
            group.servers()[0]
        except (registry.NonExistentRegistryEntry, IndexError):
            if serverPort is None:
                raise ValueError('connect requires a (server, port) ' \
                                  'if the network is not registered.')
            conf.registerNetwork(network, password, ssl)
            server = '%s:%s' % serverPort
            conf.supybot.networks.get(network).servers.append(server)
            assert conf.supybot.networks.get(network).servers(), \
                   'No servers are set for the %s network.' % network
        self.log.debug('Creating new Irc for %s.', network)
        newIrc = irclib.Irc(network)
        driver = drivers.newDriver(newIrc)
        self._loadPlugins(newIrc)
        return newIrc

    def _loadPlugins(self, irc):
        self.log.debug('Loading plugins (connecting to %s).', irc.network)
        alwaysLoadImportant = conf.supybot.plugins.alwaysLoadImportant()
        important = conf.supybot.commands.defaultPlugins.importantPlugins()
        for (name, value) in conf.supybot.plugins.getValues(fullNames=False):
            if irc.getCallback(name) is None:
                load = value()
                if not load and name in important:
                    if alwaysLoadImportant:
                        s = '%s is configured not to be loaded, but is being '\
                            'loaded anyway because ' \
                            'supybot.plugins.alwaysLoadImportant is True.'
                        self.log.warning(s, name)
                        load = True
                if load:
                    # We don't load plugins that don't start with a capital
                    # letter.
                    if name[0].isupper() and not irc.getCallback(name):
                        # This is debug because each log logs its beginning.
                        self.log.debug('Loading %s.', name)
                        try:
                            m = plugin.loadPluginModule(name,
                                                        ignoreDeprecation=True)
                            plugin.loadPluginClass(irc, m)
                        except callbacks.Error as e:
                            # This is just an error message.
                            log.warning(str(e))
                        except plugins.NoSuitableDatabase as e:
                            s = 'Failed to load %s: no suitable database(%s).' % (name, e)
                            log.warning(s)
                        except ImportError as e:
                            e = str(e)
                            if e.endswith(name):
                                s = 'Failed to load {0}: No plugin named {0} exists.'.format(
                                    utils.str.dqrepr(name))
                            elif "No module named 'config'" in e:
                                s = ("Failed to load %s: This plugin may be incompatible "
                                     "with your current Python version." % name)
                            else:
                                s = 'Failed to load %s: import error (%s).' % (name, e)
                            log.warning(s)
                        except Exception as e:
                            log.exception('Failed to load %s:', name)
                else:
                    # Let's import the module so configuration is preserved.
                    try:
                        _ = plugin.loadPluginModule(name)
                    except Exception as e:
                        log.debug('Attempted to load %s to preserve its '
                                  'configuration, but load failed: %s',
                                  name, e)
        world.starting = False

    def do376(self, irc, msg):
        msgs = conf.supybot.networks.get(irc.network).channels.joins()
        if msgs:
            for msg in msgs:
                irc.queueMsg(msg)
    do422 = do377 = do376

    def setFloodQueueTimeout(self, *args, **kwargs):
        self.commands.timeout = conf.supybot.abuse.flood.interval()

    def doBatch(self, irc, msg):
        if not conf.supybot.protocols.irc.experimentalExtensions():
            return

        batch = msg.tagged('batch') # Always not-None on a BATCH message

        if msg.args[0].startswith('+'):
            # Start of a batch, we're not interested yet.
            return
        if batch.type != 'draft/multiline':
            # This is not a multiline batch, also not interested.
            return

        assert msg.args[0].startswith("-"), (
            "BATCH's first argument should start with either - or +, but "
            "it is %s."
        ) % msg.args[0]
        # End of multiline batch. It may be a long command.

        payloads = []
        first_privmsg = None

        for message in batch.messages:
            if message.command != "PRIVMSG":
                # We're only interested in PRIVMSGs for the payloads.
                # (eg. exclude NOTICE)
                continue
            elif not payloads:
                # This is the first PRIVMSG of the batch
                first_privmsg = message
                payloads.append(message.args[1])
            elif 'draft/multiline-concat' in message.server_tags:
                # This message is not a new line, but the continuation
                # of the previous one.
                payloads.append(message.args[1])
            else:
                # New line; stop here. We're not processing extra lines
                # either as the rest of the command or as new commands.
                # This may change in the future.
                break

        payload = ''.join(payloads)
        if not payload:
            self.log.error(
                'Got empty multiline payload. This is a bug, please '
                'report it along with logs.'
            )
            return

        assert first_privmsg, "This shouldn't be None unless payload is empty"

        # Let's build a synthetic message from the various parts of the
        # batch, to look like the multiline batch was a single (large)
        # PRIVMSG:
        # * copy the tags and server tags of the 'BATCH +' command,
        # * copy the prefix and channel of any of the PRIVMSGs
        #   inside the batch
        # * create a new args[1]
        target = first_privmsg.args[0]
        synthetic_msg = ircmsgs.IrcMsg(
            msg=batch.messages[0],  # tags, server_tags, time
            prefix=first_privmsg.prefix,
            command='PRIVMSG',
            args=(target, payload)
        )

        self._doPrivmsgs(irc, synthetic_msg)

    def doPrivmsg(self, irc, msg):
        if conf.supybot.protocols.irc.experimentalExtensions():
            if 'batch' in msg.server_tags \
                    and any(batch.type =='draft/multiline'
                            for batch in irc.state.getParentBatches(msg)):
                # We will handle the message in doBatch when the entire batch ends.
                return

        self._doPrivmsgs(irc, msg)

    def _doPrivmsgs(self, irc, msg):
        """If the given message is a command, triggers Limnoria's
        command-dispatching for that command.

        Takes the same arguments as ``doPrivmsg`` would, but ``msg`` can
        potentially be an artificial message synthesized in doBatch
        from a multiline batch.

        Usually, a command is a single message, so ``payload=msg.params[0]``
        However, when ``msg`` is part of a multiline message, the payload
        is the concatenation of multiple messages.
        See <https://ircv3.net/specs/extensions/multiline>.
        """
        assert self is irc.callbacks[0], \
               'Owner isn\'t first callback: %r' % irc.callbacks
        if ircmsgs.isCtcp(msg):
            return

        s = callbacks.addressed(irc, msg)
        if s:
            ignored = ircdb.checkIgnored(msg.prefix)
            if ignored:
                self.log.info('Ignoring command from %s.', msg.prefix)
                return
            maximum = conf.supybot.abuse.flood.command.maximum()
            self.commands.enqueue(msg)
            if conf.supybot.abuse.flood.command() \
               and self.commands.len(msg) > maximum \
               and not ircdb.checkCapability(msg.prefix, 'trusted'):
                punishment = conf.supybot.abuse.flood.command.punishment()
                banmask = conf.supybot.protocols.irc.banmask \
                        .makeBanmask(msg.prefix)
                self.log.info('Ignoring %s for %s seconds due to an apparent '
                              'command flood.', banmask, punishment)
                ircdb.ignores.add(banmask, time.time() + punishment)
                if conf.supybot.abuse.flood.command.notify():
                    irc.reply('You\'ve given me %s commands within the last '
                              '%i seconds; I\'m now ignoring you for %s.' %
                              (maximum,
                               conf.supybot.abuse.flood.interval(),
                               utils.timeElapsed(punishment, seconds=False)))
                return
            try:
                tokens = callbacks.tokenize(s, channel=msg.channel,
                                            network=irc.network)
                self.Proxy(irc, msg, tokens)
            except SyntaxError as e:
                if conf.supybot.reply.error.detailed():
                    irc.error(str(e))
                else:
                    irc.replyError(msg=msg)
                    self.log.info('Syntax error: %s', e)

    def logmark(self, irc, msg, args, text):
        """<text>

        Logs <text> to the global Supybot log at critical priority.  Useful for
        marking logfiles for later searching.
        """
        self.log.critical(text)
        irc.replySuccess()
    logmark = wrap(logmark, ['text'])

    def announce(self, irc, msg, args, text):
        """<text>

        Sends <text> to all channels the bot is currently on and not
        lobotomized in.
        """
        u = ircdb.users.getUser(msg.prefix)

        template = self.registryValue('announceFormat')

        text = ircutils.standardSubstitute(
            irc, msg, template, env={'owner': u.name, 'text': text})

        for channel in irc.state.channels:
            c = ircdb.channels.getChannel(channel)
            if not c.lobotomized:
                irc.queueMsg(ircmsgs.privmsg(channel, text))

        irc.noReply()
    announce = wrap(announce, ['text'])

    def defaultplugin(self, irc, msg, args, optlist, command, plugin):
        """[--remove] <command> [<plugin>]

        Sets the default plugin for <command> to <plugin>.  If --remove is
        given, removes the current default plugin for <command>.  If no plugin
        is given, returns the current default plugin set for <command>.  See
        also, supybot.commands.defaultPlugins.importantPlugins.
        """
        remove = False
        for (option, arg) in optlist:
            if option == 'remove':
                remove = True
        (_, cbs) = irc.findCallbacksForArgs([command])
        if remove:
            try:
                conf.supybot.commands.defaultPlugins.unregister(command)
                irc.replySuccess()
            except registry.NonExistentRegistryEntry:
                s = 'I don\'t have a default plugin set for that command.'
                irc.error(s)
        elif not cbs:
            irc.errorInvalid('command', command)
        elif plugin:
            if not plugin.isCommand(command):
                irc.errorInvalid('command in the %s plugin' % plugin.name(),
                                 command)
            registerDefaultPlugin(command, plugin.name())
            irc.replySuccess()
        else:
            try:
                irc.reply(conf.supybot.commands.defaultPlugins.get(command)())
            except registry.NonExistentRegistryEntry:
                s = 'I don\'t have a default plugin set for that command.'
                irc.error(s)
    defaultplugin = wrap(defaultplugin, [getopts({'remove': ''}),
                                         'commandName',
                                         additional('plugin')])

    def ircquote(self, irc, msg, args, s):
        """<string to be sent to the server>

        Sends the raw string given to the server.
        """
        try:
            m = ircmsgs.IrcMsg(s)
        except Exception as e:
            irc.error(utils.exnToString(e))
        else:
            irc.queueMsg(m)
            irc.noReply()
    ircquote = wrap(ircquote, ['text'])

    def quit(self, irc, msg, args, text):
        """[<text>]

        Exits the bot with the QUIT message <text>.  If <text> is not given,
        the default quit message (supybot.plugins.Owner.quitMsg) will be used.
        If there is no default quitMsg set, your nick will be used. The standard
        substitutions ($version, $nick, etc.) are all handled appropriately.
        """
        text = text or self.registryValue('quitMsg') or msg.nick
        text = ircutils.standardSubstitute(irc, msg, text)
        irc.noReply()
        m = ircmsgs.quit(text)
        world.upkeep()
        for irc in world.ircs[:]:
            irc.queueMsg(m)
            irc.die()
    quit = wrap(quit, [additional('text')])

    def flush(self, irc, msg, args):
        """takes no arguments

        Runs all the periodic flushers in world.flushers.  This includes
        flushing all logs and all configuration changes to disk.
        """
        world.flush()
        irc.replySuccess()
    flush = wrap(flush)

    def upkeep(self, irc, msg, args, level):
        """[<level>]

        Runs the standard upkeep stuff (flushes and gc.collects()).  If given
        a level, runs that level of upkeep (currently, the only supported
        level is "high", which causes the bot to flush a lot of caches as well
        as do normal upkeep stuff).
        """
        L = []
        if level == 'high':
            L.append(format('Regexp cache flushed: %n cleared.',
                            (len(re._cache), 'regexp')))
            re.purge()
            L.append(format('Pattern cache flushed: %n cleared.',
                            (len(ircutils._patternCache), 'compiled pattern')))
            ircutils._patternCache.clear()
            L.append(format('hostmaskPatternEqual cache flushed: %n cleared.',
                            (len(ircutils._hostmaskPatternEqualCache),
                             'result')))
            ircutils._hostmaskPatternEqualCache.clear()
            L.append(format('ircdb username cache flushed: %n cleared.',
                            (len(ircdb.users._nameCache),
                             'username to id mapping')))
            ircdb.users._nameCache.clear()
            L.append(format('ircdb hostmask cache flushed: %n cleared.',
                            (len(ircdb.users._hostmaskCache),
                            'hostmask to id mapping')))
            ircdb.users._hostmaskCache.clear()
            L.append(format('linecache line cache flushed: %n cleared.',
                            (len(linecache.cache), 'line')))
            linecache.clearcache()
            if minisix.PY2:
                sys.exc_clear()
        collected = world.upkeep()
        if gc.garbage:
            L.append('Garbage!  %r.' % gc.garbage)
        if collected is not None:
            # Some time between 5.2 and 7.1, Pypy (3?) started returning None
            # when gc.collect() is called.
            L.append(format('%n collected.', (collected, 'object')))
        if L:
            irc.reply('  '.join(L))
        else:
            irc.replySuccess()
    upkeep = wrap(upkeep, [additional(('literal', ['high']))])

    def load(self, irc, msg, args, optlist, name):
        """[--deprecated] <plugin>

        Loads the plugin <plugin> from any of the directories in
        conf.supybot.directories.plugins; usually this includes the main
        installed directory and 'plugins' in the current directory.
        --deprecated is necessary if you wish to load deprecated plugins.
        """
        ignoreDeprecation = False
        for (option, argument) in optlist:
            if option == 'deprecated':
                ignoreDeprecation = True
        if name.endswith('.py'):
            name = name[:-3]
        if irc.getCallback(name):
            irc.error('%s is already loaded.' % name.capitalize())
            return
        try:
            module = plugin.loadPluginModule(name, ignoreDeprecation)
        except plugin.Deprecated:
            irc.error('%s is deprecated.  Use --deprecated '
                      'to force it to load.' % name.capitalize())
            return
        except ImportError as e:
            if str(e).endswith(name):
                irc.error('No plugin named %s exists.' % utils.str.dqrepr(name))
            elif "No module named 'config'" in str(e):
                 irc.error('This plugin may be incompatible with your current Python '
                           'version. Try running 2to3 on it.')
            else:
                irc.error(str(e))
            return
        cb = plugin.loadPluginClass(irc, module)
        name = cb.name() # Let's normalize this.
        conf.registerPlugin(name, True)
        irc.replySuccess()
    load = wrap(load, [getopts({'deprecated': ''}), 'something'])

    def reload(self, irc, msg, args, name):
        """<plugin>

        Unloads and subsequently reloads the plugin by name; use the 'list'
        command to see a list of the currently loaded plugins.
        """
        if ircutils.strEqual(name, self.name()):
            irc.error('You can\'t reload the %s plugin.' % name)
            return
        callbacks = irc.removeCallback(name)
        if callbacks:
            module = sys.modules[callbacks[0].__module__]
            if hasattr(module, 'reload'):
                x = module.reload()
            try:
                module = plugin.loadPluginModule(name)
                if hasattr(module, 'reload') and 'x' in locals():
                    module.reload(x)
                if hasattr(module, 'config'):
                    from importlib import reload
                    reload(module.config)
                for callback in callbacks:
                    callback.die()
                    del callback
                gc.collect() # This makes sure the callback is collected.
                callback = plugin.loadPluginClass(irc, module)
                irc.replySuccess()
            except ImportError:
                for callback in callbacks:
                    irc.addCallback(callback)
                irc.error('No plugin named %s exists.' % name)
        else:
            irc.error('There was no plugin %s.' % name)
    reload = wrap(reload, ['something'])

    def unload(self, irc, msg, args, name):
        """<plugin>

        Unloads the callback by name; use the 'list' command to see a list
        of the currently loaded plugins.  Obviously, the Owner plugin can't
        be unloaded.
        """
        if ircutils.strEqual(name, self.name()):
            irc.error('You can\'t unload the %s plugin.' % name)
            return
        # Let's do this so even if the plugin isn't currently loaded, it doesn't
        # stay attempting to load.
        old_callback = irc.getCallback(name)
        if old_callback:
            # Normalize the plugin case to prevent duplicate registration
            # entries, https://github.com/ProgVal/Limnoria/issues/1295
            name = old_callback.name()
            conf.registerPlugin(name, False)
            callbacks = irc.removeCallback(name)
            if callbacks:
                for callback in callbacks:
                    callback.die()
                    del callback
                gc.collect()
                irc.replySuccess()
                return
        irc.error('There was no plugin %s.' % name)
    unload = wrap(unload, ['something'])

    def defaultcapability(self, irc, msg, args, action, capability):
        """{add|remove} <capability>

        Adds or removes (according to the first argument) <capability> from the
        default capabilities given to users (the configuration variable
        supybot.capabilities stores these).
        """
        if action == 'add':
            conf.supybot.capabilities().add(capability)
            irc.replySuccess()
        elif action == 'remove':
            try:
                conf.supybot.capabilities().remove(capability)
                irc.replySuccess()
            except KeyError:
                if ircdb.isAntiCapability(capability):
                    irc.error('That capability wasn\'t in '
                              'supybot.capabilities.')
                else:
                    anticap = ircdb.makeAntiCapability(capability)
                    conf.supybot.capabilities().add(anticap)
                    irc.replySuccess()
    defaultcapability = wrap(defaultcapability,
                             [('literal', ['add','remove']), 'capability'])

    def disable(self, irc, msg, args, plugin, command):
        """[<plugin>] <command>

        Disables the command <command> for all users (including the owners).
        If <plugin> is given, only disables the <command> from <plugin>.  If
        you want to disable a command for most users but not for yourself, set
        a default capability of -plugin.command or -command (if you want to
        disable the command in all plugins).
        """
        if command in ('enable', 'identify'):
            irc.error('You can\'t disable %s.' % command)
            return
        if plugin:
            if plugin.isCommand(command):
                pluginCommand = '%s.%s' % (plugin.name(), command)
                conf.supybot.commands.disabled().add(pluginCommand)
                plugin._disabled.add(command, plugin.name())
            else:
                irc.error('%s is not a command in the %s plugin.' %
                          (command, plugin.name()))
                return
        else:
            conf.supybot.commands.disabled().add(command)
            self._disabled.add(command)
        irc.replySuccess()
    disable = wrap(disable, [optional('plugin'), 'commandName'])

    def enable(self, irc, msg, args, plugin, command):
        """[<plugin>] <command>

        Enables the command <command> for all users.  If <plugin>
        if given, only enables the <command> from <plugin>.  This command is
        the inverse of disable.
        """
        try:
            if plugin:
                plugin._disabled.remove(command, plugin.name())
                command = '%s.%s' % (plugin.name(), command)
            else:
                self._disabled.remove(command)
            conf.supybot.commands.disabled().remove(command)
            irc.replySuccess()
        except KeyError:
            irc.error('That command wasn\'t disabled.')
    enable = wrap(enable, [optional('plugin'), 'commandName'])

    def rename(self, irc, msg, args, command_plugin, command, newName):
        """<plugin> <command> <new name>

        Renames <command> in <plugin> to the <new name>.
        """
        if not command_plugin.isCommand(command):
            what = 'command in the %s plugin' % command_plugin.name()
            irc.errorInvalid(what, command)
        if hasattr(command_plugin, newName):
            irc.error('The %s plugin already has an attribute named %s.' %
                      (command_plugin, newName))
            return
        plugin.registerRename(command_plugin.name(), command, newName)
        plugin.renameCommand(command_plugin, command, newName)
        irc.replySuccess()
    rename = wrap(rename, ['plugin', 'commandName', 'commandName'])

    def unrename(self, irc, msg, args, plugin):
        """<plugin>

        Removes all renames in <plugin>.  The plugin will be reloaded after
        this command is run.
        """
        try:
            conf.supybot.commands.renames.unregister(plugin.name())
        except registry.NonExistentRegistryEntry:
            irc.errorInvalid('plugin', plugin.name())
        self.reload(irc, msg, [plugin.name()]) # This makes the replySuccess.
    unrename = wrap(unrename, ['plugin'])

    def reloadlocale(self, irc, msg, args):
        """takes no argument

        Reloads the locale of the bot."""
        i18n.reloadLocales()
        irc.replySuccess()

Class = Owner

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
