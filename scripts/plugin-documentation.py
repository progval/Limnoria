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

import os
import cgi
import imp
import sys
import os.path
import textwrap
import traceback

if 'src' not in sys.path:
    sys.path.insert(0, 'src')

from fix import *

import conf
import callbacks

if conf.pluginDir not in sys.path:
    sys.path.insert(0, conf.pluginDir)

def makePluginDocumentation(filename):
    trClasses = { 'dark':'light', 'light':'dark' }
    trClass = 'dark'
    pluginName = filename.split('.')[0]
    moduleInfo = imp.find_module(pluginName)
    module = imp.load_module(pluginName, *moduleInfo)
    directory = os.path.join('docs', 'plugins')
    if not os.path.exists(directory):
        os.mkdir(directory)
    plugin = module.Class()
    if isinstance(plugin, callbacks.Privmsg) and not \
       isinstance(plugin, callbacks.PrivmsgRegexp):
        fd = file(os.path.join(directory,'%s.html' % pluginName), 'w')
        fd.write(textwrap.dedent("""
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
        <html lang="en-us">
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <title>Documentation for the %s plugin for Supybot</title>
        <link rel="stylesheet" type="text/css" href="supybot.css">
        <body><div>
        %s<br><br><table>
        <tr id="headers"><td>Command</td><td>Args</td><td>
        Detailed Help</td></tr>
        """) % (pluginName, cgi.escape(module.__doc__)))
        for attr in dir(plugin):
            trClass = trClasses[trClass]
            if plugin.isCommand(attr):
                method = getattr(plugin, attr)
                if hasattr(method, '__doc__'):
                    doclines = method.__doc__.splitlines()
                    help = doclines.pop(0)
                    morehelp = 'This command has no detailed help.'
                    if doclines:
                        doclines = filter(None, doclines)
                        doclines = map(str.strip, doclines)
                        morehelp = ' '.join(doclines)
                    fd.write(textwrap.dedent("""
                    <tr class="%s"><td>%s</td><td>%s</td><td class="detail">%s
                    </td></tr>
                    """) % (trClass, attr, cgi.escape(help), cgi.escape(morehelp)))
        fd.write(textwrap.dedent("""
        </table>
        """))
        if hasattr(module, 'example'):
            s = module.example.encode('string-escape')
            s = s.replace('\\n', '\n')
            s = s.replace("\\'", "'")
            fd.write(textwrap.dedent("""
            <p>Here's an example session with this plugin:</p>
            <pre>
            %s
            </pre>
            """) % cgi.escape(s))
        fd.write(textwrap.dedent("""
        </div>
        </body>
        </html>
        """))
        fd.close()

if __name__ == '__main__':
    for filename in os.listdir(conf.pluginDir):
        if filename.endswith('.py') and filename.lower() != filename:
            makePluginDocumentation(filename)
            
    


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

