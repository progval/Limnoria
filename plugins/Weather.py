#!/n/bronze/7/fincher/bin/python

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

import plugins

import re
import sets

import utils
import webutils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Weather')


class Weather(callbacks.Privmsg):
    threaded = True
    def callCommand(self, method, irc, msg, *L):
        try:
            callbacks.Privmsg.callCommand(self, method, irc, msg, *L)
        except webutils.WebError, e:
            irc.error(str(e))
            
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
        r'<small><font face="arial">([^<]+)</font></small></td>', re.I | re.S)
    _heatregex = re.compile(
        r'Heat Index</font></strong>:</small></a></td>\s+<td align="right">'
        r'<small><font face="arial">([^<]+)</font></small></td>', re.I | re.S)
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
    _countryMap = {'uk': 'gb'}
    def weather(self, irc, msg, args):
        """<US zip code> <US/Canada city, state> <Foreign city, country>

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
	    if country in self._countryMap.keys():
	        country = self._countryMap[country]
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?' \
                  'pass=&dpp=&forecast=zandh&config=&' \
                  'place=%s&state=%s&country=%s' % (city, state, country)
	    html = webutils.getUrl(url)
	    if 'was not found' in html:
	        url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?' \
		      'pass=&dpp=&forecast=zandh&config=&' \
		      'place=%s&state=&country=%s' % (city, state)
		html = webutils.getUrl(url)
		if 'was not found' in html:
		    irc.error('No such location could be found.')
		    return

        #We received a single argument.  Zipcode or station id.
        else:
            zip = privmsgs.getArgs(args)
            zip = zip.replace(',', '')  
            zip = zip.lower().split()
            url = 'http://www.hamweather.net/cgi-bin/hw3/hw3.cgi?' \
                  'config=&forecast=zandh&pands=%s&Submit=GO' % args[0]
            html = webutils.getUrl(url)
	    if 'was not found' in html:
	        irc.error('No such location could be found.')
		return
		
        headData = self._cityregex.search(html)
        if headData:
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
        if temp:
            temp = temp.group(1)
        conds = self._condregex.search(html)
        if conds:
            conds = conds.group(1)
        self.log.warning(repr(self._chillregex))
        if chill:
            #self.log.warning(chill.groups())
            chill = chill.group(1)
        heat = self._heatregex.search(html)
        if heat:
            heat = heat.group(1)

        if int(heat[:-2]) > int(temp[:-2]):
            index = ' (Heat Index: %s)' % heat
        elif int(chill[:-2]) < int(temp[:-2]):
            index = ' (Wind Chill: %s)' % chill
        else:
            index = ''

        if temp and conds and city and state:
            conds = conds.replace('Tsra', 'Thunder Storms')
            s = 'The current temperature in %s, %s is %s%s. Conditions: %s' % \
                (city, state, temp, index, conds)
            irc.reply(msg, s)
        else:
            irc.error('The format of the page was odd.')


Class = Weather

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
