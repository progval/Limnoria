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

import fix

import gc
import re
import sys
import imp
import glob
import time
started = time.time()
import os.path
import unittest

import debug

import world
world.startedAt = started
import ircdb
import irclib
import drivers
import ircmsgs
import ircutils
import callbacks
import OwnerCommands

nicks = ['fatjim','scn','moshez','LordVan','MetaCosm','pythong','fishfart',
         'alb','d0rt','jemfinch','StyxAlso','fors','deltab','gd',
         'hellz_hunter','are_j|pub_comp','jason_','dreid','sayke_','winjer',
         'TenOfTen','GoNoVas','queuetue','the|zzz','Hellfried','Therion',
         'shro','DaCa','rexec','polin8','r0ky','aaron_','ironfroggy','eugene',
         'faassen','tirloni','mackstann','Yhg1s','ElBarono','vegai','shang',
         'typo_','kikoforgetme','asqui','TazyTiggy','fab','nixman','liiwi',
         'AdamV','paolo','red_one','_AleX_','lament','jamessan','supybot',
         'macr0_zzz','plaisthos','redghost','disco','mphardy','gt3','mathie',
         'jonez','r0ky-office','tic','d33p','ES3merge','talin','af','flippo',
         'sholden','ameoba','shepherg','j2','Acapnotic','dash','merlin262',
         'Taaus','_moshez','rik','jafo__','blk-majik','JT__','itamar',
         'kermit-','davidmccabe','glyph','jojo','dave_p','goo','hyjinx',
         'SamB','exarkun','drewp','Ragica','skylan','redgore','k3','Ra1stlin',
         'StevenK','carball','h3x','carljm','_jacob','teratorn','frangen',
         'phed','datazone','Yaggo','acct_','nowhere','pyn','ThomasWaldmann',
         'dunker','pilotLight','brainless','LoganH_','jmpnz','steinn',
         'EliasREC','lowks__','OldSmrf','Mad77','snibril','delta','psy',
         'skimpIzu','Kengur','MoonFallen','kotkis','Hyperi']

fd = file(os.path.join('test', 'rfc2812.msgs'), 'r')
rawmsgs = [line.strip() for line in fd]
fd.close()

msgs = []
for s in rawmsgs:
    try:
        msgs.append(ircmsgs.IrcMsg(s))
    except:
        print 'IrcMsg constructor failed: %r' % s

nicks += [msg.nick for msg in msgs if msg.nick]

class path(str):
    """A class to represent platform-independent paths."""
    _r = re.compile(r'[\\/]')
    def __hash__(self):
        return reduce(lambda h, s: h ^ hash(s), self._r.split(self), 0)
    def __eq__(self, other):
        return self._r.split(self) == self._r.split(other)

class TimeoutError(AssertionError):
    def __str__(self):
        return '%r timed out' % self.args[0]

