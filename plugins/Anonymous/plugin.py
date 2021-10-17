###
# Copyright (c) 2005, Daniel DiPaolo
# Copyright (c) 2014, James McCoy
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

import functools

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.callbacks as callbacks
import supybot.ircutils as ircutils
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Anonymous')

class Anonymous(callbacks.Plugin):
    """
    This plugin allows users to act through the bot anonymously.  The 'do'
    command has the bot perform an anonymous action in a given channel, and
    the 'say' command allows other people to speak through the bot.  Since
    this can be fairly well abused, you might want to set
    supybot.plugins.Anonymous.requireCapability so only users with that
    capability can use this plugin.  For extra security, you can require that
    the user be *in* the channel they are trying to address anonymously with
    supybot.plugins.Anonymous.requirePresenceInChannel, or you can require
    that the user be registered by setting
    supybot.plugins.Anonymous.requireRegistration.

    Example: Proving that you are the owner
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    When you ask for cloak/vhost for your bot, the network operators will
    often ask you to prove that you own the bot. You can do this for example
    with the following method::

        @load Anonymous
        @config plugins.anonymous.requirecapability owner
        @config plugins.anonymous.allowprivatetarget True
        @anonymous say <operator nick> Hi, my owner is <your nick> :)

    This
    * Loads the plugin.
    * Makes the plugin require that you are the owner

      * If anyone could send private messages as the bot, they could also
        access network services.

    * Allows sending private messages
    * Sends message ``Hi, my owner is <your nick> :)`` to ``operator nick``.

      * Note that you won't see the messages that are sent to the bot.

    """
    def _preCheck(self, irc, msg, target, action):
        if self.registryValue('requireRegistration', target, irc.network):
            try:
                foo = ircdb.users.getUser(msg.prefix)
            except KeyError:
                irc.errorNotRegistered(Raise=True)
        capability = self.registryValue('requireCapability',
                                        target, irc.network)
        if capability:
            if not ircdb.checkCapability(msg.prefix, capability):
                irc.errorNoCapability(capability, Raise=True)
        if action != 'tell':
            require_presence = self.registryValue('requirePresenceInChannel',
                                                  target, irc.network)
            if require_presence and \
               msg.nick not in irc.state.channels[target].users:
                irc.error(format(_('You must be in %s to %q in there.'),
                                 target, action), Raise=True)
            c = ircdb.channels.getChannel(target)
            if c.lobotomized:
                irc.error(format(_('I\'m lobotomized in %s.'), target),
                          Raise=True)
            if not c._checkCapability(self.name()):
                irc.error(_('That channel has set its capabilities so as to '
                          'disallow the use of this plugin.'), Raise=True)
        elif not self.registryValue('allowPrivateTarget'):
            irc.error(_('This command is disabled (supybot.plugins.Anonymous.'
                      'allowPrivateTarget is False).'), Raise=True)

    def say(self, irc, msg, args, target, text):
        """<channel> <text>

        Sends <text> to <channel>.
        """
        self._preCheck(irc, msg, target, 'say')
        self.log.info('Saying %q in %s due to %s.',
                      text, target, msg.prefix)
        irc.queueMsg(ircmsgs.privmsg(target, text))
        irc.noReply()
    say = wrap(say, ['inChannel', 'text'])

    def tell(self, irc, msg, args, target, text):
        """<nick> <text>

        Sends <text> to <nick>.  Can only be used if
        supybot.plugins.Anonymous.allowPrivateTarget is True.
        """
        self._preCheck(irc, msg, target, 'tell')
        self.log.info('Telling %q to %s due to %s.',
                      text, target, msg.prefix)
        irc.queueMsg(ircmsgs.privmsg(target, text))
        irc.noReply()
    tell = wrap(tell, ['nick', 'text'])

    def do(self, irc, msg, args, channel, text):
        """<channel> <action>

        Performs <action> in <channel>.
        """
        self._preCheck(irc, msg, channel, 'do')
        self.log.info('Performing %q in %s due to %s.',
                      text, channel, msg.prefix)
        irc.reply(text, action=True, to=channel)
    do = wrap(do, ['inChannel', 'text'])

    def react(self, irc, msg, args, channel, reaction, nick):
        """<channel> <reaction> <nick>

        Sends the <reaction> to <nick>'s last message.
        <reaction> is typically a smiley or an emoji.

        This may not be supported on the current network, as this
        command depends on IRCv3 features.
        This is also not supported if
        supybot.protocols.irc.experimentalExtensions disabled
        (don't enable it unless you know what you are doing).
        """
        self._preCheck(irc, msg, channel, 'react')

        if not conf.supybot.protocols.irc.experimentalExtensions():
            irc.error(_('Unable to react, '
                        'supybot.protocols.irc.experimentalExtensions is '
                        'disabled.'), Raise=True)

        if not 'message-tags' in irc.state.capabilities_ack:
            irc.error(_('Unable to react, the network does not support '
                        'message-tags.'), Raise=True)

        if irc.state.getClientTagDenied('draft/reply') \
                or irc.state.getClientTagDenied('draft/react'):
            irc.error(_('Unable to react, the network does not allow '
                        'draft/reply and/or draft/react.'), Raise=True)

        iterable = filter(functools.partial(self._validLastMsg, irc),
                          reversed(irc.state.history))
        for react_to_msg in iterable:
            if react_to_msg.nick == nick:
                break
        else:
            irc.error(_('I couldn\'t find a message from %s in '
                      'my history of %s messages.')
                      % (nick, len(irc.state.history)),
                      Raise=True)

        react_to_msgid = react_to_msg.server_tags.get('msgid')

        if not react_to_msgid:
            irc.error(_('Unable to react, %s\'s last message does not have '
                        'a message id.') % nick, Raise=True)

        self.log.info('Reacting with %q in %s due to %s.',
                      reaction, channel, msg.prefix)

        reaction_msg = ircmsgs.IrcMsg(command='TAGMSG', args=(channel,),
            server_tags={'+draft/reply': react_to_msgid,
                         '+draft/react': reaction})

        irc.queueMsg(reaction_msg)
    react = wrap(
        react, ['inChannel', 'somethingWithoutSpaces', 'nickInChannel'])

    def _validLastMsg(self, irc, msg):
        return msg.prefix and \
               msg.command == 'PRIVMSG' and \
               msg.channel


Anonymous = internationalizeDocstring(Anonymous)

Class = Anonymous


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
