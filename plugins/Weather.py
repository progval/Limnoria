#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

"""
This plugin does weather-related stuff.  It can't change the weather, though,
so don't get your hopes up.  We just report it.
"""

__revision__ = "$Id$"

import plugins

import re
import sets
import urllib

import conf
import utils
import webutils
import ircutils
import privmsgs
import registry
import callbacks

unitAbbrevs = utils.abbrev(['Fahrenheit', 'Celsius', 'Centigrade', 'Kelvin'])
unitAbbrevs['C'] = 'Celsius'
unitAbbrevs['Ce'] = 'Celsius'

class WeatherUnit(registry.String):
    def setValue(self, s):
        #print '***', repr(s)
        s = s.capitalize()
        if s not in unitAbbrevs:
            raise registry.InvalidRegistryValue,\
                  'Unit must be one of Fahrenheit, Celsius, or Kelvin.'
        s = unitAbbrevs[s]
        registry.String.setValue(self, s)

class WeatherCommand(registry.String):
    def setValue(self, s):
        m = Weather.weatherCommands
        if s not in m:
            raise registry.InvalidRegistryValue,\
                  'Command must be one of %s' % utils.commaAndify(m)
        else:
            method = getattr(Weather, s)
            Weather.weather.im_func.__doc__ = method.__doc__
        registry.String.setValue(self, s)

# Registry variables moved to the bottom to use Weather.weatherCommands.

