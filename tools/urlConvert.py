#!/usr/bin/env python

import sys
import time

import supybot.ircmsgs as ircmsgs
import supybot.plugins.URL as URL


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'usage: %s URL.db' % sys.argv[0]
        sys.exit()
    try:
        olddb = file(sys.argv[1])
    except IOError, e:
        print str(e)
        sys.exit()
    db = URL.URLDB()
    for line in olddb:
        (url, person) = line.split()
        m = ircmsgs.IrcMsg(command='PRIVMSG', args=('#foo', '%s' % url), prefix=person)
        m.tag('receivedAt', time.time())
        db.add(None, url, m)
    db.close()
    olddb.close()
