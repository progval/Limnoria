#!/usr/bin/env python

"""
This script exists mostly to pull out literal strings in a program in order to
spell-check them.
"""

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
                
goodChars = string.letters + string.whitespace
prefixes = ('r"', "r'", '$Id')
def main():
    for filename in sys.argv[1:]:
        s = getText(filename)
        node = parser.ast2list(parser.suite(s), True)
        for (lineno, s) in strings(node):
            if s.translate(string.ascii, string.printable):
                continue
            for prefix in prefixes:
                if s.startswith(prefix):
                    continue
            s = eval(s)
            s = s.replace('%s', ' ')
            s = s.replace('%r', ' ')
            if len(s.translate(string.ascii, goodChars))/len(s) < 0.2:
                continue
            if len(s) <= 3:
                continue
            print '%s: %s: %s' % (filename, lineno, s)

if __name__ == '__main__':
    main()
