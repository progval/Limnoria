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
import urllib2

from itertools import ifilter

import conf
import debug
import utils
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
    if advanced:
        print 'The Sourceforge plugin has the functionality to watch for URLs'
        print 'that match a specific pattern (we call this a snarfer). When'
        print 'supybot sees such a URL, he will parse the web page for'
        print 'information and reply with the results.\n'
        if yn('Do you want the Sourceforge snarfer enabled by default?') =='n':
            onStart.append('Sourceforge toggle tracker off')

    print 'The bugs and rfes commands of the Sourceforge plugin can be set'
    print 'to query a default project when no project is specified.  If this'
    print 'project is not set, calling either of those commands will display'
    print 'the associated help.  With the default project set, calling'
    print 'bugs/rfes with no arguments will find the most recent bugs/rfes'
    print 'for the default project.\n'
    if yn('Do you want to specify a default project?') == 'y':
        project = anything('Project name:')
        if project:
            onStart.append('Sourceforge defaultproject %s' % project)

class TrackerError(Exception):
    pass

class Sourceforge(callbacks.PrivmsgCommandAndRegexp, plugins.Toggleable):
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

    toggles = plugins.ToggleDictionary({'tracker' : True})
    project = None
    _projectURL = 'http://sourceforge.net/projects/'

    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        plugins.Toggleable.__init__(self)

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

    def defaultproject(self, irc, msg, args):
        """[<project>]

        Sets the default project to be used with bugs and rfes. If a project
        is not specified, clears the default project.
        """
        project = privmsgs.getArgs(args, needed=0, optional=1)
        self.project = project
        irc.reply(msg, conf.replySuccess)
    defaultproject = privmsgs.checkCapability(defaultproject, 'admin')

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
        except Exception, e:
            raise callbacks.Error, debug.exnToString(e)

    def _getTrackerList(self, url):
        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            fd.close()
            head = '#%s: %s'
            resp = [head % entry for entry in self._formatResp(text)]
            if resp:
                if len(resp) > 10:
                    resp = map(lambda s: utils.ellipsisify(s, 50), resp)
                return '%s' % utils.commaAndify(resp)
            raise callbacks.Error, 'No Trackers were found. (%s)' %\
                conf.replyPossibleBug
        except Exception, e:
            raise callbacks.Error, debug.exnToString(e)
        
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
        except ValueError, e:
            irc.error(msg, str(e))
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

    _bugLink = re.compile(r'"([^"]+)">Bugs')
    def bugs(self, irc, msg, args):
        """[<project>]

        Returns a list of the most recent bugs filed against <project>.
        Defaults to searching for bugs in the project set by defaultproject.
        """
        project = privmsgs.getArgs(args, needed=0, optional=1)
        project = project or self.project
        if not project:
            raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._bugLink)
        except TrackerError:
            irc.error(msg, 'Can\'t find the Bugs link.')
            return
        irc.reply(msg, self._getTrackerList(url))

    def bug(self, irc, msg, args):
        """[<project>] <num>

        Returns a description of the bug with Tracker id <num> and the 
        corresponding Tracker URL.  Defaults to searching for bugs in the 
        project set by defaultproject.
        """
        (project, bugnum) = privmsgs.getArgs(args, optional=1)
        if not bugnum:
            try:
                int(project)
            except ValueError:
                irc.error(msg, '"%s" is not a proper bugnumber.' % project)
            bugnum = project
            project = self.project
        try:
            url = self._getTrackerURL(project, self._bugLink)
        except TrackerError:
            irc.error(msg, 'Can\'t find the Bugs link.')
            return
        self._getTrackerInfo(irc, msg, url, bugnum)

    _rfeLink = re.compile(r'"([^"]+)">RFE')
    def rfes(self, irc, msg, args):
        """[<project>]

        Returns a list of the most recent RFEs filed against <project>.
        Defaults to searching for RFEs in the project set by defaultproject.
        """
        project = privmsgs.getArgs(args, needed=0, optional=1)
        project = project or self.project
        if not project:
            raise callbacks.ArgumentError
        try:
            url = self._getTrackerURL(project, self._rfeLink)
        except TrackerError, e:
            irc.error(msg, 'Can\'t find the RFEs link.')
            return
        irc.reply(msg, self._getTrackerList(url))

    def rfe(self, irc, msg, args):
        """[<project>] <num>

        Returns a description of the bug with Tracker id <num> and the 
        corresponding Tracker URL.  Defaults to searching for bugs in the 
        project set by defaultproject.
        """
        (project, rfenum) = privmsgs.getArgs(args, optional=1)
        if not rfenum:
            try:
                int(project)
            except ValueError:
                irc.error(msg, '"%s" is not a proper rfenumber.' % project)
            rfenum = str(int(project))
            project = self.project
        try:
            url = self._getTrackerURL(project, self._rfeLink)
        except TrackerError:
            irc.error(msg, 'Can\'t find the RFE link.')
            return
        self._getTrackerInfo(irc, msg, url, rfenum)

    _bold = lambda self, m: (ircutils.bold(m[0]),) + m[1:]
    _sfTitle = re.compile(r'Detail:(\d+) - ([^<]+)</title>', re.I)
    _linkType = re.compile(r'(\w+ \w+|\w+): Tracker Detailed View', re.I)
    def sfSnarfer(self, irc, msg, match):
        r"https?://(?:www\.)?(?:sourceforge|sf)\.net/tracker/" \
        r".*\?(?:&?func=detail|&?aid=\d+|&?group_id=\d+|&?atid=\d+){4}"
        if not self.toggles.get('tracker', channel=msg.args[0]):
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

Class = Sourceforge

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
