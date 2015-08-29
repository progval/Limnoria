# -*- coding: utf8 -*-
###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.utils.minisix as minisix
import supybot.callbacks as callbacks

tokenize = callbacks.tokenize


class TokenizerTestCase(SupyTestCase):
    def testEmpty(self):
        self.assertEqual(tokenize(''), [])

    def testNullCharacter(self):
        self.assertEqual(tokenize(utils.str.dqrepr('\0')), ['\0'])

    def testSingleDQInDQString(self):
        self.assertEqual(tokenize('"\\""'), ['"'])

    def testDQsWithBackslash(self):
        self.assertEqual(tokenize('"\\\\"'), ["\\"])

    def testDoubleQuotes(self):
        self.assertEqual(tokenize('"\\"foo\\""'), ['"foo"'])

    def testSingleWord(self):
        self.assertEqual(tokenize('foo'), ['foo'])

    def testMultipleSimpleWords(self):
        words = 'one two three four five six seven eight'.split()
        for i in range(len(words)):
            self.assertEqual(tokenize(' '.join(words[:i])), words[:i])

    def testSingleQuotesNotQuotes(self):
        self.assertEqual(tokenize("it's"), ["it's"])

    def testQuotedWords(self):
        self.assertEqual(tokenize('"foo bar"'), ['foo bar'])
        self.assertEqual(tokenize('""'), [''])
        self.assertEqual(tokenize('foo "" bar'), ['foo', '', 'bar'])
        self.assertEqual(tokenize('foo "bar baz" quux'),
                         ['foo', 'bar baz', 'quux'])

    _testUnicode = """
def testUnicode(self):
    self.assertEqual(tokenize(u'好'), [u'好'])
    self.assertEqual(tokenize(u'"好"'), [u'好'])"""
    if minisix.PY3:
        _testUnicode = _testUnicode.replace("u'", "'")
    exec(_testUnicode)

    def testNesting(self):
        self.assertEqual(tokenize('[]'), [[]])
        self.assertEqual(tokenize('[foo]'), [['foo']])
        self.assertEqual(tokenize('[ foo ]'), [['foo']])
        self.assertEqual(tokenize('foo [bar]'), ['foo', ['bar']])
        self.assertEqual(tokenize('foo bar [baz quux]'),
                         ['foo', 'bar', ['baz', 'quux']])
        try:
            orig = conf.supybot.commands.nested()
            conf.supybot.commands.nested.setValue(False)
            self.assertEqual(tokenize('[]'), ['[]'])
            self.assertEqual(tokenize('[foo]'), ['[foo]'])
            self.assertEqual(tokenize('foo [bar]'), ['foo', '[bar]'])
            self.assertEqual(tokenize('foo bar [baz quux]'),
                             ['foo', 'bar', '[baz', 'quux]'])
        finally:
            conf.supybot.commands.nested.setValue(orig)

    def testError(self):
        self.assertRaises(SyntaxError, tokenize, '[foo') #]
        self.assertRaises(SyntaxError, tokenize, '"foo') #"

    def testPipe(self):
        try:
            conf.supybot.commands.nested.pipeSyntax.setValue(True)
            self.assertRaises(SyntaxError, tokenize, '| foo')
            self.assertRaises(SyntaxError, tokenize, 'foo ||bar')
            self.assertRaises(SyntaxError, tokenize, 'bar |')
            self.assertEqual(tokenize('foo|bar'), ['bar', ['foo']])
            self.assertEqual(tokenize('foo | bar'), ['bar', ['foo']])
            self.assertEqual(tokenize('foo | bar | baz'),
                             ['baz', ['bar',['foo']]])
            self.assertEqual(tokenize('foo bar | baz'),
                             ['baz', ['foo', 'bar']])
            self.assertEqual(tokenize('foo | bar baz'),
                             ['bar', 'baz', ['foo']])
            self.assertEqual(tokenize('foo bar | baz quux'),
                             ['baz', 'quux', ['foo', 'bar']])
        finally:
            conf.supybot.commands.nested.pipeSyntax.setValue(False)
            self.assertEqual(tokenize('foo|bar'), ['foo|bar'])
            self.assertEqual(tokenize('foo | bar'), ['foo', '|', 'bar'])
            self.assertEqual(tokenize('foo | bar | baz'),
                             ['foo', '|', 'bar', '|', 'baz'])
            self.assertEqual(tokenize('foo bar | baz'),
                             ['foo', 'bar', '|', 'baz'])

    def testQuoteConfiguration(self):
        f = callbacks.tokenize
        self.assertEqual(f('[foo]'), [['foo']])
        self.assertEqual(f('"[foo]"'), ['[foo]'])
        try:
            original = conf.supybot.commands.quotes()
            conf.supybot.commands.quotes.setValue('`')
            self.assertEqual(f('[foo]'), [['foo']])
            self.assertEqual(f('`[foo]`'), ['[foo]'])
            conf.supybot.commands.quotes.setValue('\'')
            self.assertEqual(f('[foo]'), [['foo']])
            self.assertEqual(f('\'[foo]\''), ['[foo]'])
            conf.supybot.commands.quotes.setValue('`\'')
            self.assertEqual(f('[foo]'), [['foo']])
            self.assertEqual(f('`[foo]`'), ['[foo]'])
            self.assertEqual(f('[foo]'), [['foo']])
            self.assertEqual(f('\'[foo]\''), ['[foo]'])
        finally:
            conf.supybot.commands.quotes.setValue(original)

    def testBold(self):
        s = '\x02foo\x02'
        self.assertEqual(tokenize(s), [s])
        s = s[:-1] + '\x0f'
        self.assertEqual(tokenize(s), [s])

    def testColor(self):
        s = '\x032,3foo\x03'
        self.assertEqual(tokenize(s), [s])
        s = s[:-1] + '\x0f'
        self.assertEqual(tokenize(s), [s])


