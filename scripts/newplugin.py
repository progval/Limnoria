#!/usr/bin/env python

import os
import sys

from questions import *

template = '''
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

"""
Add the module docstring here.  This will be used by the setup.py script.
"""

from baseplugin import *

import privmsgs
import callbacks

class %s(%s):
    %s


Class = %s

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
'''.strip() # This removes the newlines that precede and follow the text.

if __name__ == '__main__':
    name = anything('What should the name of the plugin be?')
    if name.endswith('.py'):
        name = name[:-3]
    if expect('Do you want a command-based plugin' \
              ' or a regexp-based plugin?',
              ['command', 'regexp']) == 'command':
        className = 'callbacks.Privmsg'
    else:
        className = 'callbacks.PrivmsgRegexp'
    if yn('Does your plugin need to be threaded?') == 'y':
        threaded = 'threaded = True'
    else:
        threaded = 'pass'

    fd = file(os.path.join('plugins', name + '.py'), 'w')
    fd.write(template % (name, className, threaded, name))
    fd.close()
    print 'Your new plugin template is in plugins/%s.py' % name

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
