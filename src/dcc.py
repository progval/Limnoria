#!/usr/bin/env python
# You need a copyright notice here, azaroth.

# You might do well to put links to the documentation you're basing this on
# here.  Then other people can help maintain it more easily.

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
    # This needs to be more specific, it would catch too many messages
    # discussing DCC stuff.  I added a test for this.
    return msg.command == 'PRIVMSG' and msg.args[1][1:4] == 'DCC'
   

# ---- Out Handlers ----

class DCCHandler:
    # You should reconsider whether all these arguments are necessary in the
    # constructor.  Long argument lists generally mean bad factoring.
    def __init__(self, irc, nick, hostmask, logger=None):
        self.irc = irc
        self.nick = nick
        self.hostmask = hostmask
        self.sock = None
        # XXX () in if/while.
        if (logger):
            # XXX Log something specific
            self.log = logger
        else:
            self.log = log
        # XXX Why 120?  Shouldn't that be configurable?
        self.timeout = 120

    def start(self):
        # What's this self.open?  I don't see an open method.
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
    # What I said about long argument lists in DCCHandler applies doubly here.
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
        host = ircutils.hostFromHostmask(self.irc.prefix)
        if not ip:
            try:
                ip = socket.gethostbyname(host)
            except: # XXX Don't use blank excepts.
                # XXX Be sure you mention who you are and why you couldn't do
                # what you should.
                self.log.warning('Could not determine IP address')
                return
        try:
            self.filesize = os.path.getsize(self.filename)
        except OSError, e:
            # XXX: There should be a log.warning or log.error here.
            # Doesn't exist
            # ^^^^^^^^^^^^^ What doesn't exist?
            return

        sock = utils.getSocket(ip)
        try:
            sock.bind((ip, 0))
        except socket.error, e:
            # XXX: There should be a log.warning or log.error here.
            return
        port = sock.getsockname()[1]
        self.port = port

        self.registerPort()

        i = ircutils.dccIP(ip)
        sock.listen(1)
##         self.irc.queueMsg(ircmsgs.privmsg(self.nick,
##               '\x01DCC SEND %s %s %d %d\x01' % (self.filename, i, port,
##                                                 self.filesize)))
## That formatting is bad.  Try this instead:
##         msg = ircmsgs.privmsg(self.nick,
##                               '\x01DCC SEND %s %s %s %s\x01' % \
##                               (self.filename, i, port, self.filesize))
##         self.irc.queueMsg(msg)
## Even better, I'll define a function ircmsgs.py.
        msg = ircmsgs.dcc(self.nick, 'SEND', self.filename, i, port, self.filesize)
        self.irc.queueMsg(msg)
        # Wait for possible RESUME
        # That comment isn't enough, why are we really sleeping?  Why only one
        # second?  A link to some documentation might help.
        time.sleep(1)

        try:
            (realSock, addr) = sock.accept()
        except socket.error, e:
            sock.close()
            # Remember, we dont' use % in log strings -- we just put the
            # arguments there after the string.  utils.exnToString(e) gives a
            # prettier string form than just e; the latter doesn't show what the
            # class of the exception is.
            # XXX % in log.
            self.log.info('%r: Send init errored with %s',
                          self.filename, utils.exnToString(e))
            return
        # XXX % in log.
        self.log.info('%r: Sending to %s' % (self.filename, self.nick))
        # There shouldn't be blank space like this in a single function.  But
        # then again, a single function shouldn't be this long.  Perhaps you
        # can break this into multiple functions?


        self.sock = realSock
        fh = file(self.filename)
        # Why no arguments to this clientConnected method?
        self.clientConnected()
        self.startTime = time.time()
        try:
            slow = 0
            fh.seek(self.startPosition)
            self.currentPosition = fh.tell()
            # Again, please no parentheses around the conditions of while loops
            # and if statements.
            # XXX () in while/if
            while (self.currentPosition < self.filesize):
                data = fh.read(min(1024, self.filesize-self.currentPosition))
                self.sock.send(data)
                self.currentPosition = fh.tell()
                self.bytesSent += 1024
                self.packetSent()
                
        except socket.error, e:
            # Aborted/timedout chat
            # XXX % in log.
            self.log.info('%r: Send errored with %s' %
                                 (self.filename, e))
        except SendException, e:
            # XXX % in log.
            self.log.info('%r: Send aborted with %s' %
                          (self.filename, e))
        # Wait for send to complete
        self.endTime = time.time()
        duration = self.endTime - self.startTime
        # XXX.  % in log.  Also use %r here instead of %s.
        self.log.info('\'%s\': Sent %s/%s' %
                             (self.filename, fh.tell(), self.filesize))
        # Why sleep here?
        time.sleep(1.0)
        # XXX These closes should go in a finally: block.
        fh.close()
        self.sock.close()
        self.clientClosed()
    

