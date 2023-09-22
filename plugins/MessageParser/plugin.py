###
# Copyright (c) 2010, Daniel Folkinshteyn
# Copyright (c) 2010-2021, Valentin Lorentz
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

import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import supybot.conf as conf
import supybot.ircdb as ircdb

import re
import os
import sys
import time

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('MessageParser')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

#try:
    #import sqlite
#except ImportError:
    #raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           #'plugin.  Download it at ' \
                           #'<http://code.google.com/p/pysqlite/>'

import sqlite3

# these are needed cuz we are overriding getdb
import threading
import supybot.world as world


import supybot.log as log


class MessageParser(callbacks.Plugin, plugins.ChannelDBHandler):
    """This plugin can set regexp triggers to activate the bot.
    Use 'add' command to add regexp trigger, 'remove' to remove."""
    threaded = True
    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)

    def makeDb(self, filename):
        """Create the database and connect to it."""
        if os.path.exists(filename):
            db = sqlite3.connect(filename)
            if minisix.PY2:
                db.text_factory = str
            return db
        db = sqlite3.connect(filename)
        if minisix.PY2:
            db.text_factory = str
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE triggers (
                          id INTEGER PRIMARY KEY,
                          regexp TEXT UNIQUE ON CONFLICT REPLACE,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          usage_count INTEGER,
                          action TEXT,
                          locked BOOLEAN
                          )""")
        db.commit()
        return db

    # override this because sqlite3 doesn't have autocommit
    # use isolation_level instead.
    def getDb(self, channel):
        """Use this to get a database for a specific channel."""
        currentThread = threading.currentThread()
        if channel not in self.dbCache and currentThread == world.mainThread:
            self.dbCache[channel] = self.makeDb(self.makeFilename(channel))
        if currentThread != world.mainThread:
            db = self.makeDb(self.makeFilename(channel))
        else:
            db = self.dbCache[channel]
        db.isolation_level = None
        return db

    def _updateRank(self, network, channel, regexp):
        subfolder = None if channel == 'global' else channel
        if self.registryValue('keepRankInfo', subfolder, network):
            db = self.getDb(channel)
            cursor = db.cursor()
            cursor.execute("""SELECT usage_count
                      FROM triggers
                      WHERE regexp=?""", (regexp,))
            old_count = cursor.fetchall()[0][0]
            cursor.execute("UPDATE triggers SET usage_count=? WHERE regexp=?", (old_count + 1, regexp,))
            db.commit()

    def _runCommandFunction(self, irc, msg, command, action_name):
        """Run a command from message, as if command was sent over IRC."""
        try:
            tokens = callbacks.tokenize(command,
                channel=msg.channel, network=irc.network)
        except SyntaxError as e:
            # Emulate what callbacks.py does
            self.log.debug('Error return: %s', utils.exnToString(e))
            irc.error(format('%s, in %r (triggered by %r)',
                             e, command, action_name))
        try:
            self.Proxy(irc.irc, msg, tokens)
        except Exception as e:
            log.exception('Uncaught exception in function called by MessageParser:')

    def _checkManageCapabilities(self, irc, msg, channel):
        """Check if the user has any of the required capabilities to manage
        the regexp database."""
        capabilities = self.registryValue('requireManageCapability')
        if capabilities:
            for capability in re.split(r'\s*;\s*', capabilities):
                if capability.startswith('channel,'):
                    capability = capability[8:]
                    if channel != 'global':
                        capability = ircdb.makeChannelCapability(channel, capability)
                if capability and ircdb.checkCapability(msg.prefix, capability):
                    #print "has capability:", capability
                    return True
            return False
        else:
            return True

    def do_privmsg_notice(self, irc, msg):
        channel = msg.channel
        if not channel:
            return

        if 'batch' in msg.server_tags:
            parent_batches = irc.state.getParentBatches(msg)
            parent_batch_types = [batch.type for batch in parent_batches]
            if 'chathistory' in parent_batch_types:
                # Either sent automatically by the server upon join,
                # or triggered by a plugin (why?!)
                # Either way, replying to messages from the history would
                # look weird, because they may have been sent a while ago,
                # and we may have already answered them.
                # (this is the same behavior as in Owner.doPrivmsg and
                # PluginRegexp.doPrivmsg)
                return

        if self.registryValue('enable', channel, irc.network):
            actions = []
            results = []
            for channel in set(map(plugins.getChannel, (channel, 'global'))):
                db = self.getDb(channel)
                cursor = db.cursor()
                cursor.execute("SELECT regexp, action FROM triggers")
                # Fetch results and prepend channel name or 'global'. This
                # prevents duplicating the following lines.
                results.extend([(channel,)+x for x in cursor.fetchall()])
            if len(results) == 0:
                return
            max_triggers = self.registryValue('maxTriggers', channel, irc.network)
            for (channel, regexp, action) in results:
                try:
                    for match in re.finditer(regexp, msg.args[1]):
                        if match is not None:
                            thisaction = action
                            self._updateRank(irc.network, channel, regexp)
                            for (i, j) in enumerate(match.groups()):
                                if match.group(i+1) is not None:
                                    # Need a lambda to prevent re.sub from
                                    # interpreting backslashes in the replacement
                                    thisaction = re.sub(r'\$' + str(i+1), lambda _: match.group(i+1), thisaction)
                            actions.append((regexp, thisaction))
                            if max_triggers != 0 and max_triggers == len(actions):
                                break
                    if max_triggers != 0 and max_triggers == len(actions):
                        break
                except Exception:
                    self.log.exception('Error while handling %r', regexp)


            for (regexp, action) in actions:
                self._runCommandFunction(irc, msg, action, regexp)

    def doPrivmsg(self, irc, msg):
        if not callbacks.addressed(irc, msg): #message is not direct command
            self.do_privmsg_notice(irc, msg)

    def doNotice(self, irc, msg):
        if self.registryValue('enableForNotices', msg.channel, irc.network):
            self.do_privmsg_notice(irc, msg)

    @internationalizeDocstring
    def add(self, irc, msg, args, channel, regexp, action):
        """[<channel>|global] <regexp> <action>

        Associates <regexp> with <action>.  <channel> is only
        necessary if the message isn't sent on the channel
        itself.  Action is echoed upon regexp match, with variables $1, $2,
        etc. being interpolated from the regexp match groups."""
        if not self._checkManageCapabilities(irc, msg, channel):
            capabilities = self.registryValue('requireManageCapability')
            irc.errorNoCapability(capabilities, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id, usage_count, locked FROM triggers WHERE regexp=?", (regexp,))
        results = cursor.fetchall()
        if len(results) != 0:
            (id, usage_count, locked) = list(map(int, results[0]))
        else:
            locked = 0
            usage_count = 0
        if not locked:
            try:
                re.compile(regexp)
            except Exception as e:
                irc.error(_('Invalid python regexp: %s') % (e,))
                return
            if ircdb.users.hasUser(msg.prefix):
                name = ircdb.users.getUser(msg.prefix).name
            else:
                name = msg.nick
            cursor.execute("""INSERT INTO triggers VALUES
                              (NULL, ?, ?, ?, ?, ?, ?)""",
                            (regexp, name, int(time.time()), usage_count, action, locked,))
            db.commit()
            irc.replySuccess()
        else:
            irc.error(_('That trigger is locked.'))
            return
    add = wrap(add, ['channelOrGlobal', 'something', 'something'])

    @internationalizeDocstring
    def remove(self, irc, msg, args, channel, optlist, regexp):
        """[<channel>|global] [--id] <regexp>]

        Removes the trigger for <regexp> from the triggers database.
        <channel> is only necessary if
        the message isn't sent in the channel itself.
        If option --id specified, will retrieve by regexp id, not content.
        """
        if not self._checkManageCapabilities(irc, msg, channel):
            capabilities = self.registryValue('requireManageCapability')
            irc.errorNoCapability(capabilities, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        target = 'regexp'
        for (option, arg) in optlist:
            if option == 'id':
                target = 'id'
        sql = "SELECT id, locked FROM triggers WHERE %s=?" % (target,)
        cursor.execute(sql, (regexp,))
        results = cursor.fetchall()
        if len(results) != 0:
            (id, locked) = list(map(int, results[0]))
        else:
            irc.error(_('There is no such regexp trigger.'))
            return

        if locked:
            irc.error(_('This regexp trigger is locked.'))
            return

        cursor.execute("""DELETE FROM triggers WHERE id=?""", (id,))
        db.commit()
        irc.replySuccess()
    remove = wrap(remove, ['channelOrGlobal',
                            getopts({'id': '',}),
                            'something'])

    @internationalizeDocstring
    def lock(self, irc, msg, args, channel, regexp):
        """[<channel>|global] <regexp>

        Locks the <regexp> so that it cannot be
        removed or overwritten to.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        if not self._checkManageCapabilities(irc, msg, channel):
            capabilities = self.registryValue('requireManageCapability')
            irc.errorNoCapability(capabilities, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id FROM triggers WHERE regexp=?", (regexp,))
        results = cursor.fetchall()
        if len(results) == 0:
            irc.error(_('There is no such regexp trigger.'))
            return
        cursor.execute("UPDATE triggers SET locked=1 WHERE regexp=?", (regexp,))
        db.commit()
        irc.replySuccess()
    lock = wrap(lock, ['channelOrGlobal', 'text'])

    @internationalizeDocstring
    def unlock(self, irc, msg, args, channel, regexp):
        """[<channel>|global] <regexp>

        Unlocks the entry associated with <regexp> so that it can be
        removed or overwritten.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        if not self._checkManageCapabilities(irc, msg, channel):
            capabilities = self.registryValue('requireManageCapability')
            irc.errorNoCapability(capabilities, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id FROM triggers WHERE regexp=?", (regexp,))
        results = cursor.fetchall()
        if len(results) == 0:
            irc.error(_('There is no such regexp trigger.'))
            return
        cursor.execute("UPDATE triggers SET locked=0 WHERE regexp=?", (regexp,))
        db.commit()
        irc.replySuccess()
    unlock = wrap(unlock, ['channelOrGlobal', 'text'])

    @internationalizeDocstring
    def show(self, irc, msg, args, channel, optlist, regexp):
        """[<channel>|global] [--id] <regexp>

        Looks up the value of <regexp> in the triggers database.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        If option --id specified, will retrieve by regexp id, not content.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        target = 'regexp'
        for (option, arg) in optlist:
            if option == 'id':
                target = 'id'
        sql = "SELECT regexp, action FROM triggers WHERE %s=?" % (target,)
        cursor.execute(sql, (regexp,))
        results = cursor.fetchall()
        if len(results) != 0:
            (regexp, action) = results[0]
        else:
            irc.error(_('There is no such regexp trigger.'))
            return

        irc.reply("The action for regexp trigger \"%s\" is \"%s\"" % (regexp, action))
    show = wrap(show, ['channelOrGlobal',
                        getopts({'id': '',}),
                        'something'])

    @internationalizeDocstring
    def info(self, irc, msg, args, channel, optlist, regexp):
        """[<channel>|global] [--id] <regexp>

        Display information about <regexp> in the triggers database.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        If option --id specified, will retrieve by regexp id, not content.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        target = 'regexp'
        for (option, arg) in optlist:
            if option == 'id':
                target = 'id'
        sql = "SELECT * FROM triggers WHERE %s=?" % (target,)
        cursor.execute(sql, (regexp,))
        results = cursor.fetchall()
        if len(results) != 0:
            (id, regexp, added_by, added_at, usage_count,
                    action, locked) = results[0]
        else:
            irc.error(_('There is no such regexp trigger.'))
            return

        irc.reply(_("The regexp id is %d, regexp is \"%s\", and action is"
                    " \"%s\". It was added by user %s on %s, has been "
                    "triggered %d times, and is %s.") % (id,
                    regexp,
                    action,
                    added_by,
                    time.strftime(conf.supybot.reply.format.time(),
                                     time.localtime(int(added_at))),
                    usage_count,
                    locked and _("locked") or _("not locked"),))
    info = wrap(info, ['channelOrGlobal',
                        getopts({'id': '',}),
                        'something'])

    @internationalizeDocstring
    def list(self, irc, msg, args, channel):
        """[<channel>|global]

        Lists regexps present in the triggers database.
        <channel> is only necessary if the message isn't sent in the channel
        itself. Regexp ID listed in parentheses.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT regexp, id FROM triggers ORDER BY id")
        results = cursor.fetchall()
        if len(results) != 0:
            regexps = results
        else:
            irc.reply(_('There are no regexp triggers in the database.'))
            return

        s = [ "%s: %s" % (ircutils.bold('#'+str(regexp[1])), regexp[0]) for regexp in regexps ]
        separator = self.registryValue('listSeparator', channel, irc.network)
        irc.reply(separator.join(s))
    list = wrap(list, ['channelOrGlobal'])

    @internationalizeDocstring
    def rank(self, irc, msg, args, channel):
        """[<channel>|global]

        Returns a list of top-ranked regexps, sorted by usage count
        (rank). The number of regexps returned is set by the
        rankListLength registry value. <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        numregexps = self.registryValue('rankListLength', channel, irc.network)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT regexp, usage_count
                          FROM triggers
                          ORDER BY usage_count DESC
                          LIMIT ?""", (numregexps,))
        regexps = cursor.fetchall()
        if len(regexps) == 0:
            irc.reply(_('There are no regexp triggers in the database.'))
            return
        s = [ "#%d \"%s\" (%d)" % (i+1, regexp[0], regexp[1]) for i, regexp in enumerate(regexps) ]
        irc.reply(", ".join(s))
    rank = wrap(rank, ['channelOrGlobal'])

    @internationalizeDocstring
    def vacuum(self, irc, msg, args, channel):
        """[<channel>|global]

        Vacuums the database for <channel>.
        See SQLite vacuum doc here: http://www.sqlite.org/lang_vacuum.html
        <channel> is only necessary if the message isn't sent in
        the channel itself.
        First check if user has the required capability specified in plugin
        config requireVacuumCapability.
        """
        capability = self.registryValue('requireVacuumCapability')
        if capability:
            if not ircdb.checkCapability(msg.prefix, capability):
                irc.errorNoCapability(capability, Raise=True)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""VACUUM""")
        db.commit()
        irc.replySuccess()
    vacuum = wrap(vacuum, ['channelOrGlobal'])
MessageParser = internationalizeDocstring(MessageParser)

Class = MessageParser


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
