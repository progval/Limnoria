#!/usr/bin/env python

# Copyright (c) Robert Sanderson All rights reserved.
# See LICENCE file in this distribution for details.

# Documentation on DCC specification
# http://www.mirc.co.uk/help/dccresum.txt
# www.irchelp.org/irchelp/rfc/dccspec.html
# Also several other lesser known/implemented/used commands are floating around
# but not implemented in major clients.

import os
import time
import struct

import log
import conf
import utils
import world
import socket
import ircmsgs
import ircutils
import threading

def isDCC(msg):
    return msg.command == 'PRIVMSG' and msg.args[1][:5] == '\x01DCC '


conf.registerGroup(conf.supybot.protocols, 'dcc')
conf.registerGlobalValue(conf.supybot.protocols.dcc, 'timeout',
                         registry.Integer(120, "Timeout on DCC sockets"))
conf.registerGlobalValue(conf.supybot.protocols.dcc, 'packetSize',
                         registry.Integer(1024, "Size of packet to send"))
conf.registerGlobalValue(conf.supybot.protocols.dcc, 'chatLineLength',
                         registry.Integer(1024, "Max size of line to read"))

# ---- Out Handlers ----

class DCCHandler:
    def __init__(self, irc, nick, hostmask, logger=None):
        self.irc = irc
        self.nick = nick
        self.hostmask = hostmask
        self.sock = None
        if logger:
            self.log = logger
        else:
            self.log = log

        self.timeout = conf.supybot.protocols.dcc.timeout()

    def start(self):
        t = threading.Thread(target=self.open)
        world.threadsSpawned += 1
        t.setDaemon(True)
        t.start()

    def open(self):
        # Override in subclasses to do something
        pass

    def clientConnected(self):
        # Override in subclasses to do something when a client connects
        pass

    def clientClosed(self):
        # Override to do something when a client closes connection
        pass


class SendHandler(DCCHandler):
    """ Handle sending a file """
    def __init__(self, irc, nick, hostmask, filename, logger=None, start=0):
        DCCHandler.__init__(self, irc, nick, hostmask, logger)
        self.filename = filename
        self.startPosition = start
        self.currentPosition = 0
        self.filesize = 0
        self.currentSpeed = 0
        self.bytesSent = 0

    def packetSent(self):
        pass

    def registerPort(self):
        pass

    def open(self):
        ip = conf.supybot.externalIP()
        try:
            self.filesize = os.path.getsize(self.filename)
        except OSError, e:
            self.log.warning('Requested file does not exist: %r',
                             self.filename)
            return
        sock = utils.getSocket(ip)
        try:
            sock.bind((ip, 0))
        except socket.error, e:
            self.log.warning('Could not bind a socket to send.')
            return
        port = sock.getsockname()[1]
        self.port = port
        self.registerPort()
        i = ircutils.dccIP(ip)
        sock.listen(1)
        msg = ircmsgs.dcc(self.nick, 'SEND', self.filename, i, port, self.filesize)
        self.irc.queueMsg(msg)

        # Wait for possible RESUME request to be handled which may change
        # self.startPosition on self
        # See Resume doc (URL in header)
        time.sleep(1)

        try:
            (realSock, addr) = sock.accept()
        except socket.error, e:
            sock.close()
            self.log.info('%r: Send init errored with %s',
                          self.filename, utils.exnToString(e))
            return
        self.log.info('%r: Sending to %s', self.filename, self.nick)

        self.sock = realSock
        fh = file(self.filename)
        try:
            self.clientConnected()
            self.startTime = time.time()
            packetSize = conf.supybot.protocols.dcc.packetSize()
            try:
                slow = 0
                fh.seek(self.startPosition)
                self.currentPosition = fh.tell()
                while self.currentPosition < self.filesize:
                    data = fh.read(min(packetSize, self.filesize - \
                                   self.currentPosition))
                    self.sock.send(data)
                    self.currentPosition = fh.tell()
                    self.bytesSent += 1024
                    self.packetSent()
            except socket.error, e:
                exn = utils.exnToString(e)
                self.log.info('%r: Send errored with %s', self.filename, exn)
            except SendException, e:
                exn = utils.exnToString(e)
                self.log.info('%r: Send aborted with %s', self.filename, exn)

            self.endTime = time.time()
            duration = self.endTime - self.startTime
            self.log.info('%r: Sent %s/%s', self.filename, fh.tell(),
                      self.filesize)
            # Sleep to allow client to finish reading data.
            # This is needed as we'll be here immediately after the final
            # packet
            time.sleep(1.0)
            self.clientClosed()
        finally:
            # Ensure that we're not leaking handles
            fh.close()
            self.sock.close()
    

class ChatHandler(DCCHandler):
    """ Handle a DCC chat (initiate) """
    def lineReceived(self, line):
        # Override in subclasses to process a line of text
        pass

    def open(self):
        ip = conf.supybot.externalIP()
        sock = utils.getSocket(ip)
        lineLength = conf.supybot.protocols.dcc.chatLineLength()
        try:
            sock.bind((ip, 0))
        except socket.error, e:
            self.log.error('Could not bind chat socket.')
            return
        port = sock.getsockname()[1]
        i = ircutils.dccIP(ip)
        sock.listen(1)
        msg = ircmsgs.dcc(self.nick, 'CHAT', 'chat', i, port)
        self.irc.queueMsg(msg)
        try:
            (realSock, addr) = sock.accept()
        except socket.timeout:
            sock.close()
            self.log.info('CHAT to %s timed out', self.nick)
            return
        self.log.info('CHAT accepted from %s', self.nick)
        realSock.settimeout(self.timeout)
        self.startTime = time.time()
        self.sock = realSock
        try:
            self.clientConnected()
            while 1:
                line = realSock.recv(lineLength)
                if line != "\n":
                    self.lineReceived(line)
        except socket.error, e:
            self.log.info('CHAT ended with %s', self.nick)
        finally:
            self.sock.close()
            self.endTime = time.time()
            self.clientClosed()


