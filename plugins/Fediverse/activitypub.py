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

import os
import json
import email
import base64
import functools
import contextlib
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key


from supybot import commands, conf
from supybot.utils import gen, web


XRD_URI = "{http://docs.oasis-open.org/ns/xri/xrd-1.0}"
ACTIVITY_MIMETYPE = "application/activity+json"


class ActivityPubError(Exception):
    pass


class ProtocolError(ActivityPubError):
    pass


class ActivityPubProtocolError(ActivityPubError):
    pass


class WebfingerError(ProtocolError):
    pass


class ActorNotFound(ActivityPubError):
    pass


def sandbox(f):
    """Runs a function in a process with limited memory to prevent
    XML memory bombs
    <https://docs.python.org/3/library/xml.html#xml-vulnerabilities>
    """

    @functools.wraps(f)
    def newf(*args, **kwargs):
        try:
            return commands.process(
                f,
                *args,
                timeout=10,
                heap_size=300 * 1024 * 1024,
                pn="Fediverse",
                cn=f.__name__,
                **kwargs
            )
        except (commands.ProcessTimeoutError, MemoryError):
            raise web.Error(
                "Page is too big or the server took "
                "too much time to answer the request."
            )

    return newf


@contextlib.contextmanager
def convert_exceptions(to_class, msg="", from_none=False):
    try:
        yield
    except Exception as e:
        arg = msg + str(e)
        if from_none:
            raise to_class(arg) from None
        else:
            raise to_class(arg) from e


@sandbox
def _get_webfinger_url(hostname):
    try:
        doc = ET.fromstring(
            web.getUrlContent("https://%s/.well-known/host-meta" % hostname)
        )

        for link in doc.iter(XRD_URI + "Link"):
            if link.attrib["rel"] == "lrdd":
                return link.attrib["template"]
    except web.Error:
        # Fall back to the default Webfinger URL
        return "https://%s/.well-known/webfinger?resource={uri}" % hostname


def has_webfinger_support(hostname):
    """Returns whether the hostname probably supports webfinger or not.

    This relies on an edge case of the Webfinger specification,
    so it may not successfully detect some hosts because they don't follow
    the specification."""
    request = urllib.request.Request(
        "https://%s/.well-known/webfinger" % hostname, method="HEAD"
    )
    try:
        urllib.request.urlopen(request)
    except urllib.error.HTTPError as e:
        if e.code == 400:
            # RFC 7033 requires a 400 response when the "resource" parameter
            # is missing: https://tools.ietf.org/html/rfc7033#section-4.2
            #
            # This works for:
            # * Misskey
            # * PeerTube
            # * Pleroma
            return True
        elif e.headers.get("Content-Type", "") == "application/jrd+json":
            # WriteFreely, and possibly others.
            # https://github.com/writeas/writefreely/issues/310
            return True
        elif e.code == 404:
            if e.headers.get("Server", "").lower() == "mastodon":
                # https://github.com/tootsuite/mastodon/issues/13757
                return True

    # Else, the host probably doesn't support Webfinger.

    # Known false negatives:
    # * Nextcloud (returns 404)
    # * Pixelfed (returns 302 to the homepage):
    #   https://github.com/pixelfed/pixelfed/issues/2180
    # * Plume (returns 404):
    #   https://github.com/Plume-org/Plume/issues/770
    return False


def webfinger(hostname, uri):
    template = _get_webfinger_url(hostname)
    assert template, "missing webfinger url template for %s" % hostname

    with convert_exceptions(ActorNotFound):
        content = web.getUrlContent(
            template.replace("{uri}", uri),
            headers={"Accept": "application/json"},
        )

    with convert_exceptions(WebfingerError, "Invalid JSON: ", True):
        return json.loads(content.decode())


def get_instance_actor_url():
    root_url = conf.supybot.servers.http.publicUrl()
    if not root_url:
        return None

    return urllib.parse.urljoin(root_url, "/fediverse/instance_actor")


def _generate_private_key():
    return generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )


def _get_private_key():
    path = conf.supybot.directories.data.dirize("Fediverse/instance_key.pem")
    if not os.path.isfile(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        key = _generate_private_key()
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(path, "wb") as fd:
            fd.write(pem)

    with open(path, "rb") as fd:
        return serialization.load_pem_private_key(
            fd.read(), password=None, backend=default_backend()
        )


def get_public_key():
    return _get_private_key().public_key()


def get_public_key_pem():
    return get_public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def signed_request(url, headers=None, data=None):
    method = "get" if data is None else "post"
    instance_actor_url = get_instance_actor_url()
    headers = gen.InsensitivePreservingDict(
        {**web.defaultHeaders, **(headers or {})}
    )

    if "Date" not in headers:
        headers["Date"] = email.utils.formatdate(usegmt=True)

    if instance_actor_url:
        parsed_url = urllib.parse.urlparse(url)
        signed_headers = [
            ("(request-target)", method + " " + parsed_url.path),
            ("host", parsed_url.hostname),
        ]
        for (header_name, header_value) in headers.items():
            signed_headers.append((header_name.lower(), header_value))
        signed_text = "\n".join("%s: %s" % header for header in signed_headers)

        private_key = _get_private_key()
        signature = private_key.sign(
            signed_text.encode(), padding.PKCS1v15(), hashes.SHA256()
        )

        headers["Signature"] = (
            'keyId="%s#main-key",' % instance_actor_url
            + 'headers="%s",' % " ".join(k for (k, v) in signed_headers)
            + 'signature="%s"' % base64.b64encode(signature).decode()
        )

    with convert_exceptions(ActivityPubProtocolError):
        return web.getUrlContent(url, headers=headers, data=data)


def actor_url(localuser, hostname):
    uri = "acct:%s@%s" % (localuser, hostname)
    for link in webfinger(hostname, uri)["links"]:
        if link["rel"] == "self" and link["type"] == ACTIVITY_MIMETYPE:
            return link["href"]

    raise ActorNotFound(localuser, hostname)


def get_actor(localuser, hostname):
    url = actor_url(localuser, hostname)

    return get_resource_from_url(url)


def get_resource_from_url(url):
    content = signed_request(url, headers={"Accept": ACTIVITY_MIMETYPE})

    assert content is not None, "Content from %s is None" % url

    with convert_exceptions(ActivityPubProtocolError, "Invalid JSON: ", True):
        return json.loads(content.decode())
