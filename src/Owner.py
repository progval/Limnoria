#!/usr/bin/env python

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

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

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
import supybot.irclib as irclib
import supybot.drivers as drivers
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

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
            log.warning('Invalid plugin directory: %r; removing.', dir)
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
            raise Deprecated, 'Attempted to load deprecated plugin %r' % name
    if module.__name__ in sys.modules:
        sys.modules[module.__name__] = module
    linecache.checkcache()
    return module

def loadPluginClass(irc, module, register=None):
    """Loads the plugin Class from the given module into the given Irc."""
    try:
        cb = module.Class()
    except AttributeError:
        raise callbacks.Error, 'This plugin module doesn\'t have a "Class" ' \
                               'attribute to specify which plugin should be ' \
                               'instantiated.  If you didn\'t write this ' \
                               'plugin, but received it with Supybot, file ' \
                               'a bug with us about this error.'
    name = cb.name()
    public = True
    if hasattr(cb, 'public'):
        public = cb.public
    conf.registerPlugin(name, register, public)
    assert not irc.getCallback(name)
    irc.addCallback(cb)
    return cb

conf.registerPlugin('Owner', True)
conf.supybot.plugins.Owner.register('public', registry.Boolean(True,
    """Determines whether this plugin is publicly visible."""))

###
# supybot.commands.
###

conf.registerGroup(conf.supybot.commands, 'defaultPlugins')
conf.supybot.commands.defaultPlugins.help = utils.normalizeWhitespace("""
Determines what commands have default plugins set, and which plugins are set to
be the default for each of those commands.""".strip())

def registerDefaultPlugin(command, plugin):
    command = callbacks.canonicalName(command)
    conf.registerGlobalValue(conf.supybot.commands.defaultPlugins,
                             command, registry.String(plugin, ''))
    # This must be set, or the quotes won't be removed.
    conf.supybot.commands.defaultPlugins.get(command).set(plugin)

registerDefaultPlugin('ignore', 'Admin')
registerDefaultPlugin('unignore', 'Admin')
registerDefaultPlugin('addcapability', 'Admin')
registerDefaultPlugin('removecapability', 'Admin')
registerDefaultPlugin('list', 'Misc')
registerDefaultPlugin('help', 'Misc')
registerDefaultPlugin('reload', 'Owner')
registerDefaultPlugin('capabilities', 'User')

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

    def __call__(self, irc, msg, args):
        text = privmsgs.getArgs(args)
        log.critical(text)
        irc.replySuccess()

    def __getattr__(self, attr):
        return getattr(self.log, attr)


