#!/usr/bin/env python

import os
import os.path

class MutableX:
    def __init__(self):
        self.x = None

def visit(bytesRemoved, dirname, names):
    filenames = [os.path.join(dirname, s) for s in names if s.endswith('.py')]
    for filename in filenames:
        tmpname = filename + '.tmp'
        tmpfd = file(tmpname, 'w')
        fd = file(filename, 'r')
        for line in fd:
            stripped = line.rstrip()
            bytesRemoved.x += len(line) - len(stripped)
            tmpfd.write(stripped)
            tmpfd.write('\n')
        fd.close()
        tmpfd.close()
        os.rename(tmpname, filename)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        dir = '.'
    else:
        dir = sys.argv[1]
    x = MutableX()
    x.x = 0
    os.path.walk(dir, visit, x)
    print '%s bytes removed.' % x.x