class FunctionsTestCase(SupyTestCase):
    def testCanonicalName(self):
        self.assertEqual('foo', callbacks.canonicalName('foo'))
        self.assertEqual('foobar', callbacks.canonicalName('foo-bar'))
        self.assertEqual('foobar', callbacks.canonicalName('foo_bar'))
        self.assertEqual('foobar', callbacks.canonicalName('FOO-bar'))
        self.assertEqual('foobar', callbacks.canonicalName('FOOBAR'))
        self.assertEqual('foobar', callbacks.canonicalName('foo___bar'))
        self.assertEqual('foobar', callbacks.canonicalName('_f_o_o-b_a_r'))
        # The following seems to be a hack for the Karma plugin; I'm not
        # entirely sure that it's completely necessary anymore.
        self.assertEqual('foobar--', callbacks.canonicalName('foobar--'))

    def testAddressed(self):
        oldprefixchars = str(conf.supybot.reply.whenAddressedBy.chars)
        nick = 'supybot'
        conf.supybot.reply.whenAddressedBy.chars.set('~!@')
        inChannel = ['~foo', '@foo', '!foo',
                     '%s: foo' % nick, '%s foo' % nick,
                     '%s: foo' % nick.capitalize(), '%s: foo' % nick.upper()]
        inChannel = [ircmsgs.privmsg('#foo', s) for s in inChannel]
        badmsg = ircmsgs.privmsg('#foo', '%s:foo' % nick)
        self.failIf(callbacks.addressed(nick, badmsg))
        badmsg = ircmsgs.privmsg('#foo', '%s^: foo' % nick)
        self.failIf(callbacks.addressed(nick, badmsg))
        for msg in inChannel:
            self.assertEqual('foo', callbacks.addressed(nick, msg), msg)
        msg = ircmsgs.privmsg(nick, 'foo')
        self.assertEqual('foo', callbacks.addressed(nick, msg))
        conf.supybot.reply.whenAddressedBy.chars.set(oldprefixchars)
        msg = ircmsgs.privmsg('#foo', '%s::::: bar' % nick)
        self.assertEqual('bar', callbacks.addressed(nick, msg))
        msg = ircmsgs.privmsg('#foo', '%s: foo' % nick.upper())
        self.assertEqual('foo', callbacks.addressed(nick, msg))
        badmsg = ircmsgs.privmsg('#foo', '%s`: foo' % nick)
        self.failIf(callbacks.addressed(nick, badmsg))

    def testAddressedReplyWhenNotAddressed(self):
        msg1 = ircmsgs.privmsg('#foo', '@bar')
        msg2 = ircmsgs.privmsg('#foo', 'bar')
        self.assertEqual(callbacks.addressed('blah', msg1), 'bar')
        self.assertEqual(callbacks.addressed('blah', msg2), '')
        try:
            original = conf.supybot.reply.whenNotAddressed()
            conf.supybot.reply.whenNotAddressed.setValue(True)
            # need to recreate the msg objects since the old ones have already
            # been tagged
            msg1 = ircmsgs.privmsg('#foo', '@bar')
            msg2 = ircmsgs.privmsg('#foo', 'bar')
            self.assertEqual(callbacks.addressed('blah', msg1), 'bar')
            self.assertEqual(callbacks.addressed('blah', msg2), 'bar')
        finally:
            conf.supybot.reply.whenNotAddressed.setValue(original)

    def testAddressedWithMultipleNicks(self):
        msg = ircmsgs.privmsg('#foo', 'bar: baz')
        self.assertEqual(callbacks.addressed('bar', msg), 'baz')
        # need to recreate the msg objects since the old ones have already
        # been tagged
        msg = ircmsgs.privmsg('#foo', 'bar: baz')
        self.assertEqual(callbacks.addressed('biff', msg, nicks=['bar']),
                         'baz')

    def testAddressedWithNickAtEnd(self):
        msg = ircmsgs.privmsg('#foo', 'baz, bar')
        self.assertEqual(callbacks.addressed('bar', msg,
                                             whenAddressedByNickAtEnd=True),
                         'baz')

    def testAddressedPrefixCharsTakePrecedenceOverNickAtEnd(self):
        msg = ircmsgs.privmsg('#foo', '@echo foo')
        self.assertEqual(callbacks.addressed('foo', msg,
                                             whenAddressedByNickAtEnd=True,
                                             prefixChars='@'),
                         'echo foo')


    def testReply(self):
        prefix = 'foo!bar@baz'
        channelMsg = ircmsgs.privmsg('#foo', 'bar baz', prefix=prefix)
        nonChannelMsg = ircmsgs.privmsg('supybot', 'bar baz', prefix=prefix)
        self.assertEqual(ircmsgs.notice(nonChannelMsg.nick, 'foo'),
                         callbacks.reply(channelMsg, 'foo', private=True))
        self.assertEqual(ircmsgs.notice(nonChannelMsg.nick, 'foo'),
                         callbacks.reply(nonChannelMsg, 'foo'))
        self.assertEqual(ircmsgs.privmsg(channelMsg.args[0],
                                         '%s: foo' % channelMsg.nick),
                         callbacks.reply(channelMsg, 'foo'))
        self.assertEqual(ircmsgs.privmsg(channelMsg.args[0],
                                         'foo'),
                         callbacks.reply(channelMsg, 'foo', prefixNick=False))
        self.assertEqual(ircmsgs.notice(nonChannelMsg.nick, 'foo'),
                         callbacks.reply(channelMsg, 'foo',
                                         notice=True, private=True))

    def testReplyTo(self):
        prefix = 'foo!bar@baz'
        msg = ircmsgs.privmsg('#foo', 'bar baz', prefix=prefix)
        self.assertEqual(callbacks.reply(msg, 'blah', to='blah'),
                         ircmsgs.privmsg('#foo', 'blah: blah'))
        self.assertEqual(callbacks.reply(msg, 'blah', to='blah', private=True),
                         ircmsgs.notice('blah', 'blah'))

    def testTokenize(self):
        self.assertEqual(callbacks.tokenize(''), [])
        self.assertEqual(callbacks.tokenize('foo'), ['foo'])
        self.assertEqual(callbacks.tokenize('foo'), ['foo'])
        self.assertEqual(callbacks.tokenize('bar [baz]'), ['bar', ['baz']])


