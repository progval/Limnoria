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
import atexit
import logging

import ansi
import conf

deadlyExceptions = [KeyboardInterrupt, SystemExit]

if not os.path.exists(conf.logDir):
    os.mkdir(conf.logDir, 0755)

pluginLogDir = os.path.join(conf.logDir, 'plugins')

if not os.path.exists(pluginLogDir):
    os.mkdir(pluginLogDir, 0755)

class Formatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        if datefmt is None:
            datefmt = conf.logTimestampFormat
        return logging.Formatter.formatTime(self, record, datefmt)

    def formatException(self, (E, e, tb)):
        for exn in deadlyExceptions:
            if issubclass(e.__class__, exn):
                raise
        ### TODO: formatException should use cgitb.
        return logging.Formatter.formatException(self, (E, e, tb))


class DailyRotatingHandler(logging.FileHandler):
    def __init__(self, *args):
        self.lastRollover = time.localtime()
        logging.FileHandler.__init__(self, *args)
        
    def emit(self, record):
        now = time.localtime()
        if now[2] != self.lastRollover[2]:
            self.doRollover()
        self.lastRollover = now
        logging.FileHandler.emit(self, record)
        
    def doRollover(self):
        self.stream.close()
        extension = time.strftime('%d-%b-%Y', self.lastRollover)
        os.rename(self.baseFilename, '%s.%s' % (self.baseFilename, extension))
        self.stream = file(self.baseFilename, 'w')


class ColorizedFormatter(Formatter):
    def formatException(self, (E, e, tb)):
        if conf.colorizedStdoutLogging:
            return ''.join([ansi.BOLD, ansi.RED,
                            Formatter.formatException(self, (E, e, tb)),
                            ansi.RESET])
        else:
            return Formatter.formatException(self, (E, e, tb))

    def format(self, record, *args, **kwargs):
        if conf.colorizedStdoutLogging:
            color = ''
            if record.levelno == logging.CRITICAL:
                color = ansi.WHITE + ansi.BOLD
            elif record.levelno == logging.ERROR:
                color = ansi.RED
            elif record.levelno == logging.WARNING:
                color = ansi.YELLOW
            elif record.levelno == logging.VERBOSE:
                color = ansi.BLUE
            elif record.levelno == logging.PRINTF:
                color = ansi.CYAN
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
_handler = logging.FileHandler(os.path.join(conf.logDir, 'misc.log'))
_handler.setFormatter(formatter)
_handler.setLevel(conf.minimumLogPriority)
_logger.addHandler(_handler)
_logger.setLevel(-1)

if conf.stdoutLogging:
    _stdoutHandler = logging.StreamHandler(sys.stdout)
    _formatString = '%(name)s: %(levelname)s %(asctime)s %(message)s'
    _stdoutFormatter = ColorizedFormatter(_formatString)
    _stdoutHandler.setFormatter(_stdoutFormatter)
    _stdoutHandler.setLevel(conf.minimumLogPriority)
    _logger.addHandler(_stdoutHandler)

debug = _logger.debug
info = _logger.info
warning = _logger.warning
error = _logger.error
critical = _logger.critical
exception = _logger.exception

printf = curry(_logger.log, 1)
logging.PRINTF = 1
logging._levelNames['PRINTF'] = logging.PRINTF
logging._levelNames[logging.PRINTF] = 'PRINTF'

verbose = curry(_logger.log, 5)
logging.VERBOSE = 5
logging._levelNames['VERBOSE'] = logging.VERBOSE
logging._levelNames[logging.VERBOSE] = 'VERBOSE'

atexit.register(logging.shutdown)

def getPluginLogger(name):
    log = logging.getLogger('supybot.plugins.%s' % name)
    if not log.handlers:
        filename = os.path.join(pluginLogDir, '%s.log' % name)
        handler = logging.FileHandler(filename)
        handler.setLevel(conf.minimumLogPriority)
        handler.setFormatter(pluginFormatter)
        log.addHandler(handler)
    return log


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

