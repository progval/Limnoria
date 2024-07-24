###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import copy
import random

import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils

# The test framework used to provide these, but not it doesn't.  We'll add
# messages to as we find bugs (if indeed we find bugs).
msgs = []
rawmsgs = []

class FunctionsTestCase(SupyTestCase):
    hostmask = 'foo!bar@baz'
    def testHostmaskPatternEqual(self):
        for msg in msgs:
            if msg.prefix and ircutils.isUserHostmask(msg.prefix):
                s = msg.prefix
                self.assertTrue(ircutils.hostmaskPatternEqual(s, s),
                                '%r did not match itself.' % s)
                banmask = ircutils.banmask(s)
                self.assertTrue(ircutils.hostmaskPatternEqual(banmask, s),
                                '%r did not match %r' % (s, banmask))
        s = 'supybot!~supybot@dhcp065-024-075-056.columbus.rr.com'
        self.assertTrue(ircutils.hostmaskPatternEqual(s, s))
        s = 'jamessan|work!~jamessan@209-6-166-196.c3-0.' \
            'abr-ubr1.sbo-abr.ma.cable.rcn.com'
        self.assertTrue(ircutils.hostmaskPatternEqual(s, s))

    def testHostmaskSet(self):
        hs = ircutils.HostmaskSet()
        self.assertEqual(hs.match("nick!user@host"), None)
        hs.add("*!user@host")
        hs.add("*!user@host2")
        self.assertEqual(hs.match("nick!user@host"), "*!user@host")
        self.assertEqual(hs.match("nick!user@host2"), "*!user@host2")
        self.assertCountEqual(list(hs), ["*!user@host", "*!user@host2"])
        hs.remove("*!user@host2")
        self.assertEqual(hs.match("nick!user@host"), "*!user@host")
        self.assertEqual(hs.match("nick!user@host2"), None)

        hs = ircutils.HostmaskSet(["*!user@host"])
        self.assertEqual(hs.match("nick!user@host"), "*!user@host")

    def testExpiringHostmaskDict(self):
        hs = ircutils.ExpiringHostmaskDict()
        self.assertEqual(hs.match("nick!user@host"), None)
        time1 = time.time() + 15
        time2 = time.time() + 10
        hs["*!user@host"] = time1
        hs["*!user@host2"] = time2
        self.assertEqual(hs.match("nick!user@host"), "*!user@host")
        self.assertEqual(hs.match("nick!user@host2"), "*!user@host2")
        self.assertCountEqual(list(hs.items()),
            [("*!user@host", time1), ("*!user@host2", time2)])
        del hs["*!user@host2"]
        self.assertEqual(hs.match("nick!user@host"), "*!user@host")
        self.assertEqual(hs.match("nick!user@host2"), None)
        timeFastForward(10)
        self.assertEqual(hs.match("nick!user@host"), "*!user@host")
        timeFastForward(10)
        self.assertEqual(hs.match("nick!user@host"), None)

        hs = ircutils.ExpiringHostmaskDict([("*!user@host", time.time() + 10)])
        self.assertEqual(hs.match("nick!user@host"), "*!user@host")
        self.assertEqual(hs.match("nick!user@host2"), None)
        timeFastForward(11)
        self.assertEqual(hs.match("nick!user@host"), None)
        self.assertEqual(hs.match("nick!user@host2"), None)

    def testIsUserHostmask(self):
        self.assertTrue(ircutils.isUserHostmask(self.hostmask))
        self.assertTrue(ircutils.isUserHostmask('a!b@c'))
        self.assertFalse(ircutils.isUserHostmask('!bar@baz'))
        self.assertFalse(ircutils.isUserHostmask('!@baz'))
        self.assertFalse(ircutils.isUserHostmask('!bar@'))
        self.assertFalse(ircutils.isUserHostmask('!@'))
        self.assertFalse(ircutils.isUserHostmask('foo!@baz'))
        self.assertFalse(ircutils.isUserHostmask('foo!bar@'))
        self.assertFalse(ircutils.isUserHostmask(''))
        self.assertFalse(ircutils.isUserHostmask('!'))
        self.assertFalse(ircutils.isUserHostmask('@'))
        self.assertFalse(ircutils.isUserHostmask('!bar@baz'))

    def testSplitHostmask(self):
        # This is the only valid case:
        self.assertEqual(ircutils.splitHostmask('foo!bar@baz'),
            ('foo', 'bar', 'baz'))

        # This ones are technically allowed by RFC1459, but never happens in
        # practice:
        self.assertEqual(ircutils.splitHostmask('foo!bar!qux@quux'),
            ('foo', 'bar!qux', 'quux'))
        self.assertEqual(ircutils.splitHostmask('foo!bar@baz@quux'),
            ('foo', 'bar@baz', 'quux'))
        self.assertEqual(ircutils.splitHostmask('foo!bar@baz!qux@quux'),
            ('foo', 'bar@baz!qux', 'quux'))

        # And this one in garbage, let's just make sure we don't crash:
        self.assertEqual(ircutils.splitHostmask('foo!bar@baz!qux'),
            ('foo', 'bar', 'baz!qux'))

    def testIsChannel(self):
        self.assertTrue(ircutils.isChannel('#'))
        self.assertTrue(ircutils.isChannel('&'))
        self.assertFalse(ircutils.isChannel('+'))
        self.assertTrue(ircutils.isChannel('+', chantypes='#&+!'))
        self.assertTrue(ircutils.isChannel('!'))
        self.assertTrue(ircutils.isChannel('#foo'))
        self.assertTrue(ircutils.isChannel('&foo'))
        self.assertFalse(ircutils.isChannel('+foo'))
        self.assertTrue(ircutils.isChannel('+foo', chantypes='#&+!'))
        self.assertTrue(ircutils.isChannel('!foo'))
        self.assertFalse(ircutils.isChannel('#foo bar'))
        self.assertFalse(ircutils.isChannel('#foo,bar'))
        self.assertFalse(ircutils.isChannel('#foobar\x07'))
        self.assertFalse(ircutils.isChannel('foo'))
        self.assertFalse(ircutils.isChannel(''))

    def testBold(self):
        s = ircutils.bold('foo')
        self.assertEqual(s[0], '\x02')
        self.assertEqual(s[-1], '\x02')

    def testItalic(self):
        s = ircutils.italic('foo')
        self.assertEqual(s[0], '\x1d')
        self.assertEqual(s[-1], '\x1d')

    def testUnderline(self):
        s = ircutils.underline('foo')
        self.assertEqual(s[0], '\x1f')
        self.assertEqual(s[-1], '\x1f')

    def testReverse(self):
        s = ircutils.reverse('foo')
        self.assertEqual(s[0], '\x16')
        self.assertEqual(s[-1], '\x16')

    def testMircColor(self):
        # No colors provided should return the same string
        s = 'foo'
        self.assertEqual(s, ircutils.mircColor(s))
        # Test positional args
        self.assertEqual('\x0300foo\x03', ircutils.mircColor(s, 'white'))
        self.assertEqual('\x031,02foo\x03',ircutils.mircColor(s,'black','blue'))
        self.assertEqual('\x0300,03foo\x03', ircutils.mircColor(s, None, 'green'))
        # Test keyword args
        self.assertEqual('\x0304foo\x03', ircutils.mircColor(s, fg='red'))
        self.assertEqual('\x0300,05foo\x03', ircutils.mircColor(s, bg='brown'))
        self.assertEqual('\x036,07foo\x03',
                         ircutils.mircColor(s, bg='orange', fg='purple'))

