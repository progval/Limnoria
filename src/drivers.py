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

import fix

import re
import os
import sys

import conf
import ansi
import debug
import ircmsgs

_drivers = {}
_deadDrivers = []
_newDrivers = []

class IrcDriver(object):
    """Base class for drivers."""
    def __init__(self):
        _newDrivers.append((self.name(), self))
        if not hasattr(self, 'irc'):
            self.irc = None # This is to satisfy PyChecker.

    def run(self):
        raise NotImplementedError

    def die(self):
        # The end of any overrided die method should be
        # "super(Class, obj).die()", in order to make
        # sure this (and anything else later added) is done.
        _deadDrivers.append(self.name())

    def reconnect(self):
        raise NotImplementedError

    def name(self):
        return repr(self)


class Interactive(IrcDriver):
    """Interactive (stdin/stdout) driver for testing.

    Python statements can be evaluated by beginning the line with a '#'

    Variables can be set using the form "$variable=value", where value is
    valid Python syntactical construct.

    Variables are inserted for $variable in lines.
    """
    _varre = r'[^\\](\$[a-zA-Z_][a-zA-Z0-9_]*)'
    _setre = re.compile('^' + _varre + r'\s*=\s*(.*)')
    _replacere = re.compile(_varre)
    _dict = {}
    def run(self):
        while 1:
            msg = self.irc.takeMsg()
            if not msg:
                break
            else:
                sys.stdout.write(ansi.BOLD + ansi.YELLOW)
                sys.stdout.write(str(msg))
                sys.stdout.write(ansi.RESET)
        line = sys.stdin.readline()
        if line == "":
            self.irc.die()
            self.die()
        elif line == os.linesep:
            pass
        elif self._setre.match(line):
            (var, val) = self._setre.match(line).groups()
            self._dict[var] = eval(val)
        elif line[0] == '#':
            print eval(line[1:])
        else:
            def f(m):
                return self._dict.get(m.group(0), m.group(0))
            line = self._replacere.sub(f, line.strip())
            msg = ircmsgs.privmsg(self.irc.nick, line)
            msg.prefix = 'nick!user@host.domain.tld'
            self.irc.feedMsg(msg)

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
            debug.recoverableException()
            _deadDrivers.append(name)
    for name in _deadDrivers:
        try:
            del _drivers[name]
        except KeyError:
            pass
    while _newDrivers:
        (name, driver) = _newDrivers.pop()
        if name in _drivers:
            _drivers[name].die()
            del _drivers[name]
        _drivers[name] = driver

def newDriver(server, irc, moduleName=conf.driverModule):
    """Returns a new driver for the given server using conf.driverModule."""
    driver = __import__(moduleName).Driver(server, irc)
    irc.driver = driver
    return driver

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
