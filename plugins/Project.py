#!/usr/bin/python

###
# Copyright (c) 2004, Jeremiah Fincher
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
This plugin handles public collaboration on projects in channels.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import os
import time
import string
import os.path
from itertools import ilen

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Project', True)

Project = conf.registerPlugin('Project')
conf.registerChannelValue(conf.supybot.plugins.Project, 'default',
    registry.String('', """Determines what the default project for this channel
    is."""))

class Record(object):
    __metaclass__ = dbi.Record
    __fields__ = [
        'desc',
        'by',
        'at',
        ]

class TrackerDB(dbi.DB):
    Mapping = 'flat'
    Record = Record
        
class ProjectDB(object):
    def __init__(self, channel, project):
        dir = plugins.makeChannelFilename(channel, 'Projects')
        if not os.path.exists(dir):
            os.mkdir(dir)
        self.projectDir = os.path.join(dir, project)
        if not os.path.exists(self.projectDir):
            os.mkdir(self.projectDir)
        self._fixes = TrackerDB(os.path.join(self.projectDir, 'Fixes.db'))
        self._features = TrackerDB(os.path.join(self.projectDir, 'Features.db'))
        started = os.path.join(self.projectDir, 'started')
        if not os.path.exists(started):
            fd = file(started, 'w')
            try:
                fd.write(str(int(time.time())))
            finally:
                fd.close()

    def fix(self, by, desc):
        return self._fixes.add(Record(desc=desc, by=by, at=time.time()))

    def feature(self, by, desc):
        return self._features.add(Record(desc=desc, by=by, at=time.time()))

    def getFix(self, id):
        return self._fixes.get(id)

    def getFeature(self, id):
        return self._features.get(id)

    def fixes(self):
        return list(self._fixes)

    def features(self):
        return list(self._features)

    def numFixes(self):
        return ilen(self._fixes)

    def numFeatures(self):
        return ilen(self._features)

    def started(self):
        fd = file(os.path.join(self.projectDir, 'started'))
        try:
            return int(fd.read().strip())
        finally:
            fd.close()
            
class ProjectsDB(object):
    def __init__(self):
        self.dbs = ircutils.IrcDict()
        listing = os.listdir
        for basename in listing(conf.supybot.directories.data()):
            dirname = conf.supybot.directories.data.dirize(basename)
            if ircutils.isChannel(basename) and 'Projects' in listing(dirname):
                assert os.path.isdir(dirname)
                for project in listing(os.path.join(dirname, 'Projects')):
                    self.newProject(basename, project)
        
    def _getDb(self, channel, project):
        return self.dbs[channel][project]
    
    def fix(self, channel, project, by, description):
        """Returns the new id of a bug fixed."""
        return self._getDb(channel, project).fix(by, description)

    def fixes(self, channel, project):
        """Returns a list of (id, description) pairs of the fixes."""
        return self._getDb(channel, project).fixes()

    def feature(self, channel, project, by, description):
        """returns the new id of a feature added."""
        return self._getDb(channel, project).feature(by, description)

    def getFix(self, channel, project, id):
        return self._getDb(channel, project).getFix(id)

    def getFeature(self, channel, project, id):
        return self._getDb(channel, project).getFeature(id)

    def features(self, channel, project):
        """Returns a list of (id, description) pairs of the features."""
        return self._getDb(channel, project).features()
        
    def numFixes(self, channel, project):
        """Returns the number of fixes on project."""
        return self._getDb(channel, project).numFixes()

    def numFeatures(self, channel, project):
        """Returns the number of features on project."""
        return self._getDb(channel, project).numFeatures()

    def started(self, channel, project):
        """Returns when the project was began."""
        return self._getDb(channel, project).started()

    def newProject(self, channel, project):
        """Starts a new project named project on channel."""
        if project in ('.', '..'):
            raise ValueError, 'Invalid project name.'
        if channel not in self.dbs:
            self.dbs[channel] = ircutils.IrcDict()
        if project not in self.dbs[channel]:
            self.dbs[channel][project] = ProjectDB(channel, project)

    def projects(self, channel):
        """Returns the projects on channel."""
        dir = plugins.makeChannelFilename(channel, 'Projects')
        return os.listdir(conf.supybot.directories.data.dirize(dir))

    def isProject(self, channel, project):
        """Returns whether project is a project in channel."""
        return project in ircutils.IrcSet(self.projects(channel))
        
        