class ChatHandler(DCCHandler):
    """ Handle a DCC chat (initiate) """
    def handleLine(self, line):
        # What's this for?  Documentation!
        pass

    def open(self):
        ip = conf.supybot.externalIP()
        # XXX () in while/if
        if (not ip):
            # Try and find it with utils
            # No, I'll fix externalIP to return something sane for you.
            pass

        sock = utils.getSocket(ip)
        try:
            sock.bind((ip, 0))
        except socket.error, e:
            # XXX Who are you, and why can't you?
            self.irc.error('Unable to initiate DCC CHAT.')
            return
        port = sock.getsockname()[1]
        i = ircutils.dccIP(ip)
        sock.listen(1)
        # XXX Use ircmsgs.dcc
        self.irc.queueMsg(ircmsgs.privmsg(self.nick,
                               '\x01DCC CHAT chat %s %s\x01' % (i, port)))
        try:
            (realSock, addr) = sock.accept()
        except socket.timeout:
            # XXX % in log
            self.log.info('CHAT to %s timed out' % self.nick)
            return
        # XXX % in log.
        self.log.info('CHAT accepted from %s' % self.nick)
        realSock.settimeout(self.timeout)
        self.startTime = time.time()
        self.sock = realSock
        try:
            self.clientConnected()
            # XXX () in while/if
            while (1):
                # XXX Why 66000?
                line = realSock.recv(66000)
                # XXX Don't use <>; use !=.
                if (line <> "\n"):
                    self.handleLine(line)
        except socket.error, e:
            # Aborted/timedout chat. Only way to end.
            # Are you sure you don't still need to close the socket here? 
            # XXX % in log.  Also, don't use parens around a single value.
            self.log.info('CHAT ended with %s' % (self.nick))
        self.endTime = time.time()
        self.clientClosed()


# ---- In Handlers ----


class DCCReqHandler:
    def __init__(self, irc, msg, args, logger=None):
        self.irc = irc
        self.msg = msg
        self.args = args
        # XXX: () in while/if
        if (logger):
            self.log = logger
        else:
            self.log = log

    def start(self):
        t = threading.Thread(target=self.open)
        world.threadsSpawned += 1
        t.setDaemon(True)
        t.start()

    # Always put a blank line between methods, even if they just pass.
    def clientConnected(self):
        pass
    # XXX No blank line between methods.
    def clientClosed(self):
        pass