class AmbiguityTestCase(PluginTestCase):
    plugins = ('Misc',) # Something so it doesn't complain.
    class Foo(callbacks.Plugin):
        def bar(self, irc, msg, args):
            irc.reply('foo.bar')
    class Bar(callbacks.Plugin):
        def bar(self, irc, msg, args):
            irc.reply('bar.bar')

    def testAmbiguityWithCommandSameNameAsPlugin(self):
        self.irc.addCallback(self.Foo(self.irc))
        self.assertResponse('bar', 'foo.bar')
        self.irc.addCallback(self.Bar(self.irc))
        self.assertResponse('bar', 'bar.bar')

class ProperStringificationOfReplyArgs(PluginTestCase):
    plugins = ('Misc',) # Same as above.
    class NonString(callbacks.Plugin):
        def int(self, irc, msg, args):
            irc.reply(1)
    class ExpectsString(callbacks.Plugin):
        def lower(self, irc, msg, args):
            irc.reply(args[0].lower())

    def test(self):
        self.irc.addCallback(self.NonString(self.irc))
        self.irc.addCallback(self.ExpectsString(self.irc))
        self.assertResponse('expectsstring lower [nonstring int]', '1')

## class PrivmsgTestCaseWithKarma(ChannelPluginTestCase):
##     plugins = ('Utilities', 'Misc', 'Web', 'Karma', 'String')
##     conf.allowEval = True
##     timeout = 2
##     def testSecondInvalidCommandRespondsWithThreadedInvalidCommands(self):
##         try:
##             orig = conf.supybot.plugins.Karma.response()
##             conf.supybot.plugins.Karma.response.setValue(True)
##             self.assertNotRegexp('echo [foo++] [foo++]', 'not a valid')
##             _ = self.irc.takeMsg()
##         finally:
##             conf.supybot.plugins.Karma.response.setValue(orig)

    
class PrivmsgTestCase(ChannelPluginTestCase):
    plugins = ('Utilities', 'Misc', 'Web', 'String')
    conf.allowEval = True
    timeout = 2
    def testEmptySquareBrackets(self):
        self.assertError('echo []')

