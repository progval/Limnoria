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
import sys
sys.path.insert(0, 'src')
from fix import *
from questions import *
import os
import imp
import conf
import ircdb
sys.path.insert(0, conf.pluginDir)
import socket
if __name__ == '__main__':
    ###
    # First things first.
    ###
    if ny('Are you an advanced Supybot/IRC user?') == 'y':
        advanced = True
    else:
        advanced = False
    ###
    # Basic stuff.
    ###
    name = anything('What would you like to name your config file?')
    if not name.endswith('.conf'):
        name += '.conf'
    configfd = file(os.path.join(conf.confDir, name), 'w')
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
    if ny('Does that server require connection on a non-standard port?')=='y':
        server = ':'.join(server, anything('What port is that?'))
    configfd.write('Server: %s\n' % server)
    if ny('Does the server require a password to connect?') == 'y':
        password = anything('What password would you like the bot to use?')
        configfd.write('Pass: ' + password)
    nick = anything('What nick would you like the bot to use?')
    configfd.write('Nick: %s\n' % nick)
    if advanced and ny('Would you like to set a user/ident?') == 'y':
        user = anything('What user would you like the bot to use?')
        configfd.write('User: %s\n' % user)
        ident = anything('What ident would you like the bot to use?')
        configfd.write('Ident: %s\n' % ident)
    configfd.write('\n')
    onStart = []
    onStart.append('# Commands to run before connecting.')
    onStart.append('load AdminCommands')
    onStart.append('load UserCommands')
    onStart.append('load ChannelCommands')
    onStart.append('load MiscCommands')
    afterConnect = []
    afterConnect.append('# Commands to run after connecting.')

    ###
    # Modules.
    ###
    if yn('Would you like to see a list of the available modules?') == 'y':
        filenames = os.listdir(conf.pluginDir)
        plugins = []
        for filename in filenames:
            if filename.endswith('.py') and \
               filename.lower() != filename:
                plugins.append(os.path.splitext(filename)[0])
        print 'The available plugins are:\n  %s' % '\n  '.join(plugins)
        while yn('Would you like to add a plugin?') == 'y':
            plugin = expect('What plugin?', plugins)
            moduleInfo = imp.find_module(plugin)
            try:
                module = imp.load_module(plugin, *moduleInfo)
            except ImportError, e:
                print 'Sorry, this plugin cannot be loaded.  You need the ' \
                      'python module %s to load it.' % e.args[0].split()[-1]
                continue
            print module.__doc__
            if yn('Would you like to add this plugin?') == 'y':
                if hasattr(module, 'configure'):
                    module.configure(onStart, afterConnect, advanced)
                else:
                    onStart.append('load %s' % plugin)
                if 'load %s' % plugin in onStart:
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
        channels = anything('What channels? (separate channels by spaces)')
        afterConnect.append('join %s' % channels)
    postConnect = 'Would you like any commands to run ' \
                  'when the bot is finished connecting to the server?'
    while advanced and yn(postConnect) == 'y':
        postConnect = 'Would you like any other commands to run ' \
                      'when the bot is finished connecting to the server?'
        afterConnect.append(anything('What command?'))
    ###
    # Set owner user.
    ###
    if yn('Would you like to add an owner user?') == 'y':
        owner = anything('What should the owner\'s username be?')
        password = anything('What should the owner\'s password be?')
        user = ircdb.IrcUser()
        user.setPassword(password)
        user.addCapability('owner')
        while yn('Would you like to add a hostmask for the owner?') == 'y':
            user.addHostmask(anything('What hostmask?'))
        ircdb.users.setUser(owner, user)

    ###
    # Finito!
    ###
    for command in onStart:
        configfd.write(command)
        configfd.write('\n')
    configfd.write('\n')
    for command in afterConnect:
        configfd.write(command)
        configfd.write('\n')
    configfd.close()

    print
    print 'You\'re done!  Now run the bot with the command line:'
    print 'src/bot.py conf/%s' % name
    print
        
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
