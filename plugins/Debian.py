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

"""
This is a module to contain Debian-specific commands.
"""

__revision__ = "$Id$"
__author__ = "James Vega (jamessan) <jamessan@users.sf.net>"

import re
import gzip
import sets
import getopt
import popen2
import socket
import urllib
import fnmatch
import os.path

import BeautifulSoup

from itertools import imap, ifilter

import supybot.conf as conf
import supybot.utils as utils
import supybot.plugins as plugins
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.webutils as webutils
import supybot.callbacks as callbacks


def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Debian', True)
    if not utils.findBinaryInPath('zgrep'):
        if not advanced:
            output("""I can't find zgrep in your path.  This is necessary
                      to run the file command.  I'll disable this command
                      now.  When you get zgrep in your path, use the command
                      'enable Debian.file' to re-enable the command.""")
            capabilities = conf.supybot.capabilities()
            capabilities.add('-Debian.file')
            conf.supybot.capabilities.set(capabilities)
        else:
            output("""I can't find zgrep in your path.  If you want to run
                      the file command with any sort of expediency, you'll
                      need it.  You can use a python equivalent, but it's
                      about two orders of magnitude slower.  THIS MEANS IT
                      WILL TAKE AGES TO RUN THIS COMMAND.  Don't do this.""")
            if yn('Do you want to use a Python equivalent of zgrep?'):
                conf.supybot.plugins.Debian.pythonZgrep.setValue(True)
            else:
                output('I\'ll disable file now.')
                capabilities = conf.supybot.capabilities()
                capabilities.add('-Debian.file')
                conf.supybot.capabilities.set(capabilities)

conf.registerPlugin('Debian')
conf.registerGlobalValue(conf.supybot.plugins.Debian, 'pythonZgrep',
    registry.Boolean(False, """An advanced option, mostly just for testing;
    uses a Python-coded zgrep rather than the actual zgrep executable,
    generally resulting in a 50x slowdown.  What would take 2 seconds will
    take 100 with this enabled.  Don't enable this."""))
