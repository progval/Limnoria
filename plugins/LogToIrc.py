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
import ircdb
import ircmsgs
import ircutils
import privmsgs
import registry
import callbacks


class IrcHandler(logging.Handler):
    def emit(self, record):
        config = conf.supybot.plugins.LogToIrc
        try:
            s = utils.normalizeWhitespace(self.format(record))
        except:
            self.handleError(record)
        for target in config.targets():
            msgmaker = ircmsgs.privmsg
            if config.notice() and not ircutils.isChannel(target):
                msgmaker = ircmsgs.notice
            msg = msgmaker(target, s)
            for irc in world.ircs:
                try:
                    if not irc.driver.connected:
                        continue
                except AttributeError, e:
                    print '*** AttributeError, shouldn\'t happen: %s' % e
                    continue
                msgOk = True
                if target in irc.state.channels:
                    channel = irc.state.channels[target]
                    for modeChar in config.channelModesRequired():
                        if modeChar not in channel.modes:
                            msgOk = False
                else:
                    capability = config.userCapabilityRequired()
                    if capability:
                        try:
                            hostmask = irc.state.nicksToHostmasks[target]
                        except KeyError:
                            msgOk = False
                            continue
                        if not ircdb.checkCapability(hostmask, capability):
                            msgOk = False
                if msgOk:
                    irc.queueMsg(msg)
                else:
                    print '*** Not sending to %r' % target
                        
                        
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
    def set(self, s):
        s = s.upper()
        try:
            self.setValue(getattr(logging, s))
            _ircHandler.setLevel(self.value)
        except AttributeError:
            self.error()
    
    def setValue(self, v):
        if v <= logging.DEBUG:
            self.error()
        else:
            log.LogLevel.setValue(self, v)

class ValidChannelOrNick(registry.String):
    """Value must be a valid channel or a valid nick."""
    def setValue(self, v):
        if not (ircutils.isNick(v) or ircutils.isChannel(v)):
            self.error()
        registry.String.setValue(self, v)

class Targets(registry.SpaceSeparatedListOfStrings):
    Value = ValidChannelOrNick

conf.registerPlugin('LogToIrc')
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc, 'level',
    IrcLogLevel(logging.WARNING, """Determines what the minimum priority
    level logged will be to IRC. See supybot.log.level for possible
    values.  DEBUG is disabled due to the large quantity of output."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc, 'targets',
    Targets([], """Determines which channels/nicks the bot should
    log to.  If no channels/nicks are set, this plugin will effectively be
    turned off."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc, 'channelModesRequired',
    registry.String('s', """Determines what channel modes a channel will be
    required to have for the bot to log to the channel.  If this string is
    empty, no modes will be checked."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc,
    'userCapabilityRequired', registry.String('owner', """Determines what
    capability is required for the bot to log to in private messages to the
    user.  If this is empty, there will be no capability that's checked."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc, 'colorized',
    registry.Boolean(False, """Determines whether the bot's logs
    to IRC will be colorized with mIRC colors."""))
conf.registerGlobalValue(conf.supybot.plugins.LogToIrc, 'notice',
    registry.Boolean(False, """Determines whether the bot's logs to IRC will be
    sent via NOTICE instead of PRIVMSG.  Channels will always be PRIVMSGed,
    regardless of this variable; NOTICEs will only be used if this variable is
    True and the target is a nick, not a channel."""))

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
        targets = self.registryValue('targets')
        for target in targets:
            if ircutils.isChannel(target):
                irc.queueMsg(ircmsgs.join(target))
    do377 = do422 = do376
            

Class = LogToIrc

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
