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

import json

PRIVATE_KEY = b"""
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA6jtjTlaTh1aR+q3gpZvb4dj8s81zKmwy7cwn44LtLV+ivNf/
SkWPr1zkm/gWFItC3058Faqk9p4fdJaxVJJTW0KL7LlJs+LTcMsLi2nTgvBZg7oE
KRXZxuJJcc5QNkgY8vHt1PxdD17mZBGwfg2loZfnjZOOz4F8wdQ18Da1ZFUFyc+R
qj1THdXbpBjF7zcNyJOWzzRwhpiqdJomnTAYDscAkkF2/gI8tYP+Is31GOE1phPC
DH20uvJNUtDnXSdUm2Ol21LmePV4pWS75mcIHz5YAKwAGo9XoUQa8lC6IHw6LX+y
CVKkoSc0Ouzr3acQCLZ8EDUIh2nMhw/VtYV7JwIDAQABAoIBAFSARkwtqZ1qmtFf
xyqXttScblYDaWfFjv4A5+cJBb2XweL03ZGS1MpD7elir7yLnP1omBVM8aRS2TA7
aRAElfPXZxloovE1hGgtqCWMcRTM1s5R3kxgKKe6XRqkfoWGrxF+O/nZbU0tRFqX
kx92lulcHtoRgLTVlwdqImddpUTjQrWmrt3nEjTZj5tHcPGdC2ovH/bFrganbCR1
If6xG2r6RWSfMEpj7yFTKRvnLCr2VpviDOwFh/zZdwyqBRKW6LNZP04TtlFfKh5C
1R2tZVRHQ7Ed99yruirW0rmgOjA6dJTpN6oX6x3DpTi48oK2jktEIk07P7jy1mZY
NeCQcqkCgYEA+M0DQ+0fBm/RJyDIxsupMAf8De1kG6Bj8gVSRnvtD0Fb3LTswT3I
TDnIVttjOzBsbpZVdjdCE9Wcfj9pIwu3YTO54OTS8kiwYRshzEm3UpdPOSCnIZUx
jwbbwEHq0zEeIWVjDBDXN2fqEcu7gFqBzYivAh8hYq78BJkUeBWU3N0CgYEA8QJ0
6xS551VEGLbn9h5pPxze7l8a9WJc1uIxRexeBtd4UwJ5e1yLN68FVNjGr3JtreJ3
KP/VyynFubNRvwGEnifKe9QyiATFCbVeAFBQFuA0w89LOmBiHc+uHz1uA5oXnD99
Y0pEu8g+QsBKeQowMhkYnw4h5cq3AVCKRIdNpdMCgYEAwy5p8l7SKQWNagnBGJtr
BeAtr2tdToL8BUCBdAQCTCZ0/2b8GPjz6kCmVuVTKnrphbPwJYZiExdP5oauXyzw
1pNyreg1SJcXr4ZOdGocI/HJ18Iy+xiEwXSa7m+H3dg5j+9uzWdkvvWJXh6a4K2g
CPLCgIKVeUpXMPA6a55aow0CgYAMpoRckonvipo4ceFbGd2MYoeRG4zetHsLDHRp
py6ITWcTdF3MC9+C3Lz65yYGr4ryRaDblhIyx86JINB5piq/4nbOaST93sI48Dwu
6AhMKxiZ7peUSNrdlbkeCqtrpPr4SJzcSVmyQaCDAHToRZCiEI8qSiOdXDae6wtW
7YM14QKBgQDnbseQK0yzrsZoOmQ9PBULr4vNLiL5+OllOG1+GNNztk/Q+Xfx6Hvw
h6cgTcpZsvaa2CW6A2yqenmGfKBgiRoN39vFqjVDkjL1HaL3rPeK1H7RWrz1Sto7
rut+UhYHat9fo6950Wvxa4Iee9q0NOF0HUkD6WupcPyC0nSEex8Z6A==
-----END RSA PRIVATE KEY-----
"""

HOSTMETA_URL = "https://example.org/.well-known/host-meta"
HOSTMETA_DATA = b"""<?xml version="1.0" encoding="UTF-8"?>
<XRD xmlns="http://docs.oasis-open.org/ns/xri/xrd-1.0">
  <Link rel="lrdd" type="application/xrd+xml" template="https://example.org/.well-known/webfinger?resource={uri}"/>
</XRD>
"""

