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

__revision__ = "$Id$"

import plugins

import re
import gzip
import sets
import getopt
import popen2
import socket
import urllib
import fnmatch
import os.path
import urllib2
from itertools import imap, ifilter

import conf
import utils
import privmsgs
import callbacks
import configurable


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
            print 'to run the file command.  I\'ll disable this command '
            print 'now.  When you get zegrep in your path, use the command '
            print '"enable file" to re-enable the command.'
            onStart.append('disable file')
        else:
            print 'I can\'t find zegrep in your path.  If you want to run the '
            print 'file command with any sort of expediency, you\'ll need '
            print 'it.  You can use a python equivalent, but it\'s about two '
            print 'orders of magnitude slower.  THIS MEANS IT WILL TAKE AGES '
            print 'TO RUN THIS COMMAND.  Don\'t do this.'
            if yn('Do you want to use a Python equivalent of zegrep?') == 'y':
                onStart.append('usepythonzegrep')
            else:
                print 'I\'ll disable file now.'
                onStart.append('disable file')

class Debian(callbacks.Privmsg,
             configurable.Mixin,
             plugins.PeriodicFileDownloader):
    threaded = True
    periodicFiles = {
        # This file is only updated once a week, so there's no sense in
        # downloading a new one every day.
        'Contents-i386.gz': ('ftp://ftp.us.debian.org/'
                             'debian/dists/unstable/Contents-i386.gz',
                             604800, None)
        }
    contents = os.path.join(conf.supybot.directories.data(),'Contents-i386.gz')
    configurables = configurable.Dictionary(
        [('python-zegrep', configurable.BoolType, False,
          """An advanced option, mostly just for testing; uses a Python-coded
          zegrep rather than the actual zegrep executable, generally resulting
          in a 50x slowdown.  What would take 2 seconds will take 100 with this
          enabled.  Don't enable this.""")]
    )
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        configurable.Mixin.__init__(self)
        plugins.PeriodicFileDownloader.__init__(self)

    def die(self):
        callbacks.Privmsg.die(self)
        configurable.Mixin.die(self)

    def file(self, irc, msg, args):
        """[--{regexp,exact}=<value>] [<glob>]

        Returns packages in Debian that includes files matching <glob>. If
        --regexp is given, returns packages that include files matching the
        given regexp.  If --exact is given, returns packages that include files
        matching exactly the string given.
        """
        self.getFile('Contents-i386.gz')
        # Make sure it's anchored, make sure it doesn't have a leading slash
        # (the filenames don't have leading slashes, and people may not know
        # that).
        (optlist, rest) = getopt.getopt(args, '', ['regexp=', 'exact='])
        if not optlist and not rest:
            raise callbacks.ArgumentError
        if len(optlist) + len(rest) > 1:
            irc.error('Only one search option is allowed.')
            return
        for (option, arg) in optlist:
            if option == '--exact':
                regexp = arg.lstrip('/')
            elif option == '--regexp':
                regexp = arg
        if rest:
            glob = rest.pop()
            regexp = fnmatch.translate(glob.lstrip('/'))
        try:
            re_obj = re.compile(regexp, re.I)
        except re.error, e:
            irc.error("Error in regexp: %s" % e)
            return
        if self.configurables.get('python-zegrep', None):
            fd = gzip.open(self.contents)
            r = imap(lambda tup: tup[0], 
                     ifilter(lambda tup: tup[0],
                             imap(lambda line:(re_obj.search(line), line),fd)))
        else:
            try:
                (r, w) = popen2.popen4(['zegrep', regexp, self.contents])
                w.close()
            except TypeError:
                # We're on Windows.
                irc.error('This command won\'t work on this platform.  '
                               'If you think it should (i.e., you know that '
                               'you have a zegrep binary somewhere) then file '
                               'a bug about it at http://supybot.sf.net/ .')
                return
        packages = sets.Set()  # Make packages unique
        try:
            for line in r:
                if len(packages) > 100:
                    irc.error('More than 100 packages matched, '
                                   'please narrow your search.')
                    return
                try:
                    (filename, pkg_list) = line[:-1].split()
                    if filename == 'FILE':
                        # This is the last line before the actual files.
                        continue
                except ValueError: # Unpack list of wrong size.
                    continue       # We've not gotten to the files yet.
                packages.update(pkg_list.split(','))
        finally:
            if hasattr(r, 'close'):
                r.close()
        if len(packages) == 0:
            irc.reply('I found no packages with that file.')
        else:
            irc.reply(utils.commaAndify(packages))
                
    _debreflags = re.DOTALL | re.IGNORECASE
    _debpkgre = re.compile(r'<a[^>]+>(.*?)</a>', _debreflags)
    _debbrre = re.compile(r'<td align="center">(\S+)\s*</?td>', _debreflags)
    _debtablere = re.compile(r'<table[^>]*>(.*?)</table>', _debreflags)
    _debnumpkgsre = re.compile(r'out of total of (\d+)', _debreflags)
    _debBranches = ('stable', 'testing', 'unstable', 'experimental')
    def version(self, irc, msg, args):
        """[stable|testing|unstable|experimental] <package name>

        Returns the current version(s) of a Debian package in the given branch
        (if any, otherwise all available ones are displayed).
        """
        if not args:
            raise callbacks.ArgumentError
        if args and args[0] in self._debBranches:
            branch = args.pop(0)
        else:
            branch = 'all'
        if not args:
            irc.error('You must give a package name.')
            return
        responses = []
        numberOfPackages = 0
        package = privmsgs.getArgs(args)
        package = urllib.quote(package)
        url = 'http://packages.debian.org/cgi-bin/search_packages.pl?keywords'\
              '=%s&searchon=names&version=%s&release=all' % (package, branch)
        try:
            fd = urllib2.urlopen(url)
            html = fd.read()
            fd.close()
        except urllib2.HTTPError, e:
            irc.error('I couldn\'t reach the search page (%s).' % e)
            return
        except socket.error, e:
            if e.args[0] == 110 or e.args[0] == 10060:
                irc.error('Connection timed out to packages.debian.org.')
                return
            else:
                raise

        if 'is down at the moment' in html:
            irc.error('Packages.debian.org is down at the moment.  '
                           'Please try again later.')
            return
        m = self._debnumpkgsre.search(html)
        if m:
            numberOfPackages = m.group(1)
        m = self._debtablere.search(html)
        if m is None:
            irc.reply('No package found for %s (%s)' %
                      (urllib.unquote(package), branch))
        else:
            tableData = m.group(1)
            rows = tableData.split('</TR>')
            for row in rows:
                pkgMatch = self._debpkgre.search(row)
                brMatch = self._debbrre.search(row)
                if pkgMatch and brMatch:
                    s = '%s (%s)' % (pkgMatch.group(1), brMatch.group(1))
                    responses.append(s)
            resp = 'Total matches: %s, shown: %s.  %s' % \
                   (numberOfPackages, len(responses), ', '.join(responses))
            irc.reply(resp)

    _incomingRe = re.compile(r'<a href="(.*?\.deb)">', re.I)
    def incoming(self, irc, msg, args):
        """[--{regexp,arch}=<value>] <glob>
        
        Checks debian incoming for a matching package name.  The arch
        parameter defaults to i386; --regexp returns only those package names
        that match a given regexp, and normal matches use standard *nix
        globbing.
        """
        (optlist, rest) = getopt.getopt(args, '', ['regexp=', 'arch='])
        predicates = []
        archPredicate = lambda s: ('_i386.' in s)
        for (option, arg) in optlist:
            if option == '--regexp':
                try:
                    r = utils.perlReToPythonRe(arg)
                    predicates.append(r.search)
                except ValueError:
                    irc.error('%r is not a valid regexp.' % arg)
                    return
            elif option == '--arch':
                arg = '_%s.' % arg
                archPredicate = lambda s, arg=arg: (arg in s)
        predicates.append(archPredicate)
        globs = privmsgs.getArgs(rest)
        for glob in globs:
            if '?' not in glob and '*' not in glob:
                glob = '*%s*' % glob
            predicates.append(lambda s: fnmatch.fnmatch(s, glob))
        packages = []
        fd = urllib2.urlopen('http://incoming.debian.org/')
        for line in fd:
            m = self._incomingRe.search(line)
            if m:
                name = m.group(1)
                if all(lambda p: p(name), predicates):
                    realname = rsplit(name, '_', 1)[0]
                    packages.append(realname)
        if len(packages) == 0:
            irc.error('No packages matched that search.')
        else:
            irc.reply(utils.commaAndify(packages))
    incoming = privmsgs.thread(incoming)
        
Class = Debian

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