# ---- In Handlers ----


class DCCReqHandler:
    def __init__(self, irc, msg, args, logger=None):
        self.irc = irc
        self.msg = msg
        self.args = args
        if logger:
            self.log = logger
        else:
            self.log = log

    def start(self):
        t = threading.Thread(target=self.open)
        world.threadsSpawned += 1
        t.setDaemon(True)
        t.start()

    def clientConnected(self):
        pass

    def clientClosed(self):
        pass


class SendReqHandler(DCCReqHandler):
    """ We're being sent a file """

    def __init__(self, *args, **kw):
        DCCReqHandler.__init__(self, *args, **kw)
        # This should be added to by subclasses
        self.incomingDir = conf.supybot.directories.data()
        self.filename = self.args[0]
        self.ip = ircutils.unDccIP(int(self.args[1]))
        self.port = int(self.args[2])
        self.filesize = int(self.args[3])
        self.filemode = 'w'


    def receivedPacket(self):
        # Override in subclass to do something with each packet received
        pass

    def open(self):
        if (os.path.exists(self.filename)):
            currsize = os.path.getsize(self.filename)
            if (self.filesize > currsize):
                # Send RESUME DCC message and wait for ACCEPT
                # See AcceptReqHandler below
                msg = ircutils.dcc(self.nick, 'RESUME', self.filename,
                                   self.port, currsize)
                self.irc.queueMsg(msg)
                time.sleep(1)
                if self.filemode != 'a':
                    # Didn't get an acknowledge for the RESUME
                    # Zero file and read from scratch
                    os.remove(self.filename)

        sock = utils.getSocket(self.ip)
        try:
            sock.connect((self.ip, self.port))
        except socket.error, e:
            self.log.info('File receive could not connect')
            return

        self.clientConnected()
        rootedName = os.path.abspath(os.path.join(self.incomingDir,
                                                  self.filename))
        if not rootedName.startswith(self.incomingDir):
            self.log.warning('%s tried to send relative file', self.msg.nick)
            return
           
        fh = file(rootedName, self.filemode)
        self.bytesReceived = 0
        self.startTime = time.time()
        pktSize = conf.supybot.protocols.dcc.packetSize()
        self.log.info('%r: Send starting from %s', self.filename,
                      self.msg.nick))
        try:
            while self.bytesReceived < self.filesize:
                amnt = min(self.filesize - self.bytesReceived, pktSize)
                d = sock.recv(amnt)
                self.bytesReceived += len(d)
                # Required to send back packed integer to acknowledge receive
                sock.send(struct.pack("!I", self.bytesReceived))
                f.write(d)
                self.receivedPacket()
        except socket.error, e:
            exn = utils.exnToString(e)
            self.log.info('%r: Send died with %s', filename, exn)
        finally:
            self.endTime = time.time()
            sock.close()
            f.close()
            self.log.info('%r: Received %s/%s in %d seconds',
                          self.filename, self.bytesReceived, self.filesize,
                              self.endTime - self.startTime)
            self.clientClosed()


class ResumeReqHandler(DCCReqHandler):

    def _getSendHandler(self):
        # This will work in theory, BUT note well, if you instantiate
        # and do not override this to return the REAL SendHandler
        # the client may still get the original startPosition of 0
        # See RESUME documentation URL in header
        hostmask = self.irc.state.nickToHostmask(self.msg.nick)
        h = SendHandler(self.irc, self.msg.nick, hostmask, self.filename,
                        start=self.startPosition)
        return h

    def open(self):
        # filename is (apparently) ignored by mIRC
        # so don't depend on it.
        self.filename = self.args[0]
        self.port = int(self.args[1])
        self.startPosition = int(self.args[2])

        msg = ircutils.dcc(self.msg.nick, "ACCEPT", self.filename, self.port,
                           self.startPosition)
        self.irc.queueMsg(msg)
        cxn = self._getSendHandler()
        cxn.startPosition = self.startPosition
        self.log.info('%r: RESUME received for %s', self.filename,
                      self.startPosition)

class AcceptReqHandler(DCCReqHandler):

    def _getReceiveHandler(self):
        # We need the original SendReqHandler, which needs some cross request
        # logic that we don't provide.
        # The following may work, but this should be overridden
        h = SendReqHandler(self.irc, self.msg, self.args)
        return h

    def open(self):
        self.filename = self.args[0]
        self.port = int(self.args[1])
        cxn = self._getReceiveHandler()
        cxn.filemode = 'a'
        self.log.info('%r: Got ACCEPT to resume file', self.filename)


class ChatReqHandler(DCCReqHandler):
    
    def open(self):
        ip = ircutils.unDccIP(int(self.args[1]))
        port = int(self.args[2])
        lineLength = conf.supybot.protocols.dcc.chatLineLength()

        sock = utils.getSocket(ip)
        try:
            sock.connect((ip, port))
        except:
            self.log.error('Could not connect to chat socket.')           
            return
        self.sock = sock
        sock.send('\n')
        try:
            while 1:
                line = sock.recv(lineLength)
                self.lineReceived(line)
            except socket.error, e:
                self.log.info('Chat finished')
        finally:
            sock.close()


            
