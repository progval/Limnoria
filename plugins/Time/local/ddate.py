# Copyright (c) 2014, Adam Talsma <adam@talsma.ca>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
# * Neither the name of the {organization} nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from __future__ import print_function

import sys
import datetime


def is_leap_year(year):
    """Returns True if the integer year is a Gregorian leap year."""

    return ((year % 100 != 0 and year % 4 == 0) or
            (year % 100 == 0 and year % 400 == 0))


class DDate(object):
    """Discordian Date Object.

    Methods::

        __repr__: returns the typical repr plus the ddate attributes
        __str__: returns a formatted Discordian date string

    Attributes::

        date: the datetime.[date|datetime] object used to initialize with
        day_of_week: the ordinal integer day of the week (0-5), or None
        day_of_season: the cardinal integer day of the season (1-73), or None
        holiday: string holiday currently, or None
        season: ordinal integer season number (0-5)
        year: integer Discordian YOLD

    Statics::

        HOLIDAYS: dict of Discordian holidays, {type: [holidays_per_season]}
        SEASONS: list of strings, Discordian seasons
        WEEKDAYS: list of strings, Discordian days of the week
    """

    HOLIDAYS = {
        "apostle": [
            "Mungday",
            "Mojoday",
            "Syaday",
            "Zaraday",
            "Maladay",
        ],
        "seasonal": [
            "Chaoflux",
            "Discoflux",
            "Confuflux",
            "Bureflux",
            "Afflux",
        ],
    }
    SEASONS = [
        "Chaos",
        "Discord",
        "Confusion",
        "Bureaucracy",
        "The Aftermath",
    ]
    WEEKDAYS = [
        "Sweetmorn",
        "Boomtime",
        "Pungenday",
        "Prickle-Prickle",
        "Setting Orange",
    ]

    def __init__(self, date=None, year=None, season=None, day_of_season=None,
                 *args, **kwargs):
        """Discordian date setup and mangling.

        Note: year, season and day_of_season are all required if any are used

        Args:
            date: optional date object with a timetuple method, or uses today
            year: optional integer discordian year to create from
            season: optional integer discodian season to create from
            day_of_season: optional int discordian day of season to create from
        """

        if year is not None and season is not None and \
           day_of_season is not None:
            date = (datetime.datetime(year=year - 1166, month=1, day=1) +
                    datetime.timedelta(days=(season * 73) + day_of_season - 1))
        elif date is None or not hasattr(date, "timetuple"):
            date = datetime.date.today()
        self.date = date

        time_tuple = self.date.timetuple()

        # calculate leap year using tradtional methods to align holidays
        year = time_tuple.tm_year
        self.year = year + 1166  # then adjust accordingly and assign

        day_of_year = time_tuple.tm_yday - 1  # ordinal
        if is_leap_year(year) and day_of_year > 59:
            day_of_year -= 1  # St. Tib's doesn't count

        self.day_of_week = day_of_year % 5
        self.day_of_season = day_of_year % 73 + 1  # cardinal
        self.season = int(day_of_year / 73)

        if is_leap_year(year) and time_tuple.tm_yday == 60:
            self.holiday = "St. Tib's Day"
            self.day_of_week = None
            self.day_of_season = None
            self.season = None
        elif self.day_of_season == 5:
            self.holiday = self.HOLIDAYS["apostle"][self.season]
        elif self.day_of_season == 50:
            self.holiday = self.HOLIDAYS["seasonal"][self.season]
        else:
            self.holiday = None

        super(DDate, self).__init__(*args, **kwargs)

    def __str__(self):
        """Return a formatted string for the current date."""

        today = self.date.timetuple().tm_yday == datetime.date.today(
            ).timetuple().tm_yday

        if self.holiday == "St. Tib's Day":
            return "{today}{self.holiday}, {self.year} YOLD".format(
                today="Today is " if today else "",
                self=self,
            )
        else:
            return (
                "{today}{day}, the {self.day_of_season}{pfix}"
                " day of {season} in the YOLD {self.year}{holiday}"
            ).format(
                today="Today is " if today else "",
                day=self.WEEKDAYS[self.day_of_week],
                self=self,
                pfix=day_postfix(self.day_of_season),
                season=self.SEASONS[self.season],
                holiday=". Celebrate {0}!".format(
                    self.holiday) if self.holiday else "",
            )

    def __repr__(self):
        """Return our id and attributes."""

        attributes = []
        for attr in dir(self):
            if not attr.startswith("_") and attr.lower() == attr:
                attributes.append(
                    "{attr}: {{self.{attr}}}".format(attr=attr)
                )

        return "<{name}.{cls} object at {id}>\n<{cls} {attributes}>".format(
            name=__name__,
            cls=self.__class__.__name__,
            id=hex(id(self)),
            attributes=", ".join(attributes).format(self=self),
        )


def day_postfix(day):
    """Returns day's correct postfix (2nd, 3rd, 61st, etc)."""

    if day != 11 and day % 10 == 1:
        postfix = "st"
    elif day != 12 and day % 10 == 2:
        postfix = "nd"
    elif day != 13 and day % 10 == 3:
        postfix = "rd"
    else:
        postfix = "th"

    return postfix
