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
            onStart.append('Sourceforge togglesnarfer tracker off')

    print 'The bugs and rfes commands of the Sourceforge plugin can be set'
    print 'to query a default project when no project is specified.  If this'
    print 'project is not set, calling either of those commands will display'
    print 'the associated help.  With the default project set, calling'
    print 'bugs/rfes with no arguments will find the most recent bugs/rfes'
    print 'for the default project.\n'
    if yn('Do you want to specify a default project?') == 'y':
        project = anything('Project name:')
        if project:
            onStart.append('Sourceforge setdefault %s' % project)

example = utils.wrapLines("""
<@jamessan|work> @bugs
< supybot> jamessan|work: Bug #820702: ChannelDB bugs in stats., Bug #797823: Time reporting errors on win9x, Bug #794330: Website documentation isn't finished., Bug #708327: FreeBSD plugin doesn't automatically download the new INDEX, and Bug #708158: FreeBSD plugin's searchports doesn't do depends correctly.
<@jamessan|work> @bugs supybot 797823
< supybot> jamessan|work: Time reporting errors on win9x <http://sourceforge.net/tracker/index.php?func=detail&aid=797823&group_id=58965&atid=489447>
<@jamessan|work> @bugs gaim
< supybot> jamessan|work: Bug #821118: MSN Plugin cannot be loaded
in 0.71, Bug #820961: dock icon doesn't show up with..., Bug #820879: Cannot connect to a particular irc..., Bug #820831: &copy; or &reg; render im null, Bug #820776: gaim 0.70 segfaults using certain..., Bug #820691: gaim 0.70 fails to start up on..., Bug #820687: MSN duplicating buddies at signon, Bug (6 more messages)
<@jamessan|work> @rfes pythoggoras
< supybot> jamessan|work: RFE #728701: Ability to specify 'themed' configs at command line, RFE #720757: Improve CLI interface, RFE #719248: Add config file support, and RFE #717761: Tracker for adding GUI
<@jamessan|work> @rfes pythoggoras 720757
< supybot> jamessan|work: Improve CLI interface <http://sourceforge.net/tracker/index.php?func=detail&aid=720757&group_id=75946&atid=545548>
""")