##     def testHelpNoNameError(self):
##         # This will raise a NameError if some dynamic scoping isn't working
##         self.assertNotError('load Http')
##         self.assertHelp('extension')

    def testMaximumNestingDepth(self):
        original = conf.supybot.commands.nested.maximum()
        try:
            conf.supybot.commands.nested.maximum.setValue(3)
            self.assertResponse('echo foo', 'foo')
            self.assertResponse('echo [echo foo]', 'foo')
            self.assertResponse('echo [echo [echo foo]]', 'foo')
            self.assertResponse('echo [echo [echo [echo foo]]]', 'foo')
            self.assertError('echo [echo [echo [echo [echo foo]]]]')
        finally:
            conf.supybot.commands.nested.maximum.setValue(original)

    def testSimpleReply(self):
        self.assertResponse("eval irc.reply('foo')", 'foo')

    def testSimpleReplyAction(self):
        self.assertResponse("eval irc.reply('foo', action=True)",
                            '\x01ACTION foo\x01')

    def testReplyWithNickPrefix(self):
        self.feedMsg('@len foo')
        m = self.irc.takeMsg()
        self.failUnless(m is not None, 'm: %r' % m)
        self.failUnless(m.args[1].startswith(self.nick))
        try:
            original = conf.supybot.reply.withNickPrefix()
            conf.supybot.reply.withNickPrefix.setValue(False)
            self.feedMsg('@len foobar')
            m = self.irc.takeMsg()
            self.failUnless(m is not None)
            self.failIf(m.args[1].startswith(self.nick))
        finally:
            conf.supybot.reply.withNickPrefix.setValue(original)

    def testErrorPrivateKwarg(self):
        try:
            original = conf.supybot.reply.error.inPrivate()
            conf.supybot.reply.error.inPrivate.setValue(False)
            m = self.getMsg("eval irc.error('foo', private=True)")
            self.failUnless(m, 'No message returned.')
            self.failIf(ircutils.isChannel(m.args[0]))
        finally:
            conf.supybot.reply.error.inPrivate.setValue(original)

    def testErrorNoArgumentIsArgumentError(self):
        self.assertHelp('eval irc.error()')

    def testErrorWithNotice(self):
        try:
            original = conf.supybot.reply.error.withNotice()
            conf.supybot.reply.error.withNotice.setValue(True)
            m = self.getMsg("eval irc.error('foo')")
            self.failUnless(m, 'No message returned.')
            self.failUnless(m.command == 'NOTICE')
        finally:
            conf.supybot.reply.error.withNotice.setValue(original)

    def testErrorReplyPrivate(self):
        try:
            original = str(conf.supybot.reply.error.inPrivate)
            conf.supybot.reply.error.inPrivate.set('False')
            # If this doesn't raise an error, we've got a problem, so the next
            # two assertions shouldn't run.  So we first check that what we
            # expect to error actually does so we don't go on a wild goose
            # chase because our command never errored in the first place :)
            s = 're s/foo/bar baz' # will error; should be "re s/foo/bar/ baz"
            self.assertError(s)
            m = self.getMsg(s)
            self.failUnless(ircutils.isChannel(m.args[0]))
            conf.supybot.reply.error.inPrivate.set('True')
            m = self.getMsg(s)
            self.failIf(ircutils.isChannel(m.args[0]))
        finally:
            conf.supybot.reply.error.inPrivate.set(original)

    # Now for stuff not based on the plugins.
    class First(callbacks.Plugin):
        def firstcmd(self, irc, msg, args):
            """First"""
            irc.reply('foo')

    class Second(callbacks.Plugin):
        def secondcmd(self, irc, msg, args):
            """Second"""
            irc.reply('bar')

    class FirstRepeat(callbacks.Plugin):
        def firstcmd(self, irc, msg, args):
            """FirstRepeat"""
            irc.reply('baz')

    class Third(callbacks.Plugin):
        def third(self, irc, msg, args):
            """Third"""
            irc.reply(' '.join(args))

    def tearDown(self):
        if hasattr(self.First, 'first'):
            del self.First.first
        if hasattr(self.Second, 'second'):
            del self.Second.second
        if hasattr(self.FirstRepeat, 'firstrepeat'):
            del self.FirstRepeat.firstrepeat
        ChannelPluginTestCase.tearDown(self)

    def testDispatching(self):
        self.irc.addCallback(self.First(self.irc))
        self.irc.addCallback(self.Second(self.irc))
        self.assertResponse('firstcmd', 'foo')
        self.assertResponse('secondcmd', 'bar')
        self.assertResponse('first firstcmd', 'foo')
        self.assertResponse('second secondcmd', 'bar')
        self.assertRegexp('first first firstcmd',
                'there is no command named "first" in it')

    def testAmbiguousError(self):
        self.irc.addCallback(self.First(self.irc))
        self.assertNotError('firstcmd')
        self.irc.addCallback(self.FirstRepeat(self.irc))
        self.assertError('firstcmd')
        self.assertError('firstcmd [firstcmd]')
        self.assertNotRegexp('firstcmd', '(foo.*baz|baz.*foo)')
        self.assertResponse('first firstcmd', 'foo')
        self.assertResponse('firstrepeat firstcmd', 'baz')

    def testAmbiguousHelpError(self):
        self.irc.addCallback(self.First(self.irc))
        self.irc.addCallback(self.FirstRepeat(self.irc))
        self.assertError('help first')

    def testHelpDispatching(self):
        self.irc.addCallback(self.First(self.irc))
        self.assertHelp('help firstcmd')
        self.assertHelp('help first firstcmd')
        self.irc.addCallback(self.FirstRepeat(self.irc))
        self.assertError('help firstcmd')
        self.assertRegexp('help first firstcmd', 'First', 0) # no re.I flag.
        self.assertRegexp('help firstrepeat firstcmd', 'FirstRepeat', 0)

    class TwoRepliesFirstAction(callbacks.Plugin):
        def testactionreply(self, irc, msg, args):
            irc.reply('foo', action=True)
            irc.reply('bar') # We're going to check that this isn't an action.

    def testNotActionSecondReply(self):
        self.irc.addCallback(self.TwoRepliesFirstAction(self.irc))
        self.assertAction('testactionreply', 'foo')
        m = self.getMsg(' ')
        self.failIf(m.args[1].startswith('\x01ACTION'))

    def testEmptyNest(self):
        try:
            conf.supybot.reply.whenNotCommand.set('True')
            self.assertError('echo []')
            conf.supybot.reply.whenNotCommand.set('False')
            self.assertResponse('echo []', '[]')
        finally:
            conf.supybot.reply.whenNotCommand.set('False')

    def testDispatcherHelp(self):
        self.assertNotRegexp('help first', r'\(dispatcher')
        self.assertNotRegexp('help first', r'%s')

    def testDefaultCommand(self):
        self.irc.addCallback(self.First(self.irc))
        self.irc.addCallback(self.Third(self.irc))
        self.assertError('first blah')
        self.assertResponse('third foo bar baz', 'foo bar baz')

    def testSyntaxErrorNotEscaping(self):
        self.assertError('load [foo')
        self.assertError('load foo]')

    def testNoEscapingAttributeErrorFromTokenizeWithFirstElementList(self):
        self.assertError('[plugin list] list')

    class InvalidCommand(callbacks.Plugin):
        def invalidCommand(self, irc, msg, tokens):
            irc.reply('foo')

    def testInvalidCommandOneReplyOnly(self):
        try:
            original = str(conf.supybot.reply.whenNotCommand)
            conf.supybot.reply.whenNotCommand.set('True')
            self.assertRegexp('asdfjkl', 'not a valid command')
            self.irc.addCallback(self.InvalidCommand(self.irc))
            self.assertResponse('asdfjkl', 'foo')
            self.assertNoResponse(' ', 2)
        finally:
            conf.supybot.reply.whenNotCommand.set(original)

    class BadInvalidCommand(callbacks.Plugin):
        def invalidCommand(self, irc, msg, tokens):
            s = 'This shouldn\'t keep Misc.invalidCommand from being called'
            raise Exception(s)

    def testBadInvalidCommandDoesNotKillAll(self):
        try:
            original = str(conf.supybot.reply.whenNotCommand)
            conf.supybot.reply.whenNotCommand.set('True')
            self.irc.addCallback(self.BadInvalidCommand(self.irc))
            self.assertRegexp('asdfjkl', 'not a valid command',
                    expectException=True)
        finally:
            conf.supybot.reply.whenNotCommand.set(original)


