#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import sys
import traceback
from cStringIO import StringIO

import debug

filename = 'repl'

NotYet = object()

class Repl(object):
    def __init__(self, filename='repl'):
        self.lines = []
        self.filename = filename
        self.namespace = {}
        self.out = StringIO()

    def compile(self, text):
        ret = None
        try:
            code = compile(text, self.filename, 'eval')
            sys.stdout = self.out
            ret = eval(code, self.namespace, self.namespace)
            sys.stdout = sys.__stdout__
            self.out.reset()
            if self.out.read():
                ret = self.out.read() + ret
            self.out.reset()
            self.out.truncate()
            self.namespace['_'] = ret
        except:
            try:
                code = compile(text, self.filename, 'exec')
                sys.stdout = self.out
                exec code in self.namespace, self.namespace
                sys.stdout = sys.__stdout__
                self.out.reset()
                if self.out.read():
                    ret = self.out.read() + ret
                self.out.reset()
                self.out.truncate()
            except:
                (E, e, tb) = sys.exc_info()
                ret = ''.join(traceback.format_exception(E, e, tb))
                del tb
        return ret

    def addLine(self, line):
        line = line.rstrip()
        self.lines.append(line)
        if len(self.lines) > 100:
            debug.debugMsg('too many lines in Repl.')
            self.lines = []
            return None
        if line == '' or line == '\n' or line == '\r\n':
            text = '\n'.join(self.lines)+'\n\n'
            ret = self.compile(text)
            if ret is not NotYet:
                self.lines = []
            return ret
        else:
            try:
                ret = eval(line, self.namespace, self.namespace)
                self.lines = []
                return ret
            except SyntaxError:
                try:
                    exec line in self.namespace, self.namespace
                    self.lines = []
                    return None
                except:
                    pass
            except:
                (E, e, tb) = sys.exc_info()
                return ''.join(traceback.format_exception(E, e, tb))
                del tb
            return NotYet

if __name__ == '__main__':
    def writePrompt(prompt):
        sys.stdout.write(prompt)
        sys.stdout.flush()

    prompt = '>>> '
    repl = Repl()
    while 1:
        writePrompt(prompt)
        s = sys.stdin.readline()
        if s == '':
            sys.exit(0)
        ret = repl.addLine(s)
        if ret is not NotYet:
            if ret is not None:
                s = str(ret)
                sys.stdout.write(s)
                if s[-1] != '\n':
                    sys.stdout.write('\n')
            prompt = '>>> '
        else:
            prompt = '... '