class PluginTestCase(unittest.TestCase):
    """Subclass this to write a test case for a plugin.  See test/test_Fun.py
    for an example.
    """
    timeout = 10
    plugins = ()
    def setUp(self, nick='test'):
        self.myVerbose = world.myVerbose
        for filename in os.listdir(conf.confDir):
            os.remove(os.path.join(conf.confDir, filename))
        for filename in os.listdir(conf.dataDir):
            os.remove(os.path.join(conf.dataDir, filename))
        debug.reset()
        ircdb.users.reload()
        ircdb.channels.reload()
        if not self.plugins:
            raise ValueError, 'PluginTestCase must have a "plugins" attribute.'
        self.nick = nick
        self.prefix = ircutils.joinHostmask(nick, 'user', 'host.domain.tld')
        self.irc = irclib.Irc(nick)
        while self.irc.takeMsg():
            pass
        if isinstance(self.plugins, str):
            module = OwnerCommands.loadPluginModule(self.plugins)
            cb = OwnerCommands.loadPluginClass(self.irc, module)
        else:
            for name in self.plugins:
                module = OwnerCommands.loadPluginModule(name)
                cb = OwnerCommands.loadPluginClass(self.irc, module)

    def tearDown(self):
        self.irc.die()
        gc.collect()

    def _feedMsg(self, query, timeout=None):
        if timeout is None:
            timeout = self.timeout
        if self.myVerbose:
            print # Extra newline, so it's pretty.
        msg = ircmsgs.privmsg(self.irc.nick, query, prefix=self.prefix)
        #debug.printf(msg)
        if self.myVerbose:
            print 'Feeding: %r' % msg
        self.irc.feedMsg(msg)
        fed = time.time()
        response = self.irc.takeMsg()
        while response is None and time.time() - fed < timeout:
            time.sleep(0.1) # So it doesn't suck up 100% cpu.
            drivers.run()
            response = self.irc.takeMsg()
        if self.myVerbose:
            print 'Response: %r' % msg
        return response

    def getMsg(self, query, timeout=None):
        return self._feedMsg(query, timeout=timeout)

    def feedMsg(self, query):
        """Just feeds it a message, that's all."""
        self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick, query,
                                         prefix=self.prefix))

    # These assertError/assertNoError are somewhat fragile.  The proper way to
    # do them would be to use a proxy for the irc object and intercept .error.
    # But that would be hard, so I don't bother.  When this breaks, it'll get
    # fixed, but not until then.
    def assertError(self, query):
        m = self._feedMsg(query)
        if m is None:
            raise TimeoutError, query
        self.failUnless(m.args[1].startswith('Error:'),
                        '%r did not error: %s' % (query, m.args[1]))

    def assertNotError(self, query):
        m = self._feedMsg(query)
        if m is None:
            raise TimeoutError, query
        self.failIf(m.args[1].startswith('Error:'),
                    '%r errored: %s' % (query, m.args[1]))

    def assertNoResponse(self, query, timeout=None):
        m = self._feedMsg(query, timeout)
        self.failIf(m)
        
    def assertResponse(self, query, expectedResponse):
        m = self._feedMsg(query)
        if m is None:
            raise TimeoutError, query
        self.assertEqual(m.args[1], expectedResponse,
                         '%r != %r' % (expectedResponse, m.args[1]))

    def assertRegexp(self, query, regexp, flags=re.I):
        m = self._feedMsg(query)
        if m is None:
            raise TimeoutError, query
        self.failUnless(re.search(regexp, m.args[1], flags),
                        '%r does not match %r' % (m.args[1], regexp))

    def assertNotRegexp(self, query, regexp, flags=re.I):
        m = self._feedMsg(query)
        if m is None:
            raise TimeoutError, query
        self.failUnless(re.search(regexp, m.args[1], flags) is None,
                        '%r matched %r' % (m.args[1], regexp))

    def assertRegexps(self, query, regexps):
        started = time.time()
        total = len(regexps)*self.timeout
        while regexps and time.time() - started < total:
            m = self._feedMsg(query)
            if m is None:
                raise TimeoutError, query
            regexp = regexps.pop(0)
            self.failUnless(re.search(regexp, m.args[1]),
                            '%r does not match %r' % (m.args[1], regexp))
        self.failIf(time.time() - started > total)

    def assertResponses(self, query, expectedResponses):
        responses = []
        started = time.time()
        while len(responses) < len(expectedResponses) and \
                  time.time() - started > len(expectedResponses)*self.timeout:
            m = self._feedMsg(query)
            if m is None:
                raise TimeoutError, query
            responses.append(m)
        self.assertEqual(len(expectedResponses), len(responses))
        for (m, expected) in zip(responses, expectedResponses):
            self.assertEqual(m.args[1], expected)

    def assertAction(self, query, expectedResponse=None):
        m = self._feedMsg(query)
        if m is None:
            raise TimeoutError, query
        self.failUnless(ircmsgs.isAction(m))
        if expectedResponse is not None:
            self.assertEqual(ircmsgs.unAction(m), expectedResponse)

    def assertActionRegexp(self, query, regexp, flags=re.I):
        m = self._feedMsg(query)
        if m is None:
            raise TimeoutError, query
        self.failUnless(ircmsgs.isAction(m))
        s = ircmsgs.unAction(m)
        self.failUnless(re.search(regexp, s, flags),
                        '%r does not match %r' % (s, regexp))