class PluginRegexpTestCase(PluginTestCase):
    plugins = ()
    class PCAR(callbacks.PluginRegexp):
        def test(self, irc, msg, args):
            "<foo>"
            raise callbacks.ArgumentError
    def testNoEscapingArgumentError(self):
        self.irc.addCallback(self.PCAR(self.irc))
        self.assertResponse('test', 'test <foo>')

class RichReplyMethodsTestCase(PluginTestCase):
    plugins = ('Config',)
    class NoCapability(callbacks.Plugin):
        def error(self, irc, msg, args):
            irc.errorNoCapability('admin')
    def testErrorNoCapability(self):
        self.irc.addCallback(self.NoCapability(self.irc))
        self.assertRegexp('error', 'You don\'t have the admin capability')
        self.assertNotError('config capabilities.private admin')
        self.assertRegexp('error', 'Error: You\'re missing some capability')
        self.assertNotError('config capabilities.private ""')


class SourceNestedPluginTestCase(PluginTestCase):
    plugins = ('Utilities',)
    class E(callbacks.Plugin):
        def f(self, irc, msg, args):
            """takes no arguments

            F
            """
            irc.reply('f')

        def empty(self, irc, msg, args):
            pass

        class g(callbacks.Commands):
            def h(self, irc, msg, args):
                """takes no arguments

                H
                """
                irc.reply('h')

            class i(callbacks.Commands):
                def j(self, irc, msg, args):
                    """takes no arguments

                    J
                    """
                    irc.reply('j')

        class same(callbacks.Commands):
            def same(self, irc, msg, args):
                """takes no arguments

                same
                """
                irc.reply('same')

    def test(self):
        cb = self.E(self.irc)
        self.irc.addCallback(cb)
        self.assertEqual(cb.getCommand(['f']), ['f'])
        self.assertEqual(cb.getCommand(['same']), ['same'])
        self.assertEqual(cb.getCommand(['e', 'f']), ['e', 'f'])
        self.assertEqual(cb.getCommand(['e', 'g', 'h']), ['e', 'g', 'h'])
        self.assertEqual(cb.getCommand(['e', 'g', 'i', 'j']),
                                       ['e', 'g', 'i', 'j'])
        self.assertResponse('e f', 'f')
        self.assertResponse('e same', 'same')
        self.assertResponse('e g h', 'h')
        self.assertResponse('e g i j', 'j')
        self.assertHelp('help f')
        self.assertHelp('help empty')
        self.assertHelp('help same')
        self.assertHelp('help e g h')
        self.assertHelp('help e g i j')
        self.assertRegexp('list e', 'f, g h, g i j, and same')

    def testCommandSameNameAsNestedPlugin(self):
        cb = self.E(self.irc)
        self.irc.addCallback(cb)
        self.assertResponse('e f', 'f') # Just to make sure it was loaded.
        self.assertEqual(cb.getCommand(['e', 'same']), ['e', 'same'])
        self.assertResponse('e same', 'same')


