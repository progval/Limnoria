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
    except ValueError: # We'd rather raise the ImportError, so we'll let go...
        pass
    moduleInfo = imp.find_module(name, pluginDirs)
    module = imp.load_module(name, *moduleInfo)
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


class Owner(privmsgs.CapabilityCheckingPrivmsg):
    # This plugin must be first; its priority must be lowest; otherwise odd
    # things will happen when adding callbacks.
    priority = ~sys.maxint-1 # This must be first!
    capability = 'owner'
    _srcPlugins = ('Admin', 'Channel', 'Config', 'Misc', 'Owner', 'User')
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        setattr(self.__class__, 'exec', self.__class__._exec)
        self.defaultPlugins = {'list': 'Misc',
                               'capabilities': 'User',
                               'addcapability': 'Admin',
                               'removecapability': 'Admin'}
        for (name, s) in registry._cache.iteritems():
            if name.startswith('supybot.plugins'):
                try:
                    (_, _, name) = name.split('.')
                except ValueError: #unpack list of wrong size.
                    continue
                conf.registerPlugin(name)

    def do001(self, irc, msg):
        self.log.info('Loading other src/ plugins.')
        for s in ('Admin', 'Channel', 'Config', 'Misc', 'User'):
            self.log.info('Loading %s.' % s)
            m = loadPluginModule(s)
            loadPluginClass(irc, m)
        for (name, value) in conf.supybot.plugins.getValues():
            if value():
                s = rsplit(name, '.', 1)[-1]
                if not irc.getCallback(s):
                    self.log.info('Loading %s.' % s)
                    m = loadPluginModule(s)
                    loadPluginClass(irc, m)

    def disambiguate(self, irc, tokens, ambiguousCommands=None):
        """Disambiguates the given tokens based on the plugins loaded and
           commands available in the given irc.  Returns a dictionary of
           ambiguous commands, mapping the command to the plugins it's
           available in."""
        if ambiguousCommands is None:
            ambiguousCommands = {}
        if tokens:
            command = callbacks.canonicalName(tokens[0])
            if command in self.defaultPlugins:
                tokens.insert(0, self.defaultPlugins[command])
            else:
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
            except SyntaxError, e:
                callbacks.Privmsg.errored = True
                irc.queueMsg(callbacks.error(msg, str(e)))
                return
            ambiguousCommands = {}
            self.disambiguate(irc, tokens, ambiguousCommands)
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

    def defaultplugin(self, irc, msg, args):
        """<command> [<plugin>] [--remove]

        Calls <command> from <plugin> by default, rather than complaining about
        multiple plugins providing it.  If <plugin> is not provided, shows the
        current default plugin for <command>.  If --remove is given, removes
        the current default plugin for <command>.
        """
        if '--remove' in args:
            while '--remove' in args:
                args.remove('--remove')
            remove = True
        else:
            remove = False
        (command, plugin) = privmsgs.getArgs(args, optional=1)
        command = callbacks.canonicalName(command)
        cbs = callbacks.findCallbackForCommand(irc, command)
        if not cbs:
            irc.error('That\'t not a valid command.')
            return
        if plugin:
            self.defaultPlugins[command] = plugin
        else:
            try:
                if remove:
                    del self.defaultPlugins[command]
                else:
                    L = [command]
                    d = self.disambiguate(irc, L)
                    if d:
                        raise KeyError
                    assert len(L) == 2, 'Not disambiguated!'
                    irc.reply(L[0])
            except KeyError:
                irc.error('I have no default plugin for that command.')
                return
        irc.replySuccess()
                                
    if conf.allowEval:
        def eval(self, irc, msg, args):
            """<expression>

            Evaluates <expression> and returns its value.
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
                # this error string to say --enable-eval.
                irc.error('You must enable conf.allowEval for that to work.')

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
                # This should never happen, so I haven't bothered updating
                # this error string to say --enable-eval.
                irc.error('You must enable conf.allowEval for that to work.')
    else:
        def eval(self, irc, msg, args):
            """Run your bot with --enable-eval if you want this to work."""
            irc.error('You must give your bot the --enable-eval switch for '
                      'this command to be enabled.')
        _exec = eval
            

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
        raise SystemExit, 'Quitting because I was told by %s' % msg.prefix

    def flush(self, irc, msg, args):
        """takes no arguments

        Runs all the periodic flushers in world.flushers.
        """
        world.flush()
        irc.replySuccess()

    def upkeep(self, irc, msg, args):
        """takes no arguments

        Runs the standard upkeep stuff (flushes and gc.collects()).
        """
        collected = world.upkeep()
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
                      'Use --deprecated to force it to load.')
            return
        except ImportError, e:
            if name in str(e):
                irc.error('No plugin %s exists.' % name)
            else:
                irc.error(utils.exnToString(e))
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

    def reconf(self, irc, msg, args):
        """takes no arguments

        Reloads the configuration files for the user and channel databases:
        conf/users.conf and conf/channels.conf, by default.
        """
        ircdb.users.reload()
        ircdb.channels.reload()
        irc.replySuccess()


Class = Owner


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