class ChannelPluginTestCase(PluginTestCase):
    channel = '#test'

    def setUp(self):
        PluginTestCase.setUp(self)
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        
    def _feedMsg(self, query, timeout=None):
        if timeout is None:
            timeout = self.timeout
        if self.myVerbose:
            print # Newline, just like PluginTestCase.
        if query[0] not in conf.prefixChars:
            query = conf.prefixChars[0] + query
        msg = ircmsgs.privmsg(self.channel, query, prefix=self.prefix)
        if self.myVerbose:
            print 'Feeding: %r' % msg
        self.irc.feedMsg(msg)
        fed = time.time()
        response = self.irc.takeMsg()
        while response is None and time.time() - fed < timeout:
            drivers.run()
            response = self.irc.takeMsg()
        if response is not None:
            if response.command == 'PRIVMSG':
                args = list(response.args)
                # Strip off nick: at beginning of response.
                if args[1].startswith(self.nick) or \
                   args[1].startswith(ircutils.nickFromHostmask(self.prefix)):
                    args[1] = args[1].split(None, 1)[1]
                ret = ircmsgs.privmsg(*args)
            else:
                ret = response
        else:
            ret = None
        if self.myVerbose:
            print 'Returning: %r' % ret
        return ret

    def feedMsg(self, query):
        """Just feeds it a message, that's all."""
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, query,
                                         prefix=self.prefix))


class PluginDocumentation:
    def testAllCommandsHaveHelp(self):
        for cb in self.irc.callbacks:
            if isinstance(cb, callbacks.PrivmsgRegexp):
                continue
            if hasattr(cb, 'isCommand'):
                for attr in cb.__class__.__dict__:
                    if cb.isCommand(attr):
                        self.failUnless(getattr(cb, attr).__doc__,
                                        '%s has no syntax' % attr)
    def testAllCommandsHaveMorehelp(self):
        for cb in self.irc.callbacks:
            if isinstance(cb, callbacks.PrivmsgRegexp):
                continue
            if hasattr(cb, 'isCommand'):
                for attr in cb.__class__.__dict__:
                    if cb.isCommand(attr):
                        command = getattr(cb, attr)
                        helps = command.__doc__
                        self.failUnless(helps and len(helps.splitlines()) >= 3,
                                        '%s has no help' % attr)

    def testPluginHasDocumentation(self):
        for cb in self.irc.callbacks:
            m = sys.modules[cb.__class__.__module__]
            self.failIf(m.__doc__ is None,
                        '%s has no module documentation'%cb.__class__.__name__)
                

    

if __name__ == '__main__':
    import optparse

    if not os.path.exists(conf.dataDir):
        os.mkdir(conf.dataDir)

    if not os.path.exists(conf.confDir):
        os.mkdir(conf.confDir)

    if not os.path.exists(conf.logDir):
        os.mkdir(conf.logDir)

    debug._close()
    for filename in os.listdir(conf.logDir):
        os.remove(os.path.join(conf.logDir, filename))
    debug._open()

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
    parser.add_option('-s', '--stderr', action='store_true', default=False,
                      help='Sets debug.stderr to True, printing standard log '
                           'messages to stderr.')
    (options, args) = parser.parse_args()
    if not args:
        args = map(path, glob.glob(os.path.join('test', 'test_*.py')))

    if options.exclusions:
        for name in map(path, options.exclusions):
            args = [s for s in args if s != name]

    if options.timeout:
        PluginTestCase.timeout = options.timeout

    if options.plugindirs:
        conf.pluginDirs.extend(options.plugindirs)

    if options.verbose:
        world.myVerbose = True
    else:
        world.myVerbose = False

    if options.stderr:
        debug.stderr = True
    else:
        debug.stderr = False
    
    world.testing = True
    names = [os.path.splitext(os.path.basename(name))[0] for name in args]
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
    print 'Total asserts: %s' % unittest.asserts
    world.testing = False

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
