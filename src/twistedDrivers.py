#!/usr/bin/env python

from fix import *

import time

import conf
import debug
import drivers
import ircmsgs

from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ReconnectingClientFactory

class TwistedRunnerDriver(drivers.IrcDriver):
    def run(self):
        try:
            reactor.iterate(conf.poll)
        except:
            debug.msg('Except caught outside reactor.', 'normal')
            debug.recoverableException()

class SupyIrcProtocol(LineReceiver):
    delimiter = '\n'
    MAX_LENGTH = 1024
    def __init__(self):
        reactor.callLater(1, self.checkIrcForMsgs)

    def lineReceived(self, line):
        start = time.time()
        msg = ircmsgs.IrcMsg(line)
        debug.msg('Time to parse IrcMsg: %s' % (time.time()-start), 'verbose')
        try:
            self.factory.irc.feedMsg(msg)
        except:
            debug.msg('Exception caught outside Irc object.', 'normal')
            debug.recoverableException()

    def checkIrcForMsgs(self):
        if self.connected:
            msg = self.factory.irc.takeMsg()
            while msg:
                self.transport.write(str(msg))
                msg = self.factory.irc.takeMsg()
        reactor.callLater(1, self.checkIrcForMsgs)

class SupyReconnectingFactory(ReconnectingClientFactory):
    maxDelay = 600
    protocol = SupyIrcProtocol
    def __init__(self, (server, port), irc):
        self.irc = irc
        reactor.connectTCP(server, port, self)
        

try:
    ignore(poller)
except NameError:
    poller = TwistedRunnerDriver()
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
