###
# Copyright (c) 2002-2004, Jeremiah Fincher
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
Provides commands useful to the owner of the bot; the commands here require
their caller to have the 'owner' capability.  This plugin is loaded by default.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.fix as fix

import gc
import os
import imp
import sre
import sys
import getopt
import socket
import logging
import linecache

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.irclib as irclib
import supybot.drivers as drivers
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks
import supybot.structures as structures

class Deprecated(ImportError):
    pass

def loadPluginModule(name, ignoreDeprecation=False):
    """Loads (and returns) the module for the plugin with the given name."""
    files = []
    pluginDirs = conf.supybot.directories.plugins()
    for dir in pluginDirs:
        try:
            files.extend(os.listdir(dir))
        except EnvironmentError: # OSError, IOError superclass.
            log.warning('Invalid plugin directory: %s; removing.',
                        utils.quoted(dir))
            conf.supybot.directories.plugins().remove(dir)
    loweredFiles = map(str.lower, files)
    try:
        index = loweredFiles.index(name.lower()+'.py')
        name = os.path.splitext(files[index])[0]
        if name in sys.modules:
            m = sys.modules[name]
            if not hasattr(m, 'Class'):
                raise ImportError, 'Module is not a plugin.'
    except ValueError: # We'd rather raise the ImportError, so we'll let go...
        pass
    moduleInfo = imp.find_module(name, pluginDirs)
    try:
        module = imp.load_module(name, *moduleInfo)
    except:
        if name in sys.modules:
            del sys.modules[name]
        raise
    if 'deprecated' in module.__dict__ and module.deprecated:
        if ignoreDeprecation:
            log.warning('Deprecated plugin loaded: %s', name)
        else:
            raise Deprecated, 'Attempted to load deprecated plugin %s' % \
                              utils.quoted(name)
    if module.__name__ in sys.modules:
        sys.modules[module.__name__] = module
    linecache.checkcache()
    return module

def loadPluginClass(irc, module, register=None):
    """Loads the plugin Class from the given module into the given Irc."""
    try:
        cb = module.Class()
    except AttributeError, e:
        if 'Class' in str(e):
            raise callbacks.Error, \
                  'This plugin module doesn\'t have a "Class" ' \
                  'attribute to specify which plugin should be ' \
                  'instantiated.  If you didn\'t write this ' \
                  'plugin, but received it with Supybot, file ' \
                  'a bug with us about this error.'
        else:
            raise
    plugin = cb.name()
    public = True
    if hasattr(cb, 'public'):
        public = cb.public
    conf.registerPlugin(plugin, register, public)
    assert not irc.getCallback(plugin)
    try:
        renames = registerRename(plugin)()
        if renames:
            for command in renames:
                v = registerRename(plugin, command)
                newName = v()
                assert newName
                renameCommand(cb, command, newName)
        else:
            conf.supybot.commands.renames.unregister(plugin)
    except registry.NonExistentRegistryEntry, e:
        pass # The plugin isn't there.
    irc.addCallback(cb)
    return cb

conf.registerPlugin('Owner', True)
conf.supybot.plugins.Owner.register('public', registry.Boolean(True,
    """Determines whether this plugin is publicly visible."""))

###
# supybot.commands.
###

conf.registerGroup(conf.supybot.commands, 'renames', orderAlphabetically=True)

def registerDefaultPlugin(command, plugin):
    command = callbacks.canonicalName(command)
    conf.registerGlobalValue(conf.supybot.commands.defaultPlugins,
                             command, registry.String(plugin, ''))
    # This must be set, or the quotes won't be removed.
    conf.supybot.commands.defaultPlugins.get(command).set(plugin)

def registerRename(plugin, command=None, newName=None):
    g = conf.registerGlobalValue(conf.supybot.commands.renames, plugin,
            registry.SpaceSeparatedSetOfStrings([], """Determines what commands
            in this plugin are to be renamed."""))
    if command is not None:
        g().add(command)
        v = conf.registerGlobalValue(g, command, registry.String('', ''))
        if newName is not None:
            v.setValue(newName) # In case it was already registered.
        return v
    else:
        return g

def renameCommand(cb, name, newName):
    assert not hasattr(cb, newName), 'Cannot rename over existing attributes.'
    assert newName == callbacks.canonicalName(newName), \
           'newName must already be canonicalized.'
    if name != newName:
        method = getattr(cb.__class__, name)
        setattr(cb.__class__, newName, method)
        delattr(cb.__class__, name)


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

class holder(object):
    pass

