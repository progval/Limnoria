###
# Copyright (c) 2003-2005, James Vega
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

import os
import re
import gzip
import time
import popen2
import fnmatch
import threading

import BeautifulSoup

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.utils.iter import all, imap, ifilter

class PeriodicFileDownloader(object):
    """A class to periodically download a file/files.

    A class-level dictionary 'periodicFiles' maps names of files to
    three-tuples of
    (url, seconds between downloads, function to run with downloaded file).

    'url' should be in some form that urllib2.urlopen can handle (do note that
    urllib2.urlopen handles file:// links perfectly well.)

    'seconds between downloads' is the number of seconds between downloads,
    obviously.  An important point to remember, however, is that it is only
    engaged when a command is run.  I.e., if you say you want the file
    downloaded every day, but no commands that use it are run in a week, the
    next time such a command is run, it'll be using a week-old file.  If you
    don't want such behavior, you'll have to give an error mess age to the user
    and tell him to call you back in the morning.

    'function to run with downloaded file' is a function that will be passed
    a string *filename* of the downloaded file.  This will be some random
    filename probably generated via some mktemp-type-thing.  You can do what
    you want with this; you may want to build a database, take some stats,
    or simply rename the file.  You can pass None as your function and the
    file with automatically be renamed to match the filename you have it listed
    under.  It'll be in conf.supybot.directories.data, of course.

    Aside from that dictionary, simply use self.getFile(filename) in any method
    that makes use of a periodically downloaded file, and you'll be set.
    """
    periodicFiles = None
    def __init__(self, *args, **kwargs):
        if self.periodicFiles is None:
            raise ValueError, 'You must provide files to download'
        self.lastDownloaded = {}
        self.downloadedCounter = {}
        for filename in self.periodicFiles:
            if self.periodicFiles[filename][-1] is None:
                fullname = os.path.join(conf.supybot.directories.data(),
                                        filename)
                if os.path.exists(fullname):
                    self.lastDownloaded[filename] = os.stat(fullname).st_ctime
                else:
                    self.lastDownloaded[filename] = 0
            else:
                self.lastDownloaded[filename] = 0
            self.currentlyDownloading = set()
            self.downloadedCounter[filename] = 0
            self.getFile(filename)
        super(PeriodicFileDownloader, self).__init__(*args, **kwargs)

    def _downloadFile(self, filename, url, f):
        self.currentlyDownloading.add(filename)
        try:
            try:
                infd = utils.web.getUrlFd(url)
            except IOError, e:
                self.log.warning('Error downloading %s: %s', url, e)
                return
            except utils.web.Error, e:
                self.log.warning('Error downloading %s: %s', url, e)
                return
            confDir = conf.supybot.directories.data()
            newFilename = os.path.join(confDir, utils.file.mktemp())
            outfd = file(newFilename, 'wb')
            start = time.time()
            s = infd.read(4096)
            while s:
                outfd.write(s)
                s = infd.read(4096)
            infd.close()
            outfd.close()
            self.log.info('Downloaded %s in %s seconds',
                          filename, time.time()-start)
            self.downloadedCounter[filename] += 1
            self.lastDownloaded[filename] = time.time()
            if f is None:
                toFilename = os.path.join(confDir, filename)
                if os.name == 'nt':
                    # Windows, grrr...
                    if os.path.exists(toFilename):
                        os.remove(toFilename)
                os.rename(newFilename, toFilename)
            else:
                start = time.time()
                f(newFilename)
                total = time.time() - start
                self.log.info('Function ran on %s in %s seconds',
                              filename, total)
        finally:
            self.currentlyDownloading.remove(filename)

    def getFile(self, filename):
        if world.documenting:
            return
        (url, timeLimit, f) = self.periodicFiles[filename]
        if time.time() - self.lastDownloaded[filename] > timeLimit and \
           filename not in self.currentlyDownloading:
            self.log.info('Beginning download of %s', url)
            args = (filename, url, f)
            name = '%s #%s' % (filename, self.downloadedCounter[filename])
            t = threading.Thread(target=self._downloadFile, name=name,
                                 args=(filename, url, f))
            t.setDaemon(True)
            t.start()
            world.threadsSpawned += 1


