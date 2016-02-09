###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2009, James McCoy
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

import socket

from .. import conf, ircmsgs, log as supylog, utils
from ..utils import minisix

_drivers = {}
_deadDrivers = set()
_newDrivers = []

class IrcDriver(object):
    """Base class for drivers."""
    def __init__(self, *args, **kwargs):
        add(self.name(), self)
        super(IrcDriver, self).__init__(*args, **kwargs)

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
        super(ServersMixin, self).__init__()

    def _getServers(self):
        # We do this, rather than utils.iter.cycle the servers in __init__,
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
    _deadDrivers.add(name)

def run():
    """Runs the whole driver loop."""
    for (name, driver) in _drivers.items():
        try:
            if name not in _deadDrivers:
                driver.run()
        except:
            log.exception('Uncaught exception in in drivers.run:')
            _deadDrivers.add(name)
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
        _deadDrivers.discard(name)
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
            else:
                e = str(e)
            if not e.endswith('.'):
                e += '.'
            self.warning('Disconnect from %s: %s', server, e)
        else:
            self.info('Disconnect from %s.', server)

    def reconnect(self, network, when=None):
        s = 'Reconnecting to %s' % network
        if when is not None:
            if not isinstance(when, minisix.string_types):
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

log = Log()

def newDriver(irc, moduleName=None):
    """Returns a new driver for the given server using the irc given and using
    conf.supybot.driverModule to determine what driver to pick."""
    # XXX Eventually this should be made to load the drivers from a
    #     configurable directory in addition to the installed one.
    if moduleName is None:
        moduleName = conf.supybot.drivers.module()
    if moduleName == 'default':
        moduleName = 'supybot.drivers.Socket'
    elif not moduleName.startswith('supybot.drivers.'):
        moduleName = 'supybot.drivers.' + moduleName
    driverModule = __import__(moduleName, {}, {}, ['not empty'])
    log.debug('Creating new driver (%s) for %s.', moduleName, irc)
    driver = driverModule.Driver(irc)
    irc.driver = driver
    return driver

def parseMsg(s):
    s = s.strip()
    if s:
        msg = ircmsgs.IrcMsg(s)
        return msg
    else:
        return None

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
