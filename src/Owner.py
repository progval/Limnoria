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
Provides commands useful to the owner of the bot; the commands here require
their caller to have the 'owner' capability.  This plugin is loaded by default.
"""

__revision__ = "$Id$"

import fix

import gc
import os
import imp
import sys
import sets
import getopt
import logging
import linecache

import log
import conf
import utils
import world
import ircdb
import irclib
import ircmsgs
import drivers
import privmsgs
import registry
import callbacks

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
            log.warning('Invalid plugin directory: %s', dir)
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

def loadPluginClass(irc, module):
    """Loads the plugin Class from the given module into the given irc."""
    callback = module.Class()
    assert not irc.getCallback(callback.name())
    irc.addCallback(callback)

conf.registerGroup(conf.supybot, 'commands')
conf.registerGroup(conf.supybot.commands, 'defaultPlugins')
conf.supybot.commands.defaultPlugins.help = utils.normalizeWhitespace("""
Determines what commands have default plugins set, and which plugins are set to
be the default for each of those commands.""".strip())

def registerDefaultPlugin(command, plugin):
    command = callbacks.canonicalName(command)
    conf.registerGlobalValue(conf.supybot.commands.defaultPlugins,
                             command, registry.String(plugin, ''))

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

    Logs <text> to the global supybot log at critical priority.  Useful for
    marking logfiles for later searching.
    """
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


class LogErrorHandler(logging.Handler):
    irc = None
    def handle(self, record):
        if record.levelno >= logging.ERROR:
            if record.exc_info:
                (_, e, _) = record.exc_info
                s = 'Uncaught exception in %s: %s' % (record.module, e)
            else:
                s = record.msg
            # Send to the owner dudes.
            

class Owner(privmsgs.CapabilityCheckingPrivmsg):
    # This plugin must be first; its priority must be lowest; otherwise odd
    # things will happen when adding callbacks.
    priority = ~sys.maxint-1 # This must be first!
    capability = 'owner'
    _srcPlugins = ('Admin', 'Channel', 'Config', 'Misc', 'Owner', 'User')
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.log = LogProxy(self.log)
        setattr(self.__class__, 'exec', self.__class__._exec)
        for (name, s) in registry._cache.iteritems():
            if name.startswith('supybot.plugins'):
                try:
                    (_, _, name) = name.split('.')
                except ValueError: # unpack list of wrong size.
                    continue
                conf.registerPlugin(name)
            if name.startswith('supybot.commands.defaultPlugins'):
                try:
                    (_, _, _, name) = name.split('.')
                except ValueError: # unpack list of wrong size.
                    continue
                registerDefaultPlugin(name, s)

    def isCommand(self, methodName):
        return methodName == 'log' or \
               privmsgs.CapabilityCheckingPrivmsg.isCommand(self, methodName)

    def reset(self):
        # This has to be done somewhere, I figure here is as good place as any.
        callbacks.Privmsg._mores.clear()
        privmsgs.CapabilityCheckingPrivmsg.reset(self)

    def do001(self, irc, msg):
        self.log.info('Loading other src/ plugins.')
        for s in ('Admin', 'Channel', 'Config', 'Misc', 'User'):
            if irc.getCallback(s) is None:
                self.log.info('Loading %s.' % s)
                m = loadPluginModule(s)
                loadPluginClass(irc, m)
        self.log.info('Loading plugins/ plugins.')
        for (name, value) in conf.supybot.plugins.getValues(fullNames=False):
            if irc.getCallback(name) is None:
                if value():
                    if not irc.getCallback(name):
                        self.log.info('Loading %s.' % name)
                        try:
                            m = loadPluginModule(name)
                            loadPluginClass(irc, m)
                        except ImportError, e:
                            log.warning('Failed to load %s: %s', name, e)
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
                        tokens.insert(0, srcs[0])
                    else:
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

    def doPrivmsg(self, irc, msg):
        callbacks.Privmsg.handled = False
        callbacks.Privmsg.errored = False
        if ircdb.checkIgnored(msg.prefix):
            return
        s = callbacks.addressed(irc.nick, msg)
        if s:
            try:
                tokens = callbacks.tokenize(s)
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
        def eval(self, irc, msg, args):
            """<expression>

            Evaluates <expression> (which should be a Python expression) and
            returns its value.  If an exception is raised, reports the
            exception.
            """
            if conf.allowEval:
                s = privmsgs.getArgs(args)
                try:
                    irc.reply(repr(eval(s)))
                except SyntaxError, e:
                    irc.reply('%s: %r' % (utils.exnToString(e), s))
                except Exception, e:
                    irc.reply(utils.exnToString(e))
            else:
                # This should never happen, so I haven't bothered updating
                # this error string to say --allow-eval.
                irc.error('You must run supybot with the --allow-eval '
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
                irc.error('You must run supybot with the --allow-eval '
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
            conf.supybot.commands.defaultPlugins.unregister(command)
            irc.replySuccess()
        elif not cbs:
            irc.error('That\'s not a valid command.')
            return
        elif plugin:
            registerDefaultPlugin(command, plugin)
            irc.replySuccess()
        else:
            irc.reply(conf.supybot.commands.defaultPlugins.get(command)())

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
        """takes no arguments

        Exits the bot.
        """
        world.ircs[:] = []

    def flush(self, irc, msg, args):
        """takes no arguments

        Runs all the periodic flushers in world.flushers.  This includes
        flushing all logs and all configuration changes to disk.
        """
        world.flush()
        irc.replySuccess()

    def upkeep(self, irc, msg, args):
        """takes no arguments

        Runs the standard upkeep stuff (flushes and gc.collects()).
        """
        collected = world.upkeep(scheduleNext=False)
        if gc.garbage:
            irc.reply('Garbage!  %r' % gc.garbage)
        else:
            irc.reply('%s collected.' % utils.nItems('object', collected))

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
            irc.error('That module is already loaded.')
            return
        try:
            module = loadPluginModule(name, ignoreDeprecation)
        except Deprecated:
            irc.error('Plugin %r is deprecated.  '
                      'Use --deprecated to force it to load.'  % name)
            return
        except ImportError, e:
            if name in str(e):
                irc.error('No plugin %s exists.' % name)
            else:
                irc.error(str(e))
            return
        loadPluginClass(irc, module)
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
                gc.collect()
                callback = loadPluginClass(irc, module)
                irc.replySuccess()
            except ImportError:
                for callback in callbacks:
                    irc.addCallback(callback)
                irc.error('No plugin %s exists.' % name)
        else:
            irc.error('There was no callback %s.' % name)

    def unload(self, irc, msg, args):
        """<plugin>

        Unloads the callback by name; use the 'list' command to see a list
        of the currently loaded callbacks.
        """
        name = privmsgs.getArgs(args)
        callbacks = irc.removeCallback(name)
        if callbacks:
            for callback in callbacks:
                callback.die()
                del callback
            gc.collect()
            conf.registerPlugin(name, False)
            irc.replySuccess()
        else:
            irc.error('There was no callback %s' % name)


Class = Owner


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

