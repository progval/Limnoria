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

import os
import imp
import sys

if 'src' not in sys.path:
    sys.path.insert(0, 'src')

from fix import *

import conf

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write('Usage: %s <script filename>\n' % sys.argv[0])
        sys.exit(-1)
    fd = file('src/template.py')
    template = fd.read()
    fd.close()
    try:
        dir = os.path.dirname(sys.argv[1])
        moduleName = sys.argv[1][:-3]
        moduleInfo = imp.find_module(moduleName, [dir])
        script = imp.load_module(moduleName, *moduleInfo)
    except ImportError, e:
        sys.stderr.write('Invalid script file: %s\n' % e)
        sys.exit(-1)
    template.replace('%%nick%%', repr(script.defaultNick))
    template.replace('%%user%%', repr(script.defaultUser))
    template.replace('%%ident%%', repr(script.defaultIdent))
    template.replace('%%server%%', repr(script.defaultServer))
    template.replace('%%password%%', repr(script.defaultPassword))
    template.replace('%%onStart%%', repr(conf.commandsOnStart))
    template.replace('%%afterConnect%%', repr(script.afterConnect))
    template.replace('%%configVariables%%', repr(script.configVariables))
    os.rename(sys.argv[1], sys.argv[1] + '.bak')
    fd = file(sys.argv[1], 'w')
    fd.write(template)
    fd.close()


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

