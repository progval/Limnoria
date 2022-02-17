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

import re
import sys

if sys.version_info >= (3, 9):
    import zoneinfo
else:
    zoneinfo = None

try:
    import pytz
except ImportError:
    pytz = None

_IANA_TZ_RE = re.compile(r"([\w_-]+/)*[\w_-]+")

class TimezoneException(Exception):
    pass

class MissingTimezoneLibrary(TimezoneException):
    pass

class UnknownTimeZone(TimezoneException):
    pass

def iana_timezone(name):
    """Returns a :class:datetime.tzinfo object, given an IANA timezone name,
    eg. ``"Europe/Paris"``.

    This uses :class:``zoneinfo.ZoneInfo`` if available,
    :func:``pytz.timezone`` otherwise.

    May raise instances of :exc:`TimezoneException`.
    """
    if not _IANA_TZ_RE.match(name):
        raise UnknownTimeZone(name)

    if zoneinfo:
        try:
            return zoneinfo.ZoneInfo(name)
        except zoneinfo.ZoneInfoNotFoundError as e:
            raise UnknownTimeZone(e.args[0]) from None
    elif pytz:
        try:
            return pytz.timezone(name)
        except pytz.UnknownTimeZoneError as e:
            raise UnknownTimeZone(e.args[0]) from None
    else:
        raise MissingTimezoneLibrary(
            "Could not find a timezone library. "
            "Update Python to version 3.9 or newer, or install pytz."
        )
