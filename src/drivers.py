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
Contains various drivers (network, file, and otherwise) for using IRC objects.
"""

__revision__ = "$Id$"

import supybot.fix as fix

import re
import os
import sys

import supybot.log as log
import supybot.conf as conf
import supybot.ansi as ansi
import supybot.ircmsgs as ircmsgs

_drivers = {}
_deadDrivers = []
_newDrivers = []

class IrcDriver(object):
    """Base class for drivers."""
    def __init__(self):
        add(self.name(), self)
        if not hasattr(self, 'irc'):
            self.irc = None # This is to satisfy PyChecker.

    def run(self):
        raise NotImplementedError

    def die(self):
        # The end of any overrided die method should be
        # "super(Class, self).die()", in order to make
        # sure this (and anything else later added) is done.
        remove(self.name())

    def reconnect(self, wait=False):
        raise NotImplementedError

    def name(self):
        return repr(self)

def empty():
    """Returns whether or not the driver loop is empty."""
    return (len(_drivers) + len(_newDrivers)) == 0

def add(name, driver):
    """Adds a given driver the loop with the given name."""
    _newDrivers.append((name, driver))

def remove(name):
    """Removes the driver with the given name from the loop."""
    _deadDrivers.append(name)

def run():
    """Runs the whole driver loop."""
    for (name, driver) in _drivers.iteritems():
        try:
            if name not in _deadDrivers:
                driver.run()
        except:
            log.exception('Uncaught exception in in drivers.run:')
            _deadDrivers.append(name)
    for name in _deadDrivers:
        try:
            driver = _drivers[name]
            if hasattr(driver, 'irc') and driver.irc is not None:
                # The Schedule driver has no irc object, or it's None.
                driver.irc.driver = None
            driver.irc = None
            log.info('Removing driver %s.', name)
            del _drivers[name]
        except KeyError:
            pass
    while _newDrivers:
        (name, driver) = _newDrivers.pop()
        log.debug('Adding new driver %s.', name)
        if name in _drivers:
            log.warning('Driver %s already added, killing it.', name)
            _drivers[name].die()
            del _drivers[name]
        _drivers[name] = driver

def newDriver(server, irc, moduleName=None):
    """Returns a new driver for the given server using the irc given and using
    conf.supybot.driverModule to determine what driver to pick."""
    if moduleName is None:
        moduleName = conf.supybot.drivers.module()
    if moduleName == 'default':
        try:
            import twistedDrivers
            moduleName = 'supybot.twistedDrivers'
        except ImportError:
            del sys.modules['supybot.twistedDrivers']
            moduleName = 'supybot.socketDrivers'
    elif not moduleName.startswith('supybot.'):
        moduleName = 'supybot.' + moduleName
    driverModule = __import__(moduleName, {}, {}, ['not empty'])
    log.debug('Creating new driver for %s:%s (%s)',
              server[0], server[1], moduleName)
    driver = driverModule.Driver(server, irc)
    irc.driver = driver
    return driver

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
