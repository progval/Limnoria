#!/usr/bin/env python3

###
# Copyright (c) 2003-2004, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
# Copyright (c) 2010-2021, Valentin Lorentz
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

from __future__ import print_function

import os
import sys

def error(s):
    sys.stderr.write(s)
    if not s.endswith(os.linesep):
        sys.stderr.write(os.linesep)
    sys.exit(-1)

import supybot

import re
import time
import pydoc
import pprint
import socket
import logging
import optparse

try:
    import supybot.i18n as i18n
except ImportError:
    sys.stderr.write("""Error:
    You are running a mix of Limnoria and stock Supybot code. Although you run
    one of Limnoria\'s executables, Python tries to load stock
    Supybot\'s library. To fix this issue, uninstall Supybot
    ("%s -m pip uninstall supybot" should do the job)
    and install Limnoria again.
    For your information, Supybot's libraries are installed here:
    %s\n""" %
    (sys.executable, '\n    '.join(supybot.__path__)))
    exit(-1)

import supybot.ansi as ansi
import supybot.utils as utils
import supybot.ircutils as ircutils
import supybot.registry as registry
# supybot.plugin, supybot.log, and supybot.conf will be imported later,
# because we need to set a language before loading the conf

import supybot.questions as questions
from supybot.questions import output, yn, anything, something, expect, getpass

def getPlugins(pluginDirs):
    plugins = set([])
    join = os.path.join
    for pluginDir in pluginDirs:
        try:
            for filename in os.listdir(pluginDir):
                fname = join(pluginDir, filename)
                if (filename.endswith('.py') or os.path.isdir(fname)) \
                   and filename[0].isupper():
                    plugins.add(os.path.splitext(filename)[0])
        except OSError:
            continue
    plugins.discard('Owner')
    plugins = list(plugins)
    plugins.sort()
    return plugins

def loadPlugin(name):
    import supybot.plugin as plugin
    try:
        module = plugin.loadPluginModule(name)
        if hasattr(module, 'Class'):
            return module
        else:
            output("""That plugin loaded fine, but didn't seem to be a real
            Supybot plugin; there was no Class variable to tell us what class
            to load when we load the plugin.  We'll skip over it for now, but
            you can always add it later.""")
            return None
    except Exception as e:
        output("""We encountered a bit of trouble trying to load plugin %r.
        Python told us %r.  We'll skip over it for now, you can always add it
        later.""" % (name, utils.gen.exnToString(e)))
        return None

def describePlugin(module, showUsage):
    if module.__doc__:
        output(module.__doc__, unformatted=False)
    elif hasattr(module.Class, '__doc__'):
        output(module.Class.__doc__, unformatted=False)
    else:
        output("""Unfortunately, this plugin doesn't seem to have any
        documentation.  Sorry about that.""")
    if showUsage:
        if hasattr(module, 'example'):
            if yn('This plugin has a usage example.  '
                  'Would you like to see it?', default=False):
                pydoc.pager(module.example)
        else:
            output("""This plugin has no usage example.""")

def clearLoadedPlugins(plugins, pluginRegistry):
    for plugin in plugins:
        try:
            pluginKey = pluginRegistry.get(plugin)
            if pluginKey():
                plugins.remove(plugin)
        except registry.NonExistentRegistryEntry:
            continue

_windowsVarRe = re.compile(r'%(\w+)%')
def getDirectoryName(default, basedir=os.curdir, prompt=True):
    done = False
    while not done:
        if prompt:
            dir = something('What directory do you want to use?',
                           default=os.path.join(basedir, default))
        else:
            dir = os.path.join(basedir, default)
        orig_dir = dir
        dir = os.path.expanduser(dir)
        dir = _windowsVarRe.sub(r'$\1', dir)
        dir = os.path.expandvars(dir)
        dir = os.path.abspath(dir)
        try:
            os.makedirs(dir)
            done = True
        except OSError as e:
            # 17 is File exists for Linux (and likely other POSIX systems)
            # 183 is the same for Windows
            if e.args[0] == 17 or (os.name == 'nt' and e.args[0] == 183):
                done = True
            else:
                output("""Sorry, I couldn't make that directory for some
                reason.  The Operating System told me %s.  You're going to
                have to pick someplace else.""" % e)
                prompt = True
    return (dir, os.path.dirname(orig_dir))


