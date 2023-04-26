###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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

from supybot.test import *

class TopicTestCase(ChannelPluginTestCase):
    plugins = ('Topic','User',)
    def testRemove(self):
        self.assertError('topic remove 1')
        _ = self.getMsg('topic add foo')
        _ = self.getMsg('topic add bar')
        _ = self.getMsg('topic add baz')
        self.assertError('topic remove 0')
        self.assertNotError('topic remove 3')
        self.assertNotError('topic remove 2')
        self.assertNotError('topic remove 1')
        self.assertError('topic remove 1')

    def testRemoveMultiple(self):
        self.assertError('topic remove 1 2')
        _ = self.getMsg('topic add foo')
        _ = self.getMsg('topic add bar')
        _ = self.getMsg('topic add baz')
        _ = self.getMsg('topic add derp')
        _ = self.getMsg('topic add cheese')
        self.assertNotError('topic remove 1 2')
        self.assertNotError('topic remove -1 1')
        self.assertError('topic remove -99 1')

    def testReplace(self):
        _ = self.getMsg('topic add foo')
        _ = self.getMsg('topic add bar')
        _ = self.getMsg('topic add baz')
        self.assertRegexp('topic replace 1 oof', 'oof.*bar.*baz')
        self.assertRegexp('topic replace -1 zab', 'oof.*bar.*zab')
        self.assertRegexp('topic replace 2 lorem ipsum',
                          'oof.*lorem ipsum.*zab')
        self.assertRegexp('topic replace 2 rab', 'oof.*rab.*zab')

    def testGet(self):
        self.assertError('topic get 1')
        _ = self.getMsg('topic add foo')
        _ = self.getMsg('topic add bar')
        _ = self.getMsg('topic add baz')
        self.assertRegexp('topic get 1', '^foo')
        self.assertError('topic get 0')

    def testAdd(self):
        self.assertError('topic add #floorgle')
        m = self.getMsg('topic add foo')
        self.assertEqual(m.command, 'TOPIC')
        self.assertEqual(m.args[0], self.channel)
        self.assertEqual(m.args[1], 'foo')
        m = self.getMsg('topic add bar')
        self.assertEqual(m.command, 'TOPIC')
        self.assertEqual(m.args[0], self.channel)
        self.assertEqual(m.args[1], 'foo | bar')

    def testManageCapabilities(self):
        try:
            self.irc.feedMsg(ircmsgs.mode(self.channel, args=('+o', self.nick),
                                      prefix=self.prefix))
            self.irc.feedMsg(ircmsgs.mode(self.channel, args=('+t'),
                                      prefix=self.prefix))
            world.testing = False
            origuser = self.prefix
            self.prefix = 'stuff!stuff@stuff'
            self.assertNotError('register nottester stuff', private=True)

            self.assertError('topic add foo')
            origconf = conf.supybot.plugins.Topic.requireManageCapability()
            conf.supybot.plugins.Topic.requireManageCapability.setValue('')
            self.assertNotError('topic add foo')
        finally:
            world.testing = True
            self.prefix = origuser
            conf.supybot.plugins.Topic.requireManageCapability.setValue(origconf)

    def testInsert(self):
        m = self.getMsg('topic add foo')
        self.assertEqual(m.args[1], 'foo')
        m = self.getMsg('topic insert bar')
        self.assertEqual(m.args[1], 'bar | foo')

    def testChange(self):
        _ = self.getMsg('topic add foo')
        _ = self.getMsg('topic add bar')
        _ = self.getMsg('topic add baz')
        self.assertRegexp('topic change -1 s/baz/biff/',
                          r'foo.*bar.*biff')
        self.assertRegexp('topic change 2 s/bar/baz/',
                          r'foo.*baz.*biff')
        self.assertRegexp('topic change 1 s/foo/bar/',
                          r'bar.*baz.*biff')
        self.assertRegexp('topic change -2 s/baz/bazz/',
                          r'bar.*bazz.*biff')
        self.assertError('topic change 0 s/baz/biff/')

    def testConfig(self):
        try:
            original = conf.supybot.plugins.Topic.separator()
            conf.supybot.plugins.Topic.separator.setValue(' <==> ')
            _ = self.getMsg('topic add foo')
            m = self.getMsg('topic add bar')
            self.assertIn('<==>', m.args[1])
        finally:
            conf.supybot.plugins.Topic.separator.setValue(original)

    def testReorder(self):
        _ = self.getMsg('topic add foo')
        _ = self.getMsg('topic add bar')
        _ = self.getMsg('topic add baz')
        self.assertRegexp('topic reorder 2 1 3', r'bar.*foo.*baz')
        self.assertRegexp('topic reorder 3 -2 1', r'baz.*foo.*bar')
        self.assertError('topic reorder 0 1 2')
        self.assertError('topic reorder 1 -2 2')
        self.assertError('topic reorder 1 2')
        self.assertError('topic reorder 2 3 4')
        self.assertError('topic reorder 1 2 2')
        self.assertError('topic reorder 1 1 2 3')
        _ = self.getMsg('topic remove 1')
        _ = self.getMsg('topic remove 1')
        self.assertError('topic reorder 1')
        _ = self.getMsg('topic remove 1')
        self.assertError('topic reorder 0')

    def testList(self):
        _ = self.getMsg('topic add foo')
        self.assertRegexp('topic list', '1: foo')
        _ = self.getMsg('topic add bar')
        self.assertRegexp('topic list', '1: foo.*2: bar')
        _ = self.getMsg('topic add baz')
        self.assertRegexp('topic list', '1: foo.* 2: bar.* and 3: baz')

    def testSet(self):
        _ = self.getMsg('topic add foo')
        self.assertRegexp('topic set -1 bar', 'bar')
        self.assertNotRegexp('topic set -1 baz', 'bar')
        self.assertResponse('topic set foo bar baz', 'foo bar baz')
        # Catch a bug we had where setting topic 1 would reset the whole topic
        orig = conf.supybot.plugins.Topic.format()
        sep = conf.supybot.plugins.Topic.separator()
        try:
            conf.supybot.plugins.Topic.format.setValue('$topic')
            self.assertResponse('topic add baz', 'foo bar baz%sbaz' % sep)
            self.assertResponse('topic set 1 bar', 'bar%sbaz' % sep)
        finally:
            conf.supybot.plugins.Topic.format.setValue(orig)

    def testRestore(self):
        self.getMsg('topic set foo')
        self.assertResponse('topic restore', 'foo')
        self.getMsg('topic remove 1')
        restoreError = 'Error: I haven\'t yet set the topic in #test.'
        self.assertResponse('topic restore', restoreError)

    def testRefresh(self):
        self.getMsg('topic set foo')
        self.assertResponse('topic refresh', 'foo')
        self.getMsg('topic remove 1')
        refreshError = 'Error: I haven\'t yet set the topic in #test.'
        self.assertResponse('topic refresh', refreshError)

    def testUndo(self):
        try:
            original = conf.supybot.plugins.Topic.format()
            conf.supybot.plugins.Topic.format.setValue('$topic')
            self.assertResponse('topic set ""', '')
            self.assertResponse('topic add foo', 'foo')
            self.assertResponse('topic add bar', 'foo | bar')
            self.assertResponse('topic add baz', 'foo | bar | baz')
            self.assertResponse('topic undo', 'foo | bar')
            self.assertResponse('topic undo', 'foo')
            self.assertResponse('topic undo', '')
        finally:
            conf.supybot.plugins.Topic.format.setValue(original)

    def testUndoRedo(self):
        try:
            original = conf.supybot.plugins.Topic.format()
            conf.supybot.plugins.Topic.format.setValue('$topic')
            self.assertResponse('topic set ""', '')
            self.assertResponse('topic add foo', 'foo')
            self.assertResponse('topic add bar', 'foo | bar')
            self.assertResponse('topic add baz', 'foo | bar | baz')
            self.assertResponse('topic undo', 'foo | bar')
            self.assertResponse('topic undo', 'foo')
            self.assertResponse('topic undo', '')
            self.assertResponse('topic redo', 'foo')
            self.assertResponse('topic redo', 'foo | bar')
            self.assertResponse('topic redo', 'foo | bar | baz')
            self.assertResponse('topic undo', 'foo | bar')
            self.assertResponse('topic undo', 'foo')
            self.assertResponse('topic redo', 'foo | bar')
            self.assertResponse('topic undo', 'foo')
            self.assertResponse('topic redo', 'foo | bar')
        finally:
            conf.supybot.plugins.Topic.format.setValue(original)

    def testSwap(self):
        original = conf.supybot.plugins.Topic.format()
        try:
            conf.supybot.plugins.Topic.format.setValue('$topic')
            self.assertResponse('topic set ""', '')
            self.assertResponse('topic add foo', 'foo')
            self.assertResponse('topic add bar', 'foo | bar')
            self.assertResponse('topic add baz', 'foo | bar | baz')
            self.assertResponse('topic swap 1 2', 'bar | foo | baz')
            self.assertResponse('topic swap 1 -1', 'baz | foo | bar')
            self.assertError('topic swap -1 -1')
            self.assertError('topic swap 2 -2')
            self.assertError('topic swap 1 -3')
            self.assertError('topic swap -2 2')
            self.assertError('topic swap -3 1')
        finally:
            conf.supybot.plugins.Topic.format.setValue(original)

    def testDefault(self):
        self.assertError('topic default')
        try:
            original = conf.supybot.plugins.Topic.default()
            conf.supybot.plugins.Topic.default.setValue('foo bar baz')
            self.assertResponse('topic default', 'foo bar baz')
        finally:
            conf.supybot.plugins.Topic.default.setValue(original)


    def testTopic(self):
        original = conf.supybot.plugins.Topic.format()
        try:
            conf.supybot.plugins.Topic.format.setValue('$topic')
            self.assertError('topic addd') # Error to send too many args.
            self.assertResponse('topic add foo', 'foo')
            self.assertResponse('topic add bar', 'foo | bar')
            self.assertResponse('topic', 'foo | bar')
        finally:
            conf.supybot.plugins.Topic.format.setValue(original)

    def testSeparator(self):
        original = conf.supybot.plugins.Topic.format()
        try:
            conf.supybot.plugins.Topic.format.setValue('$topic')
            self.assertResponse('topic add foo', 'foo')
            self.assertResponse('topic add bar', 'foo | bar')
            self.assertResponse('topic add baz', 'foo | bar | baz')
            self.assertResponse('topic separator ::', 'foo :: bar :: baz')
            self.assertResponse('topic separator ||', 'foo || bar || baz')
            self.assertResponse('topic separator |', 'foo | bar | baz')

        finally:
            conf.supybot.plugins.Topic.format.setValue(original)

    def testFit(self):
        original = conf.supybot.plugins.Topic.format()
        try:
            conf.supybot.plugins.Topic.format.setValue('$topic')
            self.irc.state.supported['TOPICLEN'] = 20
            self.assertResponse('topic fit foo', 'foo')
            self.assertResponse('topic fit bar', 'foo | bar')
            self.assertResponse('topic fit baz', 'foo | bar | baz')
            self.assertResponse('topic fit qux', 'bar | baz | qux')
        finally:
            conf.supybot.plugins.Topic.format.setValue(original)
            self.irc.state.supported.pop('TOPICLEN', None)


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

