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

"""
Simple utility functions.
"""

## from __future__ import generators

from fix import *

import os
import re
import string
import sgmllib
import htmlentitydefs

class HtmlToText(sgmllib.SGMLParser):
    """Taken from some eff-bot code on c.l.p."""
    entitydefs = htmlentitydefs.entitydefs
    def __init__(self, tagReplace=' '):
        self.data = []
        self.tagReplace = tagReplace
        sgmllib.SGMLParser.__init__(self)

    def unknown_starttag(self, tag, attr):
        self.data.append(self.tagReplace)

    def unknown_endtag(self, tag):
        self.data.append(self.tagReplace)

    def handle_data(self, data):
        self.data.append(data)

    def getText(self):
        text = ''.join(self.data).strip()
        return ' '.join(text.split()) # normalize whitespace

def htmlToText(s, tagReplace=' '):
    """Turns HTML into text.  tagReplace is a string to replace HTML tags with.
    """
    x = HtmlToText(tagReplace)
    x.feed(s)
    return x.getText()

def eachSubstring(s):
    """Returns every substring starting at the first index until the last."""
    for i in xrange(1, len(s)+1):
        yield s[:i]

def abbrev(strings):
    """Returns a dictionary mapping unambiguous abbreviations to full forms."""
    d = {}
    for s in strings:
        for abbreviation in eachSubstring(s):
            if abbreviation not in d:
                d[abbreviation] = s
            else:
                if abbreviation not in strings:
                    d[abbreviation] = None
    removals = []
    for key in d:
        if d[key] is None:
            removals.append(key)
    for key in removals:
        del d[key]
    return d

def timeElapsed(elapsed, leadingZeroes=False, years=True, weeks=True,
                days=True, hours=True, minutes=True, seconds=True):
    """Given <elapsed> seconds, returns a string with an English description of
    how much time as passed.  leadingZeroes determines whether 0 days, 0 hours,
    etc. will be printed; the others determine what larger time periods should
    be used.
    """
    elapsed = int(elapsed)
    assert years or weeks or days or \
           hours or minutes or seconds, 'One flag must be True'
    ret = []
    if years:
        yrs, elapsed = elapsed // 31536000, elapsed % 31536000
        if leadingZeroes or yrs:
            if yrs:
                leadingZeroes = True
            if yrs != 1:
                yrs = '%s years' % yrs
            else:
                yrs = '1 year'
            ret.append(yrs)
    if weeks:
        wks, elapsed = elapsed // 604800, elapsed % 604800
        if leadingZeroes or wks:
            if wks:
                leadingZeroes = True
            if wks != 1:
                wks = '%s weeks' % wks
            else:
                wks = '1 week'
            ret.append(wks)
    if days:
        ds, elapsed = elapsed // 86400, elapsed % 86400
        if leadingZeroes or ds:
            if ds:
                leadingZeroes = True
            if ds != 1:
                ds = '%s days' % ds
            else:
                ds = '1 day'
            ret.append(ds)
    if hours:
        hrs, elapsed = elapsed // 3600, elapsed % 3600
        if leadingZeroes or hrs:
            if hrs:
                leadingZeroes = True
            if hrs != 1:
                hrs = '%s hours' % hrs
            else:
                hrs = '1 hour'
            ret.append(hrs)
    if minutes or seconds:
        mins, secs = elapsed // 60, elapsed % 60
        if leadingZeroes or mins:
            if mins != 1:
                mins = '%s minutes' % mins
            else:
                mins = '1 minute'
            ret.append(mins)
        if seconds:
            if secs != 1:
                secs = '%s seconds' % secs
            else:
                secs = '1 second'
            ret.append(secs)
    if len(ret) == 0:
        raise ValueError, 'Time difference not great enough to be noted.'
    if len(ret) == 1:
        return ret[0]
    else:
        return commaAndify(ret)

def distance(s, t):
    """Returns the levenshtein edit distance between two strings."""
    n = len(s)
    m = len(t)
    if n == 0:
        return m
    elif m == 0:
        return n
    d = []
    for i in range(n+1):
        d.append([])
        for j in range(m+1):
            d[i].append(0)
            d[0][j] = j
        d[i][0] = i
    for i in range(1, n+1):
        cs = s[i-1]
        for j in range(1, m+1):
            ct = t[j-1]
            cost = int(cs != ct)
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost)
    return d[n][m]

_soundextrans = string.maketrans(string.ascii_uppercase,
                                 '01230120022455012623010202')
_notUpper = string.ascii.translate(string.ascii, string.ascii_uppercase)
def soundex(s, length=4):
    """Returns the soundex hash of a given string."""
    assert s
    s = s.upper() # Make everything uppercase.
    firstChar = s[0] # Save the first character.
    s = s.translate(string.ascii, _notUpper) # Delete non-letters.
    s = s.translate(_soundextrans) # Convert to soundex numbers.
    s = s.lstrip(s[0]) # Remove all repeated first characters.
    L = [firstChar]
    for c in s:
        if c != L[-1]:
            L.append(c)
    L = [c for c in L if c != '0'] + (['0']*(length-1))
    s = ''.join(L)
    return length and s[:length] or s.rstrip('0')

def dqrepr(s):
    """Returns a repr() of s guaranteed to be in double quotes."""
    # The wankers-that-be decided not to use double-quotes anymore in 2.3.
    # return '"' + repr("'\x00" + s)[6:]
    return '"%s"' % s.encode('string_escape').replace('"', '\\"')

nonEscapedSlashes = re.compile(r'(?<!\\)/')
def perlReToPythonRe(s):
    """Converts a string representation of a Perl regular expression (i.e.,
    m/^foo$/i or /foo|bar/) to a Python regular expression.
    """
    (kind, regexp, flags) = nonEscapedSlashes.split(s)
    regexp = regexp.replace('\\/', '/')
    if kind not in ('', 'm'):
        raise ValueError, 'Invalid kind: must be in ("", "m")'
    flag = 0
    try:
        for c in flags.upper():
            flag &= getattr(re, c)
    except AttributeError:
        raise ValueError, 'Invalid flag: %s' % c
    return re.compile(regexp, flag)

def perlReToReplacer(s):
    """Converts a string representation of a Perl regular expression (i.e.,
    s/foo/bar/g or s/foo/bar/i) to a Python function doing the equivalent
    replacement.
    """
    (kind, regexp, replace, flags) = nonEscapedSlashes.split(s)
    if kind != 's':
        raise ValueError, 'Invalid kind: must be "s"'
    g = False
    if 'g' in flags:
        g = True
        flags = filter('g'.__ne__, flags)
    r = perlReToPythonRe('/'.join(('', regexp, flags)))
    if g:
        return lambda s: r.sub(replace, s)
    else:
        return lambda s: r.sub(replace, s, 1)

def findBinaryInPath(s):
    """Return full path of a binary if it's in PATH, otherwise return None."""
    cmdLine = None
    for dir in os.getenv('PATH').split(':'):
        filename = os.path.join(dir, s)
        if os.path.exists(filename):
            cmdLine = filename
            break
    return cmdLine

def commaAndify(L):
    if len(L) == 0:
        return ''
    elif len(L) == 1:
        return L[0]
    elif len(L) == 2:
        return '%s and %s' % (L[0], L[1])
    else:
        # Not technically threadsafe.  But we'll see if that matters.
        originalLastElement = L[-1]
        L[-1] = 'and %s' % L[-1]
        s = ', '.join(L)
        L[-1] = originalLastElement
        return s

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