WEBFINGER_URL = "https://example.org/.well-known/webfinger?resource=acct:someuser@example.org"
WEBFINGER_VALUE = {
    "subject": "acct:someuser@example.org",
    "aliases": [
        "https://example.org/@someuser",
        "https://example.org/users/someuser",
    ],
    "links": [
        {
            "rel": "http://webfinger.net/rel/profile-page",
            "type": "text/html",
            "href": "https://example.org/@someuser",
        },
        {
            "rel": "self",
            "type": "application/activity+json",
            "href": "https://example.org/users/someuser",
        },
        {
            "rel": "http://ostatus.org/schema/1.0/subscribe",
            "template": "https://example.org/authorize_interaction?uri={uri}",
        },
    ],
}
WEBFINGER_DATA = json.dumps(WEBFINGER_VALUE).encode()

ACTOR_URL = "https://example.org/users/someuser"
ACTOR_VALUE = {
    "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
        {
            "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
            "toot": "http://joinmastodon.org/ns#",
            "featured": {"@id": "toot:featured", "@type": "@id"},
            "alsoKnownAs": {"@id": "as:alsoKnownAs", "@type": "@id"},
            "movedTo": {"@id": "as:movedTo", "@type": "@id"},
            "schema": "http://schema.org#",
            "PropertyValue": "schema:PropertyValue",
            "value": "schema:value",
            "IdentityProof": "toot:IdentityProof",
            "discoverable": "toot:discoverable",
            "Emoji": "toot:Emoji",
            "focalPoint": {"@container": "@list", "@id": "toot:focalPoint"},
        },
    ],
    "id": "https://example.org/users/someuser",
    "type": "Person",
    "following": "https://example.org/users/someuser/following",
    "followers": "https://example.org/users/someuser/followers",
    "inbox": "https://example.org/users/someuser/inbox",
    "outbox": "https://example.org/users/someuser/outbox",
    "featured": "https://example.org/users/someuser/collections/featured",
    "preferredUsername": "someuser",
    "name": "someuser",
    "summary": "<p>My Biography</p>",
    "url": "https://example.org/@someuser",
    "manuallyApprovesFollowers": False,
    "discoverable": True,
    "publicKey": {
        "id": "https://example.org/users/someuser#main-key",
        "owner": "https://example.org/users/someuser",
        "publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkaY84E/OjpjF7Dgy/nC+\nySBCiQvSOKBpNl468XP1QiOiMsILC1ec2J+LpU1Tm0kAC+uY8budLx6Wt+oz+4FU\n/82S9j9jVkWPiNVHJSQHXi13F9YQ4+MwC8niKc+qsmKUL8crSbd7dmCnOBxhvJWf\nfwOk1TW4u1fxXqHMFuw5zdfDlmRlU2FLX1LYTOxLnGp/ef/BAykV3rz6VouhAQwO\nhRay7ZgI5zlT7NtCoA17I8YiYfEs7MH0nBMrKOMw5eR1WDf5Gw78C/IAZHP1WVMv\n63V3N71OrMSfCH20OZ1H2Gyov5GX4+NSx7HI26dMDldQWOb2rYS9d0/7qM2xNUK8\n3wIDAQAB\n-----END PUBLIC KEY-----\n",
    },
    "attachment": [
        {"type": "PropertyValue", "name": "Pronoun", "value": "they"},
        {"type": "PropertyValue", "name": "Location", "value": "Somewhere"},
    ],
    "endpoints": {"sharedInbox": "https://example.org/inbox"},
    "icon": {
        "type": "Image",
        "mediaType": "image/png",
        "url": "https://assets.example.org/avatar.png",
    },
    "image": {
        "type": "Image",
        "mediaType": "image/png",
        "url": "https://assets.example.org/header.png",
    },
}
ACTOR_DATA = json.dumps(ACTOR_VALUE).encode()

OUTBOX_URL = "https://example.org/users/someuser/outbox"
OUTBOX_VALUE = {
    "@context": "https://www.w3.org/ns/activitystreams",
    "id": "https://example.org/users/someuser/outbox",
    "type": "OrderedCollection",
    "totalItems": 4835,
    "first": "https://example.org/users/someuser/outbox?page=true",
    "last": "https://example.org/users/someuser/outbox?min_id=0&page=true",
}
OUTBOX_DATA = json.dumps(OUTBOX_VALUE).encode()

