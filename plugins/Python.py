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
Various commands relating to Python (the programming language supybot is
written in) somehow.
"""

import plugins

import os
import re
import imp
import sys
import math
import random
import string
import urllib2

# Stupid printing on import...
from cStringIO import StringIO
sys.stdout = StringIO()
import this
sys.stdout = sys.__stdout__

import debug
import utils
import ircutils
import privmsgs
import callbacks

L = [os.__file__]
if hasattr(math, '__file__'):
    L.append(math.__file__)
pythonPath = map(os.path.dirname, L)

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Python')

example = utils.wrapLines("""
<jemfinch> @list Python
<supybot> jemfinch: pydoc, zen
<jemfinch> @zen
<supybot> jemfinch: Complex is better than complicated.
<jemfinch> @zen
<supybot> jemfinch: Beautiful is better than ugly.
<jemfinch> @pydoc list.reverse
<supybot> jemfinch: L.reverse() -- reverse *IN PLACE*
<jemfinch> @pydoc socket.socket
<supybot> jemfinch: socket([family[, type[, proto]]]) -> socket object. Open a socket of the given type. The family argument specifies the address family; it defaults to AF_INET. The type argument specifies whether this is a stream (SOCK_STREAM, this is the default) or datagram (SOCK_DGRAM) socket. The protocol argument defaults to 0, specifying the default protocol. Keyword arguments (4 more messages)
<jemfinch> @pydoc list
<supybot> jemfinch: list() -> new list list(sequence) -> new list initialized from sequence's items
""")

class Python(callbacks.PrivmsgCommandAndRegexp, plugins.Toggleable):
    modulechars = '%s%s%s' % (string.ascii_letters, string.digits, '_.')
    threaded = True
    regexps = ['aspnRecipes']
    toggles = plugins.ToggleDictionary({'ASPN' : True})

    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        plugins.Toggleable.__init__(self)

    def pydoc(self, irc, msg, args):
        """<python function>

        Returns the __doc__ string for a given Python function.
        """
        def normalize(s):
            return utils.normalizeWhitespace(s.replace('\n\n', '.'))
        funcname = privmsgs.getArgs(args)
        if funcname.translate(string.ascii, self.modulechars) != '':
            irc.error('That\'s not a valid module or function name.')
            return
        if '.' in funcname:
            parts = funcname.split('.')
            if len(parts) == 2 and parts[0] in __builtins__:
                (objectname, methodname) = parts
                obj = __builtins__[objectname]
                if hasattr(obj, methodname):
                    obj = getattr(obj, methodname)
                    if hasattr(obj, '__doc__'):
                        irc.reply(msg, normalize(obj.__doc__))
                    else:
                        irc.reply(msg, '%s has no documentation' % funcname)
                else:
                    irc.reply(msg, '%s has no method %s' % (parts[0],parts[1]))
            else:
                functionName = parts.pop()
                path = pythonPath
                for name in parts:
                    try:
                        info = imp.find_module(name, path)
                        newmodule = imp.load_module(name, *info)
                        path = [os.path.dirname(newmodule.__file__)]
                        if info[0] is not None:
                            info[0].close()
                    except ImportError:
                        if parts == ['os', 'path']:
                            newmodule = os.path
                        else:
                            irc.error(msg, 'No such module %s exists.' % name)
                            return
                if hasattr(newmodule, functionName):
                    f = getattr(newmodule, functionName)
                    if hasattr(f, '__doc__'):
                        s = f.__doc__.replace('\n\n', '. ')
                        s = utils.normalizeWhitespace(s)
                        irc.reply(msg, s)
                    else:
                        irc.error(msg, 'That function has no documentation.')
                else:
                    irc.error(msg, 'That function doesn\'t exist.')
        else:
            try:
                f = __builtins__[funcname]
                if hasattr(f, '__doc__'):
                    irc.reply(msg, normalize(f.__doc__))
                else:
                    irc.error(msg, 'That function has no documentation.')
            except SyntaxError:
                irc.error(msg, 'That\'s not a function!')
            except KeyError:
                irc.error(msg, 'That function doesn\'t exist.')
                
    _these = [str(s) for s in this.s.decode('rot13').splitlines() if s]
    _these.pop(0) # Initial line (The Zen of Python...)
    def zen(self, irc, msg, args):
        """takes no arguments

        Returns one of the zen of Python statements.
        """
        irc.reply(msg, random.choice(self._these))

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
        if not self.toggles.get('ASPN', channel=msg.args[0]):
            return
        url = match.group(0)
        fd = urllib2.urlopen(url)
        s = fd.read()
        fd.close()
        resp = []
        for r in self._searches:
            m = r.search(s)
            if m:
                resp.append('%s: %s' % self._bold(m.groups()))
        if resp:
            #debug.printf('; '.join(resp))
            irc.reply(msg, '; '.join(resp), prefixName = False)
            

Class = Python

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
