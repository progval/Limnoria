.. _plugin-Fediverse:

Documentation for the Fediverse plugin for Supybot
==================================================

Purpose
-------
Fetches information from ActivityPub servers.

Enabling Secure Fetch
---------------------

The default configuration works with most ActivityPub servers, but not
all of them, because they require an HTTP Signature to fetch profiles
and statuses.

Because of how HTTP Signatures work, you need to add some configuration
for Limnoria to support it.

First, you should set ``supybot.servers.http.port`` to a port you want
your bot to listen on (by default it's 8080). If there are already
plugins using it (eg. if Fediverse is already running), you should
either unload all of them and load them back, or restart your bot.

Then, you must configure a reverse-proxy in front of your bot (eg. nginx),
and it must support HTTPS.

Finally, set ``supybot.servers.http.publicUrl`` to the public URL of this
server (when opening this URL in your browser, it should show a page with
a title like "Supybot web server index").

Usage
-----
Fetches information from ActivityPub servers.

.. _commands-Fediverse:

Commands
--------
.. _command-Fediverse-featured:

featured <@user@instance>
  Returnes the featured statuses of @user@instance (aka. pinned toots).

.. _command-Fediverse-profile:

profile <@user@instance>
  Returns generic information on the account @user@instance.

.. _command-Fediverse-status:

status <url>
  Shows the content of the status at <url>.

.. _command-Fediverse-statuses:

statuses <@user@instance>
  Returned the last statuses of @user@instance.

Configuration
-------------
supybot.plugins.Fediverse.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

