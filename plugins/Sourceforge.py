#!/usr/bin/env python

###
# Copyright (c) 2003, James Vega
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

import re
import sets
import getopt

from itertools import ifilter, imap

import registry

import conf
import utils
__revision__ = "$Id$"

import plugins
import ircutils
import privmsgs
import webutils
import callbacks


def configure(onStart):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    conf.registerPlugin('Sourceforge', True)
    print 'The Sourceforge plugin has the functionality to watch for URLs'
    print 'that match a specific pattern (we call this a snarfer). When'
    print 'supybot sees such a URL, he will parse the web page for'
    print 'information and reply with the results.\n'
    if yn('Do you want this snarfer to be enabled by default?') == 'y':
        conf.supybot.plugins.Sourceforge.trackerSnarfer.setValue(True)

    print 'The bugs and rfes commands of the Sourceforge plugin can be set'
    print 'to query a default project when no project is specified.  If this'
    print 'project is not set, calling either of those commands will display'
    print 'the associated help.  With the default project set, calling'
    print 'bugs/rfes with no arguments will find the most recent bugs/rfes'
    print 'for the default project.\n'
    if yn('Do you want to specify a default project?') == 'y':
        project = anything('Project name:')
        if project:
            conf.supybot.plugins.Sourceforge.project.set(project)

    print 'Sourceforge is quite the word to type, and it may get annoying'
    print 'typing it all the time because Supybot makes you use the plugin'
    print 'name to disambiguate calls to ambiguous commands (i.e., the bug'
    print 'command is in this plugin and the Bugzilla plugin; if both are'
    print 'loaded, you\'ll have you type "sourceforge bug ..." to get this'
    print 'bug command).  You may save some time by making an alias for'
    print '"sourceforge".  We like to make it "sf".'
    if yn('Would you like to add sf as an alias for Sourceforge?') == 'y':
        if not conf.supybot.plugins.Alias():
            print 'This depends on the Alias module.'
            if yn('Would you like to load the Alias plugin now?') == 'y':
                conf.registerPlugin('Alias', True)
            else:
                print 'Then I can\'t add such an alias.'
                return
        onStart.append('alias add sf sourceforge $*')

class TrackerError(Exception):
    pass

conf.registerPlugin('Sourceforge')
conf.registerChannelValue(conf.supybot.plugins.Sourceforge, 'trackerSnarfer',
    registry.Boolean(False, """Determines whether the bot will reply to SF.net
    Tracker URLs in the channel with a nice summary of the tracker item."""))
conf.registerChannelValue(conf.supybot.plugins.Sourceforge, 'project',
    registry.String('', """Sets the default project to use in the case that no
    explicit project is given."""))

