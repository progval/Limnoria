###
# Copyright (c) 2014-2017, James Lu <james@overdrivenetworks.com>
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
import supybot.log as log
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('DDG')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


try:  # Python 3
    from urllib.parse import urlencode, parse_qs
except ImportError:  # Python 2
    from urllib import urlencode
    from urlparse import parse_qs
try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("Beautiful Soup 4 is required for this plugin: get it"
                      " at http://www.crummy.com/software/BeautifulSoup/bs4"
                      "/doc/#installing-beautiful-soup")


class DDG(callbacks.Plugin):
    """Searches for results on DuckDuckGo."""
    threaded = True

    @staticmethod
    def _ddgurl(text):
        # DuckDuckGo has a 'lite' site free of unparseable JavaScript
        # elements, so we'll use that to our advantage!
        url = "https://duckduckgo.com/lite?" + urlencode({"q": text})
        log.debug("DDG: Using URL %s for search %s", url, text)
        data = utils.web.getUrl(url).decode("utf-8")
        soup = BeautifulSoup(data)
        # Remove "sponsored link" results
        return [td for td in soup.find_all('td') if 'result-sponsored' not in str(td.parent.get('class'))]

    def search_core(self, text, channel_context=None, max_results=None, show_snippet=None):
        """
        Core results fetcher for the DDG plugin. Other plugins can call this as well via
        irc.getCallback('DDG').search_core(...)
        """
        if show_snippet is None:
            # Note: don't use ternary here, or the registry value will override any False
            # settings given to the function directly.
            show_snippet = self.registryValue("showSnippet", channel_context)
        maxr = max_results or self.registryValue("maxResults", channel_context)
        self.log.debug('DDG: got %s for max results', maxr)

        # In a nutshell, the 'lite' site puts all of its usable content
        # into tables. This means that headings, result snippets and
        # everything else are all using the same tag (<td>), which still makes
        # parsing somewhat tricky.
        results = []

        raw_results = self._ddgurl(text)
        for t in raw_results:
            res = ''
            # Each valid result has a preceding heading in the format
            # '<td valign="top">1.&nbsp;</td>', etc.
            if t.text[0].isdigit():
                res = t.next_sibling.next_sibling
            if not res:
                continue
            try:
                snippet = ''
                # 1) Get a result snippet.

                if self.registryValue("showsnippet", channel_context):
                    snippet = res.parent.next_sibling.next_sibling.\
                        find_all("td")[-1]
                    snippet = snippet.text.strip()
                # 2) Fetch the link title.
                title = res.a.text.strip()
                # 3) Fetch the result link.
                origlink = link = res.a.get('href')

                # As of 2017-01-20, some links on DuckDuckGo's site are shown going through
                # a redirect service. The links are in the format "/l/?kh=-1&uddg=https%3A%2F%2Fduckduckgo.com%2F"
                # instead of simply being "https://duckduckgo.com". So, we decode these links here.
                if link.startswith('/l/'):
                    linkparse = utils.web.urlparse(link)
                    try:
                        link = parse_qs(linkparse.query)['uddg'][0]
                    except KeyError:
                        # No link was given here, skip.
                        continue
                    except IndexError:
                        self.log.exception("DDG: failed to expand redirected result URL %s", origlink)
                        continue
                    else:
                        self.log.debug("DDG: expanded result URL from %s to %s", origlink, link)

                # Return a list of tuples in the form (link title, snippet text, link)
                results.append((title, snippet, link))

            except AttributeError:
                continue
        return results[:maxr]

    @wrap(['text'])
    def search(self, irc, msg, args, text):
        """<text>

        Searches for <text> on DuckDuckGo's web search."""
        results = self.search_core(text, msg.args[0])
        if not results:
            irc.error("No results found.")
        else:
            strings = [format("%s - %s %u", ircutils.bold(res[0]), res[1], res[2]) for res in results]
            irc.reply(', '.join(strings))

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
                # Condense newlines (<br> tags). XXX: make these separators configurable.
                for br in td.find_all('br'):
                    br.replace_with(' - ')
                res = ' | '.join(td.text.strip().split("\n"))
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