# This is used so we can support a "log" command as well as a "self.log"
# Logger.
class LogProxy(object):
    """<text>

    Logs <text> to the global Supybot log at critical priority.  Useful for
    marking logfiles for later searching.
    """
    __name__ = 'log' # Necessary for help.
    def __init__(self, log):
        self.log = log
        self.im_func = holder()
        self.im_func.func_name = 'log'

    def __call__(self, irc, msg, args, text):
        log.critical(text)
        irc.replySuccess()
    __call__ = wrap(__call__, ['text'])

    def __getattr__(self, attr):
        return getattr(self.log, attr)

conf.registerPlugin('Owner')
conf.registerGlobalValue(conf.supybot.plugins.Owner, 'quitMsg',
    registry.String('', """Determines what quit message will be used by default.
    If the quit command is called without a quit message, this will be used.  If
    this value is empty, the nick of the person giving the quit command will be
    used."""))

class Owner(privmsgs.CapabilityCheckingPrivmsg):
    # This plugin must be first; its priority must be lowest; otherwise odd
    # things will happen when adding callbacks.
    capability = 'owner'
    _srcPlugins = ircutils.IrcSet(('Admin', 'Channel', 'Config',
                                   'Misc', 'Owner', 'User'))
    def __init__(self, *args, **kwargs):
        self.__parent = super(Owner, self)
        self.__parent.__init__()
        # Setup log object/command.
        self.log = LogProxy(self.log)
        # Setup command flood detection.
        self.commands = ircutils.FloodQueue(60)
        # Setup exec command.
        setattr(self.__class__, 'exec', self.__class__._exec)
        # Setup Irc objects, connected to networks.  If world.ircs is already
        # populated, chances are that we're being reloaded, so don't do this.
        if not world.ircs:
            for network in conf.supybot.networks():
                try:
                    self._connect(network)
                except socket.error, e:
                    self.log.error('Could not connect to %s: %s.', network, e)
                except Exception, e:
                    self.log.exception('Exception connecting to %s:', network)
                    self.log.error('Could not connect to %s: %s.', network, e)
        # Setup plugins and default plugins for commands.
        for (name, s) in registry._cache.iteritems():
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

    def callPrecedence(self, irc):
        return ([], [cb for cb in irc.callbacks if cb is not self])

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG' and not world.testing:
            if ircutils.strEqual(msg.args[0], irc.nick):
                self.log.warning('Tried to send a message to myself: %r.', msg)
                return None
        return msg

    def isCommand(self, name):
        return name == 'log' or \
               self.__parent.isCommand(name)

    def reset(self):
        # This has to be done somewhere, I figure here is as good place as any.
        callbacks.Privmsg._mores.clear()
        self.__parent.reset()

    def _connect(self, network, serverPort=None):
        try:
            group = conf.supybot.networks.get(network)
            (server, port) = group.servers()[0]
        except (registry.NonExistentRegistryEntry, IndexError):
            if serverPort is None:
                raise ValueError, 'connect requires a (server, port) ' \
                                  'if the network is not registered.'
            conf.registerNetwork(network)
            serverS = '%s:%s' % serverPort
            conf.supybot.networks.get(network).servers.append(serverS)
            assert conf.supybot.networks.get(network).servers()
        self.log.info('Creating new Irc for %s.', network)
        newIrc = irclib.Irc(network)
        for irc in world.ircs:
            if irc != newIrc:
                newIrc.state.history = irc.state.history
        driver = drivers.newDriver(newIrc)
        return newIrc

    def do001(self, irc, msg):
        self.log.info('Loading plugins (connected to %s).', irc.network)
        alwaysLoadSrcPlugins = conf.supybot.plugins.alwaysLoadImportant()
        for (name, value) in conf.supybot.plugins.getValues(fullNames=False):
            if irc.getCallback(name) is None:
                load = value()
                # XXX This (_srcPlugins) should be changed to the configurable
                #     importantPlugins.
                if not load and name in self._srcPlugins:
                    if alwaysLoadSrcPlugins:
                        s = '%s is configured not to be loaded, but is being '\
                            'loaded anyway because ' \
                            'supybot.plugins.alwaysLoadImportant is True.'
                        self.log.warning(s, name)
                        load = True
                if load:
                    if not irc.getCallback(name):
                        # This is debug because each log logs its beginning.
                        self.log.debug('Loading %s.' % name)
                        try:
                            m = loadPluginModule(name, ignoreDeprecation=True)
                            loadPluginClass(irc, m)
                        except callbacks.Error, e:
                            # This is just an error message.
                            log.warning(str(e))
                        except ImportError, e:
                            log.warning('Failed to load %s: %s.', name, e)
                            if name in self._srcPlugins:
                                self.log.exception('Error loading %s:', name)
                                self.log.error('Error loading src/ plugin %s.  '
                                               'This is usually rather '
                                               'serious; these plugins are '
                                               'almost always be loaded.',name)
                        except Exception, e:
                            log.exception('Failed to load %s:', name)
                else:
                    # Let's import the module so configuration is preserved.
                    try:
                        _ = loadPluginModule(name)
                    except Exception, e:
                        log.debug('Attempted to load %s to preserve its '
                                  'configuration, but load failed: %s',
                                  name, e)
        world.starting = False

    def do376(self, irc, msg):
        networkGroup = conf.supybot.networks.get(irc.network)
        for channel in networkGroup.channels():
            irc.queueMsg(networkGroup.channels.join(channel))
    do422 = do377 = do376

    def doPrivmsg(self, irc, msg):
        assert self is irc.callbacks[0], 'Owner isn\'t first callback.'
        if ircmsgs.isCtcp(msg):
            return
        s = callbacks.addressed(irc.nick, msg)
        if s:
            ignored = ircdb.checkIgnored(msg.prefix)
            if ignored:
                self.log.info('Ignoring command from %s.' % msg.prefix)
                return
            try:
                tokens = callbacks.tokenize(s, channel=msg.args[0])
                self.Proxy(irc, msg, tokens)
            except SyntaxError, e:
                irc.queueMsg(callbacks.error(msg, str(e)))

    if conf.allowEval:
        _evalEnv = {'_': None,
                    '__': None,
                    '___': None,
                    }
        _evalEnv.update(globals())
        def eval(self, irc, msg, args, s):
            """<expression>

            Evaluates <expression> (which should be a Python expression) and
            returns its value.  If an exception is raised, reports the
            exception (and logs the traceback to the bot's logfile).
            """
            if conf.allowEval:
                try:
                    self._evalEnv.update(locals())
                    x = eval(s, self._evalEnv, self._evalEnv)
                    self._evalEnv['___'] = self._evalEnv['__']
                    self._evalEnv['__'] = self._evalEnv['_']
                    self._evalEnv['_'] = x
                    irc.reply(repr(x))
                except SyntaxError, e:
                    irc.reply('%s: %s' % (utils.exnToString(e),
                                          utils.quoted(s)))
                except Exception, e:
                    self.log.exception('Uncaught exception in Owner.eval.\n'
                                       'This is not a bug.  Please do not '
                                       'report it.')
                    irc.reply(utils.exnToString(e))
            else:
                # There's a potential that allowEval got changed after we were
                # loaded.  Let's be extra-special-safe.
                irc.error('You must run Supybot with the --allow-eval '
                          'option for this command to be enabled.')
        eval = wrap(eval, ['text'])

        def _exec(self, irc, msg, args, s):
            """<statement>

            Execs <code>.  Returns success if it didn't raise any exceptions.
            """
            if conf.allowEval:
                try:
                    exec s
                    irc.replySuccess()
                except Exception, e:
                    irc.reply(utils.exnToString(e))
            else:
                # There's a potential that allowEval got changed after we were
                # loaded.  Let's be extra-special-safe.
                irc.error('You must run Supybot with the --allow-eval '
                          'option for this command to be enabled.')
        _exec = wrap(_exec, ['text'])
    else:
        def eval(self, irc, msg, args):
            """Run your bot with --allow-eval if you want this to work."""
            irc.error('You must give your bot the --allow-eval option for '
                      'this command to be enabled.')
        _exec = eval

    def announce(self, irc, msg, args, text):
        """<text>

        Sends <text> to all channels the bot is currently on and not
        lobotomized in.
        """
        u = ircdb.users.getUser(msg.prefix)
        text = 'Announcement from my owner (%s): %s' % (u.name, text)
        for channel in irc.state.channels:
            c = ircdb.channels.getChannel(channel)
            if not c.lobotomized:
                irc.queueMsg(ircmsgs.privmsg(channel, text))
    announce = wrap(announce, ['text'])

    def defaultplugin(self, irc, msg, args, optlist, command, plugin):
        """[--remove] <command> [<plugin>]

        Sets the default plugin for <command> to <plugin>.  If --remove is
        given, removes the current default plugin for <command>.  If no plugin
        is given, returns the current default plugin set for <command>.
        """
        remove = False
        for (option, arg) in optlist:
            if option == 'remove':
                remove = True
        cbs = callbacks.findCallbackForCommand(irc, command)
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
                irc.errorInvalid('command in the %s plugin' % plugin, command)
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
        except Exception, e:
            irc.error(utils.exnToString(e))
        else:
            irc.queueMsg(m)
    ircquote = wrap(ircquote, ['text'])

    def quit(self, irc, msg, args, text):
        """[<text>]

        Exits the bot with the QUIT message <text>.  If <text> is not given,
        the default quit message (supybot.plugins.Owner.quitMsg) will be used.
        If there is no default quitMsg set, your nick will be used.
        """
        if not text:
            text = self.registryValue('quitMsg') or msg.nick
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
        as do normal upkeep stuff.
        """
        L = []
        if level == 'high':
            L.append('Regexp cache flushed: %s cleared.' %
                     utils.nItems('regexp', len(sre._cache)))
            sre.purge()
            L.append('Pattern cache flushed: %s cleared.' %
                     utils.nItems('compiled pattern',
                                  len(ircutils._patternCache)))
            ircutils._patternCache.clear()
            L.append('hostmaskPatternEqual cache flushed: %s cleared.' %
                     utils.nItems('result',
                                  len(ircutils._hostmaskPatternEqualCache)))
            ircutils._hostmaskPatternEqualCache.clear()
            L.append('ircdb username cache flushed: %s cleared.' %
                     utils.nItems('username to id mapping',
                                  len(ircdb.users._nameCache)))
            ircdb.users._nameCache.clear()
            L.append('ircdb hostmask cache flushed: %s cleared.' %
                     utils.nItems('hostmask to id mapping',
                                  len(ircdb.users._hostmaskCache)))
            ircdb.users._hostmaskCache.clear()
            L.append('linecache line cache flushed: %s cleared.' %
                     utils.nItems('line', len(linecache.cache)))
            linecache.clearcache()
            sys.exc_clear()
        collected = world.upkeep()
        if gc.garbage:
            L.append('Garbage!  %r.' % gc.garbage)
        L.append('%s collected.' % utils.nItems('object', collected))
        irc.reply('  '.join(L))
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
            module = loadPluginModule(name, ignoreDeprecation)
        except Deprecated:
            irc.error('%s is deprecated.  Use --deprecated '
                      'to force it to load.' % name.capitalize())
            return
        except ImportError, e:
            if name in str(e):
                irc.error('No plugin named %s exists.' % utils.dqrepr(name))
            else:
                irc.error(str(e))
            return
        cb = loadPluginClass(irc, module)
        name = cb.name() # Let's normalize this.
        conf.registerPlugin(name, True)
        irc.replySuccess()
    load = wrap(load, [getopts({'deprecated': ''}), 'something'])

    def reload(self, irc, msg, args, name):
        """<plugin>

        Unloads and subsequently reloads the plugin by name; use the 'list'
        command to see a list of the currently loaded plugins.
        """
        callbacks = irc.removeCallback(name)
        if callbacks:
            module = sys.modules[callbacks[0].__module__]
            if hasattr(module, 'reload'):
                x = module.reload()
            try:
                module = loadPluginModule(name)
                if hasattr(module, 'reload'):
                    module.reload(x)
                for callback in callbacks:
                    callback.die()
                    del callback
                gc.collect() # This makes sure the callback is collected.
                callback = loadPluginClass(irc, module)
                irc.replySuccess()
            except ImportError:
                for callback in callbacks:
                    irc.addCallback(callback)
                irc.error('No plugin %s exists.' % name)
        else:
            irc.error('There was no plugin %s.' % name)
    reload = wrap(reload, ['something'])

    def unload(self, irc, msg, args, name):
        """<plugin>

        Unloads the callback by name; use the 'list' command to see a list
        of the currently loaded callbacks.  Obviously, the Owner plugin can't
        be unloaded.
        """
        if ircutils.strEqual(name, self.name()):
            irc.error('You can\'t unload the %s plugin.' % name)
            return
        # Let's do this so even if the plugin isn't currently loaded, it doesn't
        # stay attempting to load.
        conf.registerPlugin(name, False)
        callbacks = irc.removeCallback(name)
        if callbacks:
            for callback in callbacks:
                callback.die()
                del callback
            gc.collect()
            irc.replySuccess()
        else:
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
            else:
                irc.error('%s is not a command in the %s plugin.' %
                          (command, plugin.name()))
                return
            self._disabled.add(command, plugin.name())
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
                command = '%s.%s' % (plugin.name(), command)
                self._disabled.remove(command, plugin.name())
            else:
                self._disabled.remove(command)
            conf.supybot.commands.disabled().remove(command)
            irc.replySuccess()
        except KeyError:
            irc.error('That command wasn\'t disabled.')
    enable = wrap(enable, [optional('plugin'), 'commandName'])

    def rename(self, irc, msg, args, plugin, command, newName):
        """<plugin> <command> <new name>

        Renames <command> in <plugin> to the <new name>.
        """
        if not plugin.isCommand(command):
            what = 'command in the %s plugin' % plugin.name()
            irc.errorInvalid(what, command)
        if hasattr(plugin, newName):
            irc.error('The %s plugin already has an attribute named %s.' %
                      (plugin, newName))
            return
        registerRename(plugin.name(), command, newName)
        renameCommand(plugin, command, newName)
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


Class = Owner

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

