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
import socket
import urllib2

from itertools import ifilter, imap

import conf
import debug
import utils
__revision__ = "$Id$"

import plugins
import ircutils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Sourceforge')
    print 'The Sourceforge plugin has the functionality to watch for URLs'
    print 'that match a specific pattern (we call this a snarfer). When'
    print 'supybot sees such a URL, he will parse the web page for'
    print 'information and reply with the results.\n'
    if yn('Do you want this snarfer to be enabled by default?') == 'y':
        onStart.append('Sourceforge config tracker-snarfer on')

    print 'The bugs and rfes commands of the Sourceforge plugin can be set'
    print 'to query a default project when no project is specified.  If this'
    print 'project is not set, calling either of those commands will display'
    print 'the associated help.  With the default project set, calling'
    print 'bugs/rfes with no arguments will find the most recent bugs/rfes'
    print 'for the default project.\n'
    if yn('Do you want to specify a default project?') == 'y':
        project = anything('Project name:')
        if project:
            onStart.append('Sourceforge config defaultproject %s' % project)

    print 'Sourceforge is quite the word to type, and it may get annoying'
    print 'typing it all the time because Supybot makes you use the plugin'
    print 'name to disambiguate calls to ambiguous commands (i.e., the bug'
    print 'command is in this plugin and the Bugzilla plugin; if both are'
    print 'loaded, you\'ll have you type "sourceforge bug ..." to get this'
    print 'bug command).  You may save some time by making an alias for'
    print '"sourceforge".  We like to make it "sf".'
    if yn('Would you like to add sf as an alias for Sourceforge?') == 'y':
        if 'load Alias' not in onStart:
            print 'This depends on the Alias module.'
            if yn('Would you like to load the Alias plugin now?') == 'y':
                onStart.append('load Alias')
            else:
                print 'Then I can\'t add such an alias.'
                return
        onStart.append('alias add sf sourceforge $*')

class TrackerError(Exception):
    pass