def _main():
    import supybot.version as version
    parser = optparse.OptionParser(usage='Usage: %prog [options]',
                                   version='Supybot %s' % version.version)
    parser.add_option('', '--allow-root', action='store_true',
                      dest='allowRoot',
                      help='Determines whether the wizard will be allowed to '
                           'as root. This should not be used except in special '
                           'circumstances, such as running inside a containerized '
                           'environment.')
    parser.add_option('', '--allow-home', action='store_true',
                      dest='allowHome',
                      help='Determines whether the wizard will be allowed to '
                           'run directly in the HOME directory. '
                           'You should not do this unless you want it to '
                           'create multiple files in your HOME directory.')
    parser.add_option('', '--allow-bin', action='store_true',
                      dest='allowBin',
                      help='Determines whether the wizard will be allowed to '
                           'run directly in a directory for binaries (eg. '
                           '/usr/bin, /usr/local/bin, or ~/.local/bin). '
                           'You should not do this unless you want it to '
                           'create multiple non-binary files in directory '
                           'that should only contain binaries.')
    parser.add_option('', '--no-network', action='store_false',
                      dest='network',
                      help='Determines whether the wizard will be allowed to '
                           'run without a network connection.')
    (options, args) = parser.parse_args()
    if os.name == 'posix':
        if (os.getuid() == 0 or os.geteuid() == 0) and not options.allowRoot:
            error('Running as root is not supported by default (see --allow-root).')
    if os.name == 'posix':
        if (os.getcwd() == os.path.expanduser('~')) and not options.allowHome:
            error('Please, don\'t run this in your HOME directory.')
        if (os.path.split(os.getcwd())[-1] == 'bin') and not options.allowBin:
            error('Please, don\'t run this in a "bin" directory.')
    if os.path.isfile(os.path.join('scripts', 'supybot-wizard')) or \
            os.path.isfile(os.path.join('..', 'scripts', 'supybot-wizard')):
        print('')
        print('+------------------------------------------------------------+')
        print('| +--------------------------------------------------------+ |')
        print('| | Warning: It looks like you are running the wizard from | |')
        print('| | the Supybot source directory. This is not recommended. | |')
        print('| | Please press Ctrl-C and change to another directory.   | |')
        print('| +--------------------------------------------------------+ |')
        print('+------------------------------------------------------------+')
        print('')

    if args:
        parser.error('This program takes no non-option arguments.')
    output("""This is a wizard to help you start running supybot.  What it
    will do is create the necessary config files based on the options you
    select here.  So hold on tight and be ready to be interrogated :)""")


    output("""First of all, we can bold the questions you're asked so you can
    easily distinguish the mostly useless blather (like this) from the
    questions that you actually have to answer.""")
    if yn('Would you like to try this bolding?', default=True):
        questions.useBold = True
        if not yn('Do you see this in bold?'):
            output("""Sorry, it looks like your terminal isn't ANSI compliant.
            Try again some other day, on some other terminal :)""")
            questions.useBold = False
        else:
            output("""Great!""")

    ###
    # Preliminary questions.
    ###
    output("""We've got some preliminary things to get out of the way before
    we can really start asking you questions that directly relate to what your
    bot is going to be like.""")

    # Advanced?
    output("""We want to know if you consider yourself an advanced Supybot
    user because some questions are just utterly boring and useless for new
    users.  Others might not make sense unless you've used Supybot for some
    time.""")
    advanced = yn('Are you an advanced Supybot user?', default=False)

    # Language?
    output("""This version of Supybot (known as Limnoria) includes another
    language. This can be changed at any time. You need to answer with a short
    id for the language, such as 'en', 'fr', 'it' (without the quotes). If
    you want to use English, just press enter.""")
    language = expect('What language do you want to use?',
                      i18n.SUPPORTED_LANGUAGES, default='en')

    class Empty:
        """This is a hack to allow the i18n to get the current language, before
        loading the conf module, before the conf module needs i18n to set the
        default strings."""
        def __call__(self):
            return self.value
    fakeConf = Empty()
    fakeConf.supybot = Empty()
    fakeConf.supybot.language = Empty()
    fakeConf.supybot.language.value = language
    i18n.conf = fakeConf
    i18n.currentLocale = language
    i18n.reloadLocales()
    import supybot.conf as conf
    i18n.import_conf() # It imports the real conf module

    ### Directories.
    # We set these variables in cache because otherwise conf and log will
    # create directories for the default values, which might not be what the
    # user wants.
    if advanced:
        output("""Now we've got to ask you some questions about where some of
        your directories are (or, perhaps, will be :)).  If you're running this
        wizard from the directory you'll actually be starting your bot from and
        don't mind creating some directories in the current directory, then
        just don't give answers to these questions and we'll create the
        directories we need right here in this directory.""")

        # conf.supybot.directories.log
        output("""Your bot will need to put its logs somewhere.  Do you have
        any specific place you'd like them?  If not, just press enter and we'll
        make a directory named "logs" right here.""")
        (logDir, basedir) = getDirectoryName('logs')
        conf.supybot.directories.log.setValue(logDir)
        import supybot.log as log
        log._stdoutHandler.setLevel(100) # *Nothing* gets through this!

        # conf.supybot.directories.data
        output("""Your bot will need to put various data somewhere.  Things
        like databases, downloaded files, etc.  Do you have any specific place
        you'd like the bot to put these things?  If not, just press enter and
        we'll make a directory named "data" right here.""")
        (dataDir, basedir) = getDirectoryName('data', basedir=basedir)
        conf.supybot.directories.data.setValue(dataDir)

        # conf.supybot.directories.conf
        output("""Your bot must know where to find its configuration files.
        It'll probably only make one or two, but it's gotta have some place to
        put them.  Where should that place be?  If you don't care, just press
        enter and we'll make a directory right here named "conf" where it'll
        store its stuff. """)
        (confDir, basedir) = getDirectoryName('conf', basedir=basedir)
        conf.supybot.directories.conf.setValue(confDir)

        # conf.supybot.directories.backup
        output("""Your bot must know where to place backups of its conf and
        data files.  Where should that place be?  If you don't care, just press
        enter and we'll make a directory right here named "backup" where it'll
        store its stuff.""")
        (backupDir, basedir) = getDirectoryName('backup', basedir=basedir)
        conf.supybot.directories.backup.setValue(backupDir)

        # conf.supybot.directories.data.tmp
        output("""Your bot needs a directory to put temporary files (used
        mainly to atomically update its configuration files).""")
        (tmpDir, basedir) = getDirectoryName('tmp', basedir=basedir)
        conf.supybot.directories.data.tmp.setValue(tmpDir)

        # conf.supybot.directories.data.web
        output("""Your bot needs a directory to put files related to the web
        server (templates, CSS).""")
        (webDir, basedir) = getDirectoryName('web', basedir=basedir)
        conf.supybot.directories.data.web.setValue(webDir)


        # imports callbacks, which imports ircdb, which requires
        # directories.conf
        import supybot.plugin as plugin

        # pluginDirs
        output("""Your bot will also need to know where to find its plugins at.
        Of course, it already knows where the plugins that it came with are,
        but your own personal plugins that you write for will probably be
        somewhere else.""")
        pluginDirs = conf.supybot.directories.plugins()
        output("""Currently, the bot knows about the following directories:""")
        output(format('%L', pluginDirs + [plugin._pluginsDir]))
        while yn('Would you like to add another plugin directory?  '
                 'Adding a local plugin directory is good style.',
                 default=True):
            (pluginDir, _) = getDirectoryName('plugins', basedir=basedir)
            if pluginDir not in pluginDirs:
                pluginDirs.append(pluginDir)
        conf.supybot.directories.plugins.setValue(pluginDirs)
    else:
        output("""Your bot needs to create some directories in order to store
        the various log, config, and data files.""")
        basedir = something("""Where would you like to create these
                            directories?""", default=os.curdir)

        # conf.supybot.directories.log
        (logDir, basedir) = getDirectoryName('logs',
                                             basedir=basedir, prompt=False)
        conf.supybot.directories.log.setValue(logDir)

        # conf.supybot.directories.data
        (dataDir, basedir) = getDirectoryName('data',
                                              basedir=basedir, prompt=False)
        conf.supybot.directories.data.setValue(dataDir)
        (tmpDir, basedir) = getDirectoryName('tmp',
                                             basedir=basedir, prompt=False)
        conf.supybot.directories.data.tmp.setValue(tmpDir)
        (webDir, basedir) = getDirectoryName('web',
                                             basedir=basedir, prompt=False)
        conf.supybot.directories.data.web.setValue(webDir)

        # conf.supybot.directories.conf
        (confDir, basedir) = getDirectoryName('conf',
                                              basedir=basedir, prompt=False)
        conf.supybot.directories.conf.setValue(confDir)

        # conf.supybot.directories.backup
        (backupDir, basedir) = getDirectoryName('backup',
                                                basedir=basedir, prompt=False)
        conf.supybot.directories.backup.setValue(backupDir)

        # pluginDirs
        pluginDirs = conf.supybot.directories.plugins()
        (pluginDir, _) = getDirectoryName('plugins',
                                          basedir=basedir, prompt=False)
        if pluginDir not in pluginDirs:
            pluginDirs.append(pluginDir)
        conf.supybot.directories.plugins.setValue(pluginDirs)

    import supybot.log as log
    log._stdoutHandler.setLevel(100) # *Nothing* gets through this!
    import supybot.plugin as plugin

    output("Good!  We're done with the directory stuff.")

    ###
    # Bot stuff
    ###
    output("""Now we're going to ask you things that actually relate to the
    bot you'll be running.""")

    network = None
    while not network:
        output("""First, we need to know the name of the network you'd like to
        connect to.  Not the server host, mind you, but the name of the
        network.  If you plan to connect to irc.libera.chat, for instance,
        you should answer this question with 'libera' or 'liberachat'
        (without the quotes).
        """)
        network = something('What IRC network will you be connecting to?')
        if '.' in network:
            output("""There shouldn't be a '.' in the network name.  Remember,
            this is the network name, not the actual server you plan to connect
            to.""")
            network = None
        elif not registry.isValidRegistryName(network):
            output("""That's not a valid name for one reason or another.  Please
            pick a simpler name, one more likely to be valid.""")
            network = None

    conf.supybot.networks.setValue([network])
    network = conf.registerNetwork(network)

    defaultServer = None
    server = None
    ip = None
    while not ip:
        serverString = something('What server would you like to connect to?',
                                 default=defaultServer)
        if options.network:
            try:
                output("""Looking up %s...""" % serverString)
                ip = socket.gethostbyname(serverString)
            except:
                output("""Sorry, I couldn't find that server.  Perhaps you
                misspelled it?  Also, be sure not to put the port in the
                server's name -- we'll ask you about that later.""")
        else:
            ip = 'no network available'

    output("""Found %s (%s).""" % (serverString, ip))

    # conf.supybot.networks.<network>.ssl
    output("""Most networks allow you to use a secure connection via SSL.
    If you are not sure whether this network supports SSL or not, check
    its website.""")
    use_ssl = yn('Do you want to use an SSL connection?', default=True)
    network.ssl.setValue(use_ssl)

    output("""IRC servers almost always accept connections on port
    6697 (or 6667 when not using SSL).  They can, however, accept connections
    anywhere their admins feel like they want to accept connections from.""")
    if yn('Does this server require connection on a non-standard port?',
          default=False):
        port = 0
        while not port:
            port = something('What port is that?')
            try:
                i = int(port)
                if not (0 < i < 65536):
                    raise ValueError()
            except ValueError:
                output("""That's not a valid port.""")
                port = 0
    else:
        if network.ssl.value:
            port = 6697
        else:
            port = 6667
    server = ':'.join([serverString, str(port)])
    network.servers.setValue([server])

    # conf.supybot.nick
    # Force the user into specifying a nick if it didn't have one already
    while True:
        nick = something('What nick would you like your bot to use?',
                         default=None)
        try:
            conf.supybot.nick.set(nick)
            break
        except registry.InvalidRegistryValue:
            output("""That's not a valid nick.  Go ahead and pick another.""")

    # conf.supybot.networks.<network>.sasl.{username,password}
    output("""Most networks allow you to create an account, using services
    typically known as NickServ. If you already have one, you can configure
    the bot to use that account by proving your username and password
    (also known as "SASL plain").
    It is usually not a requirement.""")
    if yn('Do you want your bot to use a network account?', default=False):
        while True:
            username = something('What account name should the bot use?')
            password = getpass('What is the password of that account?')
            if not username:
                if yn('Missing username. Do you want to try again?'):
                    continue
            if not password:
                if yn('Missing password. Do you want to try again?'):
                    continue
            network.sasl.username.set(username)
            network.sasl.password.set(password)
            break

    # conf.supybot.user
    if advanced:
        output("""If you've ever done a /whois on a person, you know that IRC
        provides a way for users to show the world their full name.  What would
        you like your bot's full name to be?  If you don't care, just press
        enter and it'll be the same as your bot's nick.""")
        user = ''
        user = something('What would you like your bot\'s full name to be?',
                         default=nick)
        conf.supybot.user.set(user)
    # conf.supybot.ident (if advanced)
    defaultIdent = 'limnoria'
    if advanced:
        output("""IRC servers also allow you to set your ident, which they
        might need if they can't find your identd server.  What would you like
        your ident to be?  If you don't care, press enter and we'll use
        'limnoria'.  In fact, we prefer that you do this, because it provides
        free advertising for Supybot when users /whois your bot.  But, of
        course, it's your call.""")
        while True:
            ident = something('What would you like your bot\'s ident to be?',
                              default=defaultIdent)
            try:
                conf.supybot.ident.set(ident)
                break
            except registry.InvalidRegistryValue:
                output("""That was not a valid ident.  Go ahead and pick
                another.""")
    else:
        conf.supybot.ident.set(defaultIdent)

    # conf.supybot.networks.<network>.password
    output("""Some servers require a password to connect to them.  Most
    public servers don't.  If you try to connect to a server and for some
    reason it just won't work, it might be that you need to set a
    password.""")
    if yn('Do you want to set such a password?', default=False):
        network.password.set(getpass())

    # conf.supybot.networks.<network>.channels
    output("""Of course, having an IRC bot isn't the most useful thing in the
    world unless you can make that bot join some channels.""")
    if yn('Do you want your bot to join some channels when it connects?',
          default=True):
        defaultChannels = ' '.join(network.channels())
        output("""Separate channels with spaces.  If the channel is locked
                  with a key, follow the channel name with the key separated
                  by a comma. For example:
                  #supybot-bots #mychannel,mykey #otherchannel""");
        while True:
            channels_input = something('What channels?', default=defaultChannels)
            channels = []
            error_ = False
            for channel in channels_input.split():
                L = channel.split(',')
                if len(L) == 0:
                    continue
                elif len(L) == 1:
                    (channel,) = L
                    channels.append(channel)
                elif len(L) == 2:
                    (channel, key) = L
                    channels.append(channel)
                    network.channels.key.get(channel).setValue(key)
                else:
                    output("""Too many commas in %s.""" % channel)
                    error_ = True
                    break
            if error_:
                break
            try:
                network.channels.set(' '.join(channels))
                break
            except registry.InvalidRegistryValue as e:
                output(""""%s" is an invalid IRC channel.  Be sure to prefix
                the channel with # (or +, or !, or &, but no one uses those
                channels, really).  Be sure the channel key (if you are
                supplying one) does not contain a comma.""" % e.channel)
    else:
        network.channels.setValue([])

    ###
    # Plugins
    ###
    def configurePlugin(module, advanced):
        if hasattr(module, 'configure'):
            output("""Beginning configuration for %s...""" %
                   module.Class.__name__)
            module.configure(advanced)
            print() # Blank line :)
            output("""Done!""")
        else:
            conf.registerPlugin(module.__name__, currentValue=True)

    plugins = getPlugins(pluginDirs + [plugin._pluginsDir])
    for s in ('Admin', 'User', 'Channel', 'Misc', 'Config', 'Utilities'):
        m = loadPlugin(s)
        if m is not None:
            configurePlugin(m, advanced)
        else:
            error('There was an error loading one of the core plugins that '
                  'under almost all circumstances are loaded.  Go ahead and '
                  'fix that error and run this script again.')
    clearLoadedPlugins(plugins, conf.supybot.plugins)

    output("""Now we're going to run you through plugin configuration. There's
           a variety of plugins in supybot by default, but you can create and
           add your own, of course. We'll allow you to take a look at the known
           plugins' descriptions and configure them
           if you like what you see.""")

    # bulk
    addedBulk = False
    if advanced and yn('Would you like to add plugins en masse first?'):
        addedBulk = True
        output(format("""The available plugins are: %L.""", plugins))
        output("""What plugins would you like to add?  If you've changed your
        mind and would rather not add plugins in bulk like this, just press
        enter and we'll move on to the individual plugin configuration.
        We suggest you to add Aka, Ctcp, Later, Network, Plugin, String,
        and Utilities""")
        massPlugins = anything('Separate plugin names by spaces or commas:')
        for name in re.split(r',?\s+', massPlugins):
            module = loadPlugin(name)
            if module is not None:
                configurePlugin(module, advanced)
                clearLoadedPlugins(plugins, conf.supybot.plugins)

    # individual
    if yn('Would you like to look at plugins individually?'):
        output("""Next comes your opportunity to learn more about the plugins
        that are available and select some (or all!) of them to run in your
        bot.  Before you have to make a decision, of course, you'll be able to
        see a short description of the plugin and, if you choose, an example
        session with the plugin.  Let's begin.""")
        # until we get example strings again, this will default to false
        #showUsage =yn('Would you like the option of seeing usage examples?')
        showUsage = False
        name = expect('What plugin would you like to look at?',
                      plugins, acceptEmpty=True)
        while name:
            module = loadPlugin(name)
            if module is not None:
                describePlugin(module, showUsage)
                if yn('Would you like to load this plugin?', default=True):
                    configurePlugin(module, advanced)
                    clearLoadedPlugins(plugins, conf.supybot.plugins)
            if not yn('Would you like add another plugin?'):
                break
            name = expect('What plugin would you like to look at?', plugins)

    ###
    # Sundry
    ###
    output("""Although supybot offers a supybot-adduser script, with which
    you can add users to your bot's user database, it's *very* important that
    you have an owner user for you bot.""")
    if yn('Would you like to add an owner user for your bot?', default=True):
        import supybot.ircdb as ircdb
        name = something('What should the owner\'s username be?')
        try:
            id = ircdb.users.getUserId(name)
            u = ircdb.users.getUser(id)
            if u._checkCapability('owner'):
                output("""That user already exists, and has owner capabilities
                already.  Perhaps you added it before? """)
                if yn('Do you want to remove its owner capability?',
                      default=False):
                    u.removeCapability('owner')
                    ircdb.users.setUser(u)
            else:
                output("""That user already exists, but doesn't have owner
                capabilities.""")
                if yn('Do you want to add to it owner capabilities?',
                      default=False):
                    u.addCapability('owner')
                    ircdb.users.setUser(u)
        except KeyError:
            password = getpass('What should the owner\'s password be?')
            u = ircdb.users.newUser()
            u.name = name
            u.setPassword(password)
            u.addCapability('owner')
            ircdb.users.setUser(u)

    output("""Of course, when you're in an IRC channel you can address the bot
    by its nick and it will respond, if you give it a valid command (it may or
    may not respond, depending on what your config variable replyWhenNotCommand
    is set to).  But your bot can also respond to a short "prefix character,"
    so instead of saying "bot: do this," you can say, "@do this" and achieve
    the same effect.  Of course, you don't *have* to have a prefix char, but
    if the bot ends up participating significantly in your channel, it'll ease
    things.""")
    if yn('Would you like to set the prefix char(s) for your bot?  ',
          default=True):
        output("""Enter any characters you want here, but be careful: they
        should be rare enough that people don't accidentally address the bot
        (simply because they'll probably be annoyed if they do address the bot
        on accident).  You can even have more than one.  I (jemfinch) am quite
        partial to @, but that's because I've been using it since my ocamlbot
        days.""")
        import supybot.callbacks as callbacks
        c = ''
        while not c:
            try:
                c = anything('What would you like your bot\'s prefix '
                             'character(s) to be?')
                conf.supybot.reply.whenAddressedBy.chars.set(c)
            except registry.InvalidRegistryValue as e:
                output(str(e))
                c = ''
    else:
        conf.supybot.reply.whenAddressedBy.chars.set('')

    ###
    # logging variables.
    ###

    if advanced:
        # conf.supybot.log.stdout
        output("""By default, your bot will log not only to files in the logs
        directory you gave it, but also to stdout.  We find this useful for
        debugging, and also just for the pretty output (it's colored!)""")
        stdout = not yn('Would you like to turn off this logging to stdout?',
                        default=False)
        conf.supybot.log.stdout.setValue(stdout)
        if conf.supybot.log.stdout():
            # conf.something
            output("""Some terminals may not be able to display the pretty
            colors logged to stderr.  By default, though, we turn the colors
            off for Windows machines and leave it on for *nix machines.""")
            if os.name != 'nt':
                conf.supybot.log.stdout.colorized.setValue(
                    not yn('Would you like to turn this colorization off?',
                    default=False))

        # conf.supybot.log.level
        output("""Your bot can handle debug messages at several priorities,
        CRITICAL, ERROR, WARNING, INFO, and DEBUG, in decreasing order of
        priority. By default, your bot will log all of these priorities except
        DEBUG.  You can, however, specify that it only log messages above a
        certain priority level.""")
        priority = str(conf.supybot.log.level)
        logLevel = something('What would you like the minimum priority to be?'
                             '  Just press enter to accept the default.',
                             default=priority).lower()
        while logLevel not in ['debug','info','warning','error','critical']:
            output("""That's not a valid priority.  Valid priorities include
            'DEBUG', 'INFO', 'WARNING', 'ERROR', and 'CRITICAL'""")
            logLevel = something('What would you like the minimum priority to '
                                 'be?  Just press enter to accept the default.',
                                 default=priority).lower()
        conf.supybot.log.level.set(logLevel)

        # conf.supybot.databases.plugins.channelSpecific

        output("""Many plugins in Supybot are channel-specific.  Their
        databases, likewise, are specific to each channel the bot is in.  Many
        people don't want this, so we have one central location in which to
        say that you would prefer all databases for all channels to be shared.
        This variable, supybot.databases.plugins.channelSpecific, is that
        place.""")

        conf.supybot.databases.plugins.channelSpecific.setValue(
            not yn('Would you like plugin databases to be shared by all '
                   'channels, rather than specific to each channel the '
                   'bot is in?'))

    output("""There are a lot of options we didn't ask you about simply
              because we'd rather you get up and running and have time
              left to play around with your bot.  But come back and see
              us!  When you've played around with your bot enough to
              know what you like, what you don't like, what you'd like
              to change, then take a look at your configuration file
              when your bot isn't running and read the comments,
              tweaking values to your heart's desire.""")

    # Let's make sure that src/ plugins are loaded.
    conf.registerPlugin('Admin', True)
    conf.registerPlugin('AutoMode', True)
    conf.registerPlugin('Channel', True)
    conf.registerPlugin('Config', True)
    conf.registerPlugin('Misc', True)
    conf.registerPlugin('Network', True)
    conf.registerPlugin('NickAuth', True)
    conf.registerPlugin('User', True)
    conf.registerPlugin('Utilities', True)

    ###
    # Write the registry
    ###

    # We're going to need to do a darcs predist thing here.
    #conf.supybot.debug.generated.setValue('...')

    if advanced:
        basedir = '.'
    filename = os.path.join(basedir, '%s.conf')

    filename = something("""In which file would you like to save
                         this config?""", default=filename % nick)
    if not filename.endswith('.conf'):
        filename += '.conf'
    registry.close(conf.supybot, os.path.expanduser(filename))

    # Done!
    output("""All done!  Your new bot configuration is %s.  If you're running
    a *nix based OS, you can probably start your bot with the command line
    "supybot %s".  If you're not running a *nix or similar machine, you'll
    just have to start it like you start all your other Python scripts.""" % \
                                                         (filename, filename))

def main():
    try:
        _main()
    except KeyboardInterrupt:
        # We may still be using bold text when exiting during a prompt
        if questions.useBold:
            import supybot.ansi as ansi
            print(ansi.RESET)
        print()
        print()
        output("""Well, it looks like you canceled out of the wizard before
        it was done.  Unfortunately, I didn't get to write anything to file.
        Please run the wizard again to completion.""")


if __name__ == '__main__':
    main()

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
