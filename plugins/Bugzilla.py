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
import urllib
import string
import xml.dom.minidom as minidom
import base64
import re
import os
from htmlentitydefs import entitydefs as entities

import plugins

import string

import utils
import privmsgs
import callbacks
import conf
import sqlite

dbfilename = os.path.join(conf.dataDir, 'Bugzilla.db')
def makeDb(filename):
    if os.path.exists(filename):
        return sqlite.connect(filename)
    db = sqlite.connect(filename)
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE bugzillas (
                      shorthand TEXT UNIQUE ON CONFLICT REPLACE,
                      url TEXT,
                      description TEXT
                      )""")
    cursor = db.cursor();
    cursor.execute("""INSERT INTO bugzillas VALUES (%s, %s, %s)""",
                    'rh', 'http://bugzilla.redhat.com/bugzilla', 'Red Hat')
    cursor.execute("""INSERT INTO bugzillas VALUES (%s, %s, %s)""",
                    'gnome', 'http://bugzilla.gnome.org', 'Gnome')
    cursor.execute("""INSERT INTO bugzillas VALUES (%s, %s, %s)""",
                    'xim', 'http://bugzilla.ximian.com', 'Ximian')
    cursor.execute("""INSERT INTO bugzillas VALUES (%s, %s, %s)""",
                    'moz', 'http://bugzilla.mozilla.org', 'Mozilla')
    cursor.execute("""INSERT INTO bugzillas VALUES (%s, %s, %s)""",
                    'gcc', 'http://gcc.gnu.org/bugzilla', 'GCC')
    db.commit()
    return db

class BugError(Exception):
    """A bugzilla error"""
    def __init__(self, args = None):
        Exception.__init__(self)
        self.args = args

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, yn
    onStart.append('load Bugzilla')
    print 'The Bugzilla plugin has the functionality to watch for URLs'
    print 'that match a specific pattern (we call this a snarfer). When'
    print 'supybot sees such a URL, he will parse the web page for information'
    print 'and reply with the results.\n'
    if yn('Do you want the Bugzilla snarfer enabled by default?') == 'n':
        onStart.append('Bugzilla togglesnarfer')

class Bugzilla(callbacks.PrivmsgCommandAndRegexp):
    """Show a link to a bug report with a brief description"""
    threaded = True
    regexps = ['bzSnarfer']
    def __init__(self):
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.entre = re.compile('&(\S*?);')
        self.db = makeDb(dbfilename)
        self.snarfer = True

    def die(self):
        self.db.close()
        del self.db
    
    def togglesnarfer(self, irc, msg, args):
        """takes no argument

        Disables the snarfer that responds to all Bugzilla links
        """
        self.snarfer = not self.snarfer
        if self.snarfer:
            irc.reply(msg, '%s (Snarfer is enabled)' % conf.replySuccess)
        else:
            irc.reply(msg, '%s (Snarfer is disabled)' % conf.replySuccess)
    togglesnarfer=privmsgs.checkCapability(togglesnarfer,'admin')
    def addzilla(self, irc, msg, args):
        """shorthand url description
        Add a bugzilla to the list of defined bugzillae.
        E.g.: addzilla rh http://bugzilla.redhat.com/bugzilla Red Hat Zilla"""
        try:
            words = args
            shorthand = words.pop(0)
            url = words.pop(0)
            description = ' '.join(words)
        except:
            irc.reply(msg, 'Invalid format, please see help addzilla')
            return
        cursor = self.db.cursor()
        cursor.execute("""INSERT INTO bugzillas VALUES (%s, %s, %s)""",
                    shorthand, url, description)
        self.db.commit()
        irc.reply(msg, 'Added bugzilla entry for "%s" with shorthand "%s"' % (
            description, shorthand))
        return

    def delzilla(self, irc, msg, args):
        """shorthand
        Delete a bugzilla from the list of define bugzillae.
        E.g.: delzilla rh"""
        shorthand = ' '.join(args)
        cursor = self.db.cursor()
        cursor.execute("""SELECT * from bugzillas where shorthand = %s""", shorthand)
        if cursor.rowcount == 0:
            irc.reply(msg, 'Bugzilla "%s" not defined. Try zillalist.' % shorthand)
            return
        cursor.execute("""DELETE FROM bugzillas where shorthand = %s""", shorthand)
        self.db.commit()
        irc.reply(msg, 'Deleted bugzilla "%s"' % shorthand)
        return

    def listzilla(self, irc,  msg, args):
        """[shorthand]
        List defined bugzillae
        E.g.: listzilla rh; or just listzilla"""
        shorthand = ' '.join(args)
        if shorthand:
            cursor = self.db.cursor()
            cursor.execute("""SELECT url,description from bugzillas where shorthand = %s""", shorthand)
            if cursor.rowcount == 0:
                irc.reply(msg, 'No such bugzilla defined: "%s".' % shorthand)
                return
            url, description = cursor.fetchone()
            irc.reply(msg, '%s: %s, %s' % (shorthand, description, url))
            return
        else:
            cursor = self.db.cursor()
            cursor.execute("""SELECT shorthand from bugzillas""")
            if cursor.rowcount == 0:
                irc.reply(msg, 'No bugzillae defined. Add some with "addzilla"!')
                return
            results = ['%s' % (item[0]) for item in cursor.fetchall()]
            irc.reply(msg, 'Defined bugzillae: %s' % ' '.join(results))
            return    
    def bzSnarfer(self, irc, msg, match):
        r"(.*)/show_bug.cgi\?id=([0-9]+)"
        if not self.snarfer:
            return
        queryurl = '%s/xml.cgi?id=%s' % (match.group(1), match.group(2))
        try:
            summary = self._get_short_bug_summary(queryurl, "Snarfed Bugzilla URL", match.group(2))
        except BugError, e:
            irc.reply(msg, str(e))
            return
        except IOError, e:
            msgtouser = '%s. Try yourself: %s' % (e, queryurl)
            irc.reply(msg, msgtouser)
            return
        report = {}
        report['zilla'] = "Snarfed Bugzilla URL"
        report['id'] = match.group(2)
        report['url'] = str('%s/show_bug.cgi?id=%s' % (match.group(1), match.group(2)))
        report['title'] = str(summary['title'])
        report['summary'] = str(self._mk_summary_string(summary))
        irc.reply(msg, '%(zilla)s bug #%(id)s: %(title)s' % report)
        irc.reply(msg, '  %(summary)s' % report)
        irc.reply(msg, '  %(url)s' % report)
        
    def bug(self, irc, msg, args):
        """bug shorthand number
        Look up a bug number in a bugzilla.
        E.g.: bug rh 10301"""
        try: shorthand, num = args
        except:
            irc.reply(msg, 'Invalid format. Try help bug')
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT url,description from bugzillas where shorthand = %s""", shorthand)
        if cursor.rowcount == 0:
            irc.reply(msg, 'Bugzilla "%s" is not defined.' % shorthand)
            return
        if not self._is_bug_number(num):
            irc.reply(msg, '"%s" does not seem to be a number' % num)
            return
        url, desc = cursor.fetchone()
        queryurl = '%s/xml.cgi?id=%s' % (url, num)
        try:
            summary = self._get_short_bug_summary(queryurl, desc, num)
        except BugError, e:
            irc.reply(msg, str(e))
            return
        except IOError, e:
            msgtouser = '%s. Try yourself: %s' % (e, queryurl)
            irc.reply(msg, msgtouser)
            return

        report = {}
        report['zilla'] = str(desc)
        report['id'] = str(num)
        report['url'] = str('%s/show_bug.cgi?id=%s' % (url, num))
        report['title'] = str(summary['title'])
        report['summary'] = str(self._mk_summary_string(summary))
        irc.reply(msg, '%(zilla)s bug #%(id)s: %(title)s' % report)
        irc.reply(msg, '  %(summary)s' % report)
        irc.reply(msg, '  %(url)s' % report)
        return

    def _mk_summary_string(self, summary):
        ary = []
        if summary.has_key('component'):
            ary.append('Component: %s' % summary['component'])
        if summary.has_key('severity'):
            ary.append('Severity: %s' % summary['severity'])
        if summary.has_key('assigned to'):
            ary.append('Assigned to: %s' % summary['assigned to'])
        if summary.has_key('status'):
            if summary.has_key('resolution'):
                ary.append('Status: %s/%s' %
                           (summary['status'], summary['resolution']))
            else:
                ary.append('Status: %s' % summary['status'])
        out = string.join(ary, ', ')
        return out

    def _is_bug_number(self, bug):
        try: int(bug)
        except: return 0
        else: return 1
        
    def _get_short_bug_summary(self, url, desc, num):
        bugxml = self._getbugxml(url, desc)
        try: zilladom = minidom.parseString(bugxml)
        except Exception, e:
            msg = 'Could not parse XML returned by %s bugzilla: %s'
            raise BugError(str(msg % (desc, e)))
        bug_n = zilladom.getElementsByTagName('bug')[0]
        if bug_n.hasAttribute('error'):
            errtxt = bug_n.getAttribute('error')
            zilladom.unlink()
            msg = 'Error getting %s bug #%s: %s' % (desc, num, errtxt)
            raise BugError(str(msg))
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
            node = bug_n.getElementsByTagName('component')[0]
            summary['component'] = self._getnodetxt(node)
            node = bug_n.getElementsByTagName('bug_severity')[0]
            summary['severity'] = self._getnodetxt(node)
        except Exception, e:
            zilladom.unlink()
            msg = 'Could not parse XML returned by %s bugzilla: %s'
            raise BugError(str(msg % (desc, e)))
        zilladom.unlink()
        return summary

    def _getbugxml(self, url, desc):
        try: fh = urllib.urlopen(url)
        except: raise IOError('Connection to %s bugzilla failed' % desc)
        bugxml = ''
        while 1:
            chunk = fh.read(8192)
            if chunk == '':
                break
            bugxml = bugxml + chunk
        fh.close()
        if not len(bugxml):
            msg = 'Error getting bug content from %s' % desc
            raise IOError(msg)
        return bugxml

    def _getnodetxt(self, node):
        val = ''
        for childnode in node.childNodes:
            if childnode.nodeType == childnode.TEXT_NODE:
                val = val + childnode.data
        if node.hasAttribute('encoding'):
            encoding = node.getAttribute('encoding')
            if encoding == 'base64':
                try:
                    val = base64.decodestring(val)
                except:
                    val = 'Cannot convert bug data from base64!'
        entre = self.entre
        while entre.search(val):
            entity = entre.search(val).group(1)
            if entities.has_key(entity):
                val = re.sub(entre, entities[entity], val)
            else:
                val = re.sub(entre, '_', val)
        return val
Class = Bugzilla
