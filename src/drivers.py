#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

import sys
import time
import socket

import supybot.log as supylog
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs

_drivers = {}
_deadDrivers = []
_newDrivers = []

class IrcDriver(object):
    """Base class for drivers."""
    def __init__(self):
        add(self.name(), self)

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

class ServersMixin(object):
    def __init__(self, irc, servers=()):
        self.networkGroup = conf.supybot.networks.get(irc.network)
        self.servers = servers
        super(ServersMixin, self).__init__(irc)
        
    def _getServers(self):
        # We do this, rather than itertools.cycle the servers in __init__,
        # because otherwise registry updates given as setValues or sets
        # wouldn't be visible until a restart.
        return self.networkGroup.servers()[:] # Be sure to copy!

    def _getNextServer(self):
        if not self.servers:
            self.servers = self._getServers()
        assert self.servers, 'Servers value for %s is empty.' % \
                             self.networkGroup._name
        server = self.servers.pop(0)
        self.currentServer = '%s:%s' % server
        return server
        

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

class Log(object):
    """This is used to have a nice, consistent interface for drivers to use."""
    def connect(self, server):
        self.info('Connecting to %s.', server)

    def connectError(self, server, e):
        if isinstance(e, Exception):
            if isinstance(e, socket.gaierror):
                e = e.args[1]
            else:
                e = utils.exnToString(e)
        self.warning('Error connecting to %s: %s', server, e)

    def disconnect(self, server, e=None):
        if e:
            if isinstance(e, Exception):
                e = utils.exnToString(e)
            self.warning('Disconnect from %s: %s.', server, e)
        else:
            self.info('Disconnect from %s.', server)

    def reconnect(self, network, when=None):
        s = 'Reconnecting to %s' % network
        if when is not None:
            if not isinstance(when, basestring):
                when = self.timestamp(when)
            s += ' at %s.' % when
        else:
            s += '.'
        self.info(s)

    def die(self, irc):
        self.info('Driver for %s dying.', irc)

    debug = staticmethod(supylog.debug)
    info = staticmethod(supylog.info)
    warning = staticmethod(supylog.warning)
    error = staticmethod(supylog.warning)
    critical = staticmethod(supylog.critical)
    timestamp = staticmethod(supylog.timestamp)
    exception = staticmethod(supylog.exception)
    stat = staticmethod(supylog.stat)

log = Log()
        
def newDriver(irc, moduleName=None):
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
    log.debug('Creating new driver for %s.', irc)
    driver = driverModule.Driver(irc)
    irc.driver = driver
    return driver

def parseMsg(s):
    start = time.time()
    msg = ircmsgs.IrcMsg(s)
    log.stat('Time to parse IrcMsg: %s', time.time()-start)
    return msg

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
