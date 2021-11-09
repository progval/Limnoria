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
from unittest import skipIf

from supybot.test import *
from supybot import utils

from . import wikidata

class GeographyTestCase(PluginTestCase):
    plugins = ("Geography",)


class GeographyWikidataTestCase(SupyTestCase):
    @skipIf(not network, "Network test")
    def testDirect(self):
        """The queried object directly has a timezone property"""
        self.assertEqual(
            wikidata.timezone_from_qid("Q1384"), # New York
            utils.time.iana_timezone("America/New_York")
        ) 

    @skipIf(not network, "Network test")
    def testParent(self):
        """The queried object does not have a TZ property
        but it is part of an object that does"""
        self.assertEqual(
            wikidata.timezone_from_qid("Q22690"), # Metz, France
            utils.time.iana_timezone("Europe/Paris")
        ) 

    @skipIf(not network, "Network test")
    def testParentAndIgnoreSelf(self):
        """The queried object has a TZ property, but it's useless to us;
        however it is part of an object that has a useful one."""
        self.assertEqual(
            wikidata.timezone_from_qid("Q60"), # New York City, NY
            utils.time.iana_timezone("America/New_York")
        ) 

    @skipIf(not network, "Network test")
    def testParentQualifiedIgnorePreferred(self):
        """The queried object does not have a TZ property,
        and is part of an object that does.
        However, this parent's 'preferred' timezone is not the
        right one, so we must make sure to select the right one
        based on P518 ('applies to part')."""
        # La Réunion is a French region, but in UTC+4.
        # France has a bunch of timezone statements, and 'Europe/Paris'
        # is marked as Preferred because it is the time of metropolitan
        # France. However, it is not valid for La Réunion.
        self.assertEqual(
            wikidata.timezone_from_qid("Q17070"), # La Réunion
            datetime.timezone(datetime.timedelta(hours=4))
        ) 

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
