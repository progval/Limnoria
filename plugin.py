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
        soup = BeautifulSoup(data)
        for t in soup.find_all('td'):
            if "1." in t.text:
                 res = t.next_sibling.next_sibling
            try:
                # 1) Get a result snippet.
                snippet = res.parent.next_sibling.next_sibling.find("td",
                     class_="result-snippet")
                # 2) Fetch the result link.
                link = res.a.get('href')
                snippet = snippet.text.strip()

                s = format("%s - %u", snippet, link)
                irc.reply(s)
                return
            except (AttributeError, UnboundLocalError):
                continue
        else:
            irc.error("No results found.")
    search = wrap(search, ['text'])

Class = DDG


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
