#!/usr/bin/env python

import plugins

import socket
import textwrap
import threading
import struct
import time
import os
import os.path
import glob

import dcc
import conf
import utils
import world
import ircmsgs
import ircutils
import privmsgs
import callbacks
import registry

conf.registerPlugin('FServe')
conf.registerGlobalValue(conf.supybot.plugins.FServe, 'packetSize',
           registry.Integer(1024, 'Size of packets to send/receive with DCC'))
conf.registerGroup(conf.supybot.plugins.FServe, 'queues')
conf.registerChannelValue(conf.supybot.plugins.FServe, 'queueNames',
                          registry.SpaceSeparatedListOfStrings([],
                                   'List of queues for this channel'))

# --- Exceptions ---

class QueueException(Exception):
    msg = "Could not queue file"
    def __init__(self, m):
        self.msg = m


# --- Handlers ---

class SendHandler(dcc.SendHandler):
    caller = None

    def clientConnected(self):
        self.sock.settimeout(self.caller.timeout)

    def packetSent(self):
        self.currentSpeed = (self.bytesSent / (time.time() - self.startTime))
        if (self.currentSpeed > self.caller.maxSpeed):
            time.sleep(0.9)
        if (self.currentSpeed < self.caller.minSpeed):
            #Allow a little leeway
            slow += 1
            if (slow > 5):
                # Too Slow
                self.log.info('\'%s\': Send too slow' % (self.filename))
                raise SendException('Too slow')

    def clientClosed(self):
        # alert queue that we're done
        self.caller.sendFinished(self)

    def registerPort(self):
        pass



