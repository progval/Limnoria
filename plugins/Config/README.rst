.. _plugin-Config:

Documentation for the Config plugin for Supybot
===============================================

Purpose
-------
Handles configuration of the bot while it is running.

Usage
-----
Provides access to the Supybot configuration. This is
a core Supybot plugin that should not be removed!

Commands
--------
channel [<network>] [<channel>] <name> [<value>]
  If <value> is given, sets the channel configuration variable for <name> to <value> for <channel> on the <network>. Otherwise, returns the current channel configuration value of <name>. <channel> is only necessary if the message isn't sent in the channel itself. More than one channel may be given at once by separating them with commas. <network> defaults to the current network.

config <name> [<value>]
  If <value> is given, sets the value of <name> to <value>. Otherwise, returns the current value of <name>. You may omit the leading "supybot." in the name if you so choose.

default <name>
  Returns the default value of the configuration variable <name>.

export <filename>
  Exports the public variables of your configuration to <filename>. If you want to show someone your configuration file, but you don't want that person to be able to see things like passwords, etc., this command will export a "sanitized" configuration file suitable for showing publicly.

help <name>
  Returns the description of the configuration variable <name>.

list <group>
  Returns the configuration variables available under the given configuration <group>. If a variable has values under it, it is preceded by an '@' sign. If a variable is a 'ChannelValue', that is, it can be separately configured for each channel using the 'channel' command in this plugin, it is preceded by an '#' sign. And if a variable is a 'NetworkValue', it is preceded by a ':' sign.

network [<network>] <name> [<value>]
  If <value> is given, sets the network configuration variable for <name> to <value> for <network>. Otherwise, returns the current network configuration value of <name>. <network> defaults to the current network.

reload takes no arguments
  Reloads the various configuration files (user database, channel database, registry, etc.).

reset channel [<network>] [<channel>] <name>
  Resets the channel-specific value of variable <name>, so that it will match the network-specific value (or the global one if the latter isn't set). <network> and <channel> default to the current network and channel.

reset network [<network>] [<channel>] <name>
  Resets the network-specific value of variable <name>, so that it will match the global. <network> defaults to the current network and channel.

search <word>
  Searches for <word> in the current configuration variables.

searchhelp <phrase>
  Searches for <phrase> in the help of current configuration variables.

searchvalues <word>
  Searches for <word> in the values of current configuration variables.

setdefault <name>
  Resets the configuration variable <name> to its default value. Use commands 'reset channel' and 'reset network' instead to make a channel- or network- specific value inherit from the global one.

Configuration
-------------
supybot.plugins.Config.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

