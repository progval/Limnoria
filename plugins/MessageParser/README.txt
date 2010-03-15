The MessageParser plugin allows you to set custom regexp triggers, which will trigger the bot to respond if they match anywhere in the message. This is useful for those cases when you want a bot response even when the bot was not explicitly addressed by name or prefix character.

== Commands ==

The main commands of the plugin are 'add', 'remove', and 'show'. There are also 'listall' and 'triggerrank'. We will discuss them all below.

=== messageparser add ===

To add a trigger, use the obviously-named "messageparser add" command. It takes two arguments, the regexp (using standard python style regular expressions), and the output message response string. If either of those contain spaces, they must be quoted. 

Here is a basic example command:
messageparser add "some stuff" "I saw some stuff!"
Once that is added, any message that contains the string "some stuff" will cause the bot to respond with "I saw some stuff!".

The response string can contain placeholders for regexp match groups. These will be interpolated into the string. Here's an example:
messageparser add "my name is (\w+)" "hello, $1!"
If you then send a message "hi, my name is bla", the bot will respond with "hello, bla!". 

The regexp triggers are set to be unique - if you add the same regexp on top of an existing one, its response string will be overwritten.

If more than one regexp trigger matches, their responses will be concatenated into one response message, separated by " and ".

=== messageparser remove ===

You can remove a trigger using the remove command, by specifying the verbatim regexp you want to remove the trigger for. Here's a simple example:
messageparser remove "some stuff"
This would remove the trigger for "some stuff" that we have set in the section above.

=== messageparser show ===

You can show the contents of the response string for a particular trigger by using the show command, and specifying the verbatim regexp you want to display. Here's an example:
messageparser show "my name is (\w+)"
Will display the trigger with its associated response string.

=== messageparser listall ===

The listall command will list all the regexps which are currently in the database. It takes no agruments.

=== messageparser triggerrank ===

The plugin by default keeps statistics on how many times each regexp was triggered. Using the triggerrank command you can see the regexps sorted in descending order of number of trigger times. The number in parentheses after each regexp is the count of trigger occurrences for each.

== Configuration ==

Supybot configuration is self-documenting. Run  'config list plugins.messageparser' for list of config keys, and 'config help <config key>' for help on each one.