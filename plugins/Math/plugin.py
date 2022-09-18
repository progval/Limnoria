###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2009, James McCoy
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

from __future__ import division

import re
import math
import cmath
import types
import string

import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Math')

from .local import convertcore
from supybot.utils.math_evaluator import safe_eval, InvalidNode, SAFE_ENV

baseArg = ('int', 'base', lambda i: i <= 36)

class Math(callbacks.Plugin):
    """Provides commands to work with math, such as a calculator and
    a unit converter."""
    @internationalizeDocstring
    def base(self, irc, msg, args, frm, to, number):
        """<fromBase> [<toBase>] <number>

        Converts <number> from base <fromBase> to base <toBase>.
        If <toBase> is left out, it converts to decimal.
        """
        if not number:
            number = str(to)
            to = 10
        try:
            irc.reply(self._convertBaseToBase(number, to, frm))
        except ValueError:
            irc.error(_('Invalid <number> for base %s: %s') % (frm, number))
    base = wrap(base, [('int', 'base', lambda i: 2 <= i <= 36),
                       optional(('int', 'base', lambda i: 2 <= i <= 36), 10),
                       additional('something')])

    def _convertDecimalToBase(self, number, base):
        """Convert a decimal number to another base; returns a string."""
        if number == 0:
            return '0'
        elif number < 0:
            negative = True
            number = -number
        else:
            negative = False
        digits = []
        while number != 0:
            digit = number % base
            if digit >= 10:
                digit = string.ascii_uppercase[digit - 10]
            else:
                digit = str(digit)
            digits.append(digit)
            number = number // base
        digits.reverse()
        return '-'*negative + ''.join(digits)

    def _convertBaseToBase(self, number, toBase, fromBase):
        """Convert a number from any base, 2 through 36, to any other
        base, 2 through 36. Returns a string."""
        number = minisix.long(str(number), fromBase)
        if toBase == 10:
            return str(number)
        return self._convertDecimalToBase(number, toBase)

    def _floatToString(self, x):
        if -1e-10 < x < 1e-10:
            return '0'
        elif -1e-10 < int(x) - x < 1e-10:
            return str(int(x))
        else:
            return str(x)

    def _complexToString(self, x):
        realS = self._floatToString(x.real)
        imagS = self._floatToString(x.imag)
        if imagS == '0':
            return realS
        elif imagS == '1':
            imagS = '+i'
        elif imagS == '-1':
            imagS = '-i'
        elif x.imag < 0:
            imagS = '%si' % imagS
        else:
            imagS = '+%si' % imagS
        if realS == '0' and imagS == '0':
            return '0'
        elif realS == '0':
            return imagS.lstrip('+')
        elif imagS == '0':
            return realS
        else:
            return '%s%s' % (realS, imagS)

    @internationalizeDocstring
    def calc(self, irc, msg, args, text):
        """<math expression>

        Returns the value of the evaluated <math expression>.  The syntax is
        Python syntax; the type of arithmetic is floating point.  Floating
        point arithmetic is used in order to prevent a user from being able to
        crash to the bot with something like '10**10**10**10'.  One consequence
        is that large values such as '10**24' might not be exact.
        """
        try:
            self.log.info('evaluating %q from %s', text, msg.prefix)
            x = complex(safe_eval(text, allow_ints=False))
            irc.reply(self._complexToString(x))
        except OverflowError:
            maxFloat = math.ldexp(0.9999999999999999, 1024)
            irc.error(_('The answer exceeded %s or so.') % maxFloat)
        except InvalidNode as e:
            irc.error(_('Invalid syntax: %s') % e.args[0])
        except NameError as e:
            irc.error(_('%s is not a defined function.') % e.args[0])
        except MemoryError:
            irc.error(_('Memory error (too much recursion?)'))
        except Exception as e:
            irc.error(str(e))
    calc = wrap(calc, ['text'])

    @internationalizeDocstring
    def icalc(self, irc, msg, args, text):
        """<math expression>

        This is the same as the calc command except that it allows integer
        math, and can thus cause the bot to suck up CPU.  Hence it requires
        the 'trusted' capability to use.
        """
        try:
            self.log.info('evaluating %q from %s', text, msg.prefix)
            result = safe_eval(text, allow_ints=True)
            float(result)  # fail early if it is too large to be displayed
        except OverflowError:
            maxFloat = math.ldexp(0.9999999999999999, 1024)
            irc.error(_('The answer exceeded %s or so.') % maxFloat)
        except InvalidNode as e:
            irc.error(_('Invalid syntax: %s') % e.args[0])
        except NameError as e:
            irc.error(_('%s is not a defined function.') % str(e).split()[1])
        except Exception as e:
            irc.error(utils.exnToString(e))
        else:
            try:
                result_str = str(result)
            except ValueError as e:
                # Probably too large to be converted to string; go through
                # floats instead.
                # https://docs.python.org/3/library/stdtypes.html#int-max-str-digits
                # (Depending on configuration, this may be dead code because it
                # is caught by the float() check above.
                result_str = str(float(result))
            irc.reply(result_str)
    icalc = wrap(icalc, [('checkCapability', 'trusted'), 'text'])

    _rpnEnv = {
        'dup': lambda s: s.extend([s.pop()]*2),
        'swap': lambda s: s.extend([s.pop(), s.pop()])
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
                if arg in SAFE_ENV:
                    f = SAFE_ENV[arg]
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
                            irc.error(_('Not enough arguments for %s') % arg)
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
                        stack.append(safe_eval(s, allow_ints=False))
                    except SyntaxError:
                        irc.error(format(_('%q is not a defined function.'),
                                         arg))
                        return
        if len(stack) == 1:
            irc.reply(str(self._complexToString(complex(stack[0]))))
        else:
            s = ', '.join(map(self._complexToString, list(map(complex, stack))))
            irc.reply(_('Stack: [%s]') % s)

    @internationalizeDocstring
    def convert(self, irc, msg, args, number, unit1, unit2):
        """[<number>] <unit> to <other unit>

        Converts from <unit> to <other unit>. If number isn't given, it
        defaults to 1. For unit information, see 'units' command.
        """
        try:
            digits = len(str(number).split('.')[1])
        except IndexError:
            digits = 0
        try:
            newNum = convertcore.convert(number, unit1, unit2)
            if isinstance(newNum, float):
                zeros = 0
                for char in "{:f}".format(newNum).split('.')[1]:
                    if char != '0':
                        break
                    zeros += 1
                # Let's add one signifiant digit. Physicists would not like
                # that, but common people usually do not give extra zeros...
                # (for example, with '32 C to F', an extra digit would be
                # expected).
                newNum = round(newNum, digits + 1 + zeros)
            newNum = self._floatToString(newNum)
            irc.reply(str(newNum))
        except convertcore.UnitDataError as ude:
            irc.error(str(ude))
    convert = wrap(convert, [optional('float', 1.0),'something','to','text'])

    @internationalizeDocstring
    def units(self, irc, msg, args, type):
        """ [<type>]

        With no arguments, returns a list of measurement types, which can be
        passed as arguments. When called with a type as an argument, returns
        the units of that type.
        """

        irc.reply(convertcore.units(type))
    units = wrap(units, [additional('text')])

Class = Math

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
