#!/usr/bin/env python

###
# Copyright (c) 2003, Daniel Berlin
# Based on code from kibot
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
Bugzilla bug retriever
"""

__revision__ = "$Id$"

import os
import re
import csv
import getopt
import urllib
import xml.dom.minidom as minidom

from itertools import imap, ifilter
from htmlentitydefs import entitydefs as entities

import supybot.registry as registry

import supybot.conf as conf
import supybot.utils as utils
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.webutils as webutils
import supybot.callbacks as callbacks
import supybot.structures as structures

statusKeys = ['unconfirmed', 'new', 'assigned', 'reopened', 'resolved',
              'verified', 'closed']
resolutionKeys = ['fixed', 'invalid', 'worksforme', 'needinfo',
                  'test-request', 'wontfix', 'cantfix', 'moved', 'duplicate',
                  'remind', 'later', 'notabug', 'notgnome', 'incomplete',
                  'gnome1.x', 'moved']
priorityKeys = ['p1', 'p2', 'p3', 'p4', 'p5', 'Low', 'Normal', 'High',
                'Immediate', 'Urgent']
severityKeys = ['enhancement', 'trivial', 'minor', 'normal', 'major',
                'critical', 'blocker']

dbfilename = os.path.join(conf.supybot.directories.data(), 'Bugzilla.db')

def makeDb(filename):
    if os.path.exists(filename):
        d = structures.PersistentDictionary(filename)
    else:
        d = structures.PersistentDictionary(filename)
        d['gcc'] = ['http://gcc.gnu.org/bugzilla', 'GCC']
        d['rh'] = ['http://bugzilla.redhat.com/bugzilla', 'Red Hat']
        d['gnome'] = ['http://bugzilla.gnome.org/bugzilla', 'Gnome']
        d['mozilla'] = ['http://bugzilla.mozilla.org', 'Mozilla']
        d['ximian'] = ['http://bugzilla.ximian.com/bugzilla', 'Ximian Gnome']
        d.flush()
    return d


class BugzillaError(Exception):
    """A bugzilla error"""
    pass


def configure(advanced):
    from supybot.questions import output, expect, anything, yn
    conf.registerPlugin('Bugzilla', True)
    output("""The Bugzilla plugin has the functionality to watch for URLs
              that match a specific pattern (we call this a snarfer). When
              supybot sees such a URL, he will parse the web page for
              information and reply with the results.""")
    if yn('Do you want this bug snarfer enabled by default?', default=False):
        conf.supybot.plugins.Bugzilla.bugSnarfer.setValue(True)

conf.registerPlugin('Bugzilla')
conf.registerChannelValue(conf.supybot.plugins.Bugzilla, 'bugSnarfer',
    registry.Boolean(False, """Determines whether the bug snarfer will be
    enabled, such that any Bugzilla URLs seen in the channel will have their
    information reported into the channel."""))
conf.registerChannelValue(conf.supybot.plugins.Bugzilla, 'bold',
    registry.Boolean(True, """Determines whether results are bolded."""))
conf.registerChannelValue(conf.supybot.plugins.Bugzilla, 'replyNoBugzilla',
    registry.String('I don\'t have a bugzilla %r.', """Determines the phrase
    to use when notifying the user that there is no information about that
    bugzilla site."""))

class Bugzilla(callbacks.PrivmsgCommandAndRegexp):
    """Show a link to a bug report with a brief description"""
    threaded = True
    regexps = ['bzSnarfer']

    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.entre = re.compile('&(\S*?);')
        # Schema: {name, [url, description]}
        self.db = makeDb(dbfilename)
        self.shorthand = utils.abbrev(self.db.keys())

    def keywords2query(self, keywords):
        """Turn a list of keywords into a URL query string"""
        query = []
        for k in keywords:
            k = k.lower()
            if k in statusKeys:
                query.append('bug_status=%s' % k.upper())
            elif k in resolutionKeys:
                query.append('resolution=%s' % k.upper())
            elif k in priorityKeys:
                query.append('priority=%s' % k.upper())
            elif k in severityKeys:
                query.append('bug_severity=%s' % k.upper())
        query.append('ctype=csv')
        return query

    def die(self):
        self.db.close()

    def add(self, irc, msg, args):
        """<name> <url> <description>

        Add a bugzilla <url> to the list of defined bugzillae. <name>
        is the name that will be used to reference the zilla in all
        commands. Unambiguous abbreviations of <name> will be accepted also.
        <description> is the common name for the bugzilla and will
        be listed with the bugzilla query.
        """
        (name, url, description) = privmsgs.getArgs(args, required=3)
        if url[-1] == '/':
            url = url[:-1]
        self.db[name] = [url, description]
        self.shorthand = utils.abbrev(self.db.keys())
        irc.replySuccess()

    def remove(self, irc, msg, args):
        """<abbreviation>

        Remove the bugzilla associated with <abbreviation> from the list of
        defined bugzillae.
        """
        name = privmsgs.getArgs(args)
        try:
            name = self.shorthand[name]
            del self.db[name]
            self.shorthand = utils.abbrev(self.db.keys())
            irc.replySuccess()
        except KeyError:
            s = self.registryValue('replyNoBugzilla', msg.args[0])
            irc.error(s % name)

    def list(self, irc,  msg, args):
        """[<abbreviation>]

        List defined bugzillae. If <abbreviation> is specified, list the
        information for that bugzilla.
        """
        name = privmsgs.getArgs(args, required=0, optional=1)
        if name:
            try:
                name = self.shorthand[name]
                (url, description) = self.db[name]
                irc.reply('%s: %s, %s' % (name, description, url))
            except KeyError:
                s = self.registryValue('replyNoBugzilla', msg.args[0])
                irc.error(s % name)
        else:
            if self.db:
                L = self.db.keys()
                L.sort()
                irc.reply(utils.commaAndify(L))
            else:
                irc.reply('I have no defined bugzillae.')

    def bzSnarfer(self, irc, msg, match):
        r"(http://\S+)/show_bug.cgi\?id=([0-9]+)"
        if not self.registryValue('bugSnarfer', msg.args[0]):
            return
        queryurl = '%s/xml.cgi?id=%s' % (match.group(1), match.group(2))
        try:
            summary = self._get_short_bug_summary(queryurl,
                                                  'Snarfed Bugzilla URL',
                                                  match.group(2))
        except BugzillaError, e:
            irc.reply(str(e))
            return
        except IOError, e:
            msgtouser = '%s. Try yourself: %s' % (e, queryurl)
            irc.reply(msgtouser)
            return
        bold = self.registryValue('bold', msg.args[0])
        report = {}
        report['id'] = match.group(2)
        report['url'] = str('%s/show_bug.cgi?id=%s' % (match.group(1),
            match.group(2)))
        report['title'] = str(summary['title'])
        report['summary'] = str(self._mk_summary_string(summary, bold))
        report['product'] = str(summary['product'])
        s = '%(product)s bug #%(id)s: %(title)s %(summary)s' % report
        irc.reply(s, prefixName=False)
    bzSnarfer = privmsgs.urlSnarfer(bzSnarfer)

    def urlquery2bugslist(self, url, query):
        """Given a URL and query list for a CSV bug list, it'll return
        all the bugs in a dict
        """
        bugs = {}
        try:
            url = '%s/buglist.cgi?%s' % (url, '&'.join(query))
            u = webutils.getUrlFd(url)
        except webutils.WebError, e:
            return bugs
        # actually read in the file
        csvreader = csv.reader(u)
        # read header
        fields = csvreader.next()
        # read the rest of the list
        for bug in csvreader:
            if isinstance(bug, basestring):
                bugid = bug
            else:
                bugid = bug[0]
            try:
                bugid = int(bugid)
            except ValueError:
                pass
            bugs[bugid] = {}
            i = 1
            for f in fields[1:]:
                bugs[bugid][f] = bug[i]
                i += 1
        u.close()
        return bugs

    def search(self, irc, msg, args):
        """[--keywords=<keyword>] <bugzilla name> <search string in desc>

        Look for bugs with <search string in the desc>, also matching
        <keywords>. <keywords> can be statuses, severities, priorities, or
        resolutions, seperated by commas"""
        keywords = None
        (optlist, rest) = getopt.getopt(args, '', ['keywords='])
        for (option, arguments) in optlist:
            if option == '--keywords':
                keywords = arguments.split(',')
        (name,searchstr)= privmsgs.getArgs(rest, required=2)
        if not keywords:
            keywords = ['UNCONFIRMED', 'NEW', 'ASSIGNED', 'REOPENED']
        query = self.keywords2query(keywords)
        query.append('short_desc_type=allwordssubstr')
        query.append('short_desc=%s' % urllib.quote(searchstr))
        query.append('order=Bug+Number')
        try:
            name = self.shorthand[name]
            (url, description) = self.db[name]
        except KeyError:
            s = self.registryValue('replyNoBugzilla', msg.args[0])
            irc.error(s % name)
            return
        bugs = self.urlquery2bugslist(url, query)
        bugids = bugs.keys()
        bugids.sort()
        if not bugs:
            irc.error('I could not find any bugs.')
            return
        s = '%s match %r (%s): %s.' % \
            (utils.nItems('bug', len(bugs)), searchstr,
             ' AND '.join(keywords), utils.commaAndify(map(str, bugids)))
        irc.reply(s)

    def bug(self, irc, msg, args):
        """<abbreviation> <number>

        Look up bug <number> in the bugzilla associated with <abbreviation>.
        """
        (name, number) = privmsgs.getArgs(args, required=2)
        try:
            name = self.shorthand[name]
            (url, description) = self.db[name]
        except KeyError:
            s = self.registryValue('replyNoBugzilla', msg.args[0])
            irc.error(s % name)
            return
        queryurl = '%s/xml.cgi?id=%s' % (url, number)
        try:
            summary = self._get_short_bug_summary(queryurl,description,number)
        except BugzillaError, e:
            irc.error(str(e))
            return
        except IOError, e:
            s = '%s.  Try yourself: %s' % (e, queryurl)
            irc.error(s)
        bold = self.registryValue('bold', msg.args[0])
        report = {}
        report['zilla'] = description
        report['id'] = number
        report['url'] = '%s/show_bug.cgi?id=%s' % (url, number)
        report['title'] = str(summary['title'])
        report['summary'] = self._mk_summary_string(summary, bold)
        s = '%(zilla)s bug #%(id)s: %(title)s %(summary)s %(url)s' % report
        irc.reply(s)

    def _mk_summary_string(self, summary, bold):
        L = []
        if bold:
            decorate = lambda s: ircutils.bold(s)
        else:
            decorate = lambda s: s
        if 'product' in summary:
            L.append(decorate('Product: ') + summary['product'])
        if 'component' in summary:
            L.append(decorate('Component: ') + summary['component'])
        if 'severity' in summary:
            L.append(decorate('Severity: ') + summary['severity'])
        if 'assigned to' in summary:
            L.append(decorate('Assigned to: ') + summary['assigned to'])
        if 'status' in summary:
            L.append(decorate('Status: ') + summary['status'])
        if 'resolution' in summary:
            L.append(decorate('Resolution: ') + summary['resolution'])
        return ', '.join(imap(str, L))

    def _get_short_bug_summary(self, url, desc, number):
        try:
            bugxml = self._getbugxml(url, desc)
            zilladom = minidom.parseString(bugxml)
        except Exception, e:
            s = 'Could not parse XML returned by %s bugzilla: %s' % (desc, e)
            raise BugzillaError, s
        bug_n = zilladom.getElementsByTagName('bug')[0]
        if bug_n.hasAttribute('error'):
            errtxt = bug_n.getAttribute('error')
            s = 'Error getting %s bug #%s: %s' % (desc, number, errtxt)
            raise BugzillaError, s
        summary = {}
        try:
            node = bug_n.getElementsByTagName('short_desc')[0]
            summary['title'] = self._getnodetxt(node)
            node = bug_n.getElementsByTagName('bug_status')[0]
            summary['status'] = self._getnodetxt(node)
            try:
                node = bug_n.getElementsByTagName('resolution')[0]
                summary['resolution'] = self._getnodetxt(node)
            except:
                pass
            node = bug_n.getElementsByTagName('assigned_to')[0]
            summary['assigned to'] = self._getnodetxt(node)
            node = bug_n.getElementsByTagName('product')[0]
            summary['product'] = self._getnodetxt(node)
            node = bug_n.getElementsByTagName('component')[0]
            summary['component'] = self._getnodetxt(node)
            node = bug_n.getElementsByTagName('bug_severity')[0]
            summary['severity'] = self._getnodetxt(node)
        except Exception, e:
            s = 'Could not parse XML returned by %s bugzilla: %s' % (desc, e)
            raise BugzillaError, s
        return summary

    def _getbugxml(self, url, desc):
        try:
            bugxml = webutils.getUrl(url)
        except webutils.WebError, e:
            raise IOError, 'Connection to %s bugzilla failed' % desc
        if not bugxml:
            raise IOError, 'Error getting bug content from %s' % desc
        return bugxml

    def _getnodetxt(self, node):
        L = []
        for childnode in node.childNodes:
            if childnode.nodeType == childnode.TEXT_NODE:
                L.append(childnode.data)
        val = ''.join(L)
        if node.hasAttribute('encoding'):
            encoding = node.getAttribute('encoding')
            if encoding == 'base64':
                try:
                    val = val.decode('base64')
                except:
                    val = 'Cannot convert bug data from base64.'
        while self.entre.search(val):
            entity = self.entre.search(val).group(1)
            if entity in entities:
                val = self.entre.sub(entities[entity], val)
            else:
                val = self.entre.sub('?', val)
        return val


Class = Bugzilla

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
