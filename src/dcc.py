
import utils
import conf
import ircutils
import socket
import ircmsgs
import log
import threading
import world

import os
import time
import struct

def isDCC(msg):
    if (msg.args[1][1:4] == "DCC"):
        return True
    else:
        return False
   

# ---- Out Handlers ----

class DCCHandler:
    def __init__(self, irc, nick, hostmask, logger = None):
        self.irc = irc
        self.nick = nick
        self.hostmask = hostmask
        self.sock = None
        if (logger):
            # Log somewhere specific
            self.log = logger
        else:
            self.log = log
        self.timeout = 120

    def start(self):
        t = threading.Thread(target=self.open)
        world.threadsSpawned += 1
        t.setDaemon(True)
        t.start()

    def clientConnected(self):
        pass
    def clientClosed(self):
        pass


class SendHandler(DCCHandler):
    """ Handle sending a file """

    def __init__(self, irc, nick, hostmask, filename, logger = None, start=0):
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
        host = ircutils.hostFromHostmask(self.irc.prefix)
        if (not ip):
            try:
                ip = socket.gethostbyname(host)
            except:
                self.log.warning('Could not determine IP address')
                return
        try:
            self.filesize = os.path.getsize(self.filename)
        except OSError, e:
            # Doesn't exist
            return

        sock = utils.getSocket(ip)
        try:
            sock.bind((ip, 0))
        except socket.error, e:
            return
        port = sock.getsockname()[1]
        self.port = port

        self.registerPort()

        i = ircutils.dccIP(ip)
        sock.listen(1)
        self.irc.queueMsg(ircmsgs.privmsg(self.nick,
              '\x01DCC SEND %s %s %d %d\x01' % (self.filename, i, port,
                                                self.filesize)))
        # Wait for possible RESUME
        time.sleep(1)

        try:
            (realSock, addr) = sock.accept()
        except socket.error, e:
            sock.close()
            self.log.info('%r: Send init errored with %s' %
                                 (self.filename, e))
            return
        self.log.info('%r: Sending to %s' % (self.filename, self.nick))


        self.sock = realSock
        fh = file(self.filename)
        self.clientConnected()
        self.startTime = time.time()
        try:
            slow = 0
            fh.seek(self.startPosition)
            self.currentPosition = fh.tell()
            while (self.currentPosition < self.filesize):
                data = fh.read(min(1024, self.filesize-self.currentPosition))
                self.sock.send(data)
                self.currentPosition = fh.tell()
                self.bytesSent += 1024
                self.packetSent()
                
        except socket.error, e:
            # Aborted/timedout chat
            self.log.info('%r: Send errored with %s' %
                                 (self.filename, e))
        except SendException, e:
            self.log.info('%r: Send aborted with %s' %
                          (self.filename, e))
        # Wait for send to complete
        self.endTime = time.time()
        duration = self.endTime - self.startTime
        self.log.info('\'%s\': Sent %s/%s' %
                             (self.filename, fh.tell(), self.filesize))
        time.sleep(1.0)
        fh.close()
        self.sock.close()
        self.clientClosed()
    

class ChatHandler(DCCHandler):
    """ Handle a DCC chat (initiate) """

    def handleLine(self, line):
        pass

    def open(self):
        ip = conf.supybot.externalIP()
        if (not ip):
            # Try and find it with utils
            pass

        sock = utils.getSocket(ip)
        try:
            sock.bind((ip, 0))
        except socket.error, e:
            self.irc.error('Unable to initiate DCC CHAT.')
            return
        port = sock.getsockname()[1]
        i = ircutils.dccIP(ip)
        sock.listen(1)
        self.irc.queueMsg(ircmsgs.privmsg(self.nick,
                               '\x01DCC CHAT chat %s %s\x01' % (i, port)))
        try:
            (realSock, addr) = sock.accept()
        except socket.timeout:
            self.log.info('CHAT to %s timed out' % self.nick)
            return
        self.log.info('CHAT accepted from %s' % self.nick)
        realSock.settimeout(self.timeout)
        self.startTime = time.time()
        self.sock = realSock
        try:
            self.clientConnected()
            while (1):
                line = realSock.recv(66000)
                if (line <> "\n"):
                    self.handleLine(line)
        except socket.error, e:
            # Aborted/timedout chat. Only way to end.
            self.log.info('CHAT ended with %s' % (self.nick))
        self.endTime = time.time()
        self.clientClosed()


# ---- In Handlers ----