class ChatHandler(dcc.ChatHandler):

    def __init__(self, irc, nick, mask, queue=None):
        self.caller = queue
        dcc.ChatHandler.__init__(self, irc, nick, mask)
        if (queue):
            self.currentDir =  os.path.join(conf.supybot.directories.data(),
                                            queue.sendDir)
        else:
            self.currentDir =  os.path.join(conf.supybot.directories.data())
        self.baseDir = self.currentDir

    def cmd_ls(self, args):
        """ Show files in current directory, using globs """
        if args:
            files = []
            for a in args:                
                for i in glob.glob(os.path.join(self.currentDir, a)):
                    if (i[:2] == "./"):
                        i = i[2:]
                    if (i[:len(self.currentDir)] == self.currentDir):
                        i = i[len(self.currentDir)+1:]
                    if (not i in files):
                        files.append(i)
        else:
            files = os.listdir(self.currentDir)
        if (not files):
            self.sock.send("There are no matching files.\n");
        files.sort()
        flist = []
        dirlist = []
        for f in files:
            full = os.path.join(self.currentDir, f)
            if (os.path.isdir(full)):
                dirlist.append(ircutils.mircColor(' %s/' % f, 'blue'))
            else:
                size = os.path.getsize(full)
                if (size > 1024000):
                    size = '%sMb' % (size / 1024000)
                elif (size > 1024):
                    size = '%sKb' % (size / 1024)
                flist.append('%s  [%s]' % (f, size))
        self.sock.send('\n'.join(dirlist) + '\n' + '\n'.join(flist) + "\n")

    def cmd_dir(self, args):
        return self.cmd_ls(args)
    def cmd_list(self, args):
        return self.cmd_ls(args)

    def cmd_cd(self, args):
        """ Change current directory """
        d = args[0]
        full = os.path.join(self.currentDir, d)
        full = os.path.abspath(full)
        if (len(full) < len(self.baseDir)):
            self.sock.send("Already in root directory\n");
            return
        if (os.path.exists(full)):
            if (os.path.isdir(full)):
                self.currentDir = full
                self.sock.send('Current directory: %s\n' %
                               self.currentDir[len(self.baseDir)+1:])
            else:
                self.sock.send('%s is not a directory\n' % d)
        else:
            self.sock.send('%s does not exist\n' % d)
        
    def cmd_get(self, args):
        fn = ' '.join(args)
        full = os.path.join(self.currentDir, fn)

        try:
            size = os.path.getsize(full)
        except OSError, e:
            f = glob.glob(full)
            if (len(f) == 1):
                full = f[0]
                size = os.path.getsize(full)
            else:
                self.sock.send('That matches more than one file\n')
                return
        min = self.caller.instantSendSize
        if (size < min):
            # Instant send
            self.caller.spawnSend(self.irc, self.nick, self.hostmask, full)
        else:
            # Check queues
            try:
                posn = self.caller.addFile(self.irc, self.nick, self.hostmask, full)
                self.sock.send('File queued at position %s\n' %
                               (posn))
                self.caller.maybeSend()
            except QueueException, e:
                self.sock.send(e.msg + "\n")
                
    def cmd_close(self, line):
        self.sock.send('Bye!\n')
        self.sock.close()
    def cmd_quit(self, line):
        self.cmd_close([])

    def cmd_queues(self, args):
        queues = self.caller.queuedFiles
        lines = []
        for q in range(len(queues)):
            if (not args or queues[q][0] == args[0]):
                fn = os.path.split(queues[q][1])[1]
                when = time.ctime(queues[q][3])
                lines.append('%s: %s  (by %s@%s)' % (q, fn, queues[q][0], when[4:-5]))
        if (lines):
            self.sock.send('\n'.join(lines) + '\n')
        else:
            self.sock.send('There is currently nothing queued.\n')

    def cmd_myqueues(self, args):
        self.cmd_queues([self.msg.nick])
            
    def cmd_sends(self, line):
        sends = self.caller.sends
        lines = []
        for i in (range(len(sends))):
            s = sends[i]
            sender = s[4]           
            fn = os.path.split(s[1])[1]
            secs = (sender.filesize - sender.currentPosition) / sender.currentSpeed
            if (secs > 3600):
                t = '%sh' % int(secs / 3600)
            elif (secs > 60):
                t = '%sm' % int(secs / 60)
            else:
                t = '%ss' % int(secs)
            lines.append('%s: %s\n  (to %s @ %sCPS, %s remaining)' % (i, fn, s[0], int(sender.currentSpeed), t))
            
        if (lines):
            self.sock.send('\n'.join(lines) + '\n')
        else:
            self.sock.send('There is currently nothing sending.\n')

    def cmd_remove(self, args):
        # remove a queue by number
        idx = args[0]
        if (not idx.isdigit()):
            self.sock.send('Usage:  remove <queue position>\n')
        else:
            posn = int(idx)
            queues = self.caller.queuedFiles
            if (len(queues) < posn or posn < 0):
                self.sock.send('There is no such queue position\n')
            else:
                # XXX infintesimal race condition
                del self.caller.queuedFiles[posn]
                self.sock.send('Removed queue.\n')
        
    def cmd_help(self, line):
        pass

    def chatConnected(self):
        self.sock.send("Welcome.\n")
        self.cmd_ls([])

    def handleLine(self, line):
        args = line.split()
        if (not args):
            return
        if (not hasattr(self, 'cmd_%s' % args[0])):
            self.sock.send('Unknown command: %s\n' % args[0])
        else:
            fn = getattr(self, 'cmd_%s' % args[0])
            fn(args[1:])


class AdminHandler(ChatHandler):
    
    def cmd_config(self, args):
        pass




# --- Queue Object ---

