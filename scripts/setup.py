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


# So we gotta:
#   Check to see if the user has sqlite installed.
#   Get the owner's user name and password
#   Provide a list of modules to load by default.
#   See what other commands the user would like to run by default.
#   Go through conf.py options and see which ones the user would like.
import os
import imp
import sys
import pydoc
import socket
import pprint

if 'src' not in sys.path:
    sys.path.insert(0, 'src')

from fix import *
from questions import *

import conf
import ircdb
import ircutils

if __name__ == '__main__':
    fd = file('src/template.py')
    template = fd.read()
    fd.close()
    ###
    # First things first.
    ###
    if yn('Are you an advanced Supybot/IRC user?') == 'y':
        advanced = True
    else:
        advanced = False
    ###
    # Basic stuff.
    ###

    # Server.
    server = ''
    while not server:
        server = anything('What server would you like to connect to?')
        try:
            print 'Looking up %s...' % server
            ip = socket.gethostbyname(server)
            print 'Found %s (%s).' % (server, ip)
        except:
            print 'Sorry, but I couldn\'t find that server.'
            server = ''
    if yn('Does that server require connection on a non-standard port?')=='y':
        port = ''
        while not port:
            port = something('What port is that?')
            try:
                i = int(port)
                if not (0 < i < 65536):
                    raise ValueError
            except ValueError:
                print 'That\'s not a valid port.'
                port = ''
        server = ':'.join((server, port))
    template = template.replace('%%server%%', repr(server))

    # Password.
    password = ''
    if yn('Does the server require a password to connect?') == 'y':
        password = anything('What password would you like the bot to use?')
    template = template.replace('%%password%%', repr(password))

    # Nick.
    nick = something('What nick would you like the bot to use?')
    while not ircutils.isNick(nick):
        print 'That\'s not a valid nick.'
        nick = something('What nick would you like the bot use?')
    template = template.replace('%%nick%%', repr(nick))

    # User/Ident.
    user = nick
    ident = nick
    if advanced and yn('Would you like to set a user/ident?') == 'y':
        user = anything('What user would you like the bot to use?')
        ident = anything('What ident would you like the bot to use?')
    template = template.replace('%%user%%', repr(user))
    template = template.replace('%%ident%%', repr(ident))
    
    onStart = []
    afterConnect = []
    onStart.append('load AdminCommands')
    onStart.append('load UserCommands')
    onStart.append('load ChannelCommands')
    onStart.append('load MiscCommands')

    ###
    # Modules.
    ###
    filenames = []
    for dir in conf.pluginDirs:
        filenames.extend(os.listdir(dir))
    plugins = []
    for filename in filenames:
        if filename.endswith('.py') and filename[0].isupper():
            plugins.append(os.path.splitext(filename)[0])
        plugins.sort()
    for s in onStart:
        if s.startswith('load'):
            (_, plugin) = s.split()
            if plugin in plugins:
                plugins.remove(plugin)
    if yn('Would you like to see a list of the available modules?') == 'y':
        print 'The available plugins are:\n  %s' % '\n  '.join(plugins)
    if advanced and yn('Would you like to add plugins en masse first?') == 'y':
        plugins = something('What plugins? (separate by spaces)').split()
        for plugin in plugins:
            moduleInfo = imp.find_module(plugin, conf.pluginDirs)
            try:
                module = imp.load_module(plugin, *moduleInfo)
            except ImportError, e:
                print 'Sorry, %s could not be loaded.' % plugin
                continue
            if hasattr(module, 'configure'):
                module.configure(onStart, afterConnect, advanced)
            else:
                onStart.append('load %s' % plugin)
    for s in onStart:
        if s.startswith('load'):
            (_, plugin) = s.split()
            if plugin in plugins:
                plugins.remove(plugin)
    usage = True
    if advanced and \
       yn('Would you like the option of seeing usage examples?')=='n':
        usage = False
    while yn('Would you like to add a plugin?') == 'y':
        plugin = expect('What plugin?', plugins)
        moduleInfo = imp.find_module(plugin, conf.pluginDirs)
        try:
            module = imp.load_module(plugin, *moduleInfo)
        except ImportError, e:
            print 'Sorry, this plugin cannot be loaded.  You need the ' \
                  'python module %s to load it.' % e.args[0].split()[-1]
            continue
        if module.__doc__:
            print module.__doc__
        else:
            print 'This plugin has no documentation.'
        if hasattr(module, 'example'):
            if usage and yn('Would you like to see a usage example?') == 'y':
                print
                print 'Here\'s an example of usage of this module:'
                print
                pydoc.pager(module.example)
        if yn('Would you like to add this plugin?') == 'y':
            if hasattr(module, 'configure'):
                module.configure(onStart, afterConnect, advanced)
            else:
                onStart.append('load %s' % plugin)
            for s in onStart:
                if s.startswith('load'):
                    (_, plugin) = s.split()
                    if plugin in plugins:
                        plugins.remove(plugin)

    ###
    # Commands
    ###
    preConnect = 'Would you like any commands to run ' \
                 'before the bot connects to the server?'
    while advanced and yn(preConnect) == 'y':
        preConnect = 'Would you like any other commands ' \
                     'to run before the bot connects to the server?'
        onStart.append(anything('What command?'))
    if yn('Do you want the bot to join any channels?') == 'y':
        channels = something('What channels? (separate channels by spaces)')
        while not all(ircutils.isChannel, channels.split()):
            for channel in channels.split():
                if not ircutils.isChannel(channel):
                    print '%r isn\'t a valid channel.' % channel
            channels = something('What channels?')
        afterConnect.append('join %s' % channels)
    postConnect = 'Would you like any commands to run ' \
                  'when the bot is finished connecting to the server?'
    while advanced and yn(postConnect) == 'y':
        postConnect = 'Would you like any other commands to run ' \
                      'when the bot is finished connecting to the server?'
        afterConnect.append(anything('What command?'))

    template = template.replace('%%onStart%%', pprint.pformat(onStart))
    template = template.replace('%%afterConnect%%',
                                pprint.pformat(afterConnect))


    ###
    # Set owner user.
    ###
    if yn('Would you like to add an owner user?') == 'y':
        owner = something('What should the owner\'s username be?')
        password = something('What should the owner\'s password be?')
        (id, user) = ircdb.users.newUser()
        user.setPassword(password)
        user.names.add(owner)
        user.addCapability('owner')
        while yn('Would you like to add a hostmask for the owner?') == 'y':
            user.addHostmask(something('What hostmask?'))
        ircdb.users.setUser(id, user)

    ###
    # Configuration variables in conf.py.
    ###
    configVariables = {}
    if advanced and \
       yn('Would you like to modify the default config variables?')=='y':
        print 'Supybot can use various "drivers" for actually handling the '
        print 'network connects the bot makes.  One of the most robust of '
        print 'these is the Twisted <http://www.twistedmatrix.com/> driver. '
        if yn('Would you like to use the Twisted driver?') == 'y':
            try:
                import twistedDrivers
                configVariables['driverModule'] = 'twistedDrivers'
            except:
                print 'Sorry, twisted doesn\'t seem to be installed.'

        print 'Supybot can allow an owner user to evaluated arbitrary Python '
        print 'code.  Obviously, this is disabled by default just in case '
        print 'there happens to be a bug in supybot\'s code. '
        if yn('Would you like to enable evaluation of arbitrary Python?')=='y':
            configVariables['allowEval'] = True
    print 'Supybot can accept a "prefix character" (or many!) to determine '
    print 'whether or not he\'s being addressed by someone.  For instance, if '
    print 'his prefixChar is "@", then "@cpustats" has the same effect as '
    print '"supybot: cpustats".'
    s = anything('What would you like supybot\'s prefixChar(s) to be?')
    configVariables['prefixChars'] = s

    if not advanced:
        try:
            import twistedDrivers
            configVariables['driverModule'] = 'twistedDrivers'
        except ImportError:
            pass
                
                
    template = template.replace('%%configVariables%%',
                                pprint.pformat(configVariables))

    filename = '%s.py' % nick
    fd = open(filename, 'w')
    fd.write(template)
    fd.close()

    os.chmod(filename, 0755)
    

    if sys.platform == 'win32':
        print
        print 'You\'re done!  Run the bot however works for you.'
        print
    else:
        print
        print 'You\'re done!  Now run the bot with the command line:'
        print './%s' % filename
        print
    
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
