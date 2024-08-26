###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009-2010, James McCoy
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

import os
import sys
import time
import string

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.utils.minisix as minisix
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.httpserver as httpserver
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Factoids')

import sqlite3

import re
from supybot.utils.seq import dameraulevenshtein

def getFactoid(irc, msg, args, state):
    assert not state.channel
    callConverter('channel', irc, msg, args, state)
    separator = state.cb.registryValue('learnSeparator',
                                       state.channel, irc.network)
    try:
        i = args.index(separator)
    except ValueError:
        raise callbacks.ArgumentError
    args.pop(i)
    key = []
    value = []
    for (j, s) in enumerate(args[:]):
        if j < i:
            key.append(args.pop(0))
        else:
            value.append(args.pop(0))
    if not key or not value:
        raise callbacks.ArgumentError
    state.args.append(' '.join(key))
    state.args.append(' '.join(value))

def getFactoidId(irc, msg, args, state):
    Type = 'key id'
    p = lambda i: i > 0
    callConverter('int', irc, msg, args, state, Type, p)

addConverter('factoid', getFactoid)
addConverter('factoidId', getFactoidId)


PAGE_SKELETON = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Factoids</title>
    <link rel="stylesheet" href="/default.css" />
</head>
%s
</html>"""

DEFAULT_TEMPLATES = {
        'factoids/index.html': PAGE_SKELETON % """\
<body class="purelisting">
    <h1>Factoids</h1>
    <form action="." method="post">
        <label for="chan">Channel name:</label>
        <input type="text" placeholder="#channel" name="chan" id="chan" />
        <input type="submit" name="submit" value="view" />
    </form>
</body>""",
        'factoids/channel.html': PAGE_SKELETON % """\
<body class="puretable">
    <h1>Factoids of %(channel)s</h1>
    <table>
        <tr class="header">
            <th class="key">""" + _('key') + """</th>
            <th class="id">""" + _('id') + """</th>
            <th class="fact">""" + _('fact') + """</th>
        </tr>
        %(rows)s
    </table>
