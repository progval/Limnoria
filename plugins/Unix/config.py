###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import supybot.conf as conf
import supybot.utils as utils
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Unix')

import plugin

progstats = plugin.progstats

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Unix', True)
    output(_("""The "progstats" command can reveal potentially sensitive
              information about your machine. Here's an example of its output:

              %s\n""") % progstats())
    if yn(_('Would you like to disable this command for non-owner users?'),
          default=True):
        conf.supybot.commands.disabled().add('Unix.progstats')


Unix = conf.registerPlugin('Unix')
conf.registerGroup(Unix, 'fortune')
conf.registerGlobalValue(Unix.fortune, 'command',
    registry.String(utils.findBinaryInPath('fortune') or '', _("""Determines
    what command will be called for the fortune command.""")))
conf.registerChannelValue(Unix.fortune, 'short',
    registry.Boolean(True, _("""Determines whether only short fortunes will be
    used if possible.  This sends the -s option to the fortune program.""")))
conf.registerGlobalValue(Unix.fortune, 'equal',
    registry.Boolean(True, _("""Determines whether fortune will give equal
    weight to the different fortune databases.  If false, then larger
    databases will be given more weight.  This sends the -e option to the
    fortune program.""")))
conf.registerChannelValue(Unix.fortune, 'offensive',
    registry.Boolean(False, _("""Determines whether fortune will retrieve
    offensive fortunes along with the normal fortunes.  This sends the -a
    option to the fortune program.""")))
conf.registerGlobalValue(Unix.fortune, 'files',
    registry.SpaceSeparatedListOfStrings([], _("""Determines what specific file
    (if any) will be used with the fortune command; if none is given, the
    system-wide default will be used.  Do note that this fortune file must be
    placed with the rest of your system's fortune files.""")))

conf.registerGroup(Unix, 'spell')
conf.registerGlobalValue(Unix.spell, 'command',
    registry.String(utils.findBinaryInPath('aspell') or
                    utils.findBinaryInPath('ispell') or '', _("""Determines
    what command will be called for the spell command.""")))
conf.registerGlobalValue(Unix.spell, 'language',
    registry.String('en', _("""Determines what aspell dictionary will be used
    for spell checking.""")))

conf.registerGroup(Unix, 'wtf')
conf.registerGlobalValue(Unix.wtf, 'command',
    registry.String(utils.findBinaryInPath('wtf') or '', _("""Determines what
    command will be called for the wtf command.""")))

conf.registerGroup(Unix, 'ping')
conf.registerGlobalValue(Unix.ping, 'command', 
    registry.String(utils.findBinaryInPath('ping') or '', """Determines what 
    command will be called for the ping command."""))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
