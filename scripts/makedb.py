#!/usr/bin/env python

import re
import sys
import anydbm

r = r'(.*?)\s+=>\s+(.*?)\n$'

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'Usage: %s <dumpname> <dbname>' % sys.argv[0]
        sys.exit(-1)
    fd = open(sys.argv[1], 'r')
    db = anydbm.open(sys.argv[2], 'c')
    for line in fd:
        m = re.match(r, line)
        if m:
            (key, value) = m.groups()[-2:]
            db[key] = value
        else:
            print 'Invalid line: %s' % line.strip()
    db.close()
    fd.close()
