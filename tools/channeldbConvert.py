#!/usr/bin/env python

###
# Copyright (c) 2004, Jeremiah Fincher
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

__revision__ = "$Id$"

import os
import sys

if len(sys.argv) <= 1:
    sys.stderr.write('Usage: %s <channeldb database file> ...' % sys.argv[0])
    sys.stderr.write(os.linesep)
    sys.exit(-1)

import sqlite

import supybot
import ircutils

if __name__ == '__main__':
    fd = file('ChannelStats.db', 'w')
    for filename in sys.argv[1:]:
        channel = os.path.basename(filename).split('-', 1)[0]
        if not ircutils.isChannel(channel):
            continue
        db = sqlite.connect(filename)
        cursor = db.cursor()
        cursor.execute("""SELECT actions, chars, frowns, joins, kicks, modes,
                                 msgs, parts, quits, smileys, topics, words
                          FROM channel_stats""")
        fd.write('%s:%s' % (channel, ','.join(map(str, cursor.fetchone()))))
        fd.write(os.linesep)
        cursor.execute("""SELECT user_id, kicked, actions, chars, frowns,
                                 joins, kicks, modes, msgs, parts, quits,
                                 smileys, topics, words
                          FROM user_stats ORDER BY user_id""")
        for t in cursor.fetchall():
            L = list(t)
            id = L.pop(0)
            fd.write('%s:%s:%s' % (id, channel, ','.join(map(str, L))))
            fd.write(os.linesep)
    fd.close()
        
    
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