STATUS_URL = "https://example.org/users/someuser/statuses/1234"
STATUS_VALUE = {
    "id": "https://example.org/users/someuser/statuses/1234/activity",
    "type": "Create",
    "actor": "https://example.org/users/someuser",
    "published": "2020-05-08T01:23:45Z",
    "to": ["https://example.org/users/someuser/followers"],
    "cc": [
        "https://www.w3.org/ns/activitystreams#Public",
        "https://example.com/users/FirstAuthor",
    ],
    "object": {
        "id": "https://example.org/users/someuser/statuses/1234",
        "type": "Note",
        "summary": None,
        "inReplyTo": "https://example.com/users/FirstAuthor/statuses/42",
        "published": "2020-05-08T01:23:45Z",
        "url": "https://example.org/@FirstAuthor/42",
        "attributedTo": "https://example.org/users/someuser",
        "to": ["https://example.org/users/someuser/followers"],
        "cc": [
            "https://www.w3.org/ns/activitystreams#Public",
            "https://example.com/users/FirstAuthor",
        ],
        "sensitive": False,
        "atomUri": "https://example.org/users/someuser/statuses/1234",
        "inReplyToAtomUri": "https://example.com/users/FirstAuthor/statuses/42",
        "conversation": "tag:example.com,2020-05-08:objectId=aaaa:objectType=Conversation",
        "content": '<p><span class="h-card"><a href="https://example.com/@FirstAuthor" class="u-url mention">@<span>FirstAuthor</span></a></span> I am replying to you</p>',
        "contentMap": {
            "en": '<p><span class="h-card"><a href="https://example.com/@FirstAuthor" class="u-url mention">@<span>FirstAuthor</span></a></span> I am replying to you</p>'
        },
        "attachment": [],
        "tag": [
            {
                "type": "Mention",
                "href": "https://example.com/users/FirstAuthor",
                "name": "@FirstAuthor@example.com",
            }
        ],
        "replies": {
            "id": "https://example.org/users/someuser/statuses/1234/replies",
            "type": "Collection",
            "first": {
                "type": "CollectionPage",
                "next": "https://example.org/users/someuser/statuses/1234/replies?only_other_accounts=true&page=true",
                "partOf": "https://example.org/users/someuser/statuses/1234/replies",
                "items": [],
            },
        },
    },
}
STATUS_DATA = json.dumps(STATUS_VALUE).encode()

STATUS_WITH_PHOTO_URL = "https://example.org/users/someuser/statuses/123"
STATUS_WITH_PHOTO_VALUE = {
    "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://example.org/schemas/litepub-0.1.jsonld",
    ],
    "actor": "https://example.org/users/someuser",
    "attachment": [
        {
            "mediaType": "image/jpeg",
            "name": "IMG_foo.jpg",
            "type": "Document",
            "url": "https://example.org/foo.jpg",
        }
    ],
    "attributedTo": "https://example.org/users/someuser",
    "cc": ["https://www.w3.org/ns/activitystreams#Public"],
    "content": "Here is a picture",
    "id": "https://example.org/users/someuser/statuses/123",
    "published": "2020-05-08T01:23:45Z",
    "sensitive": False,
    "summary": "",
    "tag": [],
    "to": ["https://example.org/users/someuser/followers"],
    "type": "Note",
}
STATUS_WITH_PHOTO_DATA = json.dumps(STATUS_WITH_PHOTO_VALUE).encode()

OUTBOX_FIRSTPAGE_URL = "https://example.org/users/someuser/outbox?page=true"
OUTBOX_FIRSTPAGE_VALUE = {
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
            "Emoji": "toot:Emoji",
            "focalPoint": {"@container": "@list", "@id": "toot:focalPoint"},
        },
    ],
    "id": "https://example.org/users/someuser/outbox?page=true",
    "type": "OrderedCollectionPage",
    "next": "https://example.org/users/someuser/outbox?max_id=104101144953797529&page=true",
    "prev": "https://example.org/users/someuser/outbox?min_id=104135036335976677&page=true",
    "partOf": "https://example.org/users/someuser/outbox",
    "orderedItems": [
        STATUS_VALUE,
        {
            "id": "https://example.org/users/someuser/statuses/1235/activity",
            "type": "Create",
            "actor": "https://example.org/users/someuser",
            "published": "2020-05-08T01:23:45Z",
            "to": ["https://example.org/users/someuser/followers"],
            "cc": ["https://www.w3.org/ns/activitystreams#Public"],
            "object": {
                "id": "https://example.org/users/someuser/statuses/1235",
                "type": "Note",
                "summary": "This is a content warning",
                "attributedTo": "https://example.org/users/someuser",
                "inReplyTo": None,
                "content": "<p>This is a status with a content warning</p>",
            },
        },
        {
            "id": "https://example.org/users/someuser/statuses/12345/activity",
            "type": "Announce",
            "actor": "https://example.org/users/someuser",
            "published": "2020-05-05T11:22:33Z",
            "to": ["https://example.org/users/someuser/followers"],
            "cc": [
                "https://example.net/users/BoostedUser",
                "https://www.w3.org/ns/activitystreams#Public",
            ],
            "object": "https://example.net/users/BoostedUser/statuses/123456",
            "atomUri": "https://example.org/users/someuser/statuses/12345/activity",
        },
    ],
}
OUTBOX_FIRSTPAGE_DATA = json.dumps(OUTBOX_FIRSTPAGE_VALUE).encode()

