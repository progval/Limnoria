.. _plugin-Todo:

Documentation for the Todo plugin for Supybot
=============================================

Purpose
-------
The Todo plugin allows registered users to keep their own personal list of
tasks to do, with an optional priority for each.

Usage
-----
This plugin allows you to create your own personal to-do list on
the bot.

.. _commands-Todo:

Commands
--------
.. _command-todo-add:

add [--priority=<num>] <text>
  Adds <text> as a task in your own personal todo list. The optional priority argument allows you to set a task as a high or low priority. Any integer is valid.

.. _command-todo-change:

change <task id> <regexp>
  Modify the task with the given id using the supplied regexp.

.. _command-todo-remove:

remove <task id> [<task id> ...]
  Removes <task id> from your personal todo list.

.. _command-todo-search:

search [--{regexp} <value>] [<glob> <glob> ...]
  Searches your todos for tasks matching <glob>. If --regexp is given, its associated value is taken as a regexp and matched against the tasks.

.. _command-todo-setpriority:

setpriority <id> <priority>
  Sets the priority of the todo with the given id to the specified value.

.. _command-todo-todo:

todo [<username>] [<task id>]
  Retrieves a task for the given task id. If no task id is given, it will return a list of task ids that that user has added to their todo list.

.. _conf-Todo:

Configuration
-------------

.. _conf-supybot.plugins.Todo.allowThirdpartyReader:


supybot.plugins.Todo.allowThirdpartyReader
  This config variable defaults to "False", is not network-specific, and is  not channel-specific.

  Determines whether users can read the todo-list of another user.

.. _conf-supybot.plugins.Todo.public:


supybot.plugins.Todo.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

