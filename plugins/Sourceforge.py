#!/usr/bin/env python

###
# Copyright (c) 2003-2004, James Vega
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
Accesses Sourceforge.net for various things
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jamessan

import re
import sets
import getopt

from itertools import ifilter, imap

import supybot.registry as registry

import supybot.conf as conf
import supybot.utils as utils

import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.webutils as webutils
import supybot.callbacks as callbacks


def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Sourceforge', True)
    output("""The Sourceforge plugin has the functionality to watch for URLs
              that match a specific pattern (we call this a snarfer). When
              supybot sees such a URL, he will parse the web page for
              information and reply with the results.""")
    if yn('Do you want this snarfer to be enabled by default?'):
        conf.supybot.plugins.Sourceforge.trackerSnarfer.setValue(True)

    output("""The bugs and rfes commands of the Sourceforge plugin can be set
              to query a default project when no project is specified.  If this
              project is not set, calling either of those commands will display
              the associated help.  With the default project set, calling
              bugs/rfes with no arguments will find the most recent bugs/rfes
              for the default project.""")
    if yn('Do you want to specify a default project?'):
        project = anything('Project name:')
        if project:
            conf.supybot.plugins.Sourceforge.defaultProject.set(project)

    output("""Sourceforge is quite the word to type, and it may get annoying
              typing it all the time because Supybot makes you use the plugin
              name to disambiguate calls to ambiguous commands (i.e., the bug
              command is in this plugin and the Bugzilla plugin; if both are
              loaded, you\'ll have you type "sourceforge bug ..." to get this
              bug command).  You may save some time by making an alias for
              "sourceforge".  We like to make it "sf".""")

class TrackerError(Exception):
    pass

conf.registerPlugin('Sourceforge')
conf.registerChannelValue(conf.supybot.plugins.Sourceforge, 'trackerSnarfer',
    registry.Boolean(False, """Determines whether the bot will reply to SF.net
    Tracker URLs in the channel with a nice summary of the tracker item."""))
conf.registerChannelValue(conf.supybot.plugins.Sourceforge, 'defaultProject',
    registry.String('', """Sets the default project to use in the case that no
    explicit project is given."""))
conf.registerGlobalValue(conf.supybot.plugins.Sourceforge, 'bold',
    registry.Boolean(True, """Determines whether the results are bolded."""))

