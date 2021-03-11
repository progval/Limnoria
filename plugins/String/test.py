###
# Copyright (c) 2003-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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

import re

from supybot.test import *
import supybot.utils as utils

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

def group(seq, groupSize, noneFill=True):
    """Groups a given sequence into sublists of length groupSize."""
    ret = []
    L = []
    i = groupSize
    for elt in seq:
        if i > 0:
            L.append(elt)
        else:
            ret.append(L)
            i = groupSize
            L = []
            L.append(elt)
        i -= 1
    if L:
        if noneFill:
            while len(L) < groupSize:
                L.append(None)
        ret.append(L)
    return ret

class StringTestCase(PluginTestCase):
    plugins = ('String', 'Format', 'Status')
    def testLen(self):
        self.assertResponse('len foo', '3')
        self.assertHelp('len')

    def testNoErrors(self):
        self.assertNotError('levenshtein Python Perl')

    def testSoundex(self):
        self.assertNotError('soundex jemfinch')
        self.assertNotRegexp('soundex foobar 3:30', 'ValueError')

    def testChr(self):
        for i in range(256):
            c = chr(i)
            regexp = r'%s|%s' % (re.escape(c), re.escape(repr(c)))
            self.assertRegexp('chr %s' % i, regexp)

    def testOrd(self):
        for c in map(chr, range(256)):
            i = ord(c)
            self.assertResponse('ord %s' % utils.str.dqrepr(c), str(i))


    def testUnicode(self):
        self.assertResponse('unicodename ☃', 'SNOWMAN')
        self.assertResponse('unicodesearch SNOWMAN', '☃')
        #self.assertResponse('unicodename ?',
        #    'No name found for this character.')
        self.assertResponse('unicodesearch FOO',
            'Error: No character found with this name.')

    def testMd5(self):
        self.assertResponse('md5 supybot', '1360578d1276e945cc235654a53f9c65')


    def testEncodeDecode(self):
        # This no longer works correctly.  It almost seems like were throwing
        # in a repr() somewhere.
        s = 'the recalcitrant jamessan tests his scramble function'
        self.assertNotRegexp('encode aldkfja foobar', 'LookupError')
        self.assertNotRegexp('decode asdflkj foobar', 'LookupError')
        self.assertResponse('decode zlib [encode zlib %s]' % s, s)
        self.assertRegexp('decode base64 $BCfBg7;9D;R(B', 'padded with')

    def testRe(self):
        self.assertResponse('re "m/system time/" [status cpu]', 'system time')
        self.assertResponse('re s/user/luser/g user user', 'luser luser')
        self.assertResponse('re s/user/luser/ user user', 'luser user')
        self.assertNotRegexp('re m/foo/ bar', 'has no attribute')
        self.assertResponse('re m/a\\S+y/ "the bot angryman is hairy"', 'angry')
        self.assertResponse('re m/a\\S+y/g "the bot angryman is hairy"',
                            'angry and airy')

    def testReNotEmptyString(self):
        self.assertError('re s//foo/g blah')

    def testReWorksWithJustCaret(self):
        self.assertResponse('re s/^/foo/ bar', 'foobar')

    def testReNoEscapingUnpackListOfWrongSize(self):
        self.assertNotRegexp('re foo bar baz', 'unpack list of wrong size')

    def testReBug850931(self):
        self.assertResponse(r're s/\b(\w+)\b/\1./g foo bar baz',
                            'foo. bar. baz.')

    def testNotOverlongRe(self):
        self.assertError('re [strjoin "" s/./ [eval \'xxx\'*400]] blah blah')

    def testXor(self):
        # This no longer works correctly.  It almost seems like were throwing
        # in a repr() somewhere.
        L = [nick for nick in nicks if '|' not in nick and
                                       '[' not in nick and
                                       ']' not in nick]
        for s0, s1, s2, s3, s4, s5, s6, s7, s8, s9 in group(L, 10):
            data = '%s%s%s%s%s%s%s%s%s' % (s0, s1, s2, s3, s4, s5, s6, s7, s8)
            self.assertResponse('xor %s [xor %s %s]' % (s9, s9, data), data)


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
