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
import re

from supybot import conf, utils, plugins, ircutils, callbacks
from supybot.commands import *
from supybot.i18n import PluginInternationalization

from . import nominatim
from . import wikidata

_ = PluginInternationalization("Geography")


def timezone_from_uri(irc, uri):
    try:
        return wikidata.timezone_from_uri(uri)
    except utils.time.UnknownTimeZone as e:
        irc.error(
            format(_("Could not understand timezone: %s"), e.args[0]),
            Raise=True,
        )
    except utils.time.MissingTimezoneLibrary:
        irc.error(
            _(
                "Timezone-related commands are not available. "
                "Your administrator need to either upgrade Python to "
                "version 3.9 or greater, or install pytz."
            ),
            Raise=True,
        )
    except utils.time.TimezoneException as e:
        irc.error(e.args[0], Raise=True)


class Geography(callbacks.Plugin):
    """Provides geography facts, such as timezones.

    This plugin uses data from `Wikidata <https://wikidata.org/>`_
    and `OSM/Nominatim <https://nominatim.openstreetmap.org/>`.
    """

    threaded = True

    @wrap(["text"])
    def localtime(self, irc, msg, args, query):
        """<location name to search>

        Returns the current used in the given location. For example,
        the name could be "Paris" or "Paris, France". The response is
        formatted according to supybot.reply.format.time
        This uses data from Wikidata and Nominatim."""
        osmids = nominatim.search_osmids(query)
        if not osmids:
            irc.error(_("Could not find the location"), Raise=True)

        for osmid in osmids:
            uri = wikidata.uri_from_osmid(osmid)
            if not uri:
                continue

            # Get the timezone object (and handle various errors)
            timezone = timezone_from_uri(irc, uri)

            if timezone is None:
                continue

            # Get the local time
            now = datetime.datetime.now(tz=timezone)

            format_ = conf.supybot.reply.format.time.getSpecific(
                channel=msg.channel, network=irc.network
            )()

            # Return it
            irc.reply(now.strftime(format_))

            return

        irc.error(
            _("Could not find the timezone of this location."), Raise=True
        )

    @wrap(["text"])
    def timezone(self, irc, msg, args, query):
        """<location name to search>

        Returns the timezone used in the given location. For example,
        the name could be "Paris" or "Paris, France".
        This uses data from Wikidata and Nominatim."""
        osmids = nominatim.search_osmids(query)
        if not osmids:
            irc.error(_("Could not find the location"), Raise=True)

        now = datetime.datetime.now(tz=datetime.timezone.utc)

        for osmid in osmids:
            uri = wikidata.uri_from_osmid(osmid)
            if not uri:
                continue

            # Get the timezone object (and handle various errors)
            timezone = timezone_from_uri(irc, uri)

            if timezone is None:
                continue

            offset = str(datetime.datetime.now(tz=timezone).utcoffset())
            if not offset.startswith("-"):
                offset = "+" + offset

            # hide seconds and minutes if they are zero
            offset = re.sub("(:00)+$", "", offset)

            # Extract a human-friendly name, depending on the type of
            # the timezone object:
            if hasattr(timezone, "key"):
                # instance of zoneinfo.ZoneInfo
                irc.reply(format("%s (currently UTC%s)", timezone.key, offset))
                return
            elif hasattr(timezone, "zone"):
                # instance of pytz.timezone
                irc.reply(format("%s (currently UTC%s)", timezone.zone, offset))
                return
            else:
                # probably datetime.timezone built from a constant offset
                try:
                    offset = timezone.utcoffset(now).seconds
                except NotImplementedError:
                    continue

                hours = int(offset / 3600)
                minutes = int(offset / 60 % 60)
                irc.reply("UTC+%0.2i:%0.2i" % (hours, minutes))
                return

        irc.error(
            _("Could not find the timezone of this location."), Raise=True
        )


Class = Geography


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
