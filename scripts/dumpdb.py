#!/usr/bin/env python

import sys
import anydbm

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage: %s <dbfile> <dumpfile>' % sys.argv[0]
        sys.exit(-1)
    db = anydbm.open(sys.argv[1], 'r')
    fd = open(sys.argv[2], 'w')
    key = db.firstkey()
    while key != None:
        fd.write('%s => %s\n' % (key, db[key]))
        key = db.nextkey(key)
    db.close()
    fd.close()
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
