###
# Copyright (c) 2003-2005, James Vega
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
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Debian', True)
    if not utils.findBinaryInPath('zgrep'):
        if not advanced:
            output("""I can't find zgrep in your path.  This is necessary
                      to run the file command.  I'll disable this command
                      now.  When you get zgrep in your path, use the command
                      'enable Debian.file' to re-enable the command.""")
            capabilities = conf.supybot.capabilities()
            capabilities.add('-Debian.file')
            conf.supybot.capabilities.set(capabilities)
        else:
            output("""I can't find zgrep in your path.  If you want to run
                      the file command with any sort of expediency, you'll
                      need it.  You can use a python equivalent, but it's
                      about two orders of magnitude slower.  THIS MEANS IT
                      WILL TAKE AGES TO RUN THIS COMMAND.  Don't do this.""")
            if yn('Do you want to use a Python equivalent of zgrep?'):
                conf.supybot.plugins.Debian.pythonZgrep.setValue(True)
            else:
                output('I\'ll disable file now.')
                capabilities = conf.supybot.capabilities()
                capabilities.add('-Debian.file')
                conf.supybot.capabilities.set(capabilities)


Debian = conf.registerPlugin('Debian')
conf.registerGlobalValue(Debian, 'pythonZgrep',
    registry.Boolean(False, """An advanced option, mostly just for testing;
    uses a Python-coded zgrep rather than the actual zgrep executable,
    generally resulting in a 50x slowdown.  What would take 2 seconds will
    take 100 with this enabled.  Don't enable this."""))
conf.registerChannelValue(Debian, 'bold',
    registry.Boolean(True, """Determines whether the plugin will use bold in
    the responses to some of its commands."""))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
