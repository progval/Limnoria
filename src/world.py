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

"""
Module for general worldly stuff, like global variables and whatnot.
"""

__revision__ = "$Id$"

import fix

import gc
import os
import sys
import sre
import time
import types
import atexit
import socket
import threading

import log
import conf
import ircutils

socket.setdefaulttimeout(10)

startedAt = time.time() # Just in case it doesn't get set later.

mainThread = threading.currentThread()
assert 'MainThread' in repr(mainThread)

threadsSpawned = 1 # Starts at one for the initial "thread."
commandsProcessed = 0

ircs = [] # A list of all the IRCs.

flushers = [] # A periodic function will flush all these.

def flush():
    """Flushes all the registered flushers."""
    for f in flushers:
        f()

def upkeep():
    """Does upkeep (like flushing, garbage collection, etc.)"""
    sys.exc_clear() # Just in case, let's clear the exception info.
    collected = gc.collect()
    if os.name == 'nt':
        try:
            import msvcrt
            msvcrt.heapmin()
        except ImportError:
            pass
        except IOError: # Win98 sux0rs!
            pass
    if gc.garbage:
        log.warning('Uncollectable garbage: %s', gc.garbage)
    if True: # XXX: Replace this with the registry variable.
        flush()
    if not dying:
        log.debug('Regexp cache size: %s', len(sre._cache))
        log.debug('Pattern cache size: %s'%len(ircutils._patternCache))
        log.debug('HostmaskPatternEqual cache size: %s' %
                  len(ircutils._hostmaskPatternEqualCache))
        log.info('%s upkeep ran.', time.strftime(conf.logTimestampFormat))
    return collected

def makeIrcsDie():
    """Kills Ircs."""
    log.info('Killing Irc objects.')
    for irc in ircs[:]:
        irc.die()

def startDying():
    """Starts dying."""
    log.info('Shutdown initiated.')
    global dying
    dying = True

def finished():
    log.info('Shutdown complete.')

atexit.register(finished)
atexit.register(upkeep)
atexit.register(makeIrcsDie)
atexit.register(startDying)

##################################################
##################################################
##################################################
## Don't even *think* about messing with these. ##
##################################################
##################################################
##################################################
startup = False
testing = False
dying = False


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
