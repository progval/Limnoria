#!/usr/bin/python
# -*- coding:utf-8 -*-

###
# Copyright (c) 2004, Stéphan Kochen
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
Allows for sending the bot's logging output to channels.
"""

__revision__ = "$Id$"

import plugins

import logging

import log
import conf
import utils
import world
import ircutils
import privmsgs
import registry
import callbacks


class IrcHandler(logging.Handler):
    def __init__(self, irc=None):
        logging.Handler.__init__(self)
        self._irc = irc

    def emit(self, record):
        try:
            if not self._irc.driver.connected:
                return
        except AttributeError:
            return
        from ircmsgs import privmsg
        for channel in conf.supybot.plugins.LogToChannel.channels():
            try:
                msg = self.format(record).split('\n')
                msg = [line.strip() for line in msg]
                msg = ' '.join(msg)
                self._irc.queueMsg(privmsg(channel, msg))
            except:
                self.handleError(record)


class IrcFormatter(log.Formatter):
    def formatException(self, ei):
        import cStringIO
        import traceback
        sio = cStringIO.StringIO()
        traceback.print_exception(ei[0], ei[1], None, None, sio)
        s = sio.getvalue()
        sio.close()
        return s


class ColorizedIrcFormatter(IrcFormatter):
    def formatException(self, (E, e, tb)):
        if conf.supybot.plugins.LogToChannel.colorized():
            return ircutils.bold(ircutils.mircColor(
                                IrcFormatter.formatException(self, (E, e, tb)),
                                fg='red'))
        else:
            return IrcFormatter.formatException(self, (E, e, tb))

    def format(self, record, *args, **kwargs):
        if conf.supybot.plugins.LogToChannel.colorized():
            fmt = '%s'
            if record.levelno == logging.CRITICAL:
                fmt = ircutils.bold(ircutils.mircColor('%s', fg='red'))
            elif record.levelno == logging.ERROR:
                fmt = ircutils.mircColor('%s', fg='red')
            elif record.levelno == logging.WARNING:
                fmt = ircutils.mircColor('%s', fg='orange')
            return fmt % IrcFormatter.format(self, record, *args, **kwargs)
        else:
            return IrcFormatter.format(self, record, *args, **kwargs)


_ircHandler = IrcHandler(irc=world.ircs[0])
_formatString = '%(name)s: %(levelname)s %(message)s'
_ircFormatter = ColorizedIrcFormatter(_formatString)
_ircHandler.setFormatter(_ircFormatter)


conf.registerPlugin('LogToChannel')
conf.registerGlobalValue(conf.supybot.plugins.LogToChannel, 'level',
    log.LogLevel(_ircHandler, logging.WARNING, """Determines what the minimum
    priority level logged will be to IRC. See supybot.log.level for possible
    values. (NEVER set this to DEBUG!)"""))
conf.supybot.plugins.LogToChannel.level._target = _ircHandler
_ircHandler.setLevel(conf.supybot.plugins.LogToChannel.level())
conf.registerGlobalValue(conf.supybot.plugins.LogToChannel, 'channels',
    conf.SpaceSeparatedSetOfChannels('', """Determines which channels the
    bot should log to or empty if none at all."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToChannel, 'colorized',
    registry.Boolean(False, """Determines whether the bot's logs
    to IRC will be colorized with mIRC colors."""))


def configure(advanced):
    from questions import something, anything, yn, output
    channels = ''
    while not channels:
        try:
            channels = anything('Which channels would you like to send log '
                                 'messages too?')
            conf.supybot.plugins.LogToChannel.channels.set(channels)
        except registry.InvalidRegistryValue, e:
            output(str(e))
            channels = ''
    colorized = yn('Would you like these messages to be colored?')
    conf.supybot.plugins.LogToChannel.colorized.setValue(colorized)
    if advanced:
        level = ''
        while not level
            try:
                level = something('What would you like the minimum priority '
                                  'level to be which will be logged to IRC?')
                conf.supybot.plugins.LogToChannel.level.set(level)
            except registry.InvalidRegistryValue, e:
                output(str(e))
                level = ''


class LogToChannel(callbacks.Privmsg):
    threaded = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        log._logger.addHandler(_ircHandler)

    def die(self):
        log._logger.removeHandler(_ircHandler)


Class = LogToChannel

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
