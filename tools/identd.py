#!/usr/local/bin/python -u

import asyncore
import asynchat
import socket
from random import randrange
import os

class identd_server(asyncore.dispatcher):
    def __init__(self, limit=10):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.helpers = []
        self.limit = limit
        os.chdir('/')
        self.bind(('', 113))
        os.setgid(25000)
        os.setuid(25000)
        self.listen(5)

    def handle_accept(self):
        self.helpers.append(identd_helper(self.accept()))
        if len(self.helpers) > self.limit:
            i = self.helpers.pop(0)
            i.close()


class identd_helper(asynchat.async_chat):
    def __init__(self, (sock, addr)):
        asynchat.async_chat.__init__(self, sock)
        self.sock = sock
        self.set_terminator('\r\n')
        self.buffer = ''

    def collect_incoming_data(self, data):
        self.buffer = self.buffer + data
        if len(self.buffer) > 512:
            self.close()

    def found_terminator(self):
        self.send('%s : USERID : DOS : user%d\r\n' % (self.buffer, randrange(10000)))
        self.close()

if __name__ == '__main__':
    import sys
    sys.stdin.close()
    sys.stdout.close()
    sys.stderr.close()
    if os.fork() != 0:
        sys.exit(0)
    os.setsid()
    s = identd_server()
    os.chdir('/')
    os.setgid(25000)
    os.setuid(25000)
    os.umask(0)
    if os.fork() != 0:
        sys.exit(0)
    asyncore.loop()
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
