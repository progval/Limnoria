###
# Copyright (c) 2018, James Lu <james@overdrivenetworks.com>
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
from supybot.test import *

import subprocess
import unittest
import os
import shutil
import compileall

try:
    from shutil import which
except ImportError:  # Python < 3.3
    from distutils.spawn import find_executable as which

TEST_PLUGIN_NAME = "TestPlugin"

class PluginCreateTestCase(SupyTestCase):

    @staticmethod
    def _communicate(proc, text):
        outs, errs = proc.communicate(input=text)

        supybot.log.info("testPluginCreate: supybot-plugin-create outs:")
        for line in outs.splitlines():
            supybot.log.info("    %s", line.decode())
        supybot.log.info("testPluginCreate: supybot-plugin-create errs:")
        for line in errs.splitlines():
            supybot.log.info("    %s", line.decode())

    def _makeplugin(self):
        proc = subprocess.Popen(['supybot-plugin-create'], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # In order: plugin name, threaded?, author, use Supybot license?, description
        cmdinput = TEST_PLUGIN_NAME.encode() + b"""
n
Test Case Runner
y
Dummy test plugin
"""
        self._communicate(proc, cmdinput)

    def testPluginCreate(self):
        if not which('supybot-plugin-create'):
            # When tests are run automatically as part of a build process (e.g. in Debian),
            # don't assume that the bot is installed yet.
            print('Skipping supybot-plugin-create test because Limnoria has not been installed yet')
            return

        tmpdir = conf.supybot.directories.data.tmp()
        curdir = os.getcwd()
        try:
            os.chdir(tmpdir)
            if TEST_PLUGIN_NAME in os.listdir('.'):
                supybot.log.info("testPluginCreate: Removing old TestPlugin directory")
                shutil.rmtree(TEST_PLUGIN_NAME)

            self._makeplugin()

            self.assertIn(TEST_PLUGIN_NAME, os.listdir('.'))

            # Make sure that out generated plugin is valid
            compileall.compile_dir(TEST_PLUGIN_NAME)

        finally:
            os.chdir(curdir)

class PluginCreateNoninteractiveTestCase(PluginCreateTestCase):
    def _makeplugin(self):
        with open(os.devnull, 'w') as devnull:  # Compat with Python < 3.3
            retcode = subprocess.call(['supybot-plugin-create', '-n', TEST_PLUGIN_NAME,
                                       '--author=skynet', '--desc=Some description'],
                                      stdin=devnull)
            self.assertFalse(retcode)  # Check that the return code is 0

class PluginCreatePartialArgsTestCase(PluginCreateTestCase):
    def _makeplugin(self):
        # We passed in a subset of args, so the script should only prompt for the
        # ones not given
        proc = subprocess.Popen(['supybot-plugin-create', '-n', TEST_PLUGIN_NAME],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        # In order: threaded?, author, use Supybot license?, description
        cmdinput = TEST_PLUGIN_NAME.encode() + b"""
Test Case Runner
y
Dummy test plugin
"""
        self._communicate(proc, cmdinput)
