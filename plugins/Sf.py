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
    onStart.append('load Sf')

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

class Sf(callbacks.PrivmsgCommandAndRegexp):
    """
    Module for Sourceforge stuff. Currently contains commands to query a
    project's most recent bugs and rfes.
    """
    threaded = True
    regexps = sets.Set(['sfSnarfer'])

    _infoRe = re.compile(r'<td nowrap>(\d+)</td><td><a href="([^"]+)">'\
        '([^<]+)</a>', re.I)
    _hrefOpts = '&set=custom&_assigned_to=0&_status=1&_category=100&'\
        '_group=100&order=artifact_id&sort=DESC'

    _resolution = re.compile(r'<b>Resolution:</b> <a.+?<br>(.+?)</td>', re.I)
    _getRes = lambda self, s: '%s: %s' % (ircutils.bold('Resolution'),
        self._resolution.search(s).group(1))
    _assigned = re.compile(r'<b>Assigned To:</b> <a.+?<br>(.+?)</td>', re.I)
    _getAssign = lambda self, s: '%s: %s' % (ircutils.bold('Assigned to'), 
        self._assigned.search(s).group(1))
    _priority = re.compile(r'<b>Priority:</b> <a.+?<br>(.+?)</td>', re.I)
    _getPri = lambda self, s: '%s: %s' % (ircutils.bold('Priority'),
        self._priority.search(s).group(1))
    _status = re.compile(r'<b>Status:</b> <a.+?<br>(.+?)</td>', re.I)
    _getStatus = lambda self, s: '%s: %s' % (ircutils.bold('Status'), 
        self._status.search(s).group(1))

    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.snarfer = True

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

    def disablesfsnarfer(self, irc, msg, args):
        """takes no argument

        Disables the snarfer that responds to all Sourceforge Tracker links
        """
        self.snarfer = False
        irc.reply(msg, conf.replySuccess)
    disablesfsnarfer=privmsgs.checkCapability(disablesfsnarfer,'admin')

    _bugLink = re.compile(r'"([^"]+)">Bugs')
    def bugs(self, irc, msg, args):
        """[<project> [<num>]]

        Returns a list of the most recent bugs filed against <project>.
        Defaults to searching for supybot bugs. If <num> is specified, the bug
        description and link are retrieved.
        """
        (project, bugnum) = privmsgs.getArgs(args, needed=0, optional=2)
        if not project:
            project = 'supybot'
        url = 'http://sourceforge.net/projects/%s' % project
        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            fd.close()
            m = self._bugLink.search(text)
            if m is None:
                irc.reply(msg, 'Can\'t find the "Bugs" link.')
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
            if bugnum != '':
                head = '%s <http://sourceforge.net%s>'
                for bug in self._formatResp(bugnum, text):
                    resp.append(head % bug)
                if resp:
                    irc.reply(msg, resp[0])
                    return
            else:
                head = 'Bug #%s: %s'
                for bug in self._formatResp(bugnum, text):
                    resp.append(head % bug)
                if resp:
                    if len(resp) > 10:
                        resp = map(lambda s: utils.ellipsisify(s, 50), resp)
                    irc.reply(msg, '%s' % utils.commaAndify(resp))
                    return
            irc.reply(msg, 'No bugs were found.')
        except ValueError, e:
            irc.error(msg, str(e))
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

    _rfeLink = re.compile(r'"([^"]+)">RFE')
    def rfes(self, irc, msg, args):
        """[<project> [<num>]]

        Returns a list of the most recent RFEs filed against <project>.
        Defaults to searching for supybot RFEs. If <num> is specified, the rfe
        description and link are retrieved.
        """
        (project, rfenum) = privmsgs.getArgs(args, needed=0, optional=2)
        if not project:
            project = 'supybot'
        url = 'http://sourceforge.net/projects/%s' % project
        try:
            fd = urllib2.urlopen(url)
            text = fd.read()
            fd.close()
            m = self._rfeLink.search(text)
            if m is None:
                irc.reply(msg, 'Can\'t find the "RFE" link.')
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
            if rfenum != '':
                head = '%s <http://sourceforge.net%s>'
                for rfe in self._formatResp(rfenum, text):
                    resp.append(head % rfe)
                if resp:
                    irc.reply(msg, resp[0])
                    return
            else:
                head = 'RFE #%s: %s'
                for rfe in self._formatResp(rfenum, text):
                    resp.append(head % rfe)
                if resp:
                    if len(resp) > 10:
                        resp = map(lambda s: utils.ellipsisify(s, 50), resp)
                    irc.reply(msg, '%s' % utils.commaAndify(resp))
                    return
            irc.reply(msg, 'No rfes were found.')
        except ValueError, e:
            irc.error(msg, str(e))
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

    _sfTitle = re.compile(r'Detail:(\d+) - ([^<]+)</title>', re.I)
    _linkType = re.compile(r'(\w+ \w+|\w+): Tracker Detailed View', re.I)
    def sfSnarfer(self, irc, msg, match):
        r"https?://(?:www\.)?(?:sourceforge|sf)\.net/tracker/(?:index\.php)?\?func=detail&aid=\d+&group_id=\d+&atid=\d+"
        if not self.snarfer:
            return
        url = match.group(0)
        fd = urllib2.urlopen(url)
        s = fd.read()
        fd.close()
        searches = (self._getStatus, self._getRes, self._getPri,
            self._getAssign)
        try:
            (num, desc) = self._sfTitle.search(s).groups()
            resp = [desc]
            linktype = self._linkType.search(s).group(1)
            for i in searches:
                try:
                    resp.append('%s' % i(s))
                except AttributeError:
                    pass
            linktype = utils.depluralize(linktype)
            irc.reply(msg, '%s #%s: %s' % (ircutils.bold(linktype),
                ircutils.bold(num), '; '.join(resp)))
        except AttributeError, e:
            irc.error(msg, 'That doesn\'t appear to be a proper Sourceforge '\
                'Tracker page.')
        except Exception, e:
            irc.error(msg, debug.exnToString(e))

Class = Sf

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
