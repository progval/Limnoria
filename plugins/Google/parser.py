###
# Copyright (c) 2020-2021, Valentin Lorentz
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

import enum
import collections
from html.parser import HTMLParser

import supybot.utils as utils

result = collections.namedtuple('result', 'link title snippet')

@enum.unique
class ParserState(enum.Enum):
    OUTSIDE = 0
    IN_LINK = 1
    IN_TITLE = 2
    TITLE_PARSED = 3
    BREADCRUMBS_PARSED = 5
    LINK_PARSED = 6

@enum.unique
class DomMark(enum.Enum):
    """A mark on an element in the stack, to know when to change state when
    poping the element from the stack."""
    HEADING = 1
    BREADCRUMBS = 2

STACKED_TAGS = ('div', 'span', 'a')

class GoogleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.results = []

        self.reset_current_result()

    def reset_current_result(self):
        self.state = ParserState.OUTSIDE
        self.current_link = None
        self.current_title = None
        self.current_snippet = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()

        if tag in STACKED_TAGS:
            self.stack.append(tag)

        if tag == 'a' and attrs['href'].startswith('/url?q=') \
                and self.state == ParserState.OUTSIDE:
            self.state = ParserState.IN_LINK
            href = attrs['href'][len('/url?q='):]
            self.current_link = utils.web.urlunquote(href.split('&sa')[0])

        elif tag == 'h3' and 'a' in self.stack and self.state == ParserState.IN_LINK:
            self.state = ParserState.IN_TITLE
            mark = DomMark.HEADING

    def handle_endtag(self, tag):
        if tag in STACKED_TAGS:
            item = self.stack.pop()
            assert item == tag, (item, tag)

        if tag == 'a' and self.state in (
                ParserState.IN_LINK, ParserState.IN_TITLE, ParserState.BREADCRUMBS_PARSED):
            if self.current_title is None:
                # That wasn't a result
                self.state = ParserState.OUTSIDE
            else:
                self.state = ParserState.LINK_PARSED

    def handle_data(self, data):
        if self.state == ParserState.IN_TITLE:
            self.current_title = data
            self.state = ParserState.TITLE_PARSED
        elif self.state == ParserState.TITLE_PARSED:
            self.state = ParserState.BREADCRUMBS_PARSED
        elif self.state == ParserState.LINK_PARSED:
            self.current_snippet = data
            self.state = ParserState.OUTSIDE
            self.build_result()

    def build_result(self):
        self.results.append(result(
            link=self.current_link,
            title=self.current_title,
            snippet=self.current_snippet,
        ))
        self.reset_current_result()

if __name__ == '__main__':
    parser = GoogleHTMLParser()
    with open('google.html') as fd:
        parser.feed(fd.read())
    print(parser.results)

