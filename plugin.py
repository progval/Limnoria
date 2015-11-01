###
# Copyright (c) 2014-2015, James Lu
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
    _ = lambda x: x


try:  # Python 3
    from urllib.parse import urlencode
except ImportError:  # Python 2
    from urllib import urlencode
try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("Beautiful Soup 4 is required for this plugin: get it"
                      " at http://www.crummy.com/software/BeautifulSoup/bs4"
                      "/doc/#installing-beautiful-soup")


class DDG(callbacks.Plugin):
    """Searches for results on DuckDuckGo."""
    threaded = True

    def _ddgurl(self, text):
        # DuckDuckGo has a 'lite' site free of unparseable JavaScript
        # elements, so we'll use that to our advantage!
        url = "https://duckduckgo.com/lite?" + urlencode({"q": text})
        self.log.debug("DDG: Using URL %s for search %s", url, text)
        data = utils.web.getUrl(url).decode("utf-8")
        soup = BeautifulSoup(data)
        # Remove "sponsored link" results
        return [td for td in soup.find_all('td') if 'result-sponsored' not in str(td.parent.get('class'))]

    def search(self, irc, msg, args, text):
        """<text>

        Searches for <text> on DuckDuckGo's web search."""
        replies = []
        channel = msg.args[0]
        # In a nutshell, the 'lite' site puts all of its usable content
        # into tables. This means that headings, result snippets and
        # everything else are all using the same tag (<td>), which makes
        # parsing somewhat difficult.
        for t in self._ddgurl(text):
            maxr = self.registryValue("maxResults", channel)
            # Hence we run a for loop to extract meaningful content:
            for n in range(1, maxr):
                res = ''
                # Each valid result has a preceding heading in the format
                # '<td valign="top">1.&nbsp;</td>', etc.
                if ("%s." % n) in t.text:
                    res = t.next_sibling.next_sibling
                if not res:
                    continue
                try:
                    snippet = ''
                    # 1) Get a result snippet.
                    if self.registryValue("showsnippet", channel):
                        snippet = res.parent.next_sibling.next_sibling.\
                            find_all("td")[-1]
                        snippet = snippet.text.strip()
                    # 2) Fetch the link title.
                    title = res.a.text.strip()
                    # 3) Fetch the result link.
                    link = res.a.get('href')
                    s = format("%s - %s %u", ircutils.bold(title), snippet,
                               link)
                    replies.append(s)
                except AttributeError:
                    continue
        else:
            if not replies:
                irc.error("No results found.")
            else:
                irc.reply(', '.join(replies))
    search = wrap(search, ['text'])

    @wrap(['text'])
    def zeroclick(self, irc, msg, args, text):
        """<text>

        Looks up <text> on DuckDuckGo's zero-click engine."""
        # Zero-click can give multiple replies for things if the
        # query is ambiguous, sort of like an encyclopedia.

        # For example, looking up "2^3" will give both:
        # Zero-click info: 8 (number)
        # Zero-click info: 8
        replies = {}
        for td in self._ddgurl(text):
            if td.text.startswith("Zero-click info:"):
                # Make a dictionary of things
                item = td.text.split("Zero-click info:", 1)[1].strip()
                td = td.parent.next_sibling.next_sibling.\
                            find("td")
                # Condense newlines (<br> tags)
                for br in td.find_all('br'):
                    br.replace_with(' - ')
                res = td.text.strip().split("\n")[0]
                try:
                    # Some zero-click results have an attached link to them.
                    link = td.a.get('href')
                    # Others have a piece of meaningless JavaScript...
                    if link != "javascript:;":
                        res += format(" %u", link)
                except AttributeError:
                    pass
                replies[item] = res
        else:
            if not replies:
                irc.error("No zero-click info could be found for '%s'." %
                          text, Raise=True)
            s = ["%s - %s" % (ircutils.bold(k), v) for k, v in replies.items()]
            irc.reply("; ".join(s))
Class = DDG


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