class Sourceforge(callbacks.PrivmsgCommandAndRegexp):
    """
    Module for Sourceforge stuff. Currently contains commands to query a
    project's most recent bugs and rfes.
    """
    threaded = True
    regexps = ['sfSnarfer']

    _reopts = re.I
    _infoRe = re.compile(r'<td nowrap>(\d+)</td><td><a href='
                         r'"([^"]+)">([^<]+)</a>', re.I)
    _hrefOpts = '&set=custom&_assigned_to=0&_status=%s&_category=100' \
                '&_group=100&order=artifact_id&sort=DESC'
    _resolution=re.compile(r'<b>(Resolution):</b> <a.+?<br>(.+?)</td>',_reopts)
    _assigned=re.compile(r'<b>(Assigned To):</b> <a.+?<br>(.+?)</td>', _reopts)
    _submitted = re.compile(r'<b>(Submitted By):</b><br>([^<]+)</td>', _reopts)
    _priority = re.compile(r'<b>(Priority):</b> <a.+?<br>(.+?)</td>', _reopts)
    _status = re.compile(r'<b>(Status):</b> <a.+?<br>(.+?)</td>', _reopts)
    _regexps =(_resolution, _assigned, _submitted, _priority, _status)
    _statusOpt = {'any':100, 'open':1, 'closed':2, 'deleted':3, 'pending':4}

    _projectURL = 'http://sourceforge.net/projects/'
    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)

    def die(self):
        callbacks.PrivmsgCommandAndRegexp.die(self)

    def _formatResp(self, text, num=''):
        """
        Parses the Sourceforge query to return a list of tuples that
        contain the bug/rfe information.
        """
        if num:
            for item in ifilter(lambda s, n=num: s and n in s,
                                self._infoRe.findall(text)):
                yield (ircutils.bold(utils.htmlToText(item[2])),
                        utils.htmlToText(item[1]))
        else:
            for item in ifilter(None, self._infoRe.findall(text)):
                yield (item[0], utils.htmlToText(item[2]))

    def _getTrackerURL(self, project, regex, status):
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
        try:
            text = webutils.getUrl(url)
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
        
    def _getTrackerInfo(self, irc, msg, url, num):
        try:
            text = webutils.getUrl(url)
            head = '%s <http://sourceforge.net%s>'
            resp = [head % match for match in self._formatResp(text,num)]
            if resp:
                irc.reply(resp[0])
                return
            irc.errorPossibleBug('No Trackers were found.')
        except webutils.WebError, e:
            irc.error(str(e))

    _bugLink = re.compile(r'"([^"]+)">Bugs')
    def bugs(self, irc, msg, args):
        """[--{any,open,closed,deleted,pending}] [<project>]

        Returns a list of the most recent bugs filed against <project>.
        <project> is not needed if there is a default project set.  Search
        defaults to open bugs.
        """
        (optlist, rest) = getopt.getopt(args, '', self._statusOpt.keys())
        project = privmsgs.getArgs(rest, required=0, optional=1)
        status = 'open'
        for (option, _) in optlist:
            option = option.lstrip('-').lower()
            if option in self._statusOpt:
                status = option
        try:
            int(project)
            # They want the bug command, they're giving us an id#.
            s = 'Use the bug command to get information about a specific bug.'
            irc.error(s)
            return
        except ValueError:
            pass
        if not project:
            project = self.registryValue('project', msg.args[0])
            if not project:
                raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._bugLink, status)
        except TrackerError, e:
            irc.error('%s.  Can\'t find the Bugs link.' % e)
            return
        irc.reply(self._getTrackerList(url))

    # TODO: consolidate total* into one command which takes options for all
    # the viable statistics that can be snarfed from the project page
    _totbugs = re.compile(r'Bugs</a>\s+?\( <b>([^<]+)</b>', re.S | re.I)
    def totalbugs(self, irc, msg, args):
        """[<project>]

        Returns a count of the open/total bugs.  <project> is not needed if a
        default project is set.
        """
        project = privmsgs.getArgs(args, required=0, optional=1)
        project = project or self.registryValue('project', msg.args[0])
        if not project:
            raise callbacks.ArgumentError
        text = webutils.getUrl(''.join([self._projectURL, project]))
        m = self._totbugs.search(text)
        if m:
            irc.reply(m.group(1))
        else:
            irc.error('Could not find bug statistics.')

    def bug(self, irc, msg, args):
        """[--{any,open,closed,deleted,pending}] [<project>] <num>

        Returns a description of the bug with Tracker id <num> and the 
        corresponding Tracker URL.  <project> is not needed if there is a
        default project set. Search defaults to open bugs.
        """
        (optlist, rest) = getopt.getopt(args, '', self._statusOpt.keys())
        (project, bugnum) = privmsgs.getArgs(rest, optional=1)
        status = 'open'
        for (option, _) in optlist:
            option = option.lstrip('-').lower()
            if option in self._statusOpt:
                status = option
        if not bugnum:
            try:
                int(project)
            except ValueError:
                irc.error('"%s" is not a proper bugnumber.' % project)
                return
            bugnum = project
            project = self.registryValue('project', msg.args[0])
            if not project:
                raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._bugLink, status)
            #self.log.warning(url)
        except TrackerError, e:
            irc.error('%s.  Can\'t find the Bugs link.' % e)
            return
        self._getTrackerInfo(irc, msg, url, bugnum)

    _rfeLink = re.compile(r'"([^"]+)">RFE')
    def rfes(self, irc, msg, args):
        """[--{any,open,closed,deleted,pending}] [<project>]

        Returns a list of the most recent RFEs filed against <project>.
        <project> is not needed if there is a default project set.  Search
        defaults to open RFEs.
        """
        (optlist, rest) = getopt.getopt(args, '', self._statusOpt.keys())
        project = privmsgs.getArgs(rest, required=0, optional=1)
        status = 'open'
        for (option, _) in optlist:
            option = option.lstrip('-').lower()
            if option in self._statusOpt:
                status = option
        try:
            int(project)
            # They want a specific RFE, they gave us its id#.
            s = 'Use the rfe command to get information about a specific rfe.'
            irc.error(s)
            return
        except ValueError:
            pass
        if not project:
            project = self.registryValue('project', msg.args[0])
            if not project:
                raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._rfeLink, status)
        except TrackerError, e:
            irc.error('%s.  Can\'t find the RFEs link.' % e)
            return
        irc.reply(self._getTrackerList(url))

    _totrfes = re.compile(r'Feature Requests</a>\s+?\( <b>([^<]+)</b>',
                          re.S | re.I)
    def totalrfes(self, irc, msg, args):
        """[<project>]

        Returns a count of the open/total RFEs.  <project> is not needed if a
        default project is set.
        """
        project = privmsgs.getArgs(args, required=0, optional=1)
        project = project or self.registryValue('project', msg.args[0])
        if not project:
            raise callbacks.ArgumentError
        text = webutils.getUrl(''.join([self._projectURL, project]))
        m = self._totrfes.search(text)
        if m:
            irc.reply(m.group(1))
        else:
            irc.error('Could not find RFE statistics.')

    def rfe(self, irc, msg, args):
        """[--{any,open,closed,deleted,pending}] [<project>] <num>

        Returns a description of the bug with Tracker id <num> and the 
        corresponding Tracker URL. <project> is not needed if there is a 
        default project set. Search defaults to open RFEs.
        """
        (optlist, rest) = getopt.getopt(args, '', self._statusOpt.keys())
        (project, rfenum) = privmsgs.getArgs(rest, optional=1)
        status = 'open'
        for (option, _) in optlist:
            option = option.lstrip('-').lower()
            if option in self._statusOpt:
                status = option
        if not rfenum:
            try:
                int(project)
            except ValueError:
                irc.error('"%s" is not a proper rfenumber.' % project)
                return
            rfenum = project
            project = self.registryValue('project', msg.args[0])
            if not project:
                raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._rfeLink, status)
        except TrackerError, e:
            irc.error('%s.  Can\'t find the RFEs link.' % e)
            return
        self._getTrackerInfo(irc, msg, url, rfenum)

    _bold = lambda self, m: (ircutils.bold(m[0]),) + m[1:]
    _sfTitle = re.compile(r'Detail:(\d+) - ([^<]+)</title>', re.I)
    _linkType = re.compile(r'(\w+ \w+|\w+): Tracker Detailed View', re.I)
    def sfSnarfer(self, irc, msg, match):
        r"https?://(?:www\.)?(?:sourceforge|sf)\.net/tracker/" \
        r".*\?(?:&?func=detail|&?aid=\d+|&?group_id=\d+|&?atid=\d+){4}"
        if not self.registryValue('trackerSnarfer', msg.args[0]):
            return
        try:
            url = match.group(0)
            s = webutils.getUrl(url)
            resp = []
            head = ''
            m = self._linkType.search(s)
            n = self._sfTitle.search(s)
            if m and n:
                linktype = m.group(1)
                linktype = utils.depluralize(linktype)
                (num, desc) = n.groups()
                head = '%s #%s:' % (ircutils.bold(linktype), num)
                resp.append(desc)
            else:
                self.log.warning('Invalid Tracker page snarfed: %s', url)
            for r in self._regexps:
                m = r.search(s)
                if m:
                    resp.append('%s: %s' % self._bold(m.groups()))
            irc.reply('%s #%s: %s' % (ircutils.bold(linktype),
                ircutils.bold(num), '; '.join(resp)), prefixName = False)
        except webutils.WebError, e:
            self.log.warning(str(e))
    sfSnarfer = privmsgs.urlSnarfer(sfSnarfer)

Class = Sourceforge

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
