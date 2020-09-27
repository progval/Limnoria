Provides command completion for IRC clients that support it.

This plugin implements an early draft of the IRCv3 autocompletion client tags.
As this is not yet a released specification, it does nothing unless
`supybot.protocols.irc.experimentalExtensions` is set to True (keep it set to
False unless you know what you are doing).

If you are interested in this feature, please contribute to
[the discussion](https://github.com/ircv3/ircv3-specifications/pull/415)