BOOSTED_URL = "https://example.net/users/BoostedUser/statuses/123456"
BOOSTED_VALUE = {
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
            "blurhash": "toot:blurhash",
            "focalPoint": {"@container": "@list", "@id": "toot:focalPoint"},
        },
    ],
    "id": "https://example.net/users/BoostedUser/statuses/123456",
    "type": "Note",
    "summary": None,
    "inReplyTo": None,
    "published": "2020-05-05T11:00:00Z",
    "url": "https://example.net/@BoostedUser/123456",
    "attributedTo": "https://example.net/users/BoostedUser",
    "to": ["https://www.w3.org/ns/activitystreams#Public"],
    "cc": ["https://example.net/users/BoostedUser/followers"],
    "sensitive": False,
    "atomUri": "https://example.net/users/BoostedUser/statuses/123456",
    "inReplyToAtomUri": None,
    "conversation": "tag:example.net,2020-05-05:objectId=bbbbb:objectType=Conversation",
    "content": "<p>Status Content</p>",
    "contentMap": {"en": "<p>Status Content</p>"},
    "attachment": [
        {
            "type": "Document",
            "mediaType": "image/png",
            "url": "https://example.net/system/media_attachments/image.png",
            "name": "Alt Text",
            "focalPoint": [0.0, 0.0],
        }
    ],
    "tag": [],
    "replies": {
        "id": "https://example.net/users/BoostedUser/statuses/123456/replies",
        "type": "Collection",
        "first": {
            "type": "CollectionPage",
            "next": "https://example.net/users/BoostedUser/statuses/123456/replies?only_other_accounts=true&page=true",
            "partOf": "https://example.net/users/BoostedUser/statuses/123456/replies",
            "items": [],
        },
    },
}
BOOSTED_DATA = json.dumps(BOOSTED_VALUE).encode()

BOOSTED_ACTOR_URL = "https://example.net/users/BoostedUser"
BOOSTED_ACTOR_VALUE = {
    "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
        {
            "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
            "toot": "http://joinmastodon.org/ns#",
            "featured": {"@id": "toot:featured", "@type": "@id"},
            "alsoKnownAs": {"@id": "as:alsoKnownAs", "@type": "@id"},
            "movedTo": {"@id": "as:movedTo", "@type": "@id"},
            "schema": "http://schema.org#",
            "PropertyValue": "schema:PropertyValue",
            "value": "schema:value",
            "IdentityProof": "toot:IdentityProof",
            "discoverable": "toot:discoverable",
            "focalPoint": {"@container": "@list", "@id": "toot:focalPoint"},
        },
    ],
    "id": "https://example.net/users/BoostedUser",
    "type": "Person",
    "following": "https://example.net/users/BoostedUser/following",
    "followers": "https://example.net/users/BoostedUser/followers",
    "inbox": "https://example.net/users/BoostedUser/inbox",
    "outbox": "https://example.net/users/BoostedUser/outbox",
    "featured": "https://example.net/users/BoostedUser/collections/featured",
    "preferredUsername": "BoostedUser",
    "name": "Boosted User",
    "url": "https://example.net/@BoostedUser",
    "endpoints": {"sharedInbox": "https://example.net/inbox"},
}
BOOSTED_ACTOR_DATA = json.dumps(BOOSTED_ACTOR_VALUE).encode()

