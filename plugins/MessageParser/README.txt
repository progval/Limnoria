The MessageParser plugin allows you to set custom regexp triggers, which will trigger the bot to respond if they match anywhere in the message. This is useful for those cases when you want a bot response even when the bot was not explicitly addressed by name or prefix character.

== Commands ==

The main commands of the plugin are 'add', 'remove', and 'show'. There are also 'listall' and 'triggerrank'. We will discuss them all below.

=== messageparser add ===

To add a trigger, use the obviously-named "messageparser add" command. It takes two arguments, the regexp (using standard python style regular expressions), and the command that is executed when it matches. If either of those contain spaces, they must be quoted. If they contain quotes, those quotes must be escaped.

Here is a basic example command:
messageparser add "some stuff" "echo I saw some stuff!"
Once that is added, any message that contains the string "some stuff" will cause the bot to respond with "I saw some stuff!".

The response string can contain placeholders for regexp match groups. These will be interpolated into the string. Here's an example:
messageparser add "my name is (\w+)" "echo hello, $1!"
If you then send a message "hi, my name is bla", the bot will respond with "hello, bla!". 

The regexp triggers are set to be unique - if you add the same regexp on top of an existing one, its response string will be overwritten.

If more than one regexp trigger matches, each one will cause its respective response. If one regexp matches multiple times in a message, it will cause multiple responses. 

You can use arbitrary supybot commands as the action - be creative, and don't limit yourself to 'echo'. A couple of my favorites are:
messageparser add ",,(\w+)" "$1"
This one causes the bot to take one-word commands from in-message, if they're preceded by double-comma. So you could send a message like "Show me your ,,version and your ,,uptime", and you'd get two responses back, one with version, one with uptime.

messageparser add ",,\(([^\)]*?)\)" "$1"
This one causes the bot to take multi-word commands from in-message, if they're preceded by double-comma and open-parenthesis, and closed with close-parenthesis. So you could send a message like "I'd like a ,,(factoids search *) please", and you'd the output of command 'factoids search *'.

Your imagination is the limit!

The trigger database is deliberately set to only allow unique regexps as triggers, to avoid accidental spam from multiple instances of the same regexp. If, however, you really want multiple responses to happen to one trigger, you can always tweak your regexp with some non-matching groups. My favorites for this are '(?i)', which causes regexp to be non-case-sensitive, but doesn't consume any characters, and '(?m)', which causes the regexp to be multiline, but also doesn't consume any characters. (See python documentation on the re module here: http://docs.python.org/library/re.html)

So, for example, if you want to set multiple triggers on someone saying "stuff", you could add triggers for "stuff", "(?m)stuff", "(?m)(?m)stuff", "(?m)(?m)(?m)stuff", etc. If you want it to be case-sensitive, you can use (?i) to the same effect.

But generally it's a good idea to avoid spamminess. :)

=== messageparser remove ===

You can remove a trigger using the remove command, by specifying the verbatim regexp you want to remove the trigger for. Here's a simple example:
messageparser remove "some stuff"
This would remove the trigger for "some stuff" if you have set one. 

=== messageparser show ===

You can show the contents of the response string for a particular trigger by using the show command, and specifying the verbatim regexp you want to display. Here's an example:
messageparser show "my name is (\w+)"
Will display the trigger with its associated response string.

=== messageparser listall ===

The listall command will list all the regexps which are currently in the database. It takes no agruments. If you send this out of channel, specify channel name as argument.

=== messageparser triggerrank ===

The plugin by default keeps statistics on how many times each regexp was triggered. Using the triggerrank command you can see the regexps sorted in descending order of number of trigger times. The number in parentheses after each regexp is the count of trigger occurrences for each.

Note if you delete, or overwrite an existing, regexp, its count will be reset to 0.

== Configuration ==

Supybot configuration is self-documenting. Run  'config list plugins.messageparser' for list of config keys, and 'config help <config key>' for help on each one.