class Sourceforge(callbacks.PrivmsgCommandAndRegexp):
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
    _resolution = re.compile(r'<b>Resolution:</b> <a.+?<br>(.+?)</td>',_reopts)
    _assigned = re.compile(r'<b>Assigned To:</b> <a.+?<br>(.+?)</td>', _reopts)
    _submitted = re.compile(r'<b>Submitted By:</b><br>([^<]+)</td>', _reopts)
    _priority = re.compile(r'<b>Priority:</b> <a.+?<br>(.+?)</td>', _reopts)
    _status = re.compile(r'<b>Status:</b> <a.+?<br>(.+?)</td>', _reopts)
    _res ={'Resolution':_resolution,'Assigned to':_assigned,
        'Submitted by':_submitted, 'Priority':_priority,
        'Status':_status}

    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.snarfers = {'tracker' : True}
        self.project = None

    def _formatResp(self, num, text):
        """
        Parses the Sourceforge query to return a list of tuples that
        contain the bug/rfe information.
        """

        matches = []
        try:
            int(num)
            for item in ifilter(lambda s, n=num: s is not None and n in s,
                                self._infoRe.findall(text)):
                matches.append((ircutils.bold(utils.htmlToText(item[2])),
                                utils.htmlToText(item[1])))
        except ValueError:
            for item in ifilter(None, self._infoRe.findall(text)):
                matches.append((item[0], utils.htmlToText(item[2])))
        return matches

    def setdefault(self, irc, msg, args):
        """<project>

        Sets the default project to be used with bugs and rfes
        """
        project = privmsgs.getArgs(args)
        self.project = project
        irc.reply(msg, conf.replySuccess)
    setdefault = privmsgs.checkCapability(setdefault, 'admin')
        
    def _toggleHelper(self, irc, msg, state, snarfer):
        if not state:
            self.snarfers[snarfer] = not self.snarfers[snarfer] 
        elif state in self._enable:
            self.snarfers[snarfer] = True
        elif state in self._disable:
            self.snarfers[snarfer] = False
        resp = []
        for k in self.snarfers:
            if self.snarfers[k]:
                resp.append('%s%s: On' % (k[0].upper(), k[1:]))
            else:
                resp.append('%s%s: Off' % (k[0].upper(), k[1:]))
        irc.reply(msg, '%s (%s)' % (conf.replySuccess, '; '.join(resp)))

    _enable = ('on', 'enable')
    _disable = ('off', 'disable')
    def togglesnarfer(self, irc, msg, args):
        """<tracker> [<on|off>]

        Toggles the snarfer that responds to Sourceforge Tracker links.  If
        nothing is specified, all snarfers will have their states
        toggled (on -> off, off -> on).  If only a state is specified, all
        snarfers will have their state set to the specified state.  If a
        specific snarfer is specified, the changes will apply only to that
        snarfer.
        """
        (snarfer, state) = privmsgs.getArgs(args, optional=1)
        snarfer = snarfer.lower()
        state = state.lower()
        if snarfer not in self.snarfers:
            raise callbacks.ArgumentError
        if state and state not in self._enable and state not in self._disable:
            raise callbacks.ArgumentError
        self._toggleHelper(irc, msg, state, snarfer)
    togglesnarfer=privmsgs.checkCapability(togglesnarfer, 'admin')

    def _getTrackerInfo(self, irc, msg, url, regex, num):
        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            fd.close()
            m = regex.search(text)
            if m is None:
                irc.reply(msg, 'Can\'t find the proper Tracker link.')
                return
            else:
                url = 'http://sourceforge.net%s%s' %\
                    (utils.htmlToText(m.group(1)), self._hrefOpts)
        except ValueError, e:
            irc.error(msg, str(e))
        except urllib2.HTTPError, e:
            irc.error(msg, e.msg())
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            fd.close()
            resp = []
            if num != '':
                head = '%s <http://sourceforge.net%s>'
                for match in self._formatResp(num, text):
                    resp.append(head % match)
                if resp:
                    irc.reply(msg, resp[0])
                    return
            else:
                head = '#%s: %s'
                for entry in self._formatResp(num, text):
                    resp.append(head % entry)
                if resp:
                    if len(resp) > 10:
                        resp = map(lambda s: utils.ellipsisify(s, 50), resp)
                    irc.reply(msg, '%s' % utils.commaAndify(resp))
                    return
            irc.reply(msg, 'No Trackers were found.')
        except ValueError, e:
            irc.error(msg, str(e))
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

    _bugLink = re.compile(r'"([^"]+)">Bugs')
    def bugs(self, irc, msg, args):
        """[<project> [<num>]]

        Returns a list of the most recent bugs filed against <project>.
        Defaults to searching for supybot bugs. If <num> is specified, the bug
        description and link are retrieved.
        """
        (project, bugnum) = privmsgs.getArgs(args, needed=0, optional=2)
        if not project:
            if self.project is None:
                raise callbacks.ArgumentError
            else:
                project = self.project
        elif not bugnum:
            try:
                bugnum = int(project)
                project = self.project
            except ValueError:
                pass
        url = 'http://sourceforge.net/projects/%s' % project
        self._getTrackerInfo(irc, msg, url, self._bugLink, bugnum)

    _rfeLink = re.compile(r'"([^"]+)">RFE')
    def rfes(self, irc, msg, args):
        """[<project> [<num>]]

        Returns a list of the most recent RFEs filed against <project>.
        Defaults to searching for supybot RFEs. If <num> is specified, the rfe
        description and link are retrieved.
        """
        (project, rfenum) = privmsgs.getArgs(args, needed=0, optional=2)
        if not project:
            if self.project is None:
                raise callbacks.ArgumentError
            else:
                project = self.project
        elif not rfenum:
            try:
                rfenum = int(project)
                project = self.project
            except ValueError:
                pass
        url = 'http://sourceforge.net/projects/%s' % project
        self._getTrackerInfo(irc, msg, url, self._rfeLink, rfenum)

    _getSnarferInfo = lambda self, k, v, s: '%s: %s' % (ircutils.bold(k),
        v.search(s).group(1))
    _sfTitle = re.compile(r'Detail:(\d+) - ([^<]+)</title>', re.I)
    _linkType = re.compile(r'(\w+ \w+|\w+): Tracker Detailed View', re.I)
    def sfSnarfer(self, irc, msg, match):
        r"https?://(?:www\.)?(?:sourceforge|sf)\.net/tracker/(?:index\.php)?\?(?:&?func=detail|&?aid=\d+|&?group_id=\d+|&?atid=\d+){4}"
        if not self.snarfers['tracker']:
            return
        url = match.group(0)
        fd = urllib2.urlopen(url)
        s = fd.read()
        fd.close()
        try:
            (num, desc) = self._sfTitle.search(s).groups()
            resp = [desc]
            linktype = self._linkType.search(s).group(1)
            for k,v in self._res.iteritems():
                try:
                    resp.append(self._getSnarferInfo(k, v, s))
                except AttributeError:
                    pass
            linktype = utils.depluralize(linktype)
            irc.reply(msg, '%s #%s: %s' % (ircutils.bold(linktype),
                ircutils.bold(num), '; '.join(resp)), prefixName = False)
        except AttributeError, e:
            irc.error(msg, 'That doesn\'t appear to be a proper Sourceforge '\
                'Tracker page. (%s)' % conf.replyPossibleBug)
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

Class = Sourceforge

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
