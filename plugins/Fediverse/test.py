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

from supybot import conf
from supybot.test import *


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


class FediverseTestCase(PluginTestCase):
    plugins = ("Fediverse",)
    config = {
        "supybot.servers.http.port": 18080,
        "supybot.servers.http.publicUrl": "https://particle18080.test.progval.net/",
    }

    def setUp(self):
        super().setUp()
        path = conf.supybot.directories.data.dirize(
            "Fediverse/instance_key.pem"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fd:
            fd.write(PRIVATE_KEY)

    if network:

        def testProfile(self):
            self.assertRegexp("profile @val@oc.todon.fr", "0E082B40E4376B1E")
            # TODO: add a test with an instance which only allows fetches
            # with valid signatures.

        def testProfileUnknown(self):
            self.assertResponse(
                "profile @nonexistinguser@oc.todon.fr",
                "Error: Unknown user @nonexistinguser@oc.todon.fr.",
            )


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