# Commented out because we don't map numbers to colors anymore.
##     def testMircColors(self):
##         # Make sure all (k, v) pairs are also (v, k) pairs.
##         for (k, v) in ircutils.mircColors.items():
##             if k:
##                 self.assertEqual(ircutils.mircColors[v], k)

    def testStripBold(self):
        self.assertEqual(ircutils.stripBold(ircutils.bold('foo')), 'foo')

    def testStripItalic(self):
        self.assertEqual(ircutils.stripItalic(ircutils.italic('foo')), 'foo')

    def testStripColor(self):
        self.assertEqual(ircutils.stripColor('\x02bold\x0302,04foo\x03bar\x0f'),
                         '\x02boldfoobar\x0f')
        self.assertEqual(ircutils.stripColor('\x03foo\x03'), 'foo')
        self.assertEqual(ircutils.stripColor('\x03foo\x0F'), 'foo\x0F')
        self.assertEqual(ircutils.stripColor('\x0312foo\x03'), 'foo')
        self.assertEqual(ircutils.stripColor('\x0312,14foo\x03'), 'foo')
        self.assertEqual(ircutils.stripColor('\x03,14foo\x03'), 'foo')
        self.assertEqual(ircutils.stripColor('\x03,foo\x03'), ',foo')
        self.assertEqual(ircutils.stripColor('\x0312foo\x0F'), 'foo\x0F')
        self.assertEqual(ircutils.stripColor('\x0312,14foo\x0F'), 'foo\x0F')
        self.assertEqual(ircutils.stripColor('\x03,14foo\x0F'), 'foo\x0F')
        self.assertEqual(ircutils.stripColor('\x03,foo\x0F'), ',foo\x0F')

    def testStripReverse(self):
        self.assertEqual(ircutils.stripReverse(ircutils.reverse('foo')), 'foo')

    def testStripUnderline(self):
        self.assertEqual(ircutils.stripUnderline(ircutils.underline('foo')),
                         'foo')

    def testStripFormatting(self):
        self.assertEqual(ircutils.stripFormatting(ircutils.bold('foo')), 'foo')
        self.assertEqual(ircutils.stripFormatting(ircutils.italic('foo')), 'foo')
        self.assertEqual(ircutils.stripFormatting(ircutils.reverse('foo')),
                         'foo')
        self.assertEqual(ircutils.stripFormatting(ircutils.underline('foo')),
                         'foo')
        self.assertEqual(ircutils.stripFormatting('\x02bold\x0302,04foo\x03'
                                                  'bar\x0f'),
                         'boldfoobar')
        s = ircutils.mircColor('[', 'blue') + ircutils.bold('09:21')
        self.assertEqual(ircutils.stripFormatting(s), '[09:21')

    def testWrap(self):
        pred = lambda s:len(s.encode())

        s = ('foo bar baz qux ' * 100)[0:-1]

        r = ircutils.wrap(s, 10)
        self.assertLessEqual(max(map(pred, r)), 10)
        self.assertEqual(''.join(r), s)

        r = ircutils.wrap(s, 100)
        self.assertLessEqual(max(map(pred, r)), 100)
        self.assertEqual(''.join(r), s)

        s = (''.join([chr(0x1f527), chr(0x1f527), chr(0x1f527), ' ']) * 100)\
                [0:-1]

        r = ircutils.wrap(s, 20)
        self.assertLessEqual(max(map(pred, r)), 20, (max(map(pred, r)), repr(r)))
        self.assertEqual(''.join(r), s)

        r = ircutils.wrap(s, 100)
        self.assertLessEqual(max(map(pred, r)), 100)
        self.assertEqual(''.join(r), s)

        s = ('foobarbazqux ' * 100)[0:-1]

        r = ircutils.wrap(s, 10)
        self.assertLessEqual(max(map(pred, r)), 10)
        self.assertEqual(''.join(r), s)

        r = ircutils.wrap(s, 100)
        self.assertLessEqual(max(map(pred, r)), 100)
        self.assertEqual(''.join(r), s)

        s = ('foobarbazqux' * 100)[0:-1]

        r = ircutils.wrap(s, 10)
        self.assertLessEqual(max(map(pred, r)), 10)
        self.assertEqual(''.join(r), s)

        r = ircutils.wrap(s, 100)
        self.assertLessEqual(max(map(pred, r)), 100)
        self.assertEqual(''.join(r), s)

        s = chr(233)*500
        r = ircutils.wrap(s, 500)
        self.assertLessEqual(max(map(pred, r)), 500)
        r = ircutils.wrap(s, 139)
        self.assertLessEqual(max(map(pred, r)), 139)

        s = '\x02\x16 barbazqux' + ('foobarbazqux ' * 20)[0:-1]
        r = ircutils.wrap(s, 91)
        self.assertLessEqual(max(map(pred, r)), 91)

    def testSafeArgument(self):
        s = 'I have been running for 9 seconds'
        bolds = ircutils.bold(s)
        colors = ircutils.mircColor(s, 'pink', 'orange')
        self.assertEqual(s, ircutils.safeArgument(s))
        self.assertEqual(bolds, ircutils.safeArgument(bolds))
        self.assertEqual(colors, ircutils.safeArgument(colors))

    def testSafeArgumentConvertsToString(self):
        self.assertEqual('1', ircutils.safeArgument(1))
        self.assertEqual(str(None), ircutils.safeArgument(None))

    def testIsNick(self):
        try:
            original = conf.supybot.protocols.irc.strictRfc()
            conf.supybot.protocols.irc.strictRfc.setValue(True)
            self.assertTrue(ircutils.isNick('jemfinch'))
            self.assertTrue(ircutils.isNick('jemfinch0'))
            self.assertTrue(ircutils.isNick('[0]'))
            self.assertTrue(ircutils.isNick('{jemfinch}'))
            self.assertTrue(ircutils.isNick('[jemfinch]'))
            self.assertTrue(ircutils.isNick('jem|finch'))
            self.assertTrue(ircutils.isNick('\\```'))
            self.assertTrue(ircutils.isNick('`'))
            self.assertTrue(ircutils.isNick('A'))
            self.assertFalse(ircutils.isNick(''))
            self.assertFalse(ircutils.isNick('8foo'))
            self.assertFalse(ircutils.isNick('10'))
            self.assertFalse(ircutils.isNick('-'))
            self.assertFalse(ircutils.isNick('-foo'))
            conf.supybot.protocols.irc.strictRfc.setValue(False)
            self.assertTrue(ircutils.isNick('services@something.undernet.net'))
        finally:
            conf.supybot.protocols.irc.strictRfc.setValue(original)

    def testIsNickNeverAllowsSpaces(self):
        try:
            original = conf.supybot.protocols.irc.strictRfc()
            conf.supybot.protocols.irc.strictRfc.setValue(True)
            self.assertFalse(ircutils.isNick('foo bar'))
            conf.supybot.protocols.irc.strictRfc.setValue(False)
            self.assertFalse(ircutils.isNick('foo bar'))
        finally:
            conf.supybot.protocols.irc.strictRfc.setValue(original)

    def testStandardSubstitute(self):
        # Stub out random msg and irc objects that provide what
        # standardSubstitute wants
        irc = getTestIrc()

        msg = ircmsgs.IrcMsg(':%s PRIVMSG #channel :stuff' % self.hostmask)
        irc._tagMsg(msg)

        f = ircutils.standardSubstitute
        vars = {'foo': 'bar', 'b': 'c', 'i': 100,
                'f': lambda: 'called'}
        self.assertEqual(f(irc, msg, '$foo', vars), 'bar')
        self.assertEqual(f(irc, None, '$foo', vars), 'bar')
        self.assertEqual(f(None, None, '$foo', vars), 'bar')
        self.assertEqual(f(None, msg, '$foo', vars), 'bar')
        self.assertEqual(f(irc, msg, '${foo}', vars), 'bar')
        self.assertEqual(f(irc, msg, '$b', vars), 'c')
        self.assertEqual(f(irc, msg, '${b}', vars), 'c')
        self.assertEqual(f(irc, msg, '$i', vars), '100')
        self.assertEqual(f(irc, msg, '${i}', vars), '100')
        self.assertEqual(f(irc, msg, '$f', vars), 'called')
        self.assertEqual(f(irc, msg, '${f}', vars), 'called')
        self.assertEqual(f(irc, msg, '$b:$i', vars), 'c:100')

    def testBanmask(self):
        for msg in msgs:
            if ircutils.isUserHostmask(msg.prefix):
                banmask = ircutils.banmask(msg.prefix)
                self.assertTrue(ircutils.hostmaskPatternEqual(banmask,
                                                              msg.prefix),
                                '%r didn\'t match %r' % (msg.prefix, banmask))
        self.assertEqual(ircutils.banmask('foobar!user@host'), '*!*@host')
        self.assertEqual(ircutils.banmask('foobar!user@host.tld'),
                         '*!*@host.tld')
        self.assertEqual(ircutils.banmask('foobar!user@sub.host.tld'),
                         '*!*@*.host.tld')
        self.assertEqual(ircutils.banmask('foo!bar@2001::'), '*!*@2001::*')

    def testAccountExtban(self):
        irc = getTestIrc()
        irc.state.addMsg(irc, ircmsgs.IrcMsg(
            prefix='foo!bar@baz', command='ACCOUNT', args=['account1']))
        irc.state.addMsg(irc, ircmsgs.IrcMsg(
            prefix='bar!baz@qux', command='ACCOUNT', args=['*']))

        with self.subTest('spec example'):
            irc.state.supported['ACCOUNTEXTBAN'] = 'a,account'
            irc.state.supported['EXTBAN'] = '~,abc'
            self.assertEqual(ircutils.accountExtban(irc, 'foo'),
                             '~a:account1')
            self.assertIsNone(ircutils.accountExtban(irc, 'bar'))
            self.assertIsNone(ircutils.accountExtban(irc, 'baz'))

        with self.subTest('InspIRCd'):
            irc.state.supported['ACCOUNTEXTBAN'] = 'account,R'
            irc.state.supported['EXTBAN'] = ',abcR'
            self.assertEqual(ircutils.accountExtban(irc, 'foo'),
                             'account:account1')
            self.assertIsNone(ircutils.accountExtban(irc, 'bar'))
            self.assertIsNone(ircutils.accountExtban(irc, 'baz'))

        with self.subTest('Solanum'):
            irc.state.supported['ACCOUNTEXTBAN'] = 'a'
            irc.state.supported['EXTBAN'] = '$,abc'
            self.assertEqual(ircutils.accountExtban(irc, 'foo'),
                             '$a:account1')
            self.assertIsNone(ircutils.accountExtban(irc, 'bar'))
            self.assertIsNone(ircutils.accountExtban(irc, 'baz'))

        with self.subTest('UnrealIRCd'):
            irc.state.supported['ACCOUNTEXTBAN'] = 'account,a'
            irc.state.supported['EXTBAN'] = '~,abc'
            self.assertEqual(ircutils.accountExtban(irc, 'foo'),
                             '~account:account1')
            self.assertIsNone(ircutils.accountExtban(irc, 'bar'))
            self.assertIsNone(ircutils.accountExtban(irc, 'baz'))

        with self.subTest('no ACCOUNTEXTBAN'):
            irc.state.supported.pop('ACCOUNTEXTBAN')
            irc.state.supported['EXTBAN'] = '~,abc'
            self.assertIsNone(ircutils.accountExtban(irc, 'foo'))
            self.assertIsNone(ircutils.accountExtban(irc, 'bar'))
            self.assertIsNone(ircutils.accountExtban(irc, 'baz'))

        with self.subTest('no EXTBAN'):
            irc.state.supported['ACCOUNTEXTBAN'] = 'account,a'
            irc.state.supported.pop('EXTBAN')
            self.assertIsNone(ircutils.accountExtban(irc, 'foo'))
            self.assertIsNone(ircutils.accountExtban(irc, 'bar'))
            self.assertIsNone(ircutils.accountExtban(irc, 'baz'))


    def testSeparateModes(self):
        self.assertEqual(ircutils.separateModes(['+ooo', 'x', 'y', 'z']),
                         [('+o', 'x'), ('+o', 'y'), ('+o', 'z')])
        self.assertEqual(ircutils.separateModes(['+o-o', 'x', 'y']),
                         [('+o', 'x'), ('-o', 'y')])
        self.assertEqual(ircutils.separateModes(['+s-o', 'x']),
                         [('+s', None), ('-o', 'x')])
        self.assertEqual(ircutils.separateModes(['+sntl', '100']),
                        [('+s', None),('+n', None),('+t', None),('+l', 100)])

    def testNickFromHostmask(self):
        self.assertEqual(ircutils.nickFromHostmask('nick!user@host.domain.tld'),
                         'nick')
        # Hostmasks with user prefixes are sent via userhost-in-names. We need to
        # properly handle the case where ! is a prefix and not grab '' as the nick
        # instead.
        self.assertEqual(ircutils.nickFromHostmask('@nick!user@some.other.host'),
                         '@nick')
        self.assertEqual(ircutils.nickFromHostmask('!@nick!user@some.other.host'),
                         '!@nick')

    def testToLower(self):
        self.assertEqual('jemfinch', ircutils.toLower('jemfinch'))
        self.assertEqual('{}|^', ircutils.toLower('[]\\~'))

    def testReplyTo(self):
        irc = getTestIrc()
        prefix = 'foo!bar@baz'
        channel = ircmsgs.privmsg('#foo', 'bar baz', prefix=prefix)
        private = ircmsgs.privmsg('jemfinch', 'bar baz', prefix=prefix)
        irc._tagMsg(channel)
        irc._tagMsg(private)
        self.assertEqual(ircutils.replyTo(channel), channel.args[0])
        self.assertEqual(ircutils.replyTo(private), private.nick)

    def testJoinModes(self):
        plusE = ('+e', '*!*@*ohio-state.edu')
        plusB = ('+b', '*!*@*umich.edu')
        minusL = ('-l', None)
        modes = [plusB, plusE, minusL]
        self.assertEqual(ircutils.joinModes(modes),
                         ['+be-l', plusB[1], plusE[1]])

    def testDccIpStuff(self):
        def randomIP():
            def rand():
                return random.randrange(0, 256)
            return '.'.join(map(str, [rand(), rand(), rand(), rand()]))
        for _ in range(100): # 100 should be good :)
            ip = randomIP()
            self.assertEqual(ip, ircutils.unDccIP(ircutils.dccIP(ip)))