class Debian(callbacks.Privmsg,
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
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        plugins.PeriodicFileDownloader.__init__(self)

    def die(self):
        callbacks.Privmsg.die(self)

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
            regexp = regexp.rstrip('$')
            regexp = ".*%s.* " % regexp
        try:
            re_obj = re.compile(regexp, re.I)
        except re.error, e:
            irc.error("Error in regexp: %s" % e)
            return
        if self.registryValue('pythonZgrep'):
            fd = gzip.open(self.contents)
            r = imap(lambda tup: tup[0],
                     ifilter(lambda tup: tup[0],
                             imap(lambda line:(re_obj.search(line), line),fd)))
        else:
            try:
                (r, w) = popen2.popen4(['zgrep', '-ie', regexp, self.contents])
                w.close()
            except TypeError:
                # We're on Windows.
                irc.error('This command won\'t work on this platform.  '
                          'If you think it should (i.e., you know that '
                          'you have a zgrep binary somewhere) then file '
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
                    if hasattr(line, 'group'): # we're actually using
                        line = line.group(0)   # pythonZgrep  :(
                    (filename, pkg_list) = line.split()
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
    _debbrre = re.compile(r'<li><a href[^>]+>(.*?)</a> \(', _debreflags)
    _debverre = re.compile(r'<br>((?:\d+:)?\S+):', _debreflags)
    _deblistre = re.compile(r'<h3>Package ([^<]+)</h3>(.*?)</ul>', _debreflags)
    _debBranches = ('stable', 'testing', 'unstable', 'experimental')
    def version(self, irc, msg, args):
        """[--exact] [stable|testing|unstable|experimental] <package name>

        Returns the current version(s) of a Debian package in the given branch
        (if any, otherwise all available ones are displayed).  If --exact is
        specified, only packages whose name exactly matches <package name>
        will be reported.
        """
        url = 'http://packages.debian.org/cgi-bin/search_packages.pl?keywords'\
              '=%s&searchon=names&version=%s&release=all&subword=1'
        if not args:
            raise callbacks.ArgumentError
        (optlist, rest) = getopt.getopt(args, '', ['exact'])
        for (option, _) in optlist:
            if option == '--exact':
                url = url.replace('&subword=1','')
        if rest and rest[0] in self._debBranches:
            branch = rest.pop(0)
        else:
            branch = 'all'
        if not rest:
            irc.error('You must give a package name.')
            return
        responses = []
        package = privmsgs.getArgs(rest)
        if '*' in package:
            irc.error('Wildcard characters can not be specified.')
            return
        package = urllib.quote(package)
        url = url % (package, branch)
        try:
            html = webutils.getUrl(url)
        except webutils.WebError, e:
            irc.error('I couldn\'t reach the search page (%s).' % e)
            return

        if 'is down at the moment' in html:
            irc.error('Packages.debian.org is down at the moment.  '
                           'Please try again later.')
            return
        pkgs = self._deblistre.findall(html)
        #self.log.warning(pkgs)
        if not pkgs:
            irc.reply('No package found for %s (%s)' %
                      (urllib.unquote(package), branch))
        else:
            for pkg in pkgs:
                pkgMatch = pkg[0]
                soup = BeautifulSoup.BeautifulSoup()
                soup.feed(pkg[1])
                liBranches = soup.fetch('li')
                branches = []
                versions = []
                def branchVers(br):
                    vers = [b.next.string.strip() for b in br]
                    return [rsplit(v, ':', 1)[0] for v in vers]
                for li in liBranches:
                    branches.append(li.first('a').string)
                    versions.append(branchVers(li.fetch('br')))
                if branches and versions:
                    for pairs in  zip(branches, versions):
                        branch = pairs[0]
                        ver = ', '.join(pairs[1])
                        s = '%s (%s)' % (pkgMatch, ': '.join([branch, ver]))
                        responses.append(s)
            resp = '%s matches found: %s' % \
                   (len(responses), '; '.join(responses))
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
        globs = privmsgs.getArgs(rest).split()
        for glob in globs:
            glob = glob.replace('*', '.*').replace('?', '.?')
            predicates.append(re.compile(r'.*%s.*' % glob).search)
        packages = []
        try:
            fd = webutils.getUrlFd('http://incoming.debian.org/')
        except webutils.WebError, e:
            irc.error(str(e))
            return
        for line in fd:
            m = self._incomingRe.search(line)
            if m:
                name = m.group(1)
                if all(None, imap(lambda p: p(name), predicates)):
                    realname = rsplit(name, '_', 1)[0]
                    packages.append(realname)
        if len(packages) == 0:
            irc.error('No packages matched that search.')
        else:
            irc.reply(utils.commaAndify(packages))
    incoming = privmsgs.thread(incoming)

    _newpkgre = re.compile(r'<li><a href[^>]+>([^<]+)</a>')
    def new(self, irc, msg, args):
        """[--{main,contrib,non-free}] [<glob>]

        Checks for packages that have been added to Debian's unstable branch
        in the past week.  If no glob is specified, returns a list of all
        packages.  If no section is specified, defaults to main.
        """
        options = ['main', 'contrib', 'non-free']
        (optlist, rest) = getopt.getopt(args, '', options)
        section = 'main'
        for (option, _) in optlist:
            option = option.lstrip('-')
            if option in options:
                section = option
        glob = privmsgs.getArgs(rest, required=0, optional=1)
        if not glob:
            glob = '*'
        if '?' not in glob and '*' not in glob:
            glob = '*%s*' % glob
        try:
            fd = webutils.getUrlFd(
                'http://packages.debian.org/unstable/newpkg_%s' % section)
        except webutils.WebError, e:
            irc.error(str(e))
        packages = []
        #self.log.warning(section)
        #self.log.warning(glob)
        for line in fd:
            m = self._newpkgre.search(line)
            if m:
                m = m.group(1)
                if fnmatch.fnmatch(m, glob):
                    packages.append(m)
        fd.close()
        if packages:
            irc.reply(utils.commaAndify(packages))
        else:
            irc.error('No packages matched that search.')

    _severity = re.compile(r'.*(?:severity set to `([^\']+)\'|'
                           r'severity:\s+([^\s]+))', re.I)
    _package = re.compile(r'Package: <[^>]+>([^<]+)<', re.I | re.S)
    _reporter = re.compile(r'Reported by: <[^>]+>([^<]+)<', re.I | re.S)
    _subject = re.compile(r'<br>([^<]+)</h1>', re.I | re.S)
    _date = re.compile(r'Date: ([^;]+);', re.I | re.S)
    _searches = (_package, _subject, _reporter, _date)
    def bug(self, irc, msg, args):
        """<num>

        Returns a description of the bug with bug id <num>.
        """
        bug = privmsgs.getArgs(args)
        if ' ' in bug:
            irc.error('Only one bug can be looked up at a time.')
            return
        try:
            int(bug)
        except ValueError:
            irc.error('<num> must be an integer.')
            return
        url = 'http://bugs.debian.org/%s' % bug
        text = webutils.getUrl(url)
        if "There is no record of Bug" in text:
            irc.error('I could not find a bug report matching that number.')
            return
        searches = map(lambda p: p.search(text), self._searches)
        sev = self._severity.search(text)
        # This section should be cleaned up to ease future modifications
        if all(None, searches):
            resp = 'Package: %s; Subject: %s; Reported by %s on %s' %\
                tuple(map(utils.htmlToText,
                          map(lambda p: p.group(1), searches)))
            if sev:
                sev = filter(None, sev.groups())
                if sev:
                    resp = '; '.join([resp, 'Severity: %s' % sev[0],
                                      '<%s>' % url])
            irc.reply(resp)
        else:
            irc.reply('I was unable to properly parse the BTS page.')

Class = Debian

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
