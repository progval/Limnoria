###
# Copyright (c) 2005, James Vega
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

import rssparser
import BeautifulSoup

import supybot.utils as utils
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


unitAbbrevs = utils.abbrev(['Fahrenheit', 'Celsius', 'Centigrade', 'Kelvin'])
unitAbbrevs['C'] = 'Celsius'
unitAbbrevs['Ce'] = 'Celsius'

noLocationError = 'No such location could be found.'
class NoLocation(callbacks.Error):
    pass

class Weather(callbacks.Plugin):
    weatherCommands = ['wunder', 'rsswunder', 'cnn', 'ham']
    threaded = True
    def __init__(self, irc):
        self.__parent = super(Weather, self)
        self.__parent.__init__(irc)

    def callCommand(self, name, irc, msg, *L, **kwargs):
        try:
            self.__parent.callCommand(name, irc, msg, *L, **kwargs)
        except utils.web.Error, e:
            irc.error(str(e))

    def _noLocation(self):
        raise NoLocation, noLocationError

    def weather(self, irc, msg, args, location):
        """<US zip code | US/Canada city, state | Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """
        channel = None
        if irc.isChannel(msg.args[0]):
            channel = msg.args[0]
        if not location:
            location = self.userValue('lastLocation', msg.prefix)
        if not location:
            raise callbacks.ArgumentError
        self.setUserValue('lastLocation', msg.prefix,
                          location, ignoreNoUser=True)
        args = [location]
        realCommandName = self.registryValue('command', channel)
        realCommand = getattr(self, realCommandName)
        try:
            realCommand(irc, msg, args[:])
        except NoLocation:
            self.log.info('%s lookup failed, Trying others.', realCommandName)
            for command in self.weatherCommands:
                if command != realCommandName:
                    self.log.info('Trying %s.', command)
                    try:
                        getattr(self, command)(irc, msg, args[:])
                        self.log.info('%s lookup succeeded.', command)
                        return
                    except NoLocation:
                        self.log.info('%s lookup failed as backup.', command)
            irc.error(format('Could not retrieve weather for %q.', location))
    weather = wrap(weather, [additional('text')])

    def _toCelsius(self, temp, unit):
        if unit == 'K':
            return temp - 273.15
        elif unit == 'F':
            return (temp - 32) * 5 /9
        else:
            return temp

    _temp = re.compile(r'(-?\d+)(.*?)(F|C)')
    def _getTemp(self, temp, deg, unit, chan):
        assert unit == unit.upper()
        assert temp == int(temp)
        default = self.registryValue('temperatureUnit', chan)
        if unitAbbrevs[unit] == default:
            # Short circuit if we're the same unit as the default.
            return format('%i%s%s', temp, deg, unit)
        temp = self._toCelsius(temp, unit)
        unit = 'C'
        if default == 'Kelvin':
            temp = temp + 273.15
            unit = 'K'
            deg = ' '
        elif default == 'Fahrenheit':
            temp = temp * 9 / 5 + 32
            unit = 'F'
        return '%i%s%s' % (temp, deg, unit)

    _hamLoc = re.compile(
        r'<td><font size="4" face="arial"><b>'
        r'(.*?), (.*?),(.*?)</b></font></td>', re.I)
    _interregex = re.compile(
        r'<td><font size="4" face="arial"><b>'
        r'([^,]+), ([^<]+)</b></font></td>', re.I)
    _hamCond = re.compile(
        r'<td width="100%" colspan="2" align="center"><strong>'
        r'<font face="arial">([^<]+)</font></strong></td>', re.I)
    _hamTemp = re.compile(
        r'<td valign="top" align="right"><strong><font face="arial">'
        r'(-?\d+)(.*?)(F|C)</font></strong></td>', re.I)
    _hamChill = re.compile(
        r'Wind Chill</font></strong>:</small></td>\s+<td align="right">'
        r'<small><font face="arial">([^N][^<]+)</font></small></td>',
         re.I | re.S)
    _hamHeat = re.compile(
        r'Heat Index</font></strong>:</small></td>\s+<td align="right">'
        r'<small><font face="arial">([^N][^<]+)</font></small></td>',
         re.I | re.S)
    # States
    _realStates = set(['ak', 'al', 'ar', 'az', 'ca', 'co', 'ct',
                       'dc', 'de', 'fl', 'ga', 'hi', 'ia', 'id',
                       'il', 'in', 'ks', 'ky', 'la', 'ma', 'md',
                       'me', 'mi', 'mn', 'mo', 'ms', 'mt', 'nc',
                       'nd', 'ne', 'nh', 'nj', 'nm', 'nv', 'ny',
                       'oh', 'ok', 'or', 'pa', 'ri', 'sc', 'sd',
                       'tn', 'tx', 'ut', 'va', 'vt', 'wa', 'wi',
                       'wv', 'wy'])
    # Provinces.  (Province being a metric state measurement mind you. :D)
    _fakeStates = set(['ab', 'bc', 'mb', 'nb', 'nf', 'ns', 'nt',
                       'nu', 'on', 'pe', 'qc', 'sk', 'yk'])
    # Certain countries are expected to use a standard abbreviation
    # The weather we pull uses weird codes.  Map obvious ones here.
    _hamCountryMap = {'uk': 'gb'}
    def ham(self, irc, msg, args, loc):
        """<US zip code | US/Canada city, state | Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """

        #If we received more than one argument, then we have received
        #a city and state argument that we need to process.
        if ' ' in loc:
            #If we received more than 1 argument, then we got a city with a
            #multi-word name.  ie ['Garden', 'City', 'KS'] instead of
            #['Liberal', 'KS'].  We join it together with a + to pass
            #to our query
            loc = utils.str.rsplit(loc, None, 1)
            state = loc.pop().lower()
            city = '+'.join(loc)
            city = city.rstrip(',').lower()
            #We must break the States up into two sections.  The US and
            #Canada are the only countries that require a State argument.

            if state in self._realStates:
                country = 'us'
            elif state in self._fakeStates:
                country = 'ca'
            else:
                country = state
                state = ''
            if country in self._hamCountryMap.keys():
                country = self._hamCountryMap[country]
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?' \
                  'pass=&dpp=&forecast=zandh&config=&' \
                  'place=%s&state=%s&country=%s' % (city, state, country)
            html = utils.web.getUrl(url)
            if 'was not found' in html:
                url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?' \
                      'pass=&dpp=&forecast=zandh&config=&' \
                      'place=%s&state=&country=%s' % (city, state)
                html = utils.web.getUrl(url)
                if 'was not found' in html: # Still.
                    self._noLocation()

        #We received a single argument.  Zipcode or station id.
        else:
            zip = loc.replace(',', '')
            zip = zip.lower()
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?' \
                  'config=&forecast=zandh&pands=%s&Submit=GO' % zip
            html = utils.web.getUrl(url)
            if 'was not found' in html:
                self._noLocation()

        headData = self._hamLoc.search(html)
        if headData is not None:
            (city, state, country) = headData.groups()
        else:
            headData = self._interregex.search(html)
            if headData:
                (city, state) = headData.groups()
            else:
                self._noLocation()

        city = city.strip()
        state = state.strip()
        temp = self._hamTemp.search(html)
        convert = self.registryValue('convert', msg.args[0])
        if temp is not None:
            (temp, deg, unit) = temp.groups()
            if convert:
                temp = self._getTemp(int(temp), deg, unit, msg.args[0])
            else:
                temp = deg.join((temp, unit))
        conds = self._hamCond.search(html)
        if conds is not None:
            conds = conds.group(1)
        index = ''
        chill = self._hamChill.search(html)
        if chill is not None:
            chill = chill.group(1)
            chill = utils.web.htmlToText(chill)
            if convert:
                tempsplit = self._temp.search(chill)
                if tempsplit:
                    (chill, deg, unit) = tempsplit.groups()
                    chill = self._getTemp(int(chill), deg, unit,msg.args[0])
            if float(chill[:-2]) < float(temp[:-2]):
                index = format(' (Wind Chill: %s)', chill)
        heat = self._hamHeat.search(html)
        if heat is not None:
            heat = heat.group(1)
            heat = utils.web.htmlToText(heat)
            if convert:
                tempsplit = self._temp.search(heat)
                if tempsplit:
                    (heat, deg, unit) = tempsplit.groups()
                    if convert:
                        heat = self._getTemp(int(heat), deg, unit,msg.args[0])
            if float(heat[:-2]) > float(temp[:-2]):
                index = format(' (Heat Index: %s)', heat)
        if temp and conds and city and state:
            conds = conds.replace('Tsra', 'Thunderstorms')
            conds = conds.replace('Ts', 'Thunderstorms')
            s = format('The current temperature in %s, %s is %s%s. '
                       'Conditions: %s.',
                       city, state, temp, index, conds)
            irc.reply(s)
        else:
            irc.errorPossibleBug('The format of the page was odd.')
    ham = wrap(ham, ['text'])

    _cnnUrl = 'http://weather.cnn.com/weather/search?wsearch='
    _cnnFTemp = re.compile(r'(-?\d+)(&deg;)(F)</span>', re.I | re.S)
    _cnnCond = re.compile(r'align="center"><b>([^<]+)</b></div></td>',
                          re.I | re.S)
    _cnnHumid = re.compile(r'Rel. Humidity: <b>(\d+%)</b>', re.I | re.S)
    _cnnWind = re.compile(r'Wind: <b>([^<]+)</b>', re.I | re.S)
    _cnnLoc = re.compile(r'<title>([^<]+)</title>', re.I | re.S)
    _cnnMultiLoc = re.compile(r'href="([^f]+forecast.jsp[^"]+)', re.I)
    # Certain countries are expected to use a standard abbreviation
    # The weather we pull uses weird codes.  Map obvious ones here.
    _cnnCountryMap = {'uk': 'en', 'de': 'ge'}
    def cnn(self, irc, msg, args, loc):
        """<US zip code | US/Canada city, state | Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """
        if ' ' in loc:
            #If we received more than 1 argument, then we got a city with a
            #multi-word name.  ie ['Garden', 'City', 'KS'] instead of
            #['Liberal', 'KS'].
            loc = utils.str.rsplit(loc, None, 1)
            state = loc.pop().lower()
            city = ' '.join(loc)
            city = city.rstrip(',').lower()
            if state in self._cnnCountryMap:
                state = self._cnnCountryMap[state]
            loc = ' '.join([city, state])
        else:
            #We received a single argument.  Zipcode or station id.
            loc = loc.replace(',', '')
        url = '%s%s' % (self._cnnUrl, utils.web.urlquote(loc))
        text = utils.web.getUrl(url) # Errors caught in callCommand.
        if 'No search results' in text or \
           'does not match a zip code' in text:
            self._noLocation()
        elif 'several matching locations for' in text:
            m = self._cnnMultiLoc.search(text)
            if m:
                text = utils.web.getUrl(m.group(1))
            else:
                self._noLocation()
        location = self._cnnLoc.search(text)
        temp = self._cnnFTemp.search(text)
        conds = self._cnnCond.search(text)
        humidity = self._cnnHumid.search(text)
        wind = self._cnnWind.search(text)
        convert = self.registryValue('convert', msg.args[0])
        if location and temp:
            location = location.group(1)
            location = location.split('-')[-1].strip()
            (temp, deg, unit) = temp.groups()
            if convert:
                temp = self._getTemp(int(temp), deg, unit, msg.args[0])
            else:
                temp = deg.join((temp, unit))
            resp = [format('The current temperature in %s is %s.',
                           location, temp)]
            if conds is not None:
                resp.append(format('Conditions: %s.', conds.group(1)))
            if humidity is not None:
                resp.append(format('Humidity: %s.', humidity.group(1)))
            if wind is not None:
                resp.append(format('Wind: %s.', wind.group(1)))
            resp = map(utils.web.htmlToText, resp)
            irc.reply(' '.join(resp))
        else:
            irc.errorPossibleBug('Could not find weather information.')
    cnn = wrap(cnn, ['text'])

    _wunderUrl = 'http://mobile.wunderground.com/cgi-bin/' \
                 'findweather/getForecast?query='
    _wunderSevere = re.compile(r'font color="?#ff0000"?>([^<]+)<', re.I)
    _wunderLoc = re.compile(r'<title> (.+?) Forecast</title>', re.I | re.S)
    _wunderMultiLoc = re.compile(r'<a href="([^"]+)', re.I | re.S)
    def wunder(self, irc, msg, args, loc):
        """<US zip code | US/Canada city, state | Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """
        url = '%s%s' % (self._wunderUrl, utils.web.urlquote(loc))
        text = utils.web.getUrl(url)
        severe = ''
        m = self._wunderSevere.search(text)
        if m:
            severe = ircutils.bold(format('  %s', m.group(1)))
        if 'Search not found' in text or \
           re.search(text, r'size="2"> Place </font>', re.I):
            self._noLocation()
        soup = BeautifulSoup.BeautifulSoup()
        soup.feed(text)
        # Get the table with all the weather info
        table = soup.first('table', {'border':'1'})
        if table is None:
            self._noLocation()
        trs = table.fetch('tr')
        try:
            time = trs.pop(0).first('b').string
        except AttributeError:
            time = ''
        info = {}
        def isText(t):
            return not isinstance(t,BeautifulSoup.NavigableText) and t.contents
        def getText(t):
            s = getattr(t, 'string', None)
            if s is None:
                t = t.contents
                num = t[0].string
                units = t[1].string
                # htmlToText strips leading whitespace, so we have to handle
                # strings with &nbsp; differently.
                if units.startswith('&nbsp;'):
                    units = utils.web.htmlToText(units)
                    s = ' '.join((num, units))
                else:
                    units = utils.web.htmlToText(units)
                    s = ' '.join((num, units[0], units[1:]))
            return s
        for tr in trs:
            k = tr.first('td').string
            v = filter(isText, tr.fetch('td')[1].contents)
            value = map(getText, v)
            info[k] = ' '.join(value)
        location = self._wunderLoc.search(text)
        temp = info['Temperature']
        convert = self.registryValue('convert', msg.args[0])
        if location and temp:
            (temp, deg, unit) = temp.split()[3:] # We only want temp format
            if convert:
                temp = self._getTemp(int(temp), deg, unit, msg.args[0])
            else:
                temp = deg.join((temp, unit))
            resp = ['The current temperature in %s is %s (%s).' %\
                    (location.group(1), temp, time)]
            conds = info['Conditions']
            resp.append('Conditions: %s.' % info['Conditions'])
            humidity = info['Humidity']
            resp.append('Humidity: %s.' % info['Humidity'])
            # Apparently, the "Dew Point" and "Wind" categories are occasionally
            # set to "-" instead of an actual reading. So, we'll just catch
            # the ValueError from trying to unpack a tuple of the wrong size.
            try:
                (dew, deg, unit) = info['Dew Point'].split()[3:]
                if convert:
                    dew = self._getTemp(int(dew), deg, unit, msg.args[0])
                else:
                    dew = deg.join((dew, unit))
                resp.append('Dew Point: %s.' % dew)
            except (ValueError, KeyError):
                pass
            try:
                resp.append('Wind: %s at %s %s.' % tuple(info['Wind'].split()))
            except (ValueError, TypeError):
                pass
            try:
                (chill, deg, unit) = info['Windchill'].split()[3:]
                if convert:
                    chill = self._getTemp(int(chill), deg, unit, msg.args[0])
                else:
                    dew = deg.join((chill, unit))
                resp.append('Windchill: %s.' % chill)
            except (ValueError, KeyError):
                pass
            if info['Pressure']:
                resp.append('Pressure: %s.' % info['Pressure'])
            if info['Visibility']:
                resp.append('Visibility: %s.' % info['Visibility'])
            resp.append(severe)
            resp = map(utils.web.htmlToText, resp)
            irc.reply(' '.join(resp))
        else:
            irc.error('Could not find weather information.')
    wunder = wrap(wunder, ['text'])

    _rsswunderUrl = 'http://www.wunderground.com/cgi-bin/findweather/' \
                    'getForecast?query=%s'
    _rsswunderfeed = re.compile(r'<link rel="alternate".*href="([^"]+)">',
                                re.I)
    _rsswunderSevere = re.compile(r'font color="?#ff0000"?><b>([^<]+)<', re.I)
    def rsswunder(self, irc, msg, args, loc):
        """<US zip code | US/Canada city, state | Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """
        url = self._rsswunderUrl % utils.web.urlquote(loc)
        url = url.replace('%20', '+')
        text = utils.web.getUrl(url)
        severe = ''
        m = self._rsswunderSevere.search(text)
        if m:
            severe = ircutils.bold(m.group(1))
        if 'Search not found' in text or \
           re.search(r'size="2"> Place </font>', text, re.I):
            self._noLocation()
        feed = self._rsswunderfeed.search(text)
        if not feed:
            irc._noLocation()
        feed = feed.group(1)
        rss = utils.web.getUrl(feed)
        info = rssparser.parse(rss)
        resp = [e['summary'] for e in info['entries']]
        resp = [s.encode('utf-8') for s in resp]
        resp.append(severe)
        irc.reply(utils.web.htmlToText('; '.join(resp)))
    rsswunder = wrap(rsswunder, ['text'])

Class = Weather


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