class WithPrivateNoticeTestCase(ChannelPluginTestCase):
    plugins = ('Utilities',)
    class WithPrivateNotice(callbacks.Plugin):
        def normal(self, irc, msg, args):
            irc.reply('should be with private notice')
        def explicit(self, irc, msg, args):
            irc.reply('should not be with private notice',
                      private=False, notice=False)
        def implicit(self, irc, msg, args):
            irc.reply('should be with notice due to private',
                      private=True)
    def test(self):
        self.irc.addCallback(self.WithPrivateNotice(self.irc))
        # Check normal behavior.
        m = self.assertNotError('normal')
        self.failIf(m.command == 'NOTICE')
        self.failUnless(ircutils.isChannel(m.args[0]))
        m = self.assertNotError('explicit')
        self.failIf(m.command == 'NOTICE')
        self.failUnless(ircutils.isChannel(m.args[0]))
        # Check abnormal behavior.
        originalInPrivate = conf.supybot.reply.inPrivate()
        originalWithNotice = conf.supybot.reply.withNotice()
        try:
            conf.supybot.reply.inPrivate.setValue(True)
            conf.supybot.reply.withNotice.setValue(True)
            m = self.assertNotError('normal')
            self.failUnless(m.command == 'NOTICE')
            self.failIf(ircutils.isChannel(m.args[0]))
            m = self.assertNotError('explicit')
            self.failIf(m.command == 'NOTICE')
            self.failUnless(ircutils.isChannel(m.args[0]))
        finally:
            conf.supybot.reply.inPrivate.setValue(originalInPrivate)
            conf.supybot.reply.withNotice.setValue(originalWithNotice)
        orig = conf.supybot.reply.withNoticeWhenPrivate()
        try:
            conf.supybot.reply.withNoticeWhenPrivate.setValue(True)
            m = self.assertNotError('implicit')
            self.failUnless(m.command == 'NOTICE')
            self.failIf(ircutils.isChannel(m.args[0]))
            m = self.assertNotError('normal')
            self.failIf(m.command == 'NOTICE')
            self.failUnless(ircutils.isChannel(m.args[0]))
        finally:
            conf.supybot.reply.withNoticeWhenPrivate.setValue(orig)

    def testWithNoticeWhenPrivateNotChannel(self):
        original = conf.supybot.reply.withNoticeWhenPrivate()
        try:
            conf.supybot.reply.withNoticeWhenPrivate.setValue(True)
            m = self.assertNotError("eval irc.reply('y',to='x',private=True)")
            self.failUnless(m.command == 'NOTICE')
            m = self.getMsg(' ')
            m = self.assertNotError("eval irc.reply('y',to='#x',private=True)")
            self.failIf(m.command == 'NOTICE')
        finally:
            conf.supybot.reply.withNoticeWhenPrivate.setValue(original)

class ProxyTestCase(SupyTestCase):
    def testHashing(self):
        msg = ircmsgs.ping('0')
        irc = irclib.Irc('test')
        proxy = callbacks.SimpleProxy(irc, msg)
        # First one way...
        self.failIf(proxy != irc)
        self.failUnless(proxy == irc)
        self.assertEqual(hash(proxy), hash(irc))
        # Then the other!
        self.failIf(irc != proxy)
        self.failUnless(irc == proxy)
        self.assertEqual(hash(irc), hash(proxy))

        # And now dictionaries...
        d = {}
        d[irc] = 'foo'
        self.failUnless(len(d) == 1)
        self.failUnless(d[irc] == 'foo')
        self.failUnless(d[proxy] == 'foo')
        d[proxy] = 'bar'
        self.failUnless(len(d) == 1)
        self.failUnless(d[irc] == 'bar')
        self.failUnless(d[proxy] == 'bar')
        d[irc] = 'foo'
        self.failUnless(len(d) == 1)
        self.failUnless(d[irc] == 'foo')
        self.failUnless(d[proxy] == 'foo')




# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