class Queue:
    name = ""
    plugin = None
    channel = ""
    timeout = 0
    maxSpeed = 0
    minSpeed = 0
    maxQueues = 0
    instantSendSize = 0
    maxSends = 0
    receiveDir = ""
    sendDir = ""
    allowedModes = []
    allowedMasks = []
    allowedNicks = []
    bannedNicks = []
    bannedMasks = []
    chatHandler = ""
    sendHandler = ""

    sends = []
    queuedFiles = []
    filesSent = 0
    bytesSent = 0
    leeches = {}

    def __init__(self, plug, channel, name):
        self.name = name
        self.plugin = plug
        self.channel = channel

        try:
            self.timeout = plug.registryValue("queues.%s.timeout" % name, channel)
        except:
            conf.registerGroup(conf.supybot.plugins.FServe.queues, name)
            group = conf.supybot.plugins.FServe.queues.get(name)
            conf.registerChannelValue(group, 'timeout', registry.Integer(90, ''))
            conf.registerChannelValue(group, 'maxSpeed', registry.Integer(0, ''))
            conf.registerChannelValue(group, 'minSpeed', registry.Integer(0, ''))
            conf.registerChannelValue(group, 'maxQueues', registry.Integer(5, ''))
            conf.registerChannelValue(group, 'instantSendSize',
                                      registry.Integer(50000, ''))
            conf.registerChannelValue(group, 'maxSends', registry.Integer(2, ''))
            conf.registerChannelValue(group, 'receiveDir',
                                      registry.String('incoming', ''))
            conf.registerChannelValue(group, 'sendDir',
                                      registry.String('files', ''))
            conf.registerChannelValue(group, 'allowedModes',
                                      registry.SpaceSeparatedListOfStrings([], ''))
            conf.registerChannelValue(group, 'allowedMasks',
                                      registry.SpaceSeparatedListOfStrings([], ''))
            conf.registerChannelValue(group, 'allowedNicks',
                                      registry.SpaceSeparatedListOfStrings([], ''))
            conf.registerChannelValue(group, 'bannedMasks',
                                      registry.SpaceSeparatedListOfStrings([], ''))
            conf.registerChannelValue(group, 'bannedNicks',
                                      registry.SpaceSeparatedListOfStrings([], ''))
            conf.registerChannelValue(group, 'chatHandler',
                                      registry.String('ChatHandler', ''))
            conf.registerChannelValue(group, 'sendHandler',
                                      registry.String('SendHandler', ''))
            

        self.timeout = plug.registryValue("queues.%s.timeout" % name, channel)
        self.maxSpeed = plug.registryValue("queues.%s.maxSpeed" % name,
                                             channel)
        self.minSpeed = plug.registryValue("queues.%s.minSpeed" % name,
                                             channel)
        self.maxQueues = plug.registryValue("queues.%s.maxQueues" % name,
                                              channel)
        self.instantSendSize = plug.registryValue("queues.%s.instantSendSize"
                                                    % name, channel)
        self.maxSends = plug.registryValue("queues.%s.maxSends" % name,
                                             channel)
        self.receiveDir = plug.registryValue("queues.%s.receiveDir" % name,
                                               channel)
        self.sendDir = plug.registryValue("queues.%s.sendDir" % name, channel)
        self.allowedModes = plug.registryValue("queues.%s.allowedModes"
                                                 % name, channel)
        self.allowedMasks = plug.registryValue("queues.%s.allowedMasks"
                                                 % name, channel)
        self.allowedNicks = plug.registryValue("queues.%s.allowedNicks"
                                                 % name, channel)
        self.bannedNicks = plug.registryValue("queues.%s.bannedNicks" % name,
                                                channel)
        self.bannedMasks = plug.registryValue("queues.%s.bannedMasks" % name,
                                                channel)
        self.chatHandler = plug.registryValue("queues.%s.chatHandler" % name,
                                                channel)
        self.sendHandler = plug.registryValue("queues.%s.sendHandler" % name,
                                                channel)

        # End of Configurables
        self.sends = []
        self.queuedFiles = []
        self.filesSent = 0
        self.bytesSent = 0
        self.leeches = {}

    def spawnChat(self, irc, nick):
        # first check permitted in queue
        hostmask = irc.state.nickToHostmask(nick)
        if (hostmask in self.bannedMasks or
            (self.allowedMasks and not hostmask in self.allowedMasks)):
            irc.reply("You are not allowed to use this queue.");
            return
        if (nick in self.bannedNicks or
            (self.allowedNicks and not nick in self.allowedNicks)):
            irc.reply("You are not allowed to use this queue.");
            return
        if (self.allowedModes):
            ops = irc.state.channels[self.channel].ops
            hops = irc.state.channels[self.channel].halfops
            voices = irc.state.channels[self.channel].voices
            users = irc.state.channels[self.channel].users
            okay = 0
            if (nick in ops and 'op' in self.allowedModes):
                okay = 1
            elif (nick in hops and 'halfop' in self.allowedModes):
                okay = 1
            elif (nick in voices and 'voice' in self.allowedModes):
                okay = 1
            elif (nick in users and 'user' in self.allowedModes):
                okay = 1
            if (not okay):
                irc.reply("You are not allowed to use this queue.");
                return

        # We're okay to talk to. Spawn DCC Chat
        parent = self.plugin._getHandlerClass(self.chatHandler)
        new = parent(irc, nick, hostmask, queue=self)
        new.start()

    def spawnSend(self, irc, nick, hostmask, file):
        parent = self.plugin._getHandlerClass(self.sendHandler)
        cxn = parent(irc, nick, hostmask, file)
        cxn.caller = self
        self.sends.append([nick, hostmask, file, irc, cxn])
        cxn.start()
    
    def getConnectionByPort(self, port):
        for s in self.sends:
            if (s[-1].port == port):
                return s[-1]
        return None

    def addFile(self, irc, nick, mask, file, posn=-1):
        for q in self.queuedFiles:
            if (q[0] == nick):
                if (q[1] == file):
                    raise(QueueException(
                        'You have already queued that file'))
                nqs += 1
                if (nqs >= self.maxQueues):
                    raise(QueueException(
                        'You have already queued the maximum number of files'))
                    
        if (posn < 0 or posn > len(self.queuedFiles)):
            # add to the end
            self.queuedFiles.append([nick, mask, file, irc, time.time()])
            return len(self.queuedFiles)
        else:
            self.queuedFiles = self.queuedFiles[:posn] + \
              [[nick, mask, file, irc, time.time()]] + self.queuedFiles[posn:]
            return posn

    def sendFinished(self, handler):
        # One send finished, so delete and check to see if we should start another
        for s in range(len(self.sends)):
            if (self.sends[s][-1] == handler):
                del self.sends[s]
                break
        self.maybeSend()
                
    def maybeSend(self):
        # maybe send another queued file
        if (self.queuedFiles and len(self.sends) < self.maxSends):
            # find a send to someone we're not sending to already
            sendingTo = []
            for s in self.sends:
                sendingTo.append(s[0])
            for q in range(len(self.queuedFiles)):
                if (not self.queuedFiles[q][0] in sendingTo):
                    #found a file to send
                    qo = self.queuedFiles[q]
                    del self.queuedFiles[q]
                    self.spawnSend(qo[3], qo[0], qo[1], qo[2])
                    break

    def updateNick(self, old, new, mask):
        for q in range(len(self.queues)):
            if self.queues[q][0] == old and self.queues[q][1] == mask:
                self.queues[q][0] = new

