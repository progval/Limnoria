#!/usr/bin/env python

from fix import *

import drivers

import twisted.protocols

class TwistedDriver(drivers.IrcDriver, twisted.protocols.basic.LineReceiver):
    def __init__(self, name, irc, (server, port), reconnect=True):
        drivers.IrcDriver.__init__(self, name)
        self.name = name
        self.server = (server, port)
        self.reconnect = reconnect
        self.irc = irc
        irc.driver = irc
        self.delimiter = '\n'
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