class Project(callbacks.Privmsg):
    def __init__(self):
        self.db = ProjectsDB()
        callbacks.Privmsg.__init__(self)
        
    def _getProject(self, channel, args):
        if args and self.db.isProject(channel, args[0]):
            project = args.pop(0)
        else:
            project = self.registryValue('default', channel)
        if project:
            return project
        else:
            raise callbacks.ArgumentError

    def _getUserId(self, irc, msg):
        try:
            return ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered(Raise=True)
    
    def add(self, irc, msg, args):
        """[<channel>] <project>

        Adds <project> to the projects in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        project = privmsgs.getArgs(args)
        try:
            self.db.newProject(channel, project)
            irc.replySuccess()
        except ValueError, e:
            irc.error('That\'s not a valid project name.')

    def default(self, irc, msg, args):
        """[<channel>] [<project>]

        If <project> is given, sets the default project in <channel> to
        <project>.  Otherwise, returns the current default project for
        <channel>.  <channel> is only necessary if the message isn't sent in
        the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        project = privmsgs.getArgs(args, required=0, optional=1)
        if project:
            cap = ircdb.makeChannelCapability(channel, 'op')
            if not ircdb.checkCapability(msg.prefix, cap):
                irc.errorNoCapability(cap, Raise=True)
            if self.db.isProject(channel, project):
                self.setRegistryValue('default', project, channel)
                irc.replySuccess()
            else:
                irc.error('That\'s not a valid project in %s.' % channel)
        else:
            project = self.registryValue('default', channel)
            if project:
                irc.reply(project)
            else:
                irc.reply('There is currently no default project in %s.' %
                          channel)
            
    def fix(self, irc, msg, args):
        """[<channel>] [<project>] <description>

        Fixes a bug on <project> for <channel>, describing the bug with
        <description>.  If <project> is not provided, the default project for
        <channel> will be used.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        project = self._getProject(channel, args)
        description = privmsgs.getArgs(args)
        userid = self._getUserId(irc, msg)
        id = self.db.fix(channel, project, userid, description)
        irc.replySuccess('Fix #%s added.' %  id)

    def feature(self, irc, msg, args):
        """[<channel>] [<project>] <description>

        Adds a feature to <project> for <channel>, describing the feature
        with <description>.  If <project> is not provided, the default project
        for <channel> will be used.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        project = self._getProject(channel, args)
        description = privmsgs.getArgs(args)
        userid = self._getUserId(irc, msg)
        id = self.db.feature(channel, project, userid, description)
        irc.replySuccess('Feature #%s added.' %  id)

    def get(self, irc, msg, args):
        """[<channel>] [<project>] {fix,feature} <id>

        Returns the fix or feature with the given id.  If <project> is not
        provided, the default project for <channel> will be used. <channel> is
        only necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        project = self._getProject(channel, args)
        (kind, id) = privmsgs.getArgs(args, required=2)
        if kind not in ('fix', 'feature'):
            irc.error('That\'s not a valid kind to get, "fix" and '
                      '"feature" are the only two valid kinds to get.',
                      Raise=True)
        try:
            id = int(id)
            if kind == 'fix':
                record = self.db.getFix(channel, project, id)
            else:
                record = self.db.getFeature(channel, project, id)
        except (ValueError, KeyError):
            irc.error('That\'s not a valid id.', Raise=True)
        name = ircdb.users.getUser(record.by).name
        irc.reply('%s (%s)' % (record.desc, name))
            
    def _formatRecord(self, record):
        desc = utils.ellipsisify(record.desc, 30)
        name = ircdb.users.getUser(record.by).name
        return '#%s: %s (%s)' % (record.id, desc, name)

    def fixes(self, irc, msg, args):
        """[<channel>] [<project>]

        Returns the fixes on <project> for <channel> in reverse chronological
        order.  If <project> is not provided, the default project for <channel>
        will be used.  <channel> is only necessary if the message isn't sent in
        the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        project = self._getProject(channel, args)
        fixes = self.db.fixes(channel, project)
        fixes.reverse() # Highest ids first.
        L = map(self._formatRecord, fixes)
        irc.reply(utils.commaAndify(L))

    def features(self, irc, msg, args):
        """[<channel>] [<project>]

        Returns the features on <project> for <channel> in reverse chronological
        order.  If <project> is not provided, the default project for <channel>
        will be used.  <channel> is only necessary if the message isn't sent in
        the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        project = self._getProject(channel, args)
        features = self.db.features(channel, project)
        features.reverse()
        L = map(self._formatRecord, features)
        irc.reply(utils.commaAndify(L))

    def summary(self, irc, msg, args):
        """[<channel>] [<project>]

        Returns a summary of <project> for <channel>.  If <project> is not
        given, it defaults to the currently active project on <channel>.
        <channel> is only necessary if the message isn't sent on the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        project = self._getProject(channel, args)
        fixes = self.db.numFixes(channel, project)
        features = self.db.numFeatures(channel, project)
        now = time.time()
        when = self.db.started(channel, project)
        elapsed = utils.timeElapsed(now-when)
        L = []
        L.append('%s has been active for %s' % (project, elapsed))
        L.append('has had %s and %s' % (utils.nItems('fix', fixes),
                                        utils.nItems('feature', features)))
        irc.reply(utils.commaAndify(L) + '.')

    def projects(self, irc, msg, args):
        """[<channel>]

        Lists the projects currently active for <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        projects = self.db.projects(channel)
        if projects:
            projects.sort()
            irc.reply(utils.commaAndify(projects))
        else:
            irc.reply('There are no currently active projects for %s.'%channel)
        

Class = Project

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
