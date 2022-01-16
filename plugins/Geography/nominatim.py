###
# Copyright (c) 2021, Valentin Lorentz
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
import time
import threading
import urllib.parse

import supybot.utils as utils
from .common import headers

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"

_QUERY_LOCK = threading.Lock()
_LAST_QUERY_TIME = 0


def _wait_before_query():
    """Should be called before any API access. Blocks the current thread
    in order to follow the rate limit:
    https://operations.osmfoundation.org/policies/nominatim/"""

    global _LAST_QUERY_TIME

    min_time_between_queries = 1.0

    with _QUERY_LOCK:
        time_since_last_query = _LAST_QUERY_TIME - time.time()
        if time_since_last_query >= min_time_between_queries:
            time.sleep(min_time_between_queries - time_since_last_query)
        _LAST_QUERY_TIME = time.time()


def _query_nominatim(path, params):
    url = NOMINATIM_BASE_URL + path + "?" + urllib.parse.urlencode(params)

    _wait_before_query()

    content = utils.web.getUrlContent(url, headers=headers())
    return json.loads(content)


def search_osmids(query):
    """Queries nominatim's search endpoint and returns a list of OSM ids

    See https://nominatim.org/release-docs/develop/api/Search/ for details
    on the query format"""
    data = _query_nominatim("/search", {"format": "json", "q": query})

    return [item["osm_id"] for item in data if item.get("osm_id")]
