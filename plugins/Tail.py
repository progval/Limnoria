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
Messages a list of targets when new lines are added to any of a list of files,
much like "tail -f" does on UNIX.
"""

__revision__ = "$Id$"
__author__ = ''

import supybot.plugins as plugins

import os
import getopt

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.schedule as schedule
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
conf.registerGlobalValue(conf.supybot.plugins.Tail, 'period',
    registry.PositiveInteger(60, """Determines how often the bot will check
    the files that are being tailed.  The number is in seconds.  This plugin
    must be reloaded for changes to this period to take effect."""))

class Tail(privmsgs.CapabilityCheckingPrivmsg):
    capability = 'owner'
    def __init__(self):
        privmsgs.CapabilityCheckingPrivmsg.__init__(self)
        self.files = {}
        period = self.registryValue('period')
        schedule.addPeriodicEvent(self._checkFiles, period, name=self.name())
        for filename in self.registryValue('files'):
            self._add(filename)

    def die(self):
        schedule.removeEvent(self.name())
        for fd in self.files.values():
            fd.close()

    def __call__(self, irc, msg):
        irc = callbacks.SimpleProxy(irc, msg)
        self.lastIrc = irc
        self.lastMsg = msg

    def _checkFiles(self):
        self.log.info('Checking files.')
        for filename in self.registryValue('files'):
            self._checkFile(filename)

    def _checkFile(self, filename):
        fd = self.files[filename]
        pos = fd.tell()
        line = fd.readline()
        while line:
            line = line.strip()
            if line:
                self._send(self.lastIrc, filename, line)
            pos = fd.tell()
            line = fd.readline()
        fd.seek(pos)

    def _add(self, filename):
        try:
            fd = file(filename)
        except EnvironmentError, e:
            self.log.warning('Couldn\'t open %s: %s', filename, e)
            raise
        fd.seek(0, 2) # 0 bytes, offset from the end of the file.
        self.files[filename] = fd
        self.registryValue('files').add(filename)

    def _remove(self, filename):
        fd = self.files.pop(filename)
        fd.close()
        self.registryValue('files').remove(filename)
        
    def _send(self, irc, filename, text):
        if self.registryValue('bold'):
            filename = ircutils.bold(filename)
        notice = self.registryValue('notice')
        payload = '%s: %s' % (filename, text)
        for target in self.registryValue('targets'):
            irc.reply(payload, to=target, notice=notice, private=True)
            
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
            self._remove(filename)
            irc.replySuccess()
        except KeyError:
            irc.error('I\'m not currently announcing %s.' % filename)

    def target(self, irc, msg, args):
        """[--remove] [<target> ...]

        If given no arguments, returns the current list of targets for this
        plugin.  If given any number of targets, will add these targets to
        the current list of targets.  If given --remove and any number of
        targets, will remove those targets from the current list of targets.
        """
        (optlist, args) = getopt.getopt(args, '', ['remove'])
        remove = False
        for (option, arg) in optlist:
            if option == '--remove':
                remove = True
        if not args:
            L = self.registryValue('targets')
            if L:
                utils.sortBy(ircutils.toLower, L)
                irc.reply(utils.commaAndify(L))
            else:
                irc.reply('I\'m not currently targetting anywhere.')
        elif remove:
            pass #XXX
        

Class = Tail

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
