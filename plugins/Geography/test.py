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

import datetime
import functools
import contextlib
from unittest import skipIf
from unittest.mock import patch

try:
    import pytz
except ImportError:
    pytz = None

try:
    import zoneinfo
except ImportError:
    zoneinfo = None

from supybot.test import *
from supybot import utils

from . import wikidata
from . import nominatim


def mock(f):
    @functools.wraps(f)
    def newf(self):
        with patch.object(wikidata, "uri_from_osmid", return_value="foo"):
            with patch.object(nominatim, "search_osmids", return_value=[42]):
                f(self)

    return newf


class GeographyTimezoneTestCase(PluginTestCase):
    plugins = ("Geography",)

    @skipIf(not pytz, "pytz is not available")
    @mock
    def testTimezonePytz(self):
        tz = pytz.timezone("Europe/Paris")
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp(
                "timezone Foo Bar", r"Europe/Paris \(currently UTC\+[12]\)"
            )

        tz = pytz.timezone("America/New_York")
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp(
                "timezone New York", r"America/New_York \(currently UTC-[45]\)"
            )

        tz = pytz.timezone("America/St_Johns")
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp(
                "timezone Newfoundland",
                r"America/St_Johns \(currently UTC-[23]:30\)",
            )

        tz = pytz.timezone("Asia/Kolkata")
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp(
                "timezone Delhi", r"Asia/Kolkata \(currently UTC\+5:30\)"
            )

    @skipIf(not zoneinfo, "Python is older than 3.9")
    @mock
    def testTimezoneZoneinfo(self):
        tz = zoneinfo.ZoneInfo("Europe/Paris")
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp(
                "timezone Foo Bar", r"Europe/Paris \(currently UTC\+[12]\)"
            )

        tz = zoneinfo.ZoneInfo("America/New_York")
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp(
                "timezone New York", r"America/New_York \(currently UTC-[45]\)"
            )

        tz = zoneinfo.ZoneInfo("America/St_Johns")
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp(
                "timezone Newfoundland",
                r"America/St_Johns \(currently UTC-[23]:30\)",
            )

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp(
                "timezone Delhi", r"Asia/Kolkata \(currently UTC\+5:30\)"
            )

    @skipIf(not zoneinfo, "Python is older than 3.9")
    @mock
    def testTimezoneAbsolute(self):
        tz = datetime.timezone(datetime.timedelta(hours=4))
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertResponse("timezone Foo Bar", "UTC+4")

        tz = datetime.timezone(datetime.timedelta(hours=4, minutes=30))
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertResponse("timezone Foo Bar", "UTC+4:30")

        tz = datetime.timezone(datetime.timedelta(hours=-4, minutes=30))
        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertResponse("timezone Foo Bar", "UTC-3:30")

    @skipIf(not network, "Network test")
    def testTimezoneIntegration(self):
        self.assertRegexp(
            "timezone Metz, France", r"Europe/Paris \(currently UTC\+[12]\)"
        )
        self.assertResponse("timezone Saint-Denis, La Réunion", "UTC+4")
        self.assertRegexp(
            "timezone Delhi", r"Asia/Kolkata \(currently UTC\+5:30\)"
        )
        self.assertRegexp("timezone Newfoundland", r"UTC-[23]:30")


class GeographyLocaltimeTestCase(PluginTestCase):
    plugins = ("Geography",)

    @skipIf(not pytz, "pytz is not available")
    @mock
    def testLocaltimePytz(self):
        tz = pytz.timezone("Europe/Paris")

        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp("localtime Foo Bar", r".*\+0[12]00$")

    @skipIf(not zoneinfo, "Python is older than 3.9")
    @mock
    def testLocaltimeZoneinfo(self):
        tz = zoneinfo.ZoneInfo("Europe/Paris")

        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp("localtime Foo Bar", r".*\+0[12]00$")

    @skipIf(not zoneinfo, "Python is older than 3.9")
    @mock
    def testLocaltimeAbsolute(self):
        tz = datetime.timezone(datetime.timedelta(hours=4))

        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp("localtime Foo Bar", r".*\+0400$")

        tz = datetime.timezone(datetime.timedelta(hours=4, minutes=30))

        with patch.object(wikidata, "timezone_from_uri", return_value=tz):
            self.assertRegexp("localtime Foo Bar", r".*\+0430$")

    @skipIf(not network, "Network test")
    def testLocaltimeIntegration(self):
        self.assertRegexp("localtime Metz, France", r".*\+0[12]00$")
        self.assertRegexp("localtime Saint-Denis, La Réunion", r".*\+0400$")


class GeographyWikidataTestCase(SupyTestCase):
    @skipIf(not network, "Network test")
    def testRelationOsmidToTimezone(self):
        self.assertEqual(
            wikidata.uri_from_osmid(450381),
            "http://www.wikidata.org/entity/Q22690",
        )
        self.assertEqual(
            wikidata.uri_from_osmid(192468),
            "http://www.wikidata.org/entity/Q47045",
        )
    @skipIf(not network, "Network test")
    def testNodeOsmidToTimezone(self):
        self.assertEqual(
            wikidata.uri_from_osmid(436012592),
            "http://www.wikidata.org/entity/Q933",
        )

    @skipIf(not network, "Network test")
    def testDirect(self):
        # The queried object directly has a timezone property
        self.assertEqual(
            # New York
            wikidata.timezone_from_uri("http://www.wikidata.org/entity/Q1384"),
            utils.time.iana_timezone("America/New_York"),
        )

    @skipIf(not network, "Network test")
    def testParent(self):
        # The queried object does not have a TZ property but it is part
        # of an object that does
        self.assertEqual(
            # Metz, France
            wikidata.timezone_from_uri(
                "http://www.wikidata.org/entity/Q22690"
            ),
            utils.time.iana_timezone("Europe/Paris"),
        )

    @skipIf(not network, "Network test")
    def testParentAndIgnoreSelf(self):
        # The queried object has a TZ property, but it's useless to us;
        # however it is part of an object that has a useful one.
        self.assertEqual(
            # New York City, NY
            wikidata.timezone_from_uri("http://www.wikidata.org/entity/Q60"),
            utils.time.iana_timezone("America/New_York"),
        )

        self.assertEqual(
            # Paris, France
            wikidata.timezone_from_uri("http://www.wikidata.org/entity/Q90"),
            utils.time.iana_timezone("Europe/Paris"),
        )

    @skipIf(not network, "Network test")
    def testParentQualifiedIgnorePreferred(self):
        # The queried object does not have a TZ property,
        # and is part of an object that does.
        # However, this parent's 'preferred' timezone is not the
        # right one, so we must make sure to select the right one
        # based on P518 ('applies to part').

        # La Réunion is a French region, but in UTC+4.
        # France has a bunch of timezone statements, and 'Europe/Paris'
        # is marked as Preferred because it is the time of metropolitan
        # France. However, it is not valid for La Réunion.
        self.assertEqual(
            # La Réunion
            wikidata.timezone_from_uri(
                "http://www.wikidata.org/entity/Q17070"
            ),
            datetime.timezone(datetime.timedelta(hours=4)),
        )


class GeographyNominatimTestCase(SupyTestCase):
    @skipIf(not network, "Network test")
    def testSearch(self):
        self.assertIn(450381, nominatim.search_osmids("Metz"))

        results = nominatim.search_osmids("Metz, France")
        self.assertEqual(results[0], 450381, results)

        results = nominatim.search_osmids("Saint-Denis, La Réunion")
        self.assertEqual(results[0], 192468, results)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
