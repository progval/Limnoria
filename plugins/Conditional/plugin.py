###
# Copyright (c) 2010, Daniel Folkinshteyn
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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import re

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('Conditional')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

if isinstance(__builtins__, dict):
    _any = __builtins__['any']
    _all = __builtins__['all']
else:
    _any = __builtins__.any
    _all = __builtins__.all

class Conditional(callbacks.Plugin):
    """Add the help for "@plugin help Conditional" here
    This should describe *how* to use this plugin."""
    threaded = True
    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)

    def _runCommandFunction(self, irc, msg, command):
        """Run a command from message, as if command was sent over IRC."""
        tokens = callbacks.tokenize(command)
        try:
            self.Proxy(irc.irc, msg, tokens)
        except Exception as e:
            self.log.exception('Uncaught exception in requested function:')

    @internationalizeDocstring
    def cif(self, irc, msg, args, condition, ifcommand, elsecommand):
        """<condition> <ifcommand> <elsecommand>

        Runs <ifcommand> if <condition> evaluates to true, runs <elsecommand>
        if it evaluates to false.

        Use other logical operators defined in this plugin and command nesting
        to your advantage here.
        """
        if condition:
            self._runCommandFunction(irc, msg, ifcommand)
        else:
            self._runCommandFunction(irc, msg, elsecommand)
        irc.noReply()
    cif = wrap(cif, ['boolean', 'something', 'something'])

    @internationalizeDocstring
    def cand(self, irc, msg, args, conds):
        """<cond1> [<cond2> ... <condN>]

        Returns true if all conditions supplied evaluate to true.
        """
        if _all(conds):
            irc.reply("true")
        else:
            irc.reply("false")
    cand = wrap(cand, [many('boolean'),])

    @internationalizeDocstring
    def cor(self, irc, msg, args, conds):
        """<cond1> [<cond2> ... <condN>]

        Returns true if any one of conditions supplied evaluates to true.
        """
        if _any(conds):
            irc.reply("true")
        else:
            irc.reply("false")
    cor = wrap(cor, [many('boolean'),])

    @internationalizeDocstring
    def cxor(self, irc, msg, args, conds):
        """<cond1> [<cond2> ... <condN>]

        Returns true if only one of conditions supplied evaluates to true.
        """
        if sum(conds) == 1:
            irc.reply("true")
        else:
            irc.reply("false")
    cxor = wrap(cxor, [many('boolean'),])

    @internationalizeDocstring
    def ceq(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a string comparison on <item1> and <item2>.
        Returns true if they are equal.
        """
        if item1 == item2:
            irc.reply('true')
        else:
            irc.reply('false')
    ceq = wrap(ceq, ['anything', 'anything'])

    @internationalizeDocstring
    def ne(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a string comparison on <item1> and <item2>.
        Returns true if they are not equal.
        """
        if item1 != item2:
            irc.reply('true')
        else:
            irc.reply('false')
    ne = wrap(ne, ['anything', 'anything'])

    @internationalizeDocstring
    def gt(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a string comparison on <item1> and <item2>.
        Returns true if <item1> is greater than <item2>.
        """
        if item1 > item2:
            irc.reply('true')
        else:
            irc.reply('false')
    gt = wrap(gt, ['anything', 'anything'])

    @internationalizeDocstring
    def ge(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a string comparison on <item1> and <item2>.
        Returns true if <item1> is greater than or equal to <item2>.
        """
        if item1 >= item2:
            irc.reply('true')
        else:
            irc.reply('false')
    ge = wrap(ge, ['anything', 'anything'])

    @internationalizeDocstring
    def lt(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a string comparison on <item1> and <item2>.
        Returns true if <item1> is less than <item2>.
        """
        if item1 < item2:
            irc.reply('true')
        else:
            irc.reply('false')
    lt = wrap(lt, ['anything', 'anything'])

    @internationalizeDocstring
    def le(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a string comparison on <item1> and <item2>.
        Returns true if <item1> is less than or equal to <item2>.
        """
        if item1 <= item2:
            irc.reply('true')
        else:
            irc.reply('false')
    le = wrap(le, ['anything', 'anything'])

    @internationalizeDocstring
    def match(self, irc, msg, args, optlist, item1, item2):
        """[--case-insensitive] <item1> <item2>

        Determines if <item1> is a substring of <item2>.
        Returns true if <item1> is contained in <item2>.

        Will only match case if --case-insensitive is not given.
        """
        optlist = dict(optlist)
        if 'case-insensitive' in optlist:
            item1 = item1.lower()
            item2 = item2.lower()
        if item2.find(item1) != -1:
            irc.reply('true')
        else:
            irc.reply('false')
    match = wrap(match, [getopts({'case-insensitive': ''}),
                         'something', 'something'])

    @internationalizeDocstring
    def nceq(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a numeric comparison on <item1> and <item2>.
        Returns true if they are equal.
        """
        if item1 == item2:
            irc.reply('true')
        else:
            irc.reply('false')
    nceq = wrap(nceq, ['float', 'float'])

    @internationalizeDocstring
    def nne(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a numeric comparison on <item1> and <item2>.
        Returns true if they are not equal.
        """
        if item1 != item2:
            irc.reply('true')
        else:
            irc.reply('false')
    nne = wrap(nne, ['float', 'float'])

    @internationalizeDocstring
    def ngt(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a numeric comparison on <item1> and <item2>.
        Returns true if <item1> is greater than <item2>.
        """
        if item1 > item2:
            irc.reply('true')
        else:
            irc.reply('false')
    ngt = wrap(ngt, ['float', 'float'])

    @internationalizeDocstring
    def nge(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a numeric comparison on <item1> and <item2>.
        Returns true if <item1> is greater than or equal to <item2>.
        """
        if item1 >= item2:
            irc.reply('true')
        else:
            irc.reply('false')
    nge = wrap(nge, ['float', 'float'])

    @internationalizeDocstring
    def nlt(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a numeric comparison on <item1> and <item2>.
        Returns true if <item1> is less than <item2>.
        """
        if item1 < item2:
            irc.reply('true')
        else:
            irc.reply('false')
    nlt = wrap(nlt, ['float', 'float'])

    @internationalizeDocstring
    def nle(self, irc, msg, args, item1, item2):
        """<item1> <item2>

        Does a numeric comparison on <item1> and <item2>.
        Returns true if <item1> is less than or equal to <item2>.
        """
        if item1 <= item2:
            irc.reply('true')
        else:
            irc.reply('false')
    nle = wrap(nle, ['float', 'float'])
Condition = internationalizeDocstring(Conditional)

Class = Conditional


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
