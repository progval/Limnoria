#!/usr/bin/env python

"""
Converts from a "key => value\n" format to a cdb database.
"""

import sys
sys.path.insert(0, 'src')
import re

import cdb

r = re.compile(r'(.*)\s+=>\s+(.*)\n')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Usage: %s <dbname> (reads stdin for data)' % sys.argv[0]
        sys.exit(-1)
    maker = cdb.Maker(sys.argv[1])
    lineno = 1
    for line in sys.stdin:
        m = r.match(line)
        if m:
            (key, value) = m.groups()
            maker.add(key, value)
            lineno += 1
        else:
            print 'Invalid Syntax, line %s' % lineno
    maker.finish()

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
