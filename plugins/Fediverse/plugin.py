###
# Copyright (c) 2020, Valentin Lorentz
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import re
import json
import importlib
import urllib.parse

from supybot import utils, callbacks, httpserver
from supybot.commands import wrap
from supybot.i18n import PluginInternationalization

from . import activitypub as ap


importlib.reload(ap)


_ = PluginInternationalization("Fediverse")


_username_regexp = re.compile("@(?P<localuser>[^@ ]+)@(?P<hostname>[^@ ]+)")


class FediverseHttp(httpserver.SupyHTTPServerCallback):
    name = "minimal ActivityPub server"
    defaultResponse = _(
        """
    You shouldn't be here, this subfolder is not for you. Go back to the
    index and try out other plugins (if any)."""
    )

    def doGetOrHead(self, handler, path, write_content):
        if path == "/instance_actor":
            self.instance_actor(write_content)
        else:
            assert False, repr(path)

    def doWellKnown(self, handler, path):
        actor_url = ap.get_instance_actor_url()
        instance_hostname = urllib.parse.urlsplit(actor_url).hostname
        instance_account = "acct:%s@%s" % (
            instance_hostname,
            instance_hostname,
        )
        if path == "/webfinger?resource=%s" % instance_account:
            headers = {"Content-Type": "application/jrd+json"}
            content = {
                "subject": instance_account,
                "links": [
                    {
                        "rel": "self",
                        "type": "application/activity+json",
                        "href": actor_url,
                    }
                ],
            }
            return (200, headers, json.dumps(content).encode())
        else:
            return None

    def instance_actor(self, write_content):
        self.send_response(200)
        self.send_header("Content-type", ap.ACTIVITY_MIMETYPE)
        self.end_headers()
        if not write_content:
            return
        pem = ap.get_public_key_pem()
        actor_url = ap.get_instance_actor_url()
        hostname = urllib.parse.urlparse(actor_url).hostname
        actor = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1",
            ],
            "id": actor_url,
            "preferredUsername": hostname,
            "type": "Person",
            "publicKey": {
                "id": actor_url + "#main-key",
                "owner": actor_url,
                "publicKeyPem": pem.decode(),
            },
            "inbox": actor_url + "/inbox",
        }
        self.wfile.write(json.dumps(actor).encode())


class Fediverse(callbacks.PluginRegexp):
    """Fetches information from ActivityPub servers."""

    threaded = True
    regexps = ["usernameSnarfer"]

    def __init__(self, irc):
        super().__init__(irc)
        self._startHttp()
        self._actor_cache = utils.structures.TimeoutDict(timeout=600)

    def _startHttp(self):
        callback = FediverseHttp()
        callback._plugin = self
        httpserver.hook("fediverse", callback)

    def die(self):
        self._stopHttp()
        super().die()

    def _stopHttp(self):
        httpserver.unhook("fediverse")

    def _get_actor(self, irc, username):
        if username in self._actor_cache:
            return self._actor_cache[username]
        match = _username_regexp.match(username)
        if not match:
            irc.errorInvalid("fediverse username", username)
        localuser = match.group("localuser")
        hostname = match.group("hostname")

        try:
            actor = ap.get_actor(localuser, hostname)
        except ap.ActorNotFound:
            # Usually a 404
            irc.error("Unknown user %s." % username, Raise=True)

        self._actor_cache[username] = actor
        self._actor_cache[actor["id"]] = actor

        return actor

    def _format_actor_username(self, actor):
        hostname = urllib.parse.urlparse(actor["id"]).hostname
        return "@%s@%s" % (actor["preferredUsername"], hostname)

    def _format_status(self, irc, status):
        assert status["type"] == "Note", status
        author_url = status["attributedTo"]
        author = self._get_actor(irc, author_url)
        return _("%s (%s): %s") % (
            author["name"],
            self._format_actor_username(author),
            utils.web.htmlToText(status["content"]),
        )

    @wrap(["somethingWithoutSpaces"])
    def profile(self, irc, msg, args, username):
        """<@user@instance>

        Returns generic information on the account @user@instance."""
        actor = self._get_actor(irc, username)

        irc.reply(
            _("\x02%s\x02 (%s): %s")
            % (
                actor["name"],
                self._format_actor_username(actor),
                utils.web.htmlToText(actor["summary"]),
            )
        )

    def usernameSnarfer(self, irc, msg, match):
        try:
            actor = self._get_actor(irc, match.group(0))
        except ap.ActivityPubError:
            # Be silent on errors
            return

        irc.reply(
            _("\x02%s\x02 (%s): %s")
            % (
                actor["name"],
                self._format_actor_username(actor),
                utils.web.htmlToText(actor["summary"]),
            )
        )

    usernameSnarfer.__doc__ = _username_regexp.pattern

    @wrap(["somethingWithoutSpaces"])
    def featured(self, irc, msg, args, username):
        """<@user@instance>

        Returned the featured statuses of @user@instance (aka. pinned toots).
        """
        actor = self._get_actor(irc, username)
        if "featured" not in actor:
            irc.error(_("No featured statuses."), Raise=True)
        statuses = json.loads(ap.signed_request(actor["featured"])).get(
            "orderedItems", []
        )
        irc.replies([self._format_status(irc, status) for status in statuses])


Class = Fediverse


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
