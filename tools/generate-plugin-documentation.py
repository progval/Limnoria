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
firstChars = {}

def genHeader(title, meta=''):
    return '''
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
                          "http://www.w3.org/TR/html4/strict.dtd">
    <html lang="en-us">
    <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>%s</title>
    <link rel="stylesheet" type="text/css"
          href="http://supybot.sourceforge.net/css/supybot.css">
    %s
    <body><div>
    ''' % (title, meta)

def genNavbar(path, cActive=True):
    download = 'http://sourceforge.net/project/showfiles.php?group_id=58965'
    bug = 'http://sourceforge.net/tracker/?func=add&amp;group_id=58965&amp;'\
          'atid=489447'
    if cActive:
        command = '<li>\n<a href="%scommands.html">Commands Index</a>\n</li>'\
                  % path[3:]
    else:
        command = '<li class="plain">\nCommands Index\n</li>'
    return '''
        <div id="nav">
        <ul>
          <li>
            <a href="%s">Home</a>
          </li>
          <li>
            <a href="http://sourceforge.net/projects/supybot/">Sourceforge Project</a>
          </li>
          <li>
            <a href="%s">
              Download
            </a>
          </li>
          <li>
            <a
            href="%s">
              Submit a Bug
            </a>
          </li>
          %s
          <li>
            <a href="http://forums.supybot.org"/>Forums</a>
          </li>
        </ul>
        <p style="clear:both; margin:0; padding:0;"></p>
        </div>
        ''' % (path, download, bug, command)

def genFooter():
    return '''
    </div>
    <div style="text-align: center"><br /><!-- Buttons -->
      <a href="http://validator.w3.org/check/referer"><img
          src="http://www.w3.org/Icons/valid-html401"
          alt="Valid HTML 4.01!" height="31" width="88" /></a>

      <a href="http://jigsaw.w3.org/css-validator/check/referer"><img
         src="http://jigsaw.w3.org/css-validator/images/vcss" 
         alt="Valid CSS!" /></a>

      <a href="http://sourceforge.net"><img
         src="http://sourceforge.net/sflogo.php?group_id=58965&amp;type=1"
         width="88" height="31" alt="SourceForge.net Logo" /></a>
    </div>
    </body>
    </html>
    '''

def prepIndex():
    directory = os.path.join('docs', 'plugins')
    if not os.path.exists(directory):
        os.mkdir(directory)
    fd = file(os.path.join('docs', 'plugins.html'), 'w')
    fd.write(textwrap.dedent('''
        %s
        <div class="maintitle">Supybot Plugin Documentation Index</div>
        %s
        <div class="mainbody">
        ''' % (genHeader('Supybot Plugin Documentation'), genNavbar('../'))))
    fd.close()