class ResumeReqHandler(dcc.ResumeReqHandler):
    plugin = None

    def _getSendHandler(self):
        return self.plugin.getConnectionByPort(self.port)


class AcceptHandler(dcc.DCCReqHandler):
    pass



# --- Plugin ---

class FServe(callbacks.Privmsg):
    queues = {}
    handlers = {'ChatHandler' : ChatHandler,
                'SendHandler' : SendHandler}
    requestHandlers = {'RESUME' : ResumeReqHandler,
                       'ACCEPT' : AcceptHandler,
                       'SEND' : dcc.SendReqHandler}
    
    def _getHandlerClass(self, type):
        return self.handlers.get(type, None)

    def getConnectionByPort(self, port):
        for chan in self.queues:
            for q in self.queues[chan]:
                qo = self.queues[chan][q]
                s = qo.getConnectionByPort(port)
                if s:
                    return s


    def list(self, irc, msg, args):
        """ Show list of queues for this channel """
        channel = privmsgs.getChannel(msg, args)
        qs = self.queues[channel].keys()
        irc.reply('Known queues: %s' % ' '.join(qs))
            

    def chat(self, irc, msg, args):
        """ Start a DCC chat interface (FServe) """
        channel = privmsgs.getChannel(msg, args)
        if (len(args) != 1):
            irc.reply("Unknown queue.")
            return
        name = args[0]
        if (not self.queues.has_key(channel)):
            # Silently ignore as we have no Queues here
            return
        queue = self.queues[channel].get(name, None)
        if (queue):
            queue.spawnChat(irc, msg.nick)

    def add(self, irc, msg, args):
        """ Add a queue """
        channel = privmsgs.getChannel(msg, args)
        name = args[0]
        # First add to per channel config
        current = self.registryValue('queueNames', channel)
        if (name in current):
            irc.reply("That queue already exists on this channel.")
        else:
            current.append(name)
            self.setRegistryValue('queueNames', current, channel)
        try:
            self.registryValue('queues.%s' % name)
        except registry.NonExistentRegistryEntry, e:
            # Register channel name group
            conf.registerGroup(conf.supybot.plugins.FServe.queues, name)

        # And register configs
        group = conf.supybot.plugins.FServe.queues.get(name)
        conf.registerChannelValue(group, 'timeout', registry.Integer(90, ''))
        conf.registerChannelValue(group, 'maxSpeed', registry.Integer(0, ''))
        conf.registerChannelValue(group, 'minSpeed', registry.Integer(0, ''))
        conf.registerChannelValue(group, 'maxQueues', registry.Integer(5, ''))
        conf.registerChannelValue(group, 'instantSendSize',
                                  registry.Integer(50000, ''))
        conf.registerChannelValue(group, 'maxSends', registry.Integer(2, ''))
        conf.registerChannelValue(group, 'receiveDir',
                                  registry.String('incoming', ''))
        conf.registerChannelValue(group, 'sendDir',
                                  registry.String('files', ''))
        conf.registerChannelValue(group, 'allowedModes',
                                  registry.SpaceSeparatedListOfStrings([], ''))
        conf.registerChannelValue(group, 'allowedMasks',
                                  registry.SpaceSeparatedListOfStrings([], ''))
        conf.registerChannelValue(group, 'allowedNicks',
                                  registry.SpaceSeparatedListOfStrings([], ''))
        conf.registerChannelValue(group, 'bannedMasks',
                                  registry.SpaceSeparatedListOfStrings([], ''))
        conf.registerChannelValue(group, 'bannedNicks',
                                  registry.SpaceSeparatedListOfStrings([], ''))
        conf.registerChannelValue(group, 'chatHandler',
                                  registry.String('ChatHandler', ''))
        conf.registerChannelValue(group, 'sendHandler',
                                  registry.String('SendHandler', ''))

        self.queues[channel][name] = Queue(self, channel, name)
        irc.reply('Created queue named %r' % name)

    add = privmsgs.checkCapability(add, 'owner')

    def remove(self, irc, msg, args):
        """ Remove a queue """
        channel = privmsgs.getChannel(msg, args)
        name = args[0]
        # Remove config only from list of Queues to build
        current = self.registryValue('queueNames', channel)
        if (name in current):
            current.remove(name)
            irc.reply('Removed queue named %r' % name)
        else:
            irc.reply('There is no such queue')

    remove = privmsgs.checkCapability(remove, 'owner')
      
    def doJoin(self, irc, msg):
        """ Maybe build some internal representations of our config """
        channel = msg.args[0]
        if (ircutils.nickEqual(msg.nick, irc.nick)):
            if (not self.queues.has_key(channel)):
                queues = self.registryValue('queueNames', channel)
                self.queues[channel] = {}
                for q in queues:
                    self.queues[channel][q] = Queue(self, channel, q)
                
    def doPrivmsg(self, irc, msg):
        """ Maybe respond to DCC request """
        if (ircutils.isCtcp(msg) and dcc.isDCC(msg)):
            ctcpArgs = msg.args[1][1:-1].split()
            dccType = ctcpArgs[1]
            dccArgs = ctcpArgs[2:]

            parent = self.requestHandlers[dccType]
            handler = parent(irc, msg, dccArgs)
            handler.plugin = self
            handler.start()


    def doNick(self, irc, msg):
        """ Let queues know that nick has changed """
        newNick = msg.args[0]
        oldNick = msg.nick
        hostmask = irc.state.nickToHostmask(msg.nick)
        for chan in self.queues:
            for queue in self.queues[chan]:
                self.queues[chan][queue].updateNick(oldNick, newNick, hostmask)
        
Class = FServe
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
