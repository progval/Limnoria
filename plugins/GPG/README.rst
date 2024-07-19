.. _plugin-GPG:

Documentation for the GPG plugin for Supybot
============================================

Purpose
-------

GPG: Provides authentication based on GPG keys.

Usage
-----

Provides authentication based on GPG keys.

First you must associate your GPG key with your Limnoria account. The gpg
add command takes two arguments, key id and key server.

My key is 0x0C207F07B2F32B67 and it's on keyserver pool.sks-keyservers.net
so and now I add it to my bot::

    <Mikaela> +gpg add 0x0C207F07B2F32B67 pool.sks-keyservers.net
    <Yvzabevn> 1 key imported, 0 unchanged, 0 not imported.

Now I can get token to sign so I can identify::

    <Guest45020> +gpg gettoken
    <Yvzabevn> Your token is: {03640620-97ea-4fdf-b0c3-ce8fb62f2dc5}. Please sign it with your GPG key, paste it somewhere, and call the 'auth' command with the URL to the (raw) file containing the signature.

Then I follow the instructions and sign my token in terminal::

    echo "{03640620-97ea-4fdf-b0c3-ce8fb62f2dc5}"|gpg --clearsign|curl -F 'sprunge=<-' http://sprunge.us

Note that I sent the output to curl with flags to directly send the
clearsigned content to sprunge.us pastebin. Curl should be installed on
most of distributions and comes with msysgit. If you remove the curl part,
you get the output to terminal and can pastebin it to any pastebin of
your choice. Sprunge.us has only plain text and is easy so I used it in
this example.

And last I give the bot link to the plain text signature::

    <Guest45020> +gpg auth http://sprunge.us/DUdd
    <Yvzabevn> You are now authenticated as Mikaela.

.. _commands-GPG:

Commands
--------

.. _command-gpg-key.add:

key add <key id> <key server>
  Add a GPG key to your account.

.. _command-gpg-key.list:

key list takes no arguments
  List your GPG keys.

.. _command-gpg-key.remove:

key remove <fingerprint>
  Remove a GPG key from your account.

.. _command-gpg-signing.auth:

signing auth <url>
  Check the GPG signature at the <url> and authenticates you if the key used is associated to a user.

.. _command-gpg-signing.gettoken:

signing gettoken takes no arguments
  Send you a token that you'll have to sign with your key.

.. _conf-GPG:

Configuration
-------------

.. _conf-supybot.plugins.GPG.auth:


supybot.plugins.GPG.auth
  This is a group of:

  .. _conf-supybot.plugins.GPG.auth.sign:


  supybot.plugins.GPG.auth.sign
    This is a group of:

    .. _conf-supybot.plugins.GPG.auth.sign.TokenTimeout:


    supybot.plugins.GPG.auth.sign.TokenTimeout
      This config variable defaults to "600", is not network-specific, and is not channel-specific.

      Determines the lifetime of a GPG signature authentication token (in seconds).

    .. _conf-supybot.plugins.GPG.auth.sign.enable:


    supybot.plugins.GPG.auth.sign.enable
      This config variable defaults to "True", is not network-specific, and is not channel-specific.

      Determines whether or not users are allowed to use GPG signing for authentication.

.. _conf-supybot.plugins.GPG.public:


supybot.plugins.GPG.public
  This config variable defaults to "True", is not network-specific, and is not channel-specific.

  Determines whether this plugin is publicly visible.

