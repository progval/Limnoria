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

import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'test')
sys.path.insert(0, 'plugins')

from fix import *

import sys
import glob
import time
import os.path
import unittest

import world
import irclib
import ircmsgs
import ircutils

fd = file(os.path.join('test', 'rfc2812.msgs'), 'r')
rawmsgs = [line.strip() for line in fd]
fd.close()

msgs = [ircmsgs.IrcMsg(s) for s in rawmsgs]

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

nicks += [msg.nick for msg in msgs if msg.nick]

def getMsgs(command):
    return [msg for msg in msgs if msg.command == command]

class PluginTestCase(unittest.TestCase):
    """Subclass this to write a test case for a plugin.  See test_FunCommands
    for an example.
    """
    timeout = 10
    def setUp(self, nick='test'):
        self.nick = nick
        self.prefix = ircutils.joinHostmask(nick, 'user', 'host.domain.tld')
        self.irc = irclib.Irc(nick)
        while self.irc.takeMsg():
            pass
        self.irc.addCallback(self.plugin)
        
    def assertResponse(self, query, expectedResponse):
        self.irc.feedMsg(ircmsgs.privmsg(self.nick, query, prefix=self.prefix))
        fed = time.time()
        response = self.irc.takeMsg()
        while response is None and time.time() - fed < self.timeout:
            response = self.irc.takeMsg()
        self.failUnless(response)
        self.assertEqual(response.args[1], expectedResponse)

    def assertResponses(self, query, expectedResponses):
        self.irc.feedMsg(ircmsgs.privmsg(self.nick, query, prefix=self.prefix))
        fed = time.time()
        responses = []
        while len(responses) < len(expectedResponses) and \
                  time.time() - fed < self.timeout :
            m = self.irc.takeMsg()
            if m:
                responses.append(m)
            else:
                time.sleep(.1)
        self.assertEqual(len(expectedResponses), len(responses))
        for (response, expected) in zip(responses, expectedResponses):
            self.assertEqual(response.args[1], expected)
            
    
if __name__ == '__main__':
    world.testing = True
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = glob.glob(os.path.join('test', 'test_*.py'))
    names = [os.path.splitext(os.path.basename(file))[0] for file in files]
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
##     print 'Total asserts: %s' % unittest.asserts
##     world.testing = False
