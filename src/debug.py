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

from fix import *

import sys

import os
import os.path
import sys
import time
import cgitb
import traceback

import ansi
try:
    import conf
except ImportError:
    class conf:
        logDir = '.'
        detailedTracebacks = True

import world

###
# CONFIGURATION
###

# Names of logfiles.

if not os.path.exists(conf.logDir):
    os.mkdir(conf.logDir)

errorfile = os.path.join(conf.logDir, 'error.log')
debugfile = os.path.join(conf.logDir, 'debug.log')
tracefile = os.path.join(conf.logDir, 'trace.log')

# stderr: True if messages should be written to stderr as well as logged.
stderr = True

# colorterm: True if the terminal run on is color.
if sys.platform == 'win32':
    colorterm = False
else:
    colorterm = True

# PRINTF: True if printf debugging messages should be printed.
PRINTF = False

# minimumPriority: Lowest priority logged;
#                  One of {'verbose', 'low', 'normal', 'high'}.
minimumPriority = 'verbose'

# deadlyExceptions: Exceptions that should cause immediate failure.
deadlyExceptions = [KeyboardInterrupt, SystemExit]

###
# END CONFIGURATION
###

_errorfd = file(errorfile, 'a')
_debugfd = file(debugfile, 'a')
_tracefd = file(tracefile, 'w')

priorities = { 'verbose': 0,
               'low': 1,
               'normal': 2,
               'high': 3 }

priorityColors = { 'verbose': ansi.BLUE,
                   'low': ansi.CYAN,
                   'normal': ansi.GREEN,
                   'high': ansi.BOLD }
priorityColors.setdefault('')

# This is a queue of the time of the last 10 calls to recoverableException.
# If the most recent time is
lastTimes = [time.time()-1] * 10

def reset():
    """Resets the various file descriptors kept open by this module."""
    global _errorfd, _debugfd, _tracefd
    _errorfd.flush()
    _errorfd.close()
    _errorfd = file(_errorfd.name, 'a')
    _debugfd.flush()
    _debugfd.close()
    _debugfd = file(_errorfd.name, 'a')
    _tracefd.flush()
    _tracefd.close()
    _tracefd = file(_errorfd.name, 'w')

def exit(i=-1):
    """Makes sure to actually exit."""
    class E(Exception):
        pass
    if deadlyExceptions:
        # Just to be safe, we'll make it a subclass of *all* the deadly
        # exceptions :)
        for exn in deadlyExceptions:
            class E(exn, E):
                pass
        raise E
    else:
        os._exit(i)

def _writeNewline(fd, s):
    fd.write(s)
    if s[-len(os.linesep):] != os.linesep:
        fd.write(os.linesep)

def recoverableError(msg):
    """Called with errors that are not critical."""
    if stderr:
        if colorterm:
            sys.stderr.write(ansi.BOLD + ansi.RED)
        _writeNewline(sys.stderr, msg)
        if colorterm:
            sys.stderr.write(ansi.RESET)
    _writeNewline(_errorfd, msg)
    _errorfd.flush()

def unrecoverableError(msg):
    """Logs some error message and then exits."""
    recoverableError(msg)
    exit(-1)

def recoverableException(type='detailed'):
    """Logs an exception that's recoverable.

    The 'type' argument can be either 'detailed' (for a nice cgitb traceback),
    'normal' (for a normal traceback), or 'terse' (for a short line stating
    the exception raised).
    """
    if world.testing:
        return
    (E, e, tb) = sys.exc_info()
    for exn in deadlyExceptions:
        if issubclass(e.__class__, exn):
            raise
    lastTimes.append(time.time())
    if lastTimes[-1] - lastTimes[0] < 0.50:
        msg('Too many exceptions too quickly.  Bailing out.', 'high')
        exit()
    else:
        del lastTimes[0]
    try:
        if type == 'detailed':
            if conf.detailedTracebacks:
                text = cgitb.text((E, e, tb))
            else:
                text = ''.join(traceback.format_exception(E, e, tb))
        elif type == 'normal':
            text = ''.join(traceback.format_exception(E, e, tb))
        elif type == 'terse':
            text = exnToString(e)
    except:
        text = ''.join(traceback.format_exception(E, e, tb))
    del tb # just to be safe.
    if stderr:
        if colorterm:
            sys.stderr.write(ansi.BOLD + ansi.RED)
        sys.stderr.write(text)
        if colorterm:
            sys.stderr.write(ansi.RESET)
    _errorfd.write(text)
    _errorfd.flush()

def unrecoverableException():
    """Logs the most recent exception and then exits."""
    recoverableException()
    exit(-1)

def msg(s, priority='low'):
    """Logs a message s with the appropriate priority."""
    if priorities[priority] >= priorities[minimumPriority]:
        if stderr:
            if colorterm:
                sys.stderr.write(priorityColors.get(priority))
            _writeNewline(sys.stderr, s)
            if colorterm:
                sys.stderr.write(ansi.RESET)
        s = '%s: %s' % (priority.upper(), s)
        _writeNewline(_debugfd, s)
        _debugfd.flush()

def printf(msg):
    """Used for simple printf debugging.  Can be turned off via PRINTF."""
    if PRINTF:
        print '*** ' + str(msg)

def methodNamePrintf(obj, methodName):
    """Does a debug.printf with the appropriate method name."""
    printf('%s: %s' % (obj.__class__.__name__, methodName))

def exnToString(e):
    """Turns a simple exception instance into a string (better than str(e))"""
    return '%s: %s' % (e.__class__.__name__, e)

def tracer(frame, event, _):
    if event == 'call':
        s = '%s: %s\n' % (frame.f_code.co_filename, frame.f_code.co_name)
        _tracefd.write(s)
        _tracefd.flush()

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
