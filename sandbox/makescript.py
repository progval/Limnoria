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

print """PRAGMA cache_size = 50000;"""
print """CREATE TABLE words (
         id INTEGER PRIMARY KEY,
         word TEXT UNIQUE ON CONFLICT IGNORE,
         sorted_word_id INTEGER
         );"""

print """CREATE INDEX sorted_word_id on words (sorted_word_id);"""

print """CREATE TABLE sorted_words (
         id INTEGER PRIMARY KEY,
         word TEXT UNIQUE ON CONFLICT IGNORE
         );"""

#print """CREATE INDEX sorted_word_word on sorted_words (sorted_word);"""

print """BEGIN TRANSACTION;"""
for line in sys.stdin:
    line = line.rstrip()
    word = line.strip().lower()
    L = list(word)
    L.sort()
    sorted = ''.join(L)
    print "INSERT INTO sorted_words VALUES (NULL, '%s');" % sorted
    print """INSERT INTO words VALUES (NULL, '%s', (SELECT id FROM sorted_words WHERE word='%s'));""" % (word, sorted)

print """END TRANSACTION;"""