class DCCReqHandler:
    def __init__(self, irc, msg, args, logger=None):
        """caller is the callback handler to log against"""
        self.irc = irc
        self.msg = msg
        self.args = args
        if (logger):
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
    filename = ""
    ip = ""
    port = 0
    filesize = 0

    def __init__(self, *args, **kw):
        DCCReqHandler.__init__(self, *args, **kw)
        # This should be added to by subclasses
        self.incomingDir = conf.supybot.directories.data()

    def receivedPacket(self):
        pass

    def open(self):
        self.filename = self.args[0]
        self.ip = ircutils.unDccIP(int(self.args[1]))
        self.port = int(self.args[2])
        self.filesize = int(self.args[3])

        if (os.path.exists(self.filename)):
            currsize = os.path.getsize(self.filename)
            if (self.filesize > currsize):
                # Send RESUME DCC message and wait for ACCEPT
                self.irc.queueMsg(ircmsgs.privmsg(self.msg.nick,
                       '\x01DCC RESUME %s %d %d\x01' % (self.filename, self.port, currsize)))
                # URHG?
                return

        sock = utils.getSocket(self.ip)
        try:
            sock.connect((self.ip, self.port))
        except:
            return

        self.clientConnected()

        rootedName = os.path.abspath(os.path.join(self.incomingDir, self.filename))
        if (rootedName[:len(self.incomingDir)] != self.incomingDir):
            self.log.warning('%s tried to send relative file' % self.msg.nick)
            return
           
        f = file(rootedName, 'w')
        self.bytesReceived = 0
        self.startTime = time.time()
        pktSize = conf.supybot.plugins.FServe.packetSize()
        self.log.info('\'%s\': Send starting from %s' %
                             (self.filename, self.msg.nick))
        try:
            while (self.bytesReceived < self.filesize):
                amnt = min(self.filesize - self.bytesReceived, pktSize)
                d = sock.recv(amnt)
                self.bytesReceived += len(d)
                sock.send(struct.pack("!I", self.bytesReceived))
                f.write(d)
                self.receivedPacket()
        except socket.error, e:
            self.log.info('\'%s\': Send died with %s' % (filename, e))
        self.endTime = time.time()
        sock.close()
        f.close()
        self.log.info('\'%s\': Received %s/%s in %d seconds' %
                             (self.filename, self.bytesReceived, self.filesize,
                              self.endTime - self.startTime))
        self.clientClosed()


class ResumeReqHandler(DCCReqHandler):

    def _getSendHandler(self):
        # This is bad. It will just start a new send.
        # It needs to look up original
        hostmask = self.irc.state.nickToHostmask(self.msg.nick)
        h = SendHandler(self.irc, self.msg.nick, hostmask, self.filename,
                        start=self.startPosition)
        return h

    def open(self):
        # filename is (apparently) ignored by mIRC
        self.filename = self.args[0]
        self.port = int(self.args[1])
        self.startPosition = int(self.args[2])
        self.irc.queueMsg(ircmsgs.privmsg(self.msg.nick,
                    '\x01DCC ACCEPT %s %s %s\x01' % (self.filename, self.port,
                                                     self.startPosition)))

        cxn = self._getSendHandler()
        cxn.startPosition = self.startPosition
        self.log.info('%r: RESUME received for %s' %
                      (self.filename, self.startPosition))




    def handleACCEPT(self):
        port = int(self.args[1])
        (ip, filename, filesize) = self.caller.resumeSends[port]
        recv = os.path.getsize(filename)
        
        sock = utils.getSocket(ip)
        try:
            sock.connect((ip, port))
        except:
            return
        sock.settimeout(conf.supybot.plugins.FServe.timeout())

        incoming = os.path.join(conf.supybot.directories.data(),
                                conf.supybot.plugins.FServe.receiveDirectory())
        rootedName = os.path.abspath(os.path.join(incoming, filename))
        if (rootedName[:len(incoming)] <> incoming):
            self.caller.log.warning('%s tried to send relative file' %
                                    self.msg.nick)
            return
           
        f = file(rootedName, 'a')
        start= time.time()
        try:
            while (recv < filesize):
                amnt = min(filesize - recv, 1024)
                d = sock.recv(amnt)
                recv += len(d)
                sock.send(struct.pack("!I", recv))
                f.write(d)
        except socket.error, e:
            self.caller.log.info('\'%s\': Resume died with %s' %
                                 (filename, e))
        end = time.time()
        durn = end - start
        sock.close()
        f.close()
        self.caller.log.info('\'%s\': %s/%s received in %s seconds' %
                             (filename, recv, filesize, durn))


    def handleCHAT(self):
        ip = ircutils.unDccIP(int(self.args[1]))
        port = int(self.args[2])

        sock = utils.getSocket(ip)
        try:
            sock.connect((ip, port))
        except:
            return
        sock.settimeout(conf.supybot.plugins.FServe.timeout())
        sock.send("Hi!\n")
        sock.recv(1024)