class Owner(privmsgs.CapabilityCheckingPrivmsg):
    # This plugin must be first; its priority must be lowest; otherwise odd
    # things will happen when adding callbacks.
    priority = ~sys.maxint-1 # This must be first!
    capability = 'owner'
    _srcPlugins = ircutils.IrcSet(('Admin', 'Channel', 'Config',
                                   'Misc', 'Owner', 'User'))
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        # Setup log object/command.
        self.log = LogProxy(self.log)
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

    def _getIrc(self, network):
        network = network.lower()
        for irc in world.ircs:
            if irc.network.lower() == network:
                return irc
        return None

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG' and not world.testing:
            if ircutils.strEqual(msg.args[0], irc.nick):
                self.log.warning('Tried to send a message to myself: %r.', msg)
                return None
        return msg
    
    def isCommand(self, methodName):
        return methodName == 'log' or \
               privmsgs.CapabilityCheckingPrivmsg.isCommand(self, methodName)

    def reset(self):
        # This has to be done somewhere, I figure here is as good place as any.
        callbacks.Privmsg._mores.clear()
        privmsgs.CapabilityCheckingPrivmsg.reset(self)

    def do001(self, irc, msg):
        self.log.info('Loading plugins.')
        alwaysLoadSrcPlugins = conf.supybot.plugins.alwaysLoadDefault()
        for (name, value) in conf.supybot.plugins.getValues(fullNames=False):
            if name.lower() in ('owner', 'alwaysloaddefault'):
                continue
            if irc.getCallback(name) is None:
                load = value()
                if not load and name in self._srcPlugins:
                    if alwaysLoadSrcPlugins:
                        s = '%s is configured not to be loaded, but is being '\
                            'loaded anyway because ' \
                            'supybot.plugins.alwaysLoadDefault is True.'
                        self.log.warning(s, name)
                        load = True
                if load:
                    if not irc.getCallback(name):
                        # This is debug because each log logs its beginning.
                        self.log.debug('Loading %s.' % name)
                        try:
                            m = loadPluginModule(name)
                            loadPluginClass(irc, m)
                        except callbacks.Error, e:
                            # This is just an error message.
                            log.warning(str(e))
                        except ImportError, e:
                            log.warning('Failed to load %s: %s', name, e)
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
                        log.info('Attempted to load %s to preserve its '
                                 'configuration, but load failed: %s',
                                 name, e)
        world.starting = False

    def disambiguate(self, irc, tokens, ambiguousCommands=None):
        """Disambiguates the given tokens based on the plugins loaded and
           commands available in the given irc.  Returns a dictionary of
           ambiguous commands, mapping the command to the plugins it's
           available in."""
        if ambiguousCommands is None:
            ambiguousCommands = {}
        if tokens:
            command = callbacks.canonicalName(tokens[0])
            try:
                plugin = conf.supybot.commands.defaultPlugins.get(command)()
                if plugin and plugin != '(Unused)':
                    tokens.insert(0, plugin)
                else:
                    raise registry.NonExistentRegistryEntry
            except registry.NonExistentRegistryEntry:
                cbs = callbacks.findCallbackForCommand(irc, command)
                if len(cbs) > 1:
                    names = [cb.name() for cb in cbs]
                    srcs = [name for name in names if name in self._srcPlugins]
                    if len(srcs) == 1:
                        if callbacks.canonicalName(name) != command:
                            # We don't insert the dispatcher name here because
                            # it's handled later.  Man, this stuff is a mess.
                            tokens.insert(0, srcs[0])
                    elif command not in map(callbacks.canonicalName, names):
                        ambiguousCommands[command] = names
            for elt in tokens:
                if isinstance(elt, list):
                    self.disambiguate(irc, elt, ambiguousCommands)
        return ambiguousCommands

    def processTokens(self, irc, msg, tokens):
        ambiguousCommands = self.disambiguate(irc, tokens)
        if ambiguousCommands:
            if len(ambiguousCommands) == 1: # Common case.
                (command, names) = ambiguousCommands.popitem()
                names.sort()
                s = 'The command %r is available in the %s plugins.  ' \
                    'Please specify the plugin whose command you ' \
                    'wish to call by using its name as a command ' \
                    'before calling it.' % \
                    (command, utils.commaAndify(names))
            else:
                L = []
                for (command, names) in ambiguousCommands.iteritems():
                    names.sort()
                    L.append('The command %r is available in the %s '
                             'plugins' %
                             (command, utils.commaAndify(names)))
                s = '%s; please specify from which plugins to ' \
                    'call these commands.' % '; '.join(L)
            irc.queueMsg(callbacks.error(msg, s))
        else:
            callbacks.IrcObjectProxy(irc, msg, tokens)

    def do376(self, irc, msg):
        channels = ircutils.IrcSet(conf.supybot.channels())
        channels |= conf.supybot.networks.get(irc.network).channels()
        channels = list(channels)
        if not channels:
            return
        utils.sortBy(lambda s: ',' not in s, channels)
        keys = []
        chans = []
        for channel in channels:
            if ',' in channel:
                (channel, key) = channel.split(',', 1)
                chans.append(channel)
                keys.append(key)
            else:
                chans.append(channel)
        irc.queueMsg(ircmsgs.joins(chans, keys))
    do422 = do377 = do376

    def doPrivmsg(self, irc, msg):
        callbacks.Privmsg.handled = False
        callbacks.Privmsg.errored = False
        if ircdb.checkIgnored(msg.prefix):
            return
        s = callbacks.addressed(irc.nick, msg)
        if s:
            brackets = conf.supybot.reply.brackets.get(msg.args[0])()
            try:
                tokens = callbacks.tokenize(s, brackets=brackets)
                if tokens and isinstance(tokens[0], list):
                    s = 'The command called may not be the result ' \
                        'of a nested command.'
                    irc.queueMsg(callbacks.error(msg, s))
                    return
                self.processTokens(irc, msg, tokens)
            except SyntaxError, e:
                callbacks.Privmsg.errored = True
                irc.queueMsg(callbacks.error(msg, str(e)))
                return

    if conf.allowEval:
        _evalEnv = {'_': None,
                    '__': None,
                    '___': None,
                    }
        _evalEnv.update(globals())
        def eval(self, irc, msg, args):
            """<expression>

            Evaluates <expression> (which should be a Python expression) and
            returns its value.  If an exception is raised, reports the
            exception.
            """
            if conf.allowEval:
                s = privmsgs.getArgs(args)
                try:
                    self._evalEnv.update(locals())
                    x = eval(s, self._evalEnv, self._evalEnv)
                    self._evalEnv['___'] = self._evalEnv['__']
                    self._evalEnv['__'] = self._evalEnv['_']
                    self._evalEnv['_'] = x
                    irc.reply(repr(x))
                except SyntaxError, e:
                    irc.reply('%s: %r' % (utils.exnToString(e), s))
                except Exception, e:
                    irc.reply(utils.exnToString(e))
            else:
                # This should never happen, so I haven't bothered updating
                # this error string to say --allow-eval.
                irc.error('You must run Supybot with the --allow-eval '
                          'option for this command to be enabled.')

        def _exec(self, irc, msg, args):
            """<statement>

            Execs <code>.  Returns success if it didn't raise any exceptions.
            """
            if conf.allowEval:
                s = privmsgs.getArgs(args)
                try:
                    exec s
                    irc.replySuccess()
                except Exception, e:
                    irc.reply(utils.exnToString(e))
            else:
                # This should never happen.
                irc.error('You must run Supybot with the --allow-eval '
                          'option for this command to be enabled.')
    else:
        def eval(self, irc, msg, args):
            """Run your bot with --allow-eval if you want this to work."""
            irc.error('You must give your bot the --allow-eval option for '
                      'this command to be enabled.')
        _exec = eval

    def announce(self, irc, msg, args):
        """<text>

        Sends <text> to all channels the bot is currently on and not
        lobotomized in.
        """
        text = privmsgs.getArgs(args)
        u = ircdb.users.getUser(msg.prefix)
        text = 'Announcement from my owner (%s): %s' % (u.name, text)
        for channel in irc.state.channels:
            c = ircdb.channels.getChannel(channel)
            if not c.lobotomized:
                irc.queueMsg(ircmsgs.privmsg(channel, text))

    def defaultplugin(self, irc, msg, args):
        """[--remove] <command> [<plugin>]

        Sets the default plugin for <command> to <plugin>.  If --remove is
        given, removes the current default plugin for <command>.  If no plugin
        is given, returns the current default plugin set for <command>.
        """
        remove = False
        (optlist, rest) = getopt.getopt(args, '', ['remove'])
        for (option, arg) in optlist:
            if option == '--remove':
                remove = True
        (command, plugin) = privmsgs.getArgs(rest, optional=1)
        command = callbacks.canonicalName(command)
        cbs = callbacks.findCallbackForCommand(irc, command)
        if remove:
            try:
                conf.supybot.commands.defaultPlugins.unregister(command)
                irc.replySuccess()
            except registry.NonExistentRegistryEntry:
                s = 'I don\'t have a default plugin set for that command.'
                irc.error(s)
        elif not cbs:
            irc.error('That\'s not a valid command.')
            return
        elif plugin:
            cb = irc.getCallback(plugin)
            if cb is None:
                irc.error('That\'s not a valid plugin.')
                return
            registerDefaultPlugin(command, plugin)
            irc.replySuccess()
        else:
            try:
                irc.reply(conf.supybot.commands.defaultPlugins.get(command)())
            except registry.NonExistentRegistryEntry:
                s = 'I don\'t have a default plugin set for that command.'
                irc.error(s)

    def ircquote(self, irc, msg, args):
        """<string to be sent to the server>

        Sends the raw string given to the server.
        """
        s = privmsgs.getArgs(args)
        try:
            m = ircmsgs.IrcMsg(s)
        except Exception, e:
            irc.error(utils.exnToString(e))
        else:
            irc.queueMsg(m)

    def quit(self, irc, msg, args):
        """[<text>]

        Exits the bot with the QUIT message <text>.  If <text> is not given,
        your nick will be substituted.
        """
        text = privmsgs.getArgs(args, required=0, optional=1)
        if not text:
            text = msg.nick
        m = ircmsgs.quit(text)
        world.upkeep()
        for irc in world.ircs[:]:
            irc.queueMsg(m)
            irc.die()

    def flush(self, irc, msg, args):
        """takes no arguments

        Runs all the periodic flushers in world.flushers.  This includes
        flushing all logs and all configuration changes to disk.
        """
        world.flush()
        irc.replySuccess()

    def upkeep(self, irc, msg, args):
        """[<level>]

        Runs the standard upkeep stuff (flushes and gc.collects()).  If given
        a level, runs that level of upkeep (currently, the only supported
        level is "high", which causes the bot to flush a lot of caches as well
        as do normal upkeep stuff.
        """
        level = privmsgs.getArgs(args, required=0, optional=1)
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
        collected = world.upkeep(scheduleNext=False)
        if gc.garbage:
            L.append('Garbage!  %r.' % gc.garbage)
        L.append('%s collected.' % utils.nItems('object', collected))
        irc.reply('  '.join(L))

    def load(self, irc, msg, args):
        """[--deprecated] <plugin>

        Loads the plugin <plugin> from any of the directories in
        conf.supybot.directories.plugins; usually this includes the main
        installed directory and 'plugins' in the current directory.
        --deprecated is necessary if you wish to load deprecated plugins.
        """
        (optlist, args) = getopt.getopt(args, '', ['deprecated'])
        ignoreDeprecation = False
        for (option, argument) in optlist:
            if option == '--deprecated':
                ignoreDeprecation = True
        name = privmsgs.getArgs(args)
        if name.endswith('.py'):
            name = name[:-3]
        if irc.getCallback(name):
            irc.error('That plugin is already loaded.')
            return
        try:
            module = loadPluginModule(name, ignoreDeprecation)
        except Deprecated:
            irc.error('That plugin is deprecated.  '
                      'Use --deprecated to force it to load.')
            return
        except ImportError, e:
            if name in str(e):
                irc.error('No plugin %s exists.' % name)
            else:
                irc.error(str(e))
            return
        cb = loadPluginClass(irc, module)
        name = cb.name() # Let's normalize this.
        conf.registerPlugin(name, True)
        irc.replySuccess()

    def reload(self, irc, msg, args):
        """<plugin>

        Unloads and subsequently reloads the plugin by name; use the 'list'
        command to see a list of the currently loaded plugins.
        """
        name = privmsgs.getArgs(args)
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

    def unload(self, irc, msg, args):
        """<plugin>

        Unloads the callback by name; use the 'list' command to see a list
        of the currently loaded callbacks.  Obviously, the Owner plugin can't
        be unloaded.
        """
        name = privmsgs.getArgs(args)
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

    def reconnect(self, irc, msg, args):
        """[<network>]

        Disconnects and then reconnects to <network>.  If no network is given,
        disconnects and then reconnects to the network the command was given
        on.
        """
        network = privmsgs.getArgs(args, required=0, optional=1)
        if network:
            badIrc = self._getIrc(network)
            if badIrc is None:
                irc.error('I\'m not currently connected on %s.' % network)
                return
        else:
            badIrc = irc
        try:
            badIrc.driver.reconnect()
            if badIrc != irc:
                irc.replySuccess()
        except AttributeError: # There's a cleaner way to do this, but I'm lazy.
            irc.error('I couldn\'t reconnect.  You should restart me instead.')

    def defaultcapability(self, irc, msg, args):
        """<add|remove> <capability>

        Adds or removes (according to the first argument) <capability> from the
        default capabilities given to users (the configuration variable
        supybot.capabilities stores these).
        """
        (action, capability) = privmsgs.getArgs(args, required=2)
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
        else:
            irc.error('That\'s not a valid action to take.  Valid actions '
                      'are "add" and "remove"')
            
    def disable(self, irc, msg, args):
        """[<plugin>] <command>

        Disables the command <command> for all users (including the owners).
        If <plugin> is given, only disables the <command> from <plugin>.  If
        you want to disable a command for most users but not for yourself, set
        a default capability of -plugin.command or -command (if you want to
        disable the command in all plugins).
        """
        (plugin, command) = privmsgs.getArgs(args, optional=1)
        if not command:
            (plugin, command) = (None, plugin)
            conf.supybot.commands.disabled().add(command)
        else:
            conf.supybot.commands.disabled().add('%s.%s' % (plugin, command))
        if command in ('enable', 'identify'):
            irc.error('You can\'t disable %s.' % command)
        else:
            self._disabled.add(command, plugin)
            irc.replySuccess()

    def enable(self, irc, msg, args):
        """[<plugin>] <command>

        Enables the command <command> for all users.  If <plugin>
        if given, only enables the <command> from <plugin>.  This command is
        the inverse of disable.
        """
        (plugin, command) = privmsgs.getArgs(args, optional=1)
        try:
            if not command:
                (plugin, command) = (None, plugin)
                conf.supybot.commands.disabled().remove(command)
            else:
                name = '%s.%s' % (plugin, command)
                conf.supybot.commands.disabled().remove(name)
            self._disabled.remove(command, plugin)
            irc.replySuccess()
        except KeyError:
            raise
            irc.error('That command wasn\'t disabled.')

    def rename(self, irc, msg, args):
        """<plugin> <command> <new name>

        Renames <command> in <plugin> to the <new name>.
        """
        (plugin, command, newName) = privmsgs.getArgs(args, required=3)
        name = callbacks.canonicalName(newName)
        if name != newName:
            irc.error('%s is a not a valid new command name.  '
                      'Try making it lowercase and removing - and _.' %newName)
            return
        cb = irc.getCallback(plugin)
        if cb is None:
            irc.error('%s is not a valid plugin.' % plugin)
            return
        if not cb.isCommand(command):
            s = '%s is not a valid command in the %s plugin.' % (name, plugin)
            irc.error(s)
            return
        if hasattr(cb, name):
            irc.error('The %s plugin already has an attribute named %s.' %
                      (plugin, name))
            return
        method = getattr(cb.__class__, command)
        setattr(cb.__class__, name, method)
        delattr(cb.__class__, command)
        irc.replySuccess()

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

    def connect(self, irc, msg, args):
        """<network> [<host[:port]>]

        Connects to another network at <host:port>.  If port is not provided, it
        defaults to 6667, the default port for IRC.
        """
        (network, server) = privmsgs.getArgs(args, optional=1)
        otherIrc = self._getIrc(network)
        if otherIrc is not None:
            irc.error('I\'m already connected to %s.' % network)
            return
        if server:
            if ':' in server:
                (server, port) = server.split(':')
                port = int(port)
            else:
                port = 6667
            serverPort = (server, port)
        else:
            try:
                serverPort = conf.supybot.networks.get(network).servers()[0]
            except (registry.NonExistentRegistryEntry, IndexError):
                irc.error('A server must be provided if the network is not '
                          'already registered.')
                return
        newIrc = self._connect(network, serverPort=serverPort)
        conf.supybot.networks().add(network)
        assert newIrc.callbacks is irc.callbacks, 'callbacks list is different'
        irc.replySuccess('Connection to %s initiated.' % network)

    def disconnect(self, irc, msg, args):
        """<network> [<quit message>]

        Disconnects and ceases to relay to and from the network represented by
        the network <network>.  If <quit message> is given, quits the network
        with the given quit message.
        """
        (network, quitMsg) = privmsgs.getArgs(args, optional=1)
        if not quitMsg:
            quitMsg = msg.nick
        otherIrc = self._getIrc(network)
        if otherIrc is not None:
            # replySuccess here, rather than lower, in case we're being
            # told to disconnect from the network we received the command on.
            irc.replySuccess()
            otherIrc.queueMsg(ircmsgs.quit(quitMsg))
            otherIrc.die()
        else:
            irc.error('I\'m not connected to %s.' % network, Raise=True)
        conf.supybot.networks().discard(network)


Class = Owner

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

