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

__revision__ = "$Id$"

import fix

import os
import sys
import time
import cgitb
import types
import atexit
import logging

import ansi
import conf
import registry

class LogLevel(registry.Value):
    def set(self, s):
        s = s.upper()
        try:
            self.value = getattr(logging, s)
        except AttributeError:
            s = 'Invalid log level: should be one of ' \
                'DEBUG, INFO, WARNING, ERROR, or CRITICAL.'
            raise registry.InvalidRegistryValue, s
    def __str__(self):
        return logging.getLevelName(self.value)
    
conf.supybot.directories.register('log', registry.String('logs', """Determines
what directory the bot will store its logfiles in."""))

conf.supybot.registerGroup('log')
conf.supybot.log.register('minimumPriority', LogLevel(logging.INFO,
"""Determines what the minimum priority logged will be.  Valid values are
DEBUG, INFO, WARNING, ERROR, and CRITICAL, in order of increasing
priority."""))
conf.supybot.log.register('timestampFormat',
registry.String('[%d-%b-%Y %H:%M:%S]',
"""Determines the format string for timestamps in logfiles.  Refer to the
Python documentation for the time module to see what formats are accepted."""))
conf.supybot.log.register('detailedTracebacks', registry.Boolean(True, """
Determines whether highly detailed tracebacks will be logged.  While more
informative (and thus more useful for debugging) they also take a significantly
greater amount of space in the logs.  Hopefully, however, such uncaught
exceptions aren't very common."""))
conf.supybot.log.registerGroup('stdout',
registry.GroupWithValue(registry.Boolean(True, """Determines whether the bot
will log to stdout.""")))

class BooleanRequiredFalseOnWindows(registry.Boolean):
    def set(self, s):
        registry.Boolean.set(self, s)
        if self.value and os.name == 'nt':
            raise InvalidRegistryValue, 'Value cannot be true on Windows.'
        
conf.supybot.log.stdout.register('colorized',
BooleanRequiredFalseOnWindows(False, """Determines whether the bot's logs to
stdout (if enabled) will be colorized with ANSI color."""))
                          
deadlyExceptions = [KeyboardInterrupt, SystemExit]

if not os.path.exists(conf.supybot.directories.log()):
    os.mkdir(conf.supybot.directories.log(), 0755)

pluginLogDir = os.path.join(conf.supybot.directories.log(), 'plugins')

if not os.path.exists(pluginLogDir):
    os.mkdir(pluginLogDir, 0755)

class Formatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        if datefmt is None:
            datefmt = conf.supybot.log.timestampFormat()
        return logging.Formatter.formatTime(self, record, datefmt)

    def formatException(self, (E, e, tb)):
        for exn in deadlyExceptions:
            if issubclass(e.__class__, exn):
                raise
        if conf.supybot.log.detailedTracebacks():
            try:
                return cgitb.text((E, e, tb)).rstrip('\r\n')
            except:
                error('Cgitb.text raised an exception.')
                return logging.Formatter.formatException(self, (E, e, tb))
        else:
            return logging.Formatter.formatException(self, (E, e, tb))


class BetterStreamHandler(logging.StreamHandler):
    def emit(self, record):
        msg = self.format(record)
        if not hasattr(types, "UnicodeType"): #if no unicode support...
            self.stream.write("%s\n" % msg)
        else:
            try:
                self.stream.write("%s\n" % msg)
            except UnicodeError:
                self.stream.write("%s\n" % msg.encode("UTF-8"))
        self.flush()
        

class BetterFileHandler(logging.FileHandler):
    def emit(self, record):
        msg = self.format(record)
        if not hasattr(types, "UnicodeType"): #if no unicode support...
            self.stream.write("%s\n" % msg)
        else:
            try:
                self.stream.write("%s\n" % msg)
            except UnicodeError:
                self.stream.write("%s\n" % msg.encode("UTF-8"))
        self.flush()
        

class DailyRotatingHandler(BetterFileHandler):
    def __init__(self, *args):
        self.lastRollover = time.localtime()
        BetterFileHandler.__init__(self, *args)
        
    def emit(self, record):
        now = time.localtime()
        if now[2] != self.lastRollover[2]:
            self.doRollover()
        self.lastRollover = now
        BetterFileHandler.emit(self, record)
        
    def doRollover(self):
        self.stream.close()
        extension = time.strftime('%d-%b-%Y', self.lastRollover)
        os.rename(self.baseFilename, '%s.%s' % (self.baseFilename, extension))
        self.stream = file(self.baseFilename, 'w')


class ColorizedFormatter(Formatter):
    def formatException(self, (E, e, tb)):
        if conf.supybot.log.stdout.colorized():
            return ''.join([ansi.BOLD, ansi.RED,
                            Formatter.formatException(self, (E, e, tb)),
                            ansi.RESET])
        else:
            return Formatter.formatException(self, (E, e, tb))

    def format(self, record, *args, **kwargs):
        if conf.supybot.log.stdout.colorized():
            color = ''
            if record.levelno == logging.CRITICAL:
                color = ansi.WHITE + ansi.BOLD
            elif record.levelno == logging.ERROR:
                color = ansi.RED
            elif record.levelno == logging.WARNING:
                color = ansi.YELLOW
            return ''.join([color,
                            Formatter.format(self, record, *args, **kwargs),
                            ansi.RESET])
        else:
            return Formatter.format(self, record, *args, **kwargs)

# These are public.
formatter = Formatter('%(levelname)s %(asctime)s %(message)s')
pluginFormatter = Formatter('%(levelname)s %(asctime)s %(name)s %(message)s')

# These are not.
_logger = logging.getLogger('supybot')
_handler = BetterFileHandler(os.path.join(conf.supybot.directories.log(),
                                          'misc.log'))
_handler.setFormatter(formatter)
_handler.setLevel(-1)
_logger.addHandler(_handler)
_logger.setLevel(conf.supybot.log.minimumPriority())

if conf.supybot.log.stdout():
    _stdoutHandler = BetterStreamHandler(sys.stdout)
    _formatString = '%(name)s: %(levelname)s %(message)s'
    _stdoutFormatter = ColorizedFormatter(_formatString)
    _stdoutHandler.setFormatter(_stdoutFormatter)
    _stdoutHandler.setLevel(-1)
    _logger.addHandler(_stdoutHandler)

debug = _logger.debug
info = _logger.info
warning = _logger.warning
error = _logger.error
critical = _logger.critical
exception = _logger.exception

setLevel = _logger.setLevel

atexit.register(logging.shutdown)

def getPluginLogger(name):
    log = logging.getLogger('supybot.plugins.%s' % name)
    if not log.handlers:
        filename = os.path.join(pluginLogDir, '%s.log' % name)
        handler = BetterFileHandler(filename)
        handler.setLevel(conf.supybot.log.minimumPriority())
        handler.setFormatter(pluginFormatter)
        log.addHandler(handler)
    return log

def timestamp(when=None):
    if when is None:
        when = time.time()
    format = conf.supybot.log.timestampFormat()
    return time.strftime(format, time.localtime(when))


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