class Sourceforge(callbacks.PrivmsgCommandAndRegexp):
    """
    Module for Sourceforge stuff. Currently contains commands to query a
    project's most recent bugs and rfes.
    """
    threaded = True
    callBefore = ['URL']
    regexps = ['sfSnarfer']

    _reopts = re.I
    _infoRe = re.compile(r'<td nowrap>(\d+)</td><td><a href='
                         r'"([^"]+)">([^<]+)</a>', re.I)
    _hrefOpts = '&set=custom&_assigned_to=0&_status=%s&_category=100' \
                '&_group=100&order=artifact_id&sort=DESC'
    _resolution=re.compile(r'<b>(Resolution):</b> <a.+?<br>(.+?)</td>',_reopts)
    _assigned=re.compile(r'<b>(Assigned To):</b> <a.+?<br>(.+?)</td>', _reopts)
    _submitted = re.compile(r'<b>(Submitted By):</b><br>([^-]+) - '
                            r'(?:nobody|<a href)', _reopts)
    _submitDate = re.compile(r'<b>(Date Submitted):</b><br>([^<]+)</', _reopts)
    _priority = re.compile(r'<b>(Priority):</b> <a.+?<br>(.+?)</td>', _reopts)
    _status = re.compile(r'<b>(Status):</b> <a.+?<br>(.+?)</td>', _reopts)
    _regexps =(_resolution, _submitDate, _submitted, _assigned, _priority,
               _status)
    _statusOpt = {'any':100, 'open':1, 'closed':2, 'deleted':3, 'pending':4}

    _projectURL = 'http://sourceforge.net/projects/'
    _trackerURL = 'http://sourceforge.net/support/tracker.php?aid='
    def __init__(self):
        super(Sourceforge, self).__init__()
        self.__class__.sf = self.__class__.sourceforge

    def _formatResp(self, text, num=''):
        """
        Parses the Sourceforge query to return a list of tuples that
        contain the tracker information.
        """
        if num:
            for item in ifilter(lambda s, n=num: s and n in s,
                                self._infoRe.findall(text)):
                if self.registryValue('bold'):
                    yield (ircutils.bold(utils.htmlToText(item[2])),
                            utils.htmlToText(item[1]))
                else:
                    yield (utils.htmlToText(item[2]),
                            utils.htmlToText(item[1]))
        else:
            for item in ifilter(None, self._infoRe.findall(text)):
                if self.registryValue('bold'):
                    yield (ircutils.bold(item[0]), utils.htmlToText(item[2]))
                else:
                    yield (item[0], utils.htmlToText(item[2]))

    def _getTrackerURL(self, project, regex, status):
        """
        Searches the project's Summary page to find the proper tracker link.
        """
        try:
            text = webutils.getUrl('%s%s' % (self._projectURL, project))
            m = regex.search(text)
            if m is None:
                raise TrackerError, 'Invalid Tracker page'
            else:
                return 'http://sourceforge.net%s%s' % (utils.htmlToText(
                    m.group(1)), self._hrefOpts % self._statusOpt[status])
        except webutils.WebError, e:
            raise callbacks.Error, str(e)

    def _getTrackerList(self, url):
        """
        Searches the tracker list page and returns a list of the trackers.
        """
        try:
            text = webutils.getUrl(url)
            if "No matches found." in text:
                return 'No trackers were found.'
            head = '#%s: %s'
            resp = [head % entry for entry in self._formatResp(text)]
            if resp:
                if len(resp) > 10:
                    resp = imap(lambda s: utils.ellipsisify(s, 50), resp)
                return '%s' % utils.commaAndify(resp)
            raise callbacks.Error, 'No Trackers were found.  (%s)' % \
                  conf.supybot.replies.possibleBug()
        except webutils.WebError, e:
            raise callbacks.Error, str(e)

    _bold = lambda self, m: (ircutils.bold(m[0]),) + m[1:]
    _sfTitle = re.compile(r'Detail:(\d+) - ([^<]+)</title>', re.I)
    _linkType = re.compile(r'(\w+ \w+|\w+): Tracker Detailed View', re.I)
    def _getTrackerInfo(self, url):
        """
        Parses the specific tracker page, returning useful information.
        """
        try:
            bold = self.registryValue('bold')
            s = webutils.getUrl(url)
            resp = []
            head = ''
            m = self._linkType.search(s)
            n = self._sfTitle.search(s)
            if m and n:
                linktype = m.group(1)
                linktype = utils.depluralize(linktype)
                (num, desc) = n.groups()
                if bold:
                    head = '%s #%s: %s' % (ircutils.bold(linktype), num, desc)
                else:
                    head = '%s #%s: %s' % (linktype, num, desc)
                resp.append(head)
            else:
                return None
            for r in self._regexps:
                m = r.search(s)
                if m:
                    if bold:
                        resp.append('%s: %s' % self._bold(m.groups()))
                    else:
                        resp.append('%s: %s' % m.groups())
            return '; '.join(resp)
        except webutils.WebError, e:
            raise TrackerError, str(e)

    def tracker(self, irc, msg, args):
        """<num>

        Returns a description of the tracker with Tracker id <num> and the
        corresponding Tracker url.
        """
        num = privmsgs.getArgs(args)
        try:
            url = '%s%s' % (self._trackerURL, num)
            resp = self._getTrackerInfo(url)
            if resp is None:
                irc.error('Invalid Tracker page snarfed: %s' % url)
            else:
                irc.reply('%s <%s>' % (resp, url))
        except TrackerError, e:
            irc.error(str(e))

    _trackerLink = {'bugs': re.compile(r'"([^"]+)">Bugs'),
                    'rfes': re.compile(r'"([^"]+)">RFE'),
                    'patches': re.compile(r'"([^"]+)">Patches'),
                   }
    def _trackers(self, irc, args, msg, tracker):
        (optlist, rest) = getopt.getopt(args, '', self._statusOpt.keys())
        project = privmsgs.getArgs(rest, required=0, optional=1)
        status = 'open'
        for (option, _) in optlist:
            option = option.lstrip('-').lower()
            if option in self._statusOpt:
                status = option
        try:
            int(project)
            s = 'Use the tracker command to get information about a specific'\
                ' tracker.'
            irc.error(s)
            return
        except ValueError:
            pass
        if not project:
            project = self.registryValue('defaultProject', msg.args[0])
            if not project:
                raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._trackerLink[tracker],
                                      status)
        except TrackerError, e:
            irc.error('%s.  I can\'t find the %s link.' %
                      (e, tracker.capitalize()))
            return
        irc.reply(self._getTrackerList(url))

    def bugs(self, irc, msg, args):
        """[--{any,open,closed,deleted,pending}] [<project>]

        Returns a list of the most recent bugs filed against <project>.
        <project> is not needed if there is a default project set.  Search
        defaults to open bugs.
        """
        self._trackers(irc, args, msg, 'bugs')

    def rfes(self, irc, msg, args):
        """[--{any,open,closed,deleted,pending}] [<project>]

        Returns a list of the most recent rfes filed against <project>.
        <project> is not needed if there is a default project set.  Search
        defaults to open rfes.
        """
        self._trackers(irc, args, msg, 'rfes')

    def patches(self, irc, msg, args):
        """[--{any,open,closed,deleted,pending}] [<project>]

        Returns a list of the most recent patches filed against <project>.
        <project> is not needed if there is a default project set.  Search
        defaults to open patches.
        """
        self._trackers(irc, args, msg, 'patches')

    _totbugs = re.compile(r'Bugs</a>\s+?\( <b>([^<]+)</b>', re.S | re.I)
    def _getNumBugs(self, project):
        text = webutils.getUrl('%s%s' % (self._projectURL, project))
        m = self._totbugs.search(text)
        if m:
            return m.group(1)
        else:
            return ''

    _totrfes = re.compile(r'Feature Requests</a>\s+?\( <b>([^<]+)</b>',
                          re.S | re.I)
    def _getNumRfes(self, project):
        text = webutils.getUrl('%s%s' % (self._projectURL, project))
        m = self._totrfes.search(text)
        if m:
            return m.group(1)
        else:
            return ''

    def total(self, irc, msg, args):
        """{bugs,rfes} [<project>]

        Returns the total count of open bugs or rfes.  <project> is only
        necessary if a default project is not set.
        """
        if not args:
            raise callbacks.ArgumentError
        type = args.pop(0)
        if type == 'bugs':
            self._totalbugs(irc, msg, args)
        elif type == 'rfes':
            self._totalrfes(irc, msg, args)
        else:
            raise callbacks.ArgumentError

    def _totalbugs(self, irc, msg, args):
        """[<project>]

        Returns a count of the open/total bugs.  <project> is not needed if a
        default project is set.
        """
        project = privmsgs.getArgs(args, required=0, optional=1)
        project = project or self.registryValue('defaultProject', msg.args[0])
        if not project:
            raise callbacks.ArgumentError
        total = self._getNumBugs(project)
        if total:
            irc.reply(total)
        else:
            irc.error('Could not find bug statistics.')

    def _totalrfes(self, irc, msg, args):
        """[<project>]

        Returns a count of the open/total RFEs.  <project> is not needed if a
        default project is set.
        """
        project = privmsgs.getArgs(args, required=0, optional=1)
        project = project or self.registryValue('defaultProject', msg.args[0])
        if not project:
            raise callbacks.ArgumentError
        total = self._getNumRfes(project)
        if total:
            irc.reply(total)
        else:
            irc.error('Could not find RFE statistics.')

    def fight(self, irc, msg, args):
        """[--{bugs,rfes}] [--{open,closed}] <project name> <project name>

        Returns the projects, in order, from greatest number of bugs to least.
        Defaults to bugs and open.
        """
        search = self._getNumBugs
        type = 0
        (optlist, rest) = getopt.getopt(args, '',
                                        ['bugs', 'rfes', 'open', 'closed'])
        for (option, _) in optlist:
            if option == '--bugs':
                search = self._getNumBugs
            if option == '--rfes':
                search = self._getNumRfes
            if option == '--open':
                type = 0
            if option == '--closed':
                type = 1
        results = []
        for proj in args:
            num = search(proj)
            if num:
                results.append((int(num.split('/')[type].split()[0]), proj))
        results.sort()
        results.reverse()
        s = ', '.join(['\'%s\': %s' % (s, i) for (i, s) in results])
        irc.reply(s)

    def sfSnarfer(self, irc, msg, match):
        r"https?://(?:www\.)?(?:sourceforge|sf)\.net/tracker/" \
        r".*\?(?:&?func=detail|&?aid=\d+|&?group_id=\d+|&?atid=\d+){4}"
        if not self.registryValue('trackerSnarfer', msg.args[0]):
            return
        try:
            url = match.group(0)
            resp = self._getTrackerInfo(url)
            if resp is None:
                self.log.warning('Invalid Tracker page snarfed: %s', url)
            else:
                irc.reply(resp, prefixName=False)
        except TrackerError, e:
            self.log.warning(str(e))
    sfSnarfer = privmsgs.urlSnarfer(sfSnarfer)

Class = Sourceforge

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
