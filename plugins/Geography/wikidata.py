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
import string
import datetime
import urllib.parse

import supybot.utils as utils

SPARQL_URL = "https://query.wikidata.org/sparql"

TIMEZONE_QUERY = string.Template("""
SELECT ?item ?itemLabel ?rank ?endtime ?appliestopart ?utcoffset ?tzid (MIN(?area) AS ?min_area) WHERE {

  # find all entities that the subject is part of, recursively
  wd:$subject (wdt:P131*) ?item.

  # Get all timezones (returns a superset of "?item wdt:P421 ?timezone", as it does not filter on rank)
  ?item p:P421 ?statement.
  ?statement ps:P421 ?timezone.

  ?statement wikibase:rank ?rank.

  # fetch the end of validity of the given statement (TODO: check it)
  OPTIONAL { ?statement pq:P582 ?endtime. }

  # filter out statements that applies only to a part of ?item...
  {
    FILTER NOT EXISTS {
      ?statement pq:P518 ?appliestopart.
    }
  }
  UNION {
    # ... unless it applies to a part that contains what we are interested in
    ?statement pq:P518 ?appliestopart.
    wd:$subject (wdt:P131*) ?appliestopart.
  }

  # Filter out values only valid in certain periods of the year (DST vs normal time)
  FILTER NOT EXISTS {
    ?statement pq:P1264 ?validinperiod.
  }

  # store the identifier of the object the statement applies to
  BIND(IF(BOUND(?appliestopart),?appliestopart,?item) AS ?statementsubject).

  #OPTIONAL { ?statementsubject wdt:P1082 ?population. }
  OPTIONAL { ?statementsubject wdt:P2046 ?area. }

  # ?timezone wdt:P31 ?timezonetype.
  # ?timezone wdt:P31 wd:Q17272692. # only keep IANA timezones
  # ?timezone wdt:P31 wd:Q17272482. # only keep UTC offsets

  {
    # Get either an IANA timezone ID...
    ?timezone wdt:P6687 ?tzid.
  }
  UNION
  {
    # ... or an absolute UTC offset that is not subject to DST
    ?timezone p:P2907 ?utcoffset_statement.
    ?utcoffset_statement ps:P2907 ?utcoffset.

    FILTER NOT EXISTS {                  
      ?utcoffset_statement pq:P1264 ?utcoffset_validinperiod.
    }
  }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}

# Deduplicate in case there is more than one ?area statement
GROUP BY ?item ?itemLabel ?rank ?endtime ?appliestopart ?utcoffset ?tzid

# Get the smallest entities first. As they are more specific,
# they are more likely to be correct.
ORDER BY ?min_area DESC(?tzid)

LIMIT 1
""")

def _query_sparql(query):
    params = {"format": "json", "query": query}
    url = SPARQL_URL + "?" + urllib.parse.urlencode(params)

    # Comply with https://meta.wikimedia.org/wiki/User-Agent_policy
    headers = utils.web.defaultHeaders.copy()
    headers["User-agent"] += " https://github.com/progval/Limnoria/ - Geography plugin"

    content = utils.web.getUrlContent(url, headers=headers)
    return json.loads(content)

def timezone_from_qid(location_qid):
    """Returns a :class:datetime.tzinfo object, given a Wikidata Q-ID.
    eg. ``"Q60"`` for New York City."""
    data = _query_sparql(TIMEZONE_QUERY.substitute(subject=location_qid))
    results = data["results"]["bindings"]
    for result in results:
        if "tzid" in result:
            return utils.time.iana_timezone(result["tzid"]["value"])
        else:
            assert "utcoffset" in result
            utc_offset = float(result["utcoffset"]["value"])
            return datetime.timezone(datetime.timedelta(hours=utc_offset))
