###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import gc
import os
import sys
import time
import atexit
import threading
import multiprocessing # python 2.6 and later!

if sys.version_info >= (2, 5, 0):
    import re as sre
else:
    import sre

import supybot.log as log
import supybot.conf as conf
import supybot.drivers as drivers
import supybot.ircutils as ircutils
import supybot.registry as registry

startedAt = time.time() # Just in case it doesn't get set later.

starting = False

mainThread = threading.currentThread()

def isMainThread():
    return mainThread is threading.currentThread()

threadsSpawned = 1 # Starts at one for the initial "thread."

class SupyThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        global threadsSpawned
        threadsSpawned += 1
        super(SupyThread, self).__init__(*args, **kwargs)
        log.debug('Spawning thread %q.', self.getName())

processesSpawned = 1 # Starts at one for the initial process.
class SupyProcess(multiprocessing.Process):
    def __init__(self, *args, **kwargs):
        global processesSpawned
        processesSpawned += 1
        super(SupyProcess, self).__init__(*args, **kwargs)
        log.debug('Spawning process %q.', self.name)


commandsProcessed = 0

ircs = [] # A list of all the IRCs.

def getIrc(network):
    network = network.lower()
    for irc in ircs:
        if irc.network.lower() == network:
            return irc
    return None

def _flushUserData():
    userdataFilename = os.path.join(conf.supybot.directories.conf(),
                                    'userdata.conf')
    registry.close(conf.users, userdataFilename)

flushers = [_flushUserData] # A periodic function will flush all these.

registryFilename = None

def flush():
    """Flushes all the registered flushers."""
    for (i, f) in enumerate(flushers):
        try:
            f()
        except Exception, e:
            log.exception('Uncaught exception in flusher #%s (%s):', i, f)

def debugFlush(s=''):
    if conf.supybot.debug.flushVeryOften():
        if s:
            log.debug(s)
        flush()

def upkeep():
    """Does upkeep (like flushing, garbage collection, etc.)"""
    # Just in case, let's clear the exception info.
    try:
        sys.exc_clear()
    except AttributeError:
        # Python 3 does not have sys.exc_clear. The except statement clears
        # the info itself (and we've just entered an except statement)
        pass
    if os.name == 'nt':
        try:
            import msvcrt
            msvcrt.heapmin()
        except ImportError:
            pass
        except IOError: # Win98 sux0rs!
            pass
    if conf.daemonized:
        # If we're daemonized, sys.stdout has been replaced with a StringIO
        # object, so let's see if anything's been printed, and if so, let's
        # log.warning it (things shouldn't be printed, and we're more likely
        # to get bug reports if we make it a warning).
        assert not type(sys.stdout) == file, 'Not a StringIO object!'
        if not hasattr(sys.stdout, 'getvalue'):
            # Stupid twisted sometimes replaces our stdout with theirs, because
            # "The Twisted Way Is The Right Way" (ha!).  So we're stuck simply
            # returning.
            log.warning('Expected cStringIO as stdout, got %r.', sys.stdout)
            return
        s = sys.stdout.getvalue()
        if s:
            log.warning('Printed to stdout after daemonization: %s', s)
            sys.stdout.reset() # Seeks to 0.
            sys.stdout.truncate() # Truncates to current offset.
        assert not type(sys.stderr) == file, 'Not a StringIO object!'
        s = sys.stderr.getvalue()
        if s:
            log.error('Printed to stderr after daemonization: %s', s)
            sys.stderr.reset() # Seeks to 0.
            sys.stderr.truncate() # Truncates to current offset.
    doFlush = conf.supybot.flush() and not starting
    if doFlush:
        flush()
        # This is so registry._cache gets filled.
        # This seems dumb, so we'll try not doing it anymore.
        #if registryFilename is not None:
        #    registry.open(registryFilename)
    if not dying:
        if sys.version_info[0] < 3:
            log.debug('Regexp cache size: %s', len(sre._cache))
        log.debug('Pattern cache size: %s', len(ircutils._patternCache))
        log.debug('HostmaskPatternEqual cache size: %s',
                  len(ircutils._hostmaskPatternEqualCache))
        #timestamp = log.timestamp()
        if doFlush:
            log.info('Flushers flushed and garbage collected.')
        else:
            log.info('Garbage collected.')
    collected = gc.collect()
    if gc.garbage:
        log.warning('Noncollectable garbage (file this as a bug on SF.net): %s',
                    gc.garbage)
    return collected

def makeDriversDie():
    """Kills drivers."""
    log.info('Killing Driver objects.')
    for driver in drivers._drivers.itervalues():
        driver.die()

def makeIrcsDie():
    """Kills Ircs."""
    log.info('Killing Irc objects.')
    for irc in ircs[:]:
        if not irc.zombie:
            irc.die()
        else:
            log.debug('Not killing %s, it\'s already a zombie.', irc)

def startDying():
    """Starts dying."""
    log.info('Shutdown initiated.')
    global dying
    dying = True

def finished():
    log.info('Shutdown complete.')

# These are in order; don't reorder them for cosmetic purposes.  The order
# in which they're registered is the reverse order in which they will run.
atexit.register(finished)
atexit.register(upkeep)
atexit.register(makeIrcsDie)
atexit.register(makeDriversDie)
atexit.register(startDying)

##################################################
##################################################
##################################################
## Don't even *think* about messing with these. ##
##################################################
##################################################
##################################################
dying = False
testing = False
starting = False
profiling = False
documenting = False


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