</body>"""
}
httpserver.set_default_templates(DEFAULT_TEMPLATES)

class FactoidsCallback(httpserver.SupyHTTPServerCallback):
    name = 'Factoids web interface'

    def doGetOrHead(self, handler, path, write_content):
        parts = path.split('/')[1:]
        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.write(httpserver.get_template('factoids/index.html'))
        elif len(parts) == 2:
            channel = utils.web.urlunquote(parts[0])
            if not ircutils.isChannel(channel):
                self.send_response(404)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                if write_content:
                    self.write(httpserver.get_template('generic/error.html')%
                        {'title': 'Factoids - not a channel',
                         'error': 'This is not a channel'})
                return
            if not self._plugin.registryValue('web.channel', channel):
                self.send_response(403)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                if write_content:
                    self.write(httpserver.get_template('generic/error.html')%
                        {'title': 'Factoids - unavailable',
                         'error': 'This channel does not exist or its factoids '
                                  'are not available here.'})
                return
            db = self._plugin.getDb(channel)
            cursor = db.cursor()
            cursor.execute("""SELECT keys.key, factoids.id, factoids.fact
                              FROM factoids, keys, relations
                              WHERE relations.key_id=keys.id AND relations.fact_id=factoids.id
                              """)
            factoids = {}
            for (key, id_, fact) in cursor.fetchall():
                if key not in factoids:
                    factoids[key] = {}
                factoids[key][id_] = fact
            content = ''
            keys = sorted(factoids.keys())
            for key in keys:
                facts = factoids[key]
                content += '<tr>'
                content += ('<td rowspan="%i" class="key">'
                                '<a name="%s" href="#%s">%s</a>'
                           '</td>') % (len(facts), key, key, key)
                for id_, fact in facts.items():
                    content += '<td class="id">%i</td>' % id_
                    content += '<td class="fact">%s</td>' % fact
                    content += '</tr><tr>'
                content = content[:-len('<tr>')]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            if write_content:
                self.write(httpserver.get_template('factoids/channel.html')%
                        {'channel': channel, 'rows': content})
    def doPost(self, handler, path, form):
        if 'chan' in form:
            self.send_response(303)
            self.send_header('Location',
                    './%s/' % utils.web.urlquote(form['chan'].value))
            self.end_headers()
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.write('Missing field \'chan\'.')

class Factoids(callbacks.Plugin, plugins.ChannelDBHandler):
    """Provides the ability to show Factoids."""
    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)
        self._http_running = False
        conf.supybot.plugins.Factoids.web.enable.addCallback(self._doHttpConf)
        if self.registryValue('web.enable'):
            self._startHttp()
    def _doHttpConf(self, *args, **kwargs):
        if self.registryValue('web.enable'):
            if not self._http_running:
                self._startHttp()
        else:
            if self._http_running:
                self._stopHttp()
    def _startHttp(self):
        callback = FactoidsCallback()
        callback._plugin = self
        httpserver.hook('factoids', callback)
        self._http_running = True
    def _stopHttp(self):
        httpserver.unhook('factoids')
        self._http_running = False
    def die(self):
        if self.registryValue('web.enable'):
            self._stopHttp()
        super(self.__class__, self).die()

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite3.connect(filename)
            if minisix.PY2:
                db.text_factory = str
            return db
        db = sqlite3.connect(filename)
        if minisix.PY2:
            db.text_factory = str
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE keys (
                          id INTEGER PRIMARY KEY,
                          key TEXT UNIQUE ON CONFLICT REPLACE
                          )""")
        cursor.execute("""CREATE TABLE factoids (
                          id INTEGER PRIMARY KEY,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          fact TEXT UNIQUE ON CONFLICT REPLACE,
                          locked BOOLEAN
                          )""")
        cursor.execute("""CREATE TABLE relations (
                          id INTEGER PRIMARY KEY,
                          key_id INTEGER,
                          fact_id INTEGER,
                          usage_count INTEGER
                          )""")
        db.commit()
        return db

    def getCommandHelp(self, command, simpleSyntax=None):
        method = self.getCommandMethod(command)
        if method.__func__.__name__ == 'learn':
            chan = None
            network = None
            if dynamic.msg is not None:
                chan = dynamic.msg.channel
            if dynamic.irc is not None:
                network = dynamic.irc.network
            s = self.registryValue('learnSeparator', chan, network)
            help = callbacks.getHelp
            if simpleSyntax is None:
                irc = dynamic.irc
                network = irc.network if irc else None
                simpleSyntax = conf.supybot.reply.showSimpleSyntax.getSpecific(
                    network, chan)()
            if simpleSyntax:
                help = callbacks.getSyntax
            return help(method,
                        doc=method._fake__doc__ % (s, s),
                        name=callbacks.formatCommand(command))
        return super(Factoids, self).getCommandHelp(command, simpleSyntax)

    def _getKeyAndFactId(self, channel, key, factoid):
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id FROM keys WHERE key=?", (key,))
        keyresults = cursor.fetchall()
        cursor.execute("SELECT id FROM factoids WHERE fact=?", (factoid,))
        factresults = cursor.fetchall()
        return (keyresults, factresults,)
    
    def learn(self, irc, msg, args, channel, key, factoid):
        if self.registryValue('requireVoice', channel, irc.network) and \
                not irc.state.channels[channel].isVoicePlus(msg.nick):
            irc.error(_('You have to be at least voiced to teach factoids.'), Raise=True)
        
        # if neither key nor factoid exist, add them.
        # if key exists but factoid doesn't, add factoid, link it to existing key
        # if factoid exists but key doesn't, add key, link it to existing factoid
        # if both key and factoid already exist, and are linked, do nothing, print nice message
        db = self.getDb(channel)
        cursor = db.cursor()
        (keyid, factid) = self._getKeyAndFactId(channel, key, factoid)
        
        if len(keyid) == 0:
            cursor.execute("""INSERT INTO keys VALUES (NULL, ?)""", (key,))
            db.commit()
        if len(factid) == 0:
            if ircdb.users.hasUser(msg.prefix):
                name = ircdb.users.getUser(msg.prefix).name
            else:
                name = msg.nick
            cursor.execute("""INSERT INTO factoids VALUES
                              (NULL, ?, ?, ?, ?)""",
                           (name, int(time.time()), factoid, 0))
            db.commit()
        (keyid, factid) = self._getKeyAndFactId(channel, key, factoid)
        
        cursor.execute("""SELECT id, key_id, fact_id from relations
                            WHERE key_id=? AND fact_id=?""", 
                            (keyid[0][0], factid[0][0],))
        existingrelation = cursor.fetchall()
        if len(existingrelation) == 0:
            cursor.execute("""INSERT INTO relations VALUES (NULL, ?, ?, ?)""", 
                    (keyid[0][0],factid[0][0],0,))
            db.commit()
            irc.replySuccess()
        else:
            irc.error("This key-factoid relationship already exists.")
        
    learn = wrap(learn, ['factoid'], checkDoc=False)
    learn._fake__doc__ = _("""[<channel>] <key> %s <value>

                         Associates <key> with <value>.  <channel> is only
                         necessary if the message isn't sent on the channel
                         itself.  The word '%s' is necessary to separate the
                         key from the value.  It can be changed to another word
                         via the learnSeparator registry value.
                         """)


    def _lookupFactoid(self, channel, key):
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT factoids.fact, factoids.id, relations.id FROM factoids, keys, relations
                          WHERE keys.key LIKE ? AND relations.key_id=keys.id AND relations.fact_id=factoids.id
                          ORDER BY factoids.id
                          LIMIT 20""", (key,))
        return cursor.fetchall()
    
    def _searchFactoid(self, channel, key):
        """Try to typo-match input to possible factoids.
        
        Assume first letter is correct, to reduce processing time.        
        First, try a simple wildcard search.
        If that fails, use the Damerau-Levenshtein edit-distance metric.
        """
        # if you made a typo in a two-character key, boo on you.
        if len(key) < 3:
            return []
            
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT key FROM keys WHERE key LIKE ?""", ('%' + key + '%',))
        wildcardkeys = cursor.fetchall()
        if len(wildcardkeys) > 0:
            return [line[0] for line in wildcardkeys]
        
        cursor.execute("""SELECT key FROM keys WHERE key LIKE ?""", (key[0] + '%',))
        flkeys = cursor.fetchall()
        if len(flkeys) == 0:
            return []
        flkeys = [line[0] for line in flkeys]
        dl_metrics = [dameraulevenshtein(key, sourcekey) for sourcekey in flkeys]
        dict_metrics = dict(list(zip(flkeys, dl_metrics)))
        if min(dl_metrics) <= 2:
            return [key for key,item in dict_metrics.items() if item <= 2]
        if min(dl_metrics) <= 3:
            return [key for key,item in dict_metrics.items() if item <= 3]
        
        return []
                
    def _updateRank(self, network, channel, factoids):
        if self.registryValue('keepRankInfo', channel, network):
            db = self.getDb(channel)
            cursor = db.cursor()
            for (fact,factid,relationid) in factoids:
                cursor.execute("""SELECT relations.usage_count
                          FROM relations
                          WHERE relations.id=?""", (relationid,))
                old_count = cursor.fetchall()[0][0]
                cursor.execute("UPDATE relations SET usage_count=? WHERE id=?", 
                            (old_count + 1, relationid,))
                db.commit()
        
    def _replyFactoids(self, irc, msg, key, channel, factoids,
                       number=0, error=True, raw=False):
        def format_fact(text):
            if raw:
                return text
            else:
                return ircutils.standardSubstitute(irc, msg, text)
        
        if factoids:
            if number:
                try:
                    irc.reply(format_fact(factoids[number-1][0]))
                    self._updateRank(irc.network, channel, [factoids[number-1]])
                except IndexError:
                    irc.error(_('That\'s not a valid number for that key.'))
                    return
            else:
                env = {'key': key}
                def prefixer(v):
                    env['value'] = v
                    formatter = self.registryValue('format',
                                                   msg.channel, irc.network)
                    return ircutils.standardSubstitute(irc, msg,
                                                       formatter, env)
                if len(factoids) == 1:
                    irc.reply(format_fact(prefixer(factoids[0][0])))
                else:
                    factoidsS = []
                    counter = 1
                    for factoid in factoids:
                        factoidsS.append(format('(#%i) %s', counter, 
                                format_fact(factoid[0])))
                        counter += 1
                    irc.replies(factoidsS, prefixer=prefixer,
                                joiner=', or ', onlyPrefixFirst=True)
                self._updateRank(irc.network, channel, factoids)
        elif error:
            irc.error(_('No factoid matches that key.'))

    def _replyApproximateFactoids(self, irc, msg, channel, key, error=True):
        if self.registryValue('replyApproximateSearchKeys'):
            factoids = self._searchFactoid(channel, key)
            factoids.sort()
            if factoids:
                keylist = ["'%s'" % (fact,) for fact in factoids]
                keylist = ', '.join(keylist)
                irc.reply("I do not know about '%s', but I do know about these similar topics: %s" % (key, keylist))
            elif error:
                irc.error('No factoid matches that key.')

    def invalidCommand(self, irc, msg, tokens):
        channel = msg.channel
        if channel:
            if self.registryValue('replyWhenInvalidCommand', channel, irc.network):
                key = ' '.join(tokens)
                factoids = self._lookupFactoid(channel, key)
                if factoids:
                    self._replyFactoids(irc, msg, key, channel, factoids, error=False)
                else:
                    self._replyApproximateFactoids(irc, msg, channel, key, error=False)

    @internationalizeDocstring
    def whatis(self, irc, msg, args, channel, optlist, words):
        """[<channel>] [--raw] <key> [<number>]

        Looks up the value of <key> in the factoid database.  If given a
        number, will return only that exact factoid. If '--raw' option is
        given, no variable substitution will take place on the factoid.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        raw = False
        for (option, arg) in optlist:
            if option == 'raw':
                raw = True
        number = None
        if len(words) > 1:
            if words[-1].isdigit():
                number = int(words.pop())
                if number <= 0:
                    irc.errorInvalid(_('key id'))
        key = ' '.join(words)
        factoids = self._lookupFactoid(channel, key)
        if factoids:
            self._replyFactoids(irc, msg, key, channel, factoids, number, raw=raw)
        else:
            self._replyApproximateFactoids(irc, msg, channel, key)
    whatis = wrap(whatis, ['channel',
                            getopts({'raw': '',}),
                            many('something')])

    @internationalizeDocstring
    def alias(self, irc, msg, args, channel, oldkey, newkey, number):
        """[<channel>] <oldkey> <newkey> [<number>]

        Adds a new key <newkey> for factoid associated with <oldkey>.
        <number> is only necessary if there's more than one factoid associated
        with <oldkey>.

        The same action can be accomplished by using the 'learn' function with
        a new key but an existing (verbatim) factoid content.
        """
        def _getNewKey(channel, newkey, arelation):
            db = self.getDb(channel)
            cursor = db.cursor()
            cursor.execute("""SELECT id FROM keys WHERE key=?""", (newkey,))
            newkey_info = cursor.fetchall()
            if len(newkey_info) == 1:
                # check if we already have the requested relation
                cursor.execute("""SELECT id FROM relations WHERE
                            key_id=? and fact_id=?""",
                            (arelation[1], arelation[2]))
                existentrelation = cursor.fetchall()
                if len(existentrelation) != 0:
                    newkey_info = False
            if len(newkey_info) == 0:
                cursor.execute("""INSERT INTO keys VALUES (NULL, ?)""",
                            (newkey,))
                db.commit()
                cursor.execute("""SELECT id FROM keys WHERE key=?""", (newkey,))
                newkey_info = cursor.fetchall()
            return newkey_info

        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT relations.id, relations.key_id, relations.fact_id
                        FROM keys, relations
                        WHERE keys.key=? AND
                        relations.key_id=keys.id""", (oldkey,))
        results = cursor.fetchall()
        if len(results) == 0:
            irc.error(_('No factoid matches that key.'))
            return
        elif len(results) == 1:
            newkey_info = _getNewKey(channel, newkey, results[0])
            if newkey_info is not False:
                cursor.execute("""INSERT INTO relations VALUES(NULL, ?, ?, ?)""",
                            (newkey_info[0][0], results[0][2], 0,))
                irc.replySuccess()
            else:
                irc.error(_('This key-factoid relationship already exists.'))
        elif len(results) > 1:
            try:
                arelation = results[number-1]
            except IndexError:
                irc.error(_("That's not a valid number for that key."))
                return
            except TypeError:
                irc.error(_("This key has more than one factoid associated "
                        "with it, but you have not provided a number."))
                return
            newkey_info = _getNewKey(channel, newkey, arelation)
            if newkey_info is not False:
                cursor.execute("""INSERT INTO relations VALUES(NULL, ?, ?, ?)""",
                            (newkey_info[0][0], arelation[2], 0,))
                irc.replySuccess()
            else:
                irc.error(_('This key-factoid relationship already exists.'))
    alias = wrap(alias, ['channel', 'something', 'something', optional('int')])

    @internationalizeDocstring
    def rank(self, irc, msg, args, channel, optlist, number):
        """[<channel>] [--plain] [--alpha] [<number>]

        Returns a list of top-ranked factoid keys, sorted by usage count
        (rank). If <number> is not provided, the default number of factoid keys
        returned is set by the rankListLength registry value.

        If --plain option is given, rank numbers and usage counts are not
        included in output.

        If --alpha option is given in addition to --plain, keys are sorted
        alphabetically, instead of by rank.

        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if not number:
            number = self.registryValue('rankListLength', channel, irc.network)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT keys.key, relations.usage_count
                          FROM keys, relations
                          WHERE relations.key_id=keys.id
                          ORDER BY relations.usage_count DESC
                          LIMIT ?""", (number,))
        factkeys = cursor.fetchall()
        plain=False
        alpha=False
        for (option, arg) in optlist:
            if option == 'plain':
                plain = True
            elif option =='alpha':
                alpha = True
        if plain:
            s = [ "%s" % (key[0],) for i, key in enumerate(factkeys) ]
            if alpha:
                s.sort()
        else:
            s = [ "#%d %s (%d)" % (i+1, key[0], key[1]) for i, key in enumerate(factkeys) ]
        irc.reply(", ".join(s))
    rank = wrap(rank, ['channel', 
                        getopts({'plain': '', 'alpha': '',}), 
                        optional('int')])

    @internationalizeDocstring
    def lock(self, irc, msg, args, channel, key):
        """[<channel>] <key>

        Locks the factoid(s) associated with <key> so that they cannot be
        removed or added to.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("UPDATE factoids "
                "SET locked=1 WHERE factoids.id IN "
                "(SELECT fact_id FROM relations WHERE key_id IN "
                "(SELECT id FROM keys WHERE key LIKE ?));", (key,))
        db.commit()
        irc.replySuccess()
    lock = wrap(lock, ['channel', 'text'])

    @internationalizeDocstring
    def unlock(self, irc, msg, args, channel, key):
        """[<channel>] <key>

        Unlocks the factoid(s) associated with <key> so that they can be
        removed or added to.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("UPDATE factoids "
                "SET locked=0 WHERE factoids.id IN "
                "(SELECT fact_id FROM relations WHERE key_id IN "
                "(SELECT id FROM keys WHERE key LIKE ?));", (key,))
        db.commit()
        irc.replySuccess()
    unlock = wrap(unlock, ['channel', 'text'])

    def _deleteRelation(self, channel, relationlist):
        db = self.getDb(channel)
        cursor = db.cursor()
        for (keyid, factid, relationid) in relationlist:
            cursor.execute("""DELETE FROM relations where relations.id=?""",
                        (relationid,))
            db.commit()

            cursor.execute("""SELECT id FROM relations
                            WHERE relations.key_id=?""", (keyid,))
            remaining_key_relations = cursor.fetchall()
            if len(remaining_key_relations) == 0:
                cursor.execute("""DELETE FROM keys where id=?""", (keyid,))

            cursor.execute("""SELECT id FROM relations
                            WHERE relations.fact_id=?""", (factid,))
            remaining_fact_relations = cursor.fetchall()
            if len(remaining_fact_relations) == 0:
                cursor.execute("""DELETE FROM factoids where id=?""", (factid,))
            db.commit()

    @internationalizeDocstring
    def forget(self, irc, msg, args, channel, words):
        """[<channel>] <key> [<number>|*]

        Removes a key-fact relationship for key <key> from the factoids
        database.  If there is more than one such relationship for this key,
        a number is necessary to determine which one should be removed.
        A * can be used to remove all relationships for <key>.

        If as a result, the key (factoid) remains without any relationships to
        a factoid (key), it shall be removed from the database.

        <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        if self.registryValue('requireVoice', channel, irc.network) and \
                not irc.state.channels[channel].isVoicePlus(msg.nick):
            irc.error(_('You have to be at least voiced to remove factoids.'), Raise=True)
        number = None
        if len(words) > 1:
            if words[-1].isdigit():
                number = int(words.pop())
                if number <= 0:
                    irc.errorInvalid(_('key id'))
            elif words[-1] == '*':
                words.pop()
                number = True
        key = ' '.join(words)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT keys.id, factoids.id, relations.id
                        FROM keys, factoids, relations
                        WHERE key LIKE ? AND
                        relations.key_id=keys.id AND
                        relations.fact_id=factoids.id""", (key,))
        results = cursor.fetchall()
        if len(results) == 0:
            irc.error(_('There is no such factoid.'))
        elif len(results) == 1 or number is True:
            self._deleteRelation(channel, results)
            irc.replySuccess()
        else:
            if number is not None:
                #results = cursor.fetchall()
                try:
                    arelation = results[number-1]
                except IndexError:
                    irc.error(_('Invalid factoid number.'))
                    return
                self._deleteRelation(channel, [arelation,])
                irc.replySuccess()
            else:
                irc.error(_('%s factoids have that key.  '
                          'Please specify which one to remove, '
                          'or use * to designate all of them.') %
                          len(results))
    forget = wrap(forget, ['channel', many('something')])

    @internationalizeDocstring
    def random(self, irc, msg, args, channel):
        """[<channel>]

        Returns random factoids from the database for <channel>.  <channel>
        is only necessary if the message isn't sent in the channel itself.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, key_id, fact_id FROM relations
                          ORDER BY random()
                          LIMIT 3""")
        results = cursor.fetchall()
        if len(results) != 0:
            L = []
            for (relationid, keyid, factid) in results:
                cursor.execute("""SELECT keys.key, factoids.fact
                            FROM keys, factoids
                            WHERE factoids.id=? AND
                            keys.id=?""", (factid,keyid,))
                (key,factoid) = cursor.fetchall()[0]
                L.append('"%s": %s' % (ircutils.bold(key), factoid))
            irc.reply('; '.join(L))
        else:
            irc.error(_('I couldn\'t find a factoid.'))
    random = wrap(random, ['channel'])

    @internationalizeDocstring
    def info(self, irc, msg, args, channel, key):
        """[<channel>] <key>

        Gives information about the factoid(s) associated with <key>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT id FROM keys WHERE key LIKE ?", (key,))
        results = cursor.fetchall()
        if len(results) == 0:
            irc.error(_('No factoid matches that key.'))
            return
        id = results[0][0]
        cursor.execute("""SELECT factoids.added_by, factoids.added_at, factoids.locked, relations.usage_count
                        FROM factoids, relations
                        WHERE relations.key_id=? AND
                        relations.fact_id=factoids.id
                        ORDER BY relations.id""", (id,))
        factoids = cursor.fetchall()
        L = []
        counter = 0
        for (added_by, added_at, locked, usage_count) in factoids:
            counter += 1
            added_at = time.strftime(conf.supybot.reply.format.time(),
                                     time.localtime(int(added_at)))
            L.append(format(_('#%i was added by %s at %s, and has been '
                            'recalled %n'),
                            counter, added_by, added_at,
                            (usage_count, _('time'))))
        factoids = '; '.join(L)
        s = format('Key %q is %s and has %n associated with it: %s',
                   key, locked and 'locked' or 'not locked',
                   (counter, 'factoid'), factoids)
        irc.reply(s)
    info = wrap(info, ['channel', 'text'])

    @internationalizeDocstring
    def change(self, irc, msg, args, channel, key, number, replacer):
        """[<channel>] <key> <number> <regexp>

        Changes the factoid #<number> associated with <key> according to
        <regexp>.
        """
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT factoids.id, factoids.fact
                        FROM keys, factoids, relations
                        WHERE keys.key LIKE ? AND
                        keys.id=relations.key_id AND
                        factoids.id=relations.fact_id""", (key,))
        results = cursor.fetchall()
        if len(results) == 0:
            irc.error(format(_('I couldn\'t find any key %q'), key))
            return
        elif len(results) < number:
            irc.errorInvalid('key id')
        (id, fact) = results[number-1]
        newfact = replacer(fact)
        cursor.execute("UPDATE factoids SET fact=? WHERE id=?", (newfact, id))
        db.commit()
        irc.replySuccess()
    change = wrap(change, ['channel', 'something',
                           'factoidId', 'regexpReplacer'])

    _sqlTrans = utils.str.MultipleReplacer({'*': '%', '?': '_'})
    @internationalizeDocstring
    def search(self, irc, msg, args, channel, optlist, globs):
        """[<channel>] [--values] [--regexp <value>] [--author <username>] [<glob> ...]

        Searches the keyspace for keys matching <glob>.  If --regexp is given,
        its associated value is taken as a regexp and matched against the keys.
        If --values is given, search the value space instead of the keyspace.
        """
        if not optlist and not globs:
            raise callbacks.ArgumentError
        tables = ['keys']
        join_factoids = False
        formats = []
        criteria = []
        join_criteria = []
        target = 'keys.key'
        predicateName = 'p'
        db = self.getDb(channel)
        for (option, arg) in optlist:
            if option == 'values':
                target = 'factoids.fact'
                join_factoids = True
            elif option == 'regexp':
                criteria.append('%s(TARGET)' % predicateName)
                def p(s, r=arg):
                    return int(bool(r.search(s)))
                db.create_function(predicateName, 1, p)
                predicateName += 'p'
            elif option == 'author':
                join_factoids = True
                criteria.append('factoids.added_by=?')
                formats.append(arg)
        for glob in globs:
            criteria.append('TARGET LIKE ?')
            formats.append(self._sqlTrans(glob))

        def _join_factoids():
            if 'factoids' not in tables:
                tables.append('factoids')
                tables.append('relations')
            join_criteria.append(
                'factoids.id=relations.fact_id AND keys.id=relations.key_id'
            )
        if join_factoids:
            _join_factoids()

        cursor = db.cursor()
        sql = """SELECT DISTINCT keys.key FROM %s WHERE %s""" % \
              (', '.join(tables), ' AND '.join(criteria + join_criteria))
        sql = sql + " ORDER BY keys.key"
        sql = sql.replace('TARGET', target)
        cursor.execute(sql, formats)

        if cursor.rowcount == 0:
            irc.reply(_('No keys matched that query.'))
        elif cursor.rowcount == 1 and \
             self.registryValue('showFactoidIfOnlyOneMatch',
                                channel, irc.network):
            self.whatis(irc, msg, [channel, cursor.fetchone()[0]])
        elif cursor.rowcount > 100:
            irc.reply(_('More than 100 keys matched that query; '
                      'please narrow your query.'))
        results = cursor.fetchall()
        if len(results) == 0:
            irc.reply(_('No keys matched that query.'))
        elif len(results) == 1 and \
             self.registryValue('showFactoidIfOnlyOneMatch',
                                channel, irc.network):
            ((key,),) = results

            # add the knowledge we gained, so avoid a full search again
            join_criteria.append('keys.key=?')
            formats.append(key)

            if not join_factoids:
                # if they were not joined before, we need to join
                # them now to get the values
                _join_factoids()

            sql = """
                SELECT factoids.fact, (1 AND %s) FROM %s
                WHERE %s
                ORDER BY factoids.id
            """ % \
                  (' AND '.join(criteria), ', '.join(tables),
                   ' AND '.join(['keys.key=?', *join_criteria]))
            sql = sql.replace('TARGET', target)
            formats.append(key)
            cursor.execute(sql, formats)
            factoids = cursor.fetchall()
            assert factoids  # we had a result before, and still should now
            if len(factoids) == 1:
                ((fact, included),) = factoids
                assert included  # matched before, should still match now
                irc.reply('%s is %s' %
                          (key, ircutils.standardSubstitute(irc, msg, fact)))
            else:
                factoidsS = []
                counter = 1
                for (fact, included) in factoids:
                    if included:
                        factoidsS.append(format('(#%i) %s', counter,
                                ircutils.standardSubstitute(irc, msg, fact)))
                    counter += 1
                irc.replies(factoidsS, prefixer=lambda s: '%s is %s' % (key, s),
                            joiner=', or ', onlyPrefixFirst=True)
        elif len(results) > 100:
            irc.reply(_('More than 100 keys matched that query; '
                      'please narrow your query.'))
        else:
            keys = [repr(t[0]) for t in results]
            s = format('%L', keys)
            irc.reply(s)
    search = wrap(search, ['channel',
                           getopts({
                               'values': '',
                               'regexp': 'regexpMatcher',
                               'author': 'somethingWithoutSpaces',
                           }),
                           any('glob')])


Class = Factoids


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
