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

from test import *

class TestFunDB(PluginTestCase, PluginDocumentation):
    plugins = ('FunDB',)

    def testDbAdd(self):
        self.assertError('dbadd l4rt foo')
        self.assertError('dbadd lart foo')

    def testDbRemove(self):
        self.assertError('dbremove l4rt foo')
        self.assertError('dbremove lart foo')

    def testLart(self):
        self.assertNotError('dbadd lart jabs $who')
        self.assertResponse('lart jemfinch for being dumb', '\x01ACTION'\
            ' jabs jemfinch for being dumb (#1)\x01')
        self.assertResponse('lart jemfinch', '\x01ACTION jabs jemfinch'\
            ' (#1)\x01')
        self.assertNotError('dbnum lart')
        self.assertNotError('dbremove lart 1')
        self.assertNotError('dbnum lart')
        self.assertError('lart jemfinch')

    def testExcuse(self):
        self.assertNotError('dbadd excuse Power failure')
        self.assertNotError('excuse')
        self.assertNotError('excuse a few random words')
        self.assertNotError('dbnum excuse')
        self.assertNotError('dbremove excuse 1')
        self.assertNotError('dbnum excuse')
        self.assertError('excuse')

    def testInsult(self):
        self.assertNotError('dbadd insult Fatty McFatty')
        self.assertNotError('insult jemfinch')
        self.assertNotError('dbnum insult')
        self.assertNotError('dbremove insult 1')
        self.assertNotError('dbnum insult')
        self.assertError('insult jemfinch')

    def testPraise(self):
        self.assertNotError('dbadd praise pets $who')
        self.assertNotError('praise jemfinch')
        self.assertResponse('praise jemfinch for being him', '\x01ACTION'\
            ' pets jemfinch for being him (#1)\x01')
        self.assertResponse('praise jemfinch', '\x01ACTION pets jemfinch'\
            ' (#1)\x01')
        self.assertNotError('dbnum praise')
        self.assertNotError('dbremove praise 1')
        self.assertNotError('dbnum praise')
        self.assertError('praise jemfinch')

    def testDbInfo(self):
        self.assertNotError('dbadd praise $who')
        self.assertNotError('dbinfo praise 1')
        self.assertNotError('dbremove praise 1')
        self.assertError('dbinfo fake 1')

    def testDbGet(self):
        self.assertError('dbget fake 1')
        self.assertError('dbget lart foo')
        self.assertNotError('dbadd praise pets $who')
        self.assertNotError('dbget praise 1')
        self.assertNotError('dbremove praise 1')
        self.assertError('dbget praise 1')

    def testDbNum(self):
        self.assertError('dbnum fake')
        self.assertError('dbnum 1')
        self.assertNotError('dbnum praise')
        self.assertNotError('dbnum lart')
        self.assertNotError('dbnum excuse')
        self.assertNotError('dbnum insult')

    def testDbChange(self):
        self.assertNotError('dbadd praise teaches $who perl')
        self.assertNotError('dbchange praise 1 s/perl/python/')
        self.assertResponse('praise jemfinch', '\x01ACTION teaches'\
            ' jemfinch python (#1)\x01')
        self.assertNotError('dbremove praise 1')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

