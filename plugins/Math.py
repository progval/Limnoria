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
Various math-related commands.
"""

import plugins

import re
import math
import cmath
import types
import string
from itertools import imap

import unum.units

import debug
import utils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Math')

class Math(callbacks.Privmsg):
    ###
    # So this is how the 'calc' command works:
    # First, we make a nice little safe environment for evaluation; basically,
    # the names in the 'math' and 'cmath' modules.  Then, we remove the ability
    # of a random user to get ints evaluated: this means we have to turn all
    # int literals (even octal numbers and hexadecimal numbers) into floats.
    # Then we delete all square brackets, underscores, and whitespace, so no
    # one can do list comprehensions or call __...__ functions.
    ###
    _mathEnv = {'__builtins__': types.ModuleType('__builtins__'), 'i': 1j}
    _mathEnv.update(math.__dict__)
    _mathEnv.update(cmath.__dict__)
    _mathRe = re.compile(r'((?:(?<![A-Fa-f\d])-)?'
                         r'(?:0x[A-Fa-f\d]+|'
                         r'0[0-7]+|'
                         r'\d+\.\d+|'
                         r'\.\d+|'
                         r'\d+\.|'
                         r'\d+))')
    def _complexToString(self, x):
        real = x.real
        imag = x.imag
        if -1e-12 < real < 1e-12 and -1e-12 < imag < 1e-12:
            return '0'
        if int(real) == real:
            real = int(real)
        if int(imag) == imag:
            imag = int(imag)
        if -1e-12 < real < 1e-12:
            real = 0
        if -1e-12 < imag < 1e-12:
            imag = 0
        if imag == 0:
            return str(real)
        elif imag == 1:
            imag = '+i'
        elif imag == -1:
            imag = '-i'
        elif imag < 0:
            imag = '%si' % imag
        elif imag > 0:
            imag = '+%si' % imag
        if real == 0:
            return imag.lstrip('+')
        else:
            return '%s%s' % (real, imag)

    def calc(self, irc, msg, args):
        """<math expression>

        Returns the value of the evaluted <math expression>.  The syntax is
        Python syntax; the type of arithmetic is floating point.  Floating
        point arithmetic is used in order to prevent a user from being able to
        crash to the bot with something like 10**10**10**10.  One consequence
        is that large values such as 10**24 might not be exact.
        """
        text = privmsgs.getArgs(args)
        text = text.translate(string.ascii, '_[] \t')
        text = text.replace('lambda', '')
        #debug.printf(text)
        def handleMatch(m):
            s = m.group(1)
            if s.startswith('0x'):
                i = int(s, 16)
            elif s.startswith('0') and '.' not in s:
                try:
                    i = int(s, 8)
                except ValueError:
                    i = int(s)
            else:
                i = float(s)
            x = complex(i)
            if x == abs(x):
                x = abs(x)
            return str(x)
        text = self._mathRe.sub(handleMatch, text)
        #debug.printf(text)
        try:
            x = complex(eval(text, self._mathEnv, self._mathEnv))
            irc.reply(msg, self._complexToString(x))
        except OverflowError:
            irc.error(msg, 'Go get scanez, this is a *real* math problem!')
        except TypeError:
            irc.error(msg, 'Something in there wasn\'t a valid number.')
        except NameError, e:
            irc.error(msg, '%s is not a defined function.' % str(e).split()[1])
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

    _rpnEnv = {
        'dup': lambda s: s.extend([s.pop()]*2),
        }
    def rpn(self, irc, msg, args):
        """<rpn math expression>

        Returns the value of an RPN expression.
        """
        stack = []
        for arg in args:
            try:
                x = complex(arg)
                if x == abs(x):
                    x = abs(x)
                stack.append(x)
            except ValueError: # Not a float.
                if arg in self._mathEnv:
                    f = self._mathEnv[arg]
                    if callable(f):
                        called = False
                        arguments = []
                        while not called and stack:
                            arguments.append(stack.pop())
                            try:
                                stack.append(f(*arguments))
                                called = True
                            except TypeError:
                                pass
                        if not called:
                            irc.error(msg, 'Not enough arguments for %s' % arg)
                            return
                    else:
                        stack.append(f)
                elif arg in self._rpnEnv:
                    self._rpnEnv[arg](stack)
                else:
                    arg2 = stack.pop()
                    arg1 = stack.pop()
                    s = '%s%s%s' % (arg1, arg, arg2)
                    try:
                        stack.append(eval(s, self._mathEnv, self._mathEnv))
                    except SyntaxError:
                        irc.error(msg, '%r is not a defined function.' % arg)
                        return
        if len(stack) == 1:
            irc.reply(msg, str(self._complexToString(complex(stack[0]))))
        else:
            s = ', '.join(imap(self._complexToString, imap(complex, stack)))
            irc.reply(msg, 'Stack: [%s]' % s)

    _convertEnv = {'__builtins__': types.ModuleType('__builtins__')}
    for (k, v) in unum.units.__dict__.iteritems():
        if isinstance(v, unum.Unum):
            _convertEnv[k.lower()] = v
    def convert(self, irc, msg, args):
        """[<number>] <units> to <other units>

        Converts the first number of <units> to the <other units>.  Valid units
        expressions include the standard Python math operators applied to valid
        units.  If <number> isn't given, it defaults to 1.
        """
        if args and args[0].isdigit():
            n = args.pop(0)
        else:
            n = 1
        (unit1, to, unit2) = privmsgs.getArgs(args, required=3)
        if to != 'to':
            raise callbacks.ArgumentError
        try:
            n = float(n)
        except ValueError:
            irc.error(msg, '%s is not a valid number.' % n)
            return
        try:
            u1 = eval(unit1.lower(), self._convertEnv, self._convertEnv)
        except:
            irc.error(msg, '%s is not a valid units expression.' % unit1)
            return
        try:
            u2 = eval(unit2.lower(), self._convertEnv, self._convertEnv)
        except:
            irc.error(msg, '%s is not a valid units expression.' % unit2)
            return
        try:
            irc.reply(msg, str((n*u1).as(u2)))
        except Exception, e:
            irc.error(msg, str(e))

    def units(self, irc, msg, args):
        """takes no arguments

        Returns all the valid units.
        """
        L = self._convertEnv.keys()
        L.remove('__builtins__')
        L.sort()
        irc.reply(msg, utils.commaAndify(L))
        
        
Class = Math

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
