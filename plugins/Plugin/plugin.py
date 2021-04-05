###
# Copyright (c) 2005, Jeremiah Fincher
# Copyright (c) 2019, James Lu <james@overdrivenetworks.com>
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

import supybot

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Plugin')


class Plugin(callbacks.Plugin):
    """
    This plugin exists to help users manage their plugins.  Use 'plugin
    list' to list the loaded plugins; use 'plugin help' to get the description
    of a plugin; use the 'plugin' command itself to determine what plugin a
    command exists in.
    """

    @internationalizeDocstring
    def help(self, irc, msg, args, cb):
        """<plugin>

        Returns a useful description of how to use <plugin>, if the plugin has
        one.
        """
        doc = cb.getPluginHelp()
        if doc:
            irc.reply(utils.str.normalizeWhitespace(doc.split("\n\n")[0]))
        else:
            irc.reply(_('That plugin is loaded, but has no plugin help.'))
    help = wrap(help, ['plugin'])

    @internationalizeDocstring
    def plugin(self, irc, msg, args, command):
        """<command>

        Returns the name of the plugin that would be used to call <command>.

        If it is not uniquely determined, returns list of all plugins that
        contain <command>.
        """
        (maxL, cbs) = irc.findCallbacksForArgs(command)
        L = []
        if maxL == command:
            for cb in cbs:
                L.append(cb.name())
        command = callbacks.formatCommand(command)
        if L:
            if irc.nested:
                irc.reply(format('%L', L))
            else:
                if len(L) > 1:
                    plugin = _('plugins')
                else:
                    plugin = _('plugin')
                irc.reply(format(_('The %q command is available in the %L '
                                 '%s.'), command, L, plugin))
        else:
            irc.error(format(_('There is no command %q.'), command))
    plugin = wrap(plugin, [many('something')])

    def _findCallbacks(self, irc, command):
        command = list(map(callbacks.canonicalName, command))
        plugin_list = []
        for cb in irc.callbacks:
            if not hasattr(cb, 'getCommand'):
                continue
            longest_matching_command = cb.getCommand(command)
            if len(longest_matching_command) >= len(command):
                # Actually, this is equivalent to use ==
                plugin_list.append(cb.name())
        return plugin_list

    @internationalizeDocstring
    def plugins(self, irc, msg, args, command):
        """<command>

        Returns the names of all plugins that contain <command>.
        """
        L = self._findCallbacks(irc, command)
        command = callbacks.formatCommand(command)
        if L:
            if irc.nested:
                irc.reply(format('%L', L))
            else:
                if len(L) > 1:
                    plugin = 'plugins'
                else:
                    plugin = 'plugin'
                irc.reply(format(_('The %q command is available in the %L %s.'),
                                 command, L, plugin))
        else:
            irc.error(format('There is no command %q.', command))
    plugins = wrap(plugins, [many('something')])

    def author(self, irc, msg, args, cb):
        """<plugin>

        Returns the author of <plugin>.  This is the person you should talk to
        if you have ideas, suggestions, or other comments about a given plugin.
        """
        if cb is None:
            irc.error(_('That plugin does not seem to be loaded.'))
            return
        module = cb.classModule

        author = getattr(module, '__author__', None)
        # Allow for a maintainer field, which better represents plugins that have changed hands
        # over time. Of course, assume that the author is the maintainer if no other info is given.
        maintainer = getattr(module, '__maintainer__', None) or author

        if author:
            if maintainer == author:
                irc.reply(_("%s was written by %s") % (cb.name(), author))
            else:
                irc.reply(_("%s was written by %s and is maintained by %s.") % \
                            (cb.name(), author, maintainer))
        else:
            irc.reply(_('%s does not have any author listed.') % cb.name())
    author = wrap(author, [('plugin')])

    @internationalizeDocstring
    def contributors(self, irc, msg, args, cb, nick):
        """<plugin> [<name>]

        Replies with a list of people who made contributions to a given plugin.
        If <name> is specified, that person's specific contributions will
        be listed. You can specify a person's name by their full name or their nick,
        which is shown inside brackets if available.
        """
        def buildContributorsString(longList):
            """
            Take a list of long names and turn it into :
            shortname[, shortname and shortname].
            """
            L = [authorInfo.format(short=True) for authorInfo in longList]
            return format('%L', L)

        def buildPeopleString(module):
            """
            Build the list of author + contributors (if any) for the requested
            plugin.
            """
            author = getattr(module, '__author__', supybot.authors.unknown)
            if author != supybot.authors.unknown:
                s = _('The %s plugin was written by %s. ' % (cb.name(), author))
            else:
                s = _('The %s plugin has not been claimed by an author. ') % cb.name()

            contribs = getattr(module, '__contributors__', {})
            if contribs:
                s += format(_('%s %h contributed to it.'),
                              buildContributorsString(contribs.keys()),
                              len(contribs))
            else:
                s += _('No additional contributors are listed.')
            return s

        def buildPersonString(module):
            """
            Build the list of contributions (if any) for the requested person
            for the requested plugin.
            """
            contributors = getattr(module, '__contributors__', {})
            # Make a mapping of nicks and names to author instances
            contributorNicks = {}
            for contributor in contributors.keys():
                if contributor.nick:
                    contributorNicks[contributor.nick.lower()] = contributor
                if contributor.name:
                    contributorNicks[contributor.name.lower()] = contributor
            lnick = nick.lower()

            author = getattr(module, '__author__', supybot.authors.unknown)
            if author != supybot.authors.unknown and \
                    (lnick == (author.name or '').lower() or lnick == (author.nick or '').lower()):
                # Special case for the plugin author. We remove legacy handling of the case where
                # someone is listed both as author and contributor, which should never really happen?
                return _('%s wrote the %s plugin.') % (author, cb.name())
            elif lnick not in contributorNicks:
                return _('%s is not listed as a contributor to %s.') % (nick, cb.name())

            authorInfo = contributorNicks[lnick]
            contributions = contributors[authorInfo]
            fullName = authorInfo.format(short=True)

            if contributions:
                return format(_('%s contributed the following to %s: %s'),
                              fullName, cb.name(), ', '.join(contributions))
            else:
                return _('%s did not list any specific contributions to the %s '
                         'plugin.') % (fullName, cb.name())

        # First we need to check and see if the requested plugin is loaded
        module = cb.classModule
        if not nick:
            irc.reply(buildPeopleString(module))
        else:
            nick = ircutils.toLower(nick)
            irc.reply(buildPersonString(module))
    contributors = wrap(contributors, ['plugin', additional('text')])
Plugin = internationalizeDocstring(Plugin)

Class = Plugin

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
