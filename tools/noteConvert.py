#!/usr/bin/env python
import os
import sys
import sqlite

import supybot.dbi as dbi
import supybot.plugins.Note as Note

def main():
    if '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) != 2:
        print 'usage: %s <sqlitedb>' % sys.argv[0]
        sys.exit(1)
    sqldb = sys.argv[1]
    if not os.path.exists(sqldb):
        print 'Could not find %s' % sqldb
        sys.exit(1)
    TxtDb = Note.NoteDB()
    db = sqlite.connect(sqldb)
    cursor = db.cursor()
    total = 0
    failed = 0
    success = 0
    cursor.execute("""SELECT notified, read, from_id, to_id, public, note  FROM notes ORDER BY id ASC""")
    if cursor.rowcount != 0:
        entries = cursor.fetchall()
        for entry in entries:
            try:
                entry = tuple(entry)
                total += 1
                notified = bool(entry[0])
                read = bool(entry[1])
                frm = int(entry[2])
                to = int(entry[3])
                public = bool(entry[4])
                text = entry[5]
                id = TxtDb.send(frm, to, public, text)
                if notified:
                    TxtDb.setNotified(id)
                if read:
                    TxtDb.setRead(id)
                success += 1
            except dbi.Error:
                failed += 1
    print '%s/%s entries successfully added.  %s failed.' % (success, total, failed)
    db.close()
    TxtDb.close()
    sys.exit(0)

if __name__ == '__main__':
    main()
