#!/usr/bin/env python
import os
import sys
import time
import sqlite

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.plugins.Lart as Lart
import supybot.plugins.Praise as Praise

conf.supybot.log.stdout.setValue(False)

def usage():
    print 'usage: %s <sqlitedb> <channel> [<botname>]' % sys.argv[0]
    print '<botname> is an optional parameter used if any db entries are '\
          'missing a "created by" user.'

def main():
    if '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) not in (3, 4):
        usage()
        sys.exit(1)
    sqldb = sys.argv[1]
    channel = sys.argv[2]
    botname = 'an unkown user'
    if len(sys.argv) == 4:
        botname = sys.argv[3]
    if not ircutils.isChannel(channel):
        print '%s is an invalid channel name.' % channel
        sys.exit(1)
    if not os.path.exists(sqldb):
        print 'Unable to open %s' % sqldb
        sys.exit(1)
    praises = Praise.Praise().db
    larts = Lart.Lart().db
    db = sqlite.connect(sqldb)
    cursor = db.cursor()
    total = 0
    failed = 0
    success = 0
    for (table, plugin) in (('larts', larts), ('praises', praises)):
        cursor.execute("""SELECT * FROM %s ORDER BY id ASC""" % table)
        table = table[:-1]
        if cursor.rowcount != 0:
            entries = cursor.fetchall()
            for entry in entries:
                try:
                    total += 1
                    text = entry[1]
                    by = entry[2]
                    if by is None:
                        by = botname
                    plugin.add(channel, time.time(), by, text)
                    success += 1
                except dbi.Error:
                    failed += 1
    print '%s/%s entries successfully added.  %s failed.' % (success, total,
                                                             failed)
    pfile = plugins.makeChannelFilename(praises.filename, channel)
    lfile = plugins.makeChannelFilename(larts.filename, channel)
    print 'Dbs are at: %s' % ', '.join((pfile, lfile))
    db.close()
    praises.close()
    larts.close()
    sys.exit(0)

if __name__ == '__main__':
    main()