class IrcDictTestCase(SupyTestCase):
    def test(self):
        d = ircutils.IrcDict()
        d['#FOO'] = 'bar'
        self.assertEqual(d['#FOO'], 'bar')
        self.assertEqual(d['#Foo'], 'bar')
        self.assertEqual(d['#foo'], 'bar')
        del d['#fOO']
        d['jemfinch{}'] = 'bar'
        self.assertEqual(d['jemfinch{}'], 'bar')
        self.assertEqual(d['jemfinch[]'], 'bar')
        self.assertEqual(d['JEMFINCH[]'], 'bar')

    def testKeys(self):
        d = ircutils.IrcDict()
        self.assertEqual(d.keys(), [])

    def testSetdefault(self):
        d = ircutils.IrcDict()
        d.setdefault('#FOO', []).append(1)
        self.assertEqual(d['#foo'], [1])
        self.assertEqual(d['#fOO'], [1])
        self.assertEqual(d['#FOO'], [1])

    def testGet(self):
        d = ircutils.IrcDict()
        self.assertEqual(d.get('#FOO'), None)
        d['#foo'] = 1
        self.assertEqual(d.get('#FOO'), 1)

    def testContains(self):
        d = ircutils.IrcDict()
        d['#FOO'] = None
        self.assertIn('#foo', d)
        d['#fOOBAR[]'] = None
        self.assertIn('#foobar{}', d)

    def testGetSetItem(self):
        d = ircutils.IrcDict()
        d['#FOO'] = 12
        self.assertEqual(12, d['#foo'])
        d['#fOOBAR[]'] = 'blah'
        self.assertEqual('blah', d['#foobar{}'])

    def testCopyable(self):
        d = ircutils.IrcDict()
        d['foo'] = 'bar'
        self.assertEqual(d, copy.copy(d))
        self.assertEqual(d, copy.deepcopy(d))


