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
This plugin does weather-related stuff.
"""

import urllib
import plugins

import re
import sets

import conf
import utils
import webutils
import privmsgs
import registry
import callbacks

unitAbbrevs = utils.abbrev(['fahrenheit', 'celsius', 'centigrade', 'kelvin'])
unitAbbrevs['c'] = 'celsius'
unitAbbrevs['ce'] = 'celsius'

class WeatherUnit(registry.String):
    def set(self, s):
        original = getattr(self, 'value', self.default)
        registry.String.set(self, s)
        s = self.value.lower()
        if s not in unitAbbrevs:
            setattr(self, 'value', original)
            raise registry.InvalidRegistryValue,\
                'Unit must be one of fahrenheit, celsius, or kelvin.'

class WeatherCommand(registry.String):
    def set(self, s):
        original = getattr(self, 'value', self.default)
        registry.String.set(self, s)
        m = Weather.commands
        if self.value not in m:
            setattr(self, 'value', original)
            raise registry.InvalidRegistryValue,\
                'Command must be one of %s' % utils.commaAndify(m)

conf.registerPlugin('Weather')
conf.registerChannelValue(conf.supybot.plugins.Weather, 'preferredUnit',
    WeatherUnit('fahrenheit', """Sets the default temperature unit to use when
    reporting the weather."""))
conf.registerChannelValue(conf.supybot.plugins.Weather, 'weatherCommand',
    WeatherCommand('cnn', """Sets the default command to use when retrieving 
    the weather."""))

class Weather(callbacks.Privmsg):
    commands = ['ham', 'cnn']
    threaded = True
    def callCommand(self, method, irc, msg, *L):
        try:
            callbacks.Privmsg.callCommand(self, method, irc, msg, *L)
        except webutils.WebError, e:
            irc.error(str(e))
            
    def _getTemp(self, temp, deg, unit, chan):
        default = self.registryValue('preferredUnit', chan).lower()
        default = unitAbbrevs[default]
        unit = unit.lower()
        if unitAbbrevs[unit] == default:
            return deg.join([str(temp), unit.upper()])
        try:
            temp = int(temp)
        except ValueError:
            return deg.join([temp, unit])
        if unit == 'f':
            temp = (temp - 32) * 5 / 9
            if default == 'kelvin':
                temp = temp + 273.15
                unit = 'K'
                deg = ' '
            else:
                unit = 'C'
        elif unit == 'c':
            if default == 'kelvin':
                temp = temp + 273.15
                unit = 'K'
                deg = ' '
            elif default == 'fahrenheit':
                temp = temp * 9 / 5 + 32
                unit = 'F'
        return deg.join([str(temp), unit])

    _cityregex = re.compile(
        r'<td><font size="4" face="arial"><b>'
        r'(.*?), (.*?),(.*?)</b></font></td>', re.I)
    _interregex = re.compile(
        r'<td><font size="4" face="arial"><b>'
        r'([^,]+), ([^<]+)</b></font></td>', re.I)
    _condregex = re.compile(
        r'<td width="100%" colspan="2" align="center"><strong>'
        r'<font face="arial">([^<]+)</font></strong></td>', re.I)
    _tempregex = re.compile(
        r'<td valign="top" align="right"><strong><font face="arial">'
        r'([^<]+)</font></strong></td>', re.I)
    _chillregex = re.compile(
        r'Wind Chill</font></strong>:</small></a></td>\s+<td align="right">'
        r'<small><font face="arial">([^N][^<]+)</font></small></td>',
         re.I | re.S)
    _heatregex = re.compile(
        r'Heat Index</font></strong>:</small></a></td>\s+<td align="right">'
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
                
        headData = self._cityregex.search(html)
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
        temp = self._tempregex.search(html)
        if temp is not None:
            temp = temp.group(1)
            (temp, deg, unit) = (temp[:-2], temp[-2], temp[-1])
            temp = self._getTemp(temp, deg, unit, msg.args[0])
        conds = self._condregex.search(html)
        if conds is not None:
            conds = conds.group(1)
        index = ''
        chill = self._chillregex.search(html)
        if chill is not None:
            #self.log.warning(chill.groups())
            chill = chill.group(1)
            if int(chill[:-2]) < int(temp[:-2]):
                index = ' (Wind Chill: %s)' % chill
        heat = self._heatregex.search(html)
        if heat is not None:
            heat = heat.group(1)
            if int(heat[:-2]) > int(temp[:-2]):
                index = ' (Heat Index: %s)' % heat
        if temp and conds and city and state:
            conds = conds.replace('Tsra', 'Thunderstorms')
            s = 'The current temperature in %s, %s is %s%s. Conditions: %s.'% \
                (city, state, temp, index, conds)
            irc.reply(s)
        else:
            irc.error('The format of the page was odd.')

    _cnnUrl = 'http://weather.cnn.com/weather/search?wsearch='
    _fTemp = re.compile(r'(-?\d+&deg;F)</span>', re.I | re.S)
    _conds = re.compile(r'align="center"><b>([^<]+)</b></div></td>', re.I|re.S)
    _humidity = re.compile(r'Rel. Humidity: <b>(\d+%)</b>', re.I | re.S)
    _wind = re.compile(r'Wind: <b>([^<]+)</b>', re.I | re.S)
    _location = re.compile(r'<title>([^<]+)</title>', re.I | re.S)
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
        location = self._location.search(text)
        temp = self._fTemp.search(text)
        conds = self._conds.search(text)
        humidity = self._humidity.search(text)
        wind = self._wind.search(text)
        if location and temp:
            location = location.group(1)
            location = location.split('-')[-1].strip()
            temp = temp.group(1)
            (temp, deg, unit) = (temp[:-2], temp[-2], temp[-1])
            temp = self._getTemp(temp, deg, unit, msg.args[0])
            resp = 'The current temperature in %s is %s.' % (location, temp)
            resp = [resp]
            if conds is not None:
                resp.append('Conditions: %s.' % conds.group(1))
            if humidity is not None:
                resp.append('Humidity: %s.' % humidity.group(1))
            if wind is not None:
                resp.append('Wind: %s.' % wind.group(1))
            resp = map(utils.htmlToText, resp)
            irc.reply('  '.join(resp))
        else:
            irc.error('Could not find weather information.')

Class = Weather

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
