Fetches information from ActivityPub servers.

# Enabling Secure Fetch

The default configuration works with most ActivityPub servers, but not
all of them, because they require an HTTP Signature to fetch profiles
and statuses.

Because of how HTTP Signatures work, you need to add some configuration
for Limnoria to support it.

First, you should set `supybot.servers.http.port` to a port you want
your bot to listen on (by default it's 8080). If there are already
plugins using it (eg. if Fediverse is already running), you should
either unload all of them and load them back, or restart your bot.

Then, you must configure a reverse-proxy in front of your bot (eg. nginx),
and it must support HTTPS.

Finally, set `supybot.servers.http.publicUrl` to the public URL of this
server (when opening this URL in your browser, it should show a page with
a title like "Supybot web server index").
