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

import supybot

import os
import cgi
import imp
import sys
import os.path
import textwrap
import traceback

import conf
conf.dataDir = 'test-data'
conf.confDir = 'test-conf'
conf.logDir = 'test-log'

import debug
import callbacks

commandDict = {}

def prepIndex():
    directory = os.path.join('docs', 'plugins')
    if not os.path.exists(directory):
        os.mkdir(directory)
    fd = file(os.path.join(directory, 'index.html'), 'w')
    fd.write(textwrap.dedent("""
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
                          "http://www.w3.org/TR/html4/strict.dtd">
    <html lang="en-us">
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Supybot plugin documentation</title>
    <link rel="stylesheet" type="text/css" href="supybot.css">
    <body><div>
    <h2>Supybot Plugin Documentation Index</h2>
    <strong>Plugin</strong>   (Command list)<br><br>
    """))
    fd.close()

def makePluginDocumentation(pluginWindow):
    global commandDict
    trClasses = { 'treven':'trodd', 'trodd':'treven' }
    trClass = 'treven'
    (pluginName, module, plugin) = pluginWindow[1]
    print 'Generating documentation for %s.py' % pluginName
    prev = pluginWindow[0][0] or 'index'
    next = pluginWindow[2][0] or 'index'
    directory = os.path.join('docs', 'plugins')
    if not os.path.exists(directory):
        os.mkdir(directory)
    id = file(os.path.join(directory, 'index.html'), 'a')
    id.write(textwrap.dedent("""
    <strong><a href="%s.html">%s</a></strong> 
    """ % (pluginName, pluginName.capitalize())))
    fd = file(os.path.join(directory,'%s.html' % pluginName), 'w')
    fd.write(textwrap.dedent("""
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
                          "http://www.w3.org/TR/html4/strict.dtd">
    <html lang="en-us">
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Documentation for the %s plugin for Supybot</title>
    <link rel="stylesheet" type="text/css" href="supybot.css">
    <link rel="home" title="Plugin Documentation Index" href="index.html">
    <link rel="next" href="%s.html">
    <link rel="previous" href="%s.html">
    <body><div>
    <h2>%s</h2><br><br><table>
    <tr id="headers"><td>Command</td><td>Args</td><td>
    Detailed Help</td></tr>
    """) % (pluginName, next, prev, cgi.escape(module.__doc__ or "")))
    attrs = [x for x in dir(plugin) if plugin.isCommand(x) and not
             x.startswith('_')]
    id.write('(%s)<br>\n' % ', '.join(attrs))
    for attr in attrs:
        if attr in commandDict:
            commandDict[attr].append(pluginName)
        else:
            commandDict[attr] = [pluginName]
        method = getattr(plugin, attr)
        if hasattr(method, '__doc__'):
            doclines = method.__doc__.splitlines()
            help = doclines.pop(0)
            morehelp = 'This command has no detailed help.'
            if doclines:
                doclines = filter(None, doclines)
                doclines = map(str.strip, doclines)
                morehelp = ' '.join(doclines)
            help = cgi.escape(help)
            morehelp = cgi.escape(morehelp)
            trClass = trClasses[trClass]
            fd.write(textwrap.dedent("""
            <tr class="%s"><td>%s</td><td>%s</td><td class="detail">%s
            </td></tr>
            """) % (trClass, attr, help, morehelp))
    fd.write(textwrap.dedent("""
    </table>
    """))
    if hasattr(module, 'example'):
        s = module.example.encode('string-escape')
        s = s.replace('\\n', '\n')
        s = s.replace("\\'", "'")
        fd.write(textwrap.dedent("""
        <h2><p>Here's an example session with this plugin:</p></h2>
        <pre>
        %s
        </pre>
        """) % cgi.escape(s))
    fd.write(textwrap.dedent("""
    </div>
    <div style="text-align:center">
    <br>
    <a href="%s.html">&lt;- %s</a> | <a href="index.html">Index</a> | <a
    href="%s.html">%s -&gt;</a>
    </div>
    </body>
    </html>
    """ % (prev, prev.capitalize(), next, next.capitalize())))
    fd.close()
    id.close()

def finishIndex():
    directory = os.path.join('docs', 'plugins')
    if not os.path.exists(directory):
        os.mkdir(directory)
    fd = file(os.path.join(directory, 'index.html'), 'a')
    fd.write(textwrap.dedent("""
    </div>
    </body>
    </html>
    """))
    fd.close()

def makeCommandsIndex():
    global commandDict
    directory = os.path.join('docs', 'plugins')
    if not os.path.exists(directory):
        os.mkdir(directory)
    fd = file(os.path.join(directory, 'commands.html'), 'w')
    fd.write(textwrap.dedent("""
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
                          "http://www.w3.org/TR/html4/strict.dtd">
    <html lang="en-us">
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Supybot Commands Index</title>
    <link rel="stylesheet" type="text/css" href="supybot.css">
    <body><div>
    <h2>Supybot Commands Index</h2>
    <strong>Command</strong>   (Plugins)<br><br>
    """))
    commands = [c for c in commandDict.iterkeys()]
    commands.sort()
    for command in commands:
        plugins = commandDict[command]
        plugins.sort()
        fd.write('<strong>%s</strong>   (%s)<br>\n' % (command,
                 ', '.join(['<a href="%s.html">%s</a>' % (p, p)
                            for p in plugins])))
    fd.write(textwrap.dedent("""
    </div>
    </body>
    </html>
    """))
    fd.close()

def genPlugins():
    for directory in conf.pluginDirs:
        for filename in os.listdir(directory):
            if filename.endswith('.py') and filename[0].isupper():
                pluginName = filename.split('.')[0]
                moduleInfo = imp.find_module(pluginName, conf.pluginDirs)
                module = imp.load_module(pluginName, *moduleInfo)
                if not hasattr(module, 'Class'):
                    print '%s is not a plugin.' % filename
                    continue
                try:
                    plugin = module.Class()
                except Exception, e:
                    print '%s could not be loaded: %s' % (filename,
                                                          debug.exnToString(e))
                    continue
                if isinstance(plugin, callbacks.Privmsg) and not \
                   isinstance(plugin, callbacks.PrivmsgRegexp):
                    yield (pluginName, module, plugin)

if __name__ == '__main__':
    prepIndex()
    plugins = [p for p in genPlugins()]
    plugins.sort()
    plugins = [(None,)] + plugins + [(None,)]
    for pluginWindow in window(plugins, 3):
        makePluginDocumentation(pluginWindow)
    finishIndex()
    makeCommandsIndex()
            
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