PEERTUBE_ACTOR_VALUE = {
    "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
        {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
        {
            "pt": "https://joinpeertube.org/ns#",
            "sc": "http://schema.org/",
            "playlists": {"@id": "pt:playlists", "@type": "@id"},
        },
    ],
    "type": "Person",
    "id": "https://peertube.cpy.re/accounts/chocobozzz",
    "following": "https://peertube.cpy.re/accounts/chocobozzz/following",
    "followers": "https://peertube.cpy.re/accounts/chocobozzz/followers",
    "playlists": "https://peertube.cpy.re/accounts/chocobozzz/playlists",
    "inbox": "https://peertube.cpy.re/accounts/chocobozzz/inbox",
    "outbox": "https://peertube.cpy.re/accounts/chocobozzz/outbox",
    "preferredUsername": "chocobozzz",
    "url": "https://peertube.cpy.re/accounts/chocobozzz",
    "name": "chocobozzz",
    "published": "2017-11-28T08:48:24.271Z",
    "summary": None,
}
PEERTUBE_ACTOR_DATA = json.dumps(PEERTUBE_ACTOR_VALUE).encode()
PEERTUBE_ACTOR_URL = "https://peertube.cpy.re/accounts/chocobozzz"


PEERTUBE_VIDEO_VALUE = {
    "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
        {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
        {
            "pt": "https://joinpeertube.org/ns#",
            "sc": "http://schema.org/",
            "Hashtag": "as:Hashtag",
            "uuid": "sc:identifier",
            "category": "sc:category",
            "licence": "sc:license",
            "subtitleLanguage": "sc:subtitleLanguage",
            "sensitive": "as:sensitive",
            "language": "sc:inLanguage",
            "icons": "as:icon",
            "isLiveBroadcast": "sc:isLiveBroadcast",
            "liveSaveReplay": {
                "@type": "sc:Boolean",
                "@id": "pt:liveSaveReplay",
            },
            "permanentLive": {
                "@type": "sc:Boolean",
                "@id": "pt:permanentLive",
            },
            "latencyMode": {"@type": "sc:Number", "@id": "pt:latencyMode"},
            "Infohash": "pt:Infohash",
            "originallyPublishedAt": "sc:datePublished",
            "views": {"@type": "sc:Number", "@id": "pt:views"},
            "state": {"@type": "sc:Number", "@id": "pt:state"},
            "size": {"@type": "sc:Number", "@id": "pt:size"},
            "fps": {"@type": "sc:Number", "@id": "pt:fps"},
            "commentsEnabled": {
                "@type": "sc:Boolean",
                "@id": "pt:commentsEnabled",
            },
            "downloadEnabled": {
                "@type": "sc:Boolean",
                "@id": "pt:downloadEnabled",
            },
            "waitTranscoding": {
                "@type": "sc:Boolean",
                "@id": "pt:waitTranscoding",
            },
            "support": {"@type": "sc:Text", "@id": "pt:support"},
            "likes": {"@id": "as:likes", "@type": "@id"},
            "dislikes": {"@id": "as:dislikes", "@type": "@id"},
            "shares": {"@id": "as:shares", "@type": "@id"},
            "comments": {"@id": "as:comments", "@type": "@id"},
        },
    ],
    "to": ["https://www.w3.org/ns/activitystreams#Public"],
    "type": "Video",
    "name": "name of video",
    "duration": "PT5160S",
    "tag": [{"type": "Hashtag", "name": "vostfr"}],
    "category": {"identifier": "2", "name": "Films"},
    "licence": {"identifier": "4", "name": "Attribution - Non Commercial"},
    "language": {"identifier": "en", "name": "English"},
    "views": 13718,
    "sensitive": False,
    "waitTranscoding": False,
    "state": 1,
    "commentsEnabled": True,
    "downloadEnabled": True,
    "published": "2017-10-23T07:54:38.155Z",
    "originallyPublishedAt": None,
    "updated": "2022-07-13T07:03:12.373Z",
    "mediaType": "text/markdown",
    "content": "description of <strong>the</strong> video\r\nwith a second line",
    "support": None,
    "subtitleLanguage": [],
    "icon": [
        # redacted
    ],
    "url": [
        # redacted
    ],
    "attributedTo": [
        {"type": "Person", "id": PEERTUBE_ACTOR_URL},
        {
            "type": "Group",
            "id": ACTOR_URL,
        },
    ],
    "isLiveBroadcast": False,
    "liveSaveReplay": None,
    "permanentLive": None,
    "latencyMode": None,
}
PEERTUBE_VIDEO_DATA = json.dumps(PEERTUBE_VIDEO_VALUE).encode()
PEERTUBE_VIDEO_URL = "https://example.org/w/gABde9e210FGHre"
