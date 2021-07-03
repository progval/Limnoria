###
# Copyright (c) 2015, Michael Daniel Telatynski <postmaster@webdevguru.co.uk>
# Copyright (c) 2015-2020, James Lu <james@overdrivenetworks.com>
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

from supybot.commands import *
from supybot.commands import ProcessTimeoutError
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.callbacks as callbacks
import supybot.ircutils as ircutils
import supybot.ircdb as ircdb
import supybot.utils as utils

import re
import sys

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('SedRegex')
except ImportError:
    _ = lambda x: x

if sys.version_info[0] < 3:
    raise ImportError('This plugin requires Python 3. For a legacy version of this plugin that still '
                      'supports Python 2, consult the python2-legacy branch at '
                      'https://github.com/jlu5/SupyPlugins/tree/python2-legacy')

from .constants import SED_REGEX, TAG_SEEN, TAG_IS_REGEX

# Replace newlines and friends with things like literal "\n" (backslash and "n")
axe_spaces = utils.str.MultipleReplacer({'\n': '\\n', '\t': '\\t', '\r': '\\r'})

class SearchNotFoundError(Exception):
    pass

class SedRegex(callbacks.PluginRegexp):
    """
    Enable SedRegex on the desired channels:
    ``config channel #yourchannel plugins.sedregex.enable True``
    After enabling SedRegex, typing a regex in the form
    ``s/text/replacement/`` will make the bot announce replacements.

    ::

       20:24 <jlu5> helli world
       20:24 <jlu5> s/i/o/
       20:24 <Limnoria> jlu5 meant to say: hello world

    You can also do ``othernick: s/text/replacement/`` to only replace
    messages from a certain user. Supybot ignores are respected by the plugin,
    and messages from ignored users will only be considered if their nick is
    explicitly given.

    Regex flags
    ^^^^^^^^^^^

    The following regex flags (i.e. the ``g`` in ``s/abc/def/g``, etc.) are
    supported:

    - ``i``: case insensitive replacement
    - ``g``: replace all occurences of the original text
    - ``s``: *(custom flag specific to this plugin)* replace only messages
      from the caller
    """

    threaded = True
    public = True
    unaddressedRegexps = ['replacer']
    flags = 0  # Make callback matching case sensitive

    @staticmethod
    def _unpack_sed(expr):
        if '\0' in expr:
            raise ValueError('Expression can\'t contain NUL')

        delim = expr[1]
        escaped_expr = ''

        for (i, c) in enumerate(expr):
            if c == delim and i > 0:
                if expr[i - 1] == '\\':
                    escaped_expr = escaped_expr[:-1] + '\0'
                    continue

            escaped_expr += c

        match = SED_REGEX.search(escaped_expr)

        if not match:
            return

        groups = match.groupdict()
        pattern = groups['pattern'].replace('\0', delim)
        replacement = groups['replacement'].replace('\0', delim)

        if groups['flags']:
            raw_flags = set(groups['flags'])
        else:
            raw_flags = set()

        flags = 0
        count = 1

        for flag in raw_flags:
            if flag == 'g':
                count = 0
            if flag == 'i':
                flags |= re.IGNORECASE

        pattern = re.compile(pattern, flags)

        return (pattern, replacement, count, raw_flags)

    # Tag all messages that SedRegex has seen before. This slightly optimizes the ignoreRegex
    # feature as all messages tagged with SedRegex.seen but not SedRegex.isRegex is NOT a regexp.
    # If we didn't have this tag, we'd have to run a regexp match on each message in the history
    # to check if it's a regexp, as there could've been regexp-like messages sent before
    # SedRegex was enabled.
    def doNotice(self, irc, msg):
        if self.registryValue('enable', msg.channel, irc.network):
            msg.tag(TAG_SEEN)

    def doPrivmsg(self, irc, msg):
       # callbacks.PluginRegexp works by defining doPrivmsg(), we don't want to overwrite
       # its behaviour
       super().doPrivmsg(irc, msg)
       self.doNotice(irc, msg)

    # SedRegex main routine. This is called automatically by callbacks.PluginRegexp on every
    # message that matches the SED_REGEX expression defined in constants.py
    # The actual regexp is passed into PluginRegexp by setting __doc__ equal to the regexp.
    def replacer(self, irc, msg, regex):
        if not self.registryValue('enable', msg.channel, irc.network):
            return
        self.log.debug("SedRegex: running on %s/%s for %s", irc.network, msg.channel, regex)
        iterable = reversed(irc.state.history)
        msg.tag(TAG_IS_REGEX)

        try:
            (pattern, replacement, count, flags) = self._unpack_sed(msg.args[1])
        except Exception as e:
            self.log.warning(_("SedRegex parser error: %s"), e, exc_info=True)
            if self.registryValue('displayErrors', msg.channel, irc.network):
                irc.error('%s.%s: %s' % (e.__class__.__module__, e.__class__.__name__, e))
            return

        next(iterable)
        if 's' in flags:  # Special 's' flag lets the bot only look at self messages
            target = msg.nick
        else:
            target = regex.group('nick')
        if not ircutils.isNick(str(target)):
            return

        regex_timeout = self.registryValue('processTimeout')
        try:
            message = process(self._replacer_process, irc, msg,
                    target, pattern, replacement, count, iterable,
                    timeout=regex_timeout, pn=self.name(), cn='replacer')
        except ProcessTimeoutError:
            irc.error(_("Search timed out."))
        except SearchNotFoundError:
            irc.error(_("Search not found in the last %i IRC messages on this network.") %
                len(irc.state.history))
        except Exception as e:
            self.log.warning(_("SedRegex replacer error: %s"), e, exc_info=True)
            if self.registryValue('displayErrors', msg.channel, irc.network):
                irc.error('%s.%s: %s' % (e.__class__.__module__,
                    e.__class__.__name__, e))
        else:
            irc.reply(message, prefixNick=False)
    replacer.__doc__ = SED_REGEX.pattern

    def _replacer_process(self, irc, msg, target, pattern, replacement, count, messages):
        for m in messages:
            if m.command in ('PRIVMSG', 'NOTICE') and \
                    ircutils.strEqual(m.args[0], msg.args[0]) and m.tagged('receivedBy') == irc:
                if target and m.nick != target:
                    continue
                # Don't snarf ignored users' messages unless specifically
                # told to.
                if ircdb.checkIgnored(m.prefix) and not target:
                    continue

                # When running substitutions, ignore the "* nick" part of any actions.
                action = ircmsgs.isAction(m)
                if action:
                    text = ircmsgs.unAction(m)
                else:
                    text = m.args[1]

                # Test messages sent before SedRegex was activated. Mark them all as seen
                # so we only need to do this check once per message.
                if not m.tagged(TAG_SEEN):
                    m.tag(TAG_SEEN)
                    if SED_REGEX.match(m.args[1]):
                        m.tag(TAG_IS_REGEX)
                # Ignore messages containing a regexp if ignoreRegex is on.
                if self.registryValue('ignoreRegex', msg.channel, irc.network) and m.tagged(TAG_IS_REGEX):
                    self.log.debug("Skipping message %s because it is tagged as isRegex", m.args[1])
                    continue
                if m.nick == msg.nick:
                    messageprefix = msg.nick
                else:
                    messageprefix = '%s thinks %s' % (msg.nick, m.nick)

                try:
                    replace_result = pattern.search(text)
                    if replace_result:
                        if self.registryValue('boldReplacementText',
                                              msg.channel, irc.network):
                            replacement = ircutils.bold(replacement)
                        subst = pattern.sub(replacement, text, count)
                        if action:  # If the message was an ACTION, prepend the nick back.
                            subst = '* %s %s' % (m.nick, subst)

                        subst = axe_spaces(subst)

                        return _("%s meant to say: %s") % \
                            (messageprefix, subst)
                except Exception as e:
                    self.log.warning(_("SedRegex error: %s"), e, exc_info=True)
                    raise

        self.log.debug(_("SedRegex: Search %r not found in the last %i messages of %s."),
                         msg.args[1], len(irc.state.history), msg.args[0])
        raise SearchNotFoundError()

Class = SedRegex


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
