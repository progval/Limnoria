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
import string
import urllib2
import xml.dom.minidom as minidom
from itertools import imap, ifilter
from htmlentitydefs import entitydefs as entities

import conf
import utils

import plugins
import ircutils
import privmsgs
import callbacks
import structures
import configurable

dbfilename = os.path.join(conf.dataDir, 'Bugzilla.db')
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

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, yn
    onStart.append('load Bugzilla')
    print 'The Bugzilla plugin has the functionality to watch for URLs'
    print 'that match a specific pattern (we call this a snarfer). When'
    print 'supybot sees such a URL, he will parse the web page for'
    print 'information and reply with the results.\n'
    if yn('Do you want this bug snarfer enabled by default?') == 'y':
        onStart.append('Bugzilla config bug-snarfer on')

replyNoBugzilla = 'I don\'t have a bugzilla %r'

class Bugzilla(callbacks.PrivmsgCommandAndRegexp, configurable.Mixin):
    """Show a link to a bug report with a brief description"""
    threaded = True
    regexps = ['bzSnarfer']
    configurables = configurable.Dictionary(
        [('bug-snarfer', configurable.BoolType, False,
         """Determines whether the bug snarfer will be enabled, such that any
         Bugzilla URLs seen in the channel will have their information reported
         into the channel.""")]
    )
    def __init__(self):
        configurable.Mixin.__init__(self)
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.entre = re.compile('&(\S*?);')
        # Schema: {name, [url, description]}
        self.db = makeDb(dbfilename)
        self.shorthand = utils.abbrev(self.db.keys())

    def die(self):
        configurable.Mixin.die(self)
        self.db.close()
        del self.db
    
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
        irc.reply(msg, conf.replySuccess)

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
            irc.reply(msg, conf.replySuccess)
        except KeyError:
            irc.error(msg, replyNoBugzilla % name)

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
                irc.reply(msg, '%s: %s, %s' % (name, description, url))
            except KeyError:
                irc.error(msg, replyNoBugzilla % name)
        else:
            if self.db:
                L = self.db.keys()
                L.sort()
                irc.reply(msg, utils.commaAndify(L))
            else:
                irc.reply(msg, 'I have no defined bugzillae.')

    def bzSnarfer(self, irc, msg, match):
        r"(http://\S+)/show_bug.cgi\?id=([0-9]+)"
        if not self.configurables.get('bug-snarfer', channel=msg.args[0]):
            return
        queryurl = '%s/xml.cgi?id=%s' % (match.group(1), match.group(2))
        try:
            summary = self._get_short_bug_summary(queryurl, 'Snarfed '\
                'Bugzilla URL', match.group(2))
        except BugzillaError, e:
            irc.reply(msg, str(e))
            return
        except IOError, e:
            msgtouser = '%s. Try yourself: %s' % (e, queryurl)
            irc.reply(msg, msgtouser)
            return
        report = {}
        report['id'] = match.group(2)
        report['url'] = str('%s/show_bug.cgi?id=%s' % (match.group(1),
            match.group(2)))
        report['title'] = str(summary['title'])
        report['summary'] = str(self._mk_summary_string(summary))
        report['product'] = str(summary['product'])
        s = '%(product)s bug #%(id)s: %(title)s %(summary)s' % report
        irc.reply(msg, s, prefixName=False)
    bzSnarfer = privmsgs.urlSnarfer(bzSnarfer)
        
    def bug(self, irc, msg, args):
        """<abbreviation> <number>

        Look up bug <number> in the bugzilla associated with <abbreviation>.
        """
        (name, number) = privmsgs.getArgs(args, required=2)
        try:
            name = self.shorthand[name]
            (url, description) = self.db[name]
        except KeyError:
            irc.error(msg, replyNoBugzilla % name)
            return
        queryurl = '%s/xml.cgi?id=%s' % (url, number)
        try:
            summary = self._get_short_bug_summary(queryurl,description,number)
        except BugzillaError, e:
            irc.error(msg, str(e))
            return
        except IOError, e:
            s = '%s.  Try yourself: %s' % (e, queryurl)
            irc.error(msg, s)
        report = {}
        report['zilla'] = description
        report['id'] = number
        report['url'] = '%s/show_bug.cgi?id=%s' % (url, number)
        report['title'] = str(summary['title'])
        report['summary'] = self._mk_summary_string(summary)
        s = '%(zilla)s bug #%(id)s: %(title)s %(summary)s %(url)s' % report
        irc.reply(msg, s)

    def _mk_summary_string(self, summary):
        L = []
        if 'product' in summary:
            L.append(ircutils.bold('Product: ') + summary['product'])
        if 'component' in summary:
            L.append(ircutils.bold('Component: ') + summary['component'])
        if 'severity' in summary:
            L.append(ircutils.bold('Severity: ') + summary['severity'])
        if 'assigned to' in summary:
            L.append(ircutils.bold('Assigned to: ') + summary['assigned to'])
        if 'status' in summary:
            L.append(ircutils.bold('Status: ') + summary['status'])
        if 'resolution' in summary:
            L.append(ircutils.bold('Resolution: ') + summary['resolution'])
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
            fh = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            raise IOError, 'Connection to %s bugzilla failed' % desc
        bugxml = fh.read()
        fh.close()
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
