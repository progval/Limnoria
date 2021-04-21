.. _plugin-Fediverse:

Documentation for the Fediverse plugin for Supybot
==================================================

Purpose
-------
Fetches information from ActivityPub servers.

Usage
-----
Fetches information from ActivityPub servers.

Enabling Secure Fetch
^^^^^^^^^^^^^^^^^^^^^

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

.. _commands-Fediverse:

Commands
--------
.. _command-fediverse-featured:

featured <@user@instance>
  Returnes the featured statuses of @user@instance (aka. pinned toots).

.. _command-fediverse-profile:

profile <@user@instance>
  Returns generic information on the account @user@instance.

.. _command-fediverse-status:

status <url>
  Shows the content of the status at <url>.

.. _command-fediverse-statuses:

statuses <@user@instance>
  Returned the last statuses of @user@instance.

.. _conf-Fediverse:

Configuration
-------------

.. _conf-supybot.plugins.Fediverse.format:


supybot.plugins.Fediverse.format
  This is a group of:

  .. _conf-supybot.plugins.Fediverse.format.statuses:


  supybot.plugins.Fediverse.format.statuses
    This is a group of:

    .. _conf-supybot.plugins.Fediverse.format.statuses.showContentWithCW:


    supybot.plugins.Fediverse.format.statuses.showContentWithCW
      This config variable defaults to "True", is network-specific, and is  channel-specific.

      Determines whether the content of a status will be shown when the status has a Content Warning.

.. _conf-supybot.plugins.Fediverse.public:


supybot.plugins.Fediverse.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Fediverse.snarfers:


supybot.plugins.Fediverse.snarfers
  This is a group of:

  .. _conf-supybot.plugins.Fediverse.snarfers.profile:


  supybot.plugins.Fediverse.snarfers.profile
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether the bot will output the profile of URLs to Fediverse accounts it sees in channel messages.

  .. _conf-supybot.plugins.Fediverse.snarfers.status:


  supybot.plugins.Fediverse.snarfers.status
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether the bot will output the content of statuses whose URLs it sees in channel messages.

  .. _conf-supybot.plugins.Fediverse.snarfers.username:


  supybot.plugins.Fediverse.snarfers.username
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether the bot will output the profile of @username@hostname accounts it sees in channel messages.