class SendReqHandler(DCCReqHandler):
    """ We're being sent a file """
    # These should be setup in __init__ unless they have a real reason for
    # being class variables.
    ip = ""
    filename = ""
    port = 0
    filesize = 0

    def __init__(self, *args, **kw):
        DCCReqHandler.__init__(self, *args, **kw)
        # This should be added to by subclasses
        self.incomingDir = conf.supybot.directories.data()

    def receivedPacket(self):
        # What's this method for?  Document.
        pass

    def open(self):
        # XXX: Should this be factored into a separate function?
        self.filename = self.args[0]
        self.ip = ircutils.unDccIP(int(self.args[1]))
        self.port = int(self.args[2])
        self.filesize = int(self.args[3])

        # XXX () in while/if
        if (os.path.exists(self.filename)):
            currsize = os.path.getsize(self.filename)
            if (self.filesize > currsize):
                # Send RESUME DCC message and wait for ACCEPT
                # XXX Line too long.
                self.irc.queueMsg(ircmsgs.privmsg(self.msg.nick,
                       '\x01DCC RESUME %s %d %d\x01' % (self.filename, self.port, currsize)))
                # URHG?
                # What does "URGH?" mean?  Details!
                return

        sock = utils.getSocket(self.ip)
        try:
            sock.connect((self.ip, self.port))
        except:
            # XXX blank except, no log.
            return

        self.clientConnected()

        # XXX long line; also, what does "rootedName" really mean?
        rootedName = os.path.abspath(os.path.join(self.incomingDir, self.filename))
        # XXX Use the startswith() method on strings.
        if (rootedName[:len(self.incomingDir)] != self.incomingDir):
            # XXX % in log.
            self.log.warning('%s tried to send relative file' % self.msg.nick)
            return
           
        # XXX f is generally used for functions; use fh, or fd, or a name 
        # representative what file is being used.
        f = file(rootedName, 'w')
        self.bytesReceived = 0
        self.startTime = time.time()
        # XXX This is a src/ plugin.  It shouldn't depend on any plugin.  You
        # definitely can't use any plugin's registry variables.  This is the
        # number 1 biggest problem in this file.
        pktSize = conf.supybot.plugins.FServe.packetSize()
        # XXX % in log, use %r
        self.log.info('\'%s\': Send starting from %s' %
                             (self.filename, self.msg.nick))
        try:
            # XXX () in while/if
            while (self.bytesReceived < self.filesize):
                amnt = min(self.filesize - self.bytesReceived, pktSize)
                d = sock.recv(amnt)
                self.bytesReceived += len(d)
                # XXX What's this do?  Document please :)
                sock.send(struct.pack("!I", self.bytesReceived))
                f.write(d)
                self.receivedPacket()
        except socket.error, e:
            # % in log, use %r.
            self.log.info('\'%s\': Send died with %s' % (filename, e))
            # XXX If you intend to fall through, i.e., not to return here, you
            # should have a comment to that effect.
        self.endTime = time.time()
        # XXX Perhaps these closes should go in a finally: block?
        sock.close()
        f.close()
        # XXX % in log, use %r.
        self.log.info('\'%s\': Received %s/%s in %d seconds' %
                             (self.filename, self.bytesReceived, self.filesize,
                              self.endTime - self.startTime))
        self.clientClosed()


class ResumeReqHandler(DCCReqHandler):

    def _getSendHandler(self):
        # XXX Explain this comment more.
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
        # XXX Use ircmsgs.dcc.
        self.irc.queueMsg(ircmsgs.privmsg(self.msg.nick,
                    '\x01DCC ACCEPT %s %s %s\x01' % (self.filename, self.port,
                                                     self.startPosition)))

        cxn = self._getSendHandler()
        cxn.startPosition = self.startPosition
        # XXX % in log.
        self.log.info('%r: RESUME received for %s' %
                      (self.filename, self.startPosition))




    def handleACCEPT(self):
        port = int(self.args[1])
        # XXX I thought we got rid of caller?
        (ip, filename, filesize) = self.caller.resumeSends[port]
        recv = os.path.getsize(filename)
        
        sock = utils.getSocket(ip)
        try:
            sock.connect((ip, port))
        except:
            # XXX No log, blank except.
            return
        sock.settimeout(conf.supybot.plugins.FServe.timeout())

        incoming = os.path.join(conf.supybot.directories.data(),
                                conf.supybot.plugins.FServe.receiveDirectory())
        rootedName = os.path.abspath(os.path.join(incoming, filename))
        # XXX Use startswith, don't use <>
        if (rootedName[:len(incoming)] <> incoming):
            # XXX % in log.
            self.caller.log.warning('%s tried to send relative file' %
                                    self.msg.nick)
            # XXX Shouldn't you close the sock?  If you had a finally block,
            # you wouldn't have to worry about that :)
            return
           
        f = file(rootedName, 'a')
        start= time.time()
        try:
            # XXX () in while/if
            while (recv < filesize):
                amnt = min(filesize - recv, 1024)
                d = sock.recv(amnt)
                recv += len(d)
                sock.send(struct.pack("!I", recv))
                f.write(d)
        except socket.error, e:
            # XXX % in log, use %r
            self.caller.log.info('\'%s\': Resume died with %s' %
                                 (filename, e))
        end = time.time()
        durn = end - start
        # XXX finally material, especially since you return early above.
        sock.close()
        f.close()
        # XXX % in log, use %r.
        self.caller.log.info('\'%s\': %s/%s received in %s seconds' %
                             (filename, recv, filesize, durn))


    def handleCHAT(self):
        ip = ircutils.unDccIP(int(self.args[1]))
        port = int(self.args[2])

        sock = utils.getSocket(ip)
        try:
            sock.connect((ip, port))
        except:
            # XXX Log something!  Who, why.
            return
        sock.settimeout(conf.supybot.plugins.FServe.timeout())
        sock.send("Hi!\n")
        sock.recv(1024)



