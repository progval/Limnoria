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

import fix

import gc
import os
import re
import sys
import time
started = time.time()
import unittest

import log
import conf
import utils
import ircdb
import world
world.startedAt = started
import irclib
import drivers
import ircmsgs
import ircutils
import callbacks

import Owner

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
        unittest.TestCase.setUp(self)

class PluginTestCase(SupyTestCase):
    """Subclass this to write a test case for a plugin.  See test/test_Fun.py
    for an example.
    """
    timeout = 10
    plugins = None
    cleanConfDir = True
    cleanDataDir = True
    def setUp(self, nick='test'):
        if self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            # Necessary because there's a test in here that shouldn\'t run.
            return
        SupyTestCase.setUp(self)
        # Set conf variables appropriately.
        conf.supybot.prefixChars.set('@')
        conf.supybot.reply.whenNotCommand.setValue(False)
        self.myVerbose = world.myVerbose
        if self.cleanConfDir:
            for filename in os.listdir(conf.supybot.directories.conf()):
                os.remove(os.path.join(conf.supybot.directories.conf(),
                                       filename))
        if self.cleanDataDir:
            for filename in os.listdir(conf.supybot.directories.data()):
                os.remove(os.path.join(conf.supybot.directories.data(),
                                       filename))
        ircdb.users.reload()
        ircdb.ignores.reload()
        ircdb.channels.reload()
        if self.plugins is None:
            raise ValueError, 'PluginTestCase must have a "plugins" attribute.'
        self.nick = nick
        self.prefix = ircutils.joinHostmask(nick, 'user', 'host.domain.tld')
        self.irc = irclib.Irc(nick)
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

    def tearDown(self):
        if self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            # Necessary because there's a test in here that shouldn\'t run.
            return
        self.irc.die()
        ircdb.users.close()
        ircdb.ignores.close()
        ircdb.channels.close()
        gc.collect()

    def _feedMsg(self, query, timeout=None, to=None, frm=None):
        if to is None:
            to = self.irc.nick
        if frm is None:
            frm = self.prefix
        if timeout is None:
            timeout = self.timeout
        if self.myVerbose:
            print # Extra newline, so it's pretty.
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
    def assertError(self, query, to=None, frm=None):
        m = self._feedMsg(query, to=to, frm=frm)
        if m is None:
            raise TimeoutError, query
        if lastGetHelp not in m.args[1]:
            self.failUnless(m.args[1].startswith('Error:'),
                            '%r did not error: %s' % (query, m.args[1]))
        return m

    def assertNotError(self, query, to=None, frm=None):
        m = self._feedMsg(query, to=to, frm=frm)
        if m is None:
            raise TimeoutError, query
        self.failIf(m.args[1].startswith('Error:'),
                    '%r errored: %s' % (query, m.args[1]))
        self.failIf(lastGetHelp in m.args[1],
                    '%r returned the help string.' % query)
        return m

    def assertHelp(self, query, to=None, frm=None):
        m = self._feedMsg(query, to=to, frm=frm)
        if m is None:
            raise TimeoutError, query
        self.failUnless(lastGetHelp in m.args[1],
                        '%s is not the help (%s)' % (m.args[1], lastGetHelp))
        return m

    def assertNoResponse(self, query, timeout=None, to=None, frm=None):
        m = self._feedMsg(query, timeout=timeout, to=to, frm=frm)
        self.failIf(m, 'Unexpected response: %r' % m)
        return m
        
    def assertResponse(self, query, expectedResponse, to=None, frm=None):
        m = self._feedMsg(query, to=to, frm=frm)
        if m is None:
            raise TimeoutError, query
        self.assertEqual(m.args[1], expectedResponse,
                         '%r != %r' % (expectedResponse, m.args[1]))
        return m

    def assertRegexp(self, query, regexp, flags=re.I, to=None, frm=None):
        m = self._feedMsg(query, to=to, frm=frm)
        if m is None:
            raise TimeoutError, query
        self.failUnless(re.search(regexp, m.args[1], flags),
                        '%r does not match %r' % (m.args[1], regexp))
        return m

    def assertNotRegexp(self, query, regexp, flags=re.I, to=None, frm=None):
        m = self._feedMsg(query, to=to, frm=frm)
        if m is None:
            raise TimeoutError, query
        self.failUnless(re.search(regexp, m.args[1], flags) is None,
                        '%r matched %r' % (m.args[1], regexp))
        return m

    def assertAction(self, query, expectedResponse=None, to=None, frm=None):
        m = self._feedMsg(query, to=to, frm=frm)
        if m is None:
            raise TimeoutError, query
        self.failUnless(ircmsgs.isAction(m))
        if expectedResponse is not None:
            self.assertEqual(ircmsgs.unAction(m), expectedResponse)
        return m

    def assertActionRegexp(self, query, regexp, flags=re.I, to=None, frm=None):
        m = self._feedMsg(query, to=to, frm=frm)
        if m is None:
            raise TimeoutError, query
        self.failUnless(ircmsgs.isAction(m))
        s = ircmsgs.unAction(m)
        self.failUnless(re.search(regexp, s, flags),
                        '%r does not match %r' % (s, regexp))

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
        self.assertEqual(m.command, 'MODE')
        m = self.irc.takeMsg()
        self.assertEqual(m.command, 'WHO')
        
    def _feedMsg(self, query, timeout=None, to=None, frm=None):
        if to is None:
            to = self.channel
        if frm is None:
            frm = self.prefix
        if timeout is None:
            timeout = self.timeout
        if self.myVerbose:
            print # Newline, just like PluginTestCase.
        if query[0] not in conf.supybot.prefixChars():
            query = conf.supybot.prefixChars()[0] + query
        msg = ircmsgs.privmsg(to, query, prefix=frm)
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

    def feedMsg(self, query):
        """Just feeds it a message, that's all."""
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, query,
                                         prefix=self.prefix))


class PluginDocumentation:
    pass # This is old stuff, it should be removed some day.
                

    


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