def makePluginDocumentation(pluginWindow):
    global commandDict
    global firstChars
    trClasses = { 'even':'odd', 'odd':'even' }
    trClass = 'even'
    (pluginName, module, plugin) = pluginWindow[1]
    print 'Generating documentation for %s.py' % pluginName
    prev = pluginWindow[0][0] or '../plugins'
    next = pluginWindow[2][0] or '../plugins'
    # can't use string.capitalize() because it lowercases every character
    # except the first. must create our own capitalized names
    cpluginName = '%s%s' % (pluginName[0].upper(), pluginName[1:])
    temp = prev.strip('./')
    cprev = '%s%s' % (temp[0].upper(), temp[1:])
    temp = next.strip('./')
    cnext = '%s%s' % (temp[0].upper(), temp[1:])
    directory = os.path.join('docs', 'plugins')
    if not os.path.exists(directory):
        os.mkdir(directory)
    id = file(os.path.join('docs', 'plugins.html'), 'a')
    id.write('<strong><a href="plugins/%s.html">%s</a></strong>\n' %
             (pluginName, cpluginName))
    fd = file(os.path.join(directory,'%s.html' % pluginName), 'w')
    title = 'Documentation for the %s plugin for Supybot' % pluginName
    meta = '''
    <link rel="home" title="Plugin Documentation Index" href="../plugins.html">
    <link rel="next" href="%s.html">
    <link rel="previous" href="%s.html">
    ''' % (next, prev)
    fd.write(textwrap.dedent('''
    %s
    <div class="plugintitle">%s</div>
    %s
    <div class="mainbody" style="padding: 0;">
    <table>
    <tr id="headers"><td>Command</td><td>Args</td><td>
    Detailed Help</td></tr>
    ''' % (genHeader(title, meta),
           cgi.escape(module.__doc__ or ""),
           genNavbar('../../'))))
    attrs = [x for x in dir(plugin) if plugin.isCommand(x) and not
             x.startswith('_')]
    id.write('(%s)<br />\n' % ', '.join(attrs))
    for attr in attrs:
        if attr in commandDict:
            commandDict[attr].append(pluginName)
        else:
            commandDict[attr] = [pluginName]
        if attr[0] not in firstChars:
            firstChars[attr[0]] = ''
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
            fd.write(textwrap.dedent('''
            <tr class="%s" id="%s"><td>%s</td><td>%s</td>
            <td class="detail">%s</td></tr>
            ''' % (trClass, attr, attr, help, morehelp)))
    fd.write('</table>\n')
    fd.write(textwrap.dedent('''
    </div>
    </div>
    <div style="text-align: center;">
    <br />
    <a href="%s.html">&lt;- %s</a> |
    <a href="../plugins.html">Plugins Index</a> |
    <a href="../commands.html">Commands Index</a> |
    <a href="%s.html">%s -&gt;</a>
    %s
    ''' % (prev, cprev, next, cnext, genFooter())))
    fd.close()
    id.close()

def finishIndex():
    directory = 'docs'
    if not os.path.exists(directory):
        os.mkdir(directory)
    fd = file(os.path.join(directory, 'plugins.html'), 'a')
    fd.write(textwrap.dedent('</div>\n%s' % genFooter()))
    fd.close()

def makeCommandsIndex():
    from string import ascii_lowercase
    global commandDict
    global firstChars
    directory = 'docs'
    if not os.path.exists(directory):
        os.mkdir(directory)
    fd = file(os.path.join(directory, 'commands.html'), 'w')
    title = 'Supybot Commands Index'
    fd.write(textwrap.dedent('''
    %s
    <div class="maintitle">%s</div>
    %s
    <div class="mainbody" style="text-align: center;">
    ''' % (genHeader(title),
           title,
           genNavbar('../', cActive=False))))
    commands = [c for c in commandDict.iterkeys()]
    commands.sort()
    for i in ascii_lowercase:
        if i in firstChars:
            fd.write('<a href="#%s">%s</a> \n' % (i, i.capitalize()))
        else:
            fd.write('%s ' % i.capitalize())
    firstChars.clear()
    fd.write('</div>\n<br />')
    pluginLink = '<a href="plugins/%s.html#%s">%s</a>'
    for command in commands:
        c = command[0]
        if c not in firstChars:
            if firstChars:
                fd.write('</div><br />\n')
            fd.write('\n<div class="whitebox">')
            firstChars[c] = ''
            fd.write('<div id="%s" class="letter">%s</div>\n' %
                     (c, c.capitalize()))
        plugins = commandDict[command]
        plugins.sort()
        fd.write('<strong>%s</strong>   (%s)<br />\n' %
                 (command,
                  ', \n\t'.join([pluginLink % (p,command,p) for p in plugins])))
    fd.write('\n</div>')
    fd.write(textwrap.dedent(genFooter()))
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
    plugins.insert(0, [None])
    plugins.append([None])
    for pluginWindow in window(plugins, 3):
        makePluginDocumentation(pluginWindow)
    finishIndex()
    makeCommandsIndex()
            
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

