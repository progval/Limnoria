#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

__revision__ = "$Id$"

import supybot.fix as fix

import gc
import os
import re
import sys
import time
started = time.time()
import shutil
import unittest
import threading

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.world as world
world.startedAt = started
import supybot.irclib as irclib
import supybot.drivers as drivers
import supybot.ircmsgs as ircmsgs
import supybot.registry as registry
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import supybot.Owner as Owner

network = True

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

originalCallbacksGetHelp = callbacks.getHelp
lastGetHelp = 'x'*1000
def cachingGetHelp(method, name=None):
    global lastGetHelp
    lastGetHelp = originalCallbacksGetHelp(method, name)
    return lastGetHelp
callbacks.getHelp = cachingGetHelp

class TimeoutError(AssertionError):
    def __str__(self):
        return '%r timed out' % self.args[0]


class SupyTestCase(unittest.TestCase):
    def setUp(self):
        log.critical('Beginning test case %s', self.id())
        threads = [t.getName() for t in threading.enumerate()]
        log.critical('Threads: %s' % utils.commaAndify(threads))
        unittest.TestCase.setUp(self)

    def tearDown(self):
        for irc in world.ircs[:]:
            irc._reallyDie()


class PluginTestCase(SupyTestCase):
    """Subclass this to write a test case for a plugin.  See test/test_Fun.py
    for an example.
    """
    timeout = 10
    plugins = None
    cleanConfDir = True
    cleanDataDir = True
    config = {}
    def __init__(self, *args, **kwargs):
        SupyTestCase.__init__(self, *args, **kwargs)
        self.originals = {}

    def setUp(self, nick='test'):
        if self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            # Necessary because there's a test in here that shouldn\'t run.
            return
        SupyTestCase.setUp(self)
        # Just in case, let's do this.  Too many people forget to call their
        # super methods.
        for irc in world.ircs[:]:
            irc._reallyDie()
        # Set conf variables appropriately.
        conf.supybot.reply.whenAddressedBy.chars.setValue('@')
        conf.supybot.reply.detailedErrors.setValue(True)
        conf.supybot.reply.whenNotCommand.setValue(True)
        self.myVerbose = world.myVerbose
        def rmFiles(dir):
            for filename in os.listdir(dir):
                file = os.path.join(dir, filename)
                if os.path.isfile(file):
                    os.remove(file)
                else:
                    shutil.rmtree(file)
        if self.cleanConfDir:
            rmFiles(conf.supybot.directories.conf())
        if self.cleanDataDir:
            rmFiles(conf.supybot.directories.data())
        ircdb.users.reload()
        ircdb.ignores.reload()
        ircdb.channels.reload()
        if self.plugins is None:
            raise ValueError, 'PluginTestCase must have a "plugins" attribute.'
        self.nick = nick
        self.prefix = ircutils.joinHostmask(nick, 'user', 'host.domain.tld')
        self.irc = irclib.Irc('test')
        while self.irc.takeMsg():
            pass
        #OwnerModule = Owner.loadPluginModule('Owner')
        MiscModule = Owner.loadPluginModule('Misc')
        ConfigModule = Owner.loadPluginModule('Config')
        _ = Owner.loadPluginClass(self.irc, Owner)
        _ = Owner.loadPluginClass(self.irc, MiscModule)
        _ = Owner.loadPluginClass(self.irc, ConfigModule)
        if isinstance(self.plugins, str):
            self.plugins = [self.plugins]
        else:
            for name in self.plugins:
                if name not in ('Owner', 'Misc', 'Config'):
                    try:
                        module = Owner.loadPluginModule(name)
                    except Owner.Deprecated, e:
                        return utils.exnToString(e)
                    cb = Owner.loadPluginClass(self.irc, module)
        for (name, value) in self.config.iteritems():
            group = conf.supybot
            parts = registry.split(name)
            if parts[0] == 'supybot':
                parts.pop(0)
            for part in parts:
                group = group.get(part)
            self.originals[group] = group()
            group.setValue(value)

    def tearDown(self):
        if self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            # Necessary because there's a test in here that shouldn\'t run.
            return
        for (group, original) in self.originals.iteritems():
            group.setValue(original)
        ircdb.users.close()
        ircdb.ignores.close()
        ircdb.channels.close()
        SupyTestCase.tearDown(self)
        gc.collect()

    def _feedMsg(self, query, timeout=None, to=None, frm=None,
                 usePrefixChar=True):
        if to is None:
            to = self.irc.nick
        if frm is None:
            frm = self.prefix
        if timeout is None:
            timeout = self.timeout
        if self.myVerbose:
            print # Extra newline, so it's pretty.
        prefixChars = conf.supybot.reply.whenAddressedBy.chars()
        if not usePrefixChar and query[0] in prefixChars:
            query = query[1:]
        msg = ircmsgs.privmsg(to, query, prefix=frm)
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
            print 'Response: %r' % response
        return response

    def getMsg(self, query, **kwargs):
        return self._feedMsg(query, **kwargs)

    def feedMsg(self, query, to=None, frm=None):
        """Just feeds it a message, that's all."""
        if to is None:
            to = self.irc.nick
        if frm is None:
            frm = self.prefix
        self.irc.feedMsg(ircmsgs.privmsg(to, query, prefix=frm))

    # These assertError/assertNoError are somewhat fragile.  The proper way to
    # do them would be to use a proxy for the irc object and intercept .error.
    # But that would be hard, so I don't bother.  When this breaks, it'll get
    # fixed, but not until then.
    def assertError(self, query, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError, query
        if lastGetHelp not in m.args[1]:
            self.failUnless(m.args[1].startswith('Error:'),
                            '%r did not error: %s' % (query, m.args[1]))
        return m

    def assertSnarfError(self, query, **kwargs):
        return self.assertError(query, usePrefixChar=False, **kwargs)

    def assertNotError(self, query, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError, query
        self.failIf(m.args[1].startswith('Error:'),
                    '%r errored: %s' % (query, m.args[1]))
        self.failIf(lastGetHelp in m.args[1],
                    '%r returned the help string.' % query)
        return m

    def assertSnarfNotError(self, query, **kwargs):
        return self.assertNotError(query, usePrefixChar=False, **kwargs)

    def assertHelp(self, query, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError, query
        self.failUnless(lastGetHelp in m.args[1],
                        '%s is not the help (%s)' % (m.args[1], lastGetHelp))
        return m

    def assertNoResponse(self, query, timeout=0, **kwargs):
        m = self._feedMsg(query, timeout=timeout, **kwargs)
        self.failIf(m, 'Unexpected response: %r' % m)
        return m

    def assertSnarfNoResponse(self, query, timeout=0, **kwargs):
        return self.assertNoResponse(query, timeout=timeout,
                                     usePrefixChar=False, **kwargs)

    def assertResponse(self, query, expectedResponse, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError, query
        self.assertEqual(m.args[1], expectedResponse,
                         '%r != %r' % (expectedResponse, m.args[1]))
        return m

    def assertSnarfResponse(self, query, expectedResponse, **kwargs):
        return self.assertResponse(query, expectedResponse,
                                   usePrefixChar=False, **kwargs)

    def assertRegexp(self, query, regexp, flags=re.I, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError, query
        self.failUnless(re.search(regexp, m.args[1], flags),
                        '%r does not match %r' % (m.args[1], regexp))
        return m

    def assertSnarfRegexp(self, query, regexp, flags=re.I, **kwargs):
        return self.assertRegexp(query, regexp, flags=re.I,
                                 usePrefixChar=False, **kwargs)

    def assertNotRegexp(self, query, regexp, flags=re.I, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError, query
        self.failUnless(re.search(regexp, m.args[1], flags) is None,
                        '%r matched %r' % (m.args[1], regexp))
        return m

    def assertSnarfNotRegexp(self, query, regexp, flags=re.I, **kwargs):
        return self.assertNotRegexp(query, regexp, flags=re.I,
                                    usePrefixChar=False, **kwargs)

    def assertAction(self, query, expectedResponse=None, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError, query
        self.failUnless(ircmsgs.isAction(m), '%r is not an action.' % m)
        if expectedResponse is not None:
            s = ircmsgs.unAction(m)
            self.assertEqual(s, expectedResponse, '%r != %r' % (s, m))
        return m

    def assertSnarfAction(self, query, expectedResponse=None, **kwargs):
        return self.assertAction(query, expectedResponse=None,
                                 usePrefixChar=False, **kwargs)

    def assertActionRegexp(self, query, regexp, flags=re.I, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError, query
        self.failUnless(ircmsgs.isAction(m))
        s = ircmsgs.unAction(m)
        self.failUnless(re.search(regexp, s, flags),
                        '%r does not match %r' % (s, regexp))

    def assertSnarfActionRegexp(self, query, regexp, flags=re.I, **kwargs):
        return self.assertActionRegexp(query, regexp, flags=re.I,
                                       usePrefixChar=False, **kwargs)

    def testDocumentation(self):
        if self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            return
        for cb in self.irc.callbacks:
            name = cb.name()
            if (name in ('Admin', 'Channel', 'Misc', 'Owner', 'User') and \
               not name.lower() in self.__class__.__name__.lower()) or \
               isinstance(cb, callbacks.PrivmsgRegexp):
                continue
            self.failUnless(sys.modules[cb.__class__.__name__].__doc__,
                            '%s has no module documentation.' % name)
            if hasattr(cb, 'isCommand'):
                for attr in dir(cb):
                    if cb.isCommand(attr) and \
                       attr == callbacks.canonicalName(attr):
                        self.failUnless(getattr(cb, attr, None).__doc__,
                                        '%s.%s has no help.' % (name, attr))


class ChannelPluginTestCase(PluginTestCase):
    channel = '#test'
    def setUp(self):
        if self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            return
        PluginTestCase.setUp(self)
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        m = self.irc.takeMsg()
        self.failIf(m is None, 'No message back from joining channel.')
        self.assertEqual(m.command, 'MODE')
        m = self.irc.takeMsg()
        self.failIf(m is None, 'No message back from joining channel.')
        self.assertEqual(m.command, 'WHO')

    def _feedMsg(self, query, timeout=None, to=None, frm=None, private=False,
                 usePrefixChar=True):
        if to is None:
            if private:
                to = self.irc.nick
            else:
                to = self.channel
        if frm is None:
            frm = self.prefix
        if timeout is None:
            timeout = self.timeout
        if self.myVerbose:
            print # Newline, just like PluginTestCase.
        prefixChars = conf.supybot.reply.whenAddressedBy.chars()
        if query[0] not in prefixChars and usePrefixChar:
            query = prefixChars[0] + query
        msg = ircmsgs.privmsg(to, query, prefix=frm)
        if self.myVerbose:
            print 'Feeding: %r' % msg
        self.irc.feedMsg(msg)
        fed = time.time()
        response = self.irc.takeMsg()
        while response is None and time.time() - fed < timeout:
            time.sleep(0.1)
            drivers.run()
            response = self.irc.takeMsg()
        if response is not None:
            if response.command == 'PRIVMSG':
                args = list(response.args)
                # Strip off nick: at beginning of response.
                if args[1].startswith(self.nick) or \
                   args[1].startswith(ircutils.nickFromHostmask(self.prefix)):
                    try:
                        args[1] = args[1].split(' ', 1)[1]
                    except IndexError:
                        # Odd.  We'll skip this.
                        pass
                ret = ircmsgs.privmsg(*args)
            else:
                ret = response
        else:
            ret = None
        if self.myVerbose:
            print 'Returning: %r' % ret
        return ret

    def feedMsg(self, query, to=None, frm=None, private=False):
        """Just feeds it a message, that's all."""
        if to is None:
            if private:
                to = self.irc.nick
            else:
                to = self.channel
        if frm is None:
            frm = self.prefix
        self.irc.feedMsg(ircmsgs.privmsg(to, query, prefix=frm))


class PluginDocumentation:
    pass # This is old stuff, it should be removed some day.


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

