#!/usr/bin/env python

import os
import sys
import shutil

if len(sys.argv) < 3:
    sys.stderr.write('Usage: %s <users file> <channels file>\n')
    sys.exit(-1)
    
(userFile, channelFile) = sys.argv[1:]

import supybot

import conf
conf.supybot.directories.conf.setValue('.')
conf.supybot.databases.users.filename.setValue(userFile)
conf.supybot.databases.channels.filename.setValue(channelFile)

import log
conf.supybot.log.stdout.setValue(False)

import ircdb

def write(fd, s):
    fd.write(s)
    fd.write(os.linesep)
    
if __name__ == '__main__':
    shutil.copy(userFile, userFile + '.bak')
    shutil.copy(channelFile, channelFile + '.bak')
    # Users.conf.
    fd = file(userFile, 'w')
    for (i, u) in enumerate(ircdb.users.users):
        if u is None:
            continue
        write(fd, 'user %s' % i)
        write(fd, '  name %s' % u.name)
        write(fd, '  ignore %s' % u.ignore)
        write(fd, '  secure %s' % u.secure)
        write(fd, '  hashed %s' % u.hashed)
        write(fd, '  password %s' % u.password)
        for capability in u.capabilities:
            try:
                (channel, capability) = rsplit(capability, '.', 1)
                capability = ','.join(channel, capability)
            except ValueError:
                pass
            write(fd, '  capability %s' % capability)
        for hostmask in u.hostmasks:
            write(fd, '  hostmask %s' % hostmask)
        write(fd, '')
    fd.close()

    # Channels.conf.
    fd = file(channelFile, 'w')
    for (name, c) in ircdb.channels.iteritems():
        write(fd, 'channel %s' % name)
        write(fd, '  defaultAllow %s' % c.defaultAllow)
        write(fd, '  lobotomized %s' % c.lobotomized)
        for capability in c.capabilities:
            write(fd, '  capability %s' % capability)
        for ban in c.bans:
            write(fd, '  ban %s' % ban)
        for ignore in c.ignores:
            write(fd, '  ignore %s' % ignore)
        write(fd, '')
        
