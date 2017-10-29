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

class HashesTestCase(PluginTestCase):
    plugins = ('Hashes')

    def testXor(self):
        # This no longer works correctly.  It almost seems like were throwing
        # in a repr() somewhere.
        L = [nick for nick in nicks if '|' not in nick and
                                       '[' not in nick and
                                       ']' not in nick]
        for s0, s1, s2, s3, s4, s5, s6, s7, s8, s9 in group(L, 10):
            data = '%s%s%s%s%s%s%s%s%s' % (s0, s1, s2, s3, s4, s5, s6, s7, s8)
            self.assertResponse('xor %s [xor %s %s]' % (s9, s9, data), data)

    def testHashes(self):
        brown_fox = 'The quick brown fox jumped over the lazy dog'
        self.assertResponse('md5 %s' % brown_fox, '08a008a01d498c404b0c30852b39d3b8')
        self.assertResponse('sha %s' % brown_fox, 'f6513640f3045e9768b239785625caa6a2588842')
        self.assertResponse('sha256 %s' % brown_fox, '7d38b5cd25a2baf85ad3bb5b9311383e671a8a142eb302b324d4a5fba8748c69')
        self.assertResponse('sha512 %s' % brown_fox, 'db25330cfa5d14eaadf11a6263371cfa0e70fcd7a63a433b91f2300ca25d45b66a7b50d2f6747995c8fa0ff365b28974792e7acd5624e1ddd0d66731f346f0e7')
        self.assertResponse('mkhash md5 %s' % brown_fox, '08a008a01d498c404b0c30852b39d3b8')
        self.assertError('mkhash NonExistant %s' % brown_fox)
        self.assertNotError('algorithms')