class Weather(callbacks.Privmsg):
    weatherCommands = ['ham', 'cnn', 'wunder']
    threaded = True
    def callCommand(self, method, irc, msg, *L):
        try:
            callbacks.Privmsg.callCommand(self, method, irc, msg, *L)
        except webutils.WebError, e:
            irc.error(str(e))
            
    def weather(self, irc, msg, args):
        # This specifically does not have a docstring.
        channel = None
        if ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
        if not args:
            s = self.userValue('lastLocation', msg.prefix)
            if s:
                args = [s]
        else:
            location = privmsgs.getArgs(args)
            self.setUserValue(msg.prefix, 'lastLocation',
                    location, ignoreNoUser=True)
        realCommandName = self.registryValue('command', channel)
        realCommand = getattr(self, realCommandName)
        realCommand(irc, msg, args)
        
    def _toCelsius(self, temp, unit):
        if unit == 'K':
            return temp - 273.15
        elif unit == 'F':
            return (temp - 32) * 5 /9
        else:
            return temp

    def _getTemp(self, temp, deg, unit, chan):
        assert unit == unit.upper()
        assert temp == int(temp)
        default = self.registryValue('temperatureUnit', chan)
        if unitAbbrevs[unit] == default:
            # Short circuit if we're the same unit as the default.
            return '%s%s%s' % (temp, deg, unit)
        temp = self._toCelsius(temp, unit)
        unit = 'C'
        if default == 'Kelvin':
            temp = temp + 273.15
            unit = 'K'
            deg = ' '
        elif default == 'Fahrenheit':
            temp = temp * 9 / 5 + 32
            unit = 'F'
        return '%s%s%s' % (temp, deg, unit)

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
    _temp = re.compile(r'(-?\d+)(.*?)(F|C)')
    _hamChill = re.compile(
        r'Wind Chill</font></strong>:</small></td>\s+<td align="right">'
        r'<small><font face="arial">([^N][^<]+)</font></small></td>',
         re.I | re.S)
    _hamHeat = re.compile(
        r'Heat Index</font></strong>:</small></td>\s+<td align="right">'
        r'<small><font face="arial">([^N][^<]+)</font></small></td>',
         re.I | re.S)
    # States
    _realStates = sets.Set(['ak', 'al', 'ar', 'az', 'ca', 'co', 'ct', 
                            'dc', 'de', 'fl', 'ga', 'hi', 'ia', 'id',
                            'il', 'in', 'ks', 'ky', 'la', 'ma', 'md',
                            'me', 'mi', 'mn', 'mo', 'ms', 'mt', 'nc',
                            'nd', 'ne', 'nh', 'nj', 'nm', 'nv', 'ny',
                            'oh', 'ok', 'or', 'pa', 'ri', 'sc', 'sd',
                            'tn', 'tx', 'ut', 'va', 'vt', 'wa', 'wi',
                            'wv', 'wy'])
    # Provinces.  (Province being a metric state measurement mind you. :D)
    _fakeStates = sets.Set(['ab', 'bc', 'mb', 'nb', 'nf', 'ns', 'nt',
                           'nu', 'on', 'pe', 'qc', 'sk', 'yk'])
    # Certain countries are expected to use a standard abbreviation
    # The weather we pull uses weird codes.  Map obvious ones here.
    _hamCountryMap = {'uk': 'gb'}
    def ham(self, irc, msg, args):
        """<US zip code | US/Canada city, state | Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """
        
        #If we received more than one argument, then we have received
        #a city and state argument that we need to process.
        if len(args) > 1:
            #If we received more than 1 argument, then we got a city with a
            #multi-word name.  ie ['Garden', 'City', 'KS'] instead of
            #['Liberal', 'KS'].  We join it together with a + to pass
            #to our query
            state = args.pop()
            state = state.lower()
            city = '+'.join(args)
            city = city.rstrip(',')
            city = city.lower()
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
            html = webutils.getUrl(url)
            if 'was not found' in html:
                url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?' \
                      'pass=&dpp=&forecast=zandh&config=&' \
                      'place=%s&state=&country=%s' % (city, state)
                html = webutils.getUrl(url)
                if 'was not found' in html: # Still.
                    irc.error('No such location could be found.')
                    return

        #We received a single argument.  Zipcode or station id.
        else:
            zip = privmsgs.getArgs(args)
            zip = zip.replace(',', '')  
            zip = zip.lower()
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?' \
                  'config=&forecast=zandh&pands=%s&Submit=GO' % zip
            html = webutils.getUrl(url)
            if 'was not found' in html:
                irc.error('No such location could be found.')
                return
                
        headData = self._hamLoc.search(html)
        if headData is not None:
            (city, state, country) = headData.groups()
        else:
            headData = self._interregex.search(html)
            if headData:
                (city, state) = headData.groups()
            else:
                irc.error('No such location could be found.')
                return

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
            chill = utils.htmlToText(chill)
            if convert:
                tempsplit = self._temp.search(chill)
                if tempsplit:
                    (chill, deg, unit) = tempsplit.groups()
                    chill = self._getTemp(int(chill), deg, unit,msg.args[0])
            if float(chill[:-2]) < float(temp[:-2]):
                index = ' (Wind Chill: %s)' % chill
        heat = self._hamHeat.search(html)
        if heat is not None:
            heat = heat.group(1)
            heat = utils.htmlToText(heat)
            if convert:
                tempsplit = self._temp.search(heat)
                if tempsplit:
                    (heat, deg, unit) = tempsplit.groups()
                    if convert:
                        heat = self._getTemp(int(heat), deg, unit,msg.args[0])
            if float(heat[:-2]) > float(temp[:-2]):
                index = ' (Heat Index: %s)' % heat
        if temp and conds and city and state:
            conds = conds.replace('Tsra', 'Thunderstorms')
            conds = conds.replace('Ts', 'Thunderstorms')
            s = 'The current temperature at %s, %s is %s%s. Conditions: %s.'% \
                (city, state, temp, index, conds)
            irc.reply(s)
        else:
            irc.error('The format of the page was odd.')

    _cnnUrl = 'http://weather.cnn.com/weather/search?wsearch='
    _cnnFTemp = re.compile(r'(-?\d+)(&deg;)(F)</span>', re.I | re.S)
    _cnnCond = re.compile(r'align="center"><b>([^<]+)</b></div></td>',
                          re.I | re.S)
    _cnnHumid = re.compile(r'Rel. Humidity: <b>(\d+%)</b>', re.I | re.S)
    _cnnWind = re.compile(r'Wind: <b>([^<]+)</b>', re.I | re.S)
    _cnnLoc = re.compile(r'<title>([^<]+)</title>', re.I | re.S)
    # Certain countries are expected to use a standard abbreviation
    # The weather we pull uses weird codes.  Map obvious ones here.
    _cnnCountryMap = {'uk': 'en', 'de': 'ge'}
    def cnn(self, irc, msg, args):
        """<US zip code | US/Canada city, state | Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """
        if len(args) > 1:
            #If we received more than 1 argument, then we got a city with a
            #multi-word name.  ie ['Garden', 'City', 'KS'] instead of
            #['Liberal', 'KS'].  We join it together with a + to pass
            #to our query
            state = args.pop().lower()
            city = ' '.join(args)
            city = city.rstrip(',').lower()
            if state in self._cnnCountryMap:
                state = self._cnnCountryMap[state]
            loc = ' '.join([city, state])
        else:
            #We received a single argument.  Zipcode or station id.
            zip = privmsgs.getArgs(args)
            loc = zip.replace(',', '').lower()
        url = '%s%s' % (self._cnnUrl, urllib.quote(loc))
        try:
            text = webutils.getUrl(url)
        except webutils.WebError, e:
            irc.error(str(e))
            return
        if "No search results" in text or "does not match a zip code" in text:
            irc.error('No such location could be found.')
            return
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
            resp = ['The current temperature at %s is %s.' % (location, temp)]
            if conds is not None:
                resp.append('Conditions: %s.' % conds.group(1))
            if humidity is not None:
                resp.append('Humidity: %s.' % humidity.group(1))
            if wind is not None:
                resp.append('Wind: %s.' % wind.group(1))
            resp = map(utils.htmlToText, resp)
            irc.reply(' '.join(resp))
        else:
            irc.error('Could not find weather information.')

    _wunderUrl = 'http://www.weatherunderground.com/cgi-bin/findweather/'\
                 'getForecast?query='
    _wunderLoc = re.compile(r'<title>[^:]+: ([^<]+)</title>', re.I | re.S)
    _wunderFTemp = re.compile(
        r'graphics/conds.*?<nobr><b>(-?\d+)</b>&nbsp;(&#176;)(F)</nobr>',
        re.I | re.S)
    _wunderCond = re.compile(r'</b></font><br>\s+<font size=-1><b>([^<]+)</b>',
                             re.I | re.S)
    _wunderHumid = re.compile(r'Humidity:</td><td[^>]+><b>(\d+%)</b>',
                              re.I | re.S)
    _wunderDew = re.compile(r'Dew Point:</td><td[^>]+><b>\s+<nobr><b>'
                            r'(-?\d+)</b>&nbsp;(&#176;)(F)</nobr>',
                            re.I | re.S)
    _wunderWind = re.compile(
        r'Wind:</td><td[^>]+>\s+<b>\s+<nobr><b>(\d+)</b>&nbsp;(mph)'
        r'</nobr>\s+/\s+<nobr><b>(\d+)</b>&nbsp;(km/h)</nobr>\s+</b>'
        r'\s+from the\s+<b>(\w{3})</b>', re.I | re.S)
    _wunderPressure = re.compile(
        r'Pressure:</td><td[^<]+><b>\s+<b>(\d+\.\d+)</b>&nbsp;(in)\s+/\s+'
        r'<b>(\d+)</b>&nbsp;(hPa)', re.I | re.S)
    _wunderVisible = re.compile(
        r'Visibility:</td><td[^>]+><b>\s+<nobr><b>(\w+)</b>&nbsp;(miles)'
        r'</nobr>\s+/\s+<nobr><b>(\w+)</b>&nbsp;(kilometers)</nobr>',
        re.I | re.S)
    _wunderUv = re.compile(r'UV:</td><td[^>]+><b>(\d\d?)</b>', re.I | re.S)
    _wunderTime = re.compile(r'Updated:\s+<b>([\w\s:,]+)</b>', re.I | re.S)
    def wunder(self, irc, msg, args):
        """<US zip code | US/Canada city, state | Foreign city, country>

        Returns the approximate weather conditions for a given city.
        """
        loc = ' '.join(args)
        url = '%s%s' % (self._wunderUrl, urllib.quote(loc))
        try:
            text = webutils.getUrl(url)
        except webutils.WebError, e:
            irc.error(str(e))
            return
        if 'Search not found' in text:
            irc.error('No such location could be found.')
            return
        if 'Search results for' in text:
            irc.error('Multiple locations found.  Please be more specific.')
            return
        location = self._wunderLoc.search(text)
        temp = self._wunderFTemp.search(text)
        convert = self.registryValue('convert', msg.args[0])
        if location and temp:
            location = location.group(1)
            location = location.replace(' Forecast', '')
            (temp, deg, unit) = temp.groups()
            if convert:
                temp = self._getTemp(int(temp), deg, unit, msg.args[0])
            else:
                temp = deg.join((temp, unit))
            time = self._wunderTime.search(text)
            if time is not None:
                time = ' (%s)' % time.group(1)
            else:
                time = ''
            resp = ['The current temperature at %s is %s%s.' %\
                    (location, temp, time)]
            conds = self._wunderCond.search(text)
            if conds is not None:
                resp.append('Conditions: %s.' % conds.group(1))
            humidity = self._wunderHumid.search(text)
            if humidity is not None:
                resp.append('Humidity: %s.' % humidity.group(1))
            dewpt = self._wunderDew.search(text)
            if dewpt is not None:
                (dew, deg, unit) = dewpt.groups()
                if convert:
                    dew = self._getTemp(int(dew), deg, unit, msg.args[0])
                else:
                    dew = deg.join((dew, unit))
                resp.append('Dew Point: %s.' % dew)
            wind = self._wunderWind.search(text)
            if wind is not None:
                resp.append('Wind: %s at %s %s (%s %s).' % (wind.group(5),
                                                            wind.group(1),
                                                            wind.group(2),
                                                            wind.group(3),
                                                            wind.group(4)))
            press = self._wunderPressure.search(text)
            if press is not None:
                resp.append('Pressure: %s %s (%s %s).' % press.groups())
            vis = self._wunderVisible.search(text)
            if vis is not None:
                resp.append('Visibility: %s %s (%s %s).' % vis.groups())
            uv = self._wunderUv.search(text)
            if uv is not None:
                resp.append('UV: %s' % uv.group(1))
            resp = map(utils.htmlToText, resp)
            irc.reply(' '.join(resp))
        else:
            irc.error('Could not find weather information.')

conf.registerPlugin('Weather')
conf.registerChannelValue(conf.supybot.plugins.Weather, 'temperatureUnit',
    WeatherUnit('Fahrenheit', """Sets the default temperature unit to use when
    reporting the weather."""))
conf.registerChannelValue(conf.supybot.plugins.Weather, 'command',
    WeatherCommand('cnn', """Sets the default command to use when retrieving 
    the weather.  Command must be one of %s.""" %
    utils.commaAndify(Weather.weatherCommands, And='or')))
conf.registerChannelValue(conf.supybot.plugins.Weather, 'convert',
    registry.Boolean(True, """Determines whether the weather commands will
    automatically convert weather units to the unit specified in
    supybot.plugins.Weather.temperatureUnit."""))

conf.registerUserValue(conf.users.plugins.Weather, 'lastLocation',
    registry.String('', ''))

Class = Weather

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
