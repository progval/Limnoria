****************
limnoria-pyodide
****************

This directory is an experiment / toy project to run Limnoria in a browser,
and access IRC servers with a Websocket
Don't expect it to work well or to be secure.

Implementation Status
=====================

Working:

* Connection to IRC
* All internals (commands, config, etc)

Not implemented yet:

* Populating the user database
* PluginDownloader
* User interface (show logs outside the dev console, ...)

Not implemented (yet?):

* anything else that depends on the network (eg. Web plugin)
* command thread (may be doable in Web workers?)

How it works
============

First, edit :file:`pyodide/limnoria.conf` to set the hostname and port
of an existing IRC server that supports WebSocket (such as Oragono).
It should not enforce a same-origin policy.

From the main source directory, run::

   python3 setup.py bdist_wheel && python3 pyodide/serve.py

It starts a web server running on ``[::]:8081``, open it with
your web browser (eg. http://[::1]:8081/). Then open your web browser's dev console.

It will load Pyodide, a Limnoria wheel, then the config file
You should see regular Limnoria logs, and the bot will join ``#limnoria-bots``
on the configured network.
