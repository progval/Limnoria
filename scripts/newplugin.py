#!/usr/bin/env python

import os
import sys

if 'src' not in sys.path:
    sys.path.insert(0, 'src')

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

import utils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load %s')

example = utils.wrapLines("""
Add an example IRC session using this module here.
""")

class %s(%s):
    %s


Class = %s

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
'''.strip() # This removes the newlines that precede and follow the text.

if __name__ == '__main__':
    name = anything('What should the name of the plugin be?')
    if name.endswith('.py'):
        name = name[:-3]
    print 'Supybot offers two major types of plugins: command-based and '
    print 'regexp-based.  Command-based plugins are the kind of plugins '
    print 'you\'ve seen most when you\'ve used supybot.  They\'re also the '
    print 'most featureful and easiest to write.  Commands can be nested, '
    print 'for instance, whereas regexp-based callbacks can\'t do nesting.'
    print
    print 'That doesn\'t mean that you\'ll never want regexp-based callbacks.'
    print 'They offer a flexibility that command-based callbacks don\'t offer;'
    print 'however, they don\'t tie into the whole system as well.'
    print
    print 'If you need to combine a command-based callback with some'
    print 'regexp-based methods, you can do so by subclassing '
    print 'callbacks.PrivmsgCommandAndRegexp and then adding a class-level '
    print 'attribute "regexps" that is a sets.Set of methods that are '
    print 'regexp-based.  But you\'ll have to do that yourself after this '
    print 'wizard is finished :)'
    print
    if expect('Do you want a command-based plugin' \
              ' or a regexp-based plugin?',
              ['command', 'regexp']) == 'command':
        className = 'callbacks.Privmsg'
    else:
        className = 'callbacks.PrivmsgRegexp'
    print 'Sometimes you\'t want a callback to be threaded.  If its methods'
    print '(command or regexp-based, either one) will take a signficant amount'
    print 'of time to run, you\'ll want to thread them so they don\'t block'
    print 'the entire bot.'
    print
    if yn('Does your plugin need to be threaded?') == 'y':
        threaded = 'threaded = True'
    else:
        threaded = 'pass'

    fd = file(os.path.join('plugins', name + '.py'), 'w')
    fd.write(template % (name, name, className, threaded, name))
    fd.close()
    print 'Your new plugin template is in plugins/%s.py' % name

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
