#!/usr/bin/env python

from fix import *

import time

import conf
import debug
import ircdb
import drivers
import ircmsgs

from twisted.internet import reactor
from twisted.manhole.telnet import Shell, ShellFactory
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
        self.mostRecentCall = reactor.callLater(1, self.checkIrcForMsgs)

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
            if msg:
                self.transport.write(str(msg))
        self.mostRecentCall = reactor.callLater(1, self.checkIrcForMsgs)

    def connectionLost(self):
        self.mostRecentCall.cancel()

    def connectionMade(self):
        self.factory.irc.driver = self
        self.factory.irc.reset()
        #self.mostRecentCall = reactor.callLater(1, self.checkIrcForMsgs)

    def die(self):
        self.transport.loseConnection()
        

class SupyReconnectingFactory(ReconnectingClientFactory):
    maxDelay = 600
    protocol = SupyIrcProtocol
    def __init__(self, (server, port), irc):
        self.irc = irc
        self.server = (server, port)
        reactor.connectTCP(server, port, self)
        

class MyShell(Shell):
    def checkUserAndPass(self, username, password):
        debug.printf(repr(username))
        debug.printf(repr(password))
        try:
            u = ircdb.users.getUser(username)
            debug.printf(u)
            if u.checkPassword(password) and u.checkCapability('owner'):
                debug.printf('returning True')
                return True
            else:
                return False
        except KeyError:
            return False
            
class MyShellFactory(ShellFactory):
    protocol = MyShell

if conf.telnetEnable and __name__ != '__main__':
    reactor.listenTCP(conf.telnetPort, MyShellFactory())
        

Driver = SupyReconnectingFactory

try:
    ignore(poller)
except NameError:
    poller = TwistedRunnerDriver()
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
