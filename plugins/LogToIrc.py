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
Allows for sending the bot's logging output to a channel or nick.
"""

__revision__ = "$Id$"

import plugins

import logging

import log
import conf
import utils
import world
import ircmsgs
import ircutils
import privmsgs
import registry
import callbacks


class IrcHandler(logging.Handler):
    def emit(self, record):
        target = conf.supybot.plugins.LogToIrc.target()
        try:
            s = utils.normalizeWhitespace(self.format(record))
        except:
            self.handleError(record)
        msg = ircmsgs.privmsg(target, s)
        if target:
            for irc in world.ircs:
                try:
                    if not irc.driver.connected:
                        continue
                except AttributeError, e:
                    print '*** AttributeError, shouldn\'t happen: %s' % e
                    continue
                if target in irc.state.channels or \
                   target in irc.state.nicksToHostmasks:
                    irc.queueMsg(msg)
            

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
        if conf.supybot.plugins.LogToIrc.colorized():
            return ircutils.bold(ircutils.mircColor(
                                IrcFormatter.formatException(self, (E, e, tb)),
                                fg='red'))
        else:
            return IrcFormatter.formatException(self, (E, e, tb))

    def format(self, record, *args, **kwargs):
        s = IrcFormatter.format(self, record, *args, **kwargs)
        if conf.supybot.plugins.LogToIrc.colorized():
            if record.levelno == logging.CRITICAL:
                s = ircutils.bold(ircutils.mircColor(s, fg='red'))
            elif record.levelno == logging.ERROR:
                s = ircutils.mircColor(s, fg='orange')
            elif record.levelno == logging.WARNING:
                s = ircutils.mircColor(s, fg='yellow')
        return s


_ircHandler = IrcHandler()
_formatString = '%(name)s: %(levelname)s %(message)s'
_ircFormatter = ColorizedIrcFormatter(_formatString)
_ircHandler.setFormatter(_ircFormatter)

class IrcLogLevel(log.LogLevel):
    """Value must be one of INFO, WARNING, ERROR, or CRITICAL."""
    def setValue(self, v):
        if v <= logging.DEBUG:
            self.error()
        else:
            log.LogLevel.setValue(self, v)
            _ircHandler.setLevel(v)

class ValidChannelOrNickOrNot(registry.String):
    """Value must be a valid channel, a valid nick, or an empty string."""
    def setValue(self, v):
        if v:
            if not (ircutils.isNick(v) or ircutils.isChannel(v)):
                self.error()
        registry.String.setValue(self, v)

conf.registerPlugin('LogToIrc')
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc, 'level',
    IrcLogLevel(logging.WARNING, """Determines what the minimum priority
    level logged will be to IRC. See supybot.log.level for possible
    values.  DEBUG is disabled due to the large quantity of output."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc, 'target',
    ValidChannelOrNickOrNot('', """Determines which channel/nick the bot should
    log to.  If no channel/nick is set, this plugin will be effectively
    off."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc, 'colorized',
    registry.Boolean(False, """Determines whether the bot's logs
    to IRC will be colorized with mIRC colors."""))

def configure(advanced):
    from questions import something, anything, yn, output
    target = ''
    while not target:
        try:
            target = anything('Which channel would you like to send log '
                              'messages too?')
            conf.supybot.plugins.LogToIrc.target.set(target)
        except registry.InvalidRegistryValue, e:
            output(str(e))
            target = ''
    colorized = yn('Would you like these messages to be colored?')
    conf.supybot.plugins.LogToIrc.colorized.setValue(colorized)
    if advanced:
        level = ''
        while not level:
            try:
                level = something('What would you like the minimum priority '
                                  'level to be which will be logged to IRC?')
                conf.supybot.plugins.LogToIrc.level.set(level)
            except registry.InvalidRegistryValue, e:
                output(str(e))
                level = ''


class LogToIrc(callbacks.Privmsg):
    threaded = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        log._logger.addHandler(_ircHandler)

    def die(self):
        log._logger.removeHandler(_ircHandler)

    def do376(self, irc, msg):
        target = self.registryValue('target')
        if target and ircutils.isChannel(target):
            irc.queueMsg(ircmsgs.join(target))
    do377 = do422 = do376
            

Class = LogToIrc

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
