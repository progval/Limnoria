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

DEBUG = False

def debug(msg, *args):
    if DEBUG:
        print(msg % args)

result = collections.namedtuple('result', 'link title snippet')

@enum.unique
class ParserState(enum.Enum):
    OUTSIDE = 0
    IN_TITLE = 1
    TITLE_PARSED = 2
    IN_SNIPPET = 3


# This is implemented as a stack automaton. Here is the transition graph.
# See comments below to find the description of each transition
#
# --> OUTSIDE --(1)--> IN_TITLE --(2)--> TITLE_PARSED --(3)--> IN_SNIPPET
#       ^  ^                                  |                     |
#       |  |                                  |                     |
#       |  +----------------(5)---------------+                     |
#       |                                                           |
#       +------------------------------(4)--------------------------+


STACKED_TAGS = ('table', 'tr', 'td', 'a')

class DDGHTMLParser(HTMLParser):
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
            debug('Stacking %s with classes %s', tag, classes)
            self.stack.append((tag, classes))

        if ('tr', ['result-sponsored']) in self.stack:
            # Skip sponsored results
            return

        if tag == 'a' and 'result-link' in classes:
            # 1. Starts the title of a result; transition from OUTSIDE
            #    to IN_TITLE
            debug('Got result-link')
            assert self.state == ParserState.OUTSIDE, (self.state, self.current_title)
            self.state = ParserState.IN_TITLE
            self.current_link = attrs['href']
            self.current_title = []

        elif tag == 'td' and 'result-snippet' in classes:
            # 3. Starts a snippet. Normally, just after a title ended.
            #    Transition from TITLE_PARSED to IN_SNIPPET
            debug('Got result-snipper')
            assert self.state == ParserState.TITLE_PARSED, self.state
            self.state = ParserState.IN_SNIPPET
            self.current_snippet = []

        elif tag == 'span' and 'link-text' in classes:
            # 5. This is the link, after a snippet if any. We're catching it
            #    detect results without a snippet. If so, transition directly
            #    from TITLE_PARSED to OUTSIDE
            debug('Got link-text')
            if self.state == ParserState.TITLE_PARSED:
                # No snippet
                self.state = ParserState.OUTSIDE
                self.current_snippet = []

    def handle_endtag(self, tag):
        if tag in STACKED_TAGS:
            item = self.stack.pop()
            assert item[0] == tag, (item, tag)

        if tag == 'a' and self.state == ParserState.IN_TITLE:
            # 2. End of the <a> node matched in step 1; transition from
            #    IN_TITLE to TITLE_PARSED
            debug('Title parsed')
            self.state = ParserState.TITLE_PARSED
        elif tag == 'td' and self.state == ParserState.IN_SNIPPET:
            # 4. End of the <td> node matched in step 3, this concludes the
            #    parsing of this result. Transition from IN_SNIPPET to OUTSIDE
            debug('Snippet parsed')
            self.build_result()
            self.state = ParserState.OUTSIDE

    def handle_data(self, data):
        if self.state == ParserState.IN_TITLE:
            debug('Got title data: %s', data)
            self.current_title.append(data)
        elif self.state == ParserState.IN_SNIPPET:
            debug('Got snippet data: %s', data)
            self.current_snippet.append(data)

    def build_result(self):
        res = result(
            link=self.current_link,
            title=''.join(self.current_title),
            snippet=''.join(self.current_snippet),
        )
        debug('Finished parsing result: %r', res)
        self.results.append(res)
        self.reset_current_result()

if __name__ == '__main__':
    parser = DDGHTMLParser()
    with open('ddg2.html') as fd:
        parser.feed(fd.read())
    print(parser.results)
