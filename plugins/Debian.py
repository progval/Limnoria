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
This is a module to contain Debian-specific commands.
"""

from baseplugin import *

import re
import gzip
import sets
import popen2
import random
import os.path
import urllib2
from itertools import imap, ifilter

import conf
import utils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Debian')
    if not utils.findBinaryInPath('zegrep'):
        if not advanced:
            print 'I can\'t find zegrep in your path.  This is necessary '
            print 'to run the debfile command.  I\'ll disable this command '
            print 'now.  When you get zegrep in your path, use the command '
            print '"enable debfile" to re-enable the command.'
            onStart.append('disable debfile')
        else:
            print 'I can\'t find zegrep in your path.  If you want to run the '
            print 'debfile command with any sort of expediency, you\'ll need '
            print 'it.  You can use a python equivalent, but it\'s about two '
            print 'orders of magnitude slower.  THIS MEANS IT WILL TAKE AGES '
            print 'TO RUN THIS COMMAND.  Don\'t do this.'
            if yn('Do you want to use a Python equivalent of zegrep?') == 'y':
                onStart.append('usepythonzegrep')
            else:
                print 'I\'ll disable debfile now.'
                onStart.append('disable debfile')

example = utils.wrapLines("""
<jemfinch> @list Debian
<supybot> debfile, debversion, usepythonzegrep
<jemfinch> @debversion python
<supybot> Total matches: 3, shown: 3.   python 2.1.3-3.2 (stable),  python 2.2.3-3 (testing),  python 2.3-4 (unstable)
<jemfinch> @debfile /usr/bin/python
<supybot> python/python, devel/crystalspace-dev, python/python1.5, python/python2.1, python/python2.1-popy, python/python2.2, python/python2.2-popy, python/python2.3, python/python2.3-popy, devel/sloccount, graphics/pythoncad, mail/pms
""")


class Debian(callbacks.Privmsg, PeriodicFileDownloader):
    threaded = True
    periodicFiles = {
        'Contents-i386.gz': ('ftp://ftp.us.debian.org/'
                             'debian/dists/unstable/Contents-i386.gz',
                             86400, None)
        }
    contents = os.path.join(conf.dataDir, 'Contents-i386.gz')
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        PeriodicFileDownloader.__init__(self)
        self.usePythonZegrep = False

    def usepythonzegrep(self, irc, msg, args):
        """takes no arguments

        Mostly a debuggin tool; tells the module to use its own hand-rolled
        zegrep in Python rather than an actual zegrep command.  The Python
        zegrep is about 50x slower than a real zegrep, so you probably don't
        want to do this.
        """
        self.usePythonZegrep = not self.usePythonZegrep
        irc.reply(msg, conf.replySuccess)

    def debfile(self, irc, msg, args):
        """<file>

        Returns the packages in the Debian distribution that include <file>.
        """
        self.getFile('Contents-i386.gz')
        # Make sure it's anchored, make sure it doesn't have a leading slash
        # (the filenames don't have leading slashes, and people may not know
        # that).
        regexp = privmsgs.getArgs(args).lstrip('^/')
        try:
            re_obj = re.compile(regexp, re.I)
        except:
            irc.error(msg, "Error in filename: %s" % regexp)
            return
        if self.usePythonZegrep:
            fd = gzip.open(self.contents)
            r = imap(lambda tup: tup[0], \
                     ifilter(lambda tup: tup[0], \
                             imap(lambda line: (re_obj.search(line), line),
                                  fd)))
        (r, w) = popen2.popen4(['zegrep', regexp, self.contents])
        packages = sets.Set()  # Make packages unique
        try:
            for line in r:
                try:
                    (filename, pkg_list) = line[:-1].split()
                    if filename == 'FILE':
                        # This is the last line before the actual files.
                        continue
                except ValueError: # Unpack list of wrong size.
                    continue       # We've not gotten to the files yet.
                packages.update(pkg_list.split(','))
                if len(packages) > 40:
                    irc.error(msg, 'More than 40 results returned, ' \
                                   'please be more specific.')
                    return
        finally:
            r.close()
            w.close()
        if len(packages) == 0:
            irc.reply(msg, 'I found no packages with that file.')
        else:
            irc.reply(msg, utils.commaAndify(packages))
                
    _debreflags = re.DOTALL | re.IGNORECASE
    _debpkgre = re.compile(r'<a.*>(.*?)</a>', _debreflags)
    _debbrre = re.compile(r'<td align="center">(\S+)\s*</?td>', _debreflags)
    _debtablere = re.compile(r'<table\s*[^>]*>(.*?)</table>', _debreflags)
    _debnumpkgsre = re.compile(r'out of total of (\d+)', _debreflags)
    _debBranches = ('stable', 'testing', 'unstable', 'experimental')
    def debversion(self, irc, msg, args):
        """<package name> [stable|testing|unstable|experimental]

        Returns the current version(s) of a Debian package in the given branch
        (if any, otherwise all available ones are displayed).
        """
        if args and args[-1] in self._debBranches:
            branch = args.pop()
        else:
            branch = 'all'
        if not args:
            irc.error(msg, 'You must give a package name.')
        responses = []
        numberOfPackages = 0
        for package in args:
            fd = urllib2.urlopen('http://packages.debian.org/cgi-bin/' \
                                 'search_packages.pl?' \
                                 'keywords=%s&searchon=names&' \
                                 'version=%s&release=all' % \
                                 (package, branch))
            html = fd.read()
            fd.close()
            m = self._debnumpkgsre.search(html)
            if m:
                numberOfPackages = m.group(1)
            m = self._debtablere.search(html)
            if m is None:
                responses.append('No package found for: %s (%s)' % \
                                 (package, branch))
            else:
                tableData = m.group(1)
                rows = tableData.split('</TR>')
                for row in rows:
                    pkgMatch = self._debpkgre.search(row)
                    brMatch = self._debbrre.search(row)
                    if pkgMatch and brMatch:
                        s = '%s (%s)' % (pkgMatch.group(1), brMatch.group(1))
                        responses.append(s)
        s = 'Total matches: %s, shown: %s.  %s' % \
            (numberOfPackages, len(responses), ', '.join(responses))
        irc.reply(msg, s)


Class = Debian

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