class Debian(callbacks.Plugin, PeriodicFileDownloader):
    threaded = True
    periodicFiles = {
        # This file is only updated once a week, so there's no sense in
        # downloading a new one every day.
        'Contents-i386.gz': ('ftp://ftp.us.debian.org/'
                             'debian/dists/unstable/Contents-i386.gz',
                             604800, None)
        }
    contents = conf.supybot.directories.data.dirize('Contents-i386.gz')
    def file(self, irc, msg, args, optlist, glob):
        """[--{regexp,exact} <value>] [<glob>]

        Returns packages in Debian that includes files matching <glob>. If
        --regexp is given, returns packages that include files matching the
        given regexp.  If --exact is given, returns packages that include files
        matching exactly the string given.
        """
        self.getFile('Contents-i386.gz')
        # Make sure it's anchored, make sure it doesn't have a leading slash
        # (the filenames don't have leading slashes, and people may not know
        # that).
        if not optlist and not glob:
            raise callbacks.ArgumentError
        if optlist and glob:
            irc.error('You must specify either a glob or a regexp/exact '
                      'search, but not both.', Raise=True)
        for (option, arg) in optlist:
            if option == 'exact':
                regexp = arg.lstrip('/')
            elif option == 'regexp':
                regexp = arg
        if glob:
            regexp = fnmatch.translate(glob.lstrip('/'))
            regexp = regexp.rstrip('$')
            regexp = ".*%s.* " % regexp
        try:
            re_obj = re.compile(regexp, re.I)
        except re.error, e:
            irc.error(format('Error in regexp: %s', e), Raise=True)
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
                          'If you think it should (i.e., you know that you '
                          'have a zgrep binary somewhere) then file a bug '
                          'about it at http://supybot.sf.net/ .', Raise=True)
        packages = set()  # Make packages unique
        try:
            for line in r:
                if len(packages) > 100:
                    irc.error('More than 100 packages matched, '
                              'please narrow your search.', Raise=True)
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
            irc.reply(format('%L', sorted(packages)))
    file = wrap(file, [getopts({'regexp':'regexpMatcher','exact':'something'}),
                       additional('glob')])

    _debreflags = re.DOTALL | re.IGNORECASE
    _deblistre = re.compile(r'<h3>Package ([^<]+)</h3>(.*?)</ul>', _debreflags)
    def version(self, irc, msg, args, optlist, branch, package):
        """[--exact] [{stable,testing,unstable,experimental}] <package name>

        Returns the current version(s) of a Debian package in the given branch
        (if any, otherwise all available ones are displayed).  If --exact is
        specified, only packages whose name exactly matches <package name>
        will be reported.
        """
        url = 'http://packages.debian.org/cgi-bin/search_packages.pl?keywords'\
              '=%s&searchon=names&version=%s&release=all&subword=1'
        for (option, _) in optlist:
            if option == 'exact':
                url = url.replace('&subword=1','')
        responses = []
        if '*' in package:
            irc.error('Wildcard characters can not be specified.', Raise=True)
        package = utils.web.urlquote(package)
        url %= (package, branch)
        try:
            html = utils.web.getUrl(url)
        except utils.web.Error, e:
            irc.error(format('I couldn\'t reach the search page (%s).', e),
                      Raise=True)
        if 'is down at the moment' in html:
            irc.error('Packages.debian.org is down at the moment.  '
                      'Please try again later.', Raise=True)
        pkgs = self._deblistre.findall(html)
        if not pkgs:
            irc.reply(format('No package found for %s (%s)',
                      utils.web.urlunquote(package), branch))
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
                    return [utils.str.rsplit(v, ':', 1)[0] for v in vers]
                for li in liBranches:
                    branches.append(li.a.string)
                    versions.append(branchVers(li.fetch('br')))
                if branches and versions:
                    for pairs in  zip(branches, versions):
                        branch = pairs[0]
                        ver = ', '.join(pairs[1])
                        s = format('%s (%s)', pkgMatch,
                                   ': '.join([branch, ver]))
                        responses.append(s)
            resp = format('%i matches found: %s',
                          len(responses), '; '.join(responses))
            irc.reply(resp)
    version = wrap(version, [getopts({'exact':''}),
                             optional(('literal', ('stable', 'testing',
                                       'unstable', 'experimental')), 'all'),
                             'text'])

    _incomingRe = re.compile(r'<a href="(.*?\.deb)">', re.I)
    def incoming(self, irc, msg, args, optlist, globs):
        """[--{regexp,arch} <value>] [<glob> ...]

        Checks debian incoming for a matching package name.  The arch
        parameter defaults to i386; --regexp returns only those package names
        that match a given regexp, and normal matches use standard *nix
        globbing.
        """
        predicates = []
        archPredicate = lambda s: ('_i386.' in s)
        for (option, arg) in optlist:
            if option == 'regexp':
                predicates.append(r.search)
            elif option == 'arch':
                arg = '_%s.' % arg
                archPredicate = lambda s, arg=arg: (arg in s)
        predicates.append(archPredicate)
        for glob in globs:
            glob = fnmatch.translate(glob)
            predicates.append(re.compile(glob).search)
        packages = []
        try:
            fd = utils.web.getUrlFd('http://incoming.debian.org/')
        except utils.web.Error, e:
            irc.error(str(e), Raise=True)
        for line in fd:
            m = self._incomingRe.search(line)
            if m:
                name = m.group(1)
                if all(None, imap(lambda p: p(name), predicates)):
                    realname = utils.str.rsplit(name, '_', 1)[0]
                    packages.append(realname)
        if len(packages) == 0:
            irc.error('No packages matched that search.')
        else:
            irc.reply(format('%L', packages))
    incoming = thread(wrap(incoming,
                           [getopts({'regexp': 'regexpMatcher',
                                     'arch': 'something'}),
                            any('glob')]))

    def bold(self, s):
        if self.registryValue('bold', dynamic.channel):
            return ircutils.bold(s)
        return s

    _update = re.compile(r' : ([^<]+)</body', re.I)
    def stats(self, irc, msg, args, pkg):
        """<source package>

        Reports various statistics (from http://packages.qa.debian.org/) about
        <source package>.
        """
        pkg = pkg.lower()
        text = utils.web.getUrl('http://packages.qa.debian.org/%s/%s.html' %
                                (pkg[0], pkg))
        if "Error 404" in text:
            irc.errorInvalid('source package name')
        updated = None
        m = self._update.search(text)
        if m:
            updated = m.group(1)
        soup = BeautifulSoup.BeautifulSoup()
        soup.feed(text)
        pairs = zip(soup.fetch('td', {'class': 'labelcell'}),
                    soup.fetch('td', {'class': 'contentcell'}))
        for (label, content) in pairs:
            if label.string == 'Last version':
                version = '%s: %s' % (self.bold(label.string), content.string)
            elif label.string == 'Maintainer':
                name = content.a.string
                email = content.fetch('a')[1]['href'][7:]
                maintainer = format('%s: %s %u', self.bold('Maintainer'),
                                    name, utils.web.mungeEmail(email))
            elif label.string == 'All bugs':
                bugsAll = format('%i Total', content.first('a').string)
            elif label.string == 'Release Critical':
                bugsRC = format('%i RC', content.first('a').string)
            elif label.string == 'Important and Normal':
                bugs = format('%i Important/Normal',
                              content.first('a').string)
            elif label.string == 'Minor and Wishlist':
                bugsMinor = format('%i Minor/Wishlist',
                                   content.first('a').string)
            elif label.string == 'Fixed and Pending':
                bugsFixed = format('%i Fixed/Pending',
                                   content.first('a').string)
            elif label.string == 'Subscribers count':
                subscribers = format('%s: %i',
                                     self.bold('Subscribers'), content.string)
        bugL = (bugsAll, bugsRC, bugs, bugsMinor, bugsFixed)
        s = '.  '.join((version, maintainer, subscribers,
                        '%s: %s' % (self.bold('Bugs'), '; '.join(bugL))))
        if updated:
            s = 'As of %s, %s' % (updated, s)
        irc.reply(s)
    stats = wrap(stats, ['somethingWithoutSpaces'])

    _newpkgre = re.compile(r'<li><a href[^>]+>([^<]+)</a>')
    def new(self, irc, msg, args, section, glob):
        """[{main,contrib,non-free}] [<glob>]

        Checks for packages that have been added to Debian's unstable branch
        in the past week.  If no glob is specified, returns a list of all
        packages.  If no section is specified, defaults to main.
        """
        try:
            fd = utils.web.getUrlFd(
                'http://packages.debian.org/unstable/newpkg_%s' % section)
        except utils.web.Error, e:
            irc.error(str(e), Raise=True)
        packages = []
        for line in fd:
            m = self._newpkgre.search(line)
            if m:
                m = m.group(1)
                if fnmatch.fnmatch(m, glob):
                    packages.append(m)
        fd.close()
        if packages:
            irc.reply(format('%L', packages))
        else:
            irc.error('No packages matched that search.')
    new = wrap(new, [optional(('literal', ('main', 'contrib', 'non-free')),
                              'main'),
                     additional('glob', '*')])

    _severity = re.compile(r'.*(?:severity set to `([^\']+)\'|'
                           r'severity:\s+<em>([^<]+)</em>)', re.I)
    _package = re.compile(r'Package: <[^>]+>([^<]+)<', re.I | re.S)
    _reporter = re.compile(r'Reported by: <[^>]+>([^<]+)<', re.I | re.S)
    _subject = re.compile(r'<br>([^<]+)</h1>', re.I | re.S)
    _date = re.compile(r'Date: ([^;]+);', re.I | re.S)
    _tags = re.compile(r'Tags: <strong>([^<]+)</strong>', re.I)
    _searches = (_package, _subject, _reporter, _date)
    def bug(self, irc, msg, args, bug):
        """<num>

        Returns a description of the bug with bug id <num>.
        """
        url = 'http://bugs.debian.org/%s' % bug
        try:
            text = utils.web.getUrl(url)
        except utils.web.Error, e:
            irc.error(str(e), Raise=True)
        if "There is no record of Bug" in text:
            irc.error('I could not find a bug report matching that number.',
                      Raise=True)
        searches = map(lambda p: p.search(text), self._searches)
        sev = self._severity.search(text)
        tags = self._tags.search(text)
        # This section should be cleaned up to ease future modifications
        if all(None, searches):
            L = map(self.bold, ('Package', 'Subject', 'Reported'))
            resp = format('%s: %%s; %s: %%s; %s: by %%s on %%s', *L)
            L = map(utils.web.htmlToText, map(lambda p: p.group(1), searches))
            resp = format(resp, *L)
            if sev:
                sev = filter(None, sev.groups())
                if sev:
                    sev = utils.web.htmlToText(sev[0])
                    resp += format('; %s: %s', self.bold('Severity'), sev)
            if tags:
                resp += format('; %s: %s', self.bold('Tags'), tags.group(1))
            resp += format('; %u', url)
            irc.reply(resp)
        else:
            irc.reply('I was unable to properly parse the BTS page.')
    bug = wrap(bug, [('id', 'bug')])

    _dpnRe = re.compile(r'"\+2">([^<]+)</font', re.I)
    def debianize(self, irc, msg, args, words):
        """<text>

        Turns <text> into a 'debian package name' using
        http://www.pigdog.com/features/dpn.html.
        """
        url = r'http://www.pigdog.org/cgi_bin/dpn.phtml?name=%s'
        try:
            text = utils.web.getUrl(url % '+'.join(words))
        except utils.web.Error, e:
            irc.error(str(e), Raise=True)
        m = self._dpnRe.search(text)
        if m is not None:
            irc.reply(m.group(1))
        else:
            irc.errorPossibleBug('Unable to parse webpage.')
    debianize = wrap(debianize, [many('something')])


Class = Debian


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
