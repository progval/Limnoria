#!/usr/bin/env python
import os
import sys
import sqlite

import supybot.dbi as dbi
import supybot.plugins.Lart as Lart
import supybot.plugins.Praise as Praise

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
    if len(sys.argv) >= 4:
        botname = sys.argv[3]
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
                    plugin.add(channel, table, text, by)
                    success += 1
                except dbi.Error:
                    failed += 1
    print '%s/%s entries successfully added.  %s failed.' % (success, total,
                                                             failed)
    print 'Dbs are at: %s' % ', '.join((praises.filename, larts.filename))
    db.close()
    praises.close()
    larts.close()
    sys.exit(0)

if __name__ == '__main__':
    main()
