#!/usr/bin/env python

import os
import sys
import symbol
import parser

import supybot.utils as utils

def strings(node):
    if node[0] == 3:
        yield (node[2], node[1])
    for x in node:
        if isinstance(x, list):
            for t in strings(x):
                yield t

def getText(filename):
    try:
        fd = file(filename)
        return fd.read()
    finally:
        fd.close()
                
def main():
    os.mkdir('strings')
    for filename in sys.argv[1:]:
        s = getText(filename)
        node = parser.ast2list(parser.suite(s), True)
        fd = file(os.path.join('strings', os.path.basename(filename)), 'w')
        for (lineno, string) in strings(node):
            fd.write('%s: %s\n' % (lineno, string))
        fd.close()

if __name__ == '__main__':
    main()