class IrcSetTestCase(SupyTestCase):
    def test(self):
        s = ircutils.IrcSet()
        s.add('foo')
        s.add('bar')
        self.assertIn('foo', s)
        self.assertIn('FOO', s)
        s.discard('alfkj')
        s.remove('FOo')
        self.assertNotIn('foo', s)
        self.assertNotIn('FOo', s)

    def testCopy(self):
        s = ircutils.IrcSet()
        s.add('foo')
        s.add('bar')
        s1 = copy.deepcopy(s)
        self.assertIn('foo', s)
        self.assertIn('FOO', s)
        s.discard('alfkj')
        s.remove('FOo')
        self.assertNotIn('foo', s)
        self.assertNotIn('FOo', s)
        self.assertIn('foo', s1)
        self.assertIn('FOO', s1)
        s1.discard('alfkj')
        s1.remove('FOo')
        self.assertNotIn('foo', s1)
        self.assertNotIn('FOo', s1)


class IrcStringTestCase(SupyTestCase):
    def testEquality(self):
        self.assertEqual('#foo', ircutils.IrcString('#foo'))
        self.assertEqual('#foo', ircutils.IrcString('#FOO'))
        self.assertEqual('#FOO', ircutils.IrcString('#foo'))
        self.assertEqual('#FOO', ircutils.IrcString('#FOO'))
        self.assertEqual(hash(ircutils.IrcString('#FOO')),
                         hash(ircutils.IrcString('#foo')))

    def testInequality(self):
        s1 = 'supybot'
        s2 = ircutils.IrcString('Supybot')
        self.assertEqual(s1, s2)
        self.assertEqual(s1, s2)

class AuthenticateTestCase(SupyTestCase):
    PAIRS = [
            (b'', ['+']),
            (b'foo'*150, [
                'Zm9v'*100,
                'Zm9v'*50
                ]),
            (b'foo'*200, [
                'Zm9v'*100,
                'Zm9v'*100,
                '+'])
            ]
    def assertMessages(self, got, should):
        got = list(got)
        for (s1, s2) in zip(got, should):
            self.assertEqual(s1, s2, (got, should))

    def testGenerator(self):
        for (decoded, encoded) in self.PAIRS:
            self.assertMessages(
                    ircutils.authenticate_generator(decoded),
                    encoded)

    def testDecoder(self):
        for (decoded, encoded) in self.PAIRS:
            decoder = ircutils.AuthenticateDecoder()
            for chunk in encoded:
                self.assertFalse(decoder.ready, (decoded, encoded))
                decoder.feed(ircmsgs.IrcMsg(command='AUTHENTICATE',
                    args=(chunk,)))
            self.assertTrue(decoder.ready)
            self.assertEqual(decoder.get(), decoded)




# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

