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

import os
import copy
import json
import functools
import contextlib
from multiprocessing import Manager

from supybot import conf, log, utils
from supybot.test import ChannelPluginTestCase, network

from . import activitypub as ap
from .test_data import (
    PRIVATE_KEY,
    HOSTMETA_URL,
    HOSTMETA_DATA,
    WEBFINGER_URL,
    WEBFINGER_DATA,
    ACTOR_URL,
    ACTOR_DATA,
    OUTBOX_URL,
    OUTBOX_DATA,
    STATUS_URL,
    STATUS_DATA,
    STATUS_VALUE,
    STATUS_WITH_PHOTO_URL,
    STATUS_WITH_PHOTO_DATA,
    OUTBOX_FIRSTPAGE_URL,
    OUTBOX_FIRSTPAGE_DATA,
    BOOSTED_URL,
    BOOSTED_DATA,
    BOOSTED_ACTOR_URL,
    BOOSTED_ACTOR_DATA,
)


class BaseFediverseTestCase(ChannelPluginTestCase):
    config = {
        # Allow snarfing the same URL twice in a row
        "supybot.snarfThrottle": 0.0
    }
    plugins = ("Fediverse",)

    def setUp(self):
        super().setUp()
        path = conf.supybot.directories.data.dirize(
            "Fediverse/instance_key.pem"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fd:
            fd.write(PRIVATE_KEY)


class NetworkedFediverseTestCase(BaseFediverseTestCase):
    if network:

        def testNetworkProfile(self):
            self.assertRegexp("profile @val@oc.todon.fr", "0E082B40E4376B1E")
            # TODO: add a test with an instance which only allows fetches
            # with valid signatures.

        def testNetworkProfileUnknown(self):
            self.assertResponse(
                "profile @nonexistinguser@oc.todon.fr",
                "Error: Unknown user @nonexistinguser@oc.todon.fr.",
            )

        def testHasWebfingerSupport(self):
            self.assertTrue(ap.has_webfinger_support("oc.todon.fr"))
            self.assertFalse(ap.has_webfinger_support("example.org"))


class NetworklessFediverseTestCase(BaseFediverseTestCase):
    timeout = 0.5

    @contextlib.contextmanager
    def mockWebfingerSupport(self, value):
        original_has_webfinger_support = ap.has_webfinger_support

        @functools.wraps(original_has_webfinger_support)
        def newf(hostname):
            if value == "not called":
                assert False
            assert type(value) is bool
            return value

        ap.has_webfinger_support = newf

        yield

        ap.has_webfinger_support = original_has_webfinger_support

    @contextlib.contextmanager
    def mockRequests(self, expected_requests):
        with Manager() as m:
            expected_requests = m.list(list(expected_requests))
            original_getUrlContent = utils.web.getUrlContent

            @functools.wraps(original_getUrlContent)
            def newf(url, headers={}, data=None):
                self.assertIsNone(data, "Unexpected POST to %s" % url)
                assert expected_requests, url
                (expected_url, response) = expected_requests.pop(0)
                self.assertEqual(url, expected_url, "Unexpected URL: %s" % url)
                log.debug("Got request to %s", url)

                if isinstance(response, bytes):
                    return response
                elif isinstance(response, Exception):
                    raise response
                else:
                    assert False, response

            utils.web.getUrlContent = newf

            try:
                yield
            finally:
                utils.web.getUrlContent = original_getUrlContent

            self.assertEqual(
                list(expected_requests), [], "Less requests than expected."
            )

    def testFeaturedNone(self):
        featured = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": "https://example.org/users/someuser/collections/featured",
            "type": "OrderedCollection",
            "orderedItems": [],
        }
        expected_requests = [
            (HOSTMETA_URL, HOSTMETA_DATA),
            (WEBFINGER_URL, WEBFINGER_DATA),
            (ACTOR_URL, ACTOR_DATA),
            (
                "https://example.org/users/someuser/collections/featured",
                json.dumps(featured).encode(),
            ),
        ]
        with self.mockRequests(expected_requests):
            self.assertResponse(
                "featured @someuser@example.org", "No featured statuses."
            )

    def testFeaturedSome(self):
        featured = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {
                    "ostatus": "http://ostatus.org#",
                    "atomUri": "ostatus:atomUri",
                    "inReplyToAtomUri": "ostatus:inReplyToAtomUri",
                    "conversation": "ostatus:conversation",
                    "sensitive": "as:sensitive",
                    "toot": "http://joinmastodon.org/ns#",
                    "votersCount": "toot:votersCount",
                },
            ],
            "id": "https://example.org/users/someuser/collections/featured",
            "type": "OrderedCollection",
            "orderedItems": [
                {
                    "id": "https://example.org/users/someuser/statuses/123456789",
                    "type": "Note",
                    "summary": None,
                    "inReplyTo": "https://example.org/users/someuser/statuses/100543712346463856",
                    "published": "2018-08-13T15:49:00Z",
                    "url": "https://example.org/@someuser/123456789",
                    "attributedTo": "https://example.org/users/someuser",
                    "to": ["https://example.org/users/someuser/followers"],
                    "cc": ["https://www.w3.org/ns/activitystreams#Public"],
                    "sensitive": False,
                    "atomUri": "https://example.org/users/someuser/statuses/123456789",
                    "inReplyToAtomUri": "https://example.org/users/someuser/statuses/100543712346463856",
                    "conversation": "tag:example.org,2018-08-13:objectId=3002048:objectType=Conversation",
                    "content": "<p>This is a pinned toot</p>",
                    "contentMap": {"en": "<p>This is a pinned toot</p>"},
                    "attachment": [],
                    "tag": [],
                    "replies": {
                        "id": "https://example.org/users/someuser/statuses/123456789/replies",
                        "type": "Collection",
                        "first": {
                            "type": "CollectionPage",
                            "next": "https://example.org/users/someuser/statuses/123456789/replies?min_id=100723569923690076&page=true",
                            "partOf": "https://example.org/users/someuser/statuses/123456789/replies",
                            "items": [
                                "https://example.org/users/someuser/statuses/100723569923690076"
                            ],
                        },
                    },
                }
            ],
        }

        expected_requests = [
            (HOSTMETA_URL, HOSTMETA_DATA),
            (WEBFINGER_URL, WEBFINGER_DATA),
            (ACTOR_URL, ACTOR_DATA),
            (
                "https://example.org/users/someuser/collections/featured",
                json.dumps(featured).encode(),
            ),
        ]

        with self.mockRequests(expected_requests):
            self.assertRegexp(
                "featured @someuser@example.org", "This is a pinned toot"
            )

    def testProfile(self):
        expected_requests = [
            (HOSTMETA_URL, HOSTMETA_DATA),
            (WEBFINGER_URL, WEBFINGER_DATA),
            (ACTOR_URL, ACTOR_DATA),
        ]

        with self.mockRequests(expected_requests):
            self.assertResponse(
                "profile @someuser@example.org",
                "\x02someuser\x02 (@someuser@example.org): My Biography",
            )

    def testProfileSnarfer(self):
        with self.mockWebfingerSupport("not called"), self.mockRequests([]):
            self.assertSnarfNoResponse("aaa @nonexistinguser@example.org bbb")

        with conf.supybot.plugins.Fediverse.snarfers.username.context(True):
            expected_requests = [
                (HOSTMETA_URL, HOSTMETA_DATA),
                (WEBFINGER_URL, WEBFINGER_DATA),
                (ACTOR_URL, ACTOR_DATA),
            ]

            # First request, should work
            with self.mockWebfingerSupport(True), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfResponse(
                    "aaa @someuser@example.org bbb",
                    "\x02someuser\x02 (@someuser@example.org): My Biography",
                )

            # Same request; it is all cached
            with self.mockWebfingerSupport("not called"), self.mockRequests(
                []
            ):
                self.assertSnarfResponse(
                    "aaa @someuser@example.org bbb",
                    "\x02someuser\x02 (@someuser@example.org): My Biography",
                )

            # Nonexisting user

            expected_requests = [
                (HOSTMETA_URL, HOSTMETA_DATA),
                (WEBFINGER_URL, utils.web.Error("blah")),
            ]

            with self.mockWebfingerSupport("not called"), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfNoResponse(
                    "aaa @nonexistinguser@example.org bbb"
                )

    def testProfileSnarferNoWebfinger(self):
        with conf.supybot.plugins.Fediverse.snarfers.username.context(False):
            # No webfinger support, shouldn't make requests
            with self.mockWebfingerSupport(False), self.mockRequests([]):
                self.assertSnarfNoResponse("aaa @someuser@example.org bbb")

    def testProfileUrlSnarfer(self):
        with self.mockWebfingerSupport("not called"), self.mockRequests([]):
            self.assertSnarfNoResponse(
                "aaa https://example.org/users/someuser bbb"
            )

        with conf.supybot.plugins.Fediverse.snarfers.profile.context(True):
            expected_requests = [(ACTOR_URL, utils.web.Error("blah"))]

            with self.mockWebfingerSupport(True), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfNoResponse(
                    "aaa https://example.org/users/someuser bbb"
                )

            expected_requests = [(ACTOR_URL, ACTOR_DATA)]

            with self.mockWebfingerSupport("not called"), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfResponse(
                    "aaa https://example.org/users/someuser bbb",
                    "\x02someuser\x02 (@someuser@example.org): My Biography",
                )

    def testProfileUnknown(self):
        expected_requests = [
            (HOSTMETA_URL, HOSTMETA_DATA),
            (WEBFINGER_URL, utils.web.Error("blah")),
        ]

        with self.mockRequests(expected_requests):
            self.assertResponse(
                "profile @nonexistinguser@example.org",
                "Error: Unknown user @nonexistinguser@example.org.",
            )

    def testStatus(self):
        expected_requests = [
            (STATUS_URL, STATUS_DATA),
            (ACTOR_URL, ACTOR_DATA),
        ]

        with self.mockRequests(expected_requests):
            self.assertResponse(
                "status https://example.org/users/someuser/statuses/1234",
                "\x02someuser\x02 (@someuser@example.org): "
                + "@ FirstAuthor I am replying to you",
            )

    def testStatusAttachment(self):
        expected_requests = [
            (STATUS_WITH_PHOTO_URL, STATUS_WITH_PHOTO_DATA),
            (ACTOR_URL, ACTOR_DATA),
        ]

        with self.mockRequests(expected_requests):
            self.assertResponse(
                "status https://example.org/users/someuser/statuses/123",
                "\x02someuser\x02 (@someuser@example.org): "
                + "Here is a picture <https://example.org/foo.jpg>",
            )

    def testStatusError(self):
        expected_requests = [(STATUS_URL, utils.web.Error("blah"))]

        with self.mockRequests(expected_requests):
            self.assertResponse(
                "status https://example.org/users/someuser/statuses/1234",
                "Error: Could not get status: blah",
            )

        expected_requests = [
            (STATUS_URL, STATUS_DATA),
            (ACTOR_URL, utils.web.Error("blah")),
        ]

        with self.mockRequests(expected_requests):
            self.assertResponse(
                "status https://example.org/users/someuser/statuses/1234",
                "<error: blah>: " + "@ FirstAuthor I am replying to you",
            )

    def testStatuses(self):
        expected_requests = [
            (HOSTMETA_URL, HOSTMETA_DATA),
            (WEBFINGER_URL, WEBFINGER_DATA),
            (ACTOR_URL, ACTOR_DATA),
            (OUTBOX_URL, OUTBOX_DATA),
            (OUTBOX_FIRSTPAGE_URL, OUTBOX_FIRSTPAGE_DATA),
            (BOOSTED_URL, BOOSTED_DATA),
            (BOOSTED_ACTOR_URL, BOOSTED_ACTOR_DATA),
        ]

        with self.mockRequests(expected_requests):
            self.assertResponse(
                "statuses @someuser@example.org",
                "\x02someuser\x02 (@someuser@example.org): "
                + "@ FirstAuthor I am replying to you, "
                + "\x02someuser\x02 (@someuser@example.org): "
                + "\x02[CW This is a content warning]\x02 "
                + "This is a status with a content warning, and "
                + "\x02Boosted User\x02 (@BoostedUser@example.net): "
                + "Status Content "
                + "<https://example.net/system/media_attachments/image.png>",
            )

        # The actors are cached from the previous request
        expected_requests = [
            (OUTBOX_URL, OUTBOX_DATA),
            (OUTBOX_FIRSTPAGE_URL, OUTBOX_FIRSTPAGE_DATA),
            (BOOSTED_URL, BOOSTED_DATA),
        ]

        with self.mockRequests(expected_requests):
            with conf.supybot.plugins.Fediverse.format.statuses.showContentWithCW.context(
                False
            ):
                self.assertResponse(
                    "statuses @someuser@example.org",
                    "\x02someuser\x02 (@someuser@example.org): "
                    + "@ FirstAuthor I am replying to you, "
                    + "\x02someuser\x02 (@someuser@example.org): "
                    + "CW This is a content warning, and "
                    + "\x02Boosted User\x02 (@BoostedUser@example.net): "
                    + "Status Content "
                    + "<https://example.net/system/media_attachments/image.png>",
                )

    def testStatusUrlSnarferDisabled(self):
        with self.mockWebfingerSupport("not called"), self.mockRequests([]):
            self.assertSnarfNoResponse(
                "aaa https://example.org/users/someuser/statuses/1234 bbb"
            )

    def testStatusUrlSnarfer(self):
        with conf.supybot.plugins.Fediverse.snarfers.status.context(True):
            expected_requests = [
                (STATUS_URL, STATUS_DATA),
                (ACTOR_URL, ACTOR_DATA),
            ]

            with self.mockWebfingerSupport(True), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfResponse(
                    "aaa https://example.org/users/someuser/statuses/1234 bbb",
                    "\x02someuser\x02 (@someuser@example.org): "
                    + "@ FirstAuthor I am replying to you",
                )

    def testStatusUrlSnarferMore(self):
        # Actually this is a test for src/callbacks.py, but it's easier to
        # stick it here.
        status_value = copy.deepcopy(STATUS_VALUE)
        str_long = "l" + ("o" * 400) + "ng"
        str_message = "mess" + ("a" * 400) + "ge"
        status_obj = status_value["object"]
        status_obj["content"] = status_obj["content"].replace(
            "to you", "to you with a " + str_long + " " + str_message
        )
        with conf.supybot.plugins.Fediverse.snarfers.status.context(True):
            expected_requests = [
                (STATUS_URL, json.dumps(status_value).encode()),
                (ACTOR_URL, ACTOR_DATA),
            ]

            with self.mockWebfingerSupport(True), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfResponse(
                    "aaa https://example.org/users/someuser/statuses/1234 bbb",
                    "\x02someuser\x02 (@someuser@example.org): "
                    + "@ FirstAuthor I am replying to you with a "
                    + " \x02(2 more messages)\x02",
                )

        self.assertNoResponse(" ")
        self.assertResponse("more", str_long + "  \x02(1 more message)\x02")
        self.assertResponse("more", str_message)

    def testStatusUrlSnarferErrors(self):
        with conf.supybot.plugins.Fediverse.snarfers.status.context(True):
            expected_requests = [(STATUS_URL, utils.web.Error("blah"))]

            with self.mockWebfingerSupport(True), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfNoResponse(
                    "aaa https://example.org/users/someuser/statuses/1234 bbb"
                )

            expected_requests = [
                (STATUS_URL, STATUS_DATA),
                (ACTOR_URL, utils.web.Error("blah")),
            ]

            with self.mockWebfingerSupport("not called"), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfResponse(
                    "aaa https://example.org/users/someuser/statuses/1234 bbb",
                    "<error: blah>: @ FirstAuthor I am replying to you",
                )

    def testSnarferType(self):
        # Sends a request, notices it's a status, gives up
        with conf.supybot.plugins.Fediverse.snarfers.profile.context(True):
            expected_requests = [(STATUS_URL, STATUS_DATA)]

            with self.mockWebfingerSupport(True), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfNoResponse(
                    "aaa https://example.org/users/someuser/statuses/1234 bbb"
                )

        # Sends a request, notices it's a profile, gives up
        with conf.supybot.plugins.Fediverse.snarfers.profile.context(True):
            expected_requests = [(ACTOR_URL, ACTOR_DATA)]

            with self.mockWebfingerSupport("not called"), self.mockRequests(
                expected_requests
            ):
                self.assertSnarfNoResponse(
                    "aaa https://example.org/users/someuser/ bbb"
                )


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
