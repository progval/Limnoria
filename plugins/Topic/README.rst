.. _plugin-Topic:

Documentation for the Topic plugin for Supybot
==============================================

Purpose
-------
Provides commands for manipulating channel topics.

Usage
-----
This plugin allows you to use many topic-related functions,
such as Add, Undo, and Remove.

Commands
--------
add [<channel>] <topic>
  Adds <topic> to the topics for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

change [<channel>] <number> <regexp>
  Changes the topic number <number> on <channel> according to the regular expression <regexp>. <number> is the one-based index into the topics; <regexp> is a regular expression of the form s/regexp/replacement/flags. <channel> is only necessary if the message isn't sent in the channel itself.

default [<channel>]
  Sets the topic in <channel> to the default topic for <channel>. The default topic for a channel may be configured via the configuration variable supybot.plugins.Topic.default.

fit [<channel>] <topic>
  Adds <topic> to the topics for <channel>. If the topic is too long for the server, topics will be popped until there is enough room. <channel> is only necessary if the message isn't sent in the channel itself.

get [<channel>] <number>
  Returns topic number <number> from <channel>. <number> is a one-based index into the topics. <channel> is only necessary if the message isn't sent in the channel itself.

insert [<channel>] <topic>
  Adds <topic> to the topics for <channel> at the beginning of the topics currently on <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

list [<channel>]
  Returns a list of the topics in <channel>, prefixed by their indexes. Mostly useful for topic reordering. <channel> is only necessary if the message isn't sent in the channel itself.

lock [<channel>]
  Locks the topic (sets the mode +t) in <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

redo [<channel>]
  Undoes the last undo. <channel> is only necessary if the message isn't sent in the channel itself.

refresh [<channel>]
  Refreshes current topic set by anyone. Restores topic if empty. <channel> is only necessary if the message isn't sent in the channel itself.

remove [<channel>] <number1> [<number2> <number3>...]
  Removes topics <numbers> from the topic for <channel> Topics are numbered starting from 1; you can also use negative indexes to refer to topics starting the from the end of the topic. <channel> is only necessary if the message isn't sent in the channel itself.

reorder [<channel>] <number> [<number> ...]
  Reorders the topics from <channel> in the order of the specified <number> arguments. <number> is a one-based index into the topics. <channel> is only necessary if the message isn't sent in the channel itself.

replace [<channel>] <number> <topic>
  Replaces topic <number> with <topic>.

restore [<channel>]
  Restores the topic to the last topic set by the bot. <channel> is only necessary if the message isn't sent in the channel itself.

save [<channel>]
  Saves the topic in <channel> to be restored with 'topic default' later. <channel> is only necessary if the message isn't sent in the channel itself.

separator [<channel>] <separator>
  Sets the topic separator for <channel> to <separator> Converts the current topic appropriately.

set [<channel>] [<number>] <topic>
  Sets the topic <number> to be <text>. If no <number> is given, this sets the entire topic. <channel> is only necessary if the message isn't sent in the channel itself.

shuffle [<channel>]
  Shuffles the topics in <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

swap [<channel>] <first topic number> <second topic number>
  Swaps the order of the first topic number and the second topic number. <channel> is only necessary if the message isn't sent in the channel itself.

topic [<channel>]
  Returns the topic for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

undo [<channel>]
  Restores the topic to the one previous to the last topic command that set it. <channel> is only necessary if the message isn't sent in the channel itself.

unlock [<channel>]
  Unlocks the topic (sets the mode -t) in <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

Configuration
-------------
supybot.plugins.Topic.allowSeparatorinTopics
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will allow topics containing the defined separator to be used. You may want to disable this if you are signing all topics by nick (see the 'format' option for ways to adjust this).

supybot.plugins.Topic.alwaysSetOnJoin
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will set the topic every time it joins, or only if the topic is empty. Requires 'config plugins.topic.setOnJoin' to be set to True.

supybot.plugins.Topic.default
  This config variable defaults to "", is network-specific, and is  channel-specific.

  Determines what the default topic for the channel is. This is used by the default command to set this topic.

supybot.plugins.Topic.format
  This config variable defaults to "$topic", is network-specific, and is  channel-specific.

  Determines what format is used to add topics in the topic. All the standard substitutes apply, in addition to "$topic" for the topic itself.

supybot.plugins.Topic.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

supybot.plugins.Topic.recognizeTopiclen
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will recognize the TOPICLEN value sent to it by the server and thus refuse to send TOPICs longer than the TOPICLEN. These topics are likely to be truncated by the server anyway, so this defaults to True.

supybot.plugins.Topic.requireManageCapability
  This config variable defaults to "channel,op; channel,halfop", is network-specific, and is  channel-specific.

  Determines the capabilities required (if any) to make any topic changes, (everything except for read-only operations). Use 'channel,capab' for channel-level capabilities. Note that absence of an explicit anticapability means user has capability.

supybot.plugins.Topic.separator
  This config variable defaults to " | ", is network-specific, and is  channel-specific.

  Determines what separator is used between individually added topics in the channel topic.

supybot.plugins.Topic.setOnJoin
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will automatically set the topic on join if it is empty.

