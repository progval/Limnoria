#!/usr/bin/python

###
# Copyright (c) 2004, Jeremiah Fincher
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
Add the module docstring here.  This will be used by the setup.py script.
"""

__revision__ = "$Id$"
__author__ = ''

import supybot.plugins as plugins

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks
import supybot.plugins.LogToIrc as LogToIrc


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Tail', True)

conf.registerPlugin('Tail')
conf.registerGlobalValue(conf.supybot.plugins.Tail, 'targets',
    LogToIrc.Targets([], """Determines what targets will be messaged with lines
    from the files being tailed."""))
conf.registerGlobalValue(conf.supybot.plugins.Tail, 'bold',
    registry.Boolean(False, """Determines whether the bot will bold the filename
    in tail lines announced to the channel."""))
conf.registerGlobalValue(conf.supybot.plugins.Tail, 'files',
    registry.SpaceSeparatedSetOfStrings([], """Determines what files the bot
    will tail to its targets."""))

conf.registerGlobalValue(conf.supybot.plugins.Tail, 'notice',
    registry.Boolean(False, """Determines whether the bot will send its tail
    messages to the targets via NOTICEs rather than PRIVMSGs."""))

class Tail(privmsgs.CapabilityCheckingPrivmsg):
    capability = 'owner'
    def __init__(self):
        privmsgs.CapabilityCheckingPrivmsg.__init__(self)
        self.files = {}
        for filename in self.registryValue('files'):
            self._add(filename)

    def __call__(self, irc, msg):
        irc = callbacks.SimpleProxy(irc, msg)
        for (filename, fd) in self.files.iteritems():
            pos = fd.tell()
            line = fd.readline()
            while line:
                self.log.debug('pos: %s, line: %s', pos, line)
                line = line.strip()
                self._send(irc, filename, line)
                pos = fd.tell()
                line = fd.readline()
            fd.seek(pos)

    def die(self):
        for fd in self.files.values():
            fd.close()
            
    def _add(self, filename):
        fd = file(filename)
        fd.seek(0, 2) # 0 bytes, offset from the end of the file.
        self.files[filename] = fd
        self.registryValue('files').add(filename)
        
    def _send(self, irc, filename, text):
        targets = self.registryValue('targets')
        if self.registryValue('bold'):
            filename = ircutils.bold(filename)
        notice = self.registryValue('notice')
        payload = '%s: %s' % (filename, text)
        for target in targets:
            irc.reply(payload, to=target, notice=notice)
            
    def add(self, irc, msg, args):
        """<filename>

        Basically does the equivalent of tail -f to the targets.
        """
        filename = privmsgs.getArgs(args)
        try:
            self._add(filename)
        except EnvironmentError, e:
            irc.error(utils.exnTostring(e))
            return
        irc.replySuccess()

    def remove(self, irc, msg, args):
        """<filename>

        Stops announcing the lines appended to <filename>.
        """
        filename = privmsgs.getArgs(args)
        try:
            fd = self.files[filename]
            del self.files[filename]
            self.registryValue('files').remove(filename)
            fd.close()
            irc.replySuccess()
        except KeyError:
            irc.error('I\'m not currently announcing %s.' % filename)
        

Class = Tail

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
