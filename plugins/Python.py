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
Various commands relating to Python (the programming language Supybot is
written in) somehow.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import os
import re
import imp
import sys
import math
import random
import string

# Stupid printing on import...
from cStringIO import StringIO
try:
    sys.stdout = StringIO()
    import this
finally:
    sys.stdout = sys.__stdout__

import supybot.conf as conf
import supybot.utils as utils
import supybot.webutils as webutils
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

L = [os.__file__]
if hasattr(math, '__file__'):
    L.append(math.__file__)
pythonPath = map(os.path.dirname, L)

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Python', True)
    if yn("""This plugin provides a snarfer for ASPN Python Recipe URLs;
             it will output the name of the Recipe when it sees such a URL.
             Would you like to enable this snarfer?"""):
        conf.supybot.plugins.Python.aspnSnarfer.setValue(True)

conf.registerPlugin('Python')
conf.registerChannelValue(conf.supybot.plugins.Python, 'aspnSnarfer',
    registry.Boolean(False, """Determines whether the ASPN Python recipe
    snarfer is enabled.  If so, it will message the channel with the name of
    the recipe when it see an ASPN Python recipe link on the channel."""))

class Python(callbacks.PrivmsgCommandAndRegexp):
    modulechars = '%s%s%s' % (string.ascii_letters, string.digits, '_.')
    regexps = ['aspnRecipes']
    def pydoc(self, irc, msg, args):
        """<python function>

        Returns the __doc__ string for a given Python function.
        """
        def normalize(s):
            return utils.normalizeWhitespace(s.replace('\n\n', '.  '))
        def getModule(name, path=pythonPath):
            if name in sys.modules:
                return sys.modules[name]
            else:
                parts = name.split('.')
                for name in parts:
                    try:
                        info = imp.find_module(name, path)
                        newmodule = imp.load_module(name, *info)
                        path = [os.path.dirname(newmodule.__file__)]
                        if info[0] is not None:
                            info[0].close()
                    except ImportError:
                        if parts == ['os', 'path']:
                            return os.path
                        else:
                            return None
                return newmodule
        name = privmsgs.getArgs(args)
        if name.translate(string.ascii, self.modulechars) != '':
            irc.error('That\'s not a valid module or function name.')
            return
        if '.' in name:
            (moduleName, funcName) = rsplit(name, '.', 1)
            if moduleName in __builtins__:
                obj = __builtins__[moduleName]
                if hasattr(obj, funcName):
                    obj = getattr(obj, funcName)
                    if hasattr(obj, '__doc__'):
                        irc.reply(normalize(obj.__doc__))
                    else:
                        irc.reply('%s has no documentation.' % name)
                else:
                    s = '%s has no method %s.' % (moduleName, funcName)
                    irc.reply(s)
            elif moduleName:
                newmodule = getModule(moduleName)
                if newmodule is None:
                    irc.error('No module %s exists.' % moduleName)
                else:
                    if hasattr(newmodule, funcName):
                        f = getattr(newmodule, funcName)
                        if hasattr(f, '__doc__') and f.__doc__:
                            s = normalize(f.__doc__)
                            irc.reply(s)
                        else:
                            irc.error('%s has no documentation.' % name)
                    else:
                        s = '%s has no function %s.' % (moduleName, funcName)
                        irc.error(s)
        else:
            if name in sys.modules:
                newmodule = sys.modules[name]
                if hasattr(newmodule, '__doc__') and newmodule.__doc__:
                    irc.reply(normalize(newmodule.__doc__))
                else:
                    irc.reply('Module %s has no documentation.' % name)
            elif name in __builtins__:
                f = __builtins__[name]
                if hasattr(f, '__doc__') and f.__doc__:
                    irc.reply(normalize(f.__doc__))
                else:
                    irc.error('That function has no documentation.')
            else:
                irc.error('No function or module %s exists.' % name)

    _these = [str(s) for s in this.s.decode('rot13').splitlines() if s]
    _these.pop(0) # Initial line (The Zen of Python...)
    def zen(self, irc, msg, args):
        """takes no arguments

        Returns one of the zen of Python statements.
        """
        irc.reply(random.choice(self._these))

    _title = re.compile(r'<b>(Title):</b>&nbsp;(.*)', re.I)
    _submit = re.compile(r'<b>(Submitter):</b>&nbsp;(.*)', re.I)
    _update = re.compile(r'<b>Last (Updated):</b>&nbsp;(.*)', re.I)
    _version = re.compile(r'<b>(Version) no:</b>&nbsp;(.*)', re.I)
    _category = re.compile(r'<b>(Category):</b>.*?<a href[^>]+>(.*?)</a>',
        re.I | re.S)
    _description = re.compile(r'<p><b>(Description):</b></p>.+?<p>(.+?)</p>',
        re.I | re.S)
    _searches = (_title, _submit, _update, _version, _category, _description)
    _bold = lambda self, g: (ircutils.bold(g[0]),) + g[1:]
    def aspnRecipes(self, irc, msg, match):
        r"http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/\d+"
        if not self.registryValue('aspnSnarfer', msg.args[0]):
            return
        url = match.group(0)
        s = webutils.getUrl(url)
        resp = []
        for r in self._searches:
            m = r.search(s)
            if m:
                resp.append('%s: %s' % self._bold(m.groups()))
        if resp:
            irc.reply('; '.join(resp), prefixName = False)
    aspnRecipes = privmsgs.urlSnarfer(aspnRecipes)


Class = Python

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
