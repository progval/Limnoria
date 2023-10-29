###
# Copyright (c) 2020-2021, Valentin Lorentz
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
from supybot.commands import urlSnarfer, wrap
from supybot.i18n import PluginInternationalization

from . import activitypub as ap
from .utils import parse_xsd_duration


importlib.reload(ap)


_ = PluginInternationalization("Fediverse")


_username_regexp = re.compile("@(?P<localuser>[^@ ]+)@(?P<hostname>[^@ ]+)")


def html_to_text(html):
    return utils.web.htmlToText(html).split("\n", 1)[0].strip()


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
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Error 404. There is nothing to see here.")

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
            "type": "Service",
            "publicKey": {
                "id": actor_url + "#main-key",
                "owner": actor_url,
                "publicKeyPem": pem.decode(),
            },
            "inbox": actor_url + "/inbox",
        }
        self.wfile.write(json.dumps(actor).encode())


class Fediverse(callbacks.PluginRegexp):
    """Fetches information from ActivityPub servers.

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
    """

    threaded = True
    regexps = ["usernameSnarfer", "urlSnarfer_"]
    callBefore = ("Web",)

    def __init__(self, irc):
        super().__init__(irc)
        self._startHttp()
        self._actor_cache = utils.structures.TimeoutDict(timeout=600)

        # Used when snarfing, to cheaply avoid querying non-ActivityPub
        # servers.
        # Is also written to when using commands that successfully find
        # ActivityPub data.
        self._webfinger_support_cache = utils.structures.TimeoutDict(
            timeout=60 * 60 * 24
        )

    def _startHttp(self):
        callback = FediverseHttp()
        callback._plugin = self
        httpserver.hook("fediverse", callback)

    def die(self):
        self._stopHttp()
        super().die()

    def _stopHttp(self):
        httpserver.unhook("fediverse")

    def _has_webfinger_support(self, hostname):
        if hostname not in self._webfinger_support_cache:
            try:
                self._webfinger_support_cache[hostname] = ap.has_webfinger_support(
                    hostname
                )
            except Exception as e:
                self.log.error(
                    "Checking Webfinger support for %s raised %s", hostname, e
                )
                return False
        return self._webfinger_support_cache[hostname]

    def _get_actor(self, irc, username):
        if username in self._actor_cache:
            return self._actor_cache[username]
        match = _username_regexp.match(username)
        if match:
            localuser = match.group("localuser")
            hostname = match.group("hostname")

            try:
                actor = ap.get_actor(localuser, hostname)
            except ap.ActorNotFound:
                irc.error("Unknown user %s." % username, Raise=True)
        else:
            match = utils.web.urlRe.match(username)
            if match:
                # TODO: error handling
                actor = ap.get_resource_from_url(match.group(0))
                try:
                    hostname = urllib.parse.urlparse(actor.get("id")).hostname
                    username = "@%s@%s" % (
                        hostname,
                        actor.get["preferredUsername"],
                    )
                except Exception:
                    username = None
            else:
                irc.errorInvalid("fediverse username", username)

        if username:
            self._actor_cache[username] = actor
            self._webfinger_support_cache[hostname] = True

        self._actor_cache[actor["id"]] = actor

        return actor

    def _format_actor_fullname(self, actor):
        try:
            hostname = urllib.parse.urlparse(actor.get("id")).hostname
        except Exception:
            hostname = "<unknown>"
        username = actor.get("preferredUsername", "<unknown>")
        name = actor.get("name", username)
        return "\x02%s\x02 (@%s@%s)" % (name, username, hostname)

    def _format_author(self, irc, author):
        if isinstance(author, str):
            # it's an URL
            try:
                author = self._get_actor(irc, author)
            except ap.ActivityPubError as e:
                return _("<error: %s>") % str(e)
            else:
                return self._format_actor_fullname(author)
        elif isinstance(author, dict):
            if author.get("type") == "Group":
                # Typically, there is an actor named "Default <username> channel"
                # on PeerTube, which we do not want to show.
                return None
            if author.get("id"):
                return self._format_author(irc, author["id"])
        elif isinstance(author, list):
            return format(
                "%L",
                filter(
                    bool, [self._format_author(irc, item) for item in author]
                ),
            )
        else:
            return "<unknown>"

    def _format_status(self, irc, msg, status):
        if status["type"] == "Create":
            return self._format_status(irc, msg, status["object"])
        elif status["type"] == "Note":
            cw = status.get("summary")
            author_fullname = self._format_author(
                irc, status.get("attributedTo")
            )
            if cw:
                if self.registryValue(
                    "format.statuses.showContentWithCW",
                    msg.channel,
                    irc.network,
                ):
                    # show CW and content
                    res = [
                        _("%s: \x02[CW %s]\x02 %s")
                        % (
                            author_fullname,
                            cw,
                            html_to_text(status["content"]),
                        )
                    ]
                else:
                    # show CW but not content
                    res = [_("%s: CW %s") % (author_fullname, cw)]
            else:
                # no CW, show content
                res = [
                    _("%s: %s")
                    % (
                        author_fullname,
                        html_to_text(status["content"]),
                    )
                ]

            for attachment in status.get("attachment", []):
                res.append(utils.str.url(attachment.get("url")))
            return " ".join(res)
        elif status["type"] == "Announce":
            # aka boost; let's go fetch the original status
            try:
                content = ap.signed_request(
                    status["object"], headers={"Accept": ap.ACTIVITY_MIMETYPE}
                )
                status = json.loads(content.decode())
                return self._format_status(irc, msg, status)
            except ap.ActivityPubProtocolError as e:
                return "<Could not fetch status: %s>" % e.args[0]
        elif status["type"] == "Video":
            author_fullname = self._format_author(
                irc, status.get("attributedTo")
            )
            return format(
                _("\x02%s\x02 (%T) by %s: %s"),
                status["name"],
                abs(parse_xsd_duration(status["duration"]).total_seconds()),
                author_fullname,
                html_to_text(status["content"]),
            )
        else:
            assert False, "Unknown status type %s: %r" % (
                status["type"],
                status,
            )

    @wrap(["somethingWithoutSpaces"])
    def profile(self, irc, msg, args, username):
        """<@user@instance>

        Returns generic information on the account @user@instance."""
        actor = self._get_actor(irc, username)

        irc.reply(
            _("%s: %s")
            % (
                self._format_actor_fullname(actor),
                html_to_text(actor["summary"]),
            )
        )

    def _format_profile(self, irc, msg, actor):
        return _("%s: %s") % (
            self._format_actor_fullname(actor),
            html_to_text(actor["summary"]),
        )

    def usernameSnarfer(self, irc, msg, match):
        if callbacks.addressed(irc, msg):
            return
        if not self.registryValue(
            "snarfers.username", msg.channel, irc.network
        ):
            return

        if not self._has_webfinger_support(match.group("hostname")):
            self.log.debug(
                "Not snarfing, host doesn't have Webfinger support."
            )
            return

        try:
            actor = self._get_actor(irc, match.group(0))
        except ap.ActivityPubError as e:
            self.log.info("Could not fetch %s: %s", match.group(0), e)
            # Be silent on errors
            return

        irc.reply(self._format_profile(irc, msg, actor), prefixNick=False)

    usernameSnarfer.__doc__ = _username_regexp.pattern

    @urlSnarfer
    def urlSnarfer_(self, irc, msg, match):
        channel = msg.channel
        network = irc.network
        url = match.group(0)
        if not channel:
            return
        if callbacks.addressed(irc, msg):
            return
        snarf_profile = self.registryValue(
            "snarfers.profile", channel, network
        )
        snarf_status = self.registryValue("snarfers.status", channel, network)
        if not snarf_profile and not snarf_status:
            return

        hostname = urllib.parse.urlparse(url).hostname
        if not self._has_webfinger_support(hostname):
            self.log.debug(
                "Not snarfing, host doesn't have Webfinger support."
            )
            return

        try:
            resource = ap.get_resource_from_url(url)
        except ap.ActivityPubError:
            return

        try:
            if snarf_profile and resource["type"] in ("Person", "Service"):
                irc.reply(self._format_profile(irc, msg, resource))
            elif snarf_status and resource["type"] in (
                "Create",
                "Note",
                "Announce",
            ):
                irc.reply(
                    self._format_status(irc, msg, resource), prefixNick=False
                )
        except ap.ActivityPubError:
            return

    urlSnarfer_.__doc__ = utils.web._httpUrlRe

    @wrap(["somethingWithoutSpaces"])
    def featured(self, irc, msg, args, username):
        """<@user@instance>

        Returnes the featured statuses of @user@instance (aka. pinned toots).
        """
        actor = self._get_actor(irc, username)
        if "featured" not in actor:
            irc.reply(_("No featured statuses."))
            return
        statuses = json.loads(
            ap.signed_request(actor["featured"]).decode()
        ).get("orderedItems", [])
        if not statuses:
            irc.reply(_("No featured statuses."))
            return
        irc.replies(
            filter(
                bool,
                (self._format_status(irc, msg, status) for status in statuses),
            )
        )

    @wrap(["somethingWithoutSpaces"])
    def statuses(self, irc, msg, args, username):
        """<@user@instance>

        Returned the last statuses of @user@instance.
        """
        actor = self._get_actor(irc, username)
        if "outbox" not in actor:
            irc.error(_("No status."), Raise=True)
        outbox = json.loads(ap.signed_request(actor["outbox"]).decode())

        # Fetches the first page of the outbox. This should be a good-enough
        # approximation of the number of statuses to show.
        statuses = json.loads(ap.signed_request(outbox["first"]).decode()).get(
            "orderedItems", []
        )
        irc.replies(
            filter(
                bool,
                (self._format_status(irc, msg, status) for status in statuses),
            )
        )

    @wrap(["url"])
    def status(self, irc, msg, args, url):
        """<url>

        Shows the content of the status at <url>.
        """
        try:
            status = ap.get_resource_from_url(url)
        except ap.ActivityPubError as e:
            irc.error(_("Could not get status: %s") % e.args[0], Raise=True)
        else:
            hostname = urllib.parse.urlparse(url).hostname
            self._webfinger_support_cache[hostname] = True

        irc.reply(self._format_status(irc, msg, status))


Class = Fediverse


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
