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
Provides several commands that go out to websites and get things.
"""

__revision__ = "$Id$"

import plugins

import re
import sets
import getopt
import socket
import urllib
import urllib2
import xml.dom.minidom
from itertools import imap, ifilter

import conf
import utils
import webutils
import privmsgs
import callbacks

class FreshmeatException(Exception):
    pass

class Http(callbacks.Privmsg):
    threaded = True
    maxSize = 4096
    _titleRe = re.compile(r'<title>(.*?)</title>', re.I | re.S)
    def callCommand(self, method, irc, msg, *L):
        try:
            callbacks.Privmsg.callCommand(self, method, irc, msg, *L)
        except webutils.WebError, e:
            irc.error(str(e))
            
    def headers(self, irc, msg, args):
        """<url>

        Returns the HTTP headers of <url>.  Only HTTP urls are valid, of
        course.
        """
        url = privmsgs.getArgs(args)
        if not url.startswith('http://'):
            irc.error('Only HTTP urls are valid.')
            return
        fd = webutils.getUrlFd(url)
        s = ', '.join(['%s: %s' % (k, v) for (k, v) in fd.headers.items()])
        irc.reply(s)
            
    _doctypeRe = re.compile(r'(<!DOCTYPE[^>]+>)', re.M)
    def doctype(self, irc, msg, args):
        """<url>

        Returns the DOCTYPE string of <url>.  Only HTTP urls are valid, of
        course.
        """
        url = privmsgs.getArgs(args)
        if not url.startswith('http://'):
            irc.error('Only HTTP urls are valid.')
            return
        s = webutils.getUrl(url, size=self.maxSize)
        m = self._doctypeRe.search(s)
        if m:
            s = utils.normalizeWhitespace(m.group(0))
            irc.reply('%s has the following doctype: %s' % (url, s))
        else:
            irc.reply('%s has no specified doctype.' % url)
            
    def size(self, irc, msg, args):
        """<url>

        Returns the Content-Length header of <url>.  Only HTTP urls are valid,
        of course.
        """
        url = privmsgs.getArgs(args)
        if not url.startswith('http://'):
            irc.error('Only HTTP urls are valid.')
            return
        fd = webutils.getUrlFd(url)
        try:
            size = fd.headers['Content-Length']
            irc.reply('%s is %s bytes long.' % (url, size))
        except KeyError:
            s = fd.read(self.maxSize)
            if len(s) != self.maxSize:
                irc.reply('%s is %s bytes long.' % (url, len(s)))
            else:
                irc.reply('The server didn\'t tell me how long %s is '
                               'but it\'s longer than %s bytes.' %
                               (url,self.maxSize))

    def title(self, irc, msg, args):
        """<url>

        Returns the HTML <title>...</title> of a URL.
        """
        url = privmsgs.getArgs(args)
        if '://' not in url:
            url = 'http://%s' % url
        text = webutils.getUrl(url, size=self.maxSize)
        m = self._titleRe.search(text)
        if m is not None:
            irc.reply(utils.htmlToText(m.group(1).strip()))
        else:
            irc.reply('That URL appears to have no HTML title '
                           'within the first %s bytes.' % self.maxSize)

    def freshmeat(self, irc, msg, args):
        """<project name>

        Returns Freshmeat data about a given project.
        """
        project = privmsgs.getArgs(args)
        project = ''.join(project.split())
        url = 'http://www.freshmeat.net/projects-xml/%s' % project
        try:
            text = webutils.getUrl(url)
            if text.startswith('Error'):
                text = text.split(None, 1)[1]
                raise FreshmeatException, text
            dom = xml.dom.minidom.parseString(text)
            def getNode(name):
                node = dom.getElementsByTagName(name)[0]
                return str(node.childNodes[0].data)
            project = getNode('projectname_full')
            version = getNode('latest_release_version')
            vitality = getNode('vitality_percent')
            popularity = getNode('popularity_percent')
            lastupdated = getNode('date_updated')
            irc.reply('%s, last updated %s, with a vitality percent of %s '
                      'and a popularity of %s, is in version %s.' %
                      (project, lastupdated, vitality, popularity, version))
        except FreshmeatException, e:
            irc.error(str(e))

    def stockquote(self, irc, msg, args):
        """<company symbol>

        Gets the information about the current price and change from the
        previous day of a given compny (represented by a stock symbol).
        """
        symbol = privmsgs.getArgs(args)
        url = 'http://finance.yahoo.com/d/quotes.csv?s=%s' \
              '&f=sl1d1t1c1ohgv&e=.csv' % symbol
        quote = webutils.getUrl(url)
        data = quote.split(',')
        if data[1] != '0.00':
            irc.reply('The current price of %s is %s, as of %s EST.  '
                      'A change of %s from the last business day.' %
                      (data[0][1:-1], data[1], data[3][1:-1], data[4]))
        else:
            m = 'I couldn\'t find a listing for %s' % symbol
            irc.error(m)

    _mlgeekquotere = re.compile('<p class="qt">(.*?)</p>', re.M | re.DOTALL)
    def geekquote(self, irc, msg, args):
        """[<id>]

        Returns a random geek quote from bash.org; the optional argument
        id specifies which quote to retrieve.
        """
        id = privmsgs.getArgs(args, required=0, optional=1)
        id = id or 'random1'
        html = webutils.getUrl('http://bash.org/?%s' % id)
        m = self._mlgeekquotere.search(html)
        if m is None:
            irc.error('No quote found.')
            return
        quote = utils.htmlToText(m.group(1))
        quote = ' // '.join(quote.splitlines())
        irc.reply(quote)

    _cyborgRe = re.compile(r'<p class="mediumheader">(.*?)</p>', re.I)
    def cyborg(self, irc, msg, args):
        """<name>

        Returns a cyborg acronym for <name> from <http://www.cyborgname.com/>.
        """
        name = privmsgs.getArgs(args)
        name = urllib.quote(name)
        url = 'http://www.cyborgname.com/cyborger.cgi?acronym=%s' % name
        html = webutils.getUrl(url)
        m = self._cyborgRe.search(html)
        if m:
            irc.reply(m.group(1))
        else:
            irc.errorPossibleBug('No cyborg name returned.')
        
    _acronymre = re.compile(r'valign="middle" width="7\d%" bgcolor="[^"]+">'
                            r'(?:<b>)?([^<]+)')
    def acronym(self, irc, msg, args):
        """<acronym>

        Displays acronym matches from acronymfinder.com
        """
        acronym = privmsgs.getArgs(args)
        url = 'http://www.acronymfinder.com/' \
              'af-query.asp?String=exact&Acronym=%s' % urllib.quote(acronym)
        request = urllib2.Request(url, headers={'User-agent':
          'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 4.0)'})
        html = webutils.getUrl(request)
        if 'daily limit' in html:
            s = 'Acronymfinder.com says I\'ve reached my daily limit.  Sorry.'
            irc.error(s)
            return
        # The following definitions are stripped and empties are removed.
        defs = filter(None, imap(str.strip, self._acronymre.findall(html)))
        utils.sortBy(lambda s: not s.startswith('[not an acronym]'), defs)
        for (i, s) in enumerate(defs):
            if s.startswith('[not an acronym]'):
                defs[i] = s.split('is ', 1)[1]
        if len(defs) == 0:
            irc.reply('No definitions found.')
        else:
            s = ', or '.join(defs)
            irc.reply('%s could be %s' % (acronym, s))

    _netcraftre = re.compile(r'whatos text -->(.*?)<a href="/up/acc', re.S)
    def netcraft(self, irc, msg, args):
        """<hostname|ip>

        Returns Netcraft.com's determination of what operating system and
        webserver is running on the host given.
        """
        hostname = privmsgs.getArgs(args)
        url = 'http://uptime.netcraft.com/up/graph/?host=%s' % hostname
        html = webutils.getUrl(url)
        m = self._netcraftre.search(html)
        if m:
            html = m.group(1)
            s = utils.htmlToText(html, tagReplace='').strip('\xa0 ')
            irc.reply(s[9:]) # Snip off "the site"
        elif 'We could not get any results' in html:
            irc.reply('No results found for %s.' % hostname)
        else:
            irc.error('The format of page the was odd.')

    def kernel(self, irc, msg, args):
        """takes no arguments

        Returns information about the current version of the Linux kernel.
        """
        try:
            fd = webutils.getUrlFd('http://kernel.org/kdist/finger_banner')
            stable = 'unknown'
            beta = 'unknown'
            for line in fd:
                (name, version) = line.split(':')
                if 'latest stable' in name:
                    stable = version.strip()
                elif 'latest beta' in name:
                    beta = version.strip()
        finally:
            fd.close()
        irc.reply('The latest stable kernel is %s; '
                  'the latest beta kernel is %s.' % (stable, beta))

    _pgpkeyre = re.compile(r'pub\s+\d{4}\w/<a href="([^"]+)">'
                           r'([^<]+)</a>[^>]+>([^<]+)</a>')
    def pgpkey(self, irc, msg, args):
        """<search words>

        Returns the results of querying pgp.mit.edu for keys that match
        the <search words>.
        """
        search = privmsgs.getArgs(args)
        urlClean = search.replace(' ', '+')
        host = 'http://pgp.mit.edu:11371'
        url = '%s/pks/lookup?op=index&search=%s' % (host, urlClean)
        try:
            L = []
            fd = webutils.getUrlFd(url)
            for line in iter(fd.next, ''):
                info = self._pgpkeyre.search(line)
                if info:
                    L.append('%s <%s%s>' % (info.group(3),host,info.group(1)))
            if len(L) == 0:
                irc.reply('No results found for %s.' % search)
            else:
                s = 'Matches found for %s: %s' % (search, ' :: '.join(L))
                irc.reply(s)
        finally:
            fd.close()

    _filextre = re.compile(
        r'<strong>Extension:</strong>.*?<tr>.*?</tr>\s+<tr>\s+<td colspan='
        r'"2">(?:<a href[^>]+>([^<]+)</a>\s+|([^<]+))</td>\s+<td>'
        r'(?:<a href[^>]+>([^<]+)</a>|<img src="images/spacer.gif"(.))',
        re.I|re.S)
    def extension(self, irc, msg, args):
        """<ext>

        Returns the results of querying filext.com for file extenstions that
        match <ext>.
        """
        ext = privmsgs.getArgs(args)
        invalid = '|<>\^=?/[]";,*'
        for c in invalid:
            if c in ext:
                irc.error('\'%s\' is an invalid extension character' % c)
                return
        s = 'http://www.filext.com/detaillist.php?extdetail=%s&goButton=Go'
        text = webutils.getUrl(s % ext)
        matches = self._filextre.findall(text)
        #print matches
        res = []
        for match in matches:
            (file1, file2, comp1, comp2) = match
            if file1:
                filetype = file1.strip()
            else:
                filetype = file2.strip()
            if comp1:
                company = comp1.strip()
            else:
                company = comp2.strip()
            if company:
                res.append('%s\'s %s' % (company, filetype))
            else:
                res.append(filetype)
        if res:
            irc.reply(utils.commaAndify(res))
        else:
            irc.error('No matching file extenstions were found.')

Class = Http

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