class Sourceforge(callbacks.PrivmsgCommandAndRegexp, plugins.Configurable):
    """
    Module for Sourceforge stuff. Currently contains commands to query a
    project's most recent bugs and rfes.
    """
    threaded = True
    regexps = ['sfSnarfer']

    _reopts = re.I
    _infoRe = re.compile(r'<td nowrap>(\d+)</td><td><a href='\
        '"([^"]+)">([^<]+)</a>', _reopts)
    _hrefOpts = '&set=custom&_assigned_to=0&_status=1&_category'\
        '=100&_group=100&order=artifact_id&sort=DESC'
    _resolution=re.compile(r'<b>(Resolution):</b> <a.+?<br>(.+?)</td>',_reopts)
    _assigned=re.compile(r'<b>(Assigned To):</b> <a.+?<br>(.+?)</td>', _reopts)
    _submitted = re.compile(r'<b>(Submitted By):</b><br>([^<]+)</td>', _reopts)
    _priority = re.compile(r'<b>(Priority):</b> <a.+?<br>(.+?)</td>', _reopts)
    _status = re.compile(r'<b>(Status):</b> <a.+?<br>(.+?)</td>', _reopts)
    _res =(_resolution, _assigned, _submitted, _priority, _status)

    configurables = plugins.ConfigurableDictionary(
        [('tracker-snarfer', plugins.ConfigurableBoolType, False,
          """Determines whether the bot will reply to SF.net Tracker URLs in
          the channel with a nice summary of the tracker item."""),
         ('default-project', plugins.ConfigurableStrType, '',
          """Sets the default project (used by the bugs/rfes commands in the
          case that no explicit project is given).""")]
    )
    _projectURL = 'http://sourceforge.net/projects/'
    def __init__(self):
        plugins.Configurable.__init__(self)
        callbacks.PrivmsgCommandAndRegexp.__init__(self)

    def die(self):
        plugins.Configurable.die(self)
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

    def _getTrackerURL(self, project, regex):
        try:
            fd = urllib2.urlopen('%s%s' % (self._projectURL, project))
            text = fd.read()
            fd.close()
            m = regex.search(text)
            if m is None:
                raise TrackerError, 'Invalid Tracker page'
            else:
                return 'http://sourceforge.net%s%s' % (utils.htmlToText(
                    m.group(1)), self._hrefOpts)
        except urllib2.HTTPError, e:
            raise callbacks.Error, e.msg()

    def _getTrackerList(self, url):
        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            fd.close()
            head = '#%s: %s'
            resp = [head % entry for entry in self._formatResp(text)]
            if resp:
                if len(resp) > 10:
                    resp = imap(lambda s: utils.ellipsisify(s, 50), resp)
                return '%s' % utils.commaAndify(resp)
            raise callbacks.Error, 'No Trackers were found. (%s)' %\
                conf.replyPossibleBug
        except urllib2.HTTPError, e:
            raise callbacks.Error, e.msg()
        
    def _getTrackerInfo(self, irc, msg, url, num):
        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            fd.close()
            head = '%s <http://sourceforge.net%s>'
            resp = [head % match for match in self._formatResp(text,num)]
            if resp:
                irc.reply(msg, resp[0])
                return
            irc.error(msg, 'No Trackers were found. (%s)' %
                conf.replyPossibleBug)
        except urllib2.HTTPError, e:
            irc.error(msg, e.msg())

    _bugLink = re.compile(r'"([^"]+)">Bugs')
    def bugs(self, irc, msg, args):
        """[<project>]

        Returns a list of the most recent bugs filed against <project>.
        <project> is not needed if there is a default project set.
        """
        project = privmsgs.getArgs(args, required=0, optional=1)
        try:
            int(project)
            irc.error(msg, 'Use the bug command to get information about a '\
                'specific bug.')
            return
        except ValueError:
            pass
        if not project:
            project = self.configurables.get('default-project', msg.args[0])
            if not project:
                raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._bugLink)
        except TrackerError, e:
            irc.error(msg, '%s.  Can\'t find the Bugs link.' % e)
            return
        irc.reply(msg, self._getTrackerList(url))

    def bug(self, irc, msg, args):
        """[<project>] <num>

        Returns a description of the bug with Tracker id <num> and the 
        corresponding Tracker URL.  <project> is not needed if there is a
        default project set.
        """
        (project, bugnum) = privmsgs.getArgs(args, optional=1)
        if not bugnum:
            try:
                int(project)
            except ValueError:
                irc.error(msg, '"%s" is not a proper bugnumber.' % project)
                return
            bugnum = project
            project = self.configurables.get('default-project', msg.args[0])
            if not project:
                raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._bugLink)
        except TrackerError, e:
            irc.error(msg, '%s.  Can\'t find the Bugs link.' % e)
            return
        self._getTrackerInfo(irc, msg, url, bugnum)

    _rfeLink = re.compile(r'"([^"]+)">RFE')
    def rfes(self, irc, msg, args):
        """[<project>]

        Returns a list of the most recent RFEs filed against <project>.
        <project> is not needed if there is a default project set.
        """
        project = privmsgs.getArgs(args, required=0, optional=1)
        try:
            int(project)
            irc.error(msg, 'Use the rfe command to get information about a '\
                'specific rfe.')
            return
        except ValueError:
            pass
        if not project:
            project = self.configurables.get('default-project', msg.args[0])
            if not project:
                raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._rfeLink)
        except TrackerError, e:
            irc.error(msg, '%s.  Can\'t find the RFEs link.' % e)
            return
        irc.reply(msg, self._getTrackerList(url))

    def rfe(self, irc, msg, args):
        """[<project>] <num>

        Returns a description of the bug with Tracker id <num> and the 
        corresponding Tracker URL. <project> is not needed if there is a 
        default project set.
        """
        (project, rfenum) = privmsgs.getArgs(args, optional=1)
        if not rfenum:
            try:
                int(project)
            except ValueError:
                irc.error(msg, '"%s" is not a proper rfenumber.' % project)
                return
            rfenum = project
            project = self.configurables.get('default-project', msg.args[0])
            if not project:
                raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._rfeLink)
        except TrackerError, e:
            irc.error(msg, '%s.  Can\'t find the RFEs link.' % e)
            return
        self._getTrackerInfo(irc, msg, url, rfenum)

    _bold = lambda self, m: (ircutils.bold(m[0]),) + m[1:]
    _sfTitle = re.compile(r'Detail:(\d+) - ([^<]+)</title>', re.I)
    _linkType = re.compile(r'(\w+ \w+|\w+): Tracker Detailed View', re.I)
    def sfSnarfer(self, irc, msg, match):
        r"https?://(?:www\.)?(?:sourceforge|sf)\.net/tracker/" \
        r".*\?(?:&?func=detail|&?aid=\d+|&?group_id=\d+|&?atid=\d+){4}"
        if not self.configurables.get('tracker-snarfer', channel=msg.args[0]):
            return
        try:
            url = match.group(0)
            fd = urllib2.urlopen(url)
            s = fd.read()
            fd.close()
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
                debug.msg('%s does not appear to be a proper Sourceforge '\
                    'Tracker page (%s)' % (url, conf.replyPossibleBug))
            for r in self._res:
                m = r.search(s)
                if m:
                    resp.append('%s: %s' % self._bold(m.groups()))
            irc.reply(msg, '%s #%s: %s' % (ircutils.bold(linktype),
                ircutils.bold(num), '; '.join(resp)), prefixName = False)
        except urllib2.HTTPError, e:
            debug.msg(e.msg())
        except socket.error, e:
            debug.msg(e.msg())
    sfSnarfer = privmsgs.urlSnarfer(sfSnarfer)

Class = Sourceforge

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
