#!/usr/bin/python

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
import imp
import sys
import math
import random
import string

# Stupid printing on import...
from cStringIO import StringIO
sys.stdout = StringIO()
import this
sys.stdout = sys.__stdout__

import utils
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
Add an example IRC session using this module here.
""")

class Python(callbacks.Privmsg):
    modulechars = '%s%s%s' % (string.ascii_letters, string.digits, '_.')
    def pydoc(self, irc, msg, args):
        """<python function>

        Returns the __doc__ string for a given Python function.
        """
        funcname = privmsgs.getArgs(args)
        if funcname.translate(string.ascii, self.modulechars) != '':
            irc.error('That\'s not a valid module or function name.')
            return
        if '.' in funcname:
            parts = funcname.split('.')
            functionName = parts.pop()
            path = pythonPath
            for name in parts:
                try:
                    info = imp.find_module(name, path)
                    newmodule = imp.load_module(name, *info)
                    path = [os.path.dirname(newmodule.__file__)]
                    info[0].close()
                except ImportError:
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
                    s = f.__doc__.replace('\n\n', '. ')
                    s = utils.normalizeWhitespace(s)
                    irc.reply(msg, s)
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


Class = Python

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
