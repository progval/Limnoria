###
# Copyright (c) 2014, James Lu
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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('DDG')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

import re
try: # Python 3
    from urllib.parse import urlencode
except ImportError: # Python 2
    from urllib import urlencode
try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("Beautiful Soup 4 is required for this plugin: get it"
        " at http://www.crummy.com/software/BeautifulSoup/bs4/doc/"
        "#installing-beautiful-soup")

class DDG(callbacks.Plugin):
    """Searches for results on DuckDuckGo."""
    threaded = True
    
    def search(self, irc, msg, args, text):
        """<query>
        
        Searches for <query> on DuckDuckGo (web search)."""
        url = "https://duckduckgo.com/lite?" + urlencode({"q":text})
        try:
            data = utils.web.getUrl(url).decode("utf-8")
        except utils.web.Error as e:
            self.log.info(url)
            irc.error(str(e), Raise=True)
        # GRR, having to clean up our HTML for the results...
        data = re.sub('\t|\r|\n', '', data)
        data = re.sub('\s{2,}', ' ', data)
        soup = BeautifulSoup(data)
        # DuckDuckGo lite uses tables for everything. Each WEB result is made 
        # up of 3 <tr> tags:
        tables = soup.find_all('table')
        
        webresults = tables[1].find_all('tr')
        if not webresults:
            # Sometimes there will be another table for page navigation.
            webresults = tables[2].find_all('tr')
        if webresults:
            try:
                if 'result-sponsored' in webresults[0]["class"]:
                    webresults = webresults[4:]
            except KeyError: pass
            # 1) The link and title.
            link = webresults[0].find('a').get('href')
            # 2) A result snippet.
            snippet = webresults[1].find("td", class_="result-snippet")
            try:
                snippet = snippet.text.strip()
            except AttributeError:
                snippet = webresults[1].td.text.strip()
            # 3) The link-text; essentially the same as the link in 1), but with the
            # URI (http(s)://) removed. We do not need this section.
            
            s = format("%s - %u", snippet, link)
            irc.reply(s)
        else:
            irc.error("No results found.")
    search = wrap(search, ['text'])

Class = DDG


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
