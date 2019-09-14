###
# Copyright (c) 2004, Jeremiah Fincher
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

import sys
import time
TIME = time # For later use.
from datetime import datetime

import supybot.conf as conf
import supybot.log as log
import supybot.utils as utils
from supybot.commands import *
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Time')

try:
    from ddate.base import DDate as _ddate
except ImportError:
    log.debug("Time: the ddate module is not available; disabling that command.")
    _ddate = None

try:
    from dateutil import parser
    def parse(s):
        todo = []
        s = s.replace('noon', '12:00')
        s = s.replace('midnight', '00:00')
        if 'tomorrow' in s:
            todo.append(lambda i: i + 86400)
            s = s.replace('tomorrow', '')
        if 'next week' in s:
            todo.append(lambda i: i + 86400*7)
            s = s.replace('next week', '')
        i = int(time.mktime(parser.parse(s, fuzzy=True).timetuple()))
        for f in todo:
            i = f(i)
        return i
except ImportError:
    parse = None

try:
    from dateutil.tz import tzlocal
except ImportError:
    tzlocal = None

try:
    import pytz
except ImportError:
    pytz = None

class Time(callbacks.Plugin):
    """This plugin allows you to use different time-related functions."""
    @internationalizeDocstring
    def seconds(self, irc, msg, args):
        """[<years>y] [<weeks>w] [<days>d] [<hours>h] [<minutes>m] [<seconds>s]

        Returns the number of seconds in the number of <years>, <weeks>,
        <days>, <hours>, <minutes>, and <seconds> given.  An example usage is
        "seconds 2h 30m", which would return 9000, which is '3600*2 + 30*60'.
        Useful for scheduling events at a given number of seconds in the
        future.
        """
        if not args:
            raise callbacks.ArgumentError
        seconds = 0
        for arg in args:
            if not arg or arg[-1] not in 'ywdhms':
                raise callbacks.ArgumentError
            (s, kind) = arg[:-1], arg[-1]
            try:
                i = int(s)
            except ValueError:
                irc.errorInvalid('argument', arg, Raise=True)
            if kind == 'y':
                seconds += i*31536000
            elif kind == 'w':
                seconds += i*604800
            elif kind == 'd':
                seconds += i*86400
            elif kind == 'h':
                seconds += i*3600
            elif kind == 'm':
                seconds += i*60
            elif kind == 's':
                seconds += i
        irc.reply(str(seconds))

    @internationalizeDocstring
    def at(self, irc, msg, args, s=None):
        """[<time string>]

        Returns the number of seconds since epoch <time string> is.
        <time string> can be any number of natural formats; just try something
        and see if it will work.
        If the <time string> is not given, defaults to now.
        """
        if not s or s == 'now':
            irc.reply(str(int(time.time())))
            return
        if not parse:
            irc.error(_('This command is not available on this bot, ask the '
                'owner to install the python-dateutil library.'), Raise=True)
        now = int(time.time())
        new = parse(s)
        if new != now:
            irc.reply(str(new))
        else:
            irc.error(_('That\'s right now!'))
    at = wrap(at, [optional('text')])

    @internationalizeDocstring
    def until(self, irc, msg, args, s):
        """<time string>

        Returns the number of seconds until <time string>.
        """
        if not parse:
            irc.error(_('This command is not available on this bot, ask the '
                'owner to install the python-dateutil library.'), Raise=True)
        now = int(time.time())
        new = parse(s)
        if new != now:
            if new - now < 0:
                new += 86400
            irc.reply(str(new-now))
        else:
            irc.error(_('That\'s right now!'))
    until = wrap(until, ['text'])

    @internationalizeDocstring
    def ctime(self, irc, msg, args, seconds):
        """[<seconds since epoch>]

        Returns the ctime for <seconds since epoch>, or the current ctime if
        no <seconds since epoch> is given.
        """
        irc.reply(time.ctime(seconds))
    ctime = wrap(ctime,[additional(('int', _('number of seconds since epoch')),
                                    TIME.time)])

    @internationalizeDocstring
    def time(self, irc, msg, args, channel, format, seconds):
        """[<channel>] [<format>] [<seconds since epoch>]

        Returns the current time in <format> format, or, if <format> is not
        given, uses the configurable format for the current channel.  If no
        <seconds since epoch> time is given, the current time is used. If
        <channel> is given without <format>, uses the format for <channel>.
        """
        if not format:
            format = self.registryValue('format', channel or msg.channel,
                                        irc.network)
        if tzlocal:
            irc.reply(datetime.fromtimestamp(seconds, tzlocal()).strftime(format))
        else:
            # NOTE: This has erroneous behavior on some older Python versions,
            # including at least up to 2.7.5 and 3.2.3. Install dateutil if you
            # can't upgrade Python.
            irc.reply(time.strftime(format, time.localtime(seconds)))
    time = wrap(time, [optional('channel'), optional('nonInt'),
                       additional('float', TIME.time)])

    @internationalizeDocstring
    def elapsed(self, irc, msg, args, seconds):
        """<seconds>

        Returns a pretty string that is the amount of time represented by
        <seconds>.
        """
        irc.reply(utils.timeElapsed(seconds))
    elapsed = wrap(elapsed, ['int'])

    @internationalizeDocstring
    def tztime(self, irc, msg, args, timezone):
        """<region>/<city>

        Takes a city and its region, and returns its local time. This
        command uses the IANA Time Zone Database."""
        if pytz is None:
            irc.error(_('Python-tz is required by the command, but is not '
                        'installed on this computer.'), Raise=True)
        try:
            timezone = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            irc.error(_('Unknown timezone'), Raise=True)
        format = self.registryValue("format", msg.channel, irc.network)
        irc.reply(datetime.now(timezone).strftime(format))
    tztime = wrap(tztime, ['text'])

    def ddate(self, irc, msg, args, year=None, month=None, day=None):
        """[<year> <month> <day>]
        Returns a the Discordian date today, or an optional different date."""
        if _ddate is not None:
            if year is not None and month is not None and day is not None:
                try:
                    irc.reply(_ddate(datetime(year=year, month=month, day=day)))
                except ValueError as e:
                    irc.error("%s", e)
            else:
                irc.reply(_ddate())
        else:
            irc.error(format(_("The 'ddate' module is not installed. Use "
                               "'%s -m pip install --user ddate' or see "
                               "%u for more information."), sys.executable,
                               "https://pypi.python.org/pypi/ddate/"))
    ddate = wrap(ddate, [optional('positiveint'), optional('positiveint'), optional('positiveint')])
Class = Time

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
