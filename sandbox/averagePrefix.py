#!/usr/bin/env python

import sys

import ircmsgs
import ircutils

sys.path.append('..')

if __name__ == '__main__':
    total = 0
    lines = 0
    for line in sys.stdin:
        msg = ircmsgs.IrcMsg(line)
        if ircutils.isUserHostmask(msg.prefix):
            total += len(msg.prefix)
            lines += 1
    print total / lines
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
