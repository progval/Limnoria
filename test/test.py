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

import supybot

import conf
conf.dataDir = 'test-data'
conf.confDir = 'test-conf'
conf.logDir = 'test-log'
conf.replyWhenNotCommand = False
conf.stdoutLogging = False
conf.detailedTracebacks = False # Bugs in cgitb can be bad.

import fix

import re
import glob
import os.path
import unittest

import world

class path(str):
    """A class to represent platform-independent paths."""
    _r = re.compile(r'[\\/]')
    def __hash__(self):
        return reduce(lambda h, s: h ^ hash(s), self._r.split(self), 0)
    def __eq__(self, other):
        return self._r.split(self) == self._r.split(other)

if __name__ == '__main__':
    import optparse

    if not os.path.exists(conf.dataDir):
        os.mkdir(conf.dataDir)

    if not os.path.exists(conf.confDir):
        os.mkdir(conf.confDir)

    if not os.path.exists(conf.logDir):
        os.mkdir(conf.logDir)

##     for filename in os.listdir(conf.logDir):
##         if filename == 'plugins':
##             continue
##         filename = os.path.join(conf.logDir, filename)
##         os.remove(filename)
    pluginLogDir = os.path.join(conf.logDir, 'plugins')
    for filename in os.listdir(pluginLogDir):
        os.remove(os.path.join(pluginLogDir, filename))

    parser = optparse.OptionParser(usage='Usage: %prog [options]',
                                   version='Supybot %s' % conf.version)
    parser.add_option('-e', '--exclude', action='append',
                      dest='exclusions', metavar='TESTFILE',
                      help='Exclude this test from the test run.')
    parser.add_option('-t', '--timeout', action='store', type='int',
                      dest='timeout',
                      help='Sets the timeout for tests to return responses.')
    parser.add_option('-p', '--plugindir', action='append',
                      metavar='plugindir', dest='plugindirs',
                      help='Adds a directory to the list of directories in '
                           'which to search for plugins.')
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      help='Sets the verbose flag, printing extra information '
                           'about each test that runs.')
    (options, args) = parser.parse_args()
    if not args:
        args = map(path, glob.glob(os.path.join('test', 'test_*.py')))

    if options.exclusions:
        for name in map(path, options.exclusions):
            args = [s for s in args if s != name]

    if options.timeout:
        PluginTestCase.timeout = options.timeout

    if options.plugindirs:
        options.plugindirs.reverse()
        conf.pluginDirs.extend(options.plugindirs)
        conf.pluginDirs.reverse()

    if options.verbose:
        world.myVerbose = True
    else:
        world.myVerbose = False

    world.testing = True
    names = [os.path.splitext(os.path.basename(name))[0] for name in args]
    names.sort()
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
    print 'Total asserts: %s' % unittest.asserts

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
