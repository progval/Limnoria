#!/usr/bin/env python3

###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import supybot

import os
import sys
import time
import os.path
import optparse

def error(s):
    sys.stderr.write(textwrap.fill(s))
    sys.stderr.write(os.linesep)
    sys.exit(-1)

import supybot.conf as conf
from supybot.questions import *

copyright = '''
###
# Copyright (c) %s, %%s
# All rights reserved.
#
%%s
###
''' % time.strftime('%Y')
# Here we use strip() instead of lstrip() on purpose.
copyright = copyright.strip()

license = '''
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
'''
license = license.lstrip()

pluginTemplate = '''
%s

from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
from supybot.i18n import PluginInternationalization


_ = PluginInternationalization('%s')


class %s(callbacks.Plugin):
    """%s"""
    %s


Class = %s


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
'''.lstrip() # This removes the newlines that precede and follow the text.

configTemplate = '''
%s

from supybot import conf, registry
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('%s')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin(%r, True)


%s = conf.registerPlugin(%r)
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(%s, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
'''.lstrip()


__init__Template = '''
%s

"""
%s: %s
"""

import sys
import supybot
from supybot import world

# Use this for the version of this plugin.
__version__ = ""

# XXX Replace this with an appropriate author or supybot.Author instance.
__author__ = supybot.authors.unknown

# This is a dictionary mapping supybot.Author instances to lists of
# contributions.
__contributors__ = {}

# This is a url where the most recent plugin package can be downloaded.
__url__ = ''

from . import config
from . import plugin
from importlib import reload
# In case we're being reloaded.
reload(config)
reload(plugin)
# Add more reloads here if you add third-party modules and want them to be
# reloaded when this plugin is reloaded.  Don't forget to import them as well!

if world.testing:
    from . import test

Class = plugin.Class
configure = config.configure


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
'''.lstrip()

setupTemplate = '''
%s

from supybot.setup import plugin_setup

plugin_setup(
    %r,
)
'''.lstrip()

testTemplate = '''
%s

from supybot.test import *


class %sTestCase(PluginTestCase):
    plugins = (%r,)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
'''.lstrip()

readmeTemplate = '''
%s
'''.lstrip()

def _main():
    global copyright
    global license
    parser = optparse.OptionParser(usage='Usage: %prog [options]',
                                   version='Supybot %s' % conf.version)
    parser.add_option('-n', '--name', action='store', dest='name',
                      help='sets the name for the plugin.')
    parser.add_option('-t', '--thread', action='store_true', dest='threaded',
                      help='makes the plugin threaded.')
    parser.add_option('-a', '--author', '--real-name', action='store',
                      dest='realName', help='Determines who the copyright is '
                      'assigned to.')
    parser.add_option('-d', '--desc', action='store', dest='desc',
                      help='Short description of plugin.')
    (options, args) = parser.parse_args()
    if options.name:
        name = options.name
        threaded = options.threaded
    else:
        name = something('What should the name of the plugin be?')
        if name.endswith('.py'):
            name = name[:-3]
        while name[0].islower():
            print('Plugin names must begin with a capital letter.')
            name = something('What should the name of the plugin be?')
            if name.endswith('.py'):
                name = name[:-3]

        if os.path.exists(name):
            error('A file or directory named %s already exists; remove or '
                  'rename it and run this program again.' % name)

        print(textwrap.fill(textwrap.dedent("""
        Sometimes you'll want a callback to be threaded.  If its methods
        (command or regexp-based, either one) will take a significant amount
        of time to run, you'll want to thread them so they don't block the
        entire bot.""").strip()))
        print()
        threaded = yn('Does your plugin need to be threaded?')

    if options.realName:
        realName = options.realName
    else:
        realName = something(textwrap.dedent("""
        What is your name, so I can fill in the copyright and license
        appropriately?
        """).strip())

        if not yn('Do you wish to use Supybot\'s license for your plugin?'):
            license = '#'

    if not options.desc:
        options.desc = something(textwrap.dedent("""
            Please provide a short description of the plugin:
            """).strip())

    if threaded:
        threaded = 'threaded = True'
    else:
        threaded = 'pass'
    if name.endswith('.py'):
        name = name[:-3]
    while name[0].islower():
        print('Plugin names must begin with a capital letter.')
        name = something('What should the name of the plugin be?')
        if name.endswith('.py'):
            name = name[:-3]
    copyright %= (realName, license)
    pathname = name

    # Make the directory.
    os.mkdir(pathname)

    def writeFile(filename, s):
        fd = open(os.path.join(pathname, filename), 'w')
        try:
            fd.write(s)
        finally:
            fd.close()

    writeFile('plugin.py', pluginTemplate % (copyright, name, name,
                                             options.desc, threaded, name))
    writeFile('config.py', configTemplate % (copyright, name, name, name, name,
                                             name))
    writeFile('__init__.py', __init__Template % (copyright, name, options.desc))
    writeFile('setup.py', setupTemplate % (copyright, name))
    writeFile('test.py', testTemplate % (copyright, name, name))
    writeFile('README.md', readmeTemplate % (options.desc,))

    pathname = os.path.join(pathname, 'local')
    os.mkdir(pathname)
    writeFile('__init__.py',
              '# Stub so local is a module, used for third-party modules\n')

    print('Your new plugin template is in the %s directory.' % name)

def main():
    try:
        _main()
    except KeyboardInterrupt:
        print()
        output("""It looks like you cancelled out of this script before it was
        finished.  Obviously, nothing was written, but just run this script
        again whenever you want to generate a template for a plugin.""")

if __name__ == '__main__':
    main()

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